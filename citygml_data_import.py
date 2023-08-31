import os
import glob

from qgis.PyQt.QtCore import QObject
from qgis.core import QgsProject, QgsVectorLayer, Qgis

from PyQt5.QtWidgets import QFileDialog,QMessageBox

class CityGMLDataImport(QObject):

    def __init__(self, iface):
        super().__init__()
        # self.layers = []
        self.iface = iface

    # 検査処理デバッグ用メソッド
    '''
    /***************************************************************************
      openFolder  読み込み元のフォルダを指定
     ***************************************************************************/
    '''
    def openFolder(self, parent):

        # ディレクトリ選択ダイアログ
        if parent.citygml_export_folder_name.text():
            currentPath = parent.citygml_export_folder_name.text()
        else:
            currentPath = os.path.expanduser('~') + '/Desktop'

        dir = QFileDialog.getExistingDirectory(None, 'CityGML：フォルダ選択', currentPath, QFileDialog.ShowDirsOnly)

        if not dir:
            return 

        # 画面に表示し、出力ボタンを活性
        parent.citygml_export_folder_name.setText(dir)
        parent.button_citygml_export.setEnabled(True)


    '''
    /***************************************************************************
      generatVectorLayer  指定したフォルダ配下の全gmlファイルに対し、VectorLayerを生成
                          gmlファイルの内容も関与するため、読み込み時点でチェックする
     ***************************************************************************/
    '''
    def generatVectorLayer(self, parent):

        parent.selectedFiles = []

        # 選択したフォルダ配下のgmlファイル名を取得
        files = glob.glob(parent.citygml_export_folder_name.text() + "/*.gml")

        if not files:
            QMessageBox.warning(None, "CityGML検査", "該当するCityGMLファイルがありませんでした。他のフォルダを選択ください。", QMessageBox.Yes)
            return False

        for filePath in files:
            url = filePath.replace('\\','/')
            _temp = url.split("/")
            fileName = _temp[len(_temp)-1]

            # VectorLayerを生成
            layer = QgsVectorLayer(url, fileName, "ogr") # memoryとしては作成できない

            if layer.isValid():
                # レイヤ登録（チェックは後処理）
                QgsProject.instance().addMapLayer(layer)

            # 検査のために１ファイルごとの情報として保持

            cnt = 0
            if fileName in parent.gml_feature_count:
                cnt = parent.gml_feature_count[fileName]

            parent.selectedFiles.append([url, layer, cnt])

        # 検査結果出力ボタンを活性
        parent.button_citygml_check_output.setEnabled(True)

        self.iface.messageBar().pushMessage("CityGML検査", "gmlファイルを正常に読み込みました。", Qgis.Info)

        return True