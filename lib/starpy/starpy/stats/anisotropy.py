# -*- coding: utf-8 -*-
'''
Created on 2012/7/6

@author: KSJ
'''
# import os
import numpy
import matplotlib.pyplot as plt

from .stcov import stcov
from ..stest import stmean
#from starpy.stats.stcov import stcov
#from starpy.stest import stmean

def polarstcovmap(cMS,tME,Zst,rLag,rLagTol,tLag=None,tLagTol=None,angLag=None,angTol=None,
                  plot=True):
  '''
  Plot polar map for empirical spatial covariance of space-time data
  SYNTAX :

  polarstcovmap(cMS,tME,Zst,rLag,rLagTol,tLag=None,tLagTol=None,angLag=None
                ,angTol=None,plot=True)

  INPUT : 

  cMS       ns by d       
  tME       1 by nt       
  Zst       ns by nt      Data
  rLag      nls by 1      1D array of vector with the r lags    
  rLagTol   nls by 1      1D array of vector with the tolerance for the r lags
  angLag    na by 1       1D array of angles to be evaluated (in radian). The 
                          two ends should be [-pi/2,pi/2) 
                          The default is [-pi/2:30/180*pi:pi/2)
  angTol    na by 1       1D array of angle tolerance around the each of angles
                          the default is the array of 15/180*pi
  plot      bool          True for plot the polar covariance. Default is True                       
                         
  OUTPUT:
  CC        list          a list of na directional empirical covariances. Each 
                          has shape of nls by nlt
  CCn       list          a list of na directional empirical covariances. Each 
                          has shape of nls by nlt
  lagr      nls by nlt    meshed spatial distances
  lagt      nls by nlt    meshed temporal lags                    
  angLag    na by 1       1D array of the diretions being evaluated      

  Remark: 
  For the purposes of plotting polar empirical covariance,               
  '''
  
  if angLag is None:
    ang_inic=-numpy.pi/2
    ang_step=30/180.*numpy.pi
    angLag=numpy.arange(ang_inic,numpy.pi/2,ang_step)
    angTol=numpy.ones(angLag.shape)*ang_step/2
  
  CC=[]
  CCn=[]
  CC4plot=numpy.empty([rLag.size,0])   
  for i,ang in enumerate(angLag):
    if tLag is not None:
      C,Cn,lagr,lagt=stcov(cMS,tME,Zst,rLag,rLagTol,tLag,tLagTol,ang=ang,angtol=angTol[i])
    else:
      C,Cn,lagr,lagt=stcov(cMS,tME,Zst,rLag,rLagTol,ang=ang,angtol=angTol[i])
    CC.append(C)
    CCn.append(Cn)
    CC4plot=numpy.hstack((CC4plot,C[:,0:1]))       
  
  if plot is True:
    idx=numpy.where(numpy.isnan(CC4plot))
    if idx[0].size>0:  
      CC3=numpy.hstack((CC4plot,numpy.hstack((CC4plot,CC4plot))))
      angLag3=numpy.hstack((angLag-numpy.pi,numpy.hstack((angLag,angLag+numpy.pi)))) 
      try:
        CC1=stmean.stmeaninterp(lagr,angLag3,CC3,lagr,angLag,method='linear')
      except:  
        CC1=stmean.stmeaninterp(lagr,angLag3,CC3,lagr,angLag,method='nearest')
      for k in range(int(idx[0].size)):
        CC4plot[idx[0][k],idx[1][k]]=CC1[idx[0][k],idx[1][k]]
      
    angLag4plot=numpy.hstack((angLag,angLag+numpy.pi))
    CC4plot=numpy.hstack((CC4plot,CC4plot))
    angLag4plot=numpy.append(angLag4plot,angLag4plot[-1]+angTol[0]*2)
    CC4plot=numpy.hstack((CC4plot,CC4plot[:,0:1]))
    
    angLag4plot=angLag4plot-angTol[0]
    theta,radius = numpy.meshgrid(angLag4plot, rLag) #rectangular plot of polar data
    fig=plt.figure()
    ax = fig.add_subplot(111,polar=True)
    im=ax.pcolor(theta, radius, CC4plot,cmap='hot_r')  
    plt.colorbar(im)  
    plt.show()  
  
  return CC,CCn,lagr,lagt,angLag

          
def iso2aniso(ciso,angle,ratio):
  '''
% iso2aniso                 - convert isotropic to anisotropic coordinates 
%
% Do the transformation which is reciprocal to the transformation made by
% the aniso2iso.m function, so that applying successively both transformation
% has no effect on the coordinates. The function maps a set of coordinates
% in an isotropic space into a set of coordinates in an anisotropic one. 
%
% SYNTAX :
%
% [c]=iso2aniso(ciso,angle,ratio); 
%
% INPUT :
%
% ciso    n by d   An 2D array of coordinates for the locations in the isotropic
%                  space. A line corresponds to the vector of coordinates at a
%                  location, so that the number of columns corresponds to the
%                  dimension of the space. Only two dimensional or three dimensional
%                  space coordinates can be processed by this function.
% angle   1 by d-1 vector of angle values that characterize the anisotropy. 
%                  In a two dimensional space, angle is the trigonometric angle
%                  between the horizontal axis and the principal axis of the
%                  ellipse. In a three dimensional space, spherical coordinates
%                  are used, such that angle(1) is the horizontal trigonometric
%                  angle and angle(2) is the vertical trigonometric angle for the
%                  principal axis of the ellipsoid. All the angles are measured
%                  counterclockwise in degrees and are between -90 and 90.
% ratio   1 by d-1 vector that characterize the ratio for the length of the axes
%                  for the ellipse (in 2D) or ellipsoid (in 3D). In a two dimensional
%                  space, ratio is the length of the secondary axis of the ellipse
%                  divided by the length of the principal axis, so that ratio in [0,1]. In a
%                  three dimensional space, ratio(1) is the length of the second
%                  axis of the ellipsoid divided by the length of the principal axis, 
%                  whereas ratio(2) is length of the third axis of the ellipsoid
%                  divided by the length of the principal axis, so that ratio(1) and
%                  ratio(2) are both in the range of [0,1].
%
% OUTPUT :
%
% c       n by d   An 2D array of coordinates having the same size as ciso, that gives the new coordinates
%                  in the anisotropic space.
%
% NOTE :
%
% It is possible to specify an additional index vector, taking integer values from 1
% to nv. The values in index specifies which of the nv variable is known at each one
% of the corresponding coordinates. The ciso matrix of coordinates and the index vector
% are then grouped together using the MATLAB cell array notation, so that ciso={ciso,index}.
% This allows to perform the same coordinate transformation at once on a set of possibly
% different variables. The output variable c is then also a cell array that contains
% both the new matrix of coordinates and the index vector.
  '''
    
  # Determine the dimension of the space and set ratio 
  if type(ciso) is numpy.ndarray:  
    d=ciso.shape[1]
  else:
    ciso=numpy.array(ciso,ndmin=2)
    d=ciso.shape[1]
  angle=angle*2*numpy.pi/360
  angle=-angle

  # When d<2 or d>3, error

  if (d<2) or (d>3):
    print ('iso2aniso function requires coordinates in a 2D or 3D space')
    return

  # Case for d=2

  if d==2:
    R=numpy.array([[numpy.cos(angle),numpy.sin(angle)],
                   [-numpy.sin(angle),numpy.cos(angle)]])
    ciso[:,1]=ciso[:,1]*ratio
    c=ciso.dot(R.T)
    

  # Case for d=3

  if d==3:
    phi=angle[0]
    teta=angle[1]
    ratioy=ratio[0]
    ratioz=ratio[1]

    R1=numpy.array([[numpy.cos(phi),numpy.sin(phi),0],
                    [-numpy.sin(phi),numpy.cos(phi),0],
                    [0,0,1]])
    R2=numpy.array([[numpy.cos(teta),0,numpy.sin(teta)],
                    [0,1,0],
                    [-numpy.sin(teta),0,numpy.cos(teta)]])
    R=(R2.T).dot(R1.T)
    ciso[:,1]=ciso[:,1]*ratioy
    ciso[:,2]=ciso[:,2]*ratioz    
    c=ciso.dot(R)

    
  return c


def aniso2iso(c,angle,ratio):
  '''
% aniso2iso                 - convert anisotropic to isotropic coordinates (Jan 1,2001)
%
% Transform a set of two dimensional or three dimensional coordinates
% using rotations and dilatations of the axes, in order to map an
% anisotropic space into an isotropic one. The geometric anisotropy
% is characterized by the angle(s) of the principal axis of the ellipse
% (in 2D) or ellipsoid (in 3D), and by the ratio(s) of the principal axis
% length by the other axes lengths. Using this function, an ellipse
% (ellipsoid) is thus mapped into a circle (sphere) having as radius the
% length of the principal axis. The transformation consist in a rotation
% of the axes followed by a dilatation. 
% 
% SYNTAX :
%
% [ciso]=aniso2iso(c,angle,ratio); 
%
% INPUT :
%
% c       n by d   matrix of coordinates for the locations in the anisotropic
%                  space. A line corresponds to the vector of coordinates at a
%                  location, so that the number of columns corresponds to the
%                  dimension of the space. Only two dimensional or three dimensional
%                  space coordinates can be processed by this function.
% angle   1 by d-1 vector of angle values that characterize the anisotropy. 
%                  In a two dimensional space, angle is the trigonometric angle
%                  between the horizontal axis and the principal axis of the
%                  ellipse. In a three dimensional space, spherical coordinates
%                  are used, such that angle(1) is the horizontal trigonometric
%                  angle and angle(2) is the vertical trigonometric angle for the
%                  principal axis of the ellipsoid. All the angles are measured
%                  counterclockwise in degrees and are between -90∞ and 90∞.
% ratio   1 by d-1 vector that characterize the ratio for the length of the axes
%                  for the ellipse (in 2D) or ellipsoid (in 3D). In a two dimensional
%                  space, ratio is the length of the secondary axis of the ellipse
%                  divided by the length of the principal axis, so that ratio in [0,1]. In a
%                  three dimensional space, ratio(1) is the length of the second
%                  axis of the ellipsoid divided by the length of the principal axis, 
%                  whereas ratio(2) is length of the third axis of the ellipsoid
%                  divided by the length of the principal axis, so that ratio(1) and
%                  ratio(2) are both in the range of [0,1].
%
% OUTPUT :
%
% ciso    n by d   matrix having the same size as c, that gives the new coordinates
%                  in the isotropic space.
%
% NOTE :
%
% It is possible to specify an additional index vector, taking integer values from 1
% to nv. The values in index specify which one of the nv variable is known at each one
% of the corresponding coordinates. The c matrix of coordinates and the index vector
% are then grouped together using the MATLAB cell array notation, so that c={c,index}.
% This allows to perform the same coordinate transformation at once on a set of possibly
% different variables. The output variable ciso is then also a cell array that contains
% both the new matrix of coordinates and the index vector.
  '''
  
  # Determine the dimension of the space and set angle
  if type(c) is numpy.ndarray:  
    d=c.shape[1]
  else:
    c=numpy.array(c,ndmin=2)
    d=c.shape[1]
  angle=angle*2*numpy.pi/360;

  # When d<2 or d>3, error

  if (d<2) or (d>3):
    print ('aniso2iso requires coordinates in a 2D or 3D space')
    return

  # Case for d=2

  if d==2:
    R=numpy.array([[numpy.cos(angle),numpy.sin(angle)],
                  [-numpy.sin(angle),numpy.cos(angle)]])
    ciso=c.dot(R.T)
    ciso[:,1]=ciso[:,1]*1./ratio

  # Case for d=3

  if d==3:
    phi=angle[0]
    teta=angle[1]
    ratioy=ratio[0]
    ratioz=ratio[1]
  
    R1=numpy.array([[numpy.cos(phi),numpy.sin(phi),0],
                    [-numpy.sin(phi),numpy.cos(phi),0],
                    [0,0,1]]) 
    R2=numpy.array([[numpy.cos(teta),0,numpy.sin(teta)],
                    [0,1,0],
                    [-numpy.sin(teta),0,numpy.cos(teta)]])
    R=(R1.T).dot(R2.T)
    ciso=c.dot(R)
    ciso[:,1]=ciso[:,1]*1./ratioy
    ciso[:,2]=ciso[:,2]*1./ratioz
  
  return ciso   


if __name__ == '__main__':
  
  from starpy.general.valstvgx import valstv2stg
  from starpy.general.coord2dist import coord2dist
  from starpy.graph.dataplot import colorplot
#  from starpy.stats.stcovfit import covmodelfit
  #print os.getcwd()
  path='/Users/hdragon689/MyMacDoc/packages/MyPythonModules/starpy_dev/examples/Data'
  x,y,t,z = numpy.loadtxt(path+'/HardData.csv',delimiter = ',',skiprows = 1,unpack = True)  
#  x,y,t,zh = map(lambda t: numpy.array(t,ndmin=2).T,(x,y,t,z))
  ch=numpy.asarray(zip(x,y,t))
  zh=z.reshape(z.size,1)
  #convert data to s,t,z type
  colorplot(ch,zh)
  
  grid_z, grid_s, grid_t, _ = valstv2stg(ch, z)
  
  rLagmax=coord2dist(grid_s,grid_s).max()
  rLag=numpy.linspace(0,rLagmax*2/3,6)
  rLagTol=numpy.ones(rLag.shape)*(rLag[1]-rLag[0])/2
  tLag=numpy.arange(10)
  tLagTol=numpy.ones(tLag.shape)*0.5
  angLag=numpy.linspace(-numpy.pi/2,numpy.pi/2,10)
  angTol=numpy.ones(angLag.size)*numpy.pi/40
  CC,CCn,lagr,lagt,al=polarstcovmap(grid_s,grid_t,grid_z,rLag,rLagTol,tLag,tLagTol,angLag=angLag,angTol=angTol)
  
  h=[0,3]
  hp=aniso2iso(h,angle=30,ratio=0.5)
  h2=iso2aniso(hp,angle=30,ratio=0.5)

  
#  #change value to residual to calculate
#  import starpy.stest.stmean
#  grid_trend = stmean.stmean( grid_s, grid_t, grid_z)
#  grid_residual = grid_z - grid_trend
#  grid_z = grid_residual  # make it fit code below
#    
#    
#  #sum along T without nan for just spatial test
#  for idx,z_i in enumerate(grid_z):
#    grid_z[idx] = z_i[numpy.where(~numpy.isnan(z_i))].mean()
#  grid_z = grid_z[:,0:1]
#
#  #avg cov
#  s_x = grid_s[:,0:1]
#  s_y = grid_s[:,1:2]
#    
#  dx = s_x - s_x.T
#  dy = s_y - s_y.T
#    
#  dr = numpy.sqrt( dx**2 + dy**2 )
#  da =  numpy.arctan( dy / dx )
#  da[ dx < 0 ] += numpy.pi # get real angle (I II QUAT
#  dv = grid_z * grid_z.T
#    
#  rt_ang = 30/180.*numpy.pi
#  b_ratio = 1
#  dr_chg = numpy.sqrt( ( numpy.cos( rt_ang ) * dx + numpy.sin( rt_ang )*dy )**2 +\
#    ( b_ratio * ( numpy.cos( rt_ang ) * dy - numpy.sin( rt_ang )*dx ) )**2 )
#  print zip(dr_chg , dr)
#  raw_input()
#    #ESTIMATE
#    #####def objv
#  from bobyqa import bobyqa
#  from stcovfit import fitcovariance
#    
#  def objf( cst, models):
#    c = cst[0::3]
#    s = cst[1::3]
#    t = cst[2::3]
#    for index,(i,j,k) in enumerate(zip(c,s,t)):
#      models[index][0] = i
#      models[index][2] = j
#      models[index][4] = k
#            
##            return fitcovariance(models,self.cov_s,
##                                 self.cov_t,self.cov_v,self.cov_n)
#
#    return fitcovariance(models,*self.stvn)
#    
#    
#  bobyqa.bobyqa( )


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
#  import matplotlib.pyplot as plt
#  numpy.fill_diagonal( dx, numpy.nan )
#  numpy.fill_diagonal( dy, numpy.nan )
#  numpy.fill_diagonal( dv, numpy.nan )
#  numpy.fill_diagonal( da, numpy.nan )
#  dx, dy, dv, da = map( lambda a: a[~numpy.isnan(a)], ( dx, dy, dv, da ) )
#  plt.subplot(121)
#  plt.plot( dx, dy, "ko")
#  plt.tricontour( dx.flatten(), dy.flatten(), dv.flatten(), 15, linewidths=0.5, colors='k' )
#  plt.tricontourf( dx.flatten(), dy.flatten(), dv.flatten(), 15, cmap=plt.cm.jet )
#  plt.colorbar()
#  plt.axis('scaled')
#    
#  plt.subplot( 122, polar = True )
#  plt.plot( da, numpy.sqrt( dx**2 + dy**2 ), 'bo' )
#  plt.axis('scaled')
#  plt.show()
    
#    plt.subplot( 133, polar = True )
#    plt.plot( da, numpy.sqrt( dx**2 + dy**2 ), 'bo' )
#    dw = lagA[1] - lagA[0]
#    dr = lagR[1] - lagR[0]
#    
#    for idx,(r_i,rr_i) in enumerate(zip(lagR,rangeR)):
#        GGG = lagCOVv[~numpy.isnan(lagCOVv)]
#        GG=lagCOVv[idx]
#        GG = numpy.ma.masked_array( GG, numpy.isnan(GG))
#        plt.bar(left = lagA-rangeA,
#                bottom =  (r_i-rr_i) * numpy.ones( lagA.shape ),
#                width = dw * numpy.ones( lagA.shape ),
#                height = dr * numpy.ones( lagA.shape ),
#                color = plt.cm.jet( GG - GGG.min() / (GGG.max() - GGG.min()) ) )
#
#    lagCOVvv = numpy.ma.masked_array(lagCOVv, mask = numpy.isnan( lagCOVv ) )
#    plt.pcolormesh( lagAA, lagRR, lagCOVvv )
#    plt.colorbar()
#    plt.axis('scaled')
#  plt.ylim( 0, 25000 )
#    from matplotlib.colorbar import ColorbarBase
#    from matplotlib.colors import Normalize
#    ColorbarBase(plt.gcf().colorbar().axis(), cmap=plt.cm.jet,
#    norm=Normalize(vmin=GG.min(), vmax=GG.max()))
#  plt.show()
#
#    
#  '''    
#
#    #get deltaS = (X^2 + Y^2) ^ 1/2
#    s_diff_v = numpy.sqrt( s_diff_v[:,0]**2 + s_diff_v[:,1]**2 )
###    t_diff_i_left, t_diff_i_right, t_diff_v = diffarray( grid_t )
###    t_diff_v = numpy.abs( t_diff_v )
#
#    
###    ans = rotate( numpy.hstack((x,y)),30)
#    ans = rotate( numpy.hstack((grid_s[:,0:1],grid_s[:,1:2])),30)
##    print ans
##    print stretch(ans,3,1)
#    o_x_line = numpy.linspace(0,10**7,2)
#    o_y_line = numpy.linspace(0,0,2)
#    o_x_line, o_y_line = map(lambda t: numpy.array(t,ndmin=2).T,(o_x_line,o_y_line))
#    ans2 = rotate( numpy.hstack((o_x_line,o_y_line)),-30)
#
#  '''

#'''
#To implement iso2aniso and aniso2iso functions for covariance modeling
#'''
#
#def rotate( coord_set, angle , direction = 'E', clock = 'counter' ): #rotate axis
#    '''
#    coord_set: numpy array [ [x1,y1],[x2,y2] ]
#    angle: degree from x axis, counterclockwise
#    direction: from which direction 'N' or 'W' or 'S' or 'E'
#    clock: 'counterclockwise' or 'clockwise'
#    '''
#    #convert to 'counterclock' & 'E'
#    if clock.lower().startswith('co'): #counterclockwsie
#        pass
#    elif clock.lower().startswith('cl'): #clockwise
#        angle = -angle
#    else:
#        raise ValueError('clockwise should be "clockwise" or "counterclockwise"')
#    
#    angle_dict = { 'e': 0.,'n':90., 'w': 180., 's':270. }
#    if angle_dict.has_key(direction.lower()):
#        angle += angle_dict[direction.lower()]
#    else:
#        raise ValueError('direction should be one of "NWSE"')
#    
#    sin_angle = numpy.sin( angle / 180. * numpy.pi )
#    cos_angle = numpy.cos( angle / 180. * numpy.pi )
#    rotate_matrix = numpy.array( [ [ cos_angle,-sin_angle ],
#                                   [ sin_angle, cos_angle ] ] )
#    
#    rotated_coord_set = coord_set.dot( rotate_matrix )
#    return rotated_coord_set
#
#def stretch( coord_set, multiple, axis = "x" ):
#    '''
#    coord_set: numpy array [ [x1,y1],[x2,y2] ]
#    multiple: multiple nX along axis
#    axis: "x" or 0 for x axis, "y" or 1 for y axis
#    '''
#    axis_dic = {"x":0, "y":1, 0:0, 1:1}
#    axis = axis_dic[axis]
#    coord_set[:,axis:axis+1] = coord_set[:,axis:axis+1] * multiple
#    return coord_set
#
#def covmap( coord_set, value_set ):
#    def diff_matrix( mat ):
#        return mat - mat.T
#    dx_mat = diff_matrix( coord_set[ :, 0:1 ] )
#    dy_mat = diff_matrix( coord_set[ :, 1:2 ] )
#    dv_mat = value_set * value_set.T
#    
#    return dx_mat, dy_mat, dv_mat  
#  
#  '''
#  '''