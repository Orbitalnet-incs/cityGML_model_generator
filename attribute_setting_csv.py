"""
/***************************************************************************
 AttributeSettingByCsv  CSVからの属性情報読み込み
                             -------------------
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""
import csv
from chardet.universaldetector import UniversalDetector

from qgis.PyQt.QtCore import QFileInfo

class AttributeSettingByCsv:
    def __init__(self):

        # 属性リスト
        self.__field_list = []


    def setFieldList(self, file_path: str) -> bool:
        '''
        /***************************************************************************
        属性リスト設定
        ***************************************************************************/
        '''
        
        # 指定のファイルが存在するか確認
        file_info = QFileInfo(file_path)
        if file_info.exists() == False:
            return False
        
        # 拡張子がCSVでなければエラー
        if file_info.suffix().lower() != "csv":
            return False

        self.__field_list.clear()

        # 文字コードを判別する
        encoding = self.__detectCharCode(file_path)
        
        # フィールド名を取得
        # 1行目にタイトル行があることを前提とする
        with open(file_path, "r", encoding=encoding) as csvfile:
            for row in csv.reader(csvfile):
                # 1行だけ読み込む
                if len(row) > 0:
                    self.__field_list = list(row)
                break

        return len(self.__field_list) > 0
    

    def __detectCharCode(self, file_path):
        '''
        /***************************************************************************
        ファイル内容の文字コード判別

        @param file_path:対象ファイルのパス
        ***************************************************************************/
        '''

        encoding = ""
        detector = UniversalDetector()
        with open(file_path, "rb") as f:
            detector.reset()
            for line in f.readlines():
                detector.feed(line)
                if detector.done:
                    break
            detector.close()
            encoding = detector.result['encoding']

        return encoding


    def fieldList(self):
        '''
        /***************************************************************************
        属性リストを取得
        ***************************************************************************/
        '''        
        return self.__field_list
