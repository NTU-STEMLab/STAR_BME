# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_OptionDlg.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_OptionDlg(object):
    def setupUi(self, OptionDlg):
        OptionDlg.setObjectName(_fromUtf8("OptionDlg"))
        OptionDlg.resize(400, 74)
        self.verticalLayout = QtWidgets.QVBoxLayout(OptionDlg)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtWidgets.QLabel(OptionDlg)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.comboBox_detrend = QtWidgets.QComboBox(OptionDlg)
        self.comboBox_detrend.setObjectName(_fromUtf8("comboBox_detrend"))
        self.horizontalLayout.addWidget(self.comboBox_detrend)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.pushButton_default = QtWidgets.QPushButton(OptionDlg)
        self.pushButton_default.setObjectName(_fromUtf8("pushButton_default"))
        self.horizontalLayout_2.addWidget(self.pushButton_default)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.pushButton_ok = QtWidgets.QPushButton(OptionDlg)
        self.pushButton_ok.setObjectName(_fromUtf8("pushButton_ok"))
        self.horizontalLayout_2.addWidget(self.pushButton_ok)
        self.pushButton_cancel = QtWidgets.QPushButton(OptionDlg)
        self.pushButton_cancel.setObjectName(_fromUtf8("pushButton_cancel"))
        self.horizontalLayout_2.addWidget(self.pushButton_cancel)
        self.pushButton_apply = QtWidgets.QPushButton(OptionDlg)
        self.pushButton_apply.setObjectName(_fromUtf8("pushButton_apply"))
        self.horizontalLayout_2.addWidget(self.pushButton_apply)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(OptionDlg)
        QtCore.QMetaObject.connectSlotsByName(OptionDlg)

    def retranslateUi(self, OptionDlg):
        OptionDlg.setWindowTitle(_translate("OptionDlg", "STAR-BME Configure", None))
        self.label.setText(_translate("OptionDlg", "Default Detrend Method", None))
        self.pushButton_default.setText(_translate("OptionDlg", "Set it to default", None))
        self.pushButton_ok.setText(_translate("OptionDlg", "Ok", None))
        self.pushButton_cancel.setText(_translate("OptionDlg", "Cancel", None))
        self.pushButton_apply.setText(_translate("OptionDlg", "Apply", None))

