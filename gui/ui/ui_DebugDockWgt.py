# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_DebugDockWgt.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_DebugDockWgt(object):
    def setupUi(self, DebugDockWgt):
        DebugDockWgt.setObjectName(_fromUtf8("DebugDockWgt"))
        DebugDockWgt.resize(400, 300)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.plainTextEdit_debug = QtWidgets.QPlainTextEdit(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plainTextEdit_debug.sizePolicy().hasHeightForWidth())
        self.plainTextEdit_debug.setSizePolicy(sizePolicy)
        self.plainTextEdit_debug.setMinimumSize(QtCore.QSize(200, 100))
        self.plainTextEdit_debug.setReadOnly(True)
        self.plainTextEdit_debug.setObjectName(_fromUtf8("plainTextEdit_debug"))
        self.verticalLayout.addWidget(self.plainTextEdit_debug)
        self.label = QtWidgets.QLabel(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setKerning(True)
        self.label.setFont(font)
        self.label.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.label.setFrameShadow(QtWidgets.QFrame.Plain)
        self.label.setLineWidth(0)
        self.label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.lineEdit_debug = QtWidgets.QLineEdit(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_debug.sizePolicy().hasHeightForWidth())
        self.lineEdit_debug.setSizePolicy(sizePolicy)
        self.lineEdit_debug.setMinimumSize(QtCore.QSize(0, 0))
        self.lineEdit_debug.setObjectName(_fromUtf8("lineEdit_debug"))
        self.verticalLayout.addWidget(self.lineEdit_debug)
        DebugDockWgt.setWidget(self.dockWidgetContents)

        self.retranslateUi(DebugDockWgt)
        QtCore.QMetaObject.connectSlotsByName(DebugDockWgt)

    def retranslateUi(self, DebugDockWgt):
        DebugDockWgt.setWindowTitle(_translate("DebugDockWgt", "Debug Window", None))
        self.label.setText(_translate("DebugDockWgt", "Specify a BMEobj attribute name (for example: hard_data.x ):", None))
        self.lineEdit_debug.setText(_translate("DebugDockWgt", "self.parent().bmeobj.", None))

