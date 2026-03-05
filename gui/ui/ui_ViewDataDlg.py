# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_ViewDataDlg.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_ViewDataDlg(object):
    def setupUi(self, ViewDataDlg):
        ViewDataDlg.setObjectName(_fromUtf8("ViewDataDlg"))
        ViewDataDlg.resize(777, 444)
        self.verticalLayout = QtWidgets.QVBoxLayout(ViewDataDlg)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.mplWidget = MplWidget(ViewDataDlg)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mplWidget.sizePolicy().hasHeightForWidth())
        self.mplWidget.setSizePolicy(sizePolicy)
        self.mplWidget.setMinimumSize(QtCore.QSize(250, 250))
        self.mplWidget.setObjectName(_fromUtf8("mplWidget"))
        self.verticalLayout.addWidget(self.mplWidget)
        self.checkBox_showtrend = QtWidgets.QCheckBox(ViewDataDlg)
        self.checkBox_showtrend.setObjectName(_fromUtf8("checkBox_showtrend"))
        self.verticalLayout.addWidget(self.checkBox_showtrend)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.checkBox_alldatascale = QtWidgets.QCheckBox(ViewDataDlg)
        self.checkBox_alldatascale.setObjectName(_fromUtf8("checkBox_alldatascale"))
        self.horizontalLayout.addWidget(self.checkBox_alldatascale)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pushButton_close = QtWidgets.QPushButton(ViewDataDlg)
        self.pushButton_close.setObjectName(_fromUtf8("pushButton_close"))
        self.horizontalLayout.addWidget(self.pushButton_close)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(ViewDataDlg)
        QtCore.QMetaObject.connectSlotsByName(ViewDataDlg)

    def retranslateUi(self, ViewDataDlg):
        ViewDataDlg.setWindowTitle(_translate("ViewDataDlg", "View Data Dialog", None))
        self.checkBox_showtrend.setText(_translate("ViewDataDlg", "Show Trend", None))
        self.checkBox_alldatascale.setText(_translate("ViewDataDlg", "Use All Data Scale", None))
        self.pushButton_close.setText(_translate("ViewDataDlg", "Close", None))

from .mplwidget import MplWidget
