# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtWidgets import *

from .ui_TaskWgt import Ui_TaskWgt

class TaskWgt(QWidget, Ui_TaskWgt):
    def __init__(self, parent = None):
        super(TaskWgt,self).__init__(parent)
        self.ui = Ui_TaskWgt()
        self.ui.setupUi(self)
