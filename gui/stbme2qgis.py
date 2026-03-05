'''
Created on 2012/1/28

@author: ksj
'''

import os
import sys
import math
import numpy
from osgeo import gdal
import subprocess
from qgis.core import *
from qgis.utils import *
from qgis.core import Qgis
try:
    from scipy.interpolate import griddata as scipy_griddata
except ImportError:
    try:
        from pylab import griddata as pylab_griddata #qgis
    except ImportError:
        from matplotlib.pylab import griddata as pylab_griddata #OSGEO4W qgis

#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

from qgis.core import *
from qgis.gui import *

# QGIS 3.38+ uses QMetaType instead of QVariant for QgsField type argument.
# Fall back to QVariant.Double for older QGIS versions.
try:
    from qgis.PyQt.QtCore import QMetaType
    _FIELD_TYPE_DOUBLE = QMetaType.Type.Double
except (ImportError, AttributeError):
    _FIELD_TYPE_DOUBLE = QVariant.Double

import STAR_BME.gui.star_math
import STAR_BME.star_variable

WORKING_PATH = STAR_BME.star_variable.WORKING_PATH
GDALWARP = STAR_BME.star_variable.GDALWARP


def debug_save_value_to_shelve( path, object_seq ):
    
    return None #close debug
    
    import shelve
    f=shelve.open(path)
    f['all'] = object_seq
    f.close()


def getColorBarRenderer( mode = 'jet', symbol = 'circle',
                         min_ = 0, max_ = 1, round_ = 4,
                         shp_type =  None, null_value = None ):

    if not shp_type:
        shp_type = QgsWkbTypes.PointGeometry
    if not null_value:
        null_value = -9999.0
    INTERVAL_NUM = 63
    OPACITY = 1
    range_list = []
    colorbar_table = getColorBarTable( mode )
    min_max_table = numpy.linspace( min_, max_, INTERVAL_NUM + 1 )
    
    #if shp_type == QgsWkbTypes.PointGeometry:
        #symbol_layer_meta = QgsSymbolLayerRegistry().symbolLayerMetadata( "SimpleMarker" )
    #elif shp_type == QgsWkbTypes.LineGeometry:
        #symbol_layer_meta = QgsSymbolLayerRegistry().symbolLayerMetadata( "SimpleLine" )
    #elif shp_type == QgsWkbTypes.PolygonGeometry:
        #symbol_layer_meta = QgsSymbolLayerRegistry().symbolLayerMetadata( "SimpleFill" )
    
    for i in range( INTERVAL_NUM ):
        if i == 0:
            min_i = -10**10
        else:
            min_i = STAR_BME.gui.star_math.round_by_significant_feature( min_max_table[i], round_ )
        if i == INTERVAL_NUM - 1:
            max_i = 10**10
        else:
            max_i = STAR_BME.gui.star_math.round_by_significant_feature( min_max_table[i+1], round_ )
                    
        symbol_i = QgsSymbol.defaultSymbol( shp_type )

        point_p =  { "name" : symbol, "size" : "3"} 
        line_p = { "name" : symbol }
        polygon_p = { "name" : symbol }
        symbol_dict = { QgsWkbTypes.PointGeometry: point_p,
                        QgsWkbTypes.LineGeometry: line_p,
                        QgsWkbTypes.PolygonGeometry: polygon_p }

        if shp_type == QgsWkbTypes.PointGeometry:
            symbol_layer_reg = QgsApplication.symbolLayerRegistry()
            symbol_layer_i = symbol_layer_reg.symbolLayerMetadata( "SimpleMarker" ).createSymbolLayer( symbol_dict[ shp_type ] )
        elif shp_type == QgsWkbTypes.LineGeometry:
            symbol_layer_reg = QgsApplication.symbolLayerRegistry()
            symbol_layer_i = symbol_layer_reg.symbolLayerMetadata( "SimpleLine" ).createSymbolLayer( symbol_dict[ shp_type ] )
        elif shp_type == QgsWkbTypes.PolygonGeometry:
            symbol_layer_reg = QgsApplication.symbolLayerRegistry()
            symbol_layer_i = symbol_layer_reg.symbolLayerMetadata( "SimpleFill" ).createSymbolLayer( symbol_dict[ shp_type ] )
    

        #symbol_layer_i = symbol_layer_meta.createSymbolLayer( symbol_dict[ shp_type ] ) 

        symbol_i.changeSymbolLayer( 0, symbol_layer_i )

        label_i = str( min_i ) + " - " + str( max_i )
        color_i = QColor()
        color_i.setRgbF( *colorbar_table[i] )
        symbol_i.setColor( color_i )
        #symbol_i.setOpacity( OPACITY )
        symbol_i.setOpacity(0.7)     
            
        range_i = QgsRendererRange( min_i, max_i, symbol_i, label_i )
        range_list.append( range_i )
    
    #add NULL data
    point_p1 =   { "name" : 'cross2', "size" : "1"} 
    line_p1 = { "name" : symbol }
    polygon_p1 = { "name" : 'SimpleFill' }
    symbol_dict = { QgsWkbTypes.PointGeometry: point_p1,
                        QgsWkbTypes.LineGeometry: line_p1,
                        QgsWkbTypes.PolygonGeometry: polygon_p1 }
    
    point_p2 =   { "name" : symbol, "size" : "3"}
    line_p2 = { "name" : symbol, 'color': '255,255,255,255' }
    polygon_p2 = { "name" : "SimpleFill", 'style': 'diagonal_x', 'color': '0,0,0,255'}
    symbol_dict2 = { QgsWkbTypes.PointGeometry: point_p2,
                    QgsWkbTypes.LineGeometry: line_p2,
                    QgsWkbTypes.PolygonGeometry: polygon_p2 }

    symbol_i = QgsSymbol.defaultSymbol( shp_type )


    if shp_type == QgsWkbTypes.PointGeometry:
         
        symbol_layer_reg = QgsApplication.symbolLayerRegistry()
        symbol_layer_1 = symbol_layer_reg.symbolLayerMetadata( "SimpleMarker" ).createSymbolLayer( symbol_dict[ shp_type ] ) 
        symbol_layer_2 = symbol_layer_reg.symbolLayerMetadata( "SimpleMarker" ).createSymbolLayer( symbol_dict2[ shp_type ] ) 
    elif shp_type == QgsWkbTypes.LineGeometry:
         
        symbol_layer_reg = QgsApplication.symbolLayerRegistry()
        symbol_layer_1 = symbol_layer_reg.symbolLayerMetadata( "SimpleLine" ).createSymbolLayer( symbol_dict[ shp_type ] ) 
        symbol_layer_2 = symbol_layer_reg.symbolLayerMetadata( "SimpleLine" ).createSymbolLayer( symbol_dict2[ shp_type ] )
    elif shp_type == QgsWkbTypes.PolygonGeometry:
         
        symbol_layer_reg = QgsApplication.symbolLayerRegistry()
        symbol_layer_1 = symbol_layer_reg.symbolLayerMetadata( "SimpleFill" ).createSymbolLayer( symbol_dict[ shp_type ] ) 
        symbol_layer_2 = symbol_layer_reg.symbolLayerMetadata( "SimpleFill" ).createSymbolLayer( symbol_dict2[ shp_type ] )
    
    if shp_type == QgsWkbTypes.PointGeometry:
        symbol_i.changeSymbolLayer( 0, symbol_layer_2 )
        symbol_i.appendSymbolLayer( symbol_layer_1 )
        symbol_i.setColor( QColor(255,255,255) ) #white
        label_i =  "NULL ({sym})".format( sym = str( null_value ) )
        range_i = QgsRendererRange( null_value, null_value, symbol_i, label_i )
        range_list.insert( 0, range_i )
    elif shp_type == QgsWkbTypes.LineGeometry:
        symbol_i.changeSymbolLayer( 0, symbol_layer_2 )
        #symbol_i.appendSymbolLayer( symbol_layer_1 )
        #symbol_i.setColor( QColor(255,255,255) ) #white
        label_i =  "NULL ({sym})".format( sym = str( null_value ) )
        range_i = QgsRendererRange( null_value, null_value, symbol_i, label_i )
        range_list.insert( 0, range_i )
    elif shp_type == QgsWkbTypes.PolygonGeometry:
        symbol_i.changeSymbolLayer( 0, symbol_layer_2 )
        #symbol_i.appendSymbolLayer( symbol_layer_1 )
        #symbol_i.setColor( QColor(255,255,255) ) #white
        label_i =  "NULL ({sym})".format( sym = str( null_value ) )
        range_i = QgsRendererRange( null_value, null_value, symbol_i, label_i )
        range_list.insert( 0, range_i )

    renderer = QgsGraduatedSymbolRenderer( '', range_list )
    try:
        # QGIS 3.10+: use classification method instead of deprecated setMode()
        from qgis.core import QgsClassificationEqualInterval
        renderer.setClassificationMethod(QgsClassificationEqualInterval())
    except (ImportError, AttributeError):
        pass  # Ranges are already manually defined, mode is informational only
    return renderer

def addVector2QgisWithRenderer(iface, layer_path, layer_name, renderer):
    lyr = QgsVectorLayer(layer_path, layer_name, 'ogr')
    if lyr.isValid():
        renderer.setClassAttribute("Obs Val")
        lyr.setRenderer( renderer )

        # Register layer with project (False = don't auto-add to layer tree root)
        QgsProject.instance().addMapLayer(lyr, False)

        #find group & add
        not_match = True

        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup('STBME_Vector')
        if group:
            group.setItemVisibilityCheckedRecursive(True)  
            tree_rlayer = QgsLayerTreeLayer(lyr)
            group.insertChildNode(0, tree_rlayer )
            not_match = False
        else:
            # Fallback: add to root if group doesn't exist
            root.addChildNode(QgsLayerTreeLayer(lyr))
            not_match = False


        
        if not_match:
            return False #find group fail
        
        # Ensure the layer node is visible and canvas is refreshed
        layer_node = QgsProject.instance().layerTreeRoot().findLayer(lyr)
        if layer_node:
            layer_node.setItemVisibilityChecked(True)
        lyr.triggerRepaint()
        iface.mapCanvas().refresh()
        iface.zoomFull()
        return lyr
    else:
        QMessageBox.warning(iface.mainWindow(), 'no', 'no')



def collapseLayer(iface, layer):
    root = QgsProject.instance().layerTreeRoot()
    myLayerNode = root.findLayer(layer)
    if myLayerNode is not None:
        myLayerNode.setExpanded(False) 
    #iface.legendInterface().setLayerExpanded( layer, False )

def saveAndAddVectorLayer2Qgis(iface, main, dataobj, flag, render_min = None , render_max = None, shp_type = None, shp_path = None ):  
    save_file_name = flag + "Data"
    vlayer = createVectorLayerFromDataObject(dataobj, flag, main.crs, shp_type = shp_type, shp_path = shp_path )

    #create working path
    if not os.path.exists(WORKING_PATH):
        os.mkdir(WORKING_PATH)
    #write vlayer to file
    save_path = os.path.join(WORKING_PATH, '{shp}.shp'.format(shp=save_file_name))
    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = "ESRI Shapefile"
    save_options.fileEncoding = "utf8"
    transform_context = QgsProject.instance().transformContext()
    write_result = QgsVectorFileWriter.writeAsVectorFormatV3(
        vlayer, save_path, transform_context, save_options)
    error_code = write_result[0] if isinstance(write_result, tuple) else write_result

    if error_code == QgsVectorFileWriter.NoError:
       
        del vlayer
        
        if flag == "Hard":
            symbol = 'circle'
        elif flag == "Soft":
            symbol = 'equilateral_triangle'
        elif flag == "Estimated":
            if shp_type == QgsWkbTypes.PointGeometry:
                symbol = 'regular_star'
            elif shp_type == QgsWkbTypes.LineGeometry:
                symbol = "SimpleLine"
            elif shp_type == QgsWkbTypes.PolygonGeometry:
                symbol = 'SimpleFill'

        rdr = getColorBarRenderer( 'jet', symbol, render_min, render_max, round_ = 4, shp_type = shp_type)

        lyr = addVector2QgisWithRenderer( iface, layer_path = os.path.join( WORKING_PATH,
                                                                            "{fn}.shp".format( fn = save_file_name )
                                                                            ),
                                          layer_name = save_file_name, renderer = rdr)
        if not lyr:
            QMessageBox.warning(main, "Find Group Fail", "Cannot Find STBME_Vector Group. Add to Top Level Instead.")
        setattr(main, flag.lower()+'_data_layer', lyr)
        return True
    else:
        QMessageBox.information(None,"no","186")
        return False
       

def createVectorLayerFromDataObject(
    dataobj, flag, crs = None, t_index = 0,
    shp_type = None, shp_path = None, null_value = -9999.0,
    sig_ftr_n = 4):
    
    if not shp_type:
        #shp_type = QGis.Point
        shp_type = QgsWkbTypes.PointGeometry 
    #create vector layer
    qsetting = QSettings()
    orig_crs_remind_setting = qsetting.value("/Projections/defaultBehaviour")
    qsetting.setValue("/Projections/defaultBehaviour", "useGlobal")
    
    #create vector layer
    #layer_type_dict = { QGis.Point: "Point", QGis.Line: "Line", QGis.Polygon: "Polygon"}
    layer_type_dict = { QgsWkbTypes.PointGeometry : "Point", QgsWkbTypes.LineGeometry: "Line", QgsWkbTypes.PolygonGeometry: "Polygon"}
    #layer_type_dict = { Qgis.Point: "Point", Qgis.Line: "Line", Qgis.Polygon: "Polygon"}

    
    #set crs if it has
    if crs:
        #vlayer.setCrs(crs)
        vlayer = QgsVectorLayer( layer_type_dict[ shp_type ]+'?crs=epsg:'+str(crs.postgisSrid()), 'whatever', "memory")
    else:
        vlayer = QgsVectorLayer( layer_type_dict[ shp_type ], 'whatever', "memory")

    vlayer.startEditing()
    #set all spatial coord & data_mean, data_variance
    data_provider = vlayer.dataProvider()
    if flag == "Hard" or flag == "Soft" or flag == "Estimated":
        # data_provider.addAttributes([ 
        #    QgsField("Mean", QVariant.Double),
        #    QgsField("Variance", QVariant.Double) ])
        data_provider.addAttributes([ 
            QgsField("Obs Val", _FIELD_TYPE_DOUBLE)])
    else:
        raise TypeError("My Strange Error.")
     
    if flag == "Hard" or flag == "Soft":
        z_grid_at_t = dataobj.z_grid[:,t_index:t_index + 1]
    elif  flag == "Estimated":
        z_grid_at_t = dataobj.z_mean_grid[:,t_index:t_index + 1]
    feature_list = []
    
    
    
    
    #if shp_type == QGis.Line or shp_type == QGis.Polygon:
    if shp_type == QgsWkbTypes.LineGeometry or shp_type == QgsWkbTypes.PolygonGeometry:
    #if shp_type == Qgis.Line or shp_type == Qgis.Polygon:
        vlayer_ref = QgsVectorLayer( shp_path, "whatever2", 'ogr' )
        #find xy_geo_pair
        xy_geo_pair = {}
        for ftre in vlayer_ref.getFeatures():
            has_data = False
            for idx, s in enumerate( dataobj.s_grid ):
                x, y = s
                if str(x) == str(ftre.geometry().centroid().asPoint().x()) and\
                   str(y) == str(ftre.geometry().centroid().asPoint().y()):# ftre.geometry().centroid().equals( geom ):
                    gg = ftre.geometry()
                    geom2 = QgsGeometry( gg )
                    xy_geo_pair[ idx ] =  geom2
                    has_data = True
                    break     
            if not has_data: raise ValueError('Very Strange Error')
        
    for ( idx,( s, val_i ) ) in enumerate( zip(dataobj.s_grid, z_grid_at_t ) ): #two slice make array dim = 2

        val = val_i[0]

        feature = QgsFeature()
        feature.initAttributes(1)
        #if shp_type == QGis.Line or shp_type == QGis.Polygon:
        if shp_type == QgsWkbTypes.LineGeometry or shp_type == QgsWkbTypes.PolygonGeometry :
        #if shp_type == Qgis.Line or shp_type == Qgis.Polygon:

            geom3 = xy_geo_pair[ idx ]
            feature.setGeometry( geom3 )   
        else:
            qpoint = QgsPointXY( float( s[0] ), float( s[1] ) )
            feature.setGeometry(QgsGeometry.fromPointXY(qpoint))
            
        if numpy.isnan(val):
            attr_val = null_value
            pass #no assign value means assign NULL value
        else:
            attr_val = val
        feature.setAttribute( 0, float(attr_val) )
        feature_list.append(feature)
        
        
    data_provider.addFeatures(feature_list)
    vlayer.updateExtents()
 
    #set crs setting to original value
    qsetting.setValue("/Projections/defaultBehaviour", orig_crs_remind_setting )
          
    vlayer.commitChanges()
    return vlayer

def changeVectorLayerRenderer(
    iface, main, lyr, symbol_name, cmap_name,
    min_, max_, round_ , class_attribute = 'Obs Val', shp_type = None
    ):
    
    if lyr:
        rdr = getColorBarRenderer( cmap_name, symbol_name, min_, max_, round_, shp_type = shp_type )
        rdr.setClassAttribute( class_attribute )
        lyr.setRenderer( rdr )
        iface.layerTreeView().refreshLayerSymbology( lyr.id() )
        collapseLayer( iface, lyr )


# NO USE  It SHOULD CAN BE USE...
#def getColorRampShader( min_ = 0.0, max_ = 255.0, mode = 'jet', rmp_type = QgsColorRampShader.INTERPOLATED ):
#    clr_rmp_shdr = QgsColorRampShader(min_, max_)
#    
#    clr_tb = getColorRampTable( mode )    
#    clr_lst = []
#    for val, rgb in zip( numpy.linspace( min_, max_, 64 ), clr_tb ):
#        qc = QColor()
#        qc.setRgbF( *rgb )
#        clr_lst.append( QgsColorRampShader.ColorRampItem( val, qc ) )
#    
#    clr_rmp_shdr.setColorRampType(rmp_type)
#    clr_rmp_shdr.setColorRampItemList( clr_lst )
#    
#    return clr_rmp_shdr

def setColorRampShader( rlayer, min_ = 0.0, max_ = 255.0, mode = 'jet', rmp_type = QgsColorRampShader.Interpolated ):
    #QGIS2
    #rlayer.setDrawingStyle( 'SingleBandPseudoColor' )
    rshd = QgsRasterShader()
    shd = QgsColorRampShader()

    
    #rlayer.setColorShadingAlgorithm(QgsRasterLayer.ColorRampShader)
    #clr_rmp_shdr = shd.rasterShaderFunction()

    clr_tb = getColorRampTable( mode )    
    clr_lst = []
    for val, rgb in zip( numpy.linspace( min_, max_, 64 ), clr_tb ):
        qc = QColor()
        qc.setRgbF( *rgb )
        clr_lst.append( QgsColorRampShader.ColorRampItem( val, qc ) )
    
    #add outlier value
    qc = QColor()
    qc.setRgbF( *clr_tb[0] )
    clr_lst.insert( 0, QgsColorRampShader.ColorRampItem( -10**10, qc ) )
    qc = QColor()
    qc.setRgbF( *clr_tb[-1] )
    clr_lst.append( QgsColorRampShader.ColorRampItem( 10**10, qc ) )
    shd.setColorRampType( rmp_type )
    shd.setColorRampItemList( clr_lst )

    rshd.setRasterShaderFunction( shd )
    rdr = QgsSingleBandPseudoColorRenderer(
        rlayer.dataProvider(), 1, rshd)
    rlayer.setRenderer(rdr)


    #rlayer.renderer().setShader(shd)
    #rlayer.renderer().shader().setRasterShaderFunction( shd )
    
    return rlayer

def addRaster2QgisWithShader(iface, file_path, file_name = None, min_ = 0.0, max_ = 255.0,
    mode = 'jet', rmp_type = QgsColorRampShader.Interpolated):

    if file_name is None:
       file_name = os.path.split(file_path)[1]
    
    rlayer = QgsRasterLayer(file_path, file_name)
    if not rlayer.isValid():
        return False

    rlayer = setColorRampShader( rlayer, min_, max_, mode, rmp_type)
    
    # Register layer with project (False = don't auto-add to layer tree root)
    QgsProject.instance().addMapLayer(rlayer, False)

    root = QgsProject.instance().layerTreeRoot()
    group = root.findGroup('STBME_Raster')
    if group:
        tree_rlayer = QgsLayerTreeLayer(rlayer)
        group.insertChildNode(0, tree_rlayer )
    else:
        # Fallback: add to root if group doesn't exist
        root.addChildNode(QgsLayerTreeLayer(rlayer))

    return rlayer
    
def saveAndAddRasterLayer2Qgis(iface, main, est_dataobj, index = 0, flags = ["mean"],
                               shader_min = 0.0, shader_max = 255.0, mode = 'jet',
                               masked = False, masked_file_path = None, null_value = -9999.0 ):

    def getPixResAndSize(grid_param):
        #get pixel resolution and size
        xmin, xmax, ymin, ymax, tmin, tmax, xn, yn, tn = main.grid_param
        
        if xn < 512:
            xsize = 512
        else:
            xsize = xn
        xresolution = ( xmax - xmin ) / xsize 
        
        if yn < 512:
            ysize = 512
        else:
            ysize = yn
        yresolution = ( ymax - ymin ) / ysize 
        
        origin_x = xmin# - 0.5*xresolution
        origin_y = ymax# + 0.5*yresolution
        
        return ( origin_x, xresolution, xmin, xmax, xsize,\
                 origin_y, yresolution, ymin, ymax, ysize )
        
    def getEstimatedPoint( point_coord, point_value, est_x_2d, est_y_2d ):
        #null_value return to NaN and remove when interpolation
        point_value[ numpy.where( point_value == null_value ) ] = numpy.nan
        point_value_without_nan = point_value[ ~numpy.isnan( point_value ) ]
        point_coord_without_nan = point_coord[ ~numpy.isnan( point_value ) ]

        try:
            est_z_2d = scipy_griddata( point_coord_without_nan,
                                       point_value_without_nan,
                                       ( est_x_2d, est_y_2d ),
                                       method = 'cubic')
        except NameError:
            pylab_x, pylab_y = zip( *point_coord_without_nan )
            #est_z_2d = pylab_griddata(pylab_x, pylab_y, point_value,est_x_2d, est_y_2d,interp = 'nn')
            est_z_2d = pylab_griddata( pylab_x, pylab_y,
                                       point_value_without_nan,est_x_2d[0], 
                                       est_y_2d[:,0][::-1],interp = 'linear')
            est_z_2d = est_z_2d[::-1]
        return est_z_2d
    
    def writeTiff( file_path, est_z_2d,
                   origin_x, xresolution, xsize,
                   origin_y, yresolution, ysize,
                   gdal_driver, crs, useCrs ):

        tif_f = gdal_driver.Create(file_path, xsize, ysize, 1, gdal.GDT_Float32)
        if not tif_f:
            return False # create fault
        tif_f.SetGeoTransform( [ origin_x, xresolution, 0, origin_y, 0, yresolution * (-1)])
        if useCrs:
            tif_f.SetProjection(str(crs.toWkt()))  
        #tif_f.GetRasterBand(1).WriteArray(convert2Uint8(est_z_2d,m,M))
        tif_f.GetRasterBand(1).WriteArray(est_z_2d)
        tif_f = None
        return True #success
      
    if not os.path.exists(WORKING_PATH):
            os.mkdir(WORKING_PATH)
    
    x_origin, x_resolution, x_min, x_max, x_size,\
    y_origin, y_resolution, y_min, y_max, y_size = getPixResAndSize(main.grid_param)
    
    for fl in flags:
        est_x_2d, est_y_2d = numpy.meshgrid(numpy.arange(x_min, x_max, x_resolution),
                                            numpy.arange(y_max, y_min, -y_resolution))

        point_coord = est_dataobj.s_grid
        point_value = getattr(est_dataobj,"z_"+fl+"_grid")[:,index]
        
        est_z_2d = getEstimatedPoint(point_coord, point_value,
                                      est_x_2d, est_y_2d)

        #output Gtiff file
        file_path = os.path.join( WORKING_PATH,
                                  '{fn}_{idx}.tif'.format( fn = fl[0].capitalize(),
                                                           idx = str(index)
                                                         )
                                 )
        t = est_dataobj.t_grid[0][index]
        file_name = fl.capitalize()+' T='+str(t)
        if os.path.exists(file_path):
            pass
        else:             
            if not writeTiff(
                file_path, est_z_2d,
                x_origin, x_resolution, x_size,
                y_origin, y_resolution, y_size,
                main.gdal_driver, main.crs, main.useCrs()):

                QMessageBox.critical(main, "Raster Create Fault", "Cannot Create File")
                return False
        
        if masked:
            m_f_name, m_f_suffix = os.path.splitext(file_path)
            #make the masked tiff
            # Check that gdalwarp exists
            if not os.path.isfile(GDALWARP):
                QMessageBox.critical(
                    main, "GDAL Not Found",
                    "Cannot find gdalwarp at:\n{}\n\n"
                    "Please ensure GDAL is installed with your QGIS installation.".format(GDALWARP))
                return False
            cmd = [ 
                GDALWARP,
                "-overwrite",
                '-q',
                '-dstalpha',
                '-crop_to_cutline',
                '-of', 'GTiff',
                '-dstnodata', '-9999.0',
                "-cutline", masked_file_path,
                file_path,
                m_f_name+'_mask'+m_f_suffix
                ]
            
            ans = subprocess.call( cmd )
            if ans != 0:
                QMessageBox.critical(
                    main, "Mask Raster Error",
                    "gdalwarp failed (exit code {}).\n\n"
                    "The mask shapefile must be a polygon layer whose features "
                    "define the clipping boundary. If your shapefile contains "
                    "multiple polygons (e.g. individual townships), you may need "
                    "to dissolve them into a single polygon first.\n\n"
                    "In QGIS: Vector ▸ Geoprocessing Tools ▸ Dissolve".format(ans))
                return False
            #change the file path to masked tiff path
            file_path = m_f_name+'_mask'+m_f_suffix
            file_name = fl.capitalize()+'_mask T='+str(t)
            
        result = addRaster2QgisWithShader( iface, file_path, file_name,
                                               min_ = shader_min,
                                               max_ = shader_max,
                                               mode = mode )
        if not result:
            #print "Layer failed to load"
            QMessageBox.critical(main, "IOError", "Layer Failed to Load")
            return False
        else:
            rrlayer = result
        
        eval("main."+fl+"_layer_list").append(index)
        setattr(main, "current_"+fl+"_layer",rrlayer)

    return True,est_z_2d




def getColorRampTable( mode = 'jet' ):
    if mode.endswith('_r'):
        try:
            table = eval(mode[:-2])()[::-1]
        except NameError:
            raise NameError("My Fault")
    else:
        try:
            table = eval(mode)() #call colormap function
        except NameError:
            raise NameError("My Fault")
        
    return table
    


def getColorBarTable( mode = 'jet' ):
    if mode.endswith('_r'):
        try:
            table = eval(mode[:-2])()[::-1]
        except NameError:
            raise NameError("My Fault")
    else:
        try:
            table = eval(mode)() #call colormap function
        except NameError:
            raise NameError("My Fault")
#    if mode == 'jet':
#        table = jet()
#    elif mode == 'hot':
#        table = hot()
        
    table_left = table[:-1]
    table_right = table[1:]
    return (table_left + table_right)/2


def jet():
    return numpy.array([
          [0.0, 0.0, 0.5625] , [0.0, 0.0, 0.625] ,
          [0.0, 0.0, 0.6875] , [0.0, 0.0, 0.75] ,
          [0.0, 0.0, 0.8125] , [0.0, 0.0, 0.875] ,
          [0.0, 0.0, 0.9375] , [0.0, 0.0, 1.0] ,
          [0.0, 0.0625, 1.0] , [0.0, 0.125, 1.0] ,
          [0.0, 0.1875, 1.0] , [0.0, 0.25, 1.0] ,
          [0.0, 0.3125, 1.0] , [0.0, 0.375, 1.0] ,
          [0.0, 0.4375, 1.0] , [0.0, 0.5, 1.0] ,
          [0.0, 0.5625, 1.0] , [0.0, 0.625, 1.0] ,
          [0.0, 0.6875, 1.0] , [0.0, 0.75, 1.0] ,
          [0.0, 0.8125, 1.0] , [0.0, 0.875, 1.0] ,
          [0.0, 0.9375, 1.0] , [0.0, 1.0, 1.0] ,
          [0.0625, 1.0, 0.9375] , [0.125, 1.0, 0.875] ,
          [0.1875, 1.0, 0.8125] , [0.25, 1.0, 0.75] ,
          [0.3125, 1.0, 0.6875] , [0.375, 1.0, 0.625] ,
          [0.4375, 1.0, 0.5625] , [0.5, 1.0, 0.5] ,
          [0.5625, 1.0, 0.4375] , [0.625, 1.0, 0.375] ,
          [0.6875, 1.0, 0.3125] , [0.75, 1.0, 0.25] ,
          [0.8125, 1.0, 0.1875] , [0.875, 1.0, 0.125] ,
          [0.9375, 1.0, 0.0625] , [1.0, 1.0, 0.0] ,
          [1.0, 0.9375, 0.0] , [1.0, 0.875, 0.0] ,
          [1.0, 0.8125, 0.0] , [1.0, 0.75, 0.0] ,
          [1.0, 0.6875, 0.0] , [1.0, 0.625, 0.0] ,
          [1.0, 0.5625, 0.0] , [1.0, 0.5, 0.0] ,
          [1.0, 0.4375, 0.0] , [1.0, 0.375, 0.0] ,
          [1.0, 0.3125, 0.0] , [1.0, 0.25, 0.0] ,
          [1.0, 0.1875, 0.0] , [1.0, 0.125, 0.0] ,
          [1.0, 0.0625, 0.0] , [1.0, 0.0, 0.0] ,
          [0.9375, 0.0, 0.0] , [0.875, 0.0, 0.0] ,
          [0.8125, 0.0, 0.0] , [0.75, 0.0, 0.0] ,
          [0.6875, 0.0, 0.0] , [0.625, 0.0, 0.0] ,
          [0.5625, 0.0, 0.0] , [0.5, 0.0, 0.0] ])
    
def hot():
    return numpy.array([
        [ 0.0417,0,0],[ 0.0833,0,0],[ 0.1250,0,0],[ 0.1667,0,0],
        [ 0.2083,0,0],[ 0.2500,0,0],[ 0.2917,0,0],[ 0.3333,0,0],
        [ 0.3750,0,0],[ 0.4167,0,0],[ 0.4583,0,0],[ 0.5000,0,0],
        [ 0.5417,0,0],[ 0.5833,0,0],[ 0.6250,0,0],[ 0.6667,0,0],
        [ 0.7083,0,0],[ 0.7500,0,0],[ 0.7917,0,0],[ 0.8333,0,0],
        [ 0.8750,0,0],[ 0.9167,0,0],[ 0.9583,0,0],[ 1.0000,0,0],
        [ 1.0000,0.0417,0],[ 1.0000,0.0833,0],[ 1.0000,0.1250,0],[ 1.0000,0.1667,0],
        [ 1.0000,0.2083,0],[ 1.0000,0.2500,0],[ 1.0000,0.2917,0],[ 1.0000,0.3333,0],
        [ 1.0000,0.3750,0],[ 1.0000,0.4167,0],[ 1.0000,0.4583,0],[ 1.0000,0.5000,0],
        [ 1.0000,0.5417,0],[ 1.0000,0.5833,0],[ 1.0000,0.6250,0],[ 1.0000,0.6667,0],
        [ 1.0000,0.7083,0],[ 1.0000,0.7500,0],[ 1.0000,0.7917,0],[ 1.0000,0.8333,0],
        [ 1.0000,0.8750,0],[ 1.0000,0.9167,0],[ 1.0000,0.9583,0],[ 1.0000,1.0000,0],
        [ 1.0000,1.0000,0.0625],[ 1.0000,1.0000,0.1250],[ 1.0000,1.0000,0.1875],[ 1.0000,1.0000,0.2500],
        [ 1.0000,1.0000,0.3125],[ 1.0000,1.0000,0.3750],[ 1.0000,1.0000,0.4375],[ 1.0000,1.0000,0.5000],
        [ 1.0000,1.0000,0.5625],[ 1.0000,1.0000,0.6250],[ 1.0000,1.0000,0.6875],[ 1.0000,1.0000,0.7500],
        [ 1.0000,1.0000,0.8125],[ 1.0000,1.0000,0.8750],[ 1.0000,1.0000,0.9375],[ 1.0000,1.0000,1.0000],
        ])

def hsv():
    return numpy.array([
[1.0000,0,0],
[1.0000,0.0938,0],
[1.0000,0.1875,0],
[1.0000,0.2813,0],
[1.0000,0.3750,0],
[1.0000,0.4688,0],
[1.0000,0.5625,0],
[1.0000,0.6563,0],
[1.0000,0.7500,0],
[1.0000,0.8438,0],
[1.0000,0.9375,0],
[0.9688,1.0000,0],
[0.8750,1.0000,0],
[0.7813,1.0000,0],
[0.6875,1.0000,0],
[0.5938,1.0000,0],
[0.5000,1.0000,0],
[0.4063,1.0000,0],
[0.3125,1.0000,0],
[0.2188,1.0000,0],
[0.1250,1.0000,0],
[0.0313,1.0000,0],
[0,1.0000,0.0625],
[0,1.0000,0.1563],
[0,1.0000,0.2500],
[0,1.0000,0.3438],
[0,1.0000,0.4375],
[0,1.0000,0.5313],
[0,1.0000,0.6250],
[0,1.0000,0.7188],
[0,1.0000,0.8125],
[0,1.0000,0.9063],
[0,1.0000,1.0000],
[0,0.9063,1.0000],
[0,0.8125,1.0000],
[0,0.7188,1.0000],
[0,0.6250,1.0000],
[0,0.5313,1.0000],
[0,0.4375,1.0000],
[0,0.3438,1.0000],
[0,0.2500,1.0000],
[0,0.1563,1.0000],
[0,0.0625,1.0000],
[0.0313,0,1.0000],
[0.1250,0,1.0000],
[0.2188,0,1.0000],
[0.3125,0,1.0000],
[0.4063,0,1.0000],
[0.5000,0,1.0000],
[0.5938,0,1.0000],
[0.6875,0,1.0000],
[0.7813,0,1.0000],
[0.8750,0,1.0000],
[0.9688,0,1.0000],
[1.0000,0,0.9375],
[1.0000,0,0.8438],
[1.0000,0,0.7500],
[1.0000,0,0.6563],
[1.0000,0,0.5625],
[1.0000,0,0.4688],
[1.0000,0,0.3750],
[1.0000,0,0.2813],
[1.0000,0,0.1875],
[1.0000,0,0.0938]
])

def cool():
    return numpy.array([
[0,1.0000,1.0000],
[0.0159,0.9841,1.0000],
[0.0317,0.9683,1.0000],
[0.0476,0.9524,1.0000],
[0.0635,0.9365,1.0000],
[0.0794,0.9206,1.0000],
[0.0952,0.9048,1.0000],
[0.1111,0.8889,1.0000],
[0.1270,0.8730,1.0000],
[0.1429,0.8571,1.0000],
[0.1587,0.8413,1.0000],
[0.1746,0.8254,1.0000],
[0.1905,0.8095,1.0000],
[0.2063,0.7937,1.0000],
[0.2222,0.7778,1.0000],
[0.2381,0.7619,1.0000],
[0.2540,0.7460,1.0000],
[0.2698,0.7302,1.0000],
[0.2857,0.7143,1.0000],
[0.3016,0.6984,1.0000],
[0.3175,0.6825,1.0000],
[0.3333,0.6667,1.0000],
[0.3492,0.6508,1.0000],
[0.3651,0.6349,1.0000],
[0.3810,0.6190,1.0000],
[0.3968,0.6032,1.0000],
[0.4127,0.5873,1.0000],
[0.4286,0.5714,1.0000],
[0.4444,0.5556,1.0000],
[0.4603,0.5397,1.0000],
[0.4762,0.5238,1.0000],
[0.4921,0.5079,1.0000],
[0.5079,0.4921,1.0000],
[0.5238,0.4762,1.0000],
[0.5397,0.4603,1.0000],
[0.5556,0.4444,1.0000],
[0.5714,0.4286,1.0000],
[0.5873,0.4127,1.0000],
[0.6032,0.3968,1.0000],
[0.6190,0.3810,1.0000],
[0.6349,0.3651,1.0000],
[0.6508,0.3492,1.0000],
[0.6667,0.3333,1.0000],
[0.6825,0.3175,1.0000],
[0.6984,0.3016,1.0000],
[0.7143,0.2857,1.0000],
[0.7302,0.2698,1.0000],
[0.7460,0.2540,1.0000],
[0.7619,0.2381,1.0000],
[0.7778,0.2222,1.0000],
[0.7937,0.2063,1.0000],
[0.8095,0.1905,1.0000],
[0.8254,0.1746,1.0000],
[0.8413,0.1587,1.0000],
[0.8571,0.1429,1.0000],
[0.8730,0.1270,1.0000],
[0.8889,0.1111,1.0000],
[0.9048,0.0952,1.0000],
[0.9206,0.0794,1.0000],
[0.9365,0.0635,1.0000],
[0.9524,0.0476,1.0000],
[0.9683,0.0317,1.0000],
[0.9841,0.0159,1.0000],
[1.0000,0,1.0000]
])
    
def spring():
    return numpy.array([
[1.0000,0,1.0000],
[1.0000,0.0159,0.9841],
[1.0000,0.0317,0.9683],
[1.0000,0.0476,0.9524],
[1.0000,0.0635,0.9365],
[1.0000,0.0794,0.9206],
[1.0000,0.0952,0.9048],
[1.0000,0.1111,0.8889],
[1.0000,0.1270,0.8730],
[1.0000,0.1429,0.8571],
[1.0000,0.1587,0.8413],
[1.0000,0.1746,0.8254],
[1.0000,0.1905,0.8095],
[1.0000,0.2063,0.7937],
[1.0000,0.2222,0.7778],
[1.0000,0.2381,0.7619],
[1.0000,0.2540,0.7460],
[1.0000,0.2698,0.7302],
[1.0000,0.2857,0.7143],
[1.0000,0.3016,0.6984],
[1.0000,0.3175,0.6825],
[1.0000,0.3333,0.6667],
[1.0000,0.3492,0.6508],
[1.0000,0.3651,0.6349],
[1.0000,0.3810,0.6190],
[1.0000,0.3968,0.6032],
[1.0000,0.4127,0.5873],
[1.0000,0.4286,0.5714],
[1.0000,0.4444,0.5556],
[1.0000,0.4603,0.5397],
[1.0000,0.4762,0.5238],
[1.0000,0.4921,0.5079],
[1.0000,0.5079,0.4921],
[1.0000,0.5238,0.4762],
[1.0000,0.5397,0.4603],
[1.0000,0.5556,0.4444],
[1.0000,0.5714,0.4286],
[1.0000,0.5873,0.4127],
[1.0000,0.6032,0.3968],
[1.0000,0.6190,0.3810],
[1.0000,0.6349,0.3651],
[1.0000,0.6508,0.3492],
[1.0000,0.6667,0.3333],
[1.0000,0.6825,0.3175],
[1.0000,0.6984,0.3016],
[1.0000,0.7143,0.2857],
[1.0000,0.7302,0.2698],
[1.0000,0.7460,0.2540],
[1.0000,0.7619,0.2381],
[1.0000,0.7778,0.2222],
[1.0000,0.7937,0.2063],
[1.0000,0.8095,0.1905],
[1.0000,0.8254,0.1746],
[1.0000,0.8413,0.1587],
[1.0000,0.8571,0.1429],
[1.0000,0.8730,0.1270],
[1.0000,0.8889,0.1111],
[1.0000,0.9048,0.0952],
[1.0000,0.9206,0.0794],
[1.0000,0.9365,0.0635],
[1.0000,0.9524,0.0476],
[1.0000,0.9683,0.0317],
[1.0000,0.9841,0.0159],
[1.0000,1.0000,0]
])
    
def summer():
    return numpy.array([
[0,0.5000,0.4000],
[0.0159,0.5079,0.4000],
[0.0317,0.5159,0.4000],
[0.0476,0.5238,0.4000],
[0.0635,0.5317,0.4000],
[0.0794,0.5397,0.4000],
[0.0952,0.5476,0.4000],
[0.1111,0.5556,0.4000],
[0.1270,0.5635,0.4000],
[0.1429,0.5714,0.4000],
[0.1587,0.5794,0.4000],
[0.1746,0.5873,0.4000],
[0.1905,0.5952,0.4000],
[0.2063,0.6032,0.4000],
[0.2222,0.6111,0.4000],
[0.2381,0.6190,0.4000],
[0.2540,0.6270,0.4000],
[0.2698,0.6349,0.4000],
[0.2857,0.6429,0.4000],
[0.3016,0.6508,0.4000],
[0.3175,0.6587,0.4000],
[0.3333,0.6667,0.4000],
[0.3492,0.6746,0.4000],
[0.3651,0.6825,0.4000],
[0.3810,0.6905,0.4000],
[0.3968,0.6984,0.4000],
[0.4127,0.7063,0.4000],
[0.4286,0.7143,0.4000],
[0.4444,0.7222,0.4000],
[0.4603,0.7302,0.4000],
[0.4762,0.7381,0.4000],
[0.4921,0.7460,0.4000],
[0.5079,0.7540,0.4000],
[0.5238,0.7619,0.4000],
[0.5397,0.7698,0.4000],
[0.5556,0.7778,0.4000],
[0.5714,0.7857,0.4000],
[0.5873,0.7937,0.4000],
[0.6032,0.8016,0.4000],
[0.6190,0.8095,0.4000],
[0.6349,0.8175,0.4000],
[0.6508,0.8254,0.4000],
[0.6667,0.8333,0.4000],
[0.6825,0.8413,0.4000],
[0.6984,0.8492,0.4000],
[0.7143,0.8571,0.4000],
[0.7302,0.8651,0.4000],
[0.7460,0.8730,0.4000],
[0.7619,0.8810,0.4000],
[0.7778,0.8889,0.4000],
[0.7937,0.8968,0.4000],
[0.8095,0.9048,0.4000],
[0.8254,0.9127,0.4000],
[0.8413,0.9206,0.4000],
[0.8571,0.9286,0.4000],
[0.8730,0.9365,0.4000],
[0.8889,0.9444,0.4000],
[0.9048,0.9524,0.4000],
[0.9206,0.9603,0.4000],
[0.9365,0.9683,0.4000],
[0.9524,0.9762,0.4000],
[0.9683,0.9841,0.4000],
[0.9841,0.9921,0.4000],
[1.0000,1.0000,0.4000]
])
    
def autumn():
    return numpy.array([
[1.0000,0,0],
[1.0000,0.0159,0],
[1.0000,0.0317,0],
[1.0000,0.0476,0],
[1.0000,0.0635,0],
[1.0000,0.0794,0],
[1.0000,0.0952,0],
[1.0000,0.1111,0],
[1.0000,0.1270,0],
[1.0000,0.1429,0],
[1.0000,0.1587,0],
[1.0000,0.1746,0],
[1.0000,0.1905,0],
[1.0000,0.2063,0],
[1.0000,0.2222,0],
[1.0000,0.2381,0],
[1.0000,0.2540,0],
[1.0000,0.2698,0],
[1.0000,0.2857,0],
[1.0000,0.3016,0],
[1.0000,0.3175,0],
[1.0000,0.3333,0],
[1.0000,0.3492,0],
[1.0000,0.3651,0],
[1.0000,0.3810,0],
[1.0000,0.3968,0],
[1.0000,0.4127,0],
[1.0000,0.4286,0],
[1.0000,0.4444,0],
[1.0000,0.4603,0],
[1.0000,0.4762,0],
[1.0000,0.4921,0],
[1.0000,0.5079,0],
[1.0000,0.5238,0],
[1.0000,0.5397,0],
[1.0000,0.5556,0],
[1.0000,0.5714,0],
[1.0000,0.5873,0],
[1.0000,0.6032,0],
[1.0000,0.6190,0],
[1.0000,0.6349,0],
[1.0000,0.6508,0],
[1.0000,0.6667,0],
[1.0000,0.6825,0],
[1.0000,0.6984,0],
[1.0000,0.7143,0],
[1.0000,0.7302,0],
[1.0000,0.7460,0],
[1.0000,0.7619,0],
[1.0000,0.7778,0],
[1.0000,0.7937,0],
[1.0000,0.8095,0],
[1.0000,0.8254,0],
[1.0000,0.8413,0],
[1.0000,0.8571,0],
[1.0000,0.8730,0],
[1.0000,0.8889,0],
[1.0000,0.9048,0],
[1.0000,0.9206,0],
[1.0000,0.9365,0],
[1.0000,0.9524,0],
[1.0000,0.9683,0],
[1.0000,0.9841,0],
[1.0000,1.0000,0]
])

def winter():
    return numpy.array([
[0,0,1.0000],
[0,0.0159,0.9921],
[0,0.0317,0.9841],
[0,0.0476,0.9762],
[0,0.0635,0.9683],
[0,0.0794,0.9603],
[0,0.0952,0.9524],
[0,0.1111,0.9444],
[0,0.1270,0.9365],
[0,0.1429,0.9286],
[0,0.1587,0.9206],
[0,0.1746,0.9127],
[0,0.1905,0.9048],
[0,0.2063,0.8968],
[0,0.2222,0.8889],
[0,0.2381,0.8810],
[0,0.2540,0.8730],
[0,0.2698,0.8651],
[0,0.2857,0.8571],
[0,0.3016,0.8492],
[0,0.3175,0.8413],
[0,0.3333,0.8333],
[0,0.3492,0.8254],
[0,0.3651,0.8175],
[0,0.3810,0.8095],
[0,0.3968,0.8016],
[0,0.4127,0.7937],
[0,0.4286,0.7857],
[0,0.4444,0.7778],
[0,0.4603,0.7698],
[0,0.4762,0.7619],
[0,0.4921,0.7540],
[0,0.5079,0.7460],
[0,0.5238,0.7381],
[0,0.5397,0.7302],
[0,0.5556,0.7222],
[0,0.5714,0.7143],
[0,0.5873,0.7063],
[0,0.6032,0.6984],
[0,0.6190,0.6905],
[0,0.6349,0.6825],
[0,0.6508,0.6746],
[0,0.6667,0.6667],
[0,0.6825,0.6587],
[0,0.6984,0.6508],
[0,0.7143,0.6429],
[0,0.7302,0.6349],
[0,0.7460,0.6270],
[0,0.7619,0.6190],
[0,0.7778,0.6111],
[0,0.7937,0.6032],
[0,0.8095,0.5952],
[0,0.8254,0.5873],
[0,0.8413,0.5794],
[0,0.8571,0.5714],
[0,0.8730,0.5635],
[0,0.8889,0.5556],
[0,0.9048,0.5476],
[0,0.9206,0.5397],
[0,0.9365,0.5317],
[0,0.9524,0.5238],
[0,0.9683,0.5159],
[0,0.9841,0.5079],
[0,1.0000,0.5000]
])

def gray():
    return numpy.array([
[0,0,0],
[0.0159,0.0159,0.0159],
[0.0317,0.0317,0.0317],
[0.0476,0.0476,0.0476],
[0.0635,0.0635,0.0635],
[0.0794,0.0794,0.0794],
[0.0952,0.0952,0.0952],
[0.1111,0.1111,0.1111],
[0.1270,0.1270,0.1270],
[0.1429,0.1429,0.1429],
[0.1587,0.1587,0.1587],
[0.1746,0.1746,0.1746],
[0.1905,0.1905,0.1905],
[0.2063,0.2063,0.2063],
[0.2222,0.2222,0.2222],
[0.2381,0.2381,0.2381],
[0.2540,0.2540,0.2540],
[0.2698,0.2698,0.2698],
[0.2857,0.2857,0.2857],
[0.3016,0.3016,0.3016],
[0.3175,0.3175,0.3175],
[0.3333,0.3333,0.3333],
[0.3492,0.3492,0.3492],
[0.3651,0.3651,0.3651],
[0.3810,0.3810,0.3810],
[0.3968,0.3968,0.3968],
[0.4127,0.4127,0.4127],
[0.4286,0.4286,0.4286],
[0.4444,0.4444,0.4444],
[0.4603,0.4603,0.4603],
[0.4762,0.4762,0.4762],
[0.4921,0.4921,0.4921],
[0.5079,0.5079,0.5079],
[0.5238,0.5238,0.5238],
[0.5397,0.5397,0.5397],
[0.5556,0.5556,0.5556],
[0.5714,0.5714,0.5714],
[0.5873,0.5873,0.5873],
[0.6032,0.6032,0.6032],
[0.6190,0.6190,0.6190],
[0.6349,0.6349,0.6349],
[0.6508,0.6508,0.6508],
[0.6667,0.6667,0.6667],
[0.6825,0.6825,0.6825],
[0.6984,0.6984,0.6984],
[0.7143,0.7143,0.7143],
[0.7302,0.7302,0.7302],
[0.7460,0.7460,0.7460],
[0.7619,0.7619,0.7619],
[0.7778,0.7778,0.7778],
[0.7937,0.7937,0.7937],
[0.8095,0.8095,0.8095],
[0.8254,0.8254,0.8254],
[0.8413,0.8413,0.8413],
[0.8571,0.8571,0.8571],
[0.8730,0.8730,0.8730],
[0.8889,0.8889,0.8889],
[0.9048,0.9048,0.9048],
[0.9206,0.9206,0.9206],
[0.9365,0.9365,0.9365],
[0.9524,0.9524,0.9524],
[0.9683,0.9683,0.9683],
[0.9841,0.9841,0.9841],
[1.0000,1.0000,1.0000]
])
    
def bone():
    return numpy.array([
[0,0,0.0052],
[0.0139,0.0139,0.0243],
[0.0278,0.0278,0.0434],
[0.0417,0.0417,0.0625],
[0.0556,0.0556,0.0816],
[0.0694,0.0694,0.1007],
[0.0833,0.0833,0.1198],
[0.0972,0.0972,0.1389],
[0.1111,0.1111,0.1580],
[0.1250,0.1250,0.1771],
[0.1389,0.1389,0.1962],
[0.1528,0.1528,0.2153],
[0.1667,0.1667,0.2344],
[0.1806,0.1806,0.2535],
[0.1944,0.1944,0.2726],
[0.2083,0.2083,0.2917],
[0.2222,0.2222,0.3108],
[0.2361,0.2361,0.3299],
[0.2500,0.2500,0.3490],
[0.2639,0.2639,0.3681],
[0.2778,0.2778,0.3872],
[0.2917,0.2917,0.4062],
[0.3056,0.3056,0.4253],
[0.3194,0.3194,0.4444],
[0.3333,0.3385,0.4583],
[0.3472,0.3576,0.4722],
[0.3611,0.3767,0.4861],
[0.3750,0.3958,0.5000],
[0.3889,0.4149,0.5139],
[0.4028,0.4340,0.5278],
[0.4167,0.4531,0.5417],
[0.4306,0.4722,0.5556],
[0.4444,0.4913,0.5694],
[0.4583,0.5104,0.5833],
[0.4722,0.5295,0.5972],
[0.4861,0.5486,0.6111],
[0.5000,0.5677,0.6250],
[0.5139,0.5868,0.6389],
[0.5278,0.6059,0.6528],
[0.5417,0.6250,0.6667],
[0.5556,0.6441,0.6806],
[0.5694,0.6632,0.6944],
[0.5833,0.6823,0.7083],
[0.5972,0.7014,0.7222],
[0.6111,0.7205,0.7361],
[0.6250,0.7396,0.7500],
[0.6389,0.7587,0.7639],
[0.6528,0.7778,0.7778],
[0.6745,0.7917,0.7917],
[0.6962,0.8056,0.8056],
[0.7179,0.8194,0.8194],
[0.7396,0.8333,0.8333],
[0.7613,0.8472,0.8472],
[0.7830,0.8611,0.8611],
[0.8047,0.8750,0.8750],
[0.8264,0.8889,0.8889],
[0.8481,0.9028,0.9028],
[0.8698,0.9167,0.9167],
[0.8915,0.9306,0.9306],
[0.9132,0.9444,0.9444],
[0.9349,0.9583,0.9583],
[0.9566,0.9722,0.9722],
[0.9783,0.9861,0.9861],
[1.0000,1.0000,1.0000]
])

def copper():
    return numpy.array([
[0,0,0],
[0.0198,0.0124,0.0079],
[0.0397,0.0248,0.0158],
[0.0595,0.0372,0.0237],
[0.0794,0.0496,0.0316],
[0.0992,0.0620,0.0395],
[0.1190,0.0744,0.0474],
[0.1389,0.0868,0.0553],
[0.1587,0.0992,0.0632],
[0.1786,0.1116,0.0711],
[0.1984,0.1240,0.0790],
[0.2183,0.1364,0.0869],
[0.2381,0.1488,0.0948],
[0.2579,0.1612,0.1027],
[0.2778,0.1736,0.1106],
[0.2976,0.1860,0.1185],
[0.3175,0.1984,0.1263],
[0.3373,0.2108,0.1342],
[0.3571,0.2232,0.1421],
[0.3770,0.2356,0.1500],
[0.3968,0.2480,0.1579],
[0.4167,0.2604,0.1658],
[0.4365,0.2728,0.1737],
[0.4563,0.2852,0.1816],
[0.4762,0.2976,0.1895],
[0.4960,0.3100,0.1974],
[0.5159,0.3224,0.2053],
[0.5357,0.3348,0.2132],
[0.5556,0.3472,0.2211],
[0.5754,0.3596,0.2290],
[0.5952,0.3720,0.2369],
[0.6151,0.3844,0.2448],
[0.6349,0.3968,0.2527],
[0.6548,0.4092,0.2606],
[0.6746,0.4216,0.2685],
[0.6944,0.4340,0.2764],
[0.7143,0.4464,0.2843],
[0.7341,0.4588,0.2922],
[0.7540,0.4712,0.3001],
[0.7738,0.4836,0.3080],
[0.7937,0.4960,0.3159],
[0.8135,0.5084,0.3238],
[0.8333,0.5208,0.3317],
[0.8532,0.5332,0.3396],
[0.8730,0.5456,0.3475],
[0.8929,0.5580,0.3554],
[0.9127,0.5704,0.3633],
[0.9325,0.5828,0.3712],
[0.9524,0.5952,0.3790],
[0.9722,0.6076,0.3869],
[0.9921,0.6200,0.3948],
[1.0000,0.6324,0.4027],
[1.0000,0.6448,0.4106],
[1.0000,0.6572,0.4185],
[1.0000,0.6696,0.4264],
[1.0000,0.6820,0.4343],
[1.0000,0.6944,0.4422],
[1.0000,0.7068,0.4501],
[1.0000,0.7192,0.4580],
[1.0000,0.7316,0.4659],
[1.0000,0.7440,0.4738],
[1.0000,0.7564,0.4817],
[1.0000,0.7688,0.4896],
[1.0000,0.7812,0.4975]
])
    
def pink():
    return numpy.array([
[0.1179,0,0],
[0.1959,0.1029,0.1029],
[0.2507,0.1455,0.1455],
[0.2955,0.1782,0.1782],
[0.3343,0.2057,0.2057],
[0.3691,0.2300,0.2300],
[0.4009,0.2520,0.2520],
[0.4303,0.2722,0.2722],
[0.4579,0.2910,0.2910],
[0.4839,0.3086,0.3086],
[0.5085,0.3253,0.3253],
[0.5320,0.3412,0.3412],
[0.5546,0.3563,0.3563],
[0.5762,0.3709,0.3709],
[0.5971,0.3849,0.3849],
[0.6172,0.3984,0.3984],
[0.6367,0.4115,0.4115],
[0.6557,0.4241,0.4241],
[0.6741,0.4364,0.4364],
[0.6920,0.4484,0.4484],
[0.7094,0.4600,0.4600],
[0.7265,0.4714,0.4714],
[0.7431,0.4825,0.4825],
[0.7594,0.4933,0.4933],
[0.7664,0.5175,0.5040],
[0.7732,0.5407,0.5143],
[0.7800,0.5628,0.5245],
[0.7868,0.5842,0.5345],
[0.7935,0.6048,0.5443],
[0.8001,0.6247,0.5540],
[0.8067,0.6440,0.5634],
[0.8133,0.6627,0.5727],
[0.8197,0.6809,0.5819],
[0.8262,0.6986,0.5909],
[0.8325,0.7159,0.5998],
[0.8389,0.7328,0.6086],
[0.8452,0.7493,0.6172],
[0.8514,0.7655,0.6257],
[0.8576,0.7813,0.6341],
[0.8637,0.7968,0.6424],
[0.8698,0.8120,0.6506],
[0.8759,0.8270,0.6587],
[0.8819,0.8416,0.6667],
[0.8879,0.8560,0.6746],
[0.8938,0.8702,0.6824],
[0.8997,0.8842,0.6901],
[0.9056,0.8979,0.6977],
[0.9114,0.9114,0.7052],
[0.9172,0.9172,0.7272],
[0.9230,0.9230,0.7485],
[0.9287,0.9287,0.7692],
[0.9344,0.9344,0.7893],
[0.9400,0.9400,0.8090],
[0.9456,0.9456,0.8282],
[0.9512,0.9512,0.8469],
[0.9567,0.9567,0.8653],
[0.9623,0.9623,0.8832],
[0.9677,0.9677,0.9008],
[0.9732,0.9732,0.9181],
[0.9786,0.9786,0.9351],
[0.9840,0.9840,0.9517],
[0.9894,0.9894,0.9681],
[0.9947,0.9947,0.9842],
[1.0000,1.0000,1.0000]
])