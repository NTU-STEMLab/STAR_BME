from qgis.PyQt.QtCore import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import pyqtSignal

class TimeBarSlider(QSlider):
    canDrawNow = pyqtSignal()
    def __init__(self, parent = None):
        QSlider.__init__(self, parent)
    def mouseReleaseEvent( self, ev ):
        QSlider.mouseReleaseEvent(self,ev)