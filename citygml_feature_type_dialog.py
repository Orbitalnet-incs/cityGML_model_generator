"""
地物設定ダイアログ
"""
import os

from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import Qt

# UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'citygml_feature_type_dialog_base.ui'))


class CityGMLFeatureTypeDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent, flags = Qt.WindowFlags()):
        super(CityGMLFeatureTypeDialog, self).__init__(parent, flags)

        self.setupUi(self)

        self.feature_type_selected = ""

        self.feature_type.addItem("bldg:Building")
        self.feature_type.addItem("luse:LandUse")
        self.feature_type.addItem("tran:Road")
        
        # 他のタイプは開発中

        self.feature_type.currentTextChanged.connect(self.changeFileName)
        self.button_box.accepted.connect(self.selectFeatureType)
        self.button_box.rejected.connect(self.reject)

        self.changeFileName(self.feature_type.currentText())

    def changeFileName(self, feature_type: str):
        if feature_type == "":
            self.file_name.clear()
            return

        # ファイル名を更新
        parts = feature_type.split(":")
        self.file_name.setText(f"[meshcode]_{parts[0]}_6697.gml")

    def featureType(self) -> str:
        return self.feature_type_selected

    def setFeatureType(self, text: str):
        index = self.feature_type.findText(text)
        if index < 0:
            return
        self.feature_type.setCurrentIndex(index)
    
    def selectFeatureType(self):
        self.feature_type_selected = self.feature_type.currentText()
        self.accept()