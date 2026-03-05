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
import math
import copy
from io import StringIO

from STAR_BME.lib import pybme
from STAR_BME.gui.stbme2qgis import saveAndAddVectorLayer2Qgis
from STAR_BME.gui.main_mplcolorbar import ColorBarDockWgt
from STAR_BME.gui.ui.ui_SetDataDlg import Ui_SetDataDlg

import star_variable
WORKING_PATH = star_variable.WORKING_PATH
SYS_ENCODING = star_variable.SYS_ENCODING
DEFAULT_ENCODING = star_variable.DEFAULT_ENCODING


class SetDataDlg(QDialog,Ui_SetDataDlg):
  def __init__(self,iface = None, MainDlg = None):
    super(SetDataDlg,self).__init__(None) # for Mac, old windows: super(SetDataDlg,self).__init__(MainDlg)
    self.iface=iface
    self.MainDlg=MainDlg
    
    self.ui=Ui_SetDataDlg()
    self.ui.setupUi(self)
    
    #old QprogressDialog for load from layer
    # self.qpgd = QProgressDialog(self)
    # self.qpgd.setWindowModality(Qt.WindowModal)
    # self.qpgd.setAutoClose(False)

    # Hide "Histogram" type
    idx = self.ui.comboBox_softpdftype.findText("Histogram")
    self.ui.comboBox_softpdftype.removeItem(idx)
    self.ui.label_soft_2.setText("")
    self.ui.label_soft_3.setText("")
    self.ui.comboBox_soft_2.hide()
    self.ui.comboBox_soft_3.hide()
    # Hide "User Defined" type
    #idx = self.ui.comboBox_inputformat.findText(QString("User Defined"))
    #self.ui.comboBox_inputformat.removeItem(idx)
    #change combobox setting
    #self.change()

    self.ui.pushButton_hardselect.clicked.connect(lambda clicked, flag = "hard":self.selectDataFrom(flag))
    self.ui.pushButton_softselect.clicked.connect(lambda clicked, flag = "soft":self.selectDataFrom(flag))
    
    self.ui.comboBox_inputformat.currentIndexChanged[int].connect( self.change )
    self.ui.tableWidget_harddata.verticalScrollBar().valueChanged[int].connect( self.updateHardDataPreview )
    self.ui.tableWidget_softdata.verticalScrollBar().valueChanged[int].connect( self.updateSoftDataPreview )
    self.ui.pushButton_create.clicked.connect(self.create)
    self.ui.pushButton_cancel.clicked.connect(self.cancel)
    
    self.data_source_type = None
    
    self.hard_layer = None
    self.hard_data_path = ""
    self.hard_data_delimiter = ","
    self.hard_data_skiprows = 0
    self.hard_data_count = 0
    self.hard_file_obj = None
    self.hard_mutex = QMutex()
    self.hard_thread = None

    self.soft_layer = None
    self.soft_data_path = ""
    self.soft_data_delimiter = ","
    self.soft_data_skiprows = 0
    self.soft_data_count = 0
    self.soft_file_obj = None
    self.soft_mutex = QMutex()
    self.soft_thread = None
    
    self.grid_param = () #xmin xmax ymin ymax tmin tmax xn yn tn

  def selectDataFrom( self, flag ):
      from_that = str(eval("self.ui.comboBox_"+flag+"from").currentText())
      if from_that == "File":
          self.loadDataFromFile( flag )
      elif from_that == "Layer":
          self.loadDataFromLayer( flag )
      elif from_that == "Grid Input":
          self.loadDataFromGridInput( flag )
      elif from_that == 'Shape File':
          self.loadDataFromShapeFile( flag )
      elif from_that == "Shape File (With Time Input)":
          self.loadDataFromShapeFileWithTimeInput( flag )
      
  def updateHardDataPreview(self,int_):
      if self.getDataSourceType() in ["File", "ShapeFile", "Layer", "Grid Input"]:
          self._updateDataPreview(
              int_,self.hard_mutex,
              self.ui.tableWidget_harddata,
              self.hard_file_obj)

  def updateSoftDataPreview(self,int_):
      if self.getDataSourceType() in ["File", "ShapeFile", "Layer"]:
          self._updateDataPreview(
              int_,self.soft_mutex,
              self.ui.tableWidget_softdata,
              self.soft_file_obj)
                              
  def _updateDataPreview(self,int_,mutex,previewer,fileobj):
          try:
              mutex.lock() 
              if int_ == previewer.verticalScrollBar().maximum():
                  if fileobj:      
                      for i in range(50):
                          line = fileobj.readline()
                          if line:            
                              values = line.split(",")
                              values[-1]=values[-1].rstrip("\n")
                              previewer.setRowCount(previewer.rowCount()+1)
                              for j in range(len(values)):
                                  try:
                                      witem = QTableWidgetItem(values[j])
                                  except UnicodeDecodeError:
                                      witem = QTableWidgetItem(values[j])
                                  previewer.setItem(previewer.rowCount() - 1, j, witem)      
                          else:
                              return
          finally:
              mutex.unlock()
              
  def loadDataFromFile(self, flag):
      dlg = LoadFileDlg( flag, self )
      if dlg.exec_():
          self.previewDataFromeFile(flag, str(dlg.file_path), dlg.delimiter, dlg.start_row - 1)
          self.data_source_type = "File"

  def setFileObjFromThread(self,arg):
      fileobj=arg[0]
      flag=arg[1]
      if flag == "hard":
          self.hard_file_obj = fileobj
      elif flag == "soft":
          self.soft_file_obj = fileobj

  def setFinishedFromThread(self,arg):
      flag= arg[0]
      if flag == "hard":
          self.ui.pushButton_stophard.setDisabled(True)
      elif flag == "soft":
          self.ui.pushButton_stopsoft.setDisabled(True)

  def setDataCountFromThread(self,arg):
      count = arg[0]
      flag = arg[1]
      if flag == "hard":
          self.hard_data_count = count
      elif flag == "soft":
          self.soft_data_count = count
             
  def setTitleFromThread(self,arg):
      hastitle = arg[0]
      titlelist = arg[1]
      try:
          titlelist = [ title.encode().decode( DEFAULT_ENCODING ) for title in titlelist ]
          #titlelist = [ title.decode( DEFAULT_ENCODING ) for title in titlelist ]
      except UnicodeDecodeError:
          titlelist = [ title.decode( SYS_ENCODING ) for title in titlelist ]
      flag=arg[2]

      if flag == "hard":
          tablewidget = self.ui.tableWidget_harddata
      elif flag == "soft":
          tablewidget = self.ui.tableWidget_softdata

          
      tablewidget.clear()
      tablewidget.setRowCount(0)
      tablewidget.setColumnCount(0)
      
      tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
      tablewidget.setColumnCount(len(titlelist))
      if arg[0]: #hastitle
          tablewidget.setHorizontalHeaderLabels(titlelist)
      else: #notitle
          titlelist = list(map(str,range(len(titlelist))))
          tablewidget.setHorizontalHeaderLabels(titlelist)

      if flag == "hard":
          button=["x","y","t","z"]
      elif flag == "soft":
          button=["soft_x","soft_y","soft_t"]
          if self.ui.comboBox_inputformat.currentIndex() == 0: #User Defined
              button+=["soft_1","soft_2","soft_3"]
          elif self.ui.comboBox_inputformat.currentIndex() == 1 or\
               self.ui.comboBox_inputformat.currentIndex() == 2:    # 1 => Gaussian , 2 => Uniform
              button+=["soft_1","soft_2"]

      for index,value in enumerate(titlelist):
          if len(value) == 1:
              titlelist[index] = " "+value+" "

      for i in button:
          eval("self.ui.comboBox_"+i).clear()
          eval("self.ui.comboBox_"+i).addItems(titlelist)
          if self.data_source_type in ["Layer", "ShapeFile"]:
              if i in [ 'x', 'y' ]:
                  index2 = eval("self.ui.comboBox_"+i).findText("Coordinate_{c}".format(c = i))
                  if index2 == -1:
                      index2 = eval("self.ui.comboBox_"+i).findText(" "+i+" ")
              else:
                  index2 = eval("self.ui.comboBox_"+i).findText(" "+i+" ")
          else:
              index2 = eval("self.ui.comboBox_"+i).findText(" "+i+" ")
          if index2 != -1:
              eval( "self.ui.comboBox_" + i ).setCurrentIndex( index2 )
          else:
              if self.data_source_type in ["Layer", "ShapeFile"]:
                  eval("self.ui.comboBox_"+i).setCurrentIndex(2)
              else:
                  eval("self.ui.comboBox_"+i).setCurrentIndex(0)
              
      #add None for spatial only
      if flag == "hard":
          self.ui.comboBox_t.insertItem(0,'None')
      elif flag == "soft":
          self.ui.comboBox_soft_t.insertItem(0,'None')

  def addAttributeFromThread(self,arg):
      try:
          eval("self."+arg[2]+"_mutex").lock()
          row = arg[0]
          values = arg[1]
          flag = arg[2]

          if flag == "hard":
              self.ui.tableWidget_harddata.setRowCount(row+1)
          elif flag == "soft":
              self.ui.tableWidget_softdata.setRowCount(row+1)

          for i in range(len(values)):
              try:
                  #witem=QTableWidgetItem( values[i].decode( DEFAULT_ENCODING ) )
                  witem=QTableWidgetItem( values[i].encode().decode( DEFAULT_ENCODING ) )
              except UnicodeDecodeError:
                  witem=QTableWidgetItem( values[i].decode( SYS_ENCODING ) )
              eval("self.ui.tableWidget_"+flag+"data").setItem(row,i,witem)
      finally:
         eval("self."+arg[2]+"_mutex").unlock()
      
  def create(self):
      
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
                  if os.path.exists( shp_file_path ):
                      addFileToDict( shp_file_path, shp_file_dict, shp_file_type)
              
              self.MainDlg.vector_layer_data[data_type] = shp_file_dict  
          else: 
              self.MainDlg.vector_layer_data[data_type] = {}
                 
      
      self.qpgd = QProgressDialog(self)
      self.qpgd.setWindowModality(Qt.WindowModal)
      
      if self.ui.tabWidget.count() == 2: # hard and soft
          
          #Decide which data will be processed
          has_hard = False
          has_soft = False
          if not self.ui.comboBox_x.currentIndex() == -1:
              has_hard = True
              hard_skiprows_temp = self.hard_data_skiprows
              hard_delimiter_temp = self.hard_data_delimiter 
          if not self.ui.comboBox_soft_x.currentIndex() == -1:
              has_soft = True
              soft_skiprows_temp = self.soft_data_skiprows
              soft_delimiter_temp = self.soft_data_delimiter
          
          #check dimension ( spatial_only or not )
          if has_hard and has_soft:
              index_t_h = self.ui.comboBox_t.currentIndex()
              index_t_s = self.ui.comboBox_soft_t.currentIndex()
              if index_t_h == 0:
                  if index_t_s == 0: #OK
                      pass
                  else: # dimension error
                      QMessageBox.critical(self,"Dimension Error","Hard And Soft Data Has Different Dimensions.\n"
                      "Please Check the Value of Combo box T.")
                      self.qpgd.reset()
                      self.qpgd.close()
                      return False
              else:
                  if index_t_s == 0: # dimension error
                      QMessageBox.critical(self,"Dimension Error","Hard And Soft Data Has Different Dimensions.\n"
                      "Please Check the Value of Combo box T.")
                      self.qpgd.reset()
                      self.qpgd.close()
                      return False
                  else: #OK
                      pass
                  
          
          #clean
          self.MainDlg.cleanWorkSpaceHardSoftLayer()    
          #Process hard data if has data
          if has_hard:
              try:
                float(self.ui.comboBox_x.currentText())
                title = 0
              except ValueError:
                title = 1 #has title
                
              index_x = self.ui.comboBox_x.currentIndex()
              index_y = self.ui.comboBox_y.currentIndex()
              index_t = self.ui.comboBox_t.currentIndex()
              if index_t == 0: #None, spatial only
                  index_t = index_x +1  #give the index just can run and will revise later
                  self.MainDlg.setSpatialOnly(True)
              else:
                  self.MainDlg.setSpatialOnly(False)
              index_t -= 1
              index_z = self.ui.comboBox_z.currentIndex()
              
              if self.getDataSourceType() in [ "File", "Layer", "ShapeFile" ]:
                  datapath = self.hard_data_path
                  
              usecols=(index_x,index_y,index_t,index_z)
              
              skiprows = hard_skiprows_temp + title
              delimiter = hard_delimiter_temp
    
              h_data_temp = pybme.HardData()
              h_data_temp.setProgressDialog(self.qpgd)
              
              h_data_temp.setProgressAutoClose(False)
              
              try:
                  
                  if not h_data_temp.setCoordinateFromFile(datapath, usecols = usecols[0:3], skiprows = skiprows, delimiter = delimiter):
                      #QMessageBox.information(None,"Cancel","Creating BMEobj is Cancel!\n") 
                      self.qpgd.reset()
                      self.qpgd.close()
                      return False
                       
                  if not h_data_temp.setValueFromFile(datapath, usecols = usecols[3:4], skiprows = skiprows, delimiter = delimiter):
                      self.qpgd.reset()
                      self.qpgd.close()
                      return False
              except ValueError as e:
                  h_data_temp.setProgressAutoClose(True)
                  h_data_temp.progress_dialog.close()
                  import traceback
                  traceback.print_exc()
                  QMessageBox.critical(self, "Data Error",
                                       "Please Check Input Data (Hard).\n"
                                       "Error: {err}".format(err=str(e)))
                  self.qpgd.reset()
                  self.qpgd.close()
                  return False
              
              #if spatial only, let t all equal to one
              if self.MainDlg.isSpatialOnly():
                  h_data_temp.t[:] = 1

              if not h_data_temp.setGridData():
                  self.qpgd.reset()
                  self.qpgd.close()
                  return False
              h_data_temp.updateDataInfo()
              
              if has_hard and has_soft:
                  pass # continue to process soft
              else: #close qpgd
                  h_data_temp.progress_dialog.close()
                
          #Process soft data if has data
          if has_soft:
              try:
                  float(self.ui.comboBox_soft_x.currentText())
                  title = 0
              except ValueError:
                  title = 1 #has title
    
              index_x = self.ui.comboBox_soft_x.currentIndex()
              index_y = self.ui.comboBox_soft_y.currentIndex()
              index_t = self.ui.comboBox_soft_t.currentIndex()
              
              if index_t == 0: # 0, spatial only
                  index_t = index_x +1  #give the index just can run and will revise later
                  self.MainDlg.setSpatialOnly(True)
              else:
                  self.MainDlg.setSpatialOnly(False)
              index_t -= 1
              soft1 = self.ui.comboBox_soft_1.currentIndex()
              soft2 = self.ui.comboBox_soft_2.currentIndex()
              soft3 = self.ui.comboBox_soft_3.currentIndex()
              if self.getDataSourceType() in [ "File", "Layer", "ShapeFile" ]:
                  datapath = self.soft_data_path
                  
              usecols = (index_x, index_y, index_t,
                         soft1, soft2, soft3)
              
              skiprows = soft_skiprows_temp + title
              delimiter = soft_delimiter_temp
              
              s_data_temp = pybme.SoftData()
              s_data_temp.setProgressDialog(self.qpgd)
              
              s_data_temp.setPdfType(str(self.ui.comboBox_softpdftype.currentText()))
              s_data_temp.setInputFormat(str(self.ui.comboBox_inputformat.currentText()))
              
              s_data_temp.setProgressAutoClose(False)
              try:
                  
                 if not s_data_temp.setCoordinateFromFile(datapath, usecols = usecols[0:3], skiprows = skiprows, delimiter = delimiter):
                      self.qpgd.reset()
                      self.qpgd.close()
                      return False
                  
                 if not s_data_temp.setValueFromFile(datapath, usecols = usecols[3:5], skiprows = skiprows, delimiter = delimiter):
                      self.qpgd.reset()
                      self.qpgd.close()
                      return False
      
              except ValueError as e:
                  s_data_temp.setProgressAutoClose(True)
                  s_data_temp.progress_dialog.close()
                  import traceback
                  traceback.print_exc()
                  QMessageBox.critical(self, "Data Error",
                                       "Please Check Input Data (Soft).\n"
                                       "Error: {err}".format(err=str(e)))
                  self.qpgd.reset()
                  self.qpgd.close()
                  return False
              
              #if spatial only, let t all equal to one
              if self.MainDlg.isSpatialOnly():
                  s_data_temp.t[:] = 1
                  
              if not s_data_temp.setGridData():
                  self.qpgd.reset()
                  self.qpgd.close()
                  return False
              s_data_temp.updateDataInfo()
              
              s_data_temp.setProgressAutoClose(True)
              s_data_temp.progress_dialog.close()

    
    
          if not has_hard and not has_soft:
              self.qpgd.reset()
              self.qpgd.close()
              QMessageBox.critical(self,"No Input Data","Please Input Hard or Soft Data")
              return
          elif has_hard and not has_soft:
              
              h_data_temp.has_data = True
              self.MainDlg.bmeobj.hard_data = h_data_temp
              self.hard_data_skiprows = hard_skiprows_temp
              self.hard_data_delimiter = hard_delimiter_temp
              
              #find renderer min and max
              rdr_min = h_data_temp.z_min_without_nan
              rdr_max = h_data_temp.z_max_without_nan
              
              #add layer to qgis
              saveAndAddVectorLayer2Qgis(self.iface, self.MainDlg,
                                                    h_data_temp, "Hard",
                                                    rdr_min, rdr_max )
              self.MainDlg.bmeobj.soft_data = pybme.SoftData()
              
              
          elif has_hard and has_soft: 
              h_data_temp.has_data = True
              self.MainDlg.bmeobj.hard_data = h_data_temp
              self.hard_data_skiprows = hard_skiprows_temp
              self.hard_data_delimiter = hard_delimiter_temp
              
              s_data_temp.has_data = True
              self.MainDlg.bmeobj.soft_data = s_data_temp
              self.soft_data_skiprows = soft_skiprows_temp
              self.soft_data_delimiter = soft_delimiter_temp
              
              #find renderer min and max
              rdr_min_h = h_data_temp.z_min_without_nan
              rdr_max_h = h_data_temp.z_max_without_nan
              rdr_min_s = s_data_temp.z_min_without_nan
              rdr_max_s = s_data_temp.z_max_without_nan
              rdr_min = min(rdr_min_h,rdr_min_s)
              rdr_max = max(rdr_max_h,rdr_max_s)
              
              #add layer to qgis
              saveAndAddVectorLayer2Qgis(self.iface, self.MainDlg,
                                                    h_data_temp, "Hard",
                                                    rdr_min, rdr_max )
              saveAndAddVectorLayer2Qgis(self.iface, self.MainDlg,
                                                    s_data_temp, "Soft",
                                                    rdr_min, rdr_max )
              
          elif not has_hard and has_soft:
              self.MainDlg.bmeobj.hard_data = pybme.HardData()
              
              s_data_temp.has_data = True
              self.MainDlg.bmeobj.soft_data = s_data_temp
              self.soft_data_skiprows = soft_skiprows_temp
              self.soft_data_delimiter = soft_delimiter_temp
              
              rdr_min = s_data_temp.z_min_without_nan
              rdr_max = s_data_temp.z_max_without_nan
              
              saveAndAddVectorLayer2Qgis(self.iface, self.MainDlg,
                                                    s_data_temp, "Soft",
                                                    rdr_min, rdr_max )   
              
          else:
              raise TypeError("My Fault")
          
          #add file to shelve ( e.g. main.vector_layer_data )
          addShpFileDataToMain('Hard', has_hard)
          addShpFileDataToMain('Soft', has_soft)
          
         
          self.ui.pushButton_cancel.setText("Close")
          self.MainDlg.setStage(10)
          self.MainDlg.buttonsUpdate()
          self.MainDlg.dirty = True
    
          #setting data visualization window
          # self.parent().ui.dockWidget_datavisualization.initializeUi()

          #show colorbar
          self.MainDlg.color_bar.update(rdr_min,rdr_max,'jet')
          self.MainDlg.color_bar.show()
          
          self.MainDlg.time_bar.updateAll()
          self.MainDlg.time_bar.show()
          
          
          QMessageBox.information(self,"OK","Done! BMEobj is present.\n")
          
          if self.MainDlg.isSpatialOnly():
              self.MainDlg.time_bar.ui.label_time.setDisabled(True)
              self.MainDlg.time_bar.ui.pushButton_previous.setDisabled(True)
              self.MainDlg.time_bar.ui.horizontalSlider.setDisabled(True)
              self.MainDlg.time_bar.ui.pushButton_next.setDisabled(True)
              self.MainDlg.tool_view_data.action().setDisabled(True)
              self.MainDlg.tool_histogram_view.action().setDisabled(True)
          self.accept()
          return True
      
      #process EstimatedData
      elif self.ui.tabWidget.count() == 1: #estimated
          #check t
          if not self.MainDlg.isSpatialOnly() and  self.ui.comboBox_t.currentIndex() == 0:
              QMessageBox.critical(self,"No Input Data T","You must specify a source for location T data")
              self.qpgd.reset()
              self.qpgd.close()
              return
          #Decide which data will be processed
          if not self.ui.comboBox_x.currentIndex() == -1:
              hard_skiprows_temp = self.hard_data_skiprows
              hard_delimiter_temp = self.hard_data_delimiter
          else:
              QMessageBox.critical(self,"No Input Data","You must specify a source for location data first")
              self.qpgd.reset()
              self.qpgd.close()
              return
              
          #Process Estimated data
          try:
            float(self.ui.comboBox_x.currentText())
            title = 0
          except ValueError:
            title = 1 #has title
            
          index_x = self.ui.comboBox_x.currentIndex()
          index_y = self.ui.comboBox_y.currentIndex()
          index_t = self.ui.comboBox_t.currentIndex()
          
          
          if self.MainDlg.isSpatialOnly():
              index_t = index_x +1  #give the index just can run and will revise later
                  
          index_t -= 1
          
          if self.getDataSourceType() in [ "File", "Layer", "ShapeFile", 'Grid Input' ]:
              datapath = self.hard_data_path
                  
          usecols=(index_x,index_y,index_t)
          
          skiprows = hard_skiprows_temp + title
          delimiter = hard_delimiter_temp

          e_data_temp = pybme.EstimatedData()
          e_data_temp.setProgressDialog(self.qpgd)
          
          try:
              
              if not e_data_temp.setCoordinateFromFile(datapath, usecols = usecols[0:3], skiprows = skiprows, delimiter = delimiter):
                  #QMessageBox.information(None,"Cancel","Creating BMEobj is Cancel!\n") 
                  self.qpgd.reset()
                  self.qpgd.close()
                  return False
          except ValueError:
              e_data_temp.setProgressAutoClose(True)
              e_data_temp.progress_dialog.close()
              QMessageBox.critical(self, "Data Error", "Please Check Input Data.\n"
                                         "It Cannot be Convert to Float.")
              self.qpgd.reset()
              self.qpgd.close()
              return False
          
          #if spatial only, let t all equal to one
          if self.MainDlg.isSpatialOnly():
              e_data_temp.t[:] = 1
              
          e_data_temp.setProgressAutoClose(True)
          e_data_temp.progress_dialog.close()
          
          self.MainDlg.bmeobj.estimated_data = e_data_temp
          self.hard_data_skiprows = hard_skiprows_temp
          self.hard_data_delimiter = hard_delimiter_temp
          
          self.ui.pushButton_cancel.setText("Close") 
          self.MainDlg.dirty = True
          
          #whether to show estimate dialog
          if not self.MainDlg.bmeobj.covariance.models == []:
              self.MainDlg.stage = 30
              self.MainDlg.buttonsUpdate()
              
    
          QMessageBox.information(self,"OK","Input Estimated Data is Finished!\n")
          
          #set Shape File Type To Original 
          from_that = str( self.ui.comboBox_hardfrom.currentText() )
          if from_that in [ "File", "Layer", "Grid Input" ]:
              self.MainDlg.estimated_shape_file_type = QgsWkbTypes.PointGeometry
          elif from_that == [ 'Shape File', "Shape File (With Time Input)" ]:
              pass #already set

          self.accept() 
          return True
  
  def cancel(self):
      self._stopThread(self.hard_thread)
      self._stopThread(self.soft_thread)        
      self.reject()

  def _stopThread(self,thread):
      try:
          if thread.isRunning():
              self.thread.stopped = True
              self.thread.wait()
      except AttributeError:
          pass

  def change(self):
    if self.ui.comboBox_inputformat.currentText() == "User Defined":
      self.ui.label_soft_1.setText("Numer of Limits:")
      self.ui.label_soft_2.setText("")
      self.ui.label_soft_3.setText("")
      self.ui.comboBox_soft_2.hide()
      self.ui.comboBox_soft_3.hide()
    elif self.ui.comboBox_inputformat.currentText() == "Gaussian":
      self.ui.label_soft_1.setText("Mean:")
      self.ui.label_soft_2.setText("Variance:")
      self.ui.label_soft_3.setText("")
      self.ui.comboBox_soft_2.show()
      self.ui.comboBox_soft_3.hide()
    elif self.ui.comboBox_inputformat.currentText() == "Uniform":
      self.ui.label_soft_1.setText("Lower bound:")
      self.ui.label_soft_2.setText("Upper bound:")
      self.ui.label_soft_3.setText("")
      self.ui.comboBox_soft_2.show()
      self.ui.comboBox_soft_3.hide()
      
  def getDataGenerator(self,datapath,usecols,skiprows=0):
      if datapath.endswith(".csv"):
          fobj = open(datapath,"r")
          [fobj.readline() for i in range(skiprows)]
          for line in fobj:
              line=line.split(",")
              line[-1] = line[-1].rstrip("\n")
              line = list(map(lambda x,i:x[i],[line]*len(usecols),usecols))
              yield list(map(float,line)) 

  def loadDataFromLayer(self, flag):
    svDlg=SelectVLayerDlg(self)
    layerlist=[]
    layermap = QgsProject.instance().mapLayers()
    for name, layer in layermap.items():
        if layer.type() == QgsMapLayer.VectorLayer:
            if layer.isValid():
                svDlg.ui.comboBox.addItem(name)
                layerlist.append(layer)
    if svDlg.exec_():
      i = svDlg.ui.comboBox.currentIndex()
      if i == -1:
        return
    
      #get layer
      self.layer = layerlist[i]
      
      data_path = str(os.path.join(WORKING_PATH, flag+"_data_path.csv" ))
      
      self.convertShapeFileToCsv( self.layer, file_path = data_path )
      self.previewDataFromeFile( flag, data_path, ",", 0 )
    
      self.data_source_type = "Layer"
    
  def loadDataFromGridInput( self, flag ):
      self.grid_dlg = LoadGridDlg(self)
      if self.grid_dlg.exec_():
          
          file_path = str(os.path.join(WORKING_PATH, flag+"_data_path.csv" ))
          if not self.saveGridFile( self.grid_param, file_path ):
              return

          self.previewDataFromeFile(flag, file_path, delimiter = ',', skiprows = 0)
          self.data_source_type = "Grid Input"
          
  def saveGridFile( self, grid_param, file_path ):
      param = grid_param
      x_lim = numpy.linspace(param[0],param[1],param[6])
      y_lim = numpy.linspace(param[2],param[3],param[7])
      t_lim = numpy.linspace(param[4],param[5],param[8])
      
      try:   
          x = numpy.kron(numpy.ones((1,param[7]*param[8])), x_lim).T
          y = numpy.kron( y_lim, numpy.ones((1,param[6])) )
          y = numpy.kron(numpy.ones((1,param[8])), y).T
          t = numpy.kron( t_lim, numpy.ones((1,param[6]*param[7])) ).T
          f = open( file_path, 'w')
          f.write( 'x,y,t\n' )
          for ([xi],[yi],[ti]) in zip(x,y,t):
              f.write( ','.join( map(str,(xi,yi,ti) ) ) +'\n' )
            
          f.close()
              
      except MemoryError:
          QMessageBox.critical(self,"Memory Error","Cannot create such a huge dataset\n")
          return False
      except ValueError:
          QMessageBox.critical(self,"Value Error","Cannot create such a huge dataset (Array is too big).\n")
          return False
      
      return True
                            
  def getDataSourceType(self):
      return self.data_source_type

  def thread_connect(self,thrd,sig_slot_pair):
      for sig,slot in sig_slot_pair:
          getattr( thrd, sig )[object].connect( slot )

  def loadDataFromShapeFile( self, flag):
      shp_file_path_temp = QFileDialog.getOpenFileName(self,"Load Data File",
                                                     self.parent().last_opened_folder,
                                                     "Shape Files (*.shp)")
      if not shp_file_path_temp:
          return
      else:
          self.parent().updateLastOpenedFolder( shp_file_path_temp )
          shp_file_path = str(shp_file_path_temp)
          #use shapefile to make fileobj
          data_path = str(os.path.join(WORKING_PATH, flag+"_data_path.csv" ))
          OpenShp = QgsVectorLayer(shp_file_path,"shapefile","ogr")
          if self.ui.tabWidget.count() == 1: #estimated
              self.MainDlg.estimated_shape_file_type = OpenShp.geometryType()
              self.MainDlg.estimated_shape_file_path = shp_file_path
          self.convertShapeFileToCsv( OpenShp, file_path = data_path )
          self.previewDataFromeFile( flag, data_path, ",", 0 )
          self.data_source_type = "ShapeFile"

  def loadDataFromShapeFileWithTimeInput( self, flag ):
      self.dlg = SelectShpDlg( self )
      if self.dlg.exec_():
          tmin, tmax, tn = self.dlg.tmin, self.dlg.tmax,self. dlg.tn
          shp_file_path = self.dlg.shp_file_path
      else:
          return
      
      shp_file_path = str(shp_file_path)
      
      #use shapefile to make fileobj
      data_path = str(os.path.join(WORKING_PATH, flag+"_data_path.csv" ))
      OpenShp = QgsVectorLayer(shp_file_path,"shapefile","ogr")
      #if self.ui.tabWidget.count() == 1: #estimated  // is always  "estimated"
      self.MainDlg.estimated_shape_file_type = OpenShp.geometryType()
      self.MainDlg.estimated_shape_file_path = shp_file_path
      self.convertShapeFileToCsv( OpenShp, file_path = data_path, use_t_input = ( tmin, tmax, tn ) )
      self.previewDataFromeFile( flag, data_path, ",", 0 )
      self.data_source_type = "ShapeFile"
                    
  def convertShapeFileToCsv( self, shp_obj, file_path, use_t_input = None ): 
        
        
        if use_t_input:
            f_obj = StringIO()  
            OpenShp = shp_obj
            
            #Write Field name
            f_obj.write( ",".join( [ 'x', 'y', 't' ] ) +'\n')
            
            
            #get all coordinate
            coord_list = []
            for f in OpenShp.getFeatures():
        
                #get coord
                coord_x = str( f.geometry().centroid().asPoint().x() )
                coord_y = str( f.geometry().centroid().asPoint().y() )
                coord_list.append( [ coord_x, coord_y ] )
            
            t_list = numpy.linspace( *use_t_input ) 
            for x,y in coord_list:
                for t in t_list:
                    f_obj.write( ",".join( [ x, y, str(t) ] ) +'\n' )
                    
    
            f_obj.seek( 0 )
            out_f = open( file_path, 'w' )
            out_f.write( f_obj.read() )
            out_f.close()
            f_obj.close()
            return
        
        else:
                
            f_obj = StringIO()  
            OpenShp = shp_obj
            OpenShp_dp = OpenShp.dataProvider()
            
            #Write Field name
            fd_list = [str( fd.name() ) for fd in OpenShp_dp.fields().values()]
            
            f_obj.write( ",".join( [ 'Coordinate_x', 'Coordinate_y' ] + fd_list ) +'\n')
            
            
            for f in OpenShp.getFeatures():
                #get coord
                coord_x = str( f.geometry().centroid().asPoint().x() )
                coord_y = str( f.geometry().centroid().asPoint().y() )
                
                # QGIS 3: Use attributes() instead of attributeMap().values()
                v_list = [ str( v ) for v in f.attributes() ]
                f_obj.write( ",".join( [ coord_x, coord_y ] + v_list ) +'\n' )
                    
    
            f_obj.seek( 0 )
            out_f = open( file_path, 'w' )
            out_f.write( f_obj.read().encode( SYS_ENCODING ) )
            out_f.close()
            f_obj.close()
            return

  def previewDataFromeFile( self, flag, path, delimiter, skiprows ):
      setattr( self, flag + '_data_path', path )
      setattr( self, flag + '_data_delimiter', delimiter )
      setattr( self, flag + '_data_skiprows', skiprows )
      setattr( self, flag+'_thread', LoadFileThread( path, flag,
                                                     start_row = skiprows + 1,
                                                     delimiter = delimiter,
                                                     parent = self ) )
      thread =  getattr( self, flag + '_thread' )
      thread.start()
      thread.wait()
          
                   
class LoadFileThread(QThread):
    
    settitle = pyqtSignal( object )
    setdatacount = pyqtSignal( object )
    setfileobj = pyqtSignal( object )
    addattribute = pyqtSignal( object )

    def __init__( self, filepath, flag,
                  start_row = 1,
                  delimiter = ',',
                  parent = None ):
        super(LoadFileThread,self).__init__( parent )
        self.mutex = QMutex()
        
        self.filepath = filepath
        self.flag = flag
        self.start_raw = start_row
        self.csv_delimiter = delimiter

        self.stopped = False
        
        self.sig_slot_connect( 
            [
                ["settitle",parent.setTitleFromThread],
                ["setdatacount",parent.setDataCountFromThread],
                ["setfileobj",parent.setFileObjFromThread],
                ["addattribute",parent.addAttributeFromThread]
            ]
        )
        
    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
        finally:
            self.mutex.unlock()

    def sig_slot_connect(self,sig_slot_pair):
        for sig,slot in sig_slot_pair:
            getattr( self, sig )[object].connect( slot )
            
    def run(self):
        if self.filepath.endswith(".csv") or\
           self.filepath.endswith(".txt"):
            
            csvfile=open(self.filepath)

            for skipline in range(self.start_raw-1):
                csvfile.readline()
                
            titlelist = csvfile.readline().split(self.csv_delimiter)
            titlelist[-1] = titlelist[-1].rstrip("\n")
            titletest = titlelist[0]
            try:
                float(titletest)
                self.hastitle = False
            except ValueError:
                self.hastitle = True

            self.settitle.emit( (self.hastitle,titlelist,self.flag) )


            #set data count
            csvfile.seek(0)
            for skipline in range(self.start_raw-1):
                csvfile.readline()
            linecount = sum(1 for line in csvfile)
            if self.hastitle:
                linecount-=1

            self.setdatacount.emit( (linecount,self.flag) )


            #preview
            csvfile.seek(0)
            for skipline in range(self.start_raw-1):
                csvfile.readline()
            if self.hastitle:
                csvfile.readline()

            row = 0
            while True:   
                line = csvfile.readline()
                if line:               
                    values = line.split(self.csv_delimiter)
                    values[-1] = values[-1].rstrip("\n")

                    self.addattribute.emit( (row,values,self.flag) )
                    row+=1
                    if row == 50:
                        self.setfileobj.emit( (csvfile,self.flag) )
                        break
                else:
                    self.setfileobj.emit( (csvfile,self.flag) )
                    break

from STAR_BME.gui.ui.ui_LoadFileDlg import Ui_LoadFileDlg
class LoadFileDlg(QDialog,Ui_LoadFileDlg):
    def __init__(self, flag, parent = None):
        super(LoadFileDlg,self).__init__(parent)
        self.SetDataDlg = parent
        self.flag = flag 
        
        self.ui=Ui_LoadFileDlg()
        self.ui.setupUi(self)
        
        self.accept_file_type = "Comma separated values (*.csv);;"\
                                "Text files (*.txt)"#;;"\
                                #"Excel files (*.xls *.xlsx);;"\
                                #"Shapefile (*.shp)"
                                
        
        self.file_path = None
        self.delimiter = None
        self.start_row = None
        
        self.ui.pushButton_browse.clicked.connect( self.browse )
        self.ui.pushButton_ok.clicked.connect( self.ok )
        self.ui.pushButton_cancel.clicked.connect( self.cancel )

        self.ui.radioButton_others.toggled[bool].connect( self.ui.lineEdit_others.setEnabled )
        
    def browse(self):
        #file_path_temp = QFileDialog.getOpenFileName(self,"Load Data File",
                                                     #self.SetDataDlg.parent().last_opened_folder,
                                                     #self.accept_file_type)
        file_path_temp , _ = QFileDialog.getOpenFileName(self,"Load Data File",
                                                     "","All Files (*);;Text files (*.txt);;csv(*.csv)")
        
        if not file_path_temp:
            pass
        else:
            self.SetDataDlg.MainDlg.updateLastOpenedFolder(file_path_temp)
            self.file_path = file_path_temp
            #self.ui.lineEdit_filename.setText( os.path.normpath( self.file_path ) )
            self.ui.lineEdit_filename.setText((os.path.normpath( self.file_path)))

    def ok(self):
        #file_path
        self.file_path = self.ui.lineEdit_filename.text()
        if self.file_path == u"":
            QMessageBox.critical(self, "Input Error", "Please Input File Path")
            return
        elif not os.path.exists( self.file_path) :
            QMessageBox.critical(self, "Input Error", "Please Input Correct File Path\n"
                                                      "(If The File Path Actually Exists,\n"
                                                      "You Should Have Permission to Access It)")
            return
        #self.file_path
        
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
        
        self.start_row = self.ui.spinBox_row.value()
        
        self.accept()
    
    def cancel(self):
        self.reject()

from STAR_BME.gui.ui.ui_LoadGridDlg import Ui_LoadGridDlg
class LoadGridDlg(QDialog,Ui_LoadGridDlg):
    def __init__(self, SetDataDlg = None):
        super(LoadGridDlg,self).__init__(SetDataDlg)
        self.SetDataDlg = SetDataDlg 
        
        self.ui=Ui_LoadGridDlg()
        self.ui.setupUi(self)
        
        
        
        #create for spatial only
        if self.SetDataDlg.MainDlg.isSpatialOnly():
            self.ui.lineEdit_tmin.setDisabled( True )
            self.ui.lineEdit_tmax.setDisabled( True )
            self.ui.lineEdit_tn.setDisabled( True )
                 
        self.ui.pushButton_setbydata.clicked.connect( self.setBoundaryByData )
        self.ui.pushButton_ok.clicked.connect( self.ok )
        self.ui.pushButton_cancel.clicked.connect( self.cancel )
        
    def setBoundaryByData(self):
        def getBnd(data_obj):
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
            
        bmeobj = self.parent().MainDlg.bmeobj

        H = bmeobj.hard_data.hasData()
        S = bmeobj.soft_data.hasData()
        if H and S:
            hxmin, hxmax, hymin, hymax, htmin, htmax = getBnd(bmeobj.hard_data)
            sxmin, sxmax, symin, symax, stmin, stmax = getBnd(bmeobj.soft_data)
            xmin = min(hxmin,sxmin)
            xmax = max(hxmax,sxmax)
            ymin = min(hymin,symin)
            ymax = max(hymax,symax)
            tmin = min(htmin,stmin)
            tmax = max(htmax,stmax)
            self._setBoundaryData(xmin,xmax,ymin,ymax,tmin,tmax)
        elif H:
            hxmin, hxmax, hymin, hymax, htmin, htmax = getBnd(bmeobj.hard_data)
            self._setBoundaryData(hxmin,hxmax,hymin,hymax,htmin,htmax)
        elif S:
            sxmin, sxmax, symin, symax, stmin, stmax = getBnd(bmeobj.soft_data)
            self._setBoundaryData(sxmin,sxmax,symin,symax,stmin,stmax)
        else: #no data input
            QMessageBox.critical(self, "No Input Data Found", "Please Input Hard or Soft Data Fisrt\n"
                                                              "If You Want to Use This Method.")
    
    def _setBoundaryData(self,*arg):
        self.ui.lineEdit_xmin.setText(str(arg[0]))
        self.ui.lineEdit_xmax.setText(str(arg[1]))
        self.ui.lineEdit_ymin.setText(str(arg[2]))
        self.ui.lineEdit_ymax.setText(str(arg[3]))
        self.ui.lineEdit_tmin.setText(str(arg[4]))
        self.ui.lineEdit_tmax.setText(str(arg[5]))
        
        if self.SetDataDlg.MainDlg.isSpatialOnly():
            self.ui.lineEdit_tn.setText( '1.0' )
        
    def ok(self):
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
        if not setArg(int,"Int","xn"):
            return 
        if not setArg(int,"Int","yn"):
            return
        if not setArg(int,"Int","tn"):
            return
        
        grid_param = (self.xmin,self.xmax,self.ymin,self.ymax,
                      self.tmin,self.tmax,self.xn,self.yn,self.tn)
        
        self.SetDataDlg.grid_param = grid_param
        #self.SetDataDlg.gen_obj = gen_obj
        self.accept()
    
    def cancel(self):
        self.reject()

 
from STAR_BME.gui.ui.ui_SelectVLayerDlg import Ui_SelectVLayerDlg
class SelectVLayerDlg(QDialog,Ui_SelectVLayerDlg):
  def __init__(self,parentDlg):
    super(SelectVLayerDlg,self).__init__(parentDlg)
    
    self.ui=Ui_SelectVLayerDlg()
    self.ui.setupUi(self)

    self.ui.buttonBox.accepted.connect( self.accept )
    self.ui.buttonBox.rejected.connect( self.reject )

from STAR_BME.gui.ui.ui_SelectShpDlg import Ui_SelectShpDlg
class SelectShpDlg(QDialog,Ui_SelectShpDlg):
  def __init__(self,parentDlg):
    super(SelectShpDlg,self).__init__(parentDlg)
    
    self.ui=Ui_SelectShpDlg()
    self.ui.setupUi(self)
    
    self.ui.pushButton_browse.clicked.connect( self.browse )
    self.ui.pushButton_cancel.clicked.connect( self.reject )
    self.ui.pushButton_ok.clicked.connect( self.ok )
    
  def browse( self ):
      shp_file_path_temp = QFileDialog.getOpenFileName(self,"Load Data File",
                                                     self.parent().MainDlg.last_opened_folder,
                                                     "Shape Files (*.shp)")
      if not shp_file_path_temp:
            return
      else:
            self.parent().MainDlg.updateLastOpenedFolder( shp_file_path_temp )
            self.shp_file_path_temp = shp_file_path_temp
            self.ui.lineEdit_filename.setText( shp_file_path_temp )
  def ok( self ):
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
             
      if not setArg(float,"Float","tmin"):
            return 
      if not setArg(float,"Float","tmax"):
            return
      if not setArg(int,"Int","tn"):
            return
      
      self.shp_file_path = self.shp_file_path_temp
      self.accept()