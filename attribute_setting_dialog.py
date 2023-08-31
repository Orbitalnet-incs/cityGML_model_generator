# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AttributeSettingDialog  属性設定ダイアログ
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import Qt

from qgis.PyQt.QtCore import QSettings
from .attribute_item_widget import AttributeItemWidget

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'attribute_setting_dialog_base.ui'))


class AttributeSettingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None, iface=None):
        """Constructor."""
        super(AttributeSettingDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parent = parent
        self.index = 0

        self.scrollArea.setWidgetResizable(True)
        self.itemVLayout.setAlignment(Qt.AlignTop)

        # connect設定
        self.button_item_add.clicked.connect(self.handleAddRow)
        self.button_close.clicked.connect(lambda:self.close())


        # configファイルから属性情報を取得する
        locale_path = os.path.join(os.path.dirname(__file__), "config.ini")
        settings = QSettings( locale_path, QSettings.IniFormat )
        settings.setIniCodec("utf-8")
        settings.beginGroup("SECTION1")
        self.stringAttribute = settings.value("stringAttribute")
        settings.endGroup()

        # 取得した属性情報を追加する
        for config_field in self.stringAttribute:
            self.handleAddRow(config_field)
    

    def handleAddRow(self, config_field=None):
        '''
        /***************************************************************************
         行追加
         
         @param :config_field
        ***************************************************************************/
        '''

        print("self.index", self.index)

        self.index += 1

        # 新たなitem
        itemWidget = AttributeItemWidget(self)

        if config_field != None:
            itemWidget.comb_basedata_attribute.setCurrentIndex(-1)
            # itemWidget.comb_basedata_attribute.setEnabled(False)

            # コンボボックスから選択肢を取得
            for index in range(itemWidget.comb_basedata_attribute.count()):
                items = itemWidget.comb_basedata_attribute.itemText(index)
                if items == config_field:
                    itemWidget.comb_basedata_attribute.setCurrentIndex(index)
                    # itemWidget.comb_basedata_attribute.setEnabled(True)
                    break


        # レイアウトに追加
        self.itemVLayout.addWidget(itemWidget)
        self.scrollArea.ensureWidgetVisible(itemWidget)








