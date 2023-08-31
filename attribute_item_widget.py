# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AttributeItemWidget  属性設定アイテムウィジェット
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import os
import math

from PyQt5.QtWidgets import QComboBox, QWidget
from PyQt5 import uic

from qgis.PyQt.QtCore import pyqtSignal

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'attribute_item_base.ui'))


class AttributeItemWidget(QWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    combo_type_name = QComboBox()

    def __init__(self, parent=None):
        """Constructor."""
        super(AttributeItemWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parent = parent

        self.count = 0

        # ボタン制御
        self.removeButton.clicked.connect(self.handleRemove)

        # コンボボックス登録
        print("parent.stringAttribute", parent.stringAttribute)

        for attr in parent.stringAttribute:
            self.comb_basedata_attribute.addItem(attr,attr)


    def handleRemove(self):
        '''
        /***************************************************************************
        解除ボタン操作
        ***************************************************************************/
        '''

        # index減算
        self.parent.index -= 1

        # 削除
        self.deleteLater()


    # def make_meshcode(lat,lon):
    #     '''
    #     /***************************************************************************
    #     メッシュコードを生成する関数
    #     レイヤ作成時もしくは属性設定時に地物属性としてメッシュコードを設定する

    #     @param lat : 緯度
    #     @param lon : 緯度
    #     ***************************************************************************/
    #     '''

    #     #メッシュコード作成
    #     #[1次メッシュコード上2桁]
    #     #緯度×60分÷40分＝p　余り　a
    #     p,a = divmod(lon*60,40)
    #     #[1次メッシュコード下2桁]
    #     #経度ー100度＝u　余り　f
    #     u = lat - 100
    #     f = math.modf(lat)[0]
    #     #[2次メッシュコード上1桁]
    #     #a÷5分＝q　余り　b
    #     q,b = divmod(a,5)
    #     #[2次メッシュコード下1桁]
    #     #f×60分÷7分30秒＝v　余り　g
    #     v,g = divmod(f*60,7.5)
    #     #[3次メッシュコード上1桁]
    #     #b×60秒÷30秒＝r　余り　c
    #     r,c = divmod(b*60,30)
    #     #[3次メッシュコード下1桁]
    #     #g×60秒÷45秒＝w　余り　h
    #     w,h = divmod(g*60,45) 
    #     #基準地域メッシュコード
    #     #pu　qv　rw
    #     return(str(int(p)) 
    #         + str(int(u)) 
    #         + str(int(q)) 
    #         + str(int(v))
    #         + str(int(r)) 
    #         + str(int(w)))

    def closeEvent(self, event):
        '''
        /***************************************************************************
        クローズ処理
        ***************************************************************************/
        '''
        self.closingPlugin.emit()
        event.accept()
