# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Exporter  エクスポート処理
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""
import os
import math

from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal
from qgis.core import *

from .basedata_read import BasedataRead
from .citygml_serializer import CityGMLSerializer

class Exporter(QThread):

    progress = pyqtSignal(int)

    def __init__(self, generator: BasedataRead, feature_type: str, dest_dir_path: str, parent: QObject = None):
        super().__init__(parent)

        self.generator = generator
        self.serializer = CityGMLSerializer(generator, feature_type, dest_dir_path)
        self.feature_type = feature_type

        self.was_canceled = False
        self.dst_vlayer = None
        # self.filesInfoList = []

    def cancel(self):
        """
        キャンセル
        """
        print(f"出力中止")
        self.was_canceled = True

    def wasCanceled(self):
        """
        キャンセル後
        """
        return self.was_canceled

    def dstVLayer(self, thread):
        """
        レイヤをスレッドに移動
        """
        dst_vlayer = self.dst_vlayer.clone()
        dst_vlayer.moveToThread(thread)
        return dst_vlayer

    # def filesInfo(self):
    #     """
    #     ファイル情報取得
    #     """
    #     # 本メソッドはスレッドなので、呼び出し元にconnectで渡す
    #     return self.filesInfoList 

    def run(self):
        """
        エクスポート処理開始
        """

        print(f"エクスポート処理開始")

        # 準備
        file_paths = self.generator.filePaths()
        if len(file_paths) == 0:
            return

        total = len(file_paths) * 2 + 2
        step = 0

        src_vlayers = []

        while self.was_canceled == False:
            output_type = QgsWkbTypes.Unknown

            errors = []
            is_multi = False
            for file_path in file_paths:

                if self.was_canceled:
                    break

                # ファイル名からレイヤー名を作成する
                file_name = os.path.basename(file_path)
                layer_name = os.path.splitext(file_name)[0]

                # ベクタレイヤーを作成する
                src_vlayer = self.generator.createVectorLayerForSrc(file_path, layer_name)

                # ジオメトリのチェック
                if output_type not in (QgsWkbTypes.Unknown, QgsWkbTypes.NoGeometry):
                    if QgsWkbTypes.geometryType(output_type) != QgsWkbTypes.geometryType(src_vlayer.wkbType()):
                        # レイヤーのジオメトリが他と違う場合はこのレイヤーをスキップする
                        errors.append(f"{src_vlayer.name()}はジオメトリタイプが{QgsWkbTypes.geometryDisplayString(src_vlayer.wkbType())}と異なるため除外しました。")
                        continue

                    # zとmは考慮しない

                    if QgsWkbTypes.isMultiType( src_vlayer.wkbType() ) and not QgsWkbTypes.isMultiType( output_type ):
                        output_type = QgsWkbTypes.multiType( output_type )
                        is_multi = True
                        QgsMessageLog.logMessage(f"Found a layer({src_vlayer.name()}) with multiparts, upgrading output type to {QgsWkbTypes.displayString( output_type )}")
                    
                else:
                    output_type = src_vlayer.wkbType()

                src_vlayers.append(src_vlayer)
                step += 1
                progress_value = round(step * 100 / total)
                self.progress.emit(progress_value)
                print(f"ベクタレイヤー作成{src_vlayer.name()}")

            if self.was_canceled:
                break

            # 属性設定数
            attribute_fields = self.generator.featureFields()
            attribute_count = attribute_fields.count()

            # メモリレイヤーを作成
            self.dst_vlayer = self.generator.createMemoryLayerForDst(output_type)
            if self.dst_vlayer is None:
                return None
            dst_crs = self.dst_vlayer.crs()

            self.dst_vlayer.startEditing()
            self.dst_vlayer.setCustomProperty("skipMemoryLayersCheck", 1)

            # メッシュコードフィールド
            meshcode_field_name = self.generator.meshcodeFieldName()
            meshcode_field_index = self.dst_vlayer.fields().indexFromName(meshcode_field_name)

            # メッシュコード別にCityGMLを出力したいので重複を許可しないset型
            meshcode_set = set()

            for src_vlayer in src_vlayers:

                if self.was_canceled:
                    break

                transformer = None
                if src_vlayer.crs() != self.dst_vlayer.crs():
                    transformer = QgsCoordinateTransform(src_vlayer.crs(), dst_crs, QgsProject.instance().transformContext())
                    self.generator.compensateCRS(src_vlayer.crs(), dst_crs)

                # 元のレイヤーから必要な属性のインデックスを抜き出す
                attr_indexes = {}
                src_data_provider = src_vlayer.dataProvider()
                for dst_index in range(0, attribute_count):
                    field_name = attribute_fields.at(dst_index).name()
                    src_index = src_data_provider.fieldNameIndex(field_name)
                    if src_index >= 0:
                        attr_indexes[field_name] = {"src": src_index, "dst": dst_index}

                for src_feature in src_vlayer.getFeatures():
                    dst_feature = QgsFeature(attribute_fields)
                    if src_feature.hasGeometry():
                        # ジオメトリをコピー
                        g = QgsGeometry(src_feature.geometry())
                        if transformer is not None:
                            g.transform(transformer)
                        if is_multi and not g.isMultipart():
                            g.convertToMultiType()
                        dst_feature.setGeometry(g)

                        # ジオメトリはEPSG:6668に変換済みなので緯度経度になっているはず
                        lon = None
                        lat = None
                        if src_vlayer.geometryType() in (QgsWkbTypes.PolygonGeometry, QgsWkbTypes.LineGeometry):
                            centroid = g.centroid().asPoint()
                            lon = centroid.x()
                            lat = centroid.y()
                        elif src_vlayer.geometryType() == QgsWkbTypes.PointGeometry:
                            point = g.asPoint()
                            lon = point.x()
                            lat = point.y()
                        
                        if lon != None and lat != None:
                            # メッシュコードフィールドに値を設定する
                            __meshcode = self.make_meshcode(lat, lon)
                            dst_feature.setAttribute(meshcode_field_index, __meshcode)
                            meshcode_set.add(__meshcode)

                    # 元の地物から必要な属性の値を取得する
                    # dst_feature.initAttributes(attribute_count)
                    for field_name, indexes in attr_indexes.items():
                        value = src_feature.attribute(indexes["src"])
                        dst_feature.setAttribute(indexes["dst"], value)

                    # メモリレイヤーに設定する
                    self.dst_vlayer.addFeature(dst_feature)

                step += 1
                progress_value = round(step * 100 / total)
                self.progress.emit(progress_value)
                print(f"地物出力{src_vlayer.name()}")

            for vlayer in src_vlayers:
                vlayer.deleteLater()

            if self.was_canceled:
                if self.dst_vlayer is not None:
                    self.dst_vlayer.rollBack()
            else:
                if self.dst_vlayer is not None:
                    self.dst_vlayer.commitChanges()

            # メッシュコード別にCityGML出力処理を行う
            for meshcode in meshcode_set:
                # メッシュコードフィルター
                expression = QgsExpression(f"\"{meshcode_field_name}\"='{meshcode}'")

                # ドキュメント作成開始
                feature_itr = self.dst_vlayer.getFeatures(QgsFeatureRequest(expression))

                boundedBy = self.getBound(self.dst_vlayer.getFeatures(QgsFeatureRequest(expression)))

                file_name = self.serializer.exec(feature_itr, boundedBy, meshcode)

                if file_name is None:
                    errors.append(self.serializer.lastError())
                    break

                # # ファイル名と地物数を格納
                # cnt = 0
                # feature_itr_cnt = self.dst_vlayer.getFeatures(QgsFeatureRequest(expression))
                # for feature in feature_itr_cnt:
                #     cnt =+ 1

                # print("file_name", file_name)
                # print("cnt", cnt)
                    
                # self.filesInfoList.append([file_name, cnt])

            break

        print(f"エクスポート処理終了")
            
    def make_meshcode(self, lat, lon):
        """
        メッシュコード作成

        @param lat:緯度
        @param lon:経度
        """

        #[1次メッシュコード上2桁]
        #緯度×60分÷40分＝p　余り　a
        p,a = divmod(lat*60,40)
        #[1次メッシュコード下2桁]
        #経度ー100度＝u　余り　f
        u = lon - 100
        f = math.modf(lon)[0]
        #[2次メッシュコード上1桁]
        #a÷5分＝q　余り　b
        q,b = divmod(a,5)
        #[2次メッシュコード下1桁]
        #f×60分÷7分30秒＝v　余り　g
        v,g = divmod(f*60,7.5)
        #[3次メッシュコード上1桁]
        #b×60秒÷30秒＝r　余り　c
        r,c = divmod(b*60,30)
        #[3次メッシュコード下1桁]
        #g×60秒÷45秒＝w　余り　h
        w,h = divmod(g*60,45) 
        #基準地域メッシュコード
        #pu　qv　rw
        return(str(int(p)) 
            + str(int(u)) 
            + str(int(q)) 
            + str(int(v))
            + str(int(r)) 
            + str(int(w))) 
    
    
    def getBound(self, feature_itr: QgsFeatureIterator):
        x_min = None
        y_min = None
        x_max = None
        y_max = None
        for feature in feature_itr:
            rect = feature.geometry().boundingBox()
            xMax = rect.xMaximum()
            xMin = rect.xMinimum()
            yMax = rect.yMaximum()
            yMin = rect.yMinimum()

            if x_max == None:
                x_max = xMax
                x_min = xMin
                y_max = yMax
                y_min = yMin

            if xMax > x_max:
                x_max = xMax
            if xMin < x_min:
                x_min = xMin
            if yMax > y_max:
                y_max = yMax
            if yMin < y_min:
                y_min = yMin

        # return [str(x_min), str(y_min), str(x_max), str(y_max)]
        return [str(y_min), str(x_min), str(y_max), str(x_max)]    

