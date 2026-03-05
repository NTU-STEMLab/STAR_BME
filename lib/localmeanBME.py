import numpy
from .regression import regression
from .designmatrix import designmatrix

def localmeanBME( ck, ch, cs, zh, ms, vs,
                  Khh, Ksh, Kss, order ):

    nh = zh.shape[0]
    ns = ms.shape[0]
    mkest = 0
    mhest = numpy.zeros((nh, 1))
    msest = numpy.zeros((ns, 1))
    vkest = 0

    c = numpy.vstack((ch, cs))

    #add '_' b/s we won't to change vs and Kss inplace
    vs_ = numpy.tile( vs,(1,ns ) ) if len(vs) else vs
    Kss_ = Kss + numpy.diag( numpy.diag(vs_))
    K = numpy.vstack( (numpy.hstack((Khh, Ksh.T)), numpy.hstack((Ksh, Kss_)) ) )
    z = numpy.vstack((zh, ms))
    
    best, Vbest, mm, index = regression(c, z, order, K)

    if mm.size > 0:
        mhest = mm[:nh,0:1]
        msest = mm[nh:,0:1]
    else:
        pass
        #mhest[:] = 0.0 #numpy.array([])
        #msest[:] = 0.0 #numpy.array([])

    x, index = designmatrix(ck, order)
    if x.size > 0:
        mkest = ( x.dot(best) )[0][0]
        vkest = ( x.dot(Vbest).dot(x.T) )[0][0]

    return mkest , mhest, msest, vkest
