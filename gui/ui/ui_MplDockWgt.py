# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_MplDockWgt.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_MplDockWgt(object):
    def setupUi(self, MplDockWgt):
        MplDockWgt.setObjectName(_fromUtf8("MplDockWgt"))
        MplDockWgt.resize(413, 379)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.mplWidget = MplWidget(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mplWidget.sizePolicy().hasHeightForWidth())
        self.mplWidget.setSizePolicy(sizePolicy)
        self.mplWidget.setMinimumSize(QtCore.QSize(250, 250))
        self.mplWidget.setObjectName(_fromUtf8("mplWidget"))
        self.verticalLayout.addWidget(self.mplWidget)
        self.horizontalSlider = QtWidgets.QSlider(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalSlider.sizePolicy().hasHeightForWidth())
        self.horizontalSlider.setSizePolicy(sizePolicy)
        self.horizontalSlider.setPageStep(1)
        self.horizontalSlider.setProperty("value", 0)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setInvertedAppearance(False)
        self.horizontalSlider.setInvertedControls(False)
        self.horizontalSlider.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.horizontalSlider.setTickInterval(0)
        self.horizontalSlider.setObjectName(_fromUtf8("horizontalSlider"))
        self.verticalLayout.addWidget(self.horizontalSlider)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.comboBox_data = QtWidgets.QComboBox(self.dockWidgetContents)
        self.comboBox_data.setObjectName(_fromUtf8("comboBox_data"))
        self.horizontalLayout_3.addWidget(self.comboBox_data)
        self.comboBox_stationtime = QtWidgets.QComboBox(self.dockWidgetContents)
        self.comboBox_stationtime.setObjectName(_fromUtf8("comboBox_stationtime"))
        self.comboBox_stationtime.addItem(_fromUtf8(""))
        self.comboBox_stationtime.addItem(_fromUtf8(""))
        self.horizontalLayout_3.addWidget(self.comboBox_stationtime)
        self.label = QtWidgets.QLabel(self.dockWidgetContents)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName(_fromUtf8("horizontalLayout_9"))
        self.pushButton = QtWidgets.QPushButton(self.dockWidgetContents)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.horizontalLayout_9.addWidget(self.pushButton)
        self.checkBox = QtWidgets.QCheckBox(self.dockWidgetContents)
        self.checkBox.setObjectName(_fromUtf8("checkBox"))
        self.horizontalLayout_9.addWidget(self.checkBox)
        self.verticalLayout.addLayout(self.horizontalLayout_9)
        MplDockWgt.setWidget(self.dockWidgetContents)

        self.retranslateUi(MplDockWgt)
        QtCore.QMetaObject.connectSlotsByName(MplDockWgt)

    def retranslateUi(self, MplDockWgt):
        MplDockWgt.setWindowTitle(_translate("MplDockWgt", "Data Visualization", None))
        self.comboBox_stationtime.setItemText(0, _translate("MplDockWgt", "At Station", None))
        self.comboBox_stationtime.setItemText(1, _translate("MplDockWgt", "At Time", None))
        self.label.setText(_translate("MplDockWgt", "Name Or Time", None))
        self.pushButton.setText(_translate("MplDockWgt", "Draw", None))
        self.checkBox.setText(_translate("MplDockWgt", "Auto Draw", None))

from .mplwidget import MplWidget
