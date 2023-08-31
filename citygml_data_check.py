"""
/***************************************************************************
 CityGMLDataCheck  CityGMLモデル検査
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/
"""
import os
import datetime

from PyQt5.QtWidgets import QProgressDialog, QWidget, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import Qt, QObject
from qgis.core import Qgis,QgsMessageLog

from .citygml_data_check_process import CityGMLDataCheckProcess

class CityGMLDataCheck(QObject):

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.__progress_dialog = None

    def gmlCheck_resultOutput(self, selectedFiles, parent_widget: QWidget):
        '''
        /***************************************************************************
        検査と結果出力
        ***************************************************************************/
        '''

        ###########################################################
        # 検査時の初期処理
        if not self.init_check() :
            # 出力先未選択のため終了
            return False

        self.parent = parent_widget

        ###########################################################
        # 経過ダイアログの生成
        self.__progress_dialog = QProgressDialog("検査中(割合はメッシュ数で算出)...", "キャンセル", 0, 100, parent_widget)
        self.__progress_dialog.setWindowTitle("CityGML検査")
        self.__progress_dialog.setWindowModality(Qt.WindowModal)

        ###########################################################
        # スレッドインスタンスの生成と単独のコネクション設定
        self.process = CityGMLDataCheckProcess(selectedFiles, self.out_dir)
        self.process.started.connect(self.__progress_dialog.show)
        self.process.finished.connect(self.completed)

        ###########################################################
        # 経過ダイアログとスレッドのコネクション設定
        self.__progress_dialog.canceled.connect(self.process.cancel) # キャンセル時
        self.process.progress_signal.connect(self.__progress_dialog.setValue) # 経過数値設定
        
        ###########################################################
        # Start (@see run)
        self.process.start()

        return True


    def init_check(self):
        '''
        /***************************************************************************
        検査時の初期処理
        ***************************************************************************/
        '''

        ###########################################################
        # 出力するディレクトリ選択ダイアログ
        _out_dir = None
        while not _out_dir:
            _out_dir = QFileDialog.getExistingDirectory(None, 'CityGML：検査出力フォルダ選択', os.path.expanduser('~') + '/Desktop', QFileDialog.ShowDirsOnly)        

            # 誤ったディレクトリ未選択を防止
            # 出力処理と連動しているので、検査のみの実施がないため
            if not _out_dir:
                ret = QMessageBox.question(None, "CityGML出力", "検査を実施せず終了してよろしいでしょうか？", QMessageBox.Yes, QMessageBox.No)
                if ret == QMessageBox.Yes:
                    # 終了
                    QMessageBox.warning(None, "CityGML検査結果", "検査を実施せず終了しました。", QMessageBox.Yes)
                    return False
            else:
                break

        # さらに日時分のディレクトリを作成
        dt_now = datetime.datetime.now()
        self.out_dir = _out_dir + '/検査結果_' + dt_now.strftime('%Y%m%d_%H%M')

        try:
            if os.path.isdir(self.out_dir) :
                # もし、同一ディレクトリがあれば、秒を付与
                self.out_dir = self.out_dir + dt_now.strftime('%S')

            os.makedirs(self.out_dir)
            os.makedirs(self.out_dir + "/合格")
        except Exception as e:
            self.iface.messageBar().pushMessage("検査結果", "フォルダ作成時にエラーが発生しました。", Qgis.Warning)
            QgsMessageLog.logMessage("フォルダ作成時にエラーが発生しました。", e)
            return False

        return True


    def completed(self):
        '''
        /***************************************************************************
        検査終了後の処理
        ***************************************************************************/
        '''

        ################################################################
        canceled = self.process.wasCanceled() # キャンセルだったか判定
        is_pass = self.process.dirCheckFlg()  # 合否の判定

        ################################################################
        # 終了の諸処理
        self.__progress_dialog.hide()
        self.process.stopped = True
        self.process.wait() # 念のための停止記述

        ################################################################
        # 処理結果のメッセージ出力
        ################################################################
        if not canceled:
            if is_pass:
                QMessageBox.information(None, "CityGML検査結果", "【合格】\r\n検査結果は[" + self.out_dir + "]\r\nに出力しました。", QMessageBox.Yes)
            else:
                QMessageBox.warning(None, "CityGML検査結果", "【不合格】\r\n検査結果を[" + self.out_dir + "]\r\nに出力しました。\r\n不合格事項の詳細はログファイルを参照ください。", QMessageBox.Yes)

            # 本プラグインダイアログも閉じる
            self.parent.close()

        else:
            # キャンセルであるが、出力したものは削除しない
            QMessageBox.information(None, "CityGML検査結果", "キャンセルしました。\r\n途中の検査結果は[" + self.out_dir + "]\r\nに出力しました。", QMessageBox.Yes)

        ################################################################
        # 終了の諸処理2
        self.__progress_dialog = None
        self.process = None


