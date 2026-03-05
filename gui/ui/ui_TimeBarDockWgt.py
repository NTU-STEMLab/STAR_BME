# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\scku\Desktop\GitRepos\STARBME\starbme_src\gui\ui\ui_TimeBarDockWgt.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets

def _fromUtf8(s):
    return s

def _translate(context, text, disambig):
    return QtCore.QCoreApplication.translate(context, text)

class Ui_TimeBarDockWgt(object):
    def setupUi(self, TimeBarDockWgt):
        TimeBarDockWgt.setObjectName(_fromUtf8("TimeBarDockWgt"))
        TimeBarDockWgt.resize(545, 89)
        TimeBarDockWgt.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea|QtCore.Qt.TopDockWidgetArea)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_time = QtWidgets.QLabel(self.dockWidgetContents)
        self.label_time.setAlignment(QtCore.Qt.AlignCenter)
        self.label_time.setObjectName(_fromUtf8("label_time"))
        self.gridLayout.addWidget(self.label_time, 0, 1, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.radioButton_mean = QtWidgets.QRadioButton(self.dockWidgetContents)
        self.radioButton_mean.setEnabled(False)
        self.radioButton_mean.setChecked(True)
        self.radioButton_mean.setObjectName(_fromUtf8("radioButton_mean"))
        self.buttonGroup = QtWidgets.QButtonGroup(TimeBarDockWgt)
        self.buttonGroup.setObjectName(_fromUtf8("buttonGroup"))
        self.buttonGroup.addButton(self.radioButton_mean)
        self.horizontalLayout.addWidget(self.radioButton_mean)
        self.radioButton_variance = QtWidgets.QRadioButton(self.dockWidgetContents)
        self.radioButton_variance.setEnabled(False)
        self.radioButton_variance.setObjectName(_fromUtf8("radioButton_variance"))
        self.buttonGroup.addButton(self.radioButton_variance)
        self.horizontalLayout.addWidget(self.radioButton_variance)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 3, 1, 1)
        self.pushButton_previous = QtWidgets.QPushButton(self.dockWidgetContents)
        self.pushButton_previous.setMaximumSize(QtCore.QSize(21, 23))
        self.pushButton_previous.setObjectName(_fromUtf8("pushButton_previous"))
        self.gridLayout.addWidget(self.pushButton_previous, 1, 0, 1, 1)
        self.horizontalSlider = TimeBarSlider(self.dockWidgetContents)
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
        self.gridLayout.addWidget(self.horizontalSlider, 1, 1, 1, 1)
        self.pushButton_next = QtWidgets.QPushButton(self.dockWidgetContents)
        self.pushButton_next.setMaximumSize(QtCore.QSize(21, 23))
        self.pushButton_next.setObjectName(_fromUtf8("pushButton_next"))
        self.gridLayout.addWidget(self.pushButton_next, 1, 2, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.pushButton_draw = QtWidgets.QPushButton(self.dockWidgetContents)
        self.pushButton_draw.setObjectName(_fromUtf8("pushButton_draw"))
        self.horizontalLayout_2.addWidget(self.pushButton_draw)
        self.checkBox_autodraw = QtWidgets.QCheckBox(self.dockWidgetContents)
        self.checkBox_autodraw.setObjectName(_fromUtf8("checkBox_autodraw"))
        self.horizontalLayout_2.addWidget(self.checkBox_autodraw)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 3, 1, 1)
        TimeBarDockWgt.setWidget(self.dockWidgetContents)

        self.retranslateUi(TimeBarDockWgt)
        QtCore.QMetaObject.connectSlotsByName(TimeBarDockWgt)

    def retranslateUi(self, TimeBarDockWgt):
        TimeBarDockWgt.setWindowTitle(_translate("TimeBarDockWgt", "TimeBar", None))
        self.label_time.setText(_translate("TimeBarDockWgt", "Time = ", None))
        self.radioButton_mean.setText(_translate("TimeBarDockWgt", "Mean", None))
        self.radioButton_variance.setText(_translate("TimeBarDockWgt", "Variance", None))
        self.pushButton_previous.setText(_translate("TimeBarDockWgt", "<", None))
        self.pushButton_next.setText(_translate("TimeBarDockWgt", ">", None))
        self.pushButton_draw.setText(_translate("TimeBarDockWgt", "Draw", None))
        self.checkBox_autodraw.setText(_translate("TimeBarDockWgt", "Auto Draw", None))

from .mycustomwgt import TimeBarSlider
