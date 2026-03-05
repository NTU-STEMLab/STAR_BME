# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_TaskWgt.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_TaskWgt(object):
    def setupUi(self, TaskWgt):
        TaskWgt.setObjectName(_fromUtf8("TaskWgt"))
        TaskWgt.resize(400, 74)
        self.verticalLayout = QtWidgets.QVBoxLayout(TaskWgt)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtWidgets.QLabel(TaskWgt)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pushButton_setup = QtWidgets.QPushButton(TaskWgt)
        self.pushButton_setup.setObjectName(_fromUtf8("pushButton_setup"))
        self.horizontalLayout.addWidget(self.pushButton_setup)
        self.pushButton_proccess = QtWidgets.QPushButton(TaskWgt)
        self.pushButton_proccess.setObjectName(_fromUtf8("pushButton_proccess"))
        self.horizontalLayout.addWidget(self.pushButton_proccess)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.progressBar = QtWidgets.QProgressBar(TaskWgt)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.horizontalLayout_2.addWidget(self.progressBar)
        self.pushButton_showdetail = QtWidgets.QPushButton(TaskWgt)
        self.pushButton_showdetail.setObjectName(_fromUtf8("pushButton_showdetail"))
        self.horizontalLayout_2.addWidget(self.pushButton_showdetail)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(TaskWgt)
        QtCore.QMetaObject.connectSlotsByName(TaskWgt)

    def retranslateUi(self, TaskWgt):
        TaskWgt.setWindowTitle(_translate("TaskWgt", "Form", None))
        self.label.setText(_translate("TaskWgt", "TextLabel", None))
        self.pushButton_setup.setText(_translate("TaskWgt", "Setup...", None))
        self.pushButton_proccess.setText(_translate("TaskWgt", "Proccess", None))
        self.pushButton_showdetail.setText(_translate("TaskWgt", "Show Detail", None))

