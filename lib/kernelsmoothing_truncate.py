import math
import numpy
            
def kernelsmoothing(grid_s,grid_t,grid_z,bs,bt,ktype = "gaussian", DataObj = None):
    '''
    grid_s: row by 2 numpy array
    grid_t: 1 by col numpy array
    grid_z: row by col numpy array
    bs: float
    bt: flaot
    ktype: string
    DataObj: for GUI use
    
    return grid_trend, raw by col numpy array, or return False if fail
    '''
    if not DataObj:
        from nousedataobj import NoUseDataObj
        DataObj = NoUseDataObj()
        
    title = DataObj.getProgressText()
        
    #use old code ( grid_t was 1d numpy array )
    grid_t = grid_t[0]
    
    #determ func
    func = TypeToFunc(ktype)
    
    #create grid_trend
    grid_trend = grid_z.copy()
    
    DataObj.setProgressRange(0,len(grid_s))
    DataObj.setCurrentProgress(0, title + "\n- By Kernel Smoothing...")
    for index_s in range(grid_s.shape[0]):
        if not DataObj.wasProgressCanceled():  
            for index_t in range(grid_t.shape[0]):
                if numpy.isnan(grid_z[index_s][index_t]):
                    pass
                else:
                    ds = numpy.sqrt(((grid_s - grid_s[index_s])**2).sum(axis=1))
                    dt = numpy.abs(grid_t - grid_t[index_t])
                    
                    index_ss = numpy.where(ds<=bs)
                    index_tt = numpy.where(dt<=bt)
                    selected_ds = ds[index_ss]
                    selected_dt = dt[index_tt]
                    
                    selected_grid_z = grid_z[numpy.ix_(index_ss[0],index_tt[0])]
                              
                    ds_nomal = (numpy.array([selected_ds]).T / bs)**2
                    dt_nomal = (selected_dt / bt)**2
                    
                    dr_matrix = ds_nomal + dt_nomal
                    kernel_w = func(dr_matrix)
                    
                    up = kernel_w * selected_grid_z
                    kernel_w[numpy.isnan(selected_grid_z)] = numpy.nan
                    down = kernel_w
                    grid_trend[index_s][index_t] = up[~numpy.isnan(up)].sum() / down[~numpy.isnan(down)].sum()
            DataObj.setCurrentProgress(index_s + 1)
        else:
            return False
        
    DataObj.setCurrentProgress(text = title)
    return grid_trend
 
def kernelsmoothing_est(grid_s, grid_t, grid_z, 
                        est_grid_s, est_grid_t,
                        bs, bt, ktype = "gau"):
        
    #determ func
    func = TypeToFunc(ktype)
    
    grid_t = grid_t[0]
    est_grid_t = est_grid_t[0]
    
    #create grid_trend
    est_grid_trend = numpy.empty((est_grid_s.shape[0],est_grid_t.shape[0]))
    est_grid_trend[:] = numpy.nan
    
    for index_s in range(len(est_grid_s)):
        for index_t in range(len(est_grid_t)):
            ds = numpy.sqrt(((grid_s - est_grid_s[index_s])**2).sum(axis=1))
            dt = numpy.abs(grid_t - est_grid_t[index_t])
            
            index_ss = numpy.where(ds<=bs)
            index_tt = numpy.where(dt<=bt)
            selected_ds = ds[index_ss]
            selected_dt = dt[index_tt]
            selected_grid_z = grid_z[numpy.ix_(index_ss[0],index_tt[0])]
                      
            ds_nomal = (numpy.array([selected_ds]).T / bs)**2
            dt_nomal = (selected_dt / bt)**2
            
            dr_matrix = ds_nomal + dt_nomal
            kernel_w = func(dr_matrix)
            
            up = kernel_w * selected_grid_z
            kernel_w[numpy.isnan(selected_grid_z)] = numpy.nan
            down = kernel_w
            est_grid_trend[index_s][index_t] = up[~numpy.isnan(up)].sum() / down[~numpy.isnan(down)].sum()
    return est_grid_trend

#def kernelsmoothing_cv(grid_s,grid_t,grid_z,bs,bt,ktype = "gaussian",sample = None):
#    #determ func
#    func = TypeToFunc(ktype)
#    
#    #create grid_trend
#    grid_trend = grid_z.copy()
#    
##    #sample list 
##    try:
##        sample_index_list = random.sample([[i,j] for i in xrange(len(grid_s)) for j in xrange(len(grid_t)) if ~numpy.isnan(grid_z[i][j])],sample)
##    except ValueError:
##        sample_index_list = [[i,j] for i in xrange(len(grid_s)) for j in xrange(len(grid_t)) if ~numpy.isnan(grid_z[i][j])]
#
#    
##    #get true sample number
##    samplenumber = len(sample_index_list)
##    
##    for (index_s,index_t) in sample_index_list:
#    for index_s in xrange(len(grid_s)):
#        for index_t in xrange(len(grid_t)):
#            if numpy.isnan(grid_z[index_s][index_t]):
#                pass
#            else:
#                ds = numpy.sqrt(((grid_s - grid_s[index_s])**2).sum(axis=1))
#                dt = numpy.abs(grid_t - grid_t[index_t])
#                
#                index_ss = numpy.where(ds<=bs)
#                index_tt = numpy.where(dt<=bt)
#                selected_ds = ds[index_ss]
#                selected_dt = dt[index_tt]
#                selected_grid_z = grid_z[numpy.ix_(index_ss[0],index_tt[0])]
#                          
#                ds_nomal = (numpy.array([selected_ds]).T / bs)**2
#                dt_nomal = (selected_dt / bt)**2
#                
#                dr_matrix = ds_nomal + dt_nomal
#                kernel_w = func(dr_matrix)
#                
#                up = kernel_w * selected_grid_z
#                kernel_w[numpy.isnan(selected_grid_z)] = numpy.nan
#                down = kernel_w
#                
#                #abstract self
#                
#                grid_trend[index_s][index_t] = (up[~numpy.isnan(up)].sum() - grid_z[index_s][index_t]) / (down[~numpy.isnan(down)].sum() - 1.)
#    error = (grid_z - grid_trend )**2
#    error = error[~numpy.isnan(error)]
#    samplenumber = error.size
#    square_error = error.sum()
#    mean_square_error = square_error/samplenumber
#    return mean_square_error
                 
def TypeToFunc(kerneltype):
    dictionary={"gau":gaussian,
                "gaussian":gaussian,
                "qua":quadratic,
                "quadratic":quadratic}
    return dictionary[kerneltype]

def gaussian(dr_matrix):
    answer = numpy.exp(-3 * dr_matrix)
    answer[(dr_matrix > 1)] = 0.0
    return answer

def quadratic(dr_matrix):
    answer = 1 - dr_matrix
    answer[dr_matrix < 0] = 0.0
    return answer

if __name__ == "__main__":
    import time
    func=gaussian

    grid_z = numpy.array([[1,numpy.nan,3.,4,5],
                          [5,6,1,7,8],
                          [1,numpy.nan,4,2,5],
                          [5,2,6,3,1.]])
    #grid_trend = grid_z.copy()
    grid_s=numpy.array([[1,3.],[1,8],[3,2],[4,1]])
    grid_t=numpy.array([[1,3,5,7,9.]])
    bs=8
    bt=2
    
    print (kernelsmoothing(grid_s,grid_t,grid_z,bs,bt,ktype = "gaussian"))
    
    print (kernelsmoothing_est(grid_s, grid_t, grid_z, 
                        est_grid_s = grid_s, est_grid_t = grid_t,
                        bs = bs, bt = bt, ktype = "gau"))