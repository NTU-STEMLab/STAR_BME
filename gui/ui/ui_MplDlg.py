# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_MplDlg.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_MplDlg(object):
    def setupUi(self, MplDlg):
        MplDlg.setObjectName(_fromUtf8("MplDlg"))
        MplDlg.resize(777, 444)
        self.verticalLayout = QtWidgets.QVBoxLayout(MplDlg)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtWidgets.QLabel(MplDlg)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.comboBox = QtWidgets.QComboBox(MplDlg)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.horizontalLayout.addWidget(self.comboBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.mplWidget = MplWidget(MplDlg)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mplWidget.sizePolicy().hasHeightForWidth())
        self.mplWidget.setSizePolicy(sizePolicy)
        self.mplWidget.setMinimumSize(QtCore.QSize(250, 250))
        self.mplWidget.setObjectName(_fromUtf8("mplWidget"))
        self.verticalLayout.addWidget(self.mplWidget)

        self.retranslateUi(MplDlg)
        QtCore.QMetaObject.connectSlotsByName(MplDlg)

    def retranslateUi(self, MplDlg):
        MplDlg.setWindowTitle(_translate("MplDlg", "Mpl Dialog", None))
        self.label.setText(_translate("MplDlg", "Selected Variable:", None))
        self.comboBox.setItemText(0, _translate("MplDlg", "RMSE", None))
        self.comboBox.setItemText(1, _translate("MplDlg", "Mean", None))
        self.comboBox.setItemText(2, _translate("MplDlg", "Standard deviation", None))
        self.comboBox.setItemText(3, _translate("MplDlg", "25 percentile", None))
        self.comboBox.setItemText(4, _translate("MplDlg", "Median", None))
        self.comboBox.setItemText(5, _translate("MplDlg", "75 percentile", None))
        self.comboBox.setItemText(6, _translate("MplDlg", "Min", None))
        self.comboBox.setItemText(7, _translate("MplDlg", "Max", None))

from .mplwidget import MplWidget
