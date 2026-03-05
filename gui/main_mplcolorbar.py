# -*- coding: utf-8 -*-
'''
Created on 2011/11/8

@author: ksj
'''
#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
import os
import sys
import math
import numpy
import matplotlib

from STAR_BME.gui.ui.ui_ColorBarDockWgt import Ui_ColorBarDockWgt
from STAR_BME.gui import stbme2qgis
from STAR_BME.gui import star_math

class ColorBarDockWgt(QDockWidget, Ui_ColorBarDockWgt):
    def __init__(self, parent = None,MainDlg = None):            
        super(ColorBarDockWgt,self).__init__(parent)
        
        self.MainDlg = MainDlg
        self.ui = Ui_ColorBarDockWgt()
        self.ui.setupUi(self)
        
        #rename
        self.canvas = self.ui.widget.canvas
        self.canvas.fig.subplots_adjust( right = 0.5, top = 0.95, bottom = 0.05 )
        # self.time_bar = self.parent.time_bar
        
        self.property_dlg = ColorBarPropertyDlg(self)
        
        self.min = 0
        self.max = 1
        self.cmap = 'jet'
        
        cmap = matplotlib.cm.jet
        self.colorbar = matplotlib.colorbar.ColorbarBase(self.canvas.ax, cmap=cmap)
        
        #NO USE ANYMORE
        #self.canvas.ax2 = self.canvas.ax.twiny()
        #self.canvas.ax.xaxis.set_ticks([0,0.5,1])
        #self.canvas.ax2.xaxis.set_ticks([0,0.5,1])
        
        self.ui.pushButton_changeproperty.clicked.connect(self.changeProperty)

    def update(self,m = 0, M = 1, cmap = None):

        def setRange(m, M):
            self.min = star_math.round_by_significant_feature( m )
            self.max = star_math.round_by_significant_feature( M )

        def setTickLabels():
            self.colorbar.set_ticks( numpy.linspace( 0, 1, 11 ) )
            ticklabels = list(map( star_math.round_by_significant_feature, numpy.linspace( self.min, self.max, 11 ) ))
            self.colorbar.set_ticklabels( list(map( str, ticklabels )) )
            pass
            # self.canvas.ax.xaxis.set_ticks([0,0.5,1])
            # self.canvas.ax2.xaxis.set_ticks([0,0.5,1])       
            # self.canvas.ax.xaxis.set_ticklabels(["",str(round(self.min,2)),""])
            # self.canvas.ax2.xaxis.set_ticklabels(["",str(round(self.max,2)),""])
            # self.canvas.ax.yaxis.set_ticklabels([""])
            
            # loc_y = self.canvas.ax.yaxis.get_ticklocs()
            # label_y = map(
            #               str,numpy.linspace(
            #                                  round(self.min,2),
            #                                  round(self.max,2),
            #                                  len(loc_y)
            #                                 )
            #               )
            # del self.canvas.ax.texts[:]
            # for y,y_name in zip(loc_y[1:-1],label_y[1:-1]):
            #     self.canvas.ax.text(0.5,y,y_name,ha="center", va="center")
        
        def setColorMap(cmap = None):
            if cmap is None:
                pass
            else:
                self.cmap = cmap
                cmap = getattr(matplotlib.cm,cmap)  
                self.colorbar = matplotlib.colorbar.ColorbarBase(self.canvas.ax, cmap=cmap)
                
        setColorMap(cmap)
        setRange(m,M)
        setTickLabels()
        self.canvas.draw()
    
    def changeProperty(self):
        self.property_dlg.update_(self.min,self.max,self.cmap)
        if self.MainDlg.time_bar.ui.buttonGroup.checkedButton() == self.MainDlg.time_bar.ui.radioButton_mean and\
           self.MainDlg.time_bar.current_ratio_button_value != 'mean':
            QMessageBox.critical(self.MainDlg.iface.mainWindow(),"Button Mismatch",
                                 "Please use timebar to draw first or change ratio button to original draw.")
            return
        elif self.MainDlg.time_bar.ui.buttonGroup.checkedButton() == self.MainDlg.time_bar.ui.radioButton_variance and\
           self.MainDlg.time_bar.current_ratio_button_value != 'variance':
            QMessageBox.critical(self.MainDlg.iface.mainWindow(),"Button Mismatch",
                                 "Please use timebar to draw first or change ratio button to original draw.")
            return
        self.property_dlg.show()


from STAR_BME.gui.ui.ui_ColorBarPropertyDlg import Ui_ColorBarPropertyDlg

class ColorBarPropertyDlg(QDialog, Ui_ColorBarPropertyDlg):
    def __init__(self, parent):            
        super(ColorBarPropertyDlg,self).__init__(parent)
        self.ui = Ui_ColorBarPropertyDlg()
        self.ui.setupUi(self)
        
        self.MainDlg = self.parent().MainDlg
        
        #add cmap
        cmap_list = ['jet','hsv','hot','cool',
                     'spring','summer','autumn','winter',
                     'gray','bone','copper','pink']
        self.ui.comboBox_cmap.addItems(cmap_list)
        
        self.ui.pushButton_apply.clicked.connect(self.apply)
        self.ui.pushButton_close.clicked.connect(self.reject)
        
    def apply(self):
        def convert2Float(qstr):
            try:
                res = float( qstr )
                return res
            except ValueError:
                QMessageBox.critical(self,"Convert Error","Connot convert to Float")
                return False   
        
        def changeVectorSymbolsForVairance( lyr ):
            if lyr:      
                #make a symbol
                symbol = QgsSymbolV2.defaultSymbol( QgsWkbTypes.PointGeometry )
                symbol.setColor( QColor( 0,0,0 ) )
                rdr = QgsSingleSymbolRendererV2( symbol )
                lyr.setRenderer( rdr )
                
        if self.ui.checkBox_inverse.isChecked():
            cmap = str(self.ui.comboBox_cmap.currentText())+"_r"
        else:
            cmap = str(self.ui.comboBox_cmap.currentText())
        min_ = convert2Float(self.ui.lineEdit_minvalue.text())
        if min_ is False:
            return
        max_ = convert2Float(self.ui.lineEdit_maxvalue.text())
        if max_ is False:
            return
        
        if max_ <= min_:
            QMessageBox.critical(self,"Value Error","max value should larger that min value")
            return
            
        self.parent().update(min_ , max_, cmap)
        
        if self.MainDlg.time_bar.ui.buttonGroup.checkedButton() == self.MainDlg.time_bar.ui.radioButton_mean:         
            #change layer renderer
            symbol_dict= {'hard':'circle','soft':'equilateral_triangle','estimated':'regular_star'}
            for flag in ['hard','soft']:
                lyr = getattr(self.parent().MainDlg,flag+"_data_layer")
                stbme2qgis.changeVectorLayerRenderer(self.MainDlg.iface, self.MainDlg, lyr,
                                                     symbol_dict[flag], cmap, min_, max_, 4)
            for flag in ['estimated']:
                shp_type = self.MainDlg.estimated_shape_file_type
                
                est_symbol = { QgsWkbTypes.PointGeometry: 'regular_star', QgsWkbTypes.LineGeometry: 'SimpleLine', QgsWkbTypes.PolygonGeometry: 'SimpleFill'}
                lyr = getattr(self.parent().MainDlg,flag+"_data_layer")
                stbme2qgis.changeVectorLayerRenderer(self.MainDlg.iface, self.MainDlg, lyr,
                                                     est_symbol[shp_type], cmap, min_, max_, 4,
                                                    shp_type = shp_type )
            #self.parent().MainDlg.iface.layerTreeView().refreshLayerSymbology( lyr.id() )    
        # NOUSE
        #                if lyr:
        #                    rdr = stbme2qgis.getColorBarRenderer(cmap, symbol_dict[flag], min_, max_, 4)
        #                    rdr.setClassAttribute("Obs Val")
        #                    lyr.setRendererV2(rdr)
        #                    self.parent().MainDlg.iface.legendInterface().refreshLayerSymbology(lyr)
        #                    stbme2qgis.collapseLayer(self.parent().MainDlg.iface, flag.capitalize()+"Data")
        #                    self.parent().MainDlg.iface.mapCanvas().refresh()
                    
            #process Raster
            if self.MainDlg.hasAddRasterLayer():
                rlayer = self.parent().MainDlg.current_mean_layer
                stbme2qgis.setColorRampShader(rlayer, min_, max_, mode = cmap)
        elif self.MainDlg.time_bar.ui.buttonGroup.checkedButton() == self.MainDlg.time_bar.ui.radioButton_variance:
            changeVectorSymbolsForVairance( self.MainDlg.hard_data_layer )
            changeVectorSymbolsForVairance( self.MainDlg.soft_data_layer )
            lyr = self.MainDlg.estimated_data_layer
            shp_type = self.parent().MainDlg.estimated_shape_file_type
            est_symbol = { QgsWkbTypes.PointGeometry: 'regular_star', QgsWkbTypes.LineGeometry: 'SimpleLine', QgsWkbTypes.PolygonGeometry: 'SimpleFill'}
                
            stbme2qgis.changeVectorLayerRenderer(self.MainDlg.iface, self.MainDlg, lyr,
                                                 est_symbol[shp_type], cmap, min_, max_, 4,
                                                 shp_type = shp_type)
            
            #process Raster
            if self.MainDlg.hasAddRasterLayer():
                rlayer = self.parent().MainDlg.current_variance_layer
                stbme2qgis.setColorRampShader(rlayer, min_, max_, mode = cmap)
        
        #force repaint all related layer
        for flag in ['hard_data_layer','soft_data_layer','estimated_data_layer',
                     'current_mean_layer', 'current_variance_layer']:
            lyr = getattr(self.parent().MainDlg,flag)
            try:
                lyr.setCacheImage( None )
            except AttributeError:
                pass

        self.parent().MainDlg.iface.mapCanvas().refreshAllLayers()  
        
        
    def update_(self,min_,max_,cmap):
        self.ui.lineEdit_minvalue.setText(str(min_))
        self.ui.lineEdit_maxvalue.setText(str(max_))
        idx = self.ui.comboBox_cmap.findText(cmap)
        if idx == -1:
            idx = self.ui.comboBox_cmap.findText(cmap[:-2])
            self.ui.checkBox_inverse.setChecked( True )
        self.ui.comboBox_cmap.setCurrentIndex(idx)