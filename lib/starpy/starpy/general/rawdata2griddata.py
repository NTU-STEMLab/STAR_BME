# -*- coding: utf-8 -*-
'''
Created on 2011/5/7

@author: KSJ
'''
import math
import numpy


def rawdata2griddata_list(x, y, t, z_list, DataObj = None):
    '''
    
    Input:     
    x       n by 1          Spatial coordinate x for space/time data    
    y       n by 1          Spatial coordinate y for space/time data
    t       n by 1          time coordinate t for space/time data
    z       list of n by 1  list of vectors of field values at coordiate (x,y,t)   
    DataObj optional for GUI use 

    Output: 
    
    grid_s  nMS by 2        matrix of spatial coordinates for the nMS Measuring Sites (cMS)  
    grid_t  1 by nME        vector of times of the tME Measuring Events 
    grid_z  list of         list of matrix of values for the variable Z corresponding to 
            nMS by nME      nMS Monitoring Sites and nME Measuring Event
    
    Note: 
    1) All array in Input and Output are in numpy 2D array
    2) cMS is sort ascendingly first by x then y 
    1) return (grid_s, grid_t, grid_z_list) , or return False if fail
    sort by x, then y, small to large    
    '''

#    if not DataObj:
#        from nousedataobj import NoUseDataObj
#        DataObj = NoUseDataObj()
    if DataObj:    
      title = DataObj.getProgressText()
    
    #process S and T
    result = rawdata2griddataforcoor(x, y, t, DataObj)
    if result is False:
      return False
    else:
      grid_s, grid_t = result
        
    #version cover
    try :
      numpy.in1d = numpy.setmember1d
    except AttributeError:
      pass

    #process Z_list
    
    #init grid_z_list
    grid_z_list = []
    grid_z = numpy.empty((grid_s.shape[0], grid_t.shape[1]))
    grid_z[:] = numpy.nan
    for i in range( len( z_list ) ):
      grid_z = numpy.empty((grid_s.shape[0], grid_t.shape[1]))
      grid_z[:] = numpy.nan
      grid_z_list.append( grid_z[:] )

    
    for index_s, s in enumerate(grid_s):
      if DataObj:
        if not DataObj.wasProgressCanceled():
          select_rows = numpy.where((x.flatten() == s[0]) & (y.flatten() == s[1]))[0]
          t_sel = t.flatten()[select_rows]
          for idx, z in enumerate(z_list):
            z_sel = z.flatten()[select_rows]
            for ti, zi in zip(t_sel, z_sel):
                t_col = numpy.where(grid_t[0] == ti)[0]
                if t_col.size > 0:
                    grid_z_list[idx][index_s, t_col[0]] = zi
            DataObj.setCurrentProgress(value=index_s + 1)
        else:
          return False
      else:
        select_rows = numpy.where((x.flatten() == s[0]) & (y.flatten() == s[1]))[0]
        t_sel = t.flatten()[select_rows]
        for idx, z in enumerate(z_list):
          z_sel = z.flatten()[select_rows]
          for ti, zi in zip(t_sel, z_sel):
              t_col = numpy.where(grid_t[0] == ti)[0]
              if t_col.size > 0:
                  grid_z_list[idx][index_s, t_col[0]] = zi
        
    
    if DataObj:
      DataObj.setCurrentProgress(text = title)
    
    return grid_s, grid_t, grid_z_list



def rawdata2griddata(x, y, t, z, DataObj = None):
    '''
    This function is now replaced by starpy.general.valstvgx.valstv2stg function
    
    Input:     
    x       n by 1          Spatial coordinate x for space/time data    
    y       n by 1          Spatial coordinate y for space/time data
    t       n by 1          time coordinate t for space/time data
    z       n by 1          list of vectors of field values at coordiate (x,y,t)   
    DataObj optional for GUI use 

    Output: 
    
    grid_s  nMS by 2        matrix of spatial coordinates for the nMS Measuring Sites (cMS)  
    grid_t  1 by nME        vector of times of the tME Measuring Events 
    grid_z  nMS by nME      matrix of values for the variable Z corresponding to 
            nMS Monitoring Sites and nME Measuring Event
    
    Note: 
    1) All array in Input and Output are in numpy 2D array
    2) cMS is sort ascendingly first by x then y 
    1) return (grid_s, grid_t, grid_z_list) , or return False if fail
    sort by x, then y, small to large    
    '''
    x=x.reshape(x.size,1)
    y=y.reshape(y.size,1)
    t=t.reshape(z.size,1)
    z=z.reshape(z.size,1)
    
#    if not DataObj:
#        from nousedataobj import NoUseDataObj
#        DataObj = NoUseDataObj()
    if DataObj:    
      title = DataObj.getProgressText()
    
    #process S and T
    result = rawdata2griddataforcoor(x, y, t, DataObj)
    if result is False:
        return False
    else:
        grid_s, grid_t = result
        
    #process Z
    grid_z = numpy.empty((grid_s.shape[0], grid_t.shape[1]))
    grid_z[:] = numpy.nan

    
    try :
        numpy.in1d = numpy.setmember1d
    except AttributeError:
        pass
    
    for index_s, s in enumerate(grid_s):
      if DataObj:
        if not DataObj.wasProgressCanceled():
          select_rows = numpy.where((x.flatten() == s[0]) & (y.flatten() == s[1]))[0]
          t_sel = t.flatten()[select_rows]
          z_sel = z.flatten()[select_rows]
          for ti, zi in zip(t_sel, z_sel):
              t_col = numpy.where(grid_t[0] == ti)[0]
              if t_col.size > 0:
                  grid_z[index_s, t_col[0]] = zi
          DataObj.setCurrentProgress(value=index_s + 1)
        else:
          return False
      else:
        select_rows = numpy.where((x.flatten() == s[0]) & (y.flatten() == s[1]))[0]
        t_sel = t.flatten()[select_rows]
        z_sel = z.flatten()[select_rows]
        for ti, zi in zip(t_sel, z_sel):
            t_col = numpy.where(grid_t[0] == ti)[0]
            if t_col.size > 0:
                grid_z[index_s, t_col[0]] = zi
    
    if DataObj:
      DataObj.setCurrentProgress(text = title)
    
#    for xi,yi,ti,zi in zip(x,y,t,z):
#        index_S=numpy.where(numpy.all(numpy.equal(grid_s,[xi,yi]),1) == True)[0][0]
#        index_T=numpy.where(numpy.equal(grid_t,ti) == True)[0][0]
#        grid_z[index_S][index_T]=zi
#    print grid_z
    #result=list(set(map(str,numpy.vstack((x,y)).T)))#[1:-1].split("\n "))
    #===========================================================================
    # d = {}
    # for i in numpy.vstack((x,y)).T:
    #    d[str(i)]=i
    #    result = numpy.vstack(d.values())
    #===========================================================================
    return grid_s, grid_t, grid_z

def griddata2rawdata(Z, cMS, tME):
    '''
    Converts the coordinates and values of a space/time variable 
    from a grid format (i.e. the variable Z is given as a nMS by nME matrix  
    corresponding to nMS Measuring Sites and nME Measuring Events),
    to a s/t vector format (i.e. the variable z is listed as a vector of nMS*nME values,
    corresponding to points with space/time coordinates, where the spatial coordinate
    cycle quicker than the time coordinates).   
    
    Input: 
        Z       nMS by nME      
        cMS     nMS by 2        
        tME     1 by nME        
        
    Output:
        ch      nMS*nME by 3    
        zh      nME*nME by 1
        
    Note: all input and output should be in numpy 2D array    
    '''    
    nMS=cMS.shape[0]
    nME=tME.shape[1]
    zh=(Z.T).reshape(nMS*nME,1)
    ch=numpy.hstack((numpy.kron(numpy.ones((nME,1)),cMS), \
        numpy.kron(tME.T,numpy.ones((nMS,1)))))
    idx=numpy.nonzero(~numpy.isnan(zh))
    zh=zh[idx[0],:]
    ch=ch[idx[0],:]
    
    return ch,zh


def rawdata2griddataforcoor(x, y, t, DataObj = None):
    
#    if not DataObj:
#        from nousedataobj import NoUseDataObj
#        DataObj = NoUseDataObj()
        
    if DataObj:
      title = DataObj.getProgressText()
    
    STEP_COUNT = 1000
    
    #process S
    xy = numpy.hstack((x, y))
    xy = xy.tolist()
    length = len(xy)  
    
    step = int(math.ceil(length / float(STEP_COUNT)))
    if DataObj:
      DataObj.setProgressRange(0, step)
      DataObj.setCurrentProgress(0, title + "\n- Change Numpy Array to Tuple...")
    result = []
    for i in range(step):
      if DataObj:
        if not DataObj.wasProgressCanceled():
          result += list(map(tuple, xy[i * STEP_COUNT:(i + 1) * STEP_COUNT]))
          DataObj.setCurrentProgress(i + 1)
        else:
          return False
      else:
        result += list(map(tuple, xy[i * STEP_COUNT:(i + 1) * STEP_COUNT]))  
    xy = tuple(result)
#    xy = map(tuple,xy)
    xy = set(xy)
    
    if DataObj:
      DataObj.setProgressRange(0, len(xy))
      DataObj.setCurrentProgress(0, title + "\n- Converting RawData to GridData...")
    
    xy = list(map(list, xy))
    xy.sort(key=lambda i:(i[0], i[1]))
    grid_s = numpy.array(xy) # n by 2
    
    #process T
    grid_t = numpy.unique(t) #grid_t: dimension 1 (sort included)
    grid_t = numpy.array(grid_t, ndmin=2) # grid_t: 1 by n
    return grid_s, grid_t
    
if __name__ == "__main__":
#    grid_s = numpy.random.random((3,2))
#    grid_t = numpy.random.random(4)
#    grid_z = numpy.random.random((3,4))
    
    x=numpy.array([1.,1,1,2,3],ndmin=2).T
    y=numpy.array([1.,2,1,2,1],ndmin=2).T
    t=numpy.array([1.,1,2,2,2],ndmin=2).T
    z=numpy.array([5.,4,2,4,1],ndmin=2).T
    
#    z=numpy.array([
#                   [ [5.,2] ],
#                   [ [3,4] ],
#                   [ [3,1] ],
#                   [ [6,8] ],
#                   [ [5,8] ],
#                   ])
    
#    x = numpy.random.random((1000000, 1))
#    y = numpy.random.random((1000000, 1))
#    t = numpy.random.random((1000000, 1))
#    z = numpy.random.random((1000000, 1))
    grid_s, grid_t, grid_z = rawdata2griddata(x, y, t, z)
    
    print (grid_s)
    print (grid_t)
    print (grid_z)

    grid_s, grid_t, [grid_z] = rawdata2griddata_list(x, y, t, [z])
    
    print (grid_s)
    print (grid_t)
    print (grid_z)
