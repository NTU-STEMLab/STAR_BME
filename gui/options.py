# -*- coding: utf-8 -*-
#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

import os
import sys
import copy

from ui.ui_OptionDlg import Ui_OptionDlg

class OptionDlg(QDialog, Ui_OptionDlg):
  def __init__(self,iface = None,MainDlg = None):
    self.stbme_settings = QSettings("STEMLAB","STBME")
    super(OptionDlg,self).__init__(MainDlg)
    self.iface=iface
    self.MainDlg=MainDlg
    
    self.ui=Ui_OptionDlg()
    self.ui.setupUi(self)

    self.ui.pushButton_apply.setDisabled(True)

    #get Main's param
    for i in range(self.MainDlg.ui.comboBox_detrendmethod.count()):
        self.ui.comboBox_detrend.addItem(self.MainDlg.ui.comboBox_detrendmethod.itemText(i))

    self.ui.comboBox_detrend.setCurrentIndex(self.stbme_settings.value("STBME/DetrendMethod/Index", 0, type = int))

    self.ui.pushButton_ok.clicked.connect(self.ok)
    self.ui.pushButton_cancel.clicked.connect(self.cancel)
    self.ui.pushButton_apply.clicked.connect(self.apply_setting)
    self.ui.pushButton_default.clicked.connect(self.set_default)
    self.ui.comboBox_detrend.currentIndexChanged[int].connect(self._enable_apply)
    
  def ok(self):   
      self.apply_setting()
      self.close()
    
   
  def cancel(self):
      self.close()
        
  def apply_setting(self):
      self.stbme_settings.setValue("STBME/DetrendMethod/Index", self.ui.comboBox_detrend.currentIndex() )

      self.ui.pushButton_apply.setDisabled(True)
      self.ui.pushButton_default.setDisabled(False)

  def _enable_apply(self):
      self.ui.pushButton_apply.setDisabled(False)

  def set_default(self):
      self._set_value()
      self.ui.pushButton_default.setDisabled(True)

  def _set_value(self):
      self.ui.comboBox_detrend.setCurrentIndex(0)
      


