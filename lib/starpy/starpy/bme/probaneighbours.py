# -*- coding:utf-8 -*-
import numpy
from ..general.neighbours import neighbours


def probaneighbours( c_one, c, nl, limi, probdens, nmax, dmax ):
    '''
    just like neighbours.py
    replace z with nl, then index li and probdens
    '''

    c_nebr, z_nebr, d_nebr, n_nebr, idx_nebr = neighbours( c_one, c, nl, nmax, dmax )
    if n_nebr == 0:
        empty_result = [ numpy.array([]).reshape( (0, c_one.shape[ 1 ]) ),
                         numpy.array([]).reshape( (0, 1) ),
                         numpy.array([]).reshape( (0, limi.shape[ 1 ]) ),
                         numpy.array([]).reshape( (0, probdens.shape[ 1 ]) ),
                         numpy.array([]).reshape( (0, 1) ),
                         0,
                         numpy.array([]).reshape( (0, 1) ) ]
        return empty_result
    idx_nebr_1d = idx_nebr[:,0]
    csub = c_nebr
    nlsub = z_nebr
    limisub = limi[ idx_nebr_1d, : ]
    probdenssub = probdens[ idx_nebr_1d, : ]
    dsub = d_nebr
    nssub = n_nebr
    index = idx_nebr

    return csub, nlsub, limisub, probdenssub, dsub, nssub, index

   
if __name__ == "__main__":
    import numpy
#test nd = 3
    import time
    all = numpy.loadtxt('./stary/stest/soft_20060415_20120430.csv', delimiter =',')
    c = all[:,0:3]
    nl = all[:,3:4]
    limi = all[:,4:4+39]
    probdens = all[:,4+39:4+39+39]
    
    c0 = numpy.array([[304498.398,2798410.25,5]])
    
    nmax = 15
    ar = 304371.15 * 5
    at = 3.85*5
    dmax = numpy.array([[ ar, at, ar/at]])
    aaa = time.time()
    result = probaneighbours(c0,c,nl,limi,probdens,nmax,dmax)
    print (time.time() - aaa)
    for i in result:
        print (i)