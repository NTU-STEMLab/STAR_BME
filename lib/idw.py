'''
Created on 2012/4/11

@author: KSJ
'''

import numpy

def idw_est( x, y, z, x_est, y_est ,power = 2):
    x, y, z, x_est, y_est =\
    map( lambda x : numpy.array( x, ndmin = 2 ),
         ( x, y, z, x_est, y_est ) )
    dist_matrix = numpy.sqrt( ( x.T - x_est ) **2 + ( y.T - y_est ) **2 ) + 10**-10
    weight_matrix = 1.0 / dist_matrix ** power
    up_matrix = weight_matrix * z.T
    up_matrix = up_matrix.sum( axis = 0 ) #sum column
    down_matrix = weight_matrix.sum( axis = 0 ) #sum column
    z_est = up_matrix / down_matrix
    return z_est
    
if __name__ == "__main__":
    x = numpy.random.random(5)
    y = numpy.random.random(5)
    z = numpy.random.random(5)
    
    x_est = numpy.random.random(7)
    y_est = numpy.random.random(7)
    
    print(idw_est( x, y, z, x_est, y_est))
    from scipy.spatial.distance import cdist as scipy_cdist
    def idw_est( coord, value, coord_est, power = 2):
        coord_matrix = scipy_cdist(coord_est, coord) #coord_est by coord
        weight_matrix = numpy.reciprocal(coord_matrix**power)
        up_matrix = weight_matrix * value.T
        up_matrix = up_matrix.sum(axis=1, keepdims=True) #sum column
        down_matrix = weight_matrix.sum(axis=1, keepdims=True) #sum column
        value_est = up_matrix / down_matrix
        return value_est
    print (idw_est( numpy.vstack((x, y)).T, z.reshape((-1,1)), numpy.vstack((x_est, y_est)).T))
    pass