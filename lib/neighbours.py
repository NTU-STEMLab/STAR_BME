# -*- coding:utf-8 -*-
import numpy
from .coord2dist import coord2dist

def neighbours( c_one, c, z, nmax, dmax ):
    '''
    input
    c_one: 1 by nd
        nd can be:
            1 for space or time,
            2 for space,
            3 for space-time
    c: n by nd
    z: n by ??
    nmax: int
    dmax: 1 by rd float 
        rd can be:
            1 for space or time
            3 for space-time
    return
    c_nebr, z_nebr, d_nebr, n_nebr, idx_nebr
    '''

    empty_result = [ numpy.array([]).reshape( ( 0, c_one.shape[1] ) ),
                     numpy.array([]).reshape( ( 0, 1 ) ),
                     numpy.array([]).reshape( ( 0, 1 ) ),
                     0,
                     numpy.array([]).reshape( ( 0, 1 ) ) ]

    isST = 1 if len(dmax) == 3 else 0

    if c.size == 0:
        # print 'no data'
        return empty_result

    if nmax == 0:
        # print 'nmax is 0'
        return empty_result

    if isST == 0: #
        #get distance of space (only)
        d_xy = coord2dist( c, c_one )
        index_s = numpy.where( d_xy <= dmax[0][0] )
        if len(index_s[0]) == 0:
            # print "noneighbor"
            return empty_result
        elif len( index_s[0] ) <= nmax:
            c_nebr = c[index_s[0],:]
            z_nebr = z[index_s[0],:]
            d_nebr = d_xy[index_s[0],:]
            n_nebr = len( index_s[0] )
            idx_nebr = index_s[0].reshape( ( -1, 1 ) )
            return c_nebr, z_nebr, d_nebr, n_nebr, idx_nebr
        elif len( index_s[0] ) > nmax:
            d_nebr = d_xy[index_s[0],:]
            index_s = ( numpy.sort( d_nebr[:,0].argsort()[:nmax] ), 0 ) #dummy 0 for consistence
            c_nebr = c[index_s[0],:]
            z_nebr = z[index_s[0],:]
            d_nebr = d_xy[index_s[0],:]
            n_nebr = len( index_s[0] )
            idx_nebr = index_s[0].reshape( ( -1, 1 ) )
            return c_nebr, z_nebr, d_nebr, n_nebr, idx_nebr

    elif isST == 1:#space time case

        #get distance of time
        d_t = numpy.abs( c[:,2:3] - c_one[:,2:3] )
        index_t = numpy.where( d_t <= dmax[0][1] )
        if len(index_t[0]) == 0:
            # print "noneighbor"
            return empty_result

        #get distance of space which already match time
        d_xy = coord2dist( c[index_t[0],0:2], c_one[:,0:2] )
        index_s = numpy.where( d_xy <= dmax[0][0] )
        if len(index_s[0]) == 0:
            # print "noneighbor"
            return empty_result
        
        #calculate all distance which matched perfectly
        d_r = d_xy[index_s[0],0:1] + dmax[0][2] * d_t[ index_t[0] [ index_s[0] ],0:1]
        index_r = numpy.where( d_r <= dmax[0][0] + dmax[0][2] * dmax[0][1] )
        
        if len( index_r[0] ) == 0:
            n_nebr = 0
            return empty_result
        elif len( index_r[0] ) <= nmax:
            c_nebr = c[index_t[0],:][index_s[0],:][index_r[0],:]
            z_nebr = z[index_t[0],:][index_s[0],:][index_r[0],:]
            d_nebr = d_r[index_r[0],:]
            n_nebr = len( index_r[0] )
            idx_nebr = index_t[0].reshape( ( -1, 1 ) )[index_s[0][index_r[0]],:]
            return c_nebr, z_nebr, d_nebr, n_nebr, idx_nebr
        elif len( index_r[0] ) > nmax:
            d_nebr = d_r[index_r[0],:]
            index_r = ( numpy.sort( d_nebr[:,0].argsort()[:nmax] ), 0 ) #dummy 0 for consistence
            c_nebr = c[index_t[0],:][index_s[0],:][index_r[0],:]
            z_nebr = z[index_t[0],:][index_s[0],:][index_r[0],:]
            d_nebr = d_r[index_r[0],:]
            n_nebr = len( index_r[0] )
            idx_nebr = index_t[0].reshape( ( -1, 1 ) )[index_s[0][index_r[0]],:]
            return c_nebr, z_nebr, d_nebr, n_nebr, idx_nebr
   
if __name__ == "__main__":
#    c0 = numpy.array([[0,0.,0]])
#    c= numpy.array([[1,1,1],[0,0,1],[1,0,1],[0,1,1],[1,1,0],[1,0,0],
#                    [2,1,1],[2,0,0],[0,0,2],[0,2,0],[2,2,2],[0,1,2]])
#    z= numpy.array([1,2,3,4,5,6,7,8,9,10,11,12],ndmin=2).T

#test nd = 3
    import time
    all = numpy.loadtxt('test.csv', delimiter =',')
    c = all[:,0:3]
    z = all[:,3:]
    
    c0 = numpy.array([[304498.398,2798410.25,730000]])
    
    nmax = 15
    ar = 304371.15 * 5
    at = 3.85*5
    dmax = numpy.array([[ ar, at, ar/at]])
    aaa = time.time()
    result = neighbours(c0,c,z,nmax,dmax)
    print (time.time() - aaa)
    for i in result:
        print (i)

#test nd = 2
#     import time
#     all = numpy.loadtxt('test.csv', delimiter =',')
#     c = all[:,0:2]
#     z = all[:,3:]
    
#     c0 = numpy.array([[304498.398,2798410.25]])
    
#     nmax = 15
#     ar = 304371.15 * 5
#     dmax = numpy.array([[ar]])
#     aaa = time.time()
#     result = neighbours(c0,c,z,nmax,dmax)
#     print time.time() - aaa
#     for i in result:
#         print i

#test nd = 1
    # import time
    # all = numpy.loadtxt('test.csv', delimiter =',')
    # c = all[:,0:1]
    # z = all[:,3:]
    
    # c0 = numpy.array([[304498.398]])
    
    # nmax = 15
    # ar = 304371.15 * 5
    # dmax = numpy.array([[ar]])
    # aaa = time.time()
    # result = neighbours(c0,c,z,nmax,dmax)
    # print time.time() - aaa
    # for i in result:
    #     print i