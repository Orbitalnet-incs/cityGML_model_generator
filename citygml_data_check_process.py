"""
/***************************************************************************
 CityGMLDataCheckProcess   CityGMLモデル検査処理
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import os
import shutil

import xml.etree.ElementTree as ET 
import win32com.client

from PyQt5.QtGui import QPolygonF
from qgis.PyQt.QtCore import QThread, QLineF, QPointF, pyqtSignal
from qgis.core import QgsGeometry, QgsPointXY, QgsRectangle, QgsMessageLog

class CityGMLDataCheckProcess(QThread):

    progress_signal = pyqtSignal(int)

    def __init__(self, selectedFiles, out_dir):
        super().__init__()
        self.selectedFiles = selectedFiles
        self.out_dir = out_dir

        self.was_canceled = False
        self.dir_check_flg = True
        self.excel_app = None

        # 応用スキーマの名称
        self.appli_schemas = ['Building', 'BuildingPart', 'RoofSurface', 'WallSurface', 'GroundSurface', 'OuterCeilingSurface', 'OuterFloorSurface', 'ClosureSurface', 'OuterBuildingInstallation', 'Relief', 'TINRelief', 'Road', 'UrbanPlan', 'AreaClassification', 'DistrictAndZones', 'LandUse', 'GenericCityObject', 'WaterBody']

        # 検査結果テンプレートのパス
        self.template_xlsx = os.path.join(os.path.dirname(__file__), 'check_result', 'Result_List.xlsx')


    def run(self):
        '''
        /***************************************************************************
        検査と結果出力
        ***************************************************************************/
        '''

        # 外部XML(コードリスト)の検査結果
        self.parsed_codelists = {}

        ######################################################
        # Excelを開いておく
        try:
            self.excel_app = win32com.client.GetObject(Class="Excel.Application")
        except:
            self.excel_app = win32com.client.Dispatch("Excel.Application")        

        ################################################################
        # ファイル単位でループ
        # selectedFiles = self.selectedFiles
        self.dir_check_flg = True

        # 進捗バー表示の変数
        step = 0
        total_file_cnt = len(self.selectedFiles) # 出力ファイル数

        # プロセスダイアログに0%を明記
        self.progress_signal.emit(0)

        for fileInfo in self.selectedFiles:

            if self.was_canceled:
                break

            # ファイルパスを取得
            gml_file_path = fileInfo[0]
            # VectorLayerを取得
            layer = fileInfo[1]

            v_feature_count = layer.featureCount() # レイヤの地物数
            gml_bld_count = 0 # gmlファイルの地物数

            # ファイル単位の初期処理
            self.init_on_file()

            ################################################################
            # XML解析
            try:
                # 読み込みと解析
                tree = ET.parse(gml_file_path) 
            except Exception as e:
                # parseエラーがあればここでメッセージ格納
                #【2.1】整形式（Well-Formed XML)
                self.check_msg_building_2_1 = e
                tree = None

            ################################################################
            #【2.2】妥当なXML文書
            if not layer.isValid():
                self.check_msg_building_2_2 = "VectorLayerとして有効ではない"

            if tree :
                layer_rect = None
                root = tree.getroot()

                # 要素のデータを1つずつ取得
                for child in root:

                    if self.was_canceled:
                        # 子要素単位のループを抜ける
                        break

                    ################################################################
                    if child.tag.endswith("boundedBy"): # gml:boundedBy (１ファイル１つ前提)

                        layer_extent = []
                        for envelop in child:
                            # EPSGのチェック
                            crs = envelop.attrib['srsName']

                            #【2.5】CityGMLファイルのEPSGコード"
                            if not crs.endswith("6697"):
                                self.check_msg_building_2_5.append(str(crs)) 

                            # CityGMLファイル上で記載された領域を取得
                            for point in envelop:
                                temp_array = point.text.split(" ")
                                layer_extent.append(float(temp_array[0]))
                                layer_extent.append(float(temp_array[1]))

                        layer_rect = QgsRectangle(layer_extent[0], layer_extent[1], layer_extent[2], layer_extent[3])

                    ################################################################
                    elif child.tag.endswith("cityObjectMember"):
                        for building in child:
                            ################################################################
                            # 建物の単位の処理
                            bld_index = str(building.attrib).index("id':") + 5
                            building_id = str(building.attrib)[bld_index:].replace("\'", "").replace("}", "")

                            coodscape_array = []

                            ################################################################
                            # タグのチェック
                            schema_flg = False
                            for schema in self.appli_schemas:
                                if building.tag.endswith(schema):
                                    schema_flg = True
                                    break

                            if not schema_flg:
                                self.check_msg_building_2_3.append("gml_id:" + building_id + " [" + building.tag + "]")
                                break

                            for element in building:
                                # 各建物の立体情報
                                if(element.tag.endswith("lod1Solid")) :
                                    polygon_array = []
                                    self.isSelfIntersect = []       # 自己交差
                                    self.isPolygonIntersect = []    # 境界面交差
                                    self.isNotClosed = []           # 境界面自身が閉じている（検査項目外）

                                    # Polygon(側面)単位での処理
                                    surface_polygon_array = getPosListArray(element) # posListを配列にしたPolygon単位の配列
                                    surface_idx = 0 # ログ出力のため
                                    for postlist in surface_polygon_array:
                                        # start surface
                                        line_array = []

                                        ################################################################
                                        # チェックのための準備
                                        # 点のリストを作成
                                        points = getPoints(postlist)

                                        if (len(points) < 3):
                                            continue

                                        # ポリゴンと線作成
                                        polygon = QPolygonF()
                                        polygon.append(points[0]) # 1,2番目はここで追加
                                        polygon.append(points[1])
                                        for ip in range(2, len(points)):
                                            # ポリゴンに点を追加
                                            polygon.append(points[ip])
                                            # 点のリストから順に線分を生成
                                            line_array.append(QLineF(points[ip-2],points[ip-1]))
                                            ip = ip + 1

                                        ################################################################
                                        # ポリゴン判定
                                        if self.checkPolygon(surface_idx, polygon, line_array):
                                            polygon_array.append(polygon)

                                        surface_idx = surface_idx + 1
                                        # end surface

                                    ################################################################
                                    # 【12.5】ポリゴン間の交差（重複）判定
                                    self.checkPolygon2Polygon(surface_idx, polygon_array)

                                else:
                                    # codeSpaceチェック
                                    coodscape_array.append(getCodeSpaces(element))
                            
                            # gmlの地物数カウントアップ
                            gml_bld_count = gml_bld_count + 1

                            ################################################################
                            # ファイル単位のメッセージ配列に格納
                            for coods in coodscape_array:
                                for cood in coods:
                                    #【2.4】codeSpaceにより指定された辞書に定義されていない値となっている箇所数
                                    # codelistsフォルダの階層は規定で決まっている
                                    ret_flg = self.checkCodeOnCodeList(gml_file_path + "/../" + cood[0], cood[1])
                                    if not ret_flg:
                                        self.check_msg_building_2_4.append("gml_id : " + building_id + " [xml:" + cood[0] + " code:" + str(cood[1]) + "]")

                            if self.isSelfIntersect:
                                for selfIntersect in self.isSelfIntersect:
                                    self.check_msg_building_2_12_1.append("gml_id : " + building_id + " surfaceMember@:" + str(selfIntersect))

                            if self.isPolygonIntersect:
                                for intersect in self.isPolygonIntersect:
                                    self.check_msg_building_2_12_5.append("gml_id : " + building_id + " surfaceMember@:" + str(intersect))

                ################################################################
                # レイヤ内の地物チェック
                self.checkFeature(layer, layer_rect)

                # ベースデータとの確認
                if gml_bld_count != v_feature_count:
                    self.check_msg_building_1_2 = "地物数 参照データ:" + str(v_feature_count) + ", インスタンス:" + str(gml_bld_count)


            if self.was_canceled:
                # ファイル単位のループを抜ける
                break

            ################################################################
            # 検査結果出力（ファイル単位）
            ################################################################
            self.result_out_put(gml_file_path)

            ################################################################
            # プロセスカウントアップ（ファイル単位）
            step += 1
            progress_value = round(step * 100 / total_file_cnt)
            self.progress_signal.emit(progress_value)

            # end file loop

        # Excel処理終了
        if self.excel_app:
            self.excel_app.Quit()
                

    def init_on_file(self):
        '''
        /***************************************************************************
        ファイル単位の初期処理
        ***************************************************************************/
        '''

        # 検査結果格納配列
        self.check_msg_building_1_1 = []
        self.check_msg_building_1_2 = ""
        self.check_msg_building_2_1 = ""
        self.check_msg_building_2_2 = ""
        self.check_msg_building_2_3 = []
        self.check_msg_building_2_4 = []
        self.check_msg_building_2_5 = []
        self.check_msg_building_2_6 = []
        self.check_msg_building_2_12_1 = []
        self.check_msg_building_2_12_5 = []
        self.check_msg_building_2_16 = []


    def checkPolygon(self, surface_idx, polygon, line_array):
        '''
        /***************************************************************************
        ポリゴン単体のチェック
        ***************************************************************************/
        '''

        ################################################################
        # １．ポリゴン判定
        if not polygon.isClosed():
            self.isNotClosed.append(surface_idx)
            return False

        ################################################################
        # ２．自己交差チェック（ポリゴン内の線分同士の交差） (No.12-1)
        m = 0
        for org_line in line_array:
            m = m + 1
            for n in range(0, len(line_array)-1):
                intersect_point = QPointF()
                intersect_type  = org_line.intersect(line_array[n], intersect_point)
                if intersect_type == QLineF.BoundedIntersection:
                    # 自分の点は含めない
                    if (intersect_point != org_line.p1() and intersect_point != org_line.p2()
                        and intersect_point != line_array[n].p1() and intersect_point != line_array[n].p2()):
                        self.isSelfIntersect.append(str(surface_idx) + " on Point " + str(intersect_point.x()) + "," + str(intersect_point.y()))
                        return False

                    break
        
        return True


    def checkPolygon2Polygon(self, surface_idx, polygon_array):
        '''
        /***************************************************************************
        ポリゴン間のチェック（底辺が交差）
        ***************************************************************************/
        '''

        m = 0
        for org_pol in polygon_array:
            m = m + 1
            org_line = QLineF(org_pol[0], org_pol[1])
            for n in range(0, len(polygon_array)-1):
                poly_line = QLineF(polygon_array[n][0], polygon_array[n][1])

                intersect_point = QPointF()
                intersect_type  = org_line.intersect(poly_line, intersect_point)
                if intersect_type == QLineF.BoundedIntersection:
                    # 自分の点は含めない
                    if (intersect_point != org_line.p1() and intersect_point != org_line.p2()
                        and intersect_point != poly_line.p1() and intersect_point != poly_line.p2()):
                        self.isPolygonIntersect.append(str(surface_idx) + " on Point " + str(intersect_point.x()) + "," + str(intersect_point.y()))
                        break  


    def checkFeature(self, layer, layer_rect):
        '''
        /***************************************************************************
        ベクタレイヤのフィーチャ内容をチェック
        ***************************************************************************/
        '''

        # xmlファイルに記載された領域
        # xy取得(xy反転)(数ミリバッファー)
        x1 = layer_rect.yMinimum() - 0.0001
        y1 = layer_rect.xMinimum() - 0.0001
        x2 = layer_rect.yMaximum() + 0.0001
        y2 = layer_rect.xMaximum() + 0.0001

        rect = QgsRectangle(QgsPointXY(x1, y1), QgsPointXY(x2, y2))        
        extent_geom  = QgsGeometry().fromRect(rect) 
        # extent_geom  = QgsGeometry().fromRect(layer_rect)

        # 存在したgml_idの配列
        layer_gml_ids = []
        feature_geom_array = []
        feature_geom_id_array = [] # 上記配列の順番と同一に格納するgml_id

        # Feature
        for feature in layer.getFeatures():
            gml_id = feature.attribute('gml_id')
            if gml_id:

                #【1.1】すでに存在するかチェック 
                if gml_id in layer_gml_ids:
                    self.check_msg_building_1_1.append("gml_id:" +  str(gml_id))
                else:
                    layer_gml_ids.append(gml_id)

                #【2.6】GeometoryがExtent内
                isExtent = extent_geom.contains(feature.geometry())
                if not isExtent:
                    f_rect = feature.geometry().asGeometryCollection()[0].asQPolygonF().boundingRect()
                    f_lower = f_rect.topLeft()
                    f_upper = f_rect.bottomRight()
                    self.check_msg_building_2_6.append(
                        "gml_id:" +  str(gml_id) + " [ boundedBy is (" + str(x1) + "," + str(y1) + "), (" + str(x2) + "," + str(y2) + ")," 
                         + "but feature is (" + str(f_lower.x()) + "," + str(f_lower.y()) + "), (" + str(f_upper.x()) + "," + str(f_upper.y()) + "). ]")

                # 地物同士の重さなりのため格納（LOD1なので、２次元で確認）
                collection = feature.geometry().asGeometryCollection()
                feature_geom_array.append(QgsGeometry.fromQPolygonF(collection[len(collection)-1].asQPolygonF()))
                feature_geom_id_array.append(gml_id)

        #【2.16】地物同士の重さなり
        for i in range(0, len(feature_geom_array)-1):
            for j in range(i+1, len(feature_geom_array)-1):
                isOver = feature_geom_array[i].contains(feature_geom_array[j]) # 壁がくっついていてもNG
                if isOver:
                    self.check_msg_building_2_16.append(str(feature_geom_id_array[i]) + "," + str(feature_geom_id_array[j]))
                    break


    def result_out_put(self, gml_file_path):
        '''
        /***************************************************************************
        gmlファイル単位の検査結果出力処理

        @param gml_file_path     : gmlファイルパス
        ***************************************************************************/
        '''

        url_temp = gml_file_path.split("/")
        org_fileName = url_temp[len(url_temp)-1]
        fileName = org_fileName.replace(".gml", ".xlsx")

        # ファイル単位のチェックフラグ
        file_check_flg = True

        ######################################################
        # Excel操作開始
        try:
            # 検査結果テンプレートを開く
            wb = self.excel_app.Workbooks.Open(self.template_xlsx)
            self.excel_app.Visible = False
            wb.Activate

            #初期シート選択
            ws = wb.Worksheets(1)

            # セルにファイル名を記載
            ws.Range("C1").Value = "対象ファイル：" + org_fileName

            # 検査結果配列とセルの位置マッピング
            check_arrays = [
                [self.check_msg_building_1_1, "3"],
                [self.check_msg_building_1_2, "4"],
                [self.check_msg_building_2_1, "9"],
                [self.check_msg_building_2_2, "10"],
                [self.check_msg_building_2_3, "11"],
                [self.check_msg_building_2_4, "12"],
                [self.check_msg_building_2_5, "13"],
                [self.check_msg_building_2_6, "14"],
                [self.check_msg_building_2_12_1, "20"],
                [self.check_msg_building_2_12_5, "24"],
                [self.check_msg_building_2_16, "28"],
            ]

            ######################################################
            # 検査結果を該当セルに書き込み
            for ck in check_arrays:
                if not ck[0] :
                    ws.Range("G" + ck[1]).Value = "合格"
                else :
                    if file_check_flg: # １度FalseになったらそのままFalseを保持
                        file_check_flg = False

                    ws.Range("G" + ck[1]).Value = "不合格"
                    ws.Range("H" + ck[1]).Value = str(ck[0]).replace("[","").replace("]","")  # 詳細

            ######################################################
            # 保存実行
            out_fileName_path = os.path.join(self.out_dir, "合格", fileName)
            wb.SaveCopyAs(out_fileName_path)

            # 閉じる(保存しているので警告はないはずだが、念のため警告なしにする)
            self.excel_app.DisplayAlerts = False
            wb.Close(SaveChanges=False)
            self.excel_app.DisplayAlerts = True

        except Exception as e:
            QgsMessageLog.logMessage("出力に失敗しました。", e)
            # 処理終了
            self.excel_app.Quit()
            raise

        ######################################################
        # NG発生時の処理
        if file_check_flg == False:
            # 処理共通のチェックフラグをNGにする
            self.dir_check_flg = False

            # NGフォルダに移動
            NG_dir = os.path.join(self.out_dir, "不合格")
            if not os.path.exists(NG_dir):
                os.makedirs(NG_dir)
            shutil.move(out_fileName_path, NG_dir)


    def checkCodeOnCodeList(self, path, code):
        '''
        /***************************************************************************
        コードリストに値が存在するかを確認する
        コードリストをXML解析するが、解析結果は保存して、同一コードリストの場合に参照
        
        @param path     : コードリストのファイルパス（gmlファイルからの相対パス）
        @param code     : 値
        ***************************************************************************/
        '''

        if not os.path.isfile(path):
            print("checkCodeOnCodeList : codelists is not exists.", path)
            return False

        tree = None
        # 一度解析していたらそれを参照
        if path in self.parsed_codelists:
            tree =self.parsed_codelists[path]
        else:
            # XML解析
            try:
                # 読み込みと解析
                tree = ET.parse(path) 

                # selfの解析済み配列に格納
                self.parsed_codelists[path] = tree
            except:
                print("checkCodeOnCodeList : codelists is not parsed.", path)
                return False
        
        # スキーマにそって該当タグを参照して、値を確認
        root = tree.getroot()
        for child in root:
            if child.tag.endswith("dictionaryEntry"):
                for definition in child:
                    for element in definition:
                        if element.tag.endswith("name"):
                            if code == element.text:
                                # 該当する値がある（合格）
                                return True

        
        # 該当する値がなかった（不合格）
        return False


    def cancel(self):
        '''
        /***************************************************************************
        検査および出力処理をキャンセル
        ***************************************************************************/
        '''
        # self.wait()
        # ret = QMessageBox.question(None, "CityGML検査", "検査途中ですが、キャンセルしてよろしいですか？", QMessageBox.Yes, QMessageBox.No)
        # if ret == QMessageBox.Yes:
        #     self.was_canceled = True
        self.was_canceled = True


    def wasCanceled(self):
        '''
        /***************************************************************************
        本インスタンスのwas_canceledを取得
        ***************************************************************************/
        '''
        return self.was_canceled


    def dirCheckFlg(self):
        '''
        /***************************************************************************
        本インスタンスのdirCheckFlgを取得
        ***************************************************************************/
        '''
        return self.dir_check_flg


############################################################
# ユーティリティ
############################################################

def getPosListArray(element):
    '''
    /***************************************************************************
    要素から点リストの配列を取得

    @param element : 要素
    ***************************************************************************/
    '''
    for solid in element:
        for exterior in solid:
            for compositeSurface in exterior:
                ring_array = []
                for surfaceMember in compositeSurface:
                    for polygon in surfaceMember:
                        for exterior2 in polygon:
                            for linearRing in exterior2:
                                for posList in linearRing:
                                    ring_array.append(posList.text.split(" ")) # 配列の配列
                    
                return ring_array


def getPoints(array):
    '''
    /***************************************************************************
    数値配列から平面のみの点配列を取得

    @param array : 配列
    ***************************************************************************/
    '''

    temp_point_array = []
    points = []
    for point in array:
        temp_point_array.append(float(point))

        if len(temp_point_array) == 3:
            # 平面のみ（Z軸は無視）
            points.append(QPointF(temp_point_array[0], temp_point_array[1])) 
            temp_point_array = []

    return points


def getCodeSpaces(elements):
    '''
    /***************************************************************************
    属性名がcodeSpaceであるタグを取得

    @param elements : 要素
    ***************************************************************************/
    '''
    cs_array = []
    for element1 in elements:
        if 'codeSpace' in element1.attrib:
            cs_array.append([element1.attrib['codeSpace'], element1.text])

        if len(element1) == 0:
            continue
        else:
            ret_array = getCodeSpaces(element1)
            for ret in ret_array:
                cs_array.append(ret)

    return cs_array



