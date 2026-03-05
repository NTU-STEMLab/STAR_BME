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
import numpy

import stbme2qgis

from ui.ui_TimeBarDockWgt import Ui_TimeBarDockWgt

import star_variable
WORKING_PATH = star_variable.WORKING_PATH

class TimeBarDockWgt(QDockWidget, Ui_TimeBarDockWgt):
    def __init__(self, parent):
        super(TimeBarDockWgt,self).__init__(parent)
        
        self.ui = Ui_TimeBarDockWgt()
        self.ui.setupUi(self)
        
        self.current_drawing_state = False
        self.current_index = 0
        self.current_ratio_button_state = False
        self.current_ratio_button_value = 'mean' # and 'variance'

        #Get bmeobj from mainwindow
        self.bmeobj = parent.bmeobj
        
        #rename
        self.main = parent
        self.parent = parent
        self.iface = parent.iface
        
        self.ui.pushButton_next.clicked.connect(self._next)
        self.ui.pushButton_previous.clicked.connect(self._previous)
        self.ui.pushButton_draw.clicked.connect(self.draw)
    
        self.ui.horizontalSlider.canDrawNow.connect( self._drawIfNeeded )
        self.ui.horizontalSlider.valueChanged[int].connect( self._updateLabel )
        self.ui.checkBox_autodraw.toggled[bool].connect( self._drawIfNeeded )
        self.ui.radioButton_mean.toggled[bool].connect( self._drawIfNeeded )
    
    def _next(self):
        if self.isDrawing():
            return
        
        now_value = self.ui.horizontalSlider.value()
        if now_value == self.ui.horizontalSlider.maximum():
            pass
        else:
            self.ui.horizontalSlider.setValue(now_value+1)
            self._drawIfNeeded()
        
    def _previous(self):
        if self.isDrawing():
            return
        
        now_value = self.ui.horizontalSlider.value()
        if now_value == self.ui.horizontalSlider.minimum():
            pass
        else:
            self.ui.horizontalSlider.setValue(now_value-1)
            self._drawIfNeeded()
        
    def _drawIfNeeded(self):
        if self.isAutoDraw():
            if self.isDrawing():
                pass
            else:
                self.draw()
        else:
            pass
            
    def draw(self, assign_t_value = None, null_value = -9999.0):
        self.main.mapCanvasFreeze()
        def updateColorBar():
            min_ = getattr(self.bmeobj.estimated_data,"z_"+flag+"_min_without_nan")
            max_ = getattr(self.bmeobj.estimated_data,"z_"+flag+"_max_without_nan")
            self.parent.color_bar.update(min_,max_)
            
        def changeVectorAttributeValueIfNeeded( t_list, t_value, lyr, z_grid ):   
            #find data index
            try:
                t_index = t_list.index(t_value)
            except ValueError:
                t_index = -1
                
            if t_index != -1:
                value = z_grid[:,t_index].tolist() # b/s QVariant can not use numpy.float64
                if lyr: #is layer or None
                    lyr.startEditing()
                    map_dict = {}
                    for ftr_id in range( len( value ) ):
                        val = value[ ftr_id ]
                        if numpy.isnan( val ):
                            val = null_value
                        val_dict = { 0: val }
                        map_dict[ ftr_id ] = val_dict
                    lyr.dataProvider().changeAttributeValues( map_dict )
                    lyr.commitChanges()
                    
                    #show layer
                    _node = QgsProject.instance().layerTreeRoot().findLayer(lyr)
                    if _node is not None:
                        _node.setItemVisibilityChecked(True)
            else:
                if lyr: #is layer or None
                    _node = QgsProject.instance().layerTreeRoot().findLayer(lyr)
                    if _node is not None:
                        _node.setItemVisibilityChecked(False)
        
        def changeVectorSymbolsForVairance( lyr ):
            if lyr:      
                #make a symbol
                symbol = QgsSymbol.defaultSymbol( QgsWkbTypes.PointGeometry )
                symbol.setColor( QColor( 0,0,0 ) )
                rdr = QgsSingleSymbolRenderer( symbol )
                lyr.setRenderer( rdr )
        
        if self.isDrawing():
            return

        self.qpgd = QProgressDialog(self)
        self.qpgd.setWindowModality(Qt.WindowModal)
        self.qpgd.setCancelButton(None)
        self.qpgd.setLabelText("Please Wait a Moment...")
        self.qpgd.setValue(0)
        
        try:  # ensure progress dialog & canvas are always cleaned up
            index = self.ui.horizontalSlider.value()
            if assign_t_value:
                try:
                    tt_idx = self.t_all.index( assign_t_value )
                except ValueError as e:
                    raise e
                t_value = self.t_all[ tt_idx ]
            else:
                t_value = self.t_all[ index ]
            
            if self.ui.buttonGroup.checkedButton() == self.ui.radioButton_mean:
                if not self.current_ratio_button_value == 'mean': 
                    #renew colorbar
                    min_ = self.bmeobj.estimated_data.z_mean_min_without_nan
                    max_ = self.bmeobj.estimated_data.z_mean_max_without_nan
                    cmap_ = self.parent.color_bar.cmap
                    self.parent.color_bar.update( min_, max_, cmap_)
                    
                    #change layer renderer
                    symbol_dict= {'hard':'circle','soft':'equilateral_triangle','estimated':'regular_star'}
                    for flag in ['hard','soft']:
                        lyr = getattr(self.parent,flag+"_data_layer")
                        stbme2qgis.changeVectorLayerRenderer(self.parent.iface, self.parent, lyr,
                                                         symbol_dict[flag], cmap_, min_, max_, 4)
                    for flag in ['estimated']:
                        shp_type = self.main.estimated_shape_file_type
                        est_symbol = { QgsWkbTypes.PointGeometry: 'regular_star', QgsWkbTypes.LineGeometry: 'SimpleLine', QgsWkbTypes.PolygonGeometry: 'SimpleFill'}
                    
                        lyr = getattr(self.parent,flag+"_data_layer")
                        stbme2qgis.changeVectorLayerRenderer(self.parent.iface, self.parent, lyr,
                                                         est_symbol[shp_type], cmap_, min_, max_, 4,
                                                         shp_type = shp_type)  
                changeVectorAttributeValueIfNeeded( self.t_h, t_value,
                                                    self.parent.hard_data_layer,
                                                    self.bmeobj.hard_data.z_grid)
                changeVectorAttributeValueIfNeeded( self.t_s, t_value,
                                                    self.parent.soft_data_layer,
                                                    self.bmeobj.soft_data.z_grid)
                changeVectorAttributeValueIfNeeded( self.t_e, t_value,
                                                    self.parent.estimated_data_layer,
                                                    self.bmeobj.estimated_data.z_mean_grid)
                
                self.current_ratio_button_value = 'mean'
                
            elif self.ui.buttonGroup.checkedButton() == self.ui.radioButton_variance:
                if not self.current_ratio_button_value == 'variance': #renew colobar  
                    min_ = self.bmeobj.estimated_data.z_variance_min_without_nan
                    max_ = self.bmeobj.estimated_data.z_variance_max_without_nan
                    cmap_ = self.parent.color_bar.cmap
                    self.parent.color_bar.update( min_, max_, cmap_ )
                    
                    lyr = self.parent.estimated_data_layer
                    shp_type = self.parent.estimated_shape_file_type
                    est_symbol = { QgsWkbTypes.PointGeometry: 'regular_star', QgsWkbTypes.LineGeometry: 'SimpleLine', QgsWkbTypes.PolygonGeometry: 'SimpleFill'}
                    stbme2qgis.changeVectorLayerRenderer(self.parent.iface, self.parent, lyr,
                                                         est_symbol[ shp_type ], cmap_, min_, max_, 4,
                                                         shp_type = shp_type)
                changeVectorSymbolsForVairance( self.parent.hard_data_layer )
                changeVectorSymbolsForVairance( self.parent.soft_data_layer )
                changeVectorAttributeValueIfNeeded( self.t_e, t_value,
                                                    self.parent.estimated_data_layer,
                                                    self.bmeobj.estimated_data.z_variance_grid)
                
                try:
                    self.parent.hard_data_layer.setCacheImage( None )
                except AttributeError:
                    pass
                try:
                    self.parent.soft_data_layer.setCacheImage( None )
                except AttributeError:
                    pass
                
                self.current_ratio_button_value = 'variance'
     
            #process raster if needed
            if self.parent.hasAddRasterLayer():
                try:
                    t_index = self.t_e.index( t_value )
                except ValueError:
                    t_index = -1

                # Determine which flag set to use and hide the *other* layer
                if self.ui.buttonGroup.checkedButton() == self.ui.radioButton_mean:
                    # Hide variance raster (if any) when switching to mean
                    _other = self.parent.current_variance_layer
                    if _other is not None:
                        _node = QgsProject.instance().layerTreeRoot().findLayer(_other)
                        if _node is not None:
                            _node.setItemVisibilityChecked(False)
                    flags = ["mean"]
                elif self.ui.buttonGroup.checkedButton() == self.ui.radioButton_variance:
                    # Hide mean raster (if any) when switching to variance
                    _other = self.parent.current_mean_layer
                    if _other is not None:
                        _node = QgsProject.instance().layerTreeRoot().findLayer(_other)
                        if _node is not None:
                            _node.setItemVisibilityChecked(False)
                    flags = ["variance"]
                flag = flags[0]
                
                layer_list = eval("self.parent."+flag+"_layer_list")
                curlayer = eval('self.parent.current_'+flag+'_layer')
                    
                    
                if t_index != -1: #need to draw
                    t = self.bmeobj.estimated_data.t_grid[0][t_index]
                    min_ = self.parent.color_bar.min
                    max_ = self.parent.color_bar.max
                    mode = self.parent.color_bar.cmap
                        
                    if curlayer:
                        root = QgsProject.instance().layerTreeRoot()
                        group = root.findGroup('STBME_Raster')
                        group.removeLayer(curlayer)
                        #QgsProject.instance().removeMapLayer(curlayer.id())

                    self.qpgd.setValue(30)
                    if t_index in layer_list:
                        if self.main.hasMask():
                            file_name = '{fn}_{idx}_mask.tif'.format( fn = flag[0].capitalize(),
                                                                      idx = str( t_index )  )
                            layer_name = flag.capitalize()+'_mask T='+str(t)
                        else:
                            file_name = '{fn}_{idx}.tif'.format( fn = flag[0].capitalize(),
                                                             idx = str( t_index )  )
                            layer_name = flag.capitalize()+' T='+str(t)
                        file_path = os.path.join( WORKING_PATH, file_name )
                        if os.path.exists( file_path ):                      
                            rlayer = QgsRasterLayer(file_path, layer_name)
                            if not rlayer.isValid():
                                QMessageBox.critical(self.parent, "IOError", "Layer Failed to Load")
                                #print "Layer failed to load"
                                return False
                            
                            
                            stbme2qgis.setColorRampShader(rlayer, min_, max_, mode )

                            # Register layer with project (False = don't auto-add to layer tree root)
                            QgsProject.instance().addMapLayer(rlayer, False)

                            root = QgsProject.instance().layerTreeRoot()
                            group = root.findGroup('STBME_Raster')
                            if group:
                                group.setItemVisibilityCheckedRecursive(False)
                                setattr(self.parent,"current_"+flag+'_layer',rlayer)               
                                tree_rlayer = QgsLayerTreeLayer(rlayer)
                                group.insertChildNode(0, tree_rlayer )
                                group.setItemVisibilityCheckedRecursive(True)
                            else:
                                setattr(self.parent,"current_"+flag+'_layer',rlayer)
                                root.addChildNode(QgsLayerTreeLayer(rlayer))
                            #self.iface.legendInterface().setLayerVisible(rrlayer,True)
                            self.qpgd.setValue(40)
                        else:
                            if self.main.hasMask():
                                masked = True
                                masked_file_path = self.main.mask_layer_path
                            else:
                                masked = False
                                masked_file_path = None
                            stbme2qgis.saveAndAddRasterLayer2Qgis(self.iface,
                                                                  self.parent,self.bmeobj.estimated_data,t_index,flags,
                                                                  shader_min = min_, shader_max = max_, mode = mode,
                                                                  masked = masked, masked_file_path = masked_file_path )
                            self.qpgd.setValue(50)
                    else:
                        if self.main.hasMask():
                            masked = True
                            masked_file_path = self.main.mask_layer_path
                        else:
                            masked = False
                            masked_file_path = None
                        stbme2qgis.saveAndAddRasterLayer2Qgis(self.iface,
                                                              self.parent,self.bmeobj.estimated_data,t_index,flags,
                                                              shader_min = min_, shader_max = max_, mode = mode,
                                                              masked = masked, masked_file_path = masked_file_path )
                        self.qpgd.setValue(50)
                else:
                    if curlayer:
                        #self.iface.legendInterface().setLayerVisible(curlayer,False)
                        _node = QgsProject.instance().layerTreeRoot().findLayer(curlayer)
                        if _node is not None:
                            _node.setItemVisibilityChecked(False)
                
            self.qpgd.setValue(60)
            #save current status
            self.current_index = index
            
            #fresh canvas
            self.iface.mapCanvas().refreshAllLayers() 
                
            self.qpgd.setValue(100)
        finally:
            # Always clean up — even if an exception propagated
            self.current_drawing_state = False
            self.main.mapCanvasDefrost()
            try:
                self.qpgd.setValue(100)
                self.qpgd.close()
            except Exception:
                pass

    
    def _updateLabel(self, value = 0):
        text = str( "Time = " + str( self.t_all[ value ] ) )
        self.ui.label_time.setText( text )
        
    def _updateRange(self):
        self.ui.horizontalSlider.setRange(0,len( self.t_all ) - 1 )

    def updateAll(self):
        
        #find t_all_index
        self.t_h = self.bmeobj.hard_data.t_grid[0].tolist()
        self.t_s = self.bmeobj.soft_data.t_grid[0].tolist()
        self.t_e = self.bmeobj.estimated_data.t_grid[0].tolist()
        self.t_all = sorted(list( set( self.t_h + self.t_s + self.t_e ) ) )
        
        self._updateRange()
        self._updateLabel( self.ui.horizontalSlider.value() )
        
    def isAutoDraw(self):
        return self.ui.checkBox_autodraw.isChecked()
    
    def isDrawing(self):
        return self.current_drawing_state