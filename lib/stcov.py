#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
於2011年5月10號建立
Created on 2011/5/10

參考matlab版的stcov而做，想法與實作方法上有些不同

這是用來算時空分析的變異數的函數，輸入與輸出說明如下：
lagCOVs,lagCOVt,lagCOVv,lagCOVn = stcov(grid_s,grid_t,grid_v,
                       lagS,lagS_range,
                       lagT,lagT_range):
    輸入變數：
    grid_s：numpy 2維陣列(因為包含x與y)，為所有測站的空間座標值
    grid_t：numpy 1維陣列，為所有測量的時間座標值
    grid_v：numpy 2維陣列，以grid_s為列，grid_t為行所對應的測量值
    lagS：numpy 1維陣列，變異數空間軸的點
    lagS_range：numpy 1維陣列，對應該點計算時的空間範圍
    lagT：numpy 1維陣列，變異數時間軸的點
    lagT_range：numpy 1維陣列，對應該點計算時的時間範圍
    
    輸出變數：
    lagCOVs：lagCOVv相對應點之空間差值 
            [[0,0,0,0,0]
             [1,1,1,1,1]
             [2,2,2,2,2]
                [...]   ]
    lagCOVt：lagCOVv相對應點之時間差值
            [[1,2,3,4,5]
             [1,2,3,4,5]
             [1,2,3,4,5]
                [...]   ]
    lagCOVv：以lagS為列，lagT為行的2維變異數陣列
    lagCOVn：變異數陣列計算時包含的總資料筆數 
    
    舉例：
           以下都必須轉成numpy array
    grid_s = [ [1.,3.]
               [2.,4.]
               [5.,7.] ]
    grid_t = [ 1. , 4., 6. ]
    grid_v = [ [1.,2.,3.]
               [4.,numpy.nan,6.]
               [7.,8.,9.]
    
@作者：顧尚真
@author: KSJ
'''
import itertools

import numpy
from diffarray import diffarray

def stcov(grid_s,grid_t,grid_v,lagS,lagS_range,lagT,lagT_range, DataObj = None):

    #if no GUI, give a no use obj
    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()       
    title = DataObj.getProgressText()
    
    #find spatial difference between x and y, then remember each index
    #將空間軸與時間軸各轉為每點相差的值，並記住其index (用"_i_"表示)
    s_diff_i_left,s_diff_i_right,s_diff_v=diffarray(grid_s)
    s_diff_v=numpy.sqrt(s_diff_v[:,0]**2+s_diff_v[:,1]**2)
    t_diff_i_left,t_diff_i_right,t_diff_v=diffarray(grid_t)
    t_diff_v=numpy.abs(t_diff_v)
        
    
    
    
    #meshgrid s,t
    lagTT,lagSS=numpy.meshgrid(lagT,lagS)

    #create result by lagSS's shape
    lagCOVv = numpy.empty(lagSS.shape)
    lagCOVv[:]=numpy.nan

    lagCOVm1 = numpy.empty(lagSS.shape)
    lagCOVm1[:]=numpy.nan
    #lagCOVm2 = numpy.zeros(lagSS.shape)
    lagCOVn = numpy.zeros(lagSS.shape)


    DataObj.setProgressRange(0,len(lagS))
    DataObj.setCurrentProgress(0, title + "\n- Calculating Covariance ...")
    
    #loop lagS first
    for indexS,m in enumerate(lagS):
        if not DataObj.wasProgressCanceled():
            #find all index that s_diff_v in range lagS_range
            index_diff_s = numpy.where( (s_diff_v >= m-lagS_range[indexS]) & (s_diff_v <= m+lagS_range[indexS]) )[0]
            
            DataObj.setCurrentProgress(indexS + 1) #rest
            
            s_diff_i_left_select=s_diff_i_left[index_diff_s]
            if s_diff_i_left_select.size == 0: #no match
                continue
            s_diff_i_right_select=s_diff_i_right[index_diff_s]
            
            #loop lagT then ( if lagS matched )
            for indexT,n in enumerate(lagT):
                index_diff_t=numpy.where( (t_diff_v >= n-lagT_range[indexT]) & (t_diff_v <= n+lagT_range[indexT]) )[0]
                
                DataObj.setCurrentProgress(indexS + 1) #rest
                
                t_diff_i_left_select=t_diff_i_left[index_diff_t]
                if t_diff_i_left_select.size == 0:
                    continue
                t_diff_i_right_select=t_diff_i_right[index_diff_t]
    
    
                #get grid_v that matched range
                grid_v_left_select=grid_v[numpy.ix_(s_diff_i_left_select,t_diff_i_left_select)]
                grid_v_right_select=grid_v[numpy.ix_(s_diff_i_right_select,t_diff_i_right_select)]
                
                #maybe has numpy.nan, exclude it
                grid_v_not_nan_index= ~(numpy.isnan(grid_v_left_select) | numpy.isnan(grid_v_right_select))    
                grid_v_left_select=grid_v_left_select[grid_v_not_nan_index]
                grid_v_right_select=grid_v_right_select[grid_v_not_nan_index]
                
                
                lagCOVv[indexS][indexT] = 2.*(grid_v_left_select * grid_v_right_select).sum()
                lagCOVm1[indexS][indexT] = (grid_v_left_select + grid_v_right_select).sum()
                lagCOVn[indexS][indexT] = 2. * grid_v_left_select.size
                
                DataObj.setCurrentProgress(indexS + 1) #rest
                
                #add not equal pair, need to be calculate twice
                s_diff_i_not_equal = numpy.where( s_diff_i_left_select != s_diff_i_right_select)
                t_diff_i_not_equal = numpy.where( t_diff_i_left_select != t_diff_i_right_select)
      
                s_diff_i_left_select_2 = s_diff_i_left_select[s_diff_i_not_equal]
                s_diff_i_right_select_2 = s_diff_i_right_select[s_diff_i_not_equal]
                t_diff_i_left_select_2 = t_diff_i_left_select[t_diff_i_not_equal]
                t_diff_i_right_select_2 = t_diff_i_right_select[t_diff_i_not_equal]
    
                
                grid_v_left_select=grid_v[numpy.ix_(s_diff_i_right_select_2,t_diff_i_left_select_2)]
                grid_v_right_select=grid_v[numpy.ix_(s_diff_i_left_select_2,t_diff_i_right_select_2)]
                
                grid_v_not_nan_index= ~(numpy.isnan(grid_v_left_select) | numpy.isnan(grid_v_right_select))
                
                grid_v_left_select=grid_v_left_select[grid_v_not_nan_index]
                grid_v_right_select=grid_v_right_select[grid_v_not_nan_index]
                
                DataObj.setCurrentProgress(indexS + 1) #rest
                
                lagCOVv[indexS][indexT] += 2.*(grid_v_left_select * grid_v_right_select).sum()
                lagCOVm1[indexS][indexT] += (grid_v_left_select + grid_v_right_select).sum()
                lagCOVn[indexS][indexT] += 2. * grid_v_left_select.size
            DataObj.setCurrentProgress(indexS + 1)
        else:
            return False
                
    lagCOVv/=lagCOVn
    lagCOVm1/=lagCOVn 
    lagCOVv-=lagCOVm1**2
    
    DataObj.setCurrentProgress(text = title)
    return lagSS,lagTT,lagCOVv,lagCOVn

def cov_avg_nd( coord, value, lagC, lagC_range ):
    '''
    get covariance of each range(block) and their pair number
     
    input
    coord: a list of delta matrixs
    value: row x 1, 2d numpy array
    lagC: a list of lag_limit(1d numpy array)
    lagC_range: a list of range_limit(1d numpy array)
    
    return 
    lagCOVv: dim of each lagC's len
    lagCOVn: dim of each lagC's len
    '''
    
#    delta_coord = [] #a list store each delta coordinate
#    for i in xrange( coord_dim ):
#        coord_i = coord[ :, i:i+1 ]
#        delta_coord.append( coord_i - coord_i.T )
        
    delta_value_multi = value * value.T
    delta_value_add_left = value * numpy.ones( value.T.shape )
    delta_value_add_right = value.T * numpy.ones( value.shape )
    
    matched_bool_matrix = [] # a coord_dim list store every matched bool matrix ( coord_dim x lag_num )
    for coord_i, lags, ranges in zip( coord, lagC, lagC_range ):
        matched_bool_matrix_i = [] #store 1 of coord_dim matched matrix
        for lag_i, range_i in zip( lags, ranges ):
            matched_bool_matrix_i.append( ( coord_i > lag_i - range_i ) & ( coord_i <= lag_i + range_i ) )
        matched_bool_matrix.append( matched_bool_matrix_i )
    
    #check a range has data included
#    has_data_bool_matrix = []
#    for matched_bool_matrix_i in matched_bool_matrix:
#        has_data_bool_matrix_i = [] 
#        for each_matchhed_bool_matrix in matched_bool_matrix_i:
#            has_data_bool_matrix_i.append( each_matchhed_bool_matrix.any() )
#        has_data_bool_matrix.append( has_data_bool_matrix_i )
        
    #get index set
    #use itertools to get the index of each possible case(each block)
    lag_dim_len = [ len(i) for i in lagC ]
    index_set = list( itertools.product( *map( range, lag_dim_len ) ) )
    
    #get each block value ( covariance )
    ####set result lagCOV
    lagCOVv = numpy.empty( lag_dim_len ) #index for each dim
    lagCOVm1 = numpy.empty( lag_dim_len )
    lagCOVm2 = numpy.empty( lag_dim_len )
    lagCOVv[:] = numpy.nan
    lagCOVm1[:] = numpy.nan
    lagCOVm2[:] = numpy.nan
    
    lagCOVn = numpy.zeros( lag_dim_len )
    
    
    for idx in index_set:
        #set the result bool matrix
        res_idx_matrix = numpy.ones( matched_bool_matrix[0][0].shape, dtype = bool )
        #logical-and for each dim 
        for idx_i, m_b_mat_i in zip( idx, matched_bool_matrix ):
            res_idx_matrix = numpy.logical_and( res_idx_matrix, m_b_mat_i[ idx_i ] )
        if res_idx_matrix.any() and numpy.sum( res_idx_matrix ) > 1: #has data and data num at least 2 or cannot calculate covariance
            select_dv = delta_value_multi[ res_idx_matrix ]
            select_dm1 = delta_value_add_left[ res_idx_matrix ]
            select_dm2 = delta_value_add_right[ res_idx_matrix ]
            
            lagCOVv[idx] = select_dv.sum()
            lagCOVm1[idx] = select_dm1.sum()
            lagCOVm2[idx] = select_dm2.sum()
            lagCOVn[idx] =  select_dv.size
        else:
            print( "can not calculate")
#    for j in xrange( lag_num ):    
#        for i in xrange( coord_dim ): #row of matched_bool_matrix
#            has_data_bool_matrix[ i ][ j ] =  matched_bool_matrix[ i ][ j ].any()
#            
        
    lagCOVv /= lagCOVn
    lagCOVm1 /= lagCOVn
    lagCOVm2 /= lagCOVn
    lagCOVv -= lagCOVm1*lagCOVm2
    
    return lagCOVv, lagCOVn
            
            
        
        
###### CANNOT USE                      
####def sacov( grid_s, grid_v, lagR, lagR_range, lagA, lagA_range, DataObj = None ):
####    
####    #if no GUI, give a no use obj
####    if not DataObj:
####        from nousedataobj import NoUseDataObj
####        DataObj = NoUseDataObj()
####        
####    title = DataObj.getProgressText()
####        
####        
####    #find spatial difference between x and y, then remember each index
####    s_diff_i_left, s_diff_i_right, s_diff_v = diffarray( grid_s ) # s_diff_v = [ [dx, dy],... ]
####    #get dr, da
####    delta_x = s_diff_v[:,0] #this will convert it to 1d raw
####    delta_y = s_diff_v[:,1]
####    delta_angle = numpy.arctan( delta_y / delta_x )
####    #convert 4th quadrant to 2nd quadrant
####    delta_angle[ (delta_angle > -0.5*numpy.pi ) & (delta_angle <= 0.*numpy.pi ) ] += numpy.pi
####    r_diff_v = numpy.sqrt( delta_x**2 + delta_y**2 )
####    a_diff_v = delta_angle
####    
####    #meshgrid r,a
####    lagAA,lagRR = numpy.meshgrid(lagA,lagR)
####    #create result by lagRR's shape
####    lagCOVv = numpy.empty(lagRR.shape)
####    lagCOVv[:]=numpy.nan
####    lagCOVm1 = numpy.empty(lagRR.shape)
####    lagCOVm1[:]=numpy.nan
####    lagCOVm2 = numpy.empty(lagRR.shape)
####    lagCOVm2[:]=numpy.nan
####    lagCOVn = numpy.zeros(lagRR.shape)
####        
####    DataObj.setProgressRange(0,len(lagS))
####    DataObj.setCurrentProgress(0, title + "\n- Calculating Covariance ...")
####    
####    
####    #loop lagR first
####    for indexR,m in enumerate(lagR):
####        if not DataObj.wasProgressCanceled():
####            #find all index that r_diff_v in range lagR_range
####            index_diff_r = numpy.where( (r_diff_v >= m-lagR_range[indexR]) & (r_diff_v <= m+lagR_range[indexR]) )[0]
####            
####            DataObj.setCurrentProgress(indexR + 1) #rest
####            
####            r_diff_i_left_select = r_diff_i_left[ index_diff_r ]
####            if r_diff_i_left_select.size == 0: #no match
####                continue
####            r_diff_i_right_select = r_diff_i_right[ index_diff_r ]
####            
####            #loop lagA then ( if lagR matched )
####            for indexA,n in enumerate(lagA):
####                index_diff_a = numpy.where( ( a_diff_v >= n-lagA_range[ indexA ] ) & ( a_diff_v <= n + lagA_range[indexA]) )[0]
####                
####                DataObj.setCurrentProgress( indexA + 1 ) #rest
####                
####                a_diff_i_left_select = a_diff_i_left[ index_diff_a ]
####                if a_diff_i_left_select.size == 0:
####                    continue
####                a_diff_i_right_select = a_diff_i_right[ index_diff_a ]
####    
####    
####                #get grid_a that matched range
####                grid_v_left_select=grid_v[numpy.ix_(r_diff_i_left_select, a_diff_i_left_select)]
####                grid_v_right_select=grid_v[numpy.ix_(r_diff_i_right_select, a_diff_i_right_select)]
####                
####                #maybe has numpy.nan, exclude it
####                grid_v_not_nan_index= ~(numpy.isnan(grid_v_left_select) | numpy.isnan(grid_v_right_select))    
####                grid_v_left_select=grid_v_left_select[grid_v_not_nan_index]
####                grid_v_right_select=grid_v_right_select[grid_v_not_nan_index]
####                
####                #do calculate
####                lagCOVv[indexR][indexA] = (grid_v_left_select * grid_v_right_select).sum()
####                lagCOVm1[indexR][indexA] = grid_v_left_select.sum()
####                lagCOVm2[indexR][indexA] = grid_v_right_select.sum()
####                lagCOVn[indexR][indexA] = grid_v_left_select.size
####                
####                DataObj.setCurrentProgress(indexS + 1) #reset
####                
####                s_diff_i_not_equal = numpy.where( s_diff_i_left_select != s_diff_i_right_select)
####                t_diff_i_not_equal = numpy.where( t_diff_i_left_select != t_diff_i_right_select)
####      
####                s_diff_i_left_select_2 = s_diff_i_left_select[s_diff_i_not_equal]
####                s_diff_i_right_select_2 = s_diff_i_right_select[s_diff_i_not_equal]
####                t_diff_i_left_select_2 = t_diff_i_left_select[t_diff_i_not_equal]
####                t_diff_i_right_select_2 = t_diff_i_right_select[t_diff_i_not_equal]
####    
####                
####                grid_v_left_select=grid_v[numpy.ix_(s_diff_i_right_select_2,t_diff_i_left_select_2)]
####                grid_v_right_select=grid_v[numpy.ix_(s_diff_i_left_select_2,t_diff_i_right_select_2)]
####                
####                grid_v_not_nan_index= ~(numpy.isnan(grid_v_left_select) | numpy.isnan(grid_v_right_select))
####                
####                grid_v_left_select=grid_v_left_select[grid_v_not_nan_index]
####                grid_v_right_select=grid_v_right_select[grid_v_not_nan_index]
####                
####                DataObj.setCurrentProgress(indexS + 1) #rest
####                
####                lagCOVv[indexS][indexT] += 2.*(grid_v_left_select * grid_v_right_select).sum()
####                lagCOVm1[indexS][indexT] += (grid_v_left_select + grid_v_right_select).sum()
####                lagCOVn[indexS][indexT] += 2. * grid_v_left_select.size
####            DataObj.setCurrentProgress(indexS + 1)
####        else:
####            return False
        
        
        
        
if __name__ == "__main__":
    d=numpy.load("variables2.npz")
    for key,value in d.items():
        locals()[key]=value
    print( "loadOK")
    s_diff_i_left,s_diff_i_right,s_diff_v=diffarray(grid_s)
    print('diffok')
    s_bound=s_diff_v.max()*2./3
    s_n=15
    t_n=20
    
    lagS = numpy.linspace(0,s_bound,s_n)
    lagS_range = numpy.array([s_bound/(s_n-1)*0.5]*s_n)
    lagT = numpy.arange(0,21,1)                         
    lagT_range = numpy.array([0.5]*(t_n+1))
    
    s,t,COV,COVn=stcov(grid_s,grid_t,grid_r,lagS,lagS_range,lagT,lagT_range)
    print(s)
    print(t)
    print(COV)
    print(COVn)
    numpy.savez("COV",COV=COV,COVn=COVn)
    print('saveok')