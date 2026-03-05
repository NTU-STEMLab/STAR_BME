# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_SelectShpDlg.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_SelectShpDlg(object):
    def setupUi(self, SelectShpDlg):
        SelectShpDlg.setObjectName(_fromUtf8("SelectShpDlg"))
        SelectShpDlg.resize(365, 102)
        self.verticalLayout = QtWidgets.QVBoxLayout(SelectShpDlg)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label = QtWidgets.QLabel(SelectShpDlg)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.lineEdit_filename = QtWidgets.QLineEdit(SelectShpDlg)
        self.lineEdit_filename.setReadOnly(True)
        self.lineEdit_filename.setObjectName(_fromUtf8("lineEdit_filename"))
        self.horizontalLayout_3.addWidget(self.lineEdit_filename)
        self.pushButton_browse = QtWidgets.QPushButton(SelectShpDlg)
        self.pushButton_browse.setObjectName(_fromUtf8("pushButton_browse"))
        self.horizontalLayout_3.addWidget(self.pushButton_browse)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_37 = QtWidgets.QLabel(SelectShpDlg)
        self.label_37.setObjectName(_fromUtf8("label_37"))
        self.horizontalLayout.addWidget(self.label_37)
        self.lineEdit_tmin = QtWidgets.QLineEdit(SelectShpDlg)
        self.lineEdit_tmin.setText(_fromUtf8(""))
        self.lineEdit_tmin.setObjectName(_fromUtf8("lineEdit_tmin"))
        self.horizontalLayout.addWidget(self.lineEdit_tmin)
        self.label_38 = QtWidgets.QLabel(SelectShpDlg)
        self.label_38.setObjectName(_fromUtf8("label_38"))
        self.horizontalLayout.addWidget(self.label_38)
        self.lineEdit_tmax = QtWidgets.QLineEdit(SelectShpDlg)
        self.lineEdit_tmax.setText(_fromUtf8(""))
        self.lineEdit_tmax.setObjectName(_fromUtf8("lineEdit_tmax"))
        self.horizontalLayout.addWidget(self.lineEdit_tmax)
        self.label_42 = QtWidgets.QLabel(SelectShpDlg)
        self.label_42.setObjectName(_fromUtf8("label_42"))
        self.horizontalLayout.addWidget(self.label_42)
        self.lineEdit_tn = QtWidgets.QLineEdit(SelectShpDlg)
        self.lineEdit_tn.setText(_fromUtf8(""))
        self.lineEdit_tn.setObjectName(_fromUtf8("lineEdit_tn"))
        self.horizontalLayout.addWidget(self.lineEdit_tn)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.pushButton_ok = QtWidgets.QPushButton(SelectShpDlg)
        self.pushButton_ok.setObjectName(_fromUtf8("pushButton_ok"))
        self.horizontalLayout_2.addWidget(self.pushButton_ok)
        self.pushButton_cancel = QtWidgets.QPushButton(SelectShpDlg)
        self.pushButton_cancel.setObjectName(_fromUtf8("pushButton_cancel"))
        self.horizontalLayout_2.addWidget(self.pushButton_cancel)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(SelectShpDlg)
        QtCore.QMetaObject.connectSlotsByName(SelectShpDlg)

    def retranslateUi(self, SelectShpDlg):
        SelectShpDlg.setWindowTitle(_translate("SelectShpDlg", "Select Shape File Dialog", None))
        self.label.setText(_translate("SelectShpDlg", "File Name", None))
        self.pushButton_browse.setText(_translate("SelectShpDlg", "Browse...", None))
        self.label_37.setText(_translate("SelectShpDlg", "Tmin:", None))
        self.label_38.setText(_translate("SelectShpDlg", "Tmax:", None))
        self.label_42.setText(_translate("SelectShpDlg", "Tn:", None))
        self.pushButton_ok.setText(_translate("SelectShpDlg", "Ok", None))
        self.pushButton_cancel.setText(_translate("SelectShpDlg", "Cancel", None))

