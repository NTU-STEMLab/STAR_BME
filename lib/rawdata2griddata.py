'''
Created on 2011/5/7

@author: KSJ
'''
import time
import math
import numpy

def rawdata2griddata_list(x, y, t, z_list, DataObj = None):
    '''
    x: row by 1 numpy array
    y: ditto
    t: ditto
    z_list: list of value
    DataObj: for GUI use
    
    return (grid_s, grid_t, grid_z_list) , or return False if fail
    sort by x, then y, small to large
    grid_s: row by 2 (2D numpy array)
    grid_t: 1 by col (2D numpy array)
    grid_z_list: list of row_s by col_t (2D numpy array)
    '''

    
    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()
        
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
    
    DataObj.setCurrentProgress(text = title)
    return grid_s, grid_t, grid_z_list



def rawdata2griddata(x, y, t, z, DataObj = None):
    '''
    x: row by 1 numpy array
    y: ditto
    t: ditto
    z: ditto
    DataObj: for GUI use
    
    return (grid_s, grid_t, grid_z) , or return False if fail
    sort by x, then y, small to large
    grid_s: row by 2 (2D numpy array)
    grid_t: 1 by col (2D numpy array)
    grid_z: row_s by col_t (2D numpy array)
    '''

    
    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()
        
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

    if not hasattr(numpy, 'in1d'):
        numpy.in1d = numpy.setmember1d
    
    for index_s, s in enumerate(grid_s):
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

def rawdata2griddataforcoor(x, y, t, DataObj = None):
    STEP_COUNT = 1000
    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()
        
    title = DataObj.getProgressText()
    
    #process S
    xy = numpy.hstack((x, y))
    xy = xy.tolist()
    length = len(xy)
    
    step = int(math.ceil(length / float(STEP_COUNT)))
    DataObj.setProgressRange(0, step)
    DataObj.setCurrentProgress(0, title + "\n- Change Numpy Array to Tuple...")
    result = []
    for i in range(step):
        if not DataObj.wasProgressCanceled():
            result += list(map(tuple, xy[i * STEP_COUNT:(i + 1) * STEP_COUNT]))
            DataObj.setCurrentProgress(i + 1)
        else:
            return False
    xy = tuple(result)
#    xy = map(tuple,xy)
    xy = set(xy)
    DataObj.setProgressRange(0, len(xy))
    DataObj.setCurrentProgress(0, title + "\n- Converting RawData to GridData...")
    #xy = map(list, xy)
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
