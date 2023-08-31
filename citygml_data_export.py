"""
/***************************************************************************
 CityGMLDataExport  CityGMLモデル出力
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import os
import glob

from qgis.PyQt.QtCore import QObject, pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QProgressDialog, QWidget, QDialog

from qgis.core import *
from qgis.gui import QgisInterface

from .basedata_read_basemap import BasedataReadFromBasemap, extractBasemapFiles
from .basedata_read_shape import BasedataReadFromShape
from .attribute_setting_csv import AttributeSettingByCsv
from .basedata_export import Exporter
from .citygml_feature_type_dialog import CityGMLFeatureTypeDialog

class CityGMLDataExport(QObject):

    # exportCompleted = pyqtSignal(bool, list)
    exportCompleted = pyqtSignal(bool)

    def __init__(self, iface: QgisInterface, parent: QObject = None):
        super().__init__(parent)
        self.__iface = iface
        self.__generator = None # 生成元データ
        self.__exporter = None
        self.__progress_dialog = None

        self.__attribute_setting_by_csv = None
        self.__last_error = ""

    def getFieldsOfData(self, dir_path: str):
        '''
        /***************************************************************************
        属性情報取得
        ***************************************************************************/
        '''

        self.__last_error = ""
        self.__generator = None

        # 指定のディレクトリが存在するか確認
        if os.path.exists(dir_path) == False:
            self.__last_error = f"存在しないディレクトリです"
            return []

        # Shapeファイルか基盤地図ファイルの存在確認
        cwd = os.path.abspath(os.getcwd())
        os.chdir(dir_path)
        shape_files = glob.glob("*.shp")
        os.chdir(cwd)
        
        if len(shape_files) > 0:
            # ShapeファイルからCityGMLを生成
            self.__generator = BasedataReadFromShape()
        else:
            # Shapeファイルがないので基盤地図情報ファイルを探す
            basemap_files = extractBasemapFiles(dir_path)
            if len(basemap_files) == 0:
                print("Shapeファイルおよび基盤地図情報データファイルが存在しません")
                # 基盤地図情報ファイルなし
                self.__last_error = f"Shapeファイルおよび基盤地図情報データファイルが存在しません"
                self.__generator = None
                return []

            # 基盤地図ファイルからCityGMLを生成
            self.__generator = BasedataReadFromBasemap()
            
        self.__generator.setDirectory(dir_path)

        # 生成クラスからフィールドリストを取得
        return self.__generator.fieldList()


    def getFieldsOfCsv(self, file_path: str):
        '''
        /***************************************************************************
        CSVの属性情報取得
        ***************************************************************************/
        '''
        if self.__attribute_setting_by_csv is None:
            self.__attribute_setting_by_csv = AttributeSettingByCsv()

        if self.__attribute_setting_by_csv.setFieldList(file_path) == True:
            return self.__attribute_setting_by_csv.fieldList()


    def lastError(self):
        return self.__last_error

    def export_manager(self, dest_dir_path: str, prepare_items: dict, parent_widget: QWidget = None) -> bool:
        '''
        /***************************************************************************
        CityGML出力処理
        ***************************************************************************/
        '''
        self.__last_error = ""

        # ベースデータが設定されていないときはエラー
        if self.__generator is None:
            return False

        # 出力先のディレクトリが存在するか確認
        if len(dest_dir_path) == 0:
            self.__last_error = "出力先ディレクトリが設定されていません。"
            return False
        if os.path.exists(dest_dir_path) == False:
            self.__last_error = "出力先ディレクトリは存在しません。"
            return False
        if os.path.isdir(dest_dir_path) == False:
            self.__last_error = "出力先に指定されているのはディレクトリではありません。"
            return False
        existing_files = [f for f in os.listdir(dest_dir_path) if os.path.isfile(os.path.join(dest_dir_path, f))]
        if len(existing_files) > 0:
            self.__last_error = "出力先に既にファイルがあります。"
            return False

        # 地物のタイプ
        dlg = CityGMLFeatureTypeDialog(self.__iface.mainWindow())
        if dlg.exec() == QDialog.Rejected:
            return False

        feature_type = dlg.featureType()

        # 設定項目の取得
        # 必須項目
        self.__generator.setRequiredField(prepare_items.get("required_field", "gml_id"))

        # 地物データの属性を使用する or 外部CSVの属性使用する
        self.__generator.setUseCsv(False)
        # 地物データの高さフィールド
        self.__generator.setHeightFeatureField(prepare_items.get("measured_height"))

        # if "height_feature" in prepare_items:
        #     self.__generator.setUseCsv(False)
        #     # 地物データの高さフィールド
        #     self.__generator.setHeightFeatureField(prepare_items.get("height_feature"))
        # else:
        #     self.__generator.setUseCsv(True)

        #     # 外部CSVの高さフィールド
        #     self.__generator.setHeightCsvField(prepare_items.get("height_csv"))
        #     # 外部CSVのリンクキー
        #     self.__generator.setLinkkeyCsvField(prepare_items.get("linkkey_csv"))

        # 属性設定
            #TODO:開発中 属性設定画面で設定する
        # attribute_setting = ["color", "type"]
        # self.__generator.setAttributes(attribute_setting)

        # 処理中ダイアログ表示
        self.__progress_dialog = QProgressDialog("CityGML出力中...","キャンセル",0, 100, parent_widget)
        self.__progress_dialog.setWindowModality(Qt.WindowModal)

        # エクスポート処理
        self.__exporter = Exporter(self.__generator, feature_type, dest_dir_path)

        # connect
        self.__progress_dialog.canceled.connect(self.__exporter.cancel)
        self.__exporter.progress.connect(self.__progress_dialog.setValue)
        self.__exporter.started.connect(self.__progress_dialog.show)
        self.__exporter.finished.connect(self.generateCompleted)

        # エクスポート開始
        self.__exporter.start()

    def generateCompleted(self):
        '''
        /***************************************************************************
        CityGML出力終了
        ***************************************************************************/
        '''

        canceled = False

        if self.__progress_dialog is not None:
            self.__progress_dialog.hide()

        if self.__exporter is not None:
            self.__exporter.wait()

            vlayer = self.__exporter.dstVLayer(self.thread())
            QgsProject.instance().addMapLayer(vlayer)

            canceled = self.__exporter.wasCanceled()
            # filesInfo = self.__exporter.filesInfo()

        self.__progress_dialog = None
        self.__exporter = None

        # 生成終了のシグナルを発生する
        # キャンセルフラグを渡す
        self.exportCompleted.emit(canceled)

        # CityGMLのメモリレイヤを削除
        _layers = QgsProject.instance().mapLayersByName("memory_layer")
        for memorylayer in _layers:
            QgsProject.instance().removeMapLayer(memorylayer.id())
        
        self.__iface.mapCanvas().refresh()