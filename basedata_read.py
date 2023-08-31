# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BasedataRead  基盤地図からCityGMLファイルを生成 する抽象クラス                                
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""

import warnings

from qgis.core import *

class BasedataRead:
    def __init__(self):
        self.dir_path = ""
        self.field_list = []
        
        self.required_field_name = ""
        self.height_feature_field_name = ""
        self.height_csv_field_name = ""
        self.linkkey_csv_field_name = ""

        self.meshcode_field_name = ""

        self.use_csv = False

        # 属性設定情報
        self.attribute_setting = []

    def setDirectory(self, dir_path: str):
        """ディレクトリ指定"""
        self.dir_path = dir_path

    def directory(self):
        """ディレクトリ取得"""
        return self.dir_path

    def fieldList(self) -> list:
        """フィールド情報取得"""
        return self.field_list

    def filePaths(self) -> list:
        """ファイルパス初期化"""
        return []

    def setRequiredField(self, field_name: str):
        """地物データの必須項目のフィールド名設定"""
        self.required_field_name = field_name

    def requiredField(self) -> str:
        """地物データの必須項目のフィールド名取得"""
        return self.required_field_name

    def setHeightFeatureField(self, field_name: str):
        """地物データの高さフィールド名設定"""
        self.height_feature_field_name = field_name
    
    def heightFeatureField(self) -> str:
        """地物データの高さフィールド名取得"""
        return self.height_feature_field_name

    def setHeightCsvField(self, field_name: str):
        """CSVの高さフィールド名設定"""
        self.height_csv_field_name = field_name
    
    def heightCsvField(self) -> str:
        """CSVの高さフィールド名取得"""
        return self.height_csv_field_name
 
    def setLinkkeyCsvField(self, field_name: str):
        """CSVのリンクキーフィールド名設定"""
        self.linkkey_csv_field_name = field_name
    
    def linkkeyCsvField(self) -> str:
        """CSVのリンクキーフィールド名取得"""
        return self.linkkey_csv_field_name

    def setUseCsv(self, use: bool):
        """True:地物データの高さを使用する False:外部CSVの属性使用する"""
        self.use_csv = use

    def useCsv(self) -> bool:
        """True:地物データの高さを使用する False:外部CSVの属性使用する"""
        return self.use_csv

    def featureFields(self) -> QgsFields:
        """
        地物データのフィールドを設定して返却する
        """

        # フィールドの設定
        fields = QgsFields()
        # 必須項目
        if len(self.required_field_name) > 0:
            fields.append(QgsField(self.required_field_name))

        if self.use_csv:
            # リンクキー
            fields.append(QgsField(self.linkkey_csv_field_name))
            # 高さ
            fields.append(QgsField(self.height_csv_field_name))
        else:
            # 高さ
            fields.append(QgsField(self.height_feature_field_name))

        # 属性設定で設定したフィールド
        for attribute_field in self.attribute_setting:
            fields.append(QgsField(attribute_field))

        # メッシュコード
        fields.append(QgsField(self.meshcodeFieldName()))

        print("######fields", fields.names())
        return fields

    def setAttributes(self, attribute_setting: list):
        """
        属性情報を設定する
        """
        self.attribute_setting = list(attribute_setting)

    def meshcodeFieldName(self):
        """
        メッシュコードを生成する
        """
        if len(self.meshcode_field_name) == 0:
            branch = 0
            fix = False
            while fix == False:
                meshcode_field_name = "meshcode" if branch == 0 else f"meshcode_{branch}"

                if self.required_field_name == meshcode_field_name:
                    branch += 1
                    continue

                if self.use_csv:
                    if self.height_csv_field_name == meshcode_field_name:
                        branch += 1
                        continue

                    if self.linkkey_csv_field_name == meshcode_field_name:
                        branch += 1
                        continue
                
                else:
                    if self.height_feature_field_name == meshcode_field_name:
                        branch += 1
                        continue
                
                if meshcode_field_name in self.attribute_setting:
                    branch += 1
                    continue

                # ここまで来たら重複した名前がないので決定する
                self.meshcode_field_name = meshcode_field_name
                fix = True
                
        return self.meshcode_field_name

    def createMemoryLayerForDst(self, type=QgsWkbTypes.Polygon) -> QgsVectorLayer:
        """
        設定したフィールド情報のメモリレイヤを生成する
        """
        return QgsMemoryProviderUtils.createMemoryLayer("memory_layer", self.featureFields(), type, QgsCoordinateReferenceSystem("EPSG:6668"))

    def createVectorLayerForSrc(self, file_path, layer_name):
        """
        指定したファイルのベクタレイヤを生成する
        """
        return QgsVectorLayer(file_path, layer_name, "ogr")

    def compensateCRS(self, src_crs, dst_crs):
        """
        座標参照系を変換する
        """

        if QgsProject.instance().transformContext().hasTransform(src_crs, dst_crs) == False:
            transform_context = QgsCoordinateTransformContext(QgsProject.instance().transformContext())

            sourceTransformId = -1
            destinationTransformId = -1

            warnings.simplefilter("ignore")
            transformations = QgsDatumTransform.datumTransformations(src_crs, dst_crs)
            warnings.resetwarnings()
            if len(transformations) > 0:
                sourceTransformId = transformations[0].sourceTransformId
                destinationTransformId = transformations[0].destinationTransformId

            warnings.simplefilter("ignore")
            transform_context.addSourceDestinationDatumTransform(src_crs, dst_crs, sourceTransformId, destinationTransformId)
            warnings.resetwarnings()

            operations = [op for op in QgsDatumTransform.operations(src_crs, dst_crs) if op.isAvailable]
            if len(operations) > 0:
                transform_context.addCoordinateOperation(src_crs, dst_crs, operations[0].proj)

            QgsProject.instance().setTransformContext(transform_context)