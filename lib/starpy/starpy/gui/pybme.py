# -*- coding: utf-8 -*-
'''
Created on 2011/11/1

@author: KSJ, @STEMLAB, Department of Bioenvironmental Systems Engineering, Taiwan National University, Taipei
'''
########################################################################
import os
import sys
import math, random
from io import StringIO
import numpy
import pickle
import shelve
import time

from ..general.rawdata2griddata import rawdata2griddata, rawdata2griddataforcoor, rawdata2griddata_list
from ..general.findzfromgriddata import findzfromgriddata
from ..general.pso import pso
from ..general.bobyqa import bobyqa
from ..stats.stcov import stcov
from ..stats.stcovfit import fitcovariance, estimatecovariance

from .softconverter import gs2ud,uf2ud,ud2ud,proba2stat,proba2probdens,proba2quantile
from .BMEoptions import bmeoptions
from .nousedataobj import NoUseDataObj
from .BMEprobaMoments import BMEprobaMoments


class GuiManager(object):
    '''處理gui相關的事，讓此模組在有無gui介面下皆可運行'''
    def setProgressDialog(self,qpgd):
        self.progress_dialog = qpgd
        
    def setCurrentProgress(self, value = None, text = None):
        try:
            if text:
                self.progress_dialog.setLabelText(text)
            if value:
                self.progress_dialog.setValue(value)
        except AttributeError:
            pass
    
    def setCurrentProgressAdd(self, value = "nouse"):
        self.progress_dialog.setValue(self.progress_dialog.value()+1)
        
    def setProgressRange(self, min, max):
        try:
            self.progress_dialog.setRange(int(min), int(max))
        except AttributeError:
            pass
    
    def setProgressAutoClose(self,flag = True):
        try:
            self.progress_dialog.setAutoClose(flag)
        except AttributeError:
            pass
        
    def wasProgressCanceled(self):
        try:
            return self.progress_dialog.wasCanceled()
        except AttributeError:
            return False #means continue
        
    def getProgressText(self):
        try:
            return self.progress_dialog.labelText()
        except AttributeError:
            return ""
                  
                   
    '''方法「save」與「load」用「save_list」中的str變數名稱來將變數儲存
    至檔案路徑(file_name)中(使用pickle模組)
    '''
    def save( self, pickler ):
        #dump info
        pickler.dump( '{i},{n}'.format( i = self.name,
                                        n = len( self.save_list ) ) )
        for attr in self.save_list:
            pickler.dump( attr )
            pickler.dump( getattr( self, attr ) )
        return True

    def load( self, unpickler ):
        name, arg_n = unpickler.load().split(',')
        if name != self.name:
            raise ValueError('Invalid save file')
        else:
            for i in range( int(arg_n) ):
                attr = unpickler.load()
                setattr( self, attr, unpickler.load() )

class BasicData( SaveLoadManager, GuiManager ):
    
    def __init__(self):
        self.name = "arbitrarydata" #about save (shelve's key)
        self.label_name = "ArbitraryData" #about waiting dialog's text
        
    def setDataFromFile(self, data_assign, file_name, usecols,
                        skiprows, delimiter = ",", count_per_read = 2000,
                        label = ""):
        '''
            data_assign: tuple of attribute string of data need to be assign
                         eg. ("x", "y", "t", ...) 
                             means self.x, self.y, self.t will be assign
            count_per_read: how many coordinate data read per times
        '''
        
        if not label:
            label = "Setting "+ self.label_name + "..."
            
        self.setCurrentProgress(text = label)
        
        try:
            file_obj = open(file_name,"r")
            not_close = False
        except TypeError: # already is a FileObj (useLayer)
            file_obj = file_name
            not_close = True
            
        file_obj.seek(0)
        for skiprow in range(skiprows):
            file_obj.readline()
        line_count = sum(1 for line in file_obj)
        file_obj.seek(0)
        for skiprow in range(skiprows):
            file_obj.readline()
        step = int(math.ceil(line_count/float(count_per_read)))  
        self.setProgressRange(0,step) # configure GUI
        
        result = [numpy.array([]) for i in range(len(usecols))]
        
        for step_i in range(step):
            if not self.wasProgressCanceled():
                #make like file obj 
                part_file_obj = StringIO()
                #get part of data
                for count_i in range(count_per_read):
                    try:
                        part_file_obj.write(next(file_obj))
                    except StopIteration:
                        break
    
                part_file_obj.seek(0)
                try:
                    data = numpy.loadtxt(part_file_obj, delimiter = delimiter,
                                  unpack = True,
                                  ndmin = 2,
                                  usecols = usecols,
                                  skiprows = 0)
                except TypeError: # old numpy loadtxt has no ndmin keyword arg
                    data = numpy.loadtxt(part_file_obj, delimiter = delimiter,
                                  unpack = True,
                                  usecols = usecols,
                                  skiprows = 0)
                    if data.ndim == 0:
                        data = numpy.array( data, ndmin = 2)
                    elif data.ndim == 1: #special case only one row data
                        if len(usecols) == 1:
                            data = numpy.array( data, ndmin = 2)
                        elif len( usecols ) > 1:
                            data = numpy.array([data],ndmin=2).T
                    else:
                        pass
                    
                
                result = list(map(lambda x,part_x: numpy.append(x,part_x),
                             result,data))
                part_file_obj.close()
                self.setCurrentProgress(value = step_i+1)
            else:
                return False

        if not_close:
            pass
        else:
            file_obj.close()
        result = list(map(lambda x: numpy.array(x,ndmin = 2).T, result))
        for i,j in zip(data_assign,result):
            setattr(self,i,j)
        return True
        
class CoordinateData(BasicData):
    '''基本資料[CoordinateData]的類別
    其中包含變數「x」「y」「t」「z」「tr」 「z_cv」 「tr_cv」，
    皆是 n by 1 的 numpy array
    還有轉換「x」「y」「t」「z」
    成格狀資料的變數「s_grid」「t_grid」「z_grid」「tr_grid」 「z_cv_grid」 「tr_cv_grid」，
  s_grid 是 s by 2 的 numpy array
  t_grid 是 1 by t 的 numpy array
  z_grid 是 s by t 的 numpy array (可包含 numpy.nan)
  tr_grid 是s by t 的 numpy array (可包含 numpy.nan)
  z_cv_grid 是s by t 的 numpy array (可包含 numpy.nan)
  tr_cv_grid 是s by t 的 numpy array
    與一些相關整理後的變數 如資料邊界(boundary)、資料筆數(count)等等
  station_count       有幾個空間點
  station_t_min       所有空間點中最小的時間值
  station_t_max       所有空間點中最大的時間值
  time_count          有幾個時間點
  time_x_min          所有時間點中最小的空間x值
  time_x_max          所有時間點中最大的空間x值
  time_y_min          所有時間點中最小的空間y值
  time_y_max          所有時間點中最大的空間y值
  z_min_without_nan   所有資料點中最小的觀測z值
  z_max_without_nan   所有資料點中最大的觀測z值
    與一些判定有無特定資料的旗幟(flag)變數
  has_coord           有座標輸入
  has_value           有值輸入
  has_data            有資料輸入
  has_data_info       有整理過資料
  has_data_grid       有轉換成  grid 資料形態

    '''
    def __init__(self):
        super(CoordinateData, self).__init__()
        
        self.name = "coordinatedata"
        self.label_name = "CoordinateData"
        
        self.x = numpy.array([],ndmin=2) # raw by 1 matrix
        self.y = numpy.array([],ndmin=2) # raw by 1 matrix
        self.t = numpy.array([],ndmin=2) # raw by 1 matrix
        self.z = numpy.array([],ndmin=2) # raw by 1 matrix
        self.tr = numpy.array([],ndmin=2) # raw by 1 matrix
        self.z_cv = numpy.array([],ndmin=2) # raw by 1 matrix
        self.tr_cv = numpy.array([],ndmin=2) # raw by 1 matrix
        self.s_grid = numpy.array([],ndmin=2)
        self.t_grid = numpy.array([],ndmin=2)
        self.z_grid = numpy.array([],ndmin=2)
        self.tr_grid = numpy.array([],ndmin=2)
        self.z_cv_grid = numpy.array([],ndmin=2)
        self.tr_cv_grid = numpy.array([],ndmin=2)
        
        self.station_count = 0
        self.time_count = 0
        self.time_x_min = None
        self.time_x_max = None
        self.time_y_min = None
        self.time_y_max = None
        self.station_t_min = None
        self.station_t_max = None
        self.z_min_without_nan = None
        self.z_max_without_nan = None
        self.station_z_mean = None
        self.station_z_variance = None
        
        self.has_coord = False
        self.has_value = False
        self.has_data = False
        self.has_data_info = False
        self.has_data_grid = False

        self.save_list = ["x","y","t","z", "tr", "z_cv", "tr_cv",
           "s_grid", "t_grid", "z_grid", "tr_grid", "z_cv_grid", "tr_cv_grid",
           "station_count",
           "station_t_min", "station_t_max",
           "time_count",
           "time_x_min", "time_x_max",
           "time_y_min", "time_y_max",
           "z_min_without_nan", "z_max_without_nan",
           "station_z_mean", "station_z_variance",
           "has_coord", "has_value",
           "has_data",
           "has_data_info", "has_data_grid"]

    def setCoordinateFromFile(self, file_name, usecols = (0,1,2), skiprows = 0,
                              delimiter = ",", count_per_read = 2000):
        
        label = "Set Coordinate of " + self.label_name + "..."
        if self.setDataFromFile(data_assign = ("x", "y", "t"),
                                file_name = file_name,
                                usecols = usecols,
                                skiprows = skiprows,
                                delimiter = delimiter,
                                count_per_read = count_per_read,
                                label = label):
            self.has_coord = True
            return True
        else:
            return False
       
    def setGridData(self):
        self.setCurrentProgress(0,text = "Converting " + self.label_name + " to GridData...")
        result = rawdata2griddata(self.x, self.y, self.t, self.z, self)
        if result:
            self.s_grid, self.t_grid, self.z_grid = result
            self.has_data_grid = True
            return True
        else:
            return False
              
    def updateDataInfo(self):
        x = self.s_grid[:,0]
        y = self.s_grid[:,1]
        t = self.t_grid[0]
        zwithoutnan = self.z_grid[numpy.where(~numpy.isnan(self.z_grid))]
        self.station_count = self.s_grid.shape[0] 
        self.time_count = self.t_grid.shape[1]
        
        self.time_x_min = x.min()
        self.time_x_max = x.max()
        self.time_y_min = y.min()
        self.time_y_max = y.max()
        self.station_t_min = t.min()
        self.station_t_max = t.max()
        self.z_min_without_nan = zwithoutnan.min()
        self.z_max_without_nan = zwithoutnan.max()
        

        mean_list = []
        var_list = []
        for z_i in self.z_grid:
            mean_i = z_i[numpy.where(~numpy.isnan(z_i))].mean()
            var_i = z_i[numpy.where(~numpy.isnan(z_i))].var()
            mean_list.append(mean_i)
            var_list.append(var_i)
            
        self.station_z_mean = numpy.array( mean_list, ndmin = 2 ).T
        self.station_z_variance = numpy.array( var_list, ndmin = 2 ).T
        
        self.has_data_info = True
         
    def hasCoord(self):
        return self.has_coord
    
    def hasValue(self):
        return self.has_value
    
    def hasData(self):
        return self.has_data
    
    def hasDataInfo(self):
        return self.has_data_info
    
    def hasDataGrid(self):
        return self.has_data_grid
    
class HardData(CoordinateData):
    '''
    #繼承 CoordinateData， 值(value) 在此定義
    '''
    def __init__(self):
        super(HardData,self).__init__()
        self.name = "harddata"
        self.label_name = "HardData"
        
    def setValueFromFile(self, file_name, usecols = (3,), skiprows = 0,
                         delimiter = ",", count_per_read = 2000):    
        if self.setDataFromFile(data_assign = ("z",),
                                file_name = file_name,
                                usecols = usecols,
                                skiprows = skiprows,
                                delimiter = delimiter,
                                count_per_read = count_per_read,
                                label = "Set Value of " + self.label_name + " ..."):
            self.has_value = True
            if self.has_coord:
                self.has_data = True
            return True
        else:
            return False
            
class SoftData(CoordinateData):
    '''
    #繼承 CoordinateData， 值(value) 在此定義。
    #有許多屬於softdata才有的屬性也在此定義 ( nl, limi, probadens )
    #另外z在softdata裡表示各點資料分佈的平均值, 用在移trend的時候
    '''
    def __init__(self):
        super(SoftData,self).__init__()
        self.name = "softdata"
        self.label_name = "SoftData"

        self.var = numpy.array([],ndmin=2) #matrix
        self.var_grid = numpy.array([],ndmin=2) #matrix
        self.quantile = numpy.array([],ndmin=2) #matrix
        self.quantile_grid = numpy.array([],ndmin=2) #matrix

        self.input_format = "gaussian" # string  0:user defined 1:gaussian 2:uniform (or linear)
        self.pdf_type = "linear" # string 0:histogram 1:linear
        self.nl = numpy.array([],ndmin=2) #matrix
        self.limi = numpy.array([],ndmin=2) #matrix
        self.probdens = numpy.array([],ndmin=2) #matrix
        self.quantile = numpy.array([],ndmin=2) #matrix

        self.save_list += ["var", "var_grid", "input_format", "pdf_type",
                           "nl", "limi", "probdens", "quantile", "quantile_grid"]
 
    def setValueFromFile(self, file_name, usecols = (3,4), skiprows = 0,
                         delimiter = ",", count_per_read = 2000):
        if self.input_format.lower() == "gaussian" or self.input_format.lower() == "uniform":
            if self.setDataFromFile(data_assign = ("var_a", "var_b"),
                                    file_name = file_name,
                                    usecols = usecols,
                                    skiprows = skiprows,
                                    delimiter = delimiter,
                                    count_per_read = count_per_read,
                                    label ="Set Value of " + self.label_name + " ..."):
                #return True
                pass #set data OK
                var_a, var_b = self.var_a, self.var_b
                del self.var_a, self.var_b
            else:
                return False
        else:
            pass
        # convert data to userdefined type and 
        # calculate mean(self.z) use for detrend
        self.setCurrentProgress(text = "Converting Data type...") 
        if self.input_format.lower() == "user defined": # user defined
            #from softconverter import ud2ud
            self.nl, self.limi, self.probdens = ud2ud( file_name, usecols, skiprows, delimiter )
            self.nl, self.limi, self.probdens = proba2probdens( 'dummy', self.nl, self.limi, self.probdens ) #normalize
            self.quantile = proba2quantile( 'dummy', self.nl, self.limi, self.probdens )
            self.z, self.var = proba2stat( 'dummy', self.nl, self.limi, self.probdens )
        elif self.input_format.lower() == "gaussian": # gaussian
            #var_a is mean, var_b is var
            #from softconverter import gs2ud
            self.nl, self.limi, self.probdens = gs2ud(var_a, var_b)
            self.z = var_a
            self.var = var_b

            self.nl, self.limi, self.probdens = proba2probdens( 'dummy', self.nl, self.limi, self.probdens ) #normalize
            self.quantile = proba2quantile( 'dummy', self.nl, self.limi, self.probdens )

        elif self.input_format.lower() == "uniform" or self.input_format.lower() == "linear": # uniform
            #var_a is lowbnd, var_b is upbnd
            #from softconverter import uf2ud
            self.nl, self.limi, self.probdens = uf2ud(var_a, var_b)
            self.z = ( var_a + var_b ) / 2.
            self.var = 1. / 12.* ( var_b - var_a ) ** 2

            self.nl, self.limi, self.probdens = proba2probdens( 'dummy', self.nl, self.limi, self.probdens ) #normalize
            self.quantile = proba2quantile( 'dummy', self.nl, self.limi, self.probdens )
            
        self.has_value = True
        if self.has_coord:
            self.has_data = True
        return True

    def setPdfType(self,pdft):
        if pdft.lower() not in ["histogram", "linear"]:
            return False
        else:
            self.pdf_type = pdft
            return True
        
    def setInputFormat(self,ipfm):
        if ipfm.lower() not in ["user defined", "gaussian",
                                "uniform", "linear"]:
            return False
        else:
            self.input_format = ipfm
            return True

    def setGridData(self):
        self.setCurrentProgress(0,text = "Converting " + self.label_name + " to GridData...")

        z_list = [ self.z, self.var, self.quantile[:,0:1],
                                          self.quantile[:,1:2],
                                          self.quantile[:,2:3],
                                          self.quantile[:,3:4],
                                          self.quantile[:,4:5]]
        result = rawdata2griddata_list( self.x, self.y, self.t, z_list )                                    
        if result:
            self.s_grid, self.t_grid, z_grid_list = result
            self.z_grid = z_grid_list[0]
            self.var_grid = z_grid_list[1]
            self.quantile_grid = numpy.dstack( z_grid_list[2:] )
            self.has_data_grid = True
            return True
        else:
            return False

        # result = rawdata2griddata(self.x, self.y, self.t, self.z, self)

        
        # if result:
        #     result2 = rawdata2griddata(self.x, self.y, self.t, self.var, self)
        #     if result2:
        #         result3 = rawdata2griddata(self.x, self.y, self.t, self.quantile, self)
        #         if result3:
        #             self.s_grid, self.t_grid, self.z_grid = result
        #             self.s_grid, self.t_grid, self.var_grid = result2
        #             self.s_grid, self.t_grid, self.quantile_grid = result3
        #             self.has_data_grid = True
        #             return True
        #         else:
        #             return False
        #     else:
        #         return False
        # else:
        #     return False

class EstimatedData(CoordinateData):
    '''
    #繼承 CoordinateData， 
    #值(value) 由bme推估residual後 與 tr相加而得
    #值(value) 包含 mean與variance二部份 (之後也可能會有skewness)
    #所以刪除繼承而來的z屬性
    '''
    def __init__(self):
        super(EstimatedData,self).__init__()
        self.name = "estimateddata"
        self.label_name = "EstimatedData"
        
        self.z_mean = numpy.array([],ndmin=2) # n by 1 matrix (moment[0])
        self.z_variance = numpy.array([],ndmin=2) # n by 1 matrix (moment[1])
        
        self.z_mean_grid = numpy.array([],ndmin=2) # s by t matrix
        self.z_variance_grid = numpy.array([],ndmin=2) # s by t matrix
        
        self.z_mean_min_without_nan = None
        self.z_mean_max_without_nan = None
        self.z_variance_min_without_nan = None
        self.z_variance_max_without_nan = None
        self.z_all_min_without_nan = None # use for plot boundary
        self.z_all_max_without_nan = None #
        
        self.save_list += ["z_mean", "z_variance",
                           "z_mean_grid", "z_variance_grid",
                           'z_mean_min_without_nan','z_mean_max_without_nan',
                           'z_variance_min_without_nan','z_variance_max_without_nan',
                           'z_all_min_without_nan','z_all_max_without_nan']

        del self.z, self.z_grid, self.z_min_without_nan, self.z_max_without_nan
        for remove_str in ["z","z_grid",'z_min_without_nan','z_max_without_nan']:
            self.save_list.remove(remove_str)
        
    def estimateTrend(self, trend_obj):
        
        coor_st = rawdata2griddataforcoor(self.x, self.y, self.t, self)
        if not coor_st:
            return False
        else:
            pass #result can be used
        trend_obj.setCoordinate(coor_st)
        tr_grid_est = trend_obj.estimate() #tr_grid_est or False
        if tr_grid_est is False:
            return False
        else:
            pass #result can be used
        self.s_grid, self.t_grid = coor_st
        self.tr_grid = tr_grid_est

        self.tr = findzfromgriddata(self.x, self.y, self.t,
                                    coor_st[0], coor_st[1], tr_grid_est,
                                    self)
        return True

    def updateDataInfo(self): #overload CoordnaiteData
        x = self.s_grid[:,0]
        y = self.s_grid[:,1]
        t = self.t_grid[0]
        
        zwithoutnan_m = self.z_mean_grid[numpy.where(~numpy.isnan(self.z_mean_grid))]
        #zwithoutnan_v = self.z_variance_grid[numpy.where(~numpy.isnan(self.z_variance_grid))]
        zwithoutnan_v = self.z_variance_grid[numpy.where(~numpy.isnan(self.z_mean_grid))]
        self.station_count = self.s_grid.shape[0]
        self.time_count = self.t_grid.shape[1]
        self.time_x_min = x.min()
        self.time_x_max = x.max()
        self.time_y_min = y.min()
        self.time_y_max = y.max()
        self.station_t_min = t.min()
        self.station_t_max = t.max()
        try:
            self.z_mean_min_without_nan = zwithoutnan_m.min()
            self.z_mean_max_without_nan = zwithoutnan_m.max()
            self.z_variance_min_without_nan = zwithoutnan_v.min()
            self.z_variance_max_without_nan = zwithoutnan_v.max()
        except ValueError:
            self.z_mean_min_without_nan = numpy.nan
            self.z_mean_max_without_nan = numpy.nan
            self.z_variance_min_without_nan = numpy.nan
            self.z_variance_max_without_nan = numpy.nan
               
        
        
        mean_list = []
        var_list = []
        for z_i in self.z_mean_grid:
            if z_i[numpy.where(~numpy.isnan(z_i))].size > 0:
                mean_i = z_i[numpy.where(~numpy.isnan(z_i))].mean()
                var_i = z_i[numpy.where(~numpy.isnan(z_i))].var()
            else:
                mean_i = numpy.nan
                var_i = numpy.nan
            mean_list.append(mean_i)
            var_list.append(var_i)
            
        self.station_z_mean = numpy.array( mean_list, ndmin = 2 ).T
        self.station_z_variance = numpy.array( var_list, ndmin = 2 ).T
        
        try:
            self.z_all_min_without_nan = (zwithoutnan_m - 1.96 * numpy.sqrt(zwithoutnan_v)).min()
            self.z_all_max_without_nan = (zwithoutnan_m + 1.96 * numpy.sqrt(zwithoutnan_v)).max()
        except ValueError:
            self.z_all_min_without_nan = numpy.nan
            self.z_all_max_without_nan = numpy.nan
        
        self.has_data_info = True
        
class Trend(SaveLoadManager, GuiManager):
    '''
    #Trend物件用來移除trend用
    #先給它座標、值、函式名稱，
    #再輸入預推估trend的座標(若沒輸入表示推估座標與輸入座標是相同的)
    #即推出預推估的的trend
    '''
    def __init__(self,function_name = "No Detrending"):
        self.name = "trend"
        self.save_list = ["data","parameters", "function"] #"data", "coordinate"
                          

        self.data = None # (s_grid, t_grid, z_grid)
        self.coordinate = () # () - empty tuple (means use data's coordinate) or
                             # (s_grid_est, t_grid_est) or
                             # (x_est, y_est, t_est)
        self.parameters = () # A tuple contain other parameter for estimation
        self.function = function_name # string to recognize method

    def setData(self, data_tuple):
        self.data = data_tuple
        
    def setCoordinate(self, coor_tuple):
        self.coordinate = coor_tuple
        
    def setParameters(self, params_tuple):
        self.parameters = params_tuple
        
    def setFunction(self, func_name):
        '''Use for change used method'''
        if func_name.lower() not in ["no detrending", "nd",
                                     "kernel smoothing", "ks",
                                     "user defined", "ud",
                                     "stmean", "stm"]:
            return False
        else:
            self.function = func_name
            return True
    
    def _estimateByNoDetrend(self):
        if len(self.coordinate) == 0: #coordinate and data is the same
            result = self.data[2].copy()
            result[numpy.where(~numpy.isnan(self.data[2]))] = 0.0
        elif len(self.coordinate) == 2: #st type
            result = numpy.zeros((self.coordinate[0].shape[0],self.coordinate[1].shape[1]))    
        elif len(self.coordinate) == 3: #xyt type
            result = numpy.array([])
            length = self.coordinate[0].shape[0]
            step = int(math.ceil(length / 10.))
            zeros = numpy.zeros(step)
            self.setCurrentProgress(text = "estimate trend...")
            for index,i in enumerate(range(0,step,length)):
                result = numpy.append(result,zeros)
                self.setCurrentProgress(value = (index+1) * 10)
            result = numpy.array([result[0:length]]).T #truncate
        return result
    
    def _estimateBySTMean(self):
        from stmean import stmean, stmean_est
        
        if len(self.coordinate) == 0: #coordinate and data is the same
            needed_param = self.data + self.parameters
            return stmean(*needed_param)
        elif len(self.coordinate) == 2: #st type
            needed_param = self.data + self.coordinate + self.parameters
            return stmean_est(*needed_param)
        elif len(self.coordinate) == 3: #xyt type
            x,y,t = self.coordinate
            data = rawdata2griddataforcoor(*(self.coordinate + self.parameters[-1:]))
            if not data:
                return False
            else:
                pass #data can be used, e.g. (grid_s, grid_t)
            needed_param = self.data + data + self.parameters
            trend_grid = stmean_est(*needed_param)
            return findzfromgriddata(x,y,t,data[0], data[1],trend_grid)
            #return findzfromgriddata(x,y,t,s_grid,t_grid,z_grid)
        
    def _estimateByKernelSmoothing(self):
        '''Return tr_grid_est or tr_est, depend on coordinate
        or return False if fail
        '''
        from kernelsmoothing import kernelsmoothing, kernelsmoothing_est
        
        if len(self.coordinate) == 0: #coordinate and data is the same
            needed_param = self.data + self.parameters
            return kernelsmoothing(*needed_param)
        elif len(self.coordinate) == 2: #st type
            needed_param = self.data + self.coordinate + self.parameters
            return kernelsmoothing_est(*needed_param)
        elif len(self.coordinate) == 3: #xyt type
            data = rawdata2griddataforcoor(*(self.coordinate + self.parameters[-1:]))
            if not data:
                return False
            else:
                pass #data can be used
            needed_param = self.data + data + self.parameters
            trend_grid = kernelsmoothing_est(*needed_param)
            x,y,t = self.coordinate
            return findzfromgriddata(x,y,t,data[0],data[1],trend_grid)
    
    def _estimateByUserDefined(self):
        '''Inherit Trend class and redefined this method by yourself'''
        pass
        
    def estimate(self):
        '''Return tr_grid_est or tr_est, depend on coordinate
        Or return False if fail
        '''
        if self.function.lower() in ["no detrending", "nd"]:
            return self._estimateByNoDetrend()
        elif self.function.lower() in ["kernel smoothing", "ks"]:
            return  self._estimateByKernelSmoothing()
        elif self.function.lower() in ["stmean", "stm"]:
            return self._estimateBySTMean()
        elif self.function.lower() in ["user defined", "ud"]:
            return  self._estimateByUserDefined()

class Covariance(SaveLoadManager, GuiManager):
    def __init__(self):
        self.name = "covariance"
        self.data = None # (s_grid, t_grid, z_grid)

        self.spatial_lags = numpy.array([],ndmin=2) # 1 by col
        self.spatial_tolerant_ranges = numpy.array([],ndmin=2) # 1 by col
        self.temporal_lags = numpy.array([],ndmin=2) # 1 by col
        self.temporal_tolerant_ranges = numpy.array([],ndmin=2) # 1 by col

        self.models = [] # raw by 5 [[Cn, Kn(S), Sn, Kn(T), Tn],[...],[...]]
        self.stvn = ()
        self.save_list = ["spatial_lags", "spatial_tolerant_ranges",
                          "temporal_lags", "temporal_tolerant_ranges",
                          "models"] #"data", "stvn",
        
    def setData(self, data_tuple):
        self.data = data_tuple
        
    def _setLags(self, flag, lag_list):
        setattr(self,flag,numpy.array(lag_list, ndmin = 2))
        
    def setSpatialLags(self,lag_list):
        self._setLags("spatial_lags", lag_list)
        
    def setTemporalLags(self,lag_list):
        self._setLags("temporal_lags", lag_list)
        
    def setSpatialTolerantRanges(self, range_list):
        self._setLags("spatial_tolerant_ranges", range_list)
        
    def setTemporalTolerantRanges(self, range_list):
        self._setLags("temporal_tolerant_ranges", range_list)
        
    def setModels(self,models):
        self.models = models
        
    def calculate(self):
        needed_data = (self.data[0],
                       self.data[1][0],
                       self.data[2]) # use t to 1d array 
        parameters = (self.spatial_lags[0], self.spatial_tolerant_ranges[0],
                      self.temporal_lags[0], self.temporal_tolerant_ranges[0],
                      self)
        needed_param = needed_data + parameters 
        self.stvn = stcov(*needed_param)

        return self.stvn #lagCOVs,lagCOVt,lagCOVv,lagCOVn
    
    def selectParamByBobyqa( self, init_guess, args, low_bnd, up_bnd ):
        def objf( cst, models):
            c = cst[0::3]
            s = cst[1::3]
            t = cst[2::3]
            for index,(i,j,k) in enumerate(zip(c,s,t)):
                models[index][0] = i
                models[index][2] = j
                models[index][4] = k
                
            # return fitcovariance(models,self.cov_s,
            #                      self.cov_t,self.cov_v,self.cov_n)

            return fitcovariance(models,*self.stvn)
        
        return bobyqa(objf, init_guess, args, low_bnd, up_bnd)
        
    def selectParamByPso(self,xb,args,flag,pn,it,iw,sc,si,vmp):
        def objf(cst,models):
            #change models
            c=cst[0::3]
            s=cst[1::3]
            t=cst[2::3]
            for index,(i,j,k) in enumerate(zip(c,s,t)):
                models[index][0] = i
                models[index][2] = j
                models[index][4] = k
                
            # return fitcovariance(models,self.cov_s,
            #                      self.cov_t,self.cov_v,self.cov_n)
            return fitcovariance(models,*self.stvn)
            
        #self.objfunclocation = pso(objf,xb,args,flag,pn,it,iw,sc,si,vmp)
        return pso(objf,xb,args,flag,pn,it,iw,sc,si,vmp)
         
    def calculateFit(self, split_number = 30):
        ss, tt, vv, nn = self.stvn
        plotlagS = numpy.linspace(0, ss[-1][0], split_number)
        plotlagT = numpy.linspace(0, tt[0][-1], split_number)
        plotlagTT,plotlagSS = numpy.meshgrid(plotlagT,plotlagS)
    
        plotlagCOV = estimatecovariance(plotlagSS, plotlagTT, self.models)
        
        return plotlagSS, plotlagTT, plotlagCOV
        
    def fit(self):
        #return objective function value
        return fitcovariance(self.models,*self.stvn)
        
class BmeObj(SaveLoadManager, GuiManager):
    def __init__(self, h_data = None, s_data = None,
                 e_data = None, trend = None,
                 covariance = None):
        self.name = "bmeobj"
        
        self.hard_data = h_data if h_data else HardData()
        self.soft_data = s_data if s_data else SoftData()
        self.estimated_data = e_data if e_data else EstimatedData()
        self.trend = trend if trend else Trend()
        self.covariance = covariance if covariance else Covariance()
            
        self.nhmax = None
        self.nsmax = None
        self.dmax = [[None,None,None]]
        
        self.order = 'Zero Mean' #     'Zero Mean' (QGIS), numpy.nan (Py) means Zero Mean (Default)
                                 # 'Constant Mean' (QGIS),         0 (Py) means Constant Mean
        self.options = bmeoptions()
        
        self.moments = numpy.array([[]]) # raw by 3
        self.info = numpy.array([[]]) # raw by 3
        

        self.has_cross_validation = False
        self.cross_validation_sample_type = None
        self.save_list = [ "nhmax", "nsmax", "dmax","order",
                           "moments", "info","has_cross_validation",
                           "cross_validation_sample_type" ]

        self.progress_dialog = None

    def save(self, pickler):
        if isinstance(pickler, str): #file_path
            f = open( pickler,'w' )
            pickler = pickle.Pickler( f )
        #save all obj and itself
        self.hard_data.save( pickler )
        self.soft_data.save( pickler )
        self.estimated_data.save( pickler )
        self.trend.save( pickler )
        self.covariance.save( pickler )
        SaveLoadManager.save( self, pickler )
        if isinstance(pickler, str): #file_path
            f.close()

    def load(self, unpickler):
        if isinstance(unpickler, str): #file_path
            if not os.path.exists( unpickler ):
                print("no file found")
                return False
            f = open( unpickler )
            unpickler = pickle.Unpickler( f )
        self.hard_data.load( unpickler )
        self.soft_data.load( unpickler )
        self.estimated_data.load( unpickler )
        self.trend.load( unpickler )
        self.covariance.load( unpickler )
        SaveLoadManager.load(self, unpickler )
        if isinstance(unpickler, str): #file_path
            f.close()
        return True

    def detrend(self,method = "No Detrending", parameters = ()):
        self.setCurrentProgress(0, "Detrend...")
        
        #Using temporary Trend class
        #to avoid if user cancel progress 
        #that will change variable of original Trend class
        trend_obj = Trend() #Create temporary Trend class
        if not trend_obj.setFunction(method): #Set detrend method
            return False
        data = self.getDetrendData() #Get data that trend class can use
        if data: #tuple or False
            trend_obj.setData(data)
        else:
            return False
        trend_obj.setCoordinate( coor_tuple = () ) #determind detrend, not estimate trend
        trend_obj.setParameters(parameters) #Set detrend parameters
        tr_grid = trend_obj.estimate() # trend_grid
        if type(tr_grid) == bool : #means cancel by user
            return False
        
        #
        if not self._setDataTrend((trend_obj.data[0],trend_obj.data[1],tr_grid)):
            return False
        else: 
            # set data done, now can assign temporary Trend class
            # to original trend class
            self.trend = trend_obj
            return True
        
    def getDividedCk(self, d_number):
        def getCoor(obj):
            return numpy.hstack((obj.x, obj.y, obj.t))
        ck = getCoor(self.estimated_data)
        d_ck = int(numpy.ceil(ck.shape[0] / float(d_number)))
        return [ ck[d_ck*i:d_ck*(i+1),:] for i in range(d_number) ]

    def getFunctionParameters(self):
        def getCoor(obj):
            return numpy.hstack((obj.x, obj.y, obj.t))
        
        def getCovModel():
            def convertPythonModelName(modelname): #convertPyModelNameToCModelIndex
                #                     C   PYTHON
                #//exponentialC     = 1     1
                #//gaussianC        = 2     0
                #//holesinC         = 3     
                #//holecosC         = 4     3
                #//nuggetC          = 5     4
                #//sphericalC       = 6     2
                #//mexicanhatC      = 7
                d={"gaussian":'gaussianC', "exponential":'exponentialC',
                   "spherical":'sphericalC', "holecos":'holecosC',
                   "nugget":'nuggetC'}
                return d[modelname.lower()]
            
            covparam = []
            covmodel = []
            for bv in self.covariance.models:
                covparam.append( bv[::2] )
                covmodel.append( convertPythonModelName(bv[1])+'/'+convertPythonModelName(bv[3]) )

            return covmodel,covparam
            
        ck = getCoor(self.estimated_data)
        
        if self.hard_data.hasData():
            ch = getCoor(self.hard_data)
            zh = (self.hard_data.z - self.hard_data.tr) #residual
        else:
            ch = None
            zh = None
            
        if self.soft_data.hasData():
            cs = getCoor(self.soft_data)
            softpdftype = self.soft_data.pdf_type

            #convert probdens to normal
            nlseq, limiseq, probadensseq = proba2probdens( 'dummy',
                                                            self.soft_data.nl,
                                                            self.soft_data.limi- self.soft_data.tr,
                                                            self.soft_data.probdens
                                                          )

        else:
            cs = numpy.array([],ndmin=2)
            softpdftype = 1 #no use
            nlseq = numpy.array([],ndmin=2)
            limiseq = numpy.array([],ndmin=2)
            probadensseq = numpy.array([],ndmin=2)
        
        covmodel, covparam = getCovModel()
        nhmax, nsmax, dmax, order, options = self.nhmax, self.nsmax, self.dmax, self.order, self.options

        return [ck, ch, cs, zh,
                softpdftype, nlseq, limiseq, probadensseq,
                covmodel, covparam,
                nhmax, nsmax, dmax,
                order, options]

    def calculateBMEprobaMomentsResult(self, args):
        return BMEprobaMoments( *args )

    def estimate(self):

        (ck,ch,cs,zh,softpdftype,
         nlseq,limiseq,probadensseq,
         covmodel,covparam,nhmax,nsmax,dmax,
         order,options) = self.getFunctionParameters()

        moments_temp = ck[:]
        info_temp = ck[:]
        
        ttl = len(ck)
        
        self.setProgressRange(0,len(ck))
        self.setCurrentProgress(0, "BME Estimation Starts...")

        result = BMEprobaMoments( ck,ch,cs,zh,
                                  softpdftype,
                                  nlseq,limiseq,probadensseq,
                                  covmodel,covparam,nhmax,nsmax,dmax,
                                  order,options, self.progress_dialog )
                
        if result: #tuple
            [moments_temp, info_temp] = result
        else:
            return False #cancel by user
            
        self.moments_temp = moments_temp
        self.info_temp = info_temp
        
        # get estimatedtrend
        result = self.estimated_data.estimateTrend(self.trend)
        if not result:
            return False
        else:
            pass #setting tr and tr_grid for estimated_data success
        moments_np = numpy.array(moments_temp)
        info_np = numpy.array(info_temp)
        self.estimated_data.z_mean = (moments_np[:,0] + self.estimated_data.tr.flatten()).reshape((-1,1))
        self.estimated_data.z_variance =  moments_np[:,1].reshape((-1,1))
        
        
        mean_grid = rawdata2griddata(self.estimated_data.x,
                                     self.estimated_data.y,
                                     self.estimated_data.t,
                                     self.estimated_data.z_mean, self)
        if not mean_grid:
            return False
        else:
            pass 
        self.estimated_data.z_mean_grid = mean_grid[2]
        
        variance_grid = rawdata2griddata(self.estimated_data.x,
                                         self.estimated_data.y,
                                         self.estimated_data.t,
                                         self.estimated_data.z_variance, self)
        if not variance_grid:
            return False
        else:
            pass 
        self.estimated_data.z_variance_grid = variance_grid[2]
        
        self.estimated_data.updateDataInfo()
        return True

    def getDetrendData(self):
        return self._getGridData("z")
    
    def getCovarianceData(self):
        return self._getGridData("tr")
    
    def _getGridData(self, flag):
        '''return s_grid,t_grid,z_grid'''
        #flag can be "z" "tr"
        if self.hard_data.hasData() and self.soft_data.hasData(): #has hard and soft
            x_all, y_all, t_all, flag_all =            list(map( numpy.vstack,
                     ( (self.hard_data.x,self.soft_data.x),
                       (self.hard_data.y,self.soft_data.y),
                       (self.hard_data.t,self.soft_data.t),
                       (getattr(self.hard_data, flag), getattr(self.soft_data, flag) )  ) ))
            data = rawdata2griddata(x_all, y_all, t_all, flag_all, self)
            
            return data
        elif self.hard_data.hasData(): #only has hard
            return (self.hard_data.s_grid,
                    self.hard_data.t_grid,
                    getattr(self.hard_data, flag+"_grid") )
        elif self.soft_data.hasData(): #only has soft
            return (self.soft_data.s_grid,
                    self.soft_data.t_grid,
                    getattr(self.soft_data, flag+"_grid"))
        else:
            raise ValueError("Must be an error")
        
    def _setDataTrend(self,data):
        def byDataClass(dataobj):
            needed_data = (dataobj.x, dataobj.y, dataobj.t,
                           
                           data[0], data[1], data[2], self)
            tr_temp = findzfromgriddata(*needed_data)
            if type(tr_temp) == bool: # means cancel by user
                return False   
            needed_data = (dataobj.x, dataobj.y, dataobj.t,
                           tr_temp, self)
            tr_grid_temp = rawdata2griddata(*needed_data) # (s_grid, t_grid, z_grid)
            if type(tr_grid_temp) == bool:
                return False
            return tr_temp,  tr_grid_temp[2] # 2 means tr_grid
            
            
        if self.hard_data.hasData() and self.soft_data.hasData(): #has hard and soft
            h_result = byDataClass(self.hard_data)
            if h_result == False: #tuple or False
                return False
            s_result = byDataClass(self.soft_data)
            if s_result == False:
                return False
            self.hard_data.tr, self.hard_data.tr_grid = h_result
            self.soft_data.tr, self.soft_data.tr_grid = s_result
            return True
        elif self.hard_data.hasData(): #only has hard
            h_result = byDataClass(self.hard_data)
            if h_result == False:
                return False
            self.hard_data.tr, self.hard_data.tr_grid = h_result
            return True
        elif self.soft_data.hasData(): #only has soft
            s_result = byDataClass(self.soft_data)
            if s_result == False:
                return False
            self.soft_data.tr, self.soft_data.tr_grid = s_result
            return True
        else:
            raise ValueError("Must be an error")
    
    def setOptions(self, idx, value):
        self.options[idx][0] = value

    def setOrder(self, order):
        if type(order) != float and not isinstance(order, str):
            raise ValueError('No supported type found')
        else:
            self.order = order
            return True
        
    def setNhmax(self, int_):
        if type(int_) != int:
            return False
        else:
            self.nhmax = int_
            return True
        
    def setNsmax(self, int_):
        if type(int_) != int:
            return False
        else:
            self.nsmax = int_
            return True
        
    def setDmax(self, dmax):
        if len(dmax) !=3:
            return False
        else:
            if type(dmax[0]) != float or type(dmax[1]) != float or type(dmax[2]) != float:
                return False
            else:
                self.dmax = [dmax] # 1 by 3  "2d"list
                return True
    
    def hasCrossValidation( self ):
        return self.has_cross_validation
        
    def crossValidation( self, sample_number = None, boundary = None, use_data = 'hard',
                         detrend_method = "No Detrending", detrend_parameter = () ):
        '''boundary: [xmin,xmax,ymin,ymax,tmin,tmax] '''

        def getCovModel():
            def convertPythonModelName(modelname): #convertPyModelNameToCModelIndex
                #                     C   PYTHON
                #//exponentialC     = 1     1
                #//gaussianC        = 2     0
                #//holesinC         = 3     
                #//holecosC         = 4     3
                #//nuggetC          = 5     4
                #//sphericalC       = 6     2
                #//mexicanhatC      = 7
                d={"gaussian":'gaussianC', "exponential":'exponentialC',
                   "spherical":'sphericalC', "holecos":'holecosC',
                   "nugget":'nuggetC'}
                return d[modelname.lower()]
            
            covparam = []
            covmodel = []
            for bv in self.covariance.models:
                covparam.append( bv[::2] )
                covmodel.append( convertPythonModelName(bv[1])+'/'+convertPythonModelName(bv[3]) )

            return covmodel,covparam

        hard_dataset = None
        soft_dataset = None
        all_dataset = None
        #combine
        if self.hard_data.hasData():
            hard_dataset = numpy.hstack( ( self.hard_data.x, self.hard_data.y, self.hard_data.t, self.hard_data.z, self.hard_data.tr ) )
        if self.soft_data.hasData():
            soft_dataset = numpy.hstack( ( self.soft_data.x, self.soft_data.y, self.soft_data.t, self.soft_data.z, self.soft_data.tr ) )

        if use_data == 'hard':
            all_dataset = hard_dataset
        elif use_data == 'soft':
            all_dataset = soft_dataset
        elif use_data == 'both':
            all_dataset = numpy.vstack( ( hard_dataset,soft_dataset ) )
        else:
            raise ValueError( 'parameter "use_data" is wrong.')
        
        
        #clip from boundary
        if not boundary:
            clip_hard_dataset = None
            clip_soft_dataset = None
            hard_original_index = None
            soft_original_index = None
            if use_data in ['hard','both']:
                clip_hard_dataset = hard_dataset
                hard_original_index = numpy.arange( len( hard_dataset ) )
            if use_data in ['soft','both']:
                clip_soft_dataset = soft_dataset
                soft_original_index = numpy.arange( len( soft_dataset ) )
        else:
            xmin,xmax,ymin,ymax,tmin,tmax = boundary
            if use_data in ['hard','both']:
                condition_x = ( hard_dataset[:,0] >= xmin ) & ( hard_dataset[:,0] <= xmax )
                condition_y = ( hard_dataset[:,1] >= ymin ) & ( hard_dataset[:,1] <= ymax )
                condition_t = ( hard_dataset[:,2] >= tmin ) & ( hard_dataset[:,2] <= tmax )
                hard_original_index = numpy.where( condition_x & condition_y & condition_t )[0]
                clip_hard_dataset = hard_dataset[ condition_x & condition_y & condition_t ]
                
            if use_data in ['soft','both']:
                condition_x = ( soft_dataset[:,0] >= xmin ) & ( soft_dataset[:,0] <= xmax )
                condition_y = ( soft_dataset[:,1] >= ymin ) & ( soft_dataset[:,1] <= ymax )
                condition_t = ( soft_dataset[:,2] >= tmin ) & ( soft_dataset[:,2] <= tmax )
                soft_original_index = numpy.where( condition_x & condition_y & condition_t )[0]
                clip_soft_dataset = soft_dataset[ condition_x & condition_y & condition_t ]

        len_clip_hard_dataset = 0
        len_clip_soft_dataset = 0
        if use_data == 'hard':
            len_clip_hard_dataset = len( clip_hard_dataset )
        elif use_data == 'soft':
            len_clip_soft_dataset = len( clip_soft_dataset )
        elif use_data == 'both':
            len_clip_hard_dataset = len( clip_hard_dataset )
            len_clip_soft_dataset = len( clip_soft_dataset )
        sample_number_all = len_clip_hard_dataset + len_clip_soft_dataset
            
        #set sample_number for a valid value,
        if sample_number:
            sample_number = min( [ sample_number, sample_number_all ] )
        else:
            sample_number = sample_number_all

        #get random sample index
        all_sample_index = numpy.array( sorted( random.sample( range( sample_number_all ), sample_number ) ) )
        #change to original index
        hard_sample_index = all_sample_index[ all_sample_index <= len_clip_hard_dataset - 1 ]
        soft_sample_index = all_sample_index[ all_sample_index > len_clip_hard_dataset - 1 ] - len_clip_hard_dataset

        #get estimated trend (tr_cv e.g. self.hard/soft_data.tr_cv )
        tr_obj = Trend( function_name = detrend_method )
        tr_obj.setParameters( detrend_parameter + ( NoUseDataObj(), ) )

        tr_cv_h = numpy.empty( self.hard_data.x.shape )
        tr_cv_h[:] = numpy.nan
        tr_cv_s = numpy.empty( self.soft_data.x.shape )
        tr_cv_s[:] = numpy.nan

        self.setCurrentProgress(0, "Estimate Trend...")
        #parse hard
        if len( hard_sample_index ):
            for idx in hard_original_index[ hard_sample_index ]:
                dataset = all_dataset[ numpy.arange( len( all_dataset ) ) != idx, : ]
                x,y,t,z,dummy_tr = list(map( lambda x: numpy.array(x,ndmin=2).T, numpy.transpose( dataset ) ))
                # result = rawdata2griddata(x,y,t,z, self)
                result = rawdata2griddata(x,y,t,z)
                if result:
                    grid_s, grid_t, grid_z = result
                    tr_obj.setData( result )
                    x_est, y_est, t_est = list(map( lambda x: numpy.array([ x ],ndmin=2).T, all_dataset[ idx,:3 ] ))
                    tr_obj.setCoordinate( (x_est, y_est, t_est) )
                    tr_cv_h[idx][0] =  tr_obj.estimate()
                else:
                    return False

        #parse soft
        if len( soft_sample_index ):
            for idx in soft_original_index[ soft_sample_index ]:
                if use_data == 'both':
                    idx2 = idx + len( hard_dataset )
                else: #soft
                    idx2 = idx
                dataset = all_dataset[ numpy.arange( len( all_dataset ) ) != idx2, : ]
                x,y,t,z,dummy_tr = list(map( lambda x: numpy.array(x,ndmin=2).T, numpy.transpose( dataset ) ))
                # result = rawdata2griddata(x,y,t,z, self)
                result = rawdata2griddata(x,y,t,z)
                if result:
                    grid_s, grid_t, grid_z = result
                    tr_obj.setData( result )
                    x_est, y_est, t_est = list(map( lambda x: numpy.array([ x ],ndmin=2).T, all_dataset[ idx2,:3 ] ))
                    tr_obj.setCoordinate( (x_est, y_est, t_est) )
                    tr_cv_s[idx][0] =  tr_obj.estimate() #idx is the index relate to soft data
                else:
                    return False

        #now do bme
        z_cv_h = numpy.empty( self.hard_data.x.shape )
        z_cv_h[:] = numpy.nan
        z_cv_s = numpy.empty( self.soft_data.x.shape )
        z_cv_s[:] = numpy.nan

        #set progressbar
        self.setProgressRange(0,sample_number) #for trend and z
        self.setCurrentProgress(0, "BME Validation Starts...")

        #parse hard
        if len( hard_sample_index ):
            for idx in hard_original_index[ hard_sample_index ]:
                ck = hard_dataset[ idx : idx + 1, : 3 ]
                covmodel, covparam = getCovModel()
                nhmax, nsmax, dmax, order, options = self.nhmax, self.nsmax, self.dmax, self.order, self.options
                if self.hard_data.hasData():
                    dataset = hard_dataset[ numpy.arange( len( hard_dataset ) ) != idx, : ]

                    ch = dataset[ :,:3 ]
                    zh = ( dataset[ :, 3:4 ] - dataset[ :, 4:5 ] ) #residual
                else:
                    ch = numpy.array([],ndmin=2) 
                    zh = numpy.array([],ndmin=2) 

                if self.soft_data.hasData():
                    cs = soft_dataset[ :, :3 ]
                    softpdftype = self.soft_data.pdf_type
                    
                    

                    #convert probdens to normal
                    nlseq, limiseq, probadensseq = proba2probdens( 'dummy',
                                                                    self.soft_data.nl,
                                                                    self.soft_data.limi- self.soft_data.tr,
                                                                    self.soft_data.probdens
                                                                  )

                else:
                    cs = numpy.array([],ndmin=2) 
                    softpdftype = 1 #no use
                    nlseq = numpy.array([],ndmin=2) 
                    limiseq = numpy.array([],ndmin=2) 
                    probadensseq = numpy.array([],ndmin=2) 

                
                moments_temp = ck[:]
                info_temp = ck[:]

                result = BMEprobaMoments(ck,ch,cs,zh,
                                         softpdftype,
                                         nlseq,limiseq,probadensseq,
                                         covmodel,covparam,nhmax,nsmax,dmax,
                                         order,options, self.progress_dialog)

                if result: #tuple
                    [ moments_temp, info_temp ] = result
                    z_cv_h[ idx ][0] = moments_temp[0][0]
                else:
                    return False #cancel by user

        #parse soft
        if len( soft_sample_index ):
            for idx in soft_original_index[ soft_sample_index ]:
                ck = soft_dataset[ idx : idx + 1, : 3 ]
                if self.hard_data.hasData():
                    dataset = hard_dataset

                    ch = dataset[ :,:3 ]
                    zh = ( dataset[ :, 3:4 ] - dataset[ :, 4:5 ] ) #residual
                else:
                    ch = numpy.array([],ndmin=2) 
                    zh = numpy.array([],ndmin=2) 

                if self.soft_data.hasData():

                    soft_exclude_one_point_idx = ( numpy.arange( len( soft_dataset ) ) != idx )
                    dataset = soft_dataset[ soft_exclude_one_point_idx, : ]
                    cs = dataset[ :,:3 ]
                    softpdftype = self.soft_data.pdf_type
                    covmodel, covparam = getCovModel()
                    nhmax, nsmax, dmax, order, options = self.nhmax, self.nsmax, self.dmax, self.order, self.options

                    #convert probdens to normal
                    nlseq, limiseq, probadensseq = proba2probdens( 'dummy',
                                                                    self.soft_data.nl[ soft_exclude_one_point_idx, : ],
                                                                    (self.soft_data.limi- self.soft_data.tr)[ soft_exclude_one_point_idx, : ],
                                                                    self.soft_data.probdens[ soft_exclude_one_point_idx, : ]
                                                                  )

                else:
                    cs = numpy.array([],ndmin=2) 
                    softpdftype = 1 #no use
                    nlseq = numpy.array([],ndmin=2) 
                    limiseq = numpy.array([],ndmin=2) 
                    probadensseq = numpy.array([],ndmin=2) 

                
                moments_temp = ck[:]
                info_temp = ck[:]

                result = BMEprobaMoments(ck,ch,cs,zh,
                                         softpdftype,
                                         nlseq,limiseq,probadensseq,
                                         covmodel,covparam,nhmax,nsmax,dmax,
                                         order,options, self.progress_dialog)
                
                if result: #tuple
                    [ moments_temp, info_temp ] = result
                    z_cv_s[ idx ][0] = moments_temp[0][0]
                else:
                    return False #cancel by user



        #get z_cv_grid tr_cv_grid from hard data
        if self.hard_data.hasData():

            result = rawdata2griddata( self.hard_data.x, self.hard_data.y, self.hard_data.t, tr_cv_h, self )
            if result:
                dummy_s, summy_t, tr_cv_h_grid = result
            else:
                return False
            result = rawdata2griddata( self.hard_data.x, self.hard_data.y, self.hard_data.t, z_cv_h, self )
            if result:
                dummy_s, summy_t, z_cv_h_grid = result
            else:
                return False

        if self.soft_data.hasData():

            #get z_cv tr_cv_grid from soft data
            result = rawdata2griddata( self.soft_data.x, self.soft_data.y, self.soft_data.t, tr_cv_s, self )
            if result:
                dummy_s, summy_t, tr_cv_s_grid = result
            else:
                return False
            result = rawdata2griddata( self.soft_data.x, self.soft_data.y, self.soft_data.t, z_cv_s, self )
            if result:
                dummy_s, summy_t, z_cv_s_grid = result
            else:
                return False

        #confirm set
        # if len( hard_sample_index ) and len( soft_sample_index ):

        if self.hard_data.hasData():
            self.hard_data.tr_cv = tr_cv_h
            self.hard_data.tr_cv_grid = tr_cv_h_grid
            self.hard_data.z_cv = z_cv_h + tr_cv_h
            self.hard_data.z_cv_grid = z_cv_h_grid + tr_cv_h_grid

        if self.soft_data.hasData():
            self.soft_data.tr_cv = tr_cv_s
            self.soft_data.tr_cv_grid = tr_cv_s_grid
            self.soft_data.z_cv = z_cv_s + tr_cv_s
            self.soft_data.z_cv_grid = z_cv_s_grid + tr_cv_s_grid


        #calculate root mean square error (RMSE), Mean, Standard Deviation, Median, Min Value, Max Value
        error_h = self.hard_data.z - self.hard_data.z_cv
        error_s = self.soft_data.z - self.soft_data.z_cv
        error_h_without_nan = error_h[ ~numpy.isnan( error_h ) ] #flat to 1D
        error_s_without_nan = error_s[ ~numpy.isnan( error_s ) ]
        error_all = numpy.hstack( ( error_h_without_nan, error_s_without_nan ) )

        error_all_mean = numpy.mean( error_all )
        error_all_std = numpy.std( error_all )
        error_all_25_percentile = numpy.percentile( error_all, 25 )
        error_all_median = numpy.median( error_all )
        error_all_75_percentile = numpy.percentile( error_all, 75 )
        error_all_min = numpy.min( error_all )
        error_all_max = numpy.max( error_all )

        error_all_mse = numpy.mean( error_all ** 2 )
        error_all_rmse = numpy.sqrt( error_all_mse )

        return ( error_all_rmse, error_all_mean, error_all_std,
                 error_all_25_percentile, error_all_median, error_all_75_percentile,
                 error_all_min, error_all_max )


if __name__ == "__main__": #Non-GUI test
    pass