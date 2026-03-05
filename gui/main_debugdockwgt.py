# -*- coding: utf-8 -*-
'''
Created on 2011/11/8

@author: ksj
'''


#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
import os
import sys

from ui.ui_DebugDockWgt import Ui_DebugDockWgt

class DebugDockWgt(QDockWidget, Ui_DebugDockWgt):
    def __init__(self, parent = None):
        super(DebugDockWgt,self).__init__(parent)
        
        self.ui = Ui_DebugDockWgt()
        self.ui.setupUi(self)
        
        #debug connect
        self.ui.lineEdit_debug.returnPressed.connect( self._debugword )
         
        
        
    def _debugword(self):
        
        script = str(self.ui.lineEdit_debug.text())
        
        
        from io import StringIO
        a = StringIO()
        b = StringIO()
        temp_out = sys.stdout
        sys.stdout = a
        
        try:
            #get mainwindow
            exec(script)
#            if script.rfind(".") == -1:
#                pass
#            else:
#                self.ui.lineEdit_debug.setText(script[:script.rfind(".")+1])
        except :
            print(sys.exc_type.__name__, ":", sys.exc_info()[1],)
#            self.ui.lineEdit_debug.clear()
        finally:
            self.ui.plainTextEdit_debug.appendPlainText(">>>" +a.getvalue())
            sys.stdout = temp_out
            
    
