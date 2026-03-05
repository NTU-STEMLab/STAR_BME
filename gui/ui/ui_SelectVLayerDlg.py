# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_SelectVLayerDlg.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_SelectVLayerDlg(object):
    def setupUi(self, SelectVLayerDlg):
        SelectVLayerDlg.setObjectName(_fromUtf8("SelectVLayerDlg"))
        SelectVLayerDlg.setWindowModality(QtCore.Qt.WindowModal)
        SelectVLayerDlg.resize(296, 69)
        self.verticalLayout = QtWidgets.QVBoxLayout(SelectVLayerDlg)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtWidgets.QLabel(SelectVLayerDlg)
        self.label.setMinimumSize(QtCore.QSize(77, 16))
        self.label.setMaximumSize(QtCore.QSize(77, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.comboBox = QtWidgets.QComboBox(SelectVLayerDlg)
        self.comboBox.setMinimumSize(QtCore.QSize(171, 20))
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.horizontalLayout.addWidget(self.comboBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(SelectVLayerDlg)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(SelectVLayerDlg)
        QtCore.QMetaObject.connectSlotsByName(SelectVLayerDlg)

    def retranslateUi(self, SelectVLayerDlg):
        SelectVLayerDlg.setWindowTitle(_translate("SelectVLayerDlg", "Dialog", None))
        self.label.setText(_translate("SelectVLayerDlg", "Select the Layer:", None))

