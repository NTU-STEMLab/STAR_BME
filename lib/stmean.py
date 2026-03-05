import numpy
# try:
#     from pylab import griddata as pylab_griddata #qgis
# except ImportError:
#     from matplotlib.pylab import griddata as pylab_griddata #OSGEO4W qgis

import idw

def stmean( grid_s, grid_t, grid_z, DataObj = None ):
    '''
    grid_s: row by 2 numpy array
    grid_t: 1 by col numpy array
    grid_z: row by col numpy array
    '''

    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()
        
    title = DataObj.getProgressText()
    
    DataObj.setProgressRange(0,len(grid_s))
    DataObj.setCurrentProgress(0, title + "\n- By STMean...")
    
    mask_grid_z = numpy.ma.masked_array(grid_z,numpy.isnan(grid_z))
    mean_s = numpy.array( mask_grid_z.mean( axis = 1 ) , ndmin = 2).T
    mean_t = numpy.array( mask_grid_z.mean( axis = 0 ) , ndmin = 2)
    mean_st = mask_grid_z.mean()
    grid_trend = mean_s + mean_t - mean_st
    
    grid_trend[numpy.where(numpy.isnan(grid_z))] = numpy.nan
#    print grid_z
#    print mean_s
#    print mean_t
#    print grid_trend
#    print mean_s + mean_t - mean_st
    return grid_trend
    
def stmean_est(grid_s, grid_t, grid_z, 
               est_grid_s, est_grid_t, DataObj = None):
    '''
    grid_s: row by 2 numpy array
    grid_t: 1 by col numpy array
    grid_z: row by col numpy array
    '''
    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()
        
    title = DataObj.getProgressText()
    
    DataObj.setProgressRange(0,len(grid_s))
    DataObj.setCurrentProgress(0, title + "\n- By STMean...")
    
    
    
    mask_grid_z = numpy.ma.masked_array(grid_z,numpy.isnan(grid_z))
    mean_s = numpy.array( mask_grid_z.mean( axis = 1 ) , ndmin = 2).T
    mean_t = numpy.array( mask_grid_z.mean( axis = 0 ) , ndmin = 2)
    mean_st = mask_grid_z.mean()
    
    temp_x,temp_y = map(numpy.array,zip(*grid_s))
    temp_x_est, temp_y_est = map(numpy.array,zip(*est_grid_s))
    mean_s_est = idw.idw_est( temp_x, temp_y, mean_s.T[0], temp_x_est, temp_y_est, power = 2 )
#    mean_s_est = pylab_griddata(temp_x,temp_y,mean_s.T[0],
#                                temp_x_est,temp_y_est,interp = 'nn')
    #temp_x_est and temp_y_est is not mono increasing
    #i don't know whether there is a bug in it
#    
#    mean_s_est = mean_s_est.diagonal()
    mean_s_est = numpy.array( mean_s_est,ndmin=2 ).T
    mean_t_est = numpy.array(numpy.interp(est_grid_t[0],grid_t[0],mean_t[0]),ndmin=2)
    
    #est_z_2d = pylab_griddata(pylab_x, pylab_y, point_value,est_x_2d, est_y_2d,interp = 'nn')
        
    grid_trend_est = mean_s_est + mean_t_est - mean_st
    
    return grid_trend_est
    
    
    

if __name__ == "__main__":
    grid_s=numpy.array([[1,3.],[1,8],[4,1],[3,2]])
    grid_t=numpy.array([[1,3,5,7,9.]])
    grid_z = numpy.array([[1,numpy.nan,3.,4,5],
                          [5,6,1,7,8],
                          [1,numpy.nan,4,2,5],
                          [5,2,6,3,1.]])
    
    grid_s_est=grid_s#numpy.array([[1,6.],[1,6]])[::-1]
    grid_t_est=grid_t#numpy.array([[1]])

    grid_trend = stmean(grid_s,grid_t,grid_z)
    print (grid_trend)
    grid_trend = stmean_est(grid_s,grid_t,grid_z,grid_s_est,grid_t_est)
    print (grid_trend)