# -*- coding: utf-8 -*-
'''
Created on 2012/1/28

@author: ksj
'''

#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
import os
import sys
import numpy

from matplotlib.pyplot import cm
from ui.ui_ViewDataDlg import Ui_ViewDataDlg

class ViewDataDlg(QDialog, Ui_ViewDataDlg):
    def __init__(self, parent, main):
        super(ViewDataDlg,self).__init__(parent)
        
        self.ui = Ui_ViewDataDlg()
        self.ui.setupUi(self)
        
        #Get bmeobj from mainwindow
        self.main = main
        self.bmeobj = main.bmeobj
        
        self.draw_id = None
        self.draw_flag = None
        
        #rename
        self.canvas = self.ui.mplWidget.canvas

        self.ui.pushButton_close.clicked.connect( self.close )
        self.ui.checkBox_alldatascale.toggled[bool].connect( self.changeXYBound )
        self.ui.checkBox_showtrend.toggled[bool].connect( self.showTrend )
        
        
        
        #self.ui.checkBox_alldatascale.toggled.connect(self.changeXYBound)
           
    def draw(self, id_, flag):
        self.draw_id = id_
        self.draw_flag = flag
        def setDataObj(flag):
            if flag == "est":
                self.dataobj = self.bmeobj.estimated_data
            elif flag == "hard":
                self.dataobj = self.bmeobj.hard_data
            elif flag =="soft":
                self.dataobj = self.bmeobj.soft_data
        
        def getTZTrVDataSet(flag):
            t = self.dataobj.t_grid[0]
            if flag == "hard":
                z = self.dataobj.z_grid[id_,:]
                if self.dataobj.z_grid.shape == self.dataobj.tr_grid.shape:
                    tr = self.dataobj.tr_grid[id_,:]
                    tr_no_nan = tr[numpy.where(~numpy.isnan(z))]
                else:
                    tr_no_nan = None
                var_no_nan = None

            elif flag == "soft":
                z = self.dataobj.z_grid[id_,:]
                var = self.dataobj.var_grid[id_,:]
                quantile = self.dataobj.quantile_grid[ id_,: ]
                if self.dataobj.z_grid.shape == self.dataobj.tr_grid.shape:
                    tr = self.dataobj.tr_grid[id_,:]
                    tr_no_nan = tr[numpy.where(~numpy.isnan(z))]
                else:
                    tr_no_nan = None
                var_no_nan = var[numpy.where(~numpy.isnan(z))]

                self.quantile_no_nan = quantile[numpy.where(~numpy.isnan(z))]

            elif flag == "est":
                z = self.dataobj.z_mean_grid[id_,:]
                if self.dataobj.z_mean_grid.shape == self.dataobj.tr_grid.shape:
                    tr = self.dataobj.tr_grid[id_,:]
                    tr_no_nan = tr[numpy.where(~numpy.isnan(z))]
                else:
                    tr_no_nan = None
                var = self.dataobj.z_variance_grid[id_,:]
                var_no_nan = var[numpy.where(~numpy.isnan(z))]
                
            
                
            t_no_nan = t[numpy.where(~numpy.isnan(z))]
            z_no_nan = z[numpy.where(~numpy.isnan(z))]

            return t_no_nan,z_no_nan,tr_no_nan,var_no_nan
        
        
        setDataObj(flag)
        t_no_nan,z_no_nan,tr_no_nan,var_no_nan = getTZTrVDataSet(flag)   
        title = str(self.dataobj.s_grid[id_])
        
    
        #plot
        self.canvas.ax.clear()       
        if flag == "hard":
            lines_m = self.canvas.ax.plot( t_no_nan, z_no_nan,"bo-") #data
#         elif flag == "soft":
#             lines_m = self.canvas.ax.plot(t_no_nan, z_no_nan,"b--")
#             #find probdens & limi @ that position and time
#             pltdata_list = []
#             point_x, point_y = self.dataobj.s_grid[id_]
#             xyt_list = numpy.hstack((self.dataobj.x,self.dataobj.y,self.dataobj.t))
#             xyt_list = xyt_list.tolist()

#             for point_t in self.dataobj.t_grid[0]:
#                 xyt = numpy.array([point_x,point_y,point_t]).tolist()


#                 try:
#                     idx = xyt_list.index(xyt)
#                     limi_i = self.dataobj.limi[idx]
#                     pltdata_list.append(limi_i)
#                 except ValueError:
#                     pltdata_list.append( [numpy.nan] )
                    
# ##                idx = xyt_list.index(xyt)
# ##                if idx != -1:
# ##                    limi_i = self.dataobj.limi[idx]
# ##                    pltdata_list.append(limi_i)
# ##                else:
# ##                    pltdata_list.append(numpy.nan)
                    
#    #============================================================================
#    #             try:
#    #                 #QMessageBox.information(None,'xyt,xyt_list',str(xyt)+"\n"+str(xyt_list))
#    # 
#    #                 idx = numpy.where(xyt_list == xyt)[0][2]
#    # 
#    #                 #QMessageBox.information(None,'numpy.where',str(numpy.where(xyt_list == xyt)))
#    #                 #QMessageBox.information(None,'idx',str(idx))
#    #                 
#    #                 #probdens_i = self.dataobj.probdens[idx]
#    #                 limi_i = self.dataobj.limi[idx]
#    #                 #QMessageBox.information(None,'limi',str(limi_i))
#    #                 #pltdata_list.append(probdens_i + limi_i[6])
#    #                 pltdata_list.append(limi_i)
#    #             except IndexError:
#    #                 pltdata_list.append(numpy.nan)
#    #============================================================================               
                    
#             #QMessageBox.information(None,'fds',str(pltdata_list))
#             original_xticks = self.canvas.ax.get_xticks()
#             self.canvas.ax.boxplot(pltdata_list, positions = t_no_nan)
#             #self.canvas.ax.xaxis.set_ticks(t_no_nan)
#             self.canvas.ax.xaxis.set_ticks( original_xticks )
#             # range(1,len(x_no_nan)+1), map(str,x_no_nan) )

        elif flag == "soft":
            quantile_no_nan = self.quantile_no_nan
            q_5 = quantile_no_nan[:,0]
            q_25 = quantile_no_nan[:,1]
            q_50 = quantile_no_nan[:,2]
            q_75 = quantile_no_nan[:,3]
            q_95 = quantile_no_nan[:,4]

            yerr = numpy.vstack( (q_50 - q_5, q_95 - q_50 ) )
            lines_m2 = self.canvas.ax.bar( x = t_no_nan, height = q_75 - q_50,
                                          bottom = q_50, edgecolor = 'b',
                                          align = 'center', fill=False ) #data
            lines_m4 = self.canvas.ax.bar( x = t_no_nan, height = q_50 - q_25,
                                          bottom = q_25, edgecolor = 'b',
                                          align = 'center', fill=False ) #data
            lines_m3 = self.canvas.ax.errorbar( t_no_nan, q_50,
                                                yerr = yerr, fmt = "b_") #data
            lines_m = self.canvas.ax.plot( t_no_nan, z_no_nan,"bo-")

            # lines_m = self.canvas.ax.errorbar( t_no_nan, z_no_nan,
            #                                    yerr = 1.96 * numpy.sqrt(var_no_nan), fmt = "bo-") #data
            #lines = self.canvas.ax.errorbar( )

        elif flag == "est":
            lines_m = self.canvas.ax.plot( t_no_nan, z_no_nan,"bo-")         
            up_z = z_no_nan + 1.96 * numpy.sqrt(var_no_nan)
            low_z = z_no_nan - 1.96 * numpy.sqrt(var_no_nan)
            lines = self.canvas.ax.plot(t_no_nan,up_z,"b--", t_no_nan,low_z,"b--")
        
        
        
        
        #plot trend if need and set legend
        if tr_no_nan is None: #no trend:
            self.ui.checkBox_showtrend.hide()
            self.ui.checkBox_showtrend.setChecked(False)
            if flag == "est":
                self.canvas.ax.legend((lines_m[0],lines[0]),("Data","95% Confidence Interval"))
            else:
                self.canvas.ax.legend((lines_m[0],),("Data",))
        else:
            self.ui.checkBox_showtrend.show()
            if self.ui.checkBox_showtrend.isChecked():
                lines_tr = self.canvas.ax.plot( t_no_nan, tr_no_nan, 'go-') #trend      
                if flag == "est":
                    self.canvas.ax.legend((lines_m[0],lines[0],lines_tr[0]),("Data","95% Confidence Interval","Trend"))
                else:    
                    self.canvas.ax.legend((lines_m[0],lines_tr[0]),("Data","Trend"))
            else:
                if flag == "est":
                    self.canvas.ax.legend((lines_m[0],lines[0]),("Data","95% Confidence Interval"))
                else:
                    self.canvas.ax.legend((lines_m[0],),("Data",))
            
        self.canvas.ax.set_title(title)
        self.canvas.ax.set_xlabel("Time")
        if flag == "est":
            self.canvas.ax.set_ylabel( "Estimated Data" )
        else:
            self.canvas.ax.set_ylabel( "Observed Data" )
        
        xm, xM, ym, yM = self.getBoundary()
        if self.ui.checkBox_alldatascale.isChecked():
            method = 'defined'
        else:
            method = 'default'
        self.setBoundary(method, xm, xM, ym, yM)
        self.canvas.draw()
        self.raise_()
    
    def showTrend(self,bool_):
        self.draw(self.draw_id, self.draw_flag)
        
    def getBoundary(self):
            xm,xM = self.dataobj.station_t_min,self.dataobj.station_t_max
            try:
                ym,yM = self.dataobj.z_min_without_nan,self.dataobj.z_max_without_nan
            except AttributeError: #estimated_data
                ym,yM = self.dataobj.z_all_min_without_nan,self.dataobj.z_all_max_without_nan
            return xm,xM,ym,yM
        
    def setBoundary(self, method = 'default',xm = None, xM = None, ym = None, yM = None):
        import numpy as _np
        if method == 'default':
            self.canvas.ax.autoscale_view()
        elif method == 'defined':
            # FIX D (part 2): Guard against NaN/Inf bounds from noisy
            # QMC variance estimates — fall back to autoscale if invalid.
            _vals = [xm, xM, ym, yM]
            if any(v is None or not _np.isfinite(v) for v in _vals):
                self.canvas.ax.autoscale_view()
            else:
                self.canvas.ax.set_xbound(xm, xM)
                self.canvas.ax.set_ybound(ym, yM)
       
    def changeXYBound(self,all_scale):
        if all_scale:
            xm, xM, ym, yM = self.getBoundary()
            self.setBoundary('defined',xm, xM, ym, yM)
        else:
            self.setBoundary('default')
        self.canvas.draw()

    def closeEvent(self,e):
        self.main.iface.mapCanvas().scene().removeItem(self.main.marker)
        self.close()
        
class HistogramViewDlg(ViewDataDlg): 
    
    def __init__(self, parent, main):
        super(HistogramViewDlg,self).__init__(parent, main)
        self.ui.checkBox_alldatascale.hide()
        self.ui.checkBox_showtrend.hide()
        self.resize(430,444)
    def draw(self, id_, flag): #overload draw method to draw histogram
        BINS = 20
        def setDataObj(flag):
            if flag == "est":
                self.dataobj = self.bmeobj.estimated_data
            elif flag == "hard":
                self.dataobj = self.bmeobj.hard_data
            elif flag =="soft":
                self.dataobj = self.bmeobj.soft_data
        
        def getTZTrVDataSet(flag):
            t = self.dataobj.t_grid[0]
            if flag == "hard" or flag == "soft":
                z = self.dataobj.z_grid[id_,:]
                if self.dataobj.z_grid.shape == self.dataobj.tr_grid.shape:
                    tr = self.dataobj.tr_grid[id_,:]
                    tr_no_nan = tr[numpy.where(~numpy.isnan(z))]
                else:
                    tr_no_nan = None
                var_no_nan = None
            elif flag == "est":
                z = self.dataobj.z_mean_grid[id_,:]
                if self.dataobj.z_mean_grid.shape == self.dataobj.tr_grid.shape:
                    tr = self.dataobj.tr_grid[id_,:]
                    tr_no_nan = tr[numpy.where(~numpy.isnan(z))]
                else:
                    tr_no_nan = None
                var = self.dataobj.z_variance_grid[id_,:]
                var_no_nan = var[numpy.where(~numpy.isnan(z))]
                
            
                
            t_no_nan = t[numpy.where(~numpy.isnan(z))]
            z_no_nan = z[numpy.where(~numpy.isnan(z))]

            return t_no_nan,z_no_nan,tr_no_nan,var_no_nan
        
        
        setDataObj(flag)
        t_no_nan,z_no_nan,tr_no_nan,var_no_nan = getTZTrVDataSet(flag)   
        title = str(self.dataobj.s_grid[id_])
        
    
        #plot
        self.canvas.ax.clear()       
        if flag == "hard":
            self.canvas.ax.hist( z_no_nan , BINS) #data
        elif flag == "soft":
            self.canvas.ax.hist( z_no_nan , BINS)
        elif flag == "est":
            self.canvas.ax.hist( z_no_nan , BINS)         
            
            
        self.canvas.ax.set_title(title)
        if flag == "est":
            self.canvas.ax.set_xlabel( "Estimated Data" )
        else:
            self.canvas.ax.set_xlabel( "Observed Data" )
        self.canvas.ax.set_ylabel("Count")

        self.canvas.draw()
        self.raise_()
    
