# -*- coding: utf-8 -*-
'''
Created on 2011/11/8

@author: ksj
'''


#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *

import os
import sys
import numpy

from matplotlib.mlab import griddata
from matplotlib.pyplot import cm
from ui.ui_MplDockWgt import Ui_MplDockWgt

class MplDockWgt(QDockWidget, Ui_MplDockWgt):
    def __init__(self, parent = None):
        super(MplDockWgt,self).__init__(parent)
        
        self.ui = Ui_MplDockWgt()
        self.ui.setupUi(self)
        
        self.ui.horizontalSlider.setTracking(False)

        #Get bmeobj from mainwindow
        self.bmeobj = parent.bmeobj
        
        #
        self.ui.comboBox_stationtime.currentIndexChanged[int].connect( self.updateUiThenDrawIfAuto )
        self.ui.comboBox_data.currentIndexChanged[int].connect( self.updateUiThenDrawIfAuto )
        self.ui.horizontalSlider.valueChanged[int].connect( self.drawIfAuto )
        self.ui.horizontalSlider.sliderMoved[int].connect( self.updateLabel )
        self.ui.pushButton.clicked.connect( self.draw )
        self.ui.checkBox.toggled[bool].connect( self.drawAuto )
        self.ui.checkBox.toggled[bool].connect( self.ui.pushButton.setDisabled )
               
    def initializeUi(self):
        self.ui.comboBox_data.clear()
        if self.bmeobj.hard_data.hasData():
            self.ui.comboBox_data.addItem("HardData")
        if self.bmeobj.soft_data.hasData():
            self.ui.comboBox_data.addItem("SoftData")
        self.updateUi()
        self.draw()
        
    def updateUi(self):
        self.updateSliderBar()
        self.updateLabel()
        
    def updateSliderBar(self):
        if self.useHardOrSoft() == "harddata":
            hdataobj = self.bmeobj.hard_data
            if self.atStationOrTime() == "at station":
                self.ui.horizontalSlider.setRange(0, hdataobj.station_count - 1)
                self.ui.horizontalSlider.setValue(0)
            elif self.atStationOrTime() == "at time":
                self.ui.horizontalSlider.setRange(0, hdataobj.time_count - 1)
                self.ui.horizontalSlider.setValue(0)
        elif self.useHardOrSoft() == "softdata":
            sdataobj = self.bmeobj.soft_data
            if self.atStationOrTime() == "at station":
                self.ui.horizontalSlider.setRange(0, sdataobj.station_count - 1)
                self.ui.horizontalSlider.setValue(0)
            elif self.atStationOrTime() == "at time":
                self.ui.horizontalSlider.setRange(0, sdataobj.time_count - 1)
                self.ui.horizontalSlider.setValue(0)
        
    def updateUiThenDrawIfAuto(self):
        self.updateUi()
        self.drawIfAuto(0)
    
    def drawAuto(self,flag):
        if flag:
            self.draw()
            
    def draw(self):
        if self.useHardOrSoft() == "harddata":
            data_obj = self.bmeobj.hard_data
        elif self.useHardOrSoft() == "softdata":
            data_obj = self.bmeobj.soft_data   
        if self.atStationOrTime() == "at station":
            station_index = self.ui.horizontalSlider.value()
            time_index = None
        elif self.atStationOrTime() == "at time":
            station_index = None
            time_index = self.ui.horizontalSlider.value()
        self._draw(data_obj, station_index, time_index) 
    
    def _draw(self, data_obj, station_index = None, time_index = None):
        s, t, z = (data_obj.s_grid, data_obj.t_grid, data_obj.z_grid)
        if station_index != None: #draw at station (not include 0)
            try:
                figure_title = station_name[station_index]
            except NameError:
                figure_title = "S = " + str(s[station_index])
            axes_x = t[0]
            axes_y = z[station_index,:]
            xmin = data_obj.station_t_min
            xmax = data_obj.station_t_max
            ymin = data_obj.z_min_without_nan
            ymax = data_obj.z_max_without_nan
            boundary = ((xmin, xmax),(ymin, ymax))
            self.plotStation(figure_title, axes_x, axes_y, boundary)
        elif time_index != None: #draw at time (not include 0)
            figure_title = "T = " + str(t[0][time_index])
            axes_x = s[:,0]
            axes_y = s[:,1]
            axes_z = z[:,time_index]
            xmin = data_obj.time_x_min
            xmax = data_obj.time_x_max
            ymin = data_obj.time_y_min
            ymax = data_obj.time_y_max
            zmin = data_obj.z_min_without_nan
            zmax = data_obj.z_max_without_nan
            boundary = ((xmin, xmax),(ymin, ymax),(zmin,zmax))
            self.plotTime(figure_title, axes_x, axes_y, axes_z, boundary)
            
    def drawIfAuto(self,value):
        self.updateLabel(value)
        if self.isAutoDraw():
            self.draw()
    
    def updateLabel(self, value = None):
        if value == None: #not include 0
            value = self.ui.horizontalSlider.value()
        else:
            pass
        if self.useHardOrSoft() == "harddata":
            s = self.bmeobj.hard_data.s_grid
            t = self.bmeobj.hard_data.t_grid
            if self.atStationOrTime() == "at station":
                self.ui.label.setText(str("S = " + str(s[value])))
            elif self.atStationOrTime() == "at time":
                self.ui.label.setText(str("T = " + str(t[0][value])))
        elif self.useHardOrSoft() == "softdata":
            s = self.bmeobj.soft_data.s_grid
            t = self.bmeobj.soft_data.t_grid
            if self.atStationOrTime() == "at station":
                self.ui.label.setText(str("S = " + str(s[value])))
            elif self.atStationOrTime() == "at time":
                self.ui.label.setText(str("T = " + str(t[0][value])))
        
    def atStationOrTime(self):
        return str(self.ui.comboBox_stationtime.currentText()).lower() # "at station", "at time"
    
    def useHardOrSoft(self):
        return str(self.ui.comboBox_data.currentText()).lower() # "harddata", "softdata"
    
    def isAutoDraw(self):
        return self.ui.checkBox.isChecked()
    
    def plotStation(self, title, x, y, boundary):
        x_without_nan = x[numpy.where(~numpy.isnan(y))]
        y_without_nan = y[numpy.where(~numpy.isnan(y))]
        self.ui.mplWidget.canvas.fig.clear()
        self.ui.mplWidget.canvas.ax = self.ui.mplWidget.canvas.fig.add_subplot(111)
        self.ui.mplWidget.canvas.ax.set_title(title)
        self.ui.mplWidget.canvas.ax.plot(x_without_nan, y_without_nan,
                                         "bo-")
        self.ui.mplWidget.canvas.ax.set_aspect("normal")
        self.ui.mplWidget.canvas.ax.set_xlim(boundary[0][0],
                                             boundary[0][1])
        self.ui.mplWidget.canvas.ax.set_ylim(boundary[1][0],
                                             boundary[1][1])
        self.ui.mplWidget.canvas.draw()
        
    def plotTime(self,title, x, y, z, boundary):
        x_without_nan = x[numpy.where(~numpy.isnan(z))]
        y_without_nan = y[numpy.where(~numpy.isnan(z))]
        z_without_nan = z[numpy.where(~numpy.isnan(z))]
        self.ui.mplWidget.canvas.fig.clear()
        self.ui.mplWidget.canvas.ax = self.ui.mplWidget.canvas.fig.add_subplot(111)

        self.ui.mplWidget.canvas.ax.set_title(title)
        self.ui.mplWidget.canvas.ax.set_aspect("equal")
        
########################
#        xi = numpy.linspace(boundary[0][0],
#                            boundary[0][1],200)
#        yi = numpy.linspace(boundary[1][0],
#                            boundary[1][1],200)
#        zi = griddata(x_without_nan,y_without_nan,z_without_nan,
#                      xi,yi,interp='nn')
#                      
#        self.ui.mplWidget.canvas.ax.contour(xi,yi,zi,15,linewidths=0.5,colors='k',
#                                            levels = numpy.linspace(boundary[2][0],
#                                                                    boundary[2][1],15))
#        
#        cts = self.ui.mplWidget.canvas.ax.contourf(xi,yi,zi,15,cmap=cm.jet,
#                                                   levels = numpy.linspace(boundary[2][0],
#                                                                           boundary[2][1],15))
        sctr = self.ui.mplWidget.canvas.ax.scatter(x_without_nan, y_without_nan,
                                                   c = z_without_nan, cmap = "jet",
                                                   s=40, vmin = boundary[2][0], vmax = boundary[2][1])
        self.ui.mplWidget.canvas.fig.colorbar(sctr)
#
##########################        
#        self.ui.mplWidget.canvas.ax.tricontour(x_without_nan,
#                                               y_without_nan,
#                                               z_without_nan, 10)
                  
        self.ui.mplWidget.canvas.ax.set_xlim(boundary[0][0],
                                             boundary[0][1])
        self.ui.mplWidget.canvas.ax.set_ylim(boundary[1][0],
                                             boundary[1][1])
#        cts = self.ui.mplWidget.canvas.ax.tricontourf(x_without_nan,
#                                                      y_without_nan,
#                                                      z_without_nan,
#                                                      levels = numpy.linspace(boundary[2][0],
#                                                                              boundary[2][1],8)
#                                                      )
    #    self.ui.mplWidget.canvas.fig.colorbar(cts)
        
        #deprecated 
        #self.ui.mplWidget.canvas.ax.plot(x_without_nan,y_without_nan,'bo')
        
        #show label
#        for xi,yi in zip(x_without_nan, y_without_nan):
#            self.ui.mplWidget.canvas.ax.text(xi,yi,str(xi)+","+str(yi),
#                                             fontsize=12,
#                                             ha = "left", va = "top")
        self.ui.mplWidget.canvas.draw()

