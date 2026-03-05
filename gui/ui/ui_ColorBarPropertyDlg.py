# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_ColorBarPropertyDlg.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_ColorBarPropertyDlg(object):
    def setupUi(self, ColorBarPropertyDlg):
        ColorBarPropertyDlg.setObjectName(_fromUtf8("ColorBarPropertyDlg"))
        ColorBarPropertyDlg.resize(299, 127)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(ColorBarPropertyDlg)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.label = QtWidgets.QLabel(ColorBarPropertyDlg)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout_2.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(ColorBarPropertyDlg)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(ColorBarPropertyDlg)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.verticalLayout_2.addWidget(self.label_3)
        self.horizontalLayout_3.addLayout(self.verticalLayout_2)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.comboBox_cmap = QtWidgets.QComboBox(ColorBarPropertyDlg)
        self.comboBox_cmap.setObjectName(_fromUtf8("comboBox_cmap"))
        self.horizontalLayout_2.addWidget(self.comboBox_cmap)
        self.checkBox_inverse = QtWidgets.QCheckBox(ColorBarPropertyDlg)
        self.checkBox_inverse.setObjectName(_fromUtf8("checkBox_inverse"))
        self.horizontalLayout_2.addWidget(self.checkBox_inverse)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.lineEdit_minvalue = QtWidgets.QLineEdit(ColorBarPropertyDlg)
        self.lineEdit_minvalue.setObjectName(_fromUtf8("lineEdit_minvalue"))
        self.verticalLayout.addWidget(self.lineEdit_minvalue)
        self.lineEdit_maxvalue = QtWidgets.QLineEdit(ColorBarPropertyDlg)
        self.lineEdit_maxvalue.setObjectName(_fromUtf8("lineEdit_maxvalue"))
        self.verticalLayout.addWidget(self.lineEdit_maxvalue)
        self.horizontalLayout_3.addLayout(self.verticalLayout)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pushButton_apply = QtWidgets.QPushButton(ColorBarPropertyDlg)
        self.pushButton_apply.setObjectName(_fromUtf8("pushButton_apply"))
        self.horizontalLayout.addWidget(self.pushButton_apply)
        self.pushButton_close = QtWidgets.QPushButton(ColorBarPropertyDlg)
        self.pushButton_close.setObjectName(_fromUtf8("pushButton_close"))
        self.horizontalLayout.addWidget(self.pushButton_close)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.retranslateUi(ColorBarPropertyDlg)
        QtCore.QMetaObject.connectSlotsByName(ColorBarPropertyDlg)

    def retranslateUi(self, ColorBarPropertyDlg):
        ColorBarPropertyDlg.setWindowTitle(_translate("ColorBarPropertyDlg", "ColorBar - Property", None))
        self.label.setText(_translate("ColorBarPropertyDlg", "color map", None))
        self.label_2.setText(_translate("ColorBarPropertyDlg", "minimum value", None))
        self.label_3.setText(_translate("ColorBarPropertyDlg", "maximum value", None))
        self.checkBox_inverse.setText(_translate("ColorBarPropertyDlg", "inverse", None))
        self.pushButton_apply.setText(_translate("ColorBarPropertyDlg", "Apply", None))
        self.pushButton_close.setText(_translate("ColorBarPropertyDlg", "Close", None))

