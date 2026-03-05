# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_ColorBarDockWgt.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_ColorBarDockWgt(object):
    def setupUi(self, ColorBarDockWgt):
        ColorBarDockWgt.setObjectName(_fromUtf8("ColorBarDockWgt"))
        ColorBarDockWgt.resize(94, 444)
        ColorBarDockWgt.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.widget = MplWidgetWithoutNavTools(self.dockWidgetContents)
        self.widget.setObjectName(_fromUtf8("widget"))
        self.verticalLayout.addWidget(self.widget)
        self.pushButton_changeproperty = QtWidgets.QPushButton(self.dockWidgetContents)
        self.pushButton_changeproperty.setObjectName(_fromUtf8("pushButton_changeproperty"))
        self.verticalLayout.addWidget(self.pushButton_changeproperty)
        ColorBarDockWgt.setWidget(self.dockWidgetContents)

        self.retranslateUi(ColorBarDockWgt)
        QtCore.QMetaObject.connectSlotsByName(ColorBarDockWgt)

    def retranslateUi(self, ColorBarDockWgt):
        ColorBarDockWgt.setWindowTitle(_translate("ColorBarDockWgt", "ColorBar", None))
        self.pushButton_changeproperty.setText(_translate("ColorBarDockWgt", "Change\n"
" Property...", None))

from .mplwidget import MplWidgetWithoutNavTools
