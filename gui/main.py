# -*- coding: utf-8 -*-
#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.core import QgsProject

import resources
welcomepic = QPixmap(":/stemlab.png")
welcome = QSplashScreen( welcomepic )
welcome.show()

welcome.showMessage( "Loading Modules.", color = Qt.yellow )
QApplication.processEvents()

import os
import sys
import time
import matplotlib
import shelve
#import cPickle
import pickle
import copy
import numpy

import star_variable
#DBPERMISSIONSERROR = star_variable.DBPERMISSIONSERROR
DBPERMISSIONSERROR = Exception
SHELVE_ENCODING = star_variable.SHELVE_ENCODING
WORKING_PATH = star_variable.WORKING_PATH


#try:
#    from scipy.interpolate import griddata as scipy_griddata
#except ImportError:
#    try:
#        from pylab import griddata as pylab_griddata #qgis
#    except ImportError:
#        from matplotlib.pylab import griddata as pylab_griddata #OSGEO4W qgis

from osgeo import gdal
welcome.showMessage("Loading Modules..",color = Qt.yellow)

from lib import pybme
welcome.showMessage("Loading Modules...",color = Qt.yellow)
from STAR_BME.gui import stbme2qgis

from . import setdata
from . import plotandfitcov
from . import bmeestimate


welcome.showMessage("Create GUIs...",color = Qt.yellow)
QApplication.processEvents()


from ui.ui_MainWindow import Ui_MainWindow

from ui.mplwidget import MplWidget

#try to create temp folder
if os.path.isdir( WORKING_PATH ):
    pass
else:
    os.mkdir( WORKING_PATH )

class MainWindow(QMainWindow,Ui_MainWindow):
    
    def _setDefault(self):
        def resetVectorLayerData():
            self.vector_layer_data.clear()
            
        self.bmeobj.__init__() #Reset BmeObj
        self.color_bar.hide() #Reset ColorBar
        self.time_bar.hide() #Reset TimeBar
        self.viewdatadlg.hide() #Reset ViewDataDlg
        self.histogramviewdlg.hide() #Reset HistogramViewDlg
        
        #init
        self.properties = {}
        
        self.has_add_raster_layer = False
        self.mean_layer_list = []
        self.current_mean_layer = None
        self.variance_layer_list = []
        self.current_variance_layer = None
        
        #qgis
        self.hard_data_layer = None
        self.soft_data_layer = None
        self.estimated_data_layer = None
        
        #Setting parameters
        self.setWindowTitle(self.DEFAULT_FILE_NAME + " - " + self.WINDOW_TITLE)
        self.setWindowIcon(QIcon(":/stemlab.png"))
        self.file_name = self.DEFAULT_FILE_NAME
        self.file_path = self.DEFAULT_FILE_PATH
        self.detrend_method_name = self.DEFAULT_DETREND_METHOD_NAME   
        detrend_method_index = self.ui.comboBox_detrendmethod.findText(self.detrend_method_name)
        self.ui.comboBox_detrendmethod.setCurrentIndex(detrend_method_index)   
        self.estimated_data_source_type = None 
        #self.estimated_shape_file_type = QGis.Point # 0
        self.estimated_shape_file_type = QgsWkbTypes.PointGeometry 
        self.estimated_shape_file_path = None
        
        #crs of output
        self.crs = QgsCoordinateReferenceSystem()
        self.use_crs = False
        
        #GUI configure parameters
        self.stage = -10
         
        self.buttonsUpdate()     
        #flags
        self.dirty = False
        self.has_file = False
        self.has_mask = False
        
        resetVectorLayerData()

        self.cv_dlg = None

        self.composer_view = None

        self.grid_param = None

    def setViewData(self):
        self.iface.mapCanvas().setMapTool(self.tool_view_data)
        
    def setHistogramView(self):
        self.iface.mapCanvas().setMapTool(self.tool_histogram_view)
        
    def viewData(self,qgs_point, qt_mouse_btn):
        def findId(layer):
            def getSelectedRect(x,y):
                #get point size, default 4
                pixel = 4 #self.iface.activeLayer().rendererV2().symbols()[0].size()
                #pixel tolerant
                dr = (pixel+2) * self.iface.mapCanvas().mapSettings().mapUnitsPerPixel()
                
                
                return self.iface.mapCanvas().mapSettings().mapToLayerCoordinates ( layer, QgsRectangle (x-dr, y-dr, x+dr, y+dr) )
                 
            x,y = qgs_point.x(), qgs_point.y()
            rect = getSelectedRect(x,y)
            
            qgis_request = QgsFeatureRequest()
            qgis_request.setFilterRect( rect )

            ftr_list = []
            id_count = 0
            for ftr in layer.getFeatures( qgis_request ):
                ftr_list.append( ftr )
                id_count += 1
            
            if id_count > 1:
                QMessageBox.critical(self,"BAD",
                    "Too many points within range\nPlease try to zoom in and select again.")
                return False
            elif id_count == 1:
                return ftr_list[0].id()
            else: # 0
                return False

        def showMarker(layer,id_):
            qgis_request = QgsFeatureRequest()
            qgis_request.setFilterFid( id_ )
            ftr_iter = layer.getFeatures( qgis_request )
            for ftr in ftr_iter: #only do once
                pt = ftr.geometry().asPoint()
                x, y = pt.x(), pt.y()
                marker = QgsVertexMarker(self.iface.mapCanvas())
                marker.setIconType(QgsVertexMarker.ICON_BOX)
                marker.setCenter(QgsPointXY(x, y))
                return marker
        
        try: #remove maker
            self.iface.mapCanvas().scene().removeItem(self.marker)
        except AttributeError:
            pass
        
        layer = self.iface.activeLayer()
        if layer and layer.name() in ["EstimatedData","HardData","SoftData"]:
            that_id = findId(layer)
            if that_id is not False: #b/s id = 0 will means False too !!
                self.marker = showMarker(layer, that_id)
                self.viewdatadlg.show()
                if layer.name() == "EstimatedData":
                    self.viewdatadlg.draw(that_id,"est")
                elif layer.name() == "HardData":
                    self.viewdatadlg.draw(that_id,"hard")
                elif layer.name() == "SoftData":
                    self.viewdatadlg.draw(that_id,"soft")
                    # if qt_mouse_btn == Qt.LeftButton:
                    #      QMessageBox.information(self,"GOOD!","SUCCESS!!\n"
                    #                         "coord is "+str(x)+" "+str(y)+"\nLeft")
                    # elif qt_mouse_btn == Qt.RightButton:
                    #     QMessageBox.information(self,"GOOD!","SUCCESS!!\n"
                    #                         "coord is "+str(x)+" "+str(y)+"\nRight")
       
    def histogramView(self,qgs_point, qt_mouse_btn):
        def findId(layer):
            def getSelectedRect(x,y):
                #get point size  # default to 4
                pixel = 4 #self.iface.activeLayer().rendererV2().symbols()[0].size()
                #pixel tolerant
                dr = (pixel+2) * self.iface.mapCanvas().mapSettings().mapUnitsPerPixel()
                return self.iface.mapCanvas().mapSettings().mapToLayerCoordinates ( layer, QgsRectangle (x-dr, y-dr, x+dr, y+dr) )
                
            x,y = qgs_point.x(), qgs_point.y()
            rect = getSelectedRect(x,y)

            qgis_request = QgsFeatureRequest()
            qgis_request.setFilterRect( rect )
            ftr_list = []
            id_count = 0
            for ftr in layer.getFeatures( qgis_request ):
                ftr_list.append( ftr )
                id_count += 1
            
            if id_count > 1:
                QMessageBox.critical(self,"BAD","too many")
                return False
            elif id_count == 1:
                return ftr_list[0].id()
            else: # 0
                return False

        def showMarker(layer,id_):
            qgis_request = QgsFeatureRequest()
            qgis_request.setFilterFid( id_ )
            ftr_iter = layer.getFeatures( qgis_request )
            for ftr in ftr_iter: #only do once
                pt = ftr.geometry().asPoint()
                x, y = pt.x(), pt.y()
                marker = QgsVertexMarker(self.iface.mapCanvas())
                marker.setIconType(QgsVertexMarker.ICON_BOX)
                marker.setCenter(QgsPointXY(x, y))
                return marker
        
        try: #remove maker
            self.iface.mapCanvas().scene().removeItem(self.marker)
        except AttributeError:
            pass
        
        layer = self.iface.activeLayer()
        if layer and layer.name() in ["EstimatedData","HardData","SoftData"]:
            that_id = findId(layer)
            if that_id is not False: #b/s id = 0 will means False too !!
                self.marker = showMarker(layer, that_id)
                self.histogramviewdlg.show()
                if layer.name() == "EstimatedData":
                    self.histogramviewdlg.draw(that_id,"est")
                elif layer.name() == "HardData":
                    self.histogramviewdlg.draw(that_id,"hard")
                elif layer.name() == "SoftData":
                    self.histogramviewdlg.draw(that_id,"soft")
     
    def __init__(self, iface = None, parent = None):
        def developmentLoad():
            # path = os.path.abspath(os.path.dirname(__file__))+r'\..\bmeobj_bmeestimation.bme'
            # self.bmeobj.load(path)
            pass
            #self.actOpen()
   
        def addViewDataTools():
            
            #create a action
            actionViewData = QAction( QIcon(":/timeview.png"), "Time View", self)
            actionViewData.setCheckable(True)
            #connect it to check the tool
            actionViewData.triggered.connect( self.setViewData )
            #add action to qgis toolbar
            self.iface.attributesToolBar().addAction(actionViewData)
            #create a QgsTool
            self.tool_view_data = QgsMapToolEmitPoint(self.iface.mapCanvas())
            #set it's action
            self.tool_view_data.setAction(actionViewData)
            #connect tool to pyfunc
            # self.tool_view_data.canvasClicked[QgsPoint, Qt.MouseButton].connect( self.viewData )
            self.tool_view_data.canvasClicked.connect( self.viewData )
        def addHistogramViewTools():
            #create a action
            actionHistogramView = QAction( QIcon(":/histogramview.png"), "HistogramView", self)
            actionHistogramView.setCheckable(True)
            #connect it to check the tool
            actionHistogramView.triggered.connect( self.setHistogramView )
            #add action to qgis toolbar
            self.iface.attributesToolBar().addAction(actionHistogramView)
            #create a QgsTool
            self.tool_histogram_view = QgsMapToolEmitPoint(self.iface.mapCanvas())
            #set it's action
            self.tool_histogram_view.setAction(actionHistogramView)
            #connect tool to pyfunc
            self.tool_histogram_view.canvasClicked.connect( self.histogramView)
             
        super( MainWindow, self ).__init__( parent )
        self.iface = iface
        self.ui = Ui_MainWindow()
        self.ui.setupUi( self )
        
        #version flag
        self.version = '0.6.0' #replace flag
        
        #addTool
        addViewDataTools()
        addHistogramViewTools()

        #create gdal
        FORMAT = "GTiff"
        self.gdal_driver = gdal.GetDriverByName( FORMAT )
        
        #Create bmeobj
        self.bmeobj = pybme.BmeObj()
        
        #dimension
        self.spatial_only = None
        
        #save all vector layer state
        self.vector_layer_data = {}

        #save the last opened folder
        self.last_opened_folder = os.path.abspath(os.path.dirname( __file__ ))+"/../"
        
        #createColorBar
        from main_mplcolorbar import ColorBarDockWgt
        self.color_bar = ColorBarDockWgt(self,self) #first 'self' will be change by 'adddockwidget'
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.color_bar)
        #self.color_bar.hide()
        #color_bar.resize(20,color_bar.size().height())
        #self.color_bar.update()
        #self.has_add_color_bar = False

        #Create TimeBar
        from main_timebar import TimeBarDockWgt
        self.time_bar = TimeBarDockWgt(self)
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.time_bar)
        #time_bar.resize(time_bar.size().width(),80)
        #time_bar.hide()
        #self.has_add_time_bar = False
        
        #Create ViewDataDialog
        from main_viewdatadlg import ViewDataDlg
        self.viewdatadlg = ViewDataDlg(self.iface.mainWindow(), self)
        
        #Create HistogramViewDialog
        from main_viewdatadlg import HistogramViewDlg
        self.histogramviewdlg = HistogramViewDlg(self.iface.mainWindow(), self)
           
        #kernel not yet
        #self.ui.comboBox_detrendmethod.removeItem ( 1 ) #kernel smoothing
        #self.ui.comboBox_detrendmethod.removeItem ( 1 ) #stmean
        
        #Default Parameters of the Main dialog
        self.WINDOW_TITLE = "Space Time Bayesian Maximum Entropy Method (Version 0.6.0)"
        self.DEFAULT_FILE_PATH = os.path.abspath(os.path.dirname( __file__ ))+"/../"
        self.DEFAULT_FILE_NAME = "bmeobj.bme"
        self.DEFAULT_DETREND_METHOD_NAME = "No Detrending"
        
        #Add debug dock widget
        from main_debugdockwgt import DebugDockWgt
        self.ui.dockWidget_debugwindow = DebugDockWgt(self)
        self.ui.dockWidget_debugwindow.setObjectName("dockWidget_debugwindow")
        self.addDockWidget(Qt.RightDockWidgetArea, self.ui.dockWidget_debugwindow)
        self.ui.dockWidget_debugwindow.setStyleSheet("QWidget#dockWidgetContents"
                                                    " {background : white}")
        self.ui.dockWidget_debugwindow.hide()
        self.ui.menu_view.addAction(self.ui.dockWidget_debugwindow.toggleViewAction())
        self.ui.dockWidget_debugwindow.setFloating(True)
        #Add Matplotlib dock widget
        # from main_mpldockwgt import MplDockWgt
        # self.ui.dockWidget_datavisualization = MplDockWgt(self)
        # self.ui.dockWidget_datavisualization.setObjectName("dockWidget_datavisualization")
        # self.addDockWidget(Qt.RightDockWidgetArea, self.ui.dockWidget_datavisualization)
        # self.ui.dockWidget_datavisualization.setStyleSheet("QWidget#dockWidgetContents"
        #                                             " {background : white}")
        # self.ui.dockWidget_datavisualization.hide()
        # self.ui.menu_view.addAction(self.ui.dockWidget_datavisualization.toggleViewAction())
        # self.ui.dockWidget_datavisualization.setFloating(True)
        # self.ui.dockWidget_datavisualization.setDisabled(True)
        
        self.adjustSize() 
        
        self.buttons_dic={
            #-10:self.ui.pushButton_crs,          
            -1:self.ui.pushButton_setdata,
            0:self.ui.pushButton_setestimateddata,
            
            # 4:self.ui.dockWidget_datavisualization,
            10:self.ui.pushButton_detrend,
            20:self.ui.pushButton_plotandfit,
            30:self.ui.pushButton_estimate,
            39:self.ui.pushButton_crossvalidation,
            40:self.ui.pushButton_doapp}  
        
        # button connect
        self.ui.pushButton_addbackgroundshapefile.clicked.connect( self.addbgshpfile )
        self.ui.pushButton_setdata.clicked.connect( self.setdata )
        self.ui.pushButton_setestimateddata.clicked.connect( self.setestimateddata )
        self.ui.pushButton_detrend.clicked.connect( self.detrend )
        self.ui.pushButton_plotandfit.clicked.connect( self.plotandfit )
        self.ui.pushButton_estimate.clicked.connect( self.estimate )
        self.ui.pushButton_doapp.clicked.connect( self.doapp )
        self.ui.pushButton_crossvalidation.clicked.connect( self.crossValidation )
        
        #action connect
        self.ui.pushButton_crs.clicked.connect( self.setcrs ) #new writing method
        self.ui.checkBox_crs.toggled.connect( self.changeCrsSetting )
        self.ui.checkBox_crs.hide() #no use anymore
        
        self.ui.action_new.triggered.connect( self.actNew )
        self.ui.action_save.triggered.connect( self.actSave )
        self.ui.action_saveas.triggered.connect( self.actSaveAs )
        self.ui.action_open.triggered.connect( self.actOpen )
        self.ui.action_quit.triggered.connect( self.actQuit )
        self.ui.action_about.triggered.connect( self.actAbout )
        self.ui.action_option.triggered.connect( self.actOption )
        

        self.ui.statusbar.showMessage("Ready",5000)
        
        QgsProject.instance().layerTreeRoot().addGroup("STBME_Vector")
        QgsProject.instance().layerTreeRoot().addGroup("STBME_Raster")
        #self.iface.legendInterface().addGroup("STBME_Raster")
        
        self._setDefault()
        developmentLoad()

    def addShapeFile( self, file_path, file_name, render_method = None ):
        vlayer = QgsVectorLayer( file_path, file_name, "ogr" )
        if vlayer.isValid():
            if render_method == 'Background':                    
                if vlayer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    # QGIS 3: Use QgsSymbolLayerRegistry (no V2)
                    meta = QgsApplication.symbolLayerRegistry().symbolLayerMetadata("SimpleFill")
                    symbol_lyr = meta.createSymbolLayer( { "style":"no"} ) 
                    vlayer.renderer().symbol().changeSymbolLayer(0, symbol_lyr)
                else:
                    QMessageBox.critical(self,"Error","Shape File Cannot be a Background.")
                    return False
            QgsProject.instance().addMapLayer(vlayer)
            return vlayer
        else:
            QMessageBox.critical(self,"Error","Shape File Cannot be Loaded.")
            return False
            
    def moveLayerToGroup( self, layer, group_name ):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(group_name)
        if group is None:
            return False

        # Find the layer node in the layer tree root
        layer_node = root.findLayer(layer.id())
        if layer_node is None:
            return False

        # Clone the node into the target group, then remove the original
        clone = layer_node.clone()
        group.insertChildNode(0, clone)
        layer_node.parent().removeChildNode(layer_node)
        return True
            
    def addbgshpfile(self):
        path_type = QFileDialog.getOpenFileName(\
                       self,"Load BME Object",
                       self.last_opened_folder, "Shape file (*.shp)")
        path, type_ = path_type
        if not path:
            return
        else:
            #not empty path, set to loast opened folder
            self.updateLastOpenedFolder(path)
            vlayer = self.addShapeFile(path, "BackgroundData", "Background")
            if not vlayer:
                return

        #find group & add
        self.moveLayerToGroup(vlayer, 'STBME_Vector')
            
        #make a copy file
        if self.saveVectorLayer(path, 'Background'):
            pass
        else: 
            raise ValueError('12345')
        QMessageBox.information(self, "Load Completed", "Shape File has been Loaded.")
        
    def setcrs(self):
        self.crsdlg = QgsProjectionSelectionDialog (self)
        #seself.crsdlg = QgsGenericProjectionSelector (self)
        #if self.crsdlg.selectCrs():
        if self.crsdlg.exec_():
            selected_crs = QgsCoordinateReferenceSystem( self.crsdlg.crs() )
            #selected_crs = QgsCoordinateReferenceSystem( self.crsdlg.crs(),QgsCoordinateReferenceSystem.InternalCrsId  )
            projString = selected_crs.toProj()
            if projString == "":
                QMessageBox.critical(self, self.tr("Error"), self.tr("No Valid CRS selected"))
                return
            else:
                self.crs.createFromProj(projString)
                if self.crs.isValid():
                    self.setStage(0)
                    self.buttonsUpdate()
                    self.setUseCrs( True )
                    QMessageBox.information(self, "OK","Setting Data CRS Done.")
                    pass #should be
                else:
                    QMessageBox.critical(self, "very strange error","please contact me.")
                
        else:
            return
        
    def setdata(self):
        self.dlg = setdata.SetDataDlg(self.iface, self)
        self.dlg.setWindowTitle('Specify Data')
        idx = self.dlg.ui.comboBox_hardfrom.findText("Layer")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        idx = self.dlg.ui.comboBox_hardfrom.findText("Shape File")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        idx = self.dlg.ui.comboBox_hardfrom.findText("Grid Input")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        idx = self.dlg.ui.comboBox_hardfrom.findText("Shape File (With Time Input)")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        self.dlg.exec_()

    def detrend(self):
        #Get detrend method and parameter from GUI
        method = str(self.ui.comboBox_detrendmethod.currentText())
        parameters = self._getDetrendParameters(method)
        if parameters == None: #Cancel by user
            return False
        
        #create QprogressDialog and set it to bmeobj
        self.qpgd = QProgressDialog(self)
        self.qpgd.setWindowModality(Qt.WindowModal)
        self.bmeobj.setProgressDialog(self.qpgd)
        self.bmeobj.setProgressAutoClose(False)
        if self.bmeobj.detrend(method, parameters+(self.bmeobj,)):
            self.bmeobj.trend.setParameters(parameters) # delete GUIobj
            self.bmeobj.progress_dialog.close()
            self.setStage(20)
            self.buttonsUpdate()
            self.dirty = True
            QMessageBox.information(self,"OK","Detrending completed.\n")             
            return True
        else:
            QMessageBox.critical(self, "Error", "Detrending failed.\n")
            return False
        
    def plotandfit(self):
        self.dlg = plotandfitcov.PlotAndFitCovDlg(self.iface,self)
        self.dlg.exec_()
        
    def estimate(self):
        self.dlg = bmeestimate.BmeEstDlg(self.iface, self)
        self.dlg.exec_()
    
    def doapp(self):
        if self.ui.comboBox_app.currentText() ==\
            u'Add Result to QGIS (Vector)':
            #Add Result To QGIS
            self.cleanWorkSpaceEstimatedLayer()
            if self.hasAddRasterLayer(): #need redraw
                self.cleanWorkSpaceGtiff()
                self.has_add_raster_layer = True
            self.addResultToQgis()
        elif self.ui.comboBox_app.currentText() ==\
            u'Add Result to QGIS (Raster)':
            if self.estimated_data_source_type in ['File', 'Layer', 'ShapeFile' ]:
                QMessageBox.critical(self,"Estimated Data Type Error",'Sorry! This Method Can Used Only With Estimated Data is "Grid Input" Type.')
            elif self.estimated_data_source_type == "Grid Input":
                self.cleanWorkSpaceGtiff()
                self.addResultToQgisRaster()
        elif self.ui.comboBox_app.currentText() == \
            u'Add Result to QGIS (Raster with Mask)':
            if self.estimated_data_source_type in ['File', 'Layer', 'ShapeFile' ]:
                QMessageBox.critical(self,"Estimated Data Type Error",'Sorry! This Method Can Used Only With Estimated Data is "Grid Input" Type.')
            elif self.estimated_data_source_type == "Grid Input":
                self.cleanWorkSpaceGtiff()
                self.addResultToQgisRasterWithMask()
        elif self.ui.comboBox_app.currentText() ==\
            u"Export Result to File":
            self.exportResultToFile()
        elif self.ui.comboBox_app.currentText() ==\
            u"Export Result to PNG":
                self.createCustomComposer()


            
    def _getDetrendParameters(self, method):
        if method.lower() in ["no detrending", "nd", "stmean", "stm"]:
            return ()
        elif method.lower() in ["kernel smoothing", "ks"]:     
            self.dlg = DetrendParamDlg(self, title = "Kernel Smoothing")
            
            ktype = QComboBox()
            ktype.addItem( 'Gaussian' )
            ktype.addItem( 'Quadratic' )
            
            bs = QLineEdit("")
            bt = QLineEdit('')
            
                
            self.dlg.addParameter2("bs", bs, "Spatial Range", lambda bs: float( str( bs.text() ) ) )
            self.dlg.addParameter2("bt", bt, "Temporal Range", lambda bt: float( str( bt.text() ) ))
            
            self.dlg.addParameter2("Kernel Type", ktype, "Gaussian or Quadratic", lambda cb: str( cb.currentText() ).lower() )
            
              
            while self.dlg.exec_():
                try:
                    return self.dlg.returnParameters()
                    
                except ValueError:
                    QMessageBox.critical(self,"Input Error",
                                              'You must specify all range values to run the kernel smoothing task')
                    
            return None
    
    def setestimateddata(self):
        self.dlg = setdata.SetDataDlg(self.iface, self)
        self.dlg.setWindowTitle('Prediction Locations')
        self.dlg.ui.tabWidget.removeTab(1)
        self.dlg.ui.tabWidget.setTabText(0,"Location Data")
        self.dlg.ui.label_11.setText("Select Location Data Source:")
        self.dlg.ui.label_2.setText("----Prediction Locations Preview----")
        self.dlg.ui.label_6.setDisabled(True)
        self.dlg.ui.comboBox_z.setDisabled(True)
        if self.isSpatialOnly():
            ##self.dlg.ui.comboBox_t.setCurrentIndex( 0 ) #text None
            self.dlg.ui.comboBox_t.setDisabled(True)
            self.dlg.ui.label_5.setDisabled(True) # label T

        idx = self.dlg.ui.comboBox_hardfrom.findText("Layer")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        idx = self.dlg.ui.comboBox_hardfrom.findText("Shape File")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        idx = self.dlg.ui.comboBox_hardfrom.findText("Shape File (With Time Input)")
        self.dlg.ui.comboBox_hardfrom.removeItem(idx)
        
        if self.dlg.exec_():
            self.estimated_data_source_type = self.dlg.data_source_type
            if self.estimated_data_source_type == "Grid Input":
                self.grid_param = self.dlg.grid_param
        
    def setStage(self,int_):
        self.stage = int_
        
    def buttonsUpdate(self):
        for key,button_obj in self.buttons_dic.items():
            if key <= self.stage:
                button_obj.setDisabled(False)
            else:
                button_obj.setDisabled(True)

    def actNew(self):
        #has file or not here is doesn't matter
        if self.isDirty():       
            answer = self._askForSave()
            self._saveByAnswer(answer)
            self._setDefaultByAnswer(answer)
        else:
            self._setDefault()
        
    def actSave(self):
        if self.hasFile():
            if self.isDirty():
                path = os.path.join( self.file_path, self.file_name )
                self._save(path)
            else:
                QMessageBox.information(self,"Save OK","BmeObj Has Been Saved.\n"
                                        "(No Change Found)")
        else:
            if self.isDirty():
                path_type = QFileDialog.getSaveFileName(\
                       self,"Save BME Object",
                       os.path.join( self.last_opened_folder, self.file_name ),
                       "BME Object File (*.bme);;All Files (*.*)") 
                path, type_ = path_type
                if not path:
                    return
                else:
                    self.updateLastOpenedFolder(path)
                    self._save(path)
            else:
                QMessageBox.warning(self, "Save Pass", "BmeObj Has No Change,\n"
                                    "Saving It Is Not Needed.")

    def actSaveAs(self):
        path_type = QFileDialog.getSaveFileName(\
                self, "Save BME Object",
                os.path.join(self.last_opened_folder, self.file_name),
                "BME Object file (*.bme);;All Files (*.*)")

        path, type_ = path_type
        if not path:
            return
        else:
            self.updateLastOpenedFolder(path)
        self._save(path)  

    def actOpen(self):

        path_type = QFileDialog.getOpenFileName(
            self, "Load BME Object",
            self.last_opened_folder,
            "BME Object file (*.bme *.db);;All Files (*.*)"
            )
        path, type_ = path_type
        if not path:
            return
        else:
            self.updateLastOpenedFolder(path)
            f = open(path , 'rb')
            #upkr = cPickle.Unpickler( f )
            upkr = pickle.Unpickler(f)
            #processBmeObj
            try:
                if not self.bmeobj.load(upkr):#nic):
                    QMessageBox.critical(self, "BME Load Error","can not find path")
                    return
            except DBPERMISSIONSERROR:
                QMessageBox.critical(self, "PermissionsError", "Please Make Sure You Have "
                                     "The Permission To Read That File.\nFile Opening Failed.")
                return

            self.file_path, self.file_name = os.path.split(path)
            self.dirty = False
            self.has_file = True

            self.setWindowTitle( self.file_name +" - "+self.WINDOW_TITLE )

            self.stage = upkr.load()
            upkr_crs = upkr.load()
            self.use_crs = upkr.load()
            if self.useCrs():
                if not self.crs.createFromWkt( upkr_crs ):
                    QMessageBox.warning( self, 'CRS cannot be recognized',
                                         'The Coordinate Reference System Cannot Be Read, Select It Manually')
                    while True:
                        self.crsdlg = QgsGenericProjectionSelector(self)
                        if self.crsdlg.exec_():
                            selected_crs = QgsCoordinateReferenceSystem( self.crsdlg.selectedCrsId(),
                                                         QgsCoordinateReferenceSystem.InternalCrsId )
                            projString = selected_crs.toProj()
                            if projString == u"":
                                QMessageBox.critical(self, self.tr("Error"), self.tr("No Valid CRS selected"))
                                continue
                            else:
                                self.crs.createFromProj(projString)
                                if self.crs.isValid():
                                    QMessageBox.information(self, "OK","Setting Data CRS Done.")
                                    break #should be
                                else:
                                    QMessageBox.critical(self, "very strange error","please contact me.")
                                    continue
                        else:
                            QMessageBox.critical(self, self.tr("Error"), self.tr("No Valid CRS selected"))
                            continue
            self.estimated_data_source_type = upkr.load()
            self.spatial_only = upkr.load()
            upkr_estimated_shape_file_type = upkr.load()
            self.estimated_shape_file_type = { 0: QgsWkbTypes.PointGeometry, 1: QgsWkbTypes.LineGeometry, 2:QgsWkbTypes.PolygonGeometry }[ upkr_estimated_shape_file_type ]
            self.estimated_shape_file_path = upkr.load()
            self.grid_param = upkr.load()
            
            self.vector_layer_data = upkr.load()
            self.has_add_raster_layer = upkr.load()
            self.has_mask = upkr.load()

            #load setting
            self.properties = upkr.load()
            color_dict = self.properties['color']
            time_dict = self.properties['time']
            symbol_dict = {'Hard': 'circle',
                           'Soft': 'equilateral_triangle',
                           'Estimated': 'regular_star'}

            #extract file at .stbme folder
            for key in self.vector_layer_data:
                shp_file_dict = self.vector_layer_data[key]
                if shp_file_dict:
                    for suffix in shp_file_dict:
                        shp_file_path = os.path.join( WORKING_PATH, key + 'Data' + suffix )
                        f_ = open(shp_file_path, 'wb')
                        f_.write(shp_file_dict[suffix])
                        f_.close()        
                    shp_file_path = os.path.join(WORKING_PATH, key + 'Data'+".shp")
                    if key == 'Background':
                        vlayer = self.addShapeFile( shp_file_path, 'BackgroundData', 'Background' )
                        self.moveLayerToGroup( vlayer, 'STBME_Vector' )
                    elif key == 'Mask':
                        self.mask_layer_path = shp_file_path
                    else:
                        if key == 'Estimated':
                            shp_type = self.estimated_shape_file_type
                            shp_path = self.estimated_shape_file_path
                        else:
                            shp_type = None
                            shp_path = None
                        rdr = stbme2qgis.getColorBarRenderer( color_dict['cmap'], 
                                                              symbol = symbol_dict[key],
                                                              min_ = color_dict['min'],
                                                              max_ = color_dict['max'],
                                                              shp_type = shp_type
                                                              )
                        lyr = stbme2qgis.addVector2QgisWithRenderer(self.iface, layer_path = shp_file_path,
                                                                    layer_name = key + 'Data', renderer = rdr)
                        if lyr is False:
                            QMessageBox.warning(self, "Find Group Fail", "Cannot Find STBME_Vector Group. Add to Top Level Instead.")
                        elif lyr is None: #lyr is valid
                            pass
                        elif lyr: #can use 
                            setattr( self, key.lower() +'_data_layer', lyr)

            #set Detrend Method
            self.detrend_method_name = self.bmeobj.trend.function
            detrend_method_index = self.ui.comboBox_detrendmethod.findText( self.detrend_method_name,
                                                                            Qt.MatchFixedString )
            self.ui.comboBox_detrendmethod.setCurrentIndex(detrend_method_index)   
            self.buttonsUpdate()

            #load shpfile and add
            self.mapCanvasFreeze( )

            f.close()

            if self.stage < 10:
                pass
            else:
                self.color_bar.update(m = color_dict['min'],
                                  M = color_dict['max'],
                                  cmap = color_dict['cmap'] )
                self.color_bar.show()

                if time_dict[ 'ratio_button_state' ]:
                    self.time_bar.ui.radioButton_mean.setEnabled( True )
                    self.time_bar.ui.radioButton_variance.setEnabled( True )
                else:
                    self.time_bar.ui.radioButton_mean.setEnabled( False )
                    self.time_bar.ui.radioButton_variance.setEnabled( False )
                    
                if time_dict[ 'ratio_button_value' ] == 'mean':
                    self.time_bar.ui.radioButton_mean.setChecked( True )
                elif time_dict[ 'ratio_button_value' ] == 'variance':
                    self.time_bar.ui.radioButton_variance.setChecked( True )
                else:
                    raise ValueError("MyError")

                self.time_bar.updateAll()
                self.time_bar.ui.horizontalSlider.setValue( time_dict[ 'index' ] )
            
                if self.isSpatialOnly():
                    self.time_bar.ui.label_time.setDisabled(True)
                    self.time_bar.ui.pushButton_previous.setDisabled(True)
                    self.time_bar.ui.horizontalSlider.setDisabled(True)
                    self.time_bar.ui.pushButton_next.setDisabled(True)
                    self.tool_view_data.action().setDisabled(True)
                    self.tool_histogram_view.action().setDisabled(True)
                self.time_bar.show()
                self.time_bar.draw()
            self.iface.mapCanvas().zoomToFullExtent()
            self.mapCanvasDefrost( )
            QMessageBox.information(self,"Load OK","BmeObj Has Been Loaded.")

    def actOption(self):
        from gui import options
        self.dlg=options.OptionDlg(self.iface,self)
        self.dlg.exec_()

    def actAbout(self):
        QMessageBox.about(self,u"about STAR-BME",u"STAR-BME (Space-Time Analysis Rendering with Bayesian Maximum Entropy)\n"
                          "Spatiotemporal Environmental Modeling Laboratory (STEMLAB), National Taiwan University\n"
                          "Version: "+ self.version )
        
    def actQuit(self):

        self.close()

    def _ignoreByAnswer(self, answer, event):
        if answer == QMessageBox.Yes:
            pass #Save and quit
        elif answer == QMessageBox.No:
            pass #Quit without save
        elif answer == QMessageBox.Cancel:
            event.ignore() #Cancel means should return to application
            
    def _askForSave(self):
        answer = QMessageBox.question(
            self,
            u"Save current file??",
            u"It seems like you are not saving the current file, save it??\n,",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel) 
        return answer
    
    def _save(self, path):
            
        #path is str (qgis2 was Qstring)

        if not path:
            return
        else:
            f = open(path, 'wb')
            pkr = pickle.Pickler(f)
            #save data to file
            self.bmeobj.save(pkr) #THIS WILL CLEAN SHELVE FILE FIRST,THEN SAVE DATA
    
            self.file_path, self.file_name = os.path.split(path)
            self.setWindowTitle(self.file_name + " - " + self.WINDOW_TITLE)
    
            self.dirty = False
            self.has_file = True

            pkr.dump(self.stage)
            pkr.dump(self.crs.toWkt())
            pkr.dump(self.use_crs)
            pkr.dump(self.estimated_data_source_type)
            pkr.dump(self.spatial_only)
            pkr.dump(int( self.estimated_shape_file_type ))
            pkr.dump(self.estimated_shape_file_path)
            pkr.dump(self.grid_param)
            #save QGIS's data
            pkr.dump(self.vector_layer_data)
            pkr.dump(self.has_add_raster_layer)
            pkr.dump(self.has_mask)
            

            colorbar_dict = {'min': self.color_bar.min,
                             'max': self.color_bar.max,
                             'cmap': self.color_bar.cmap}
            timebar_dict = { 'index': self.time_bar.current_index,
                             'ratio_button_state': self.time_bar.current_ratio_button_state,
                             'ratio_button_value': self.time_bar.current_ratio_button_value }
            pkr.dump( { 'color': colorbar_dict, 'time': timebar_dict } )
            
            f.close()
            QMessageBox.information(self,"Save OK","BmeObj Has Been Saved.")

    def _saveByAnswer(self, answer = QMessageBox.Yes):
        if answer == QMessageBox.Yes:
            self.actSave()
        elif answer == QMessageBox.No:
            pass
        elif answer == QMessageBox.Cancel:
            pass
            
    def isDirty(self):
        return self.dirty
    
    def isSpatialOnly(self):
        return self.spatial_only
    
    def setSpatialOnly(self,bool_):
        if type(bool_) == bool:
            self.spatial_only = bool_
        else:
            raise TypeError('need bool type.')
        
    def hasFile(self):
        return self.has_file

    def hasMask(self):
        return self.has_mask
    
    def hasAddRasterLayer(self):
        return self.has_add_raster_layer
    
    def useCrs(self):
        return self.use_crs
    
    def setUseCrs(self,bool_):
        if type(bool_) == bool:
            self.use_crs = bool_
            return True
        else:
            return False
        
    def _setDefaultByAnswer(self, answer):
        if answer == QMessageBox.Yes:
            self._setDefault()
        elif answer == QMessageBox.No:
            self._setDefault() #answer No means user want to
                               #set default without save
        elif answer == QMessageBox.Cancel:
            pass
        
    def setCurrentProgress(self, value = None, text = None):

        if text:
            self.ui.statusbar.showMessage(text)
        if value:
            self.ui.statusbar.qpgb.setValue(value)

        
    def setProgressRange(self, min, max):
        self.ui.statusbar.qpgb.setRange(int(min), int(max))

    def changeCrsSetting( self, bool_ ):
        if bool_:
            self.ui.pushButton_crs.setDisabled( True )
            self.setUseCrs( False )
            self.setStage(0)
            self.buttonsUpdate()
        else:
            self.ui.pushButton_crs.setDisabled( False )
            self.setUseCrs( False )
            self.setStage(-10)
            self.buttonsUpdate()
  
  
    def saveVectorLayer( self, vector_path, dict_key ):
        shp_dict = {}
        suffixs = ['.dbf','.prj','.qpj','.shp','.shx']
        for suffix in suffixs:
            vector_path_without_suffix = os.path.splitext(vector_path)[0]
            shp_file_path = vector_path_without_suffix + suffix 
            if os.path.exists( shp_file_path ):
                f_obj = open( shp_file_path, 'rb' )
                shp_dict[ suffix ] = f_obj.read()
                f_obj.close()
            else:
                print('Warning: {file_name} not found'.format( file_name = shp_file_path ))
                pass
        self.vector_layer_data[dict_key] = shp_dict  
        self.dirty = True
        return True
            
                
                          
    def addResultToQgis(self):
        
        def addShpFileDataToMain( data_type, has_data = True):
          
            def addFileToDict( file_path, dict_obj, key ):
                file_obj = open( file_path, "rb" )
                try:
                    dict_obj[key] = file_obj.read()
                finally:
                    file_obj.close()
            
            if has_data:
                shp_file_dict = {}
                shp_file_types = ['.dbf','.prj','.qpj','.shp','.shx']
                
                for shp_file_type in shp_file_types:
                    shp_file_path = os.path.join( WORKING_PATH, data_type + 'Data' + shp_file_type )
                    if os.path.exists(shp_file_path ):
                        addFileToDict(shp_file_path, shp_file_dict, shp_file_type)
                
                self.vector_layer_data[data_type] = shp_file_dict  
            else: 
                self.vector_layer_data[data_type] = {}
        
        self.mapCanvasFreeze()
        #change boundary if needed
        self.color_bar.min = min(self.color_bar.min,
                                 self.bmeobj.estimated_data.z_mean_min_without_nan)
        self.color_bar.max = max(self.color_bar.max,
                                 self.bmeobj.estimated_data.z_mean_max_without_nan)
        if stbme2qgis.saveAndAddVectorLayer2Qgis(self.iface, self,
                                                 self.bmeobj.estimated_data, "Estimated",
                                                 render_min = self.color_bar.min,
                                                 render_max = self.color_bar.max,
                                                 shp_type = self.estimated_shape_file_type,
                                                 shp_path = self.estimated_shape_file_path ):
            
            addShpFileDataToMain( 'Estimated', True )
        
            self.color_bar.update(self.color_bar.min , self.color_bar.max, self.color_bar.cmap)
            #change layer
            symbol_dict= {'hard':'circle','soft':'equilateral_triangle','estimated':'regular_star'}
            for flag in ['hard','soft']:
                lyr = getattr(self, flag+"_data_layer")
                if lyr:
                    rdr = stbme2qgis.getColorBarRenderer(self.color_bar.cmap, symbol_dict[flag],
                                                          self.color_bar.min, self.color_bar.max, 4)
                    rdr.setClassAttribute("Obs Val")
                    lyr.setRenderer(rdr)
                    #self.iface.legendInterface().refreshLayerSymbology(lyr)
                    root1 = QgsProject.instance().layerTreeRoot()
                    self.iface.layerTreeView().layerTreeModel().refreshLayerLegend(root1.findLayer(lyr))
                    stbme2qgis.collapseLayer( self.iface, lyr )
                    self.iface.mapCanvas().refreshAllLayers() 
            
            for flag in ['estimated']:
                shp_type = self.estimated_shape_file_type
                est_symbol = { QgsWkbTypes.PointGeometry: 'regular_star', QgsWkbTypes.LineGeometry: 'SimpleLine', QgsWkbTypes.PolygonGeometry: 'SimpleFill'}
                lyr = getattr(self, flag+"_data_layer")
                if lyr:
                    rdr = stbme2qgis.getColorBarRenderer(self.color_bar.cmap, est_symbol[shp_type],
                                                          self.color_bar.min, self.color_bar.max, 4,
                                                          shp_type = shp_type )
                    rdr.setClassAttribute("Obs Val")
                    lyr.setRenderer(rdr)
                    #self.iface.legendInterface().refreshLayerSymbology(lyr)
                    root2 = QgsProject.instance().layerTreeRoot()
                    self.iface.layerTreeView().layerTreeModel().refreshLayerLegend(root2.findLayer(lyr))
                    stbme2qgis.collapseLayer(self.iface, lyr )
                    self.iface.mapCanvas().refreshAllLayers() 
                    
            #update timebar
            self.time_bar.updateAll()
            self.time_bar.draw()
            
            #open draw estimated button
            self.time_bar.ui.radioButton_mean.setEnabled(True )
            self.time_bar.ui.radioButton_variance.setEnabled( True )
            self.time_bar.current_ratio_button_state = True

            self.mapCanvasDefrost()
            QMessageBox.information(self,"Done","Estimated Data were added to QGIS.")
        else:
            QMessageBox.critical(self,"Create File Error when creating shapefile","Error when creating shapefile")
            
        
    def addResultToQgisRaster(self):
        
        self.mapCanvasFreeze()
        #change boundary if needed
        self.color_bar.min = min(self.color_bar.min,
                                 self.bmeobj.estimated_data.z_mean_min_without_nan)
        self.color_bar.max = max(self.color_bar.max,
                                 self.bmeobj.estimated_data.z_mean_max_without_nan)
        
        if stbme2qgis.saveAndAddRasterLayer2Qgis(self.iface, self, self.bmeobj.estimated_data, index = 0,
                                                 shader_min = self.color_bar.min,
                                                 shader_max = self.color_bar.max ):

            #set flag
            self.has_add_raster_layer = True
            self.has_mask = False
            
            #update colorbar
            self.color_bar.update(self.color_bar.min , self.color_bar.max, self.color_bar.cmap)
            
            #show timebar      
            self.time_bar.updateAll()
            self.time_bar.draw()
            
            #open draw estimated button
            self.time_bar.ui.radioButton_mean.setEnabled(True )
            self.time_bar.ui.radioButton_variance.setEnabled( True )
            self.time_bar.current_ratio_button_state = True
            
            self.mapCanvasDefrost()
            QMessageBox.information(self,"Done","Raster was added to QGIS.")
            
    def addResultToQgisRasterWithMask(self):
        
        self.mapCanvasFreeze()
        masked_path_type = QFileDialog.getOpenFileName(
            self, "Load Mask Shape File",
            self.last_opened_folder, "Shape file (*.shp)")
        path, type_ = masked_path_type
        if not path: 
            return

        self.updateLastOpenedFolder(path)
        #change boundary if needed
        self.color_bar.min = min(self.color_bar.min,
                                 self.bmeobj.estimated_data.z_mean_min_without_nan)
        self.color_bar.max = max(self.color_bar.max,
                                 self.bmeobj.estimated_data.z_mean_max_without_nan)

        if stbme2qgis.saveAndAddRasterLayer2Qgis(
            self.iface, self, self.bmeobj.estimated_data, index = 0,
            shader_min = self.color_bar.min,
            shader_max = self.color_bar.max,
            masked = True, masked_file_path = path):

            #set flag
            self.has_add_raster_layer = True
            self.has_mask = True
            self.mask_layer_path = path
            
            #update colorbar
            self.color_bar.update(self.color_bar.min , self.color_bar.max, self.color_bar.cmap)
            
            #show timebar      
            self.time_bar.updateAll()
            self.time_bar.draw()
            
            #open draw estimated button
            self.time_bar.ui.radioButton_mean.setEnabled(True )
            self.time_bar.ui.radioButton_variance.setEnabled( True )
            self.time_bar.current_ratio_button_state = True
            
            
            #save mask layer
            self.saveVectorLayer(path, "Mask")
            
            self.mapCanvasDefrost()
            QMessageBox.information(self,"Done","Raster was added to QGIS.")
            
            
    def exportResultToFile(self):
        dlg = ExportFileDlg(self)
        if dlg.exec_():
            dlmt = dlg.delimiter
            sta_r = dlg.start_row
            file_n = dlg.file_path

            x = self.bmeobj.estimated_data.x
            y = self.bmeobj.estimated_data.y
            t = self.bmeobj.estimated_data.t
            mean = self.bmeobj.estimated_data.z_mean
            variance = self.bmeobj.estimated_data.z_variance

            try:
                #file_n = (file_n).split(',')
                file_n = str(file_n).split(',')
                out_f = open(os.path.normpath( ( file_n[0].strip('(').strip("'") )),"w")
            except ValueError:
                pass

            #row skip
            out_f.write("\n"*(sta_r - 1))

            #write title
            out_f.write(dlmt.join(['x','y','t','mean','variance'])+"\n")
            for data_list in zip(x,y,t,mean,variance):
                data_list = [str(i[0]) for i in data_list]
                out_f.write(dlmt.join(data_list)+"\n")

            out_f.close()
            QMessageBox.information(self,"Export Finished","The file has been exported!")

    def createCustomComposer( self ):
        if self.composer_view:
            # Re-open the existing layout designer
            designer = self.iface.openLayoutDesigner(self.composer_view)
            if designer:
                designer.view().window().show()
                designer.view().window().raise_()
        else:
            # Create a new print layout (QGIS 3 API)
            layout = QgsPrintLayout(QgsProject.instance())
            layout.initializeDefaults()
            layout.setName('STARBME Export')

            # Add a map item covering the page
            map_item = QgsLayoutItemMap(layout)
            map_item.setRect(20, 20, 20, 20)  # initial rect, will be resized
            page_size = layout.pageCollection().page(0).pageSize()
            map_item.attemptMove(QgsLayoutPoint(10, 10, QgsUnitTypes.LayoutMillimeters))
            map_item.attemptResize(QgsLayoutSize(
                page_size.width() - 20,
                page_size.height() - 20,
                QgsUnitTypes.LayoutMillimeters))
            map_item.setExtent(self.iface.mapCanvas().extent())
            layout.addLayoutItem(map_item)

            # Register layout with the project
            QgsProject.instance().layoutManager().addLayout(layout)
            self.composer_view = layout

            # Open the layout designer
            self.iface.openLayoutDesigner(layout)

            # Start the export workflow directly
            self.exportResultToPNG()
            return

    def exportResultToPNG( self ):

        def write_to_png( layout, output_filename ):
            exporter = QgsLayoutExporter(layout)
            settings = QgsLayoutExporter.ImageExportSettings()
            settings.dpi = layout.renderContext().dpi()
            if settings.dpi <= 0:
                settings.dpi = 300
            result = exporter.exportToImage(output_filename, settings)
            return result == QgsLayoutExporter.Success

        output_path = QFileDialog.getExistingDirectory( self, 'Output Path',
                                                        self.last_opened_folder )

        if not output_path:
            return
        else:

            self.updateLastOpenedFolder(output_path)

            # Re-fetch layout in case it was closed/recreated
            layout = self.composer_view
            if layout is None:
                QMessageBox.warning(self, "No Layout",
                    "No print layout found. Please create a layout first.")
                return

            # Refresh map items to current canvas extent
            for item in layout.items():
                if isinstance(item, QgsLayoutItemMap):
                    item.setExtent(self.iface.mapCanvas().extent())

            self.qpgd = QProgressDialog( self )
            self.qpgd.setWindowModality( Qt.ApplicationModal )
            self.qpgd.setWindowTitle( 'Export image...' )
            self.qpgd.setRange( 0 , self.bmeobj.estimated_data.t_grid[0].size + 1 )
            self.qpgd.setValue( 0 )
            self.qpgd.show()

            for idx, t_value in enumerate( self.bmeobj.estimated_data.t_grid[0] ):
                if self.qpgd.wasCanceled():
                    self.qpgd.setValue( self.qpgd.value() + 1 )
                    self.qpgd.reset()
                    self.qpgd.close()
                    return
                self.qpgd.setLabelText( 'Processing... {i}/{n}'.format( i = idx+1,
                                                                        n = self.bmeobj.estimated_data.t_grid[0].size +1 ))
                self.time_bar.draw( t_value )

                # Refresh map items to pick up layer changes
                for item in layout.items():
                    if isinstance(item, QgsLayoutItemMap):
                        item.refresh()

                out_file = os.path.join( output_path,
                                         'result_{ttt}.png'.format( ttt = idx) )
                if not write_to_png( layout, out_file ):
                    QMessageBox.warning(self, "Export Error",
                        "Failed to export: {}".format(out_file))

                self.qpgd.setValue( idx + 1 )

            self.time_bar._drawIfNeeded( )
            self.qpgd.setLabelText( 'Processing... {n}/{n}'.format( n = self.qpgd.value() + 1 ) )
            self.qpgd.setValue( self.qpgd.value() + 1 )
            self.qpgd.reset()
            self.qpgd.close()
            QMessageBox.information( self, 'Finished', 'All figures exported to:\n{}'.format(output_path))


    def cleanWorkSpaceGtiff(self):
        ##remove layers
        #for g_idx,group in enumerate( self.iface.legendInterface().groupLayerRelationship() ):
            #if group[0] == u'STBME_Raster':
                #for layer_id in group[1]:
                    #QgsMapLayerRegistry.instance().removeMapLayer( layer_id )

        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup('STBME_Raster')
        if group is not None:
            for child in group.children():
                group.removeChildNode(child)

        #remove dependency
        self.current_mean_layer = None
        self.current_variance_layer = None

        #removefiles
        root, dir_, files_ = next(os.walk( WORKING_PATH ))
        gtiff_list  = [ f for f in files_ if f.endswith( '.tif' ) ]
        for gtiff in gtiff_list:
            os.remove( os.path.join( root, gtiff ) )
            
        self.has_add_raster_layer = False
        self.has_mask = False
    
    def cleanWorkSpaceEstimatedLayer( self ):
        ##remove layers
        #for g_idx,group in enumerate( self.iface.legendInterface().groupLayerRelationship() ):
            #if group[0] == u'STBME_Vector':
                #for layer_id in group[1]:
                    #if unicode(layer_id).startswith( 'EstimatedData' ):
                        #QgsMapLayerRegistry.instance().removeMapLayer( layer_id )
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup('STBME_Vector')
        if group is not None:
            for child in group.children():
                if child.name() == 'EstimatedData' :
                    group.removeChildNode(child)

        # root = QgsProject.instance().layerTreeRoot()
        # group = root.findGroup('STBME_Raster')
        # group.removeLayer('EstimatedData')
        
        #remove dependency
        self.estimated_data_layer = None

        #removefiles
        root, dir_, files_ = next(os.walk( WORKING_PATH ))
        gtiff_list  = [ f for f in files_ if f.startswith( 'EstimatedData' ) ]

        for gtiff in gtiff_list:
            os.remove( os.path.join( root, gtiff ) )
        
        self.mean_layer_list = []
        self.current_mean_layer = None
        self.variance_layer_list = []
        self.current_variance_layer = None
         
        self.estimated_data_layer = None
        
    def cleanWorkSpaceHardSoftLayer( self ):

        #remove layers
        # for g_idx,group in enumerate(QgsProject.instance().layerTreeRoot().findLayers()):
        # #for g_idx,group in enumerate( self.iface.legendInterface().groupLayerRelationship() ):
        #     if group[0] == u'STBME_Vector':
        #         for layer_id in group[1]:
        #             if unicode(layer_id).startswith( ( 'HardData', 'SoftData' ) ):
        #                 QgsMapLayerRegistry.instance().removeMapLayer( layer_id )
        root1 = QgsProject.instance().layerTreeRoot()
        group = root1.findGroup('STBME_Vector')
        if group is not None:
            for child in group.children():
                if child.name() == 'HardData' or 'SoftData' :
                 #QgsProject.instance().removeMapLayer(child.layerId())
                    group.removeChildNode(child)

                #if child.name() == 'SoftData':
                    #group.removeChildNode(child)
        #     #root.removeChildNode(group)
        # root = QgsProject.instance().layerTreeRoot()
        # group = root.findGroup('STBME_Raster')
        # group.removeLayer('HardData')
        # group.removeLayer('SoftData')
        
        #first release layer
        self.hard_data_layer = None
        self.soft_data_layer = None

        #removefiles
        root, dir_, files_ = next(os.walk(WORKING_PATH))
        gtiff_list  = [f for f in files_ if f.startswith(('HardData', 'SoftData'))]
        for gtiff in gtiff_list:
            os.remove(os.path.join(root, gtiff))
        

    def updateLastOpenedFolder(self, folder_path):
        self.last_opened_folder = os.path.dirname(folder_path)

    def mapCanvasFreeze(self):
        self.iface.mapCanvas().freeze(True)
        
    def mapCanvasDefrost(self):
        self.iface.mapCanvas().freeze(False)
        self.iface.mapCanvas().refreshAllLayers() 
       
    def crossValidation( self ):
        if not self.cv_dlg:
            self.cv_dlg = CrossValidationDlg( self )
        
        self.cv_dlg.exec_()
    

class DetrendParamDlg(QDialog):
    def __init__(self,parent = None, title = ""):
        super(DetrendParamDlg,self).__init__(parent)
        self.setWindowTitle(title)
        #v left param
        self.param_container = []
        self.label_layout = QVBoxLayout()
        self.param_layout = QVBoxLayout()
        self.descr_layout = QVBoxLayout()
        
        #v right button
        v_layout = QVBoxLayout()
        okbtn = QPushButton("OK")
        v_layout.addWidget(okbtn)
        clbtn = QPushButton("Cancel")
        v_layout.addWidget(clbtn)
        v_layout.addStretch()
        
        # grid layout
        g_layout = QGridLayout()
        g_layout.addLayout(self.label_layout, 0, 0)
        g_layout.addLayout(self.param_layout, 0, 1)
        g_layout.addLayout(self.descr_layout, 0, 2)
        g_layout.setRowStretch(1, 1)
        
        #primary layout
        p_layout = QHBoxLayout()
        p_layout.addLayout(g_layout)
        p_layout.addLayout(v_layout)
        
        self.setLayout(p_layout)
        
        okbtn.clicked.connect( self.accept )
        clbtn.clicked.connect( self.reject )
        
    def addParameter(self, label, var_type, descript, default = ""):
        label = QLabel(label)
        input = QLineEdit(default)
        descr = QLabel(descript)
        self.label_layout.addWidget(label)
        self.param_layout.addWidget(input)
        self.descr_layout.addWidget(descr)
        self.param_container.append((input,var_type))
    
    def addParameter2( self, label, input_obj, descript, get_method ):
        label = QLabel(label)
        input = input_obj
        descr = QLabel(descript)
        self.label_layout.addWidget(label)
        self.param_layout.addWidget(input)
        self.descr_layout.addWidget(descr)
        self.param_container.append((input,get_method))
        
    def returnParameters(self):
        # return tuple(map(lambda input_obj, get_method : get_method( input_obj ), self.param_container))
        return tuple(map(lambda x: x[1](x[0]), self.param_container))
        # return map(lambda ( input_obj, get_method ): get_method( input_obj ), self.param_container)

from setdata import LoadFileDlg
class ExportFileDlg(LoadFileDlg):
    def __init__(self, parent = None):
        super(ExportFileDlg,self).__init__("Noused Flag", parent)
        
        self.setWindowTitle("Export File Dialog")
        self.ui.widget_filename.hide()
        self.ui.label_2.setText( 'Start to write at row')
        self.adjustSize()

    def browse(self):
        file_path_temp_type = QFileDialog.getSaveFileName(
            self,"Select Export File Name",
            self.parent().last_opened_folder + "/my_result.csv",
            self.accept_file_type)
        path, type_ = file_path_temp_type
        return path

    def ok(self):

        #process needed data
        #file_path
        #self.file_path
        file_path_temp = self.browse()
        if not file_path_temp:
            return # cancel
        else:
            self.parent().updateLastOpenedFolder( file_path_temp )
            self.file_path = file_path_temp
        
            #delimiter
            label_delimiter = self.ui.buttonGroup.checkedButton().text()
            if label_delimiter == u"Comma":
                self.delimiter = ","
            elif label_delimiter == u"Space":
                self.delimiter = " "
            elif label_delimiter == u"Tab":
                self.delimiter = "\t"
            elif label_delimiter == u"Others":
                self.delimiter = str(self.ui.lineEdit_others.text())
            
            #start_row
            self.start_row = self.ui.spinBox_row.value()
              
            self.accept()
        

from ui.ui_CrossValidationDlg import Ui_CrossValidationDlg
from ui.ui_MplDlg import Ui_MplDlg
from lib.rawdata2griddata import rawdata2griddata_list
class CrossValidationDlg( QDialog, Ui_CrossValidationDlg ):
    def __init__( self, parent = None):
        super( CrossValidationDlg, self ).__init__( parent )
        self.m_dlg = parent
        self.bmeobj = parent.bmeobj

        self.mpl_dlg_s = None
        self.mpl_dlg_t = None

        self.ui = Ui_CrossValidationDlg( )
        self.ui.setupUi( self )

        # Populate worker count combo box
        from multiprocessing import cpu_count
        _max_cpu = cpu_count()
        for i in range(1, _max_cpu + 1):
            self.ui.comboBox_worker_n.addItem(str(i))
        # Default to all available CPUs
        self.ui.comboBox_worker_n.setCurrentIndex(_max_cpu - 1)

        self.ui.pushButton_run.clicked.connect( self.run )
        self.ui.pushButton_cancel.clicked.connect( self.reject )
        self.ui.buttonGroup.buttonClicked[QAbstractButton].connect( self.updateSpinBox )
        self.ui.pushButton_spatial_result.clicked.connect( self.viewSpatial )
        self.ui.pushButton_temporal_result.clicked.connect( self.viewTemporal )

        self.updateUi()

        if self.bmeobj.hasCrossValidation():
            self.sample_type = self.bmeobj.cross_validation_sample_type
            self.ui.pushButton_spatial_result.setEnabled( True )
            self.ui.pushButton_temporal_result.setEnabled( True )

    def getBnd( self, data_obj ):
        return list(map(lambda ts,xy,minmax,data_obj = data_obj:\
                   eval("data_obj."+ts+"_"+xy+"_"+minmax),
                   *zip(
                       ("time","x","min"),
                       ("time","x","max"),
                       ("time","y","min"),
                       ("time","y","max"),
                       ("station","t","min"),
                       ("station","t","max")
                      )
                   ))

    def setTxt( self, hard, soft ):
        if hard and soft:
            hxmin, hxmax, hymin, hymax, htmin, htmax = self.getBnd( self.bmeobj.hard_data )
            sxmin, sxmax, symin, symax, stmin, stmax = self.getBnd( self.bmeobj.soft_data )
            xmin = min(hxmin,sxmin)
            xmax = max(hxmax,sxmax)
            ymin = min(hymin,symin)
            ymax = max(hymax,symax)
            tmin = min(htmin,stmin)
            tmax = max(htmax,stmax)

        elif hard:
            hxmin, hxmax, hymin, hymax, htmin, htmax = self.getBnd( self.bmeobj.hard_data )
            xmin = hxmin
            xmax = hxmax
            ymin = hymin
            ymax = hymax
            tmin = htmin
            tmax = htmax

        elif soft:
            sxmin, sxmax, symin, symax, stmin, stmax = self.getBnd( self.bmeobj.soft_data )
            xmin = sxmin
            xmax = sxmax
            ymin = symin
            ymax = symax
            tmin = stmin
            tmax = stmax
        

        self.ui.lineEdit_xmin.setText(str(xmin))
        self.ui.lineEdit_xmax.setText(str(xmax))
        self.ui.lineEdit_ymin.setText(str(ymin))
        self.ui.lineEdit_ymax.setText(str(ymax))
        self.ui.lineEdit_tmin.setText(str(tmin))
        self.ui.lineEdit_tmax.setText(str(tmax))

    def updateUi( self ):
        self.count_h = self.bmeobj.hard_data.x.size
        self.count_s = self.bmeobj.soft_data.x.size
        count_h, count_s = self.count_h, self.count_s
        self.ui.label_n.setText( "( Hard Data:{h_n}  Soft Data:{s_n} )".format( h_n = count_h, s_n = count_s ) )

        if self.bmeobj.hard_data.hasData():
            self.ui.radioButton_hard.setEnabled( True )
            self.ui.radioButton_hard.setChecked( True )
            xm_h = self.bmeobj.hard_data.x.min()
            if self.bmeobj.soft_data.hasData(): #both hard and soft
                self.ui.radioButton_soft.setEnabled( True)
                self.ui.radioButton_both.setEnabled( True )

                self.ui.spinBox.setRange( 1, count_h )
                self.ui.spinBox.setValue( count_h )

                self.setTxt( hard = True, soft = True )
            else: # only hard 
                self.ui.radioButton_soft.setDisabled( True )
                self.ui.radioButton_both.setDisabled( True )

                self.ui.spinBox.setRange( 1, count_h )
                self.ui.spinBox.setValue( count_h )

                self.setTxt( hard = True, soft = False )


        else: # only soft
            self.ui.radioButton_hard.setDisabled( True )
            self.ui.radioButton_soft.setChecked( True )
            self.ui.radioButton_both.setDisabled( True )

            self.ui.spinBox.setRange( 1, count_s )
            self.ui.spinBox.setValue( count_s )

            self.setTxt( hard = False, soft = True )

        self.ui.groupBox_boundary.setChecked(False)

    def updateSpinBox( self, btn ):
        if btn.objectName() ==  u'radioButton_hard':
            self.ui.spinBox.setRange( 1, self.count_h )
            if not self.ui.groupBox_boundary.isChecked():
                self.setTxt( hard = True, soft = False )
        elif btn.objectName() ==  u'radioButton_soft':
            self.ui.spinBox.setRange( 1, self.count_s )
            if not self.ui.groupBox_boundary.isChecked():
                self.setTxt( hard = False, soft = True )
        elif btn.objectName() ==  u'radioButton_both':
            self.ui.spinBox.setRange( 1, self.count_h + self.count_s )
            if not self.ui.groupBox_boundary.isChecked():
                self.setTxt( hard = True, soft = True )

    def run( self ):
        def setArg(t, t_n, n):
            try:
                v = eval("self.ui.lineEdit_"+n).text()
                if t == int:
                    if float(v) - t(float(v)) == 0.0:
                        pass
                    else:
                        raise ValueError
                    v = t(float(v))
                elif t == float:
                    v = t(v)
                setattr(self,n,v)
                return True
            except ValueError:
                QMessageBox.critical(self, "Error",
                                     n.capitalize() +"'s Input Type Should be "+ t_n)
                return False
            
        self.sample_type = (self.ui.buttonGroup.checkedButton().objectName())[-4:] # 'hard' or 'soft' or 'both'
        if self.ui.groupBox_boundary.isChecked():
            if not setArg(float,"Float","xmin"):
                return 
            if not setArg(float,"Float","ymin"):
                return 
            if not setArg(float,"Float","tmin"):
                return 
            if not setArg(float,"Float","xmax"):
                return 
            if not setArg(float,"Float","ymax"):
                return 
            if not setArg(float,"Float","tmax"):
                return 
            self.sample_boundary = ( self.xmin, self.xmax, self.ymin, self.ymax, self.tmin, self.tmax )
        else:
            self.sample_boundary = None
        
        self.sample_size = self.ui.spinBox.value()

        sample_number = self.sample_size
        boundary = self.sample_boundary
        use_data = str( self.sample_type )
        detrend_method = self.bmeobj.trend.function
        detrend_parameter = self.bmeobj.trend.parameters
        selected_n_workers = int(self.ui.comboBox_worker_n.currentText())

        self.qpgd = QProgressDialog(self)
        self.qpgd.setWindowModality(Qt.WindowModal)
        self.qpgd.setMinimumDuration(0)   # show immediately, don't wait 4s
        
        self.bmeobj.setProgressDialog(self.qpgd)
        self.bmeobj.setProgressAutoClose(False)
        self.bmeobj.estimated_data.setProgressDialog(self.qpgd)
        self.bmeobj.estimated_data.setProgressAutoClose(False)

        result = self.bmeobj.crossValidation(
            sample_number, boundary, use_data,
            detrend_method, detrend_parameter,
            n_workers=selected_n_workers
        )

        self.bmeobj.setProgressAutoClose(True)
        self.bmeobj.progress_dialog.close()
        self.bmeobj.estimated_data.setProgressAutoClose(True)
        self.bmeobj.estimated_data.progress_dialog.close()
        if result:
            res_rmse, res_mean, res_std, res_25p, res_median, res_75p, res_min, res_max = result
            self.bmeobj.has_cross_validation = True
            self.bmeobj.cross_validation_sample_type = use_data
            self.ui.pushButton_spatial_result.setEnabled( True )
            self.ui.pushButton_temporal_result.setEnabled( True )
            QMessageBox.information( self, "Done", "Cross validation completed.\n"
                                                   "Error statistics (observed \u2212 predicted):\n"
                                                   "  RMSE: {rmse:.4f}\n"
                                                   "  Mean error: {mean:.4f}\n"
                                                   "  Std. dev. of error: {std:.4f}\n"
                                                   "  25th percentile: {p25:.4f}\n"
                                                   "  Median error: {median:.4f}\n"
                                                   "  75th percentile: {p75:.4f}\n"
                                                   "  Min error: {min:.4f}\n"
                                                   "  Max error: {max:.4f}\n"
                                                   "\nValid samples: {n_valid} / {n_total}".format(
                                                       rmse = res_rmse, mean = res_mean, std = res_std,
                                                       p25 = res_25p, median = res_median, p75 = res_75p,
                                                       min = res_min, max = res_max,
                                                       n_valid = sum(1 for x in (res_rmse,) if not numpy.isnan(x)) and
                                                                 int(numpy.count_nonzero(~numpy.isnan(
                                                                     self.bmeobj.hard_data.z_cv if use_data == 'hard'
                                                                     else self.bmeobj.soft_data.z_cv if use_data == 'soft'
                                                                     else numpy.vstack((self.bmeobj.hard_data.z_cv,
                                                                                        self.bmeobj.soft_data.z_cv))
                                                                 ))),
                                                       n_total = sample_number) )

    def viewSpatial( self ):

        # Always recreate so flags match the *current* CV run
        # (reusing a stale dialog keeps has_hard/has_soft from a
        #  previous run, causing colorbar errors).
        self.mpl_dlg_s = MplDlg( self, 'space' )
        self.mpl_dlg_s.refreshCanvas('rmse')

    def viewTemporal( self ):

        # Always recreate — same rationale as viewSpatial
        self.mpl_dlg_t = MplDlg( self, 'time' )
        self.mpl_dlg_t.refreshCanvas('rmse')
        
from ui.ui_MplDlg import Ui_MplDlg
class MplDlg( QDialog, Ui_MplDlg ):
    def __init__( self, parent, name ):
        super( MplDlg,self ).__init__( parent )
        
        self.ui = Ui_MplDlg()
        self.ui.setupUi( self )

        self.name = name
        self.POINT_SIZE = 60
        self.cmap = matplotlib.cm.jet
        self.sample_type = parent.sample_type
        self.bmeobj = parent.bmeobj

        #check data
        self.has_hard = False
        self.has_soft = False
        self.has_value_hard = False
        self.has_value_soft = False

        if self.sample_type in [ 'hard', 'both' ]:
            self.has_hard = True
        if self.sample_type in [ 'soft', 'both' ]:
            self.has_soft = True

        if self.has_hard:
            if not numpy.isnan( self.bmeobj.hard_data.z_cv_grid ).all():
                self.has_value_hard = True
        if self.has_soft:
            if not numpy.isnan( self.bmeobj.soft_data.z_cv_grid ).all():
                self.has_value_soft = True

        self.canvas_title = {'rmse': 'RMSE',
                      'mean': 'residual mean',
                      'standard deviation': 'residual standard deviation',
                      '25 percentile': '25 percentile',
                      'median': 'residual medians',
                      '75 percentile': '75 percentile',
                      'min': 'residual min',
                      'max': 'residual max'}

        self.ui.comboBox.currentIndexChanged[str].connect( self.refreshCanvas )

    def refreshCanvas( self, combobox_str ):

        #clear content
        self.ui.mplWidget.canvas.fig.clear()
        self.ui.mplWidget.canvas.ax = self.ui.mplWidget.canvas.fig.add_subplot(111)

        if self.name == 'space':
            self.drawSpace( value = combobox_str.lower() )
        elif self.name == 'time':
            self.drawTime( value = combobox_str.lower() )
        
        self.show()
    def drawSpace( self, value ):
        def _init_station_value( data_obj ):
            station_value = numpy.empty( ( data_obj.z_cv_grid.shape[0], 1 ) )
            station_value[:] = numpy.nan
            return station_value

        def _set_value( data_obj, flag, value_type ):
            if getattr( self, 'has_{f}'.format( f = flag) ): #has_hard
                if getattr( self, 'has_value_{f}'.format( f = flag ) ): #has value
                    error = data_obj.z_grid - data_obj.z_cv_grid
                    if value_type == 'rmse':
                        #calculate root mean square error
                        rmse = error ** 2 #error and square
                        for idx, station in enumerate( rmse ):
                            station_count =  (~numpy.isnan( station )).sum()
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.sqrt( numpy.nansum( station ) / station_count ) #mean and root

                    elif value_type == 'mean':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.mean( station ) #mean and root

                    elif value_type == 'standard deviation':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.std( station ) #std

                    elif value_type == '25 percentile':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.percentile( station, 25 ) #25 percentile

                    elif value_type == 'median':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.median( station ) #median

                    elif value_type == '75 percentile':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.percentile( station, 75 ) #75 percentile

                    elif value_type == 'min':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.min( station ) #min

                    elif value_type == 'max':
                        for idx, station in enumerate( error ):
                            station = station[~numpy.isnan( station )]
                            station_count = len( station )
                            if station_count: # has value
                                getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[idx][0] = \
                                numpy.max( station ) #max

                    else:
                        raise ValueError( 'no supportted type' )

        def _start_plot( data_obj, flag, marker ):
            if getattr( self, 'has_{f}'.format( f = flag ) ):
                x = data_obj.s_grid[:,0]
                y = data_obj.s_grid[:,1]
                v = getattr( self, 'station_value_{f}'.format( f = flag[0] ) )[:,0]
                #get x,y,v of Nan
                v_nan = v[ numpy.isnan( v ) ]
                if v_nan.size:
                    x_nan = x[ numpy.isnan( v ) ]
                    y_nan = y[ numpy.isnan( v ) ]
                    self.ui.mplWidget.canvas.ax.scatter( x_nan, y_nan, c = 'w', marker = marker, s = self.POINT_SIZE )
                    self.ui.mplWidget.canvas.ax.scatter( x_nan, y_nan, c = 'k', marker = 'x', s = self.POINT_SIZE )

                v_no_nan = v[ ~numpy.isnan( v ) ]
                if v_no_nan.size:
                    x_no_nan = x[ ~numpy.isnan( v ) ]
                    y_no_nan = y[ ~numpy.isnan( v ) ]
                    setattr( self, 'line_{f}'.format( f = flag ), self.ui.mplWidget.canvas.ax.scatter( x_no_nan, y_no_nan, c = v_no_nan, s = self.POINT_SIZE, cmap = self.cmap ) )
                    setattr( self, 'vmin_{f}'.format( f = flag ), getattr( self, 'line_{f}'.format( f = flag ) ).get_clim()[0])
                    setattr( self, 'vmax_{f}'.format( f = flag ), getattr( self, 'line_{f}'.format( f = flag ) ).get_clim()[1])

        #initial value ( row by 1 )
        self.station_value_h = _init_station_value( self.bmeobj.hard_data )
        self.station_value_s = _init_station_value( self.bmeobj.soft_data )

        _set_value( self.bmeobj.hard_data, 'hard', value )
        _set_value( self.bmeobj.soft_data, 'soft', value )

        vmin_hard, vmin_soft = None, None
        vmax_hard, vmax_soft = None, None

        _start_plot( self.bmeobj.hard_data, 'hard', 'o' )
        _start_plot( self.bmeobj.soft_data, 'soft', '^' )

        #change color limit if needed
        _has_line_hard = hasattr(self, 'line_hard')
        _has_line_soft = hasattr(self, 'line_soft')
        cb = None

        if _has_line_hard and _has_line_soft:
            vmin = min( i for i in ( self.vmin_hard, self.vmin_soft ) if i is not None )
            vmax = max( i for i in ( self.vmax_hard, self.vmax_soft ) if i is not None )
            self.line_hard.set_clim( vmin, vmax )
            self.line_soft.set_clim( vmin, vmax )
            cb = self.ui.mplWidget.canvas.fig.colorbar(
                self.line_soft, ax=self.ui.mplWidget.canvas.ax )
        elif _has_line_hard:
            cb = self.ui.mplWidget.canvas.fig.colorbar(
                self.line_hard, ax=self.ui.mplWidget.canvas.ax )
        elif _has_line_soft:
            cb = self.ui.mplWidget.canvas.fig.colorbar(
                self.line_soft, ax=self.ui.mplWidget.canvas.ax )

        self.ui.mplWidget.canvas.ax.set_aspect('equal')
        #add title and label
        self.ui.mplWidget.canvas.ax.set_title( 'Spatial distribution of cross-validation results in terms of {title}'.format( title = self.canvas_title[value] ) )
        self.ui.mplWidget.canvas.ax.set_xlabel( 'Longitude ( x-coordinate )' )
        self.ui.mplWidget.canvas.ax.set_ylabel( 'Latitude ( y-coordinate )' )
        if cb is not None:
            cb.ax.set_ylabel(self.canvas_title.get(value, value))

        self.ui.mplWidget.canvas.draw()

    def drawTime(self, value):

        if self.has_hard and self.has_soft: #use both hard and soft
            if self.has_value_hard and self.has_value_soft: #need combined_z_grid
                x_hs = numpy.vstack((self.bmeobj.hard_data.x, self.bmeobj.soft_data.x))
                y_hs = numpy.vstack((self.bmeobj.hard_data.y, self.bmeobj.soft_data.y))
                t_hs = numpy.vstack((self.bmeobj.hard_data.t, self.bmeobj.soft_data.t))
                z_hs = numpy.vstack((self.bmeobj.hard_data.z, self.bmeobj.soft_data.z))
                z_cv_hs = numpy.vstack((self.bmeobj.hard_data.z_cv, self.bmeobj.soft_data.z_cv))

                s_grid, t_grid, ( z_grid, z_cv_grid ) = rawdata2griddata_list( x_hs, y_hs, t_hs, [ z_hs, z_cv_hs ] )
                time_value = numpy.empty( ( z_cv_grid.shape[1], 1 ) )
            elif self.has_value_hard:
                s_grid, t_grid, ( z_grid, z_cv_grid ) = self.bmeobj.hard_data.s_grid, self.bmeobj.hard_data.t_grid, ( self.bmeobj.hard_data.z_grid, self.bmeobj.hard_data.z_cv_grid )
                time_value = numpy.empty( ( self.bmeobj.hard_data.z_cv_grid.shape[1], 1 ) )
            elif self.has_value_soft:
                s_grid, t_grid, ( z_grid, z_cv_grid ) = self.bmeobj.soft_data.s_grid, self.bmeobj.soft_data.t_grid, ( self.bmeobj.soft_data.z_grid, self.bmeobj.soft_data.z_cv_grid )
                time_value = numpy.empty( ( self.bmeobj.soft_data.z_cv_grid.shape[1], 1 ) )
            
            time_value[:] = numpy.nan

        elif self.has_hard: #only hard
            #get hard value
            #check has value
            if self.has_value_hard: #has value

                time_value = numpy.empty( ( self.bmeobj.hard_data.z_cv_grid.shape[1], 1 ) )
                time_value[:] = numpy.nan
                #calculate root mean square error
                z_grid = self.bmeobj.hard_data.z_grid
                z_cv_grid = self.bmeobj.hard_data.z_cv_grid
            else:
                raise ValueError( 'very strange error' )

            s_grid = self.bmeobj.hard_data.s_grid
            t_grid = self.bmeobj.hard_data.t_grid

        elif self.has_soft: #only soft
            #get soft value
            #check has value
            if self.has_value_soft: #has value
                time_value = numpy.empty( ( self.bmeobj.soft_data.z_cv_grid.shape[1], 1 ) )
                time_value[:] = numpy.nan
                #calculate root mean square error
                z_grid = self.bmeobj.soft_data.z_grid
                z_cv_grid = self.bmeobj.soft_data.z_cv_grid
            else:
                raise ValueError( 'very strange error' )

            s_grid = self.bmeobj.soft_data.s_grid
            t_grid = self.bmeobj.soft_data.t_grid

        #get value


        #calculate root mean square error (RMSE), Mean, Standard Deviation, Median, Min Value, Max Value
        error_all = z_grid - z_cv_grid

        if value == 'rmse':
            rmse = error_all ** 2 #error and square
            
            for idx, time in enumerate( rmse.T ):
                time_count =  (~numpy.isnan( time )).sum()
                if time_count: # has value
                    time_value[idx][0] = numpy.sqrt( numpy.nansum( time ) / time_count ) #mean and root
        elif value == 'mean':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.mean(time)#mean

        elif value == 'standard deviation':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.std(time)#standard deviation

        elif value == '25 percentile':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.percentile(time, 25)#25 percentile

        elif value == 'median':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.median(time)#median

        elif value == '75 percentile':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.percentile(time, 75)#75 percentile

        elif value == 'min':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.min(time)#min

        elif value == 'max':
            for idx, time in enumerate( error_all.T ):
                time = time[~numpy.isnan( time )] #flat to 1D
                time_count =  len( time )
                if time_count: # has value
                    time_value[idx][0] =  numpy.max(time)#max

        else:
            raise ValueError('no supported type')

        #start plot
        x = t_grid[0]
        y = time_value[:,0]
        #get x,y of Nan
        line = self.ui.mplWidget.canvas.ax.plot( x, y, 'bo')
        self.ui.mplWidget.canvas.ax.grid(True)
        #add title and label
        self.ui.mplWidget.canvas.ax.set_title( 'Temporal distribution of cross-validation results in terms of {title}'.format( title = self.canvas_title[value] ) )
        self.ui.mplWidget.canvas.ax.set_xlabel( 'Time step' )
        self.ui.mplWidget.canvas.ax.set_ylabel( '{title}'.format( title = self.canvas_title[value] ) )

        self.ui.mplWidget.canvas.draw()

def DEBUGDLG(var):
    QMessageBox.information(self, "debug", str(var))




welcome.close()

