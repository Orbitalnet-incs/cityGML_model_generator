# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CityGMLModelGeneratorDialog  CityGMLモデル生成ダイアログ
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt

from .attribute_setting_dialog import AttributeSettingDialog
from .citygml_data_export import CityGMLDataExport
from .citygml_data_import import CityGMLDataImport
from .citygml_data_check import CityGMLDataCheck

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'citygml_model_generator_dialog_base.ui'))


class CityGMLModelGeneratorDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None, iface=None):
        """Constructor."""
        super(CityGMLModelGeneratorDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface

        # インポートとチェック
        self.citygml_data_import = CityGMLDataImport(iface)
        self.citygml_data_check = CityGMLDataCheck(iface)

        # CityGML出力
        self.data_export = CityGMLDataExport(iface)
        self.data_export.exportCompleted.connect(self.cityGmlExportDone)
        self.fields_data = []
        self.fields_csv = []

        # CityGML検査結果
        self.selectedFiles = []
        self.gml_feature_count = []

        ######################################################
        # 画面のボタンの処理の指定など
        self.initUI()


    def initUI(self):
        '''
        /***************************************************************************
        画面に関する初期設定
        ***************************************************************************/
        '''

        self.button_citygml_check_output.setVisible(False)

        # connect
        self.button_basedata_folder.clicked.connect(self.getDirectoryBasedata)
        self.basedata_folder_name.textChanged.connect(self.handleFolderTextChanged)
        self.button_basedata_import.clicked.connect(self.readBaseData)
        self.radio_button_feature.clicked.connect(self.handleAttributeChanged)
        self.radio_button_csv.clicked.connect(self.handleAttributeChanged)
        self.button_basedata_folder_3.clicked.connect(self.getCsvFilePath)
        self.button_attribute_import.clicked.connect(self.readCsvData)
        self.button_citygml_export.clicked.connect(self.handleCityGmlExport)
        # self.button_attribute_setting.clicked.connect(self.handleAttributeSetting) # 出力処理が開発中のためコメントアウト
        self.button_citygml_export_folder.clicked.connect(self.handleCityGmlFolderSelect)
        self.button_citygml_check_output.clicked.connect(self.handleCityGmlCheck)

        self.button_close.clicked.connect(lambda:self.close())


    def handleAttributeSetting(self):
        '''
        /***************************************************************************
        属性設定ボタンの操作
        ***************************************************************************/
        '''
        # ダイアログ表示
        AttributeSettingDialog(self).show()


    def handleCityGmlFolderSelect(self):
        '''
        /***************************************************************************
        CityGMLの選択ボタンの操作
        ***************************************************************************/
        '''
        #  ファイル選択およびファイル名取得
        self.citygml_data_import.openFolder(self)


    def handleCityGmlCheck(self):
        '''
        /***************************************************************************
        CityGML検査結果出力の操作
        ***************************************************************************/
        '''

        #  確認のためgmlファイルからVectorLayer再作成
        if not self.citygml_data_import.generatVectorLayer(self):
            print("generatVectorLayer is False")
            return

        # CityGML検査結果出力
        self.citygml_data_check.gmlCheck_resultOutput(self.selectedFiles, self)


    def readBaseData(self):
        '''
        /***************************************************************************
        データ読み込み
        ***************************************************************************/
        '''
        # フォルダ未選択ならエラー
        dir_path = self.basedata_folder_name.text()
        if len(dir_path) == 0:
            return

        QtWidgets.QApplication.instance().setOverrideCursor(Qt.WaitCursor)
        self.fields_data.clear()

        self.combo_feature_attribute_field.clear()
        self.combo_required_fields.clear()

        self.fields_data = self.data_export.getFieldsOfData(dir_path)
        if len(self.fields_data) > 0:
            self.combo_feature_attribute_field.addItem("")
            self.combo_required_fields.addItem("")
            for field_name in self.fields_data:
                self.combo_feature_attribute_field.addItem(field_name)
                self.combo_required_fields.addItem(field_name)
            
            # 必須項目は空白以外の先頭項目を初期選択する
            self.combo_required_fields.setCurrentIndex(1)

        QtWidgets.QApplication.instance().restoreOverrideCursor()

        # ボタン使用可否設定
        self.button_citygml_export.setEnabled(True)


    def readCsvData(self):
        '''
        /***************************************************************************
        CSV読込
        ***************************************************************************/
        '''
        file_path = self.basedata_folder_name_3.text()
        if len(file_path) == 0:
            return

        QtWidgets.QApplication.instance().setOverrideCursor(Qt.WaitCursor)

        self.combo_csv_attribute_field.clear()
        self.combo_csv_link_key.clear()
        
        self.fields_csv = self.data_export.getFieldsOfCsv(file_path)
        if len(self.fields_csv) == 0:
            self.combo_csv_attribute_field.clear()
            self.combo_csv_link_key.clear()
        else:
            for field_name in self.fields_csv:
                self.combo_csv_attribute_field.addItem(field_name)
                self.combo_csv_link_key.addItem(field_name)

        # 手前に表示
        self.raise_()
        self.activateWindow()

        QtWidgets.QApplication.instance().restoreOverrideCursor()
        

    def getDirectoryBasedata(self):
        '''
        /***************************************************************************
        ベースデータが格納されているディレクトリパスを設定
        ***************************************************************************/
        '''
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "ベースデータディレクトリ選択", "", QtWidgets.QFileDialog.DontResolveSymlinks)
        if len(dir_path) == 0:
            return
        
        self.basedata_folder_name.setText(dir_path)
    

    def handleFolderTextChanged(self):
        if self.basedata_folder_name.text() != "":
            # 読み込みボタン有効
            self.button_basedata_import.setEnabled(True)


    def getCsvFilePath(self):
        '''
        /***************************************************************************
        CSVファイルパスを設定
        ***************************************************************************/
        '''
        [file_path, filter_str] = QtWidgets.QFileDialog.getOpenFileName(self, "外部CSV選択", "", "CSVファイル(*.csv)")
        if len(file_path) == 0:
            return

        self.basedata_folder_name_3.setText(file_path)


    def handleAttributeChanged(self):
        '''
        /***************************************************************************
        属性情報読み込みラジオボタンの操作
        ***************************************************************************/
        '''
        if self.radio_button_feature.isChecked():
            # 自身のコンボボックス有効
            self.combo_feature_attribute_field.setEnabled(True)

            # 外部関連
            self.label_attribute_2.setEnabled(False)
            self.button_basedata_folder_3.setEnabled(False)
            self.button_attribute_import.setEnabled(False)
            self.combo_csv_attribute_field.setEnabled(False)

        else:
            # 地物側
            self.combo_feature_attribute_field.setEnabled(False)

            # 有効
            self.label_attribute_2.setEnabled(True)
            self.button_basedata_folder_3.setEnabled(True)
            self.button_attribute_import.setEnabled(True)
            self.combo_csv_attribute_field.setEnabled(True)


    def handleCityGmlExport(self):
        '''
        /***************************************************************************
        CityGML出力ボタンの操作
        ***************************************************************************/
        '''

        # 出力するために必要な情報がそろっているか確認
        prepare_items = {
            # 必須項目
            "required_field" : self.combo_required_fields.currentText()
        }

        if self.radio_button_feature.isChecked():
            # 地物データの属性を使用
            # 高さフィールド名
            prepare_items["measured_height"] = self.combo_feature_attribute_field.currentText()
        else:
            # 外部CSVの属性を使用
            # 高さフィールド
            prepare_items["measured_height"] = self.combo_csv_attribute_field.currentText()
            # # リンクキー
            # prepare_items["linkkey_csv"] = self.combo_csv_link_key.currentText()


        # 属性設定
        export_folder_path = self.citygml_export_folder_name.text()
        
        # エクスポート処理実行
        ret =  self.data_export.export_manager(export_folder_path, prepare_items, self)
        
        if ret == False:
            if len(self.data_export.lastError()) > 0:
                QtWidgets.QMessageBox.warning(self.iface.mainWindow(), "CityGML出力エラー", self.data_export.lastError())


    def cityGmlExportDone(self):
        '''
        /***************************************************************************
        CityGML出力後
        ***************************************************************************/
        '''

        self.basedata_folder_name.clear()
        self.combo_required_fields.clear()
        self.basedata_folder_name_3.clear()
        self.combo_feature_attribute_field.clear()
        self.combo_csv_attribute_field.clear()
        self.combo_csv_link_key.clear()
        self.button_citygml_export.setEnabled(False)

        if self.isVisible():
            message = "CityGML出力は完了しました。"
            QtWidgets.QMessageBox.information(self, self.windowTitle(), message)

        # 検査実行
        #  確認のためgmlファイルからVectorLayer再作成
        if not self.citygml_data_import.generatVectorLayer(self):
            print("generatVectorLayer is False")
            return

        # CityGML検査結果出力
        self.citygml_data_check.gmlCheck_resultOutput(self.selectedFiles, self)

        # 終了後にクリア
        self.citygml_export_folder_name.clear()
