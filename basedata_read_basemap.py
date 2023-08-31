# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BasedataReadFromBasemap   基盤地図からCityGMLファイルを生成                                 
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import os
import re

from qgis.core import *

from .basedata_read import BasedataRead

class BasedataReadFromBasemap(BasedataRead):
    def __init__(self):
        super().__init__()
        self.__category_name = ""
        self.layer_options = None

    def setDirectory(self, dir_path: str):
        super().setDirectory(dir_path)

        self.field_list.clear()

        if len(self.dir_path) == 0:
            return False

        files = extractBasemapFiles(self.dir_path)
        if len(files) == 0:
            return False

        # 最初に見つかったファイルのクラスを覚えておく
        # ディレクトリが変更されない限りディレクトリ内で別のカテゴリのファイルは読み込まないため
        rx = regExpBaseMap()
        m = rx.match(files[0])

        # タグ名は大文字小文字を区別するのでファイル名から抽出する際に念のため変換する
        self.__category_name = m.group(1)

        file_path = os.path.join(self.dir_path, files[0])

        vlayer = self.createVectorLayerForSrc(file_path, "layer for Basedata")
        
        # フィールド名のリストを作成
        self.field_list = list(vlayer.fields().names())

        # レイヤーは登録せず破棄する
        vlayer.deleteLater()

        return True

    def filePaths(self) -> list:
        # 指定ディレクトリから特定カテゴリのファイルを抽出する
        file_names = extractBasemapFiles(self.dir_path, self.__category_name)
        if len(file_names) == 0:
            return []

        return [os.path.join(self.dir_path, file_name) for file_name in file_names]

    def createVectorLayerForSrc(self, file_path, layer_name):
        self.compensateCRS(QgsCoordinateReferenceSystem("EPSG:6668"), QgsProject.instance().crs())
        return super().createVectorLayerForSrc(file_path, layer_name)


def regExpBaseMap(category = ""):
    alt_category = "(\w+)" if category == "" else category
    pattern = "FG-GML-\d{6}-" + alt_category + "-\d{8}-\d{4,}\.xml"
    return  re.compile(pattern, re.IGNORECASE)

def extractBasemapFiles(dir_path: str, category = "") -> list:
    rx_basemap = regExpBaseMap(category)
    return [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)) and rx_basemap.match(f)]

