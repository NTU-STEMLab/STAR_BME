'''
Created on 2012/7/6

@author: KSJ
'''
import os
import numpy

def rotate( coord_set, angle , direction = 'E', clock = 'counter' ): #rotate axis
    '''
    coord_set: numpy array [ [x1,y1],[x2,y2] ]
    angle: degree from x axis, counterclockwise
    direction: from which direction 'N' or 'W' or 'S' or 'E'
    clock: 'counterclockwise' or 'clockwise'
    '''
    #convert to 'counterclock' & 'E'
    if clock.lower().startswith('co'): #counterclockwsie
        pass
    elif clock.lower().startswith('cl'): #clockwise
        angle = -angle
    else:
        raise ValueError('clockwise should be "clockwise" or "counterclockwise"')
    
    angle_dict = { 'e': 0.,'n':90., 'w': 180., 's':270. }
    if direction.lower() in angle_dict:
        angle += angle_dict[direction.lower()]
    else:
        raise ValueError('direction should be one of "NWSE"')
    
    sin_angle = numpy.sin( angle / 180. * numpy.pi )
    cos_angle = numpy.cos( angle / 180. * numpy.pi )
    rotate_matrix = numpy.array( [ [ cos_angle,-sin_angle ],
                                   [ sin_angle, cos_angle ] ] )
    
    rotated_coord_set = coord_set.dot( rotate_matrix )
    return rotated_coord_set

def stretch( coord_set, multiple, axis = "x" ):
    '''
    coord_set: numpy array [ [x1,y1],[x2,y2] ]
    multiple: multiple nX along axis
    axis: "x" or 0 for x axis, "y" or 1 for y axis
    '''
    axis_dic = {"x":0, "y":1, 0:0, 1:1}
    axis = axis_dic[axis]
    coord_set[:,axis:axis+1] = coord_set[:,axis:axis+1] * multiple
    return coord_set

def covmap( coord_set, value_set ):
    def diff_matrix( mat ):
        return mat - mat.T
    dx_mat = diff_matrix( coord_set[ :, 0:1 ] )
    dy_mat = diff_matrix( coord_set[ :, 1:2 ] )
    dv_mat = value_set * value_set.T
    
    return dx_mat, dy_mat, dv_mat
    


if __name__ == '__main__':

    #print os.getcwd()
    x,y,t,z = numpy.loadtxt(r'.\..\testsource\HardData.csv',delimiter = ',',skiprows = 1,unpack = True)
    x,y,t,z = map(lambda t: numpy.array(t,ndmin=2).T,(x,y,t,z))

    #convert data to s,t,z type
    from rawdata2griddata import rawdata2griddata, rawdata2griddataforcoor
    from nousedataobj import NoUseDataObj
    DataObj = NoUseDataObj()
    grid_s, grid_t, grid_z = rawdata2griddata(x, y, t, z,DataObj)


    #change value to residual to calculate
    import stmean
    grid_trend = stmean.stmean( grid_s, grid_t, grid_z, DataObj )
    grid_residual = grid_z - grid_trend
    grid_z = grid_residual  # make it fit code below
    
    
    #sum along T without nan for just spatial test
    for idx,z_i in enumerate(grid_z):
        grid_z[idx] = z_i[numpy.where(~numpy.isnan(z_i))].mean()
    grid_z = grid_z[:,0:1]

    #avg cov
    s_x = grid_s[:,0:1]
    s_y = grid_s[:,1:2]
    
    dx = s_x - s_x.T
    dy = s_y - s_y.T
    
    dr = numpy.sqrt( dx**2 + dy**2 )
    da =  numpy.arctan( dy / dx )
    da[ dx < 0 ] += numpy.pi # get real angle (I II QUAT
    dv = grid_z * grid_z.T
    
    rt_ang = 30/180.*numpy.pi
    b_ratio = 1
    dr_chg = numpy.sqrt( ( numpy.cos( rt_ang ) * dx + numpy.sin( rt_ang )*dy )**2 +\
             ( b_ratio * ( numpy.cos( rt_ang ) * dy - numpy.sin( rt_ang )*dx ) )**2 )
    print(zip(dr_chg , dr))
    input()
    #ESTIMATE
    #####def objv
    from bobyqa import bobyqa
    from stcovfit import fitcovariance
    
    def objf( cst, models):
        c = cst[0::3]
        s = cst[1::3]
        t = cst[2::3]
        for index,(i,j,k) in enumerate(zip(c,s,t)):
            models[index][0] = i
            models[index][2] = j
            models[index][4] = k
            
#            return fitcovariance(models,self.cov_s,
#                                 self.cov_t,self.cov_v,self.cov_n)

        return fitcovariance(models,*self.stvn)
    
    
    bobyqa.bobyqa( )


####    #set avg cov limit
####    lagA = numpy.linspace( 11.25, 180-11.25, 8 ) /180. * numpy.pi
####    rangeA = numpy.linspace( 11.25, 11.25, 8 ) /180. * numpy.pi
####    lagR = numpy.linspace( 0 , 25000., 6)
####    rangeR = numpy.linspace( 2500., 2500., 6)
####    rangeR[0] = 0.
####
####    
####    import stcov
####    lagCOVv, lagCOVn = stcov.cov_avg_nd( [dr,da], grid_z, [ lagR, lagA ], [ rangeR, rangeA ] )
####    #get lagCOORD
####    lagAA,lagRR = numpy.meshgrid(lagA,lagR)
    
    

    
    
    
######  TEST FOR CALCULATE 2D LAG
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
####    dv = grid_z * grid_z.T
####    dm1 = grid_z * numpy.ones( grid_z.T.shape )
####    dm2 = grid_z.T * numpy.ones( grid_z.shape )
####    
####    for idx_a, ( limit_a, range_a ) in enumerate( zip( lagA, rangeA ) ):
####        select_bool_matrix_a =  ( da > limit_a - range_a ) & ( da <= limit_a + range_a )
####        if select_bool_matrix_a.any(): #has match
####            for idx_r, ( limit_r, range_r ) in enumerate( zip( lagR, rangeR ) ):
####                select_bool_matrix_r =( dr > limit_r - range_r ) & ( dr <= limit_r + range_r )
####                if select_bool_matrix_r.any(): #has match
####                    select_bool_matrix = ( select_bool_matrix_a ) & ( select_bool_matrix_r )
####                    if select_bool_matrix.any() and numpy.sum( select_bool_matrix ) > 1: # has both match ( angle and range )
####                        #calculate
####                        select_dv = dv[ select_bool_matrix ]
####                        select_dm1 = dm1[ select_bool_matrix ]
####                        select_dm2 = dm2[ select_bool_matrix ]
####                        
####                        lagCOVv[idx_r][idx_a] = select_dv.sum()
####                        lagCOVm1[idx_r][idx_a] = select_dm1.sum()
####                        lagCOVm2[idx_r][idx_a] = select_dm2.sum()
####                        lagCOVn[idx_r][idx_a] =  select_dv.size
####                    else:
####                        print "NOT FOUND"
####                        continue
####                else:
####                    continue
####        else:
####            continue
####    
####    lagCOVv /= lagCOVn
####    lagCOVm1 /= lagCOVn
####    lagCOVm2 /= lagCOVn
####    lagCOVv -= lagCOVm1*lagCOVm2

## OLD METHOD MAYBE FAST BUT HARD TO MENTAIN   
#    #get deltaX, deltaY, multiZ
#    from diffarray import diffarray,multiarray
#    s_diff_i_left, s_diff_i_right, s_diff_v = diffarray( grid_s, include = False )
#    #find their COV
#    s_diff_i_left2, s_diff_i_right2, s_diff_cov = multiarray(grid_z, include = False )
#    
#    delta_x, delta_y = s_diff_v[:,0], s_diff_v[:,1] #this will convert it to 1d row
#    delta_z = s_diff_cov[:,0]
#    
#    
#    #average data
#    #get deltaAngle
#    delta_angle = numpy.arctan( delta_y / delta_x )
#    #convert 4th quadrant to 2nd quadrant
#    delta_angle[ (delta_angle > -0.5*numpy.pi ) & (delta_angle <= 0.*numpy.pi ) ] += numpy.pi
#    print delta_angle
#    #set range
#    lag_angle = numpy.linspace( 22.5, 180-22.5, 8 )
#    range_angle = numpy.linspace( 22.5, 22.5, 8 )
#    lag_spatial = numpy.linspace( 0 , 15000., 8)
#    range_spatial = numpy.linspace( 1875.0, 1875, 8)

    #plot covmap
    import matplotlib.pyplot as plt
    numpy.fill_diagonal( dx, numpy.nan )
    numpy.fill_diagonal( dy, numpy.nan )
    numpy.fill_diagonal( dv, numpy.nan )
    numpy.fill_diagonal( da, numpy.nan )
    dx, dy, dv, da = map( lambda a: a[~numpy.isnan(a)], ( dx, dy, dv, da ) )
    plt.subplot(131)
    plt.plot( dx, dy, "ko")
    plt.tricontour( dx.flatten(), dy.flatten(), dv.flatten(), 15, linewidths=0.5, colors='k' )
    plt.tricontourf( dx.flatten(), dy.flatten(), dv.flatten(), 15, cmap=plt.cm.jet )
    plt.colorbar()
    plt.axis('scaled')
    
    plt.subplot( 132, polar = True )
    plt.plot( da, numpy.sqrt( dx**2 + dy**2 ), 'bo' )
    plt.axis('scaled')
    
##    plt.subplot( 133, polar = True )
##    plt.plot( da, numpy.sqrt( dx**2 + dy**2 ), 'bo' )
##    dw = lagA[1] - lagA[0]
##    dr = lagR[1] - lagR[0]
##    
##    for idx,(r_i,rr_i) in enumerate(zip(lagR,rangeR)):
##        GGG = lagCOVv[~numpy.isnan(lagCOVv)]
##        GG=lagCOVv[idx]
##        GG = numpy.ma.masked_array( GG, numpy.isnan(GG))
##        plt.bar(left = lagA-rangeA,
##                bottom =  (r_i-rr_i) * numpy.ones( lagA.shape ),
##                width = dw * numpy.ones( lagA.shape ),
##                height = dr * numpy.ones( lagA.shape ),
##                color = plt.cm.jet( GG - GGG.min() / (GGG.max() - GGG.min()) ) )
##
###    lagCOVvv = numpy.ma.masked_array(lagCOVv, mask = numpy.isnan( lagCOVv ) )
###    plt.pcolormesh( lagAA, lagRR, lagCOVvv )
###    plt.colorbar()
##    plt.axis('scaled')
    plt.ylim( 0, 25000 )
#    from matplotlib.colorbar import ColorbarBase
#    from matplotlib.colors import Normalize
#    ColorbarBase(plt.gcf().colorbar().axis(), cmap=plt.cm.jet,
#    norm=Normalize(vmin=GG.min(), vmax=GG.max()))
    plt.show()

    
    
    '''
    #get deltaS = (X^2 + Y^2) ^ 1/2
    s_diff_v = numpy.sqrt( s_diff_v[:,0]**2 + s_diff_v[:,1]**2 )
##    t_diff_i_left, t_diff_i_right, t_diff_v = diffarray( grid_t )
##    t_diff_v = numpy.abs( t_diff_v )

    
##    ans = rotate( numpy.hstack((x,y)),30)
    ans = rotate( numpy.hstack((grid_s[:,0:1],grid_s[:,1:2])),30)
#    print ans
#    print stretch(ans,3,1)
    o_x_line = numpy.linspace(0,10**7,2)
    o_y_line = numpy.linspace(0,0,2)
    o_x_line, o_y_line = map(lambda t: numpy.array(t,ndmin=2).T,(o_x_line,o_y_line))
    ans2 = rotate( numpy.hstack((o_x_line,o_y_line)),-30)
    '''
