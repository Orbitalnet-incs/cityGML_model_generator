import os

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.core import *

from .basedata_read import BasedataRead

class BasedataReadFromShape(BasedataRead):
    finished = pyqtSignal

    def setDirectory(self, dir_path: str):
        super().setDirectory(dir_path)

        self.field_list.clear()

        if len(self.dir_path) == 0:
            return False

        files = self.filePaths()
        if len(files) == 0:
            return False

        file_path = files[0]

        vlayer = self.createVectorLayerForSrc(file_path, "layer for shape")

        # フィールド名のリストを作成
        self.field_list = list(vlayer.fields().names())

        # レイヤーは登録せず破棄する
        vlayer.deleteLater()

        return True

    def filePaths(self):
        return [os.path.join(self.dir_path, f) for f in os.listdir(self.dir_path) if os.path.isfile(os.path.join(self.dir_path, f)) and f.endswith(r".shp")]
