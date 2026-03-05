import numpy
import scipy.stats
import scipy.integrate
import time

HAS_CUBATURE = True
try:
    from cubature import cubature
except ImportError:
    HAS_CUBATURE = False

def integrate_function( *args ): # 8 args

    x = args[:-8]
    softpdftype, nl, limi, probdens, mvnpdf, asMom, bsMom, pMom =  args[-8:]

    res = 1.

    res *= fs( x, softpdftype, nl, limi, probdens )
    if res == 0:
        return 0.
    else:
        res *= middle( x, asMom, bsMom, pMom )
        res *= mvnpdf( x )
    return res

def integrate_function_cubature( x_array, *args ):

    softpdftype, nl, limi, probdens, mvnpdf, asMom, bsMom, pMom =  args
    res = 1.

    res *= fs( x_array, softpdftype, nl, limi, probdens )
    if res == 0:
        return numpy.array([0.]) #instead of use res, 0. make sure array type
    else:
        res *= middle( x_array, asMom, bsMom, pMom )
        res *= mvnpdf( x_array )

    return numpy.array([res])

def fs( x, softpdftype, nl, limi, probdens ):

    res = 1.
    for x_i, nl_i, limi_i, probdens_i in zip(x, nl, limi, probdens):
        y_i = numpy.interp( x_i, limi_i[:int(nl_i[0])], probdens_i[:int(nl_i[0])],
                            left = 0., right = 0.)
        if y_i == 0:
            return 0.
        else:
            res *= y_i
    return res

def middle( x, As, Bs, P ):

    return ((As.T.dot(numpy.array(x,ndmin=2).T) + Bs) ** P)[0][0]


def norm_pdf_multivariate(x, mu, sigma):
    size = len(x)
    if size == len(mu) and (size, size) == sigma.shape:
        det = numpy.linalg.det(sigma)
        if det == 0:
            raise NameError("The covariance matrix can't be singular")

        norm_const = 1.0 / \
            (numpy.power((2 * numpy.pi), float(size) / 2)
             * numpy.power(det, 1.0 / 2))
        x_mu = numpy.array(x - mu, ndmin = 2)
        inv = numpy.linalg.inv(sigma)
        result = numpy.power(numpy.e, -0.5 * numpy.dot(numpy.dot(x_mu,inv),x_mu.T) )
        return (norm_const * result)[0][0]
    else:
        raise NameError("The dimensions of the input don't match")


def pyAllMoments(softpdftype, nl, limi, probdens,
                 meanMat, covMat, nMom, As, Bs, P,
                 absErr, relErr, maxEval):
    nd = nl.shape[0]
    if nd <= 3:
        adap = 'p'
    else:
        adap = 'h'
    ranges = []
    for nl_i, limi_i, in zip(nl, limi):
        ranges.append( (limi_i[0], limi_i[int(nl_i[0])-1]) )

    ranges = numpy.array(ranges)
    xmin = ranges[:,0].copy()
    xmax = ranges[:,1].copy()

    try:
        mvnpdf = scipy.stats.multivariate_normal( meanMat.T[0], covMat ).pdf
    except AttributeError:
        mvnpdf = lambda x: norm_pdf_multivariate(x, mu = meanMat.T[0], sigma = covMat)

    value = []
    error = []
    finfo = []

    for i in range( nMom ):

        asMom = As[:,i:i+1]
        bsMom = Bs[0][i]
        pMom = P[0][i]

        if HAS_CUBATURE:
            #v,e = cubature(nd, integrate_function_cubature,
            #               ranges[:,0].copy(),ranges[:,1].copy(),adaptive = 'h')
            #!!use ranges[:,0] will got a bug...
            v, e = cubature( ndim = nd, func = integrate_function_cubature,
                             xmin = xmin, xmax = xmax,
                             args = ( softpdftype, nl, limi, probdens, 
                                       mvnpdf, asMom, bsMom, pMom ),
                             adaptive = adap,
                             abserr = absErr,
                             relerr = relErr,
                             maxEval = maxEval,
                             fdim=1 )
            v = v[0]
            e = e[0]
        else:
            v,e = scipy.integrate.nquad( integrate_function , ranges,
                                         args=( softpdftype, nl, limi, probdens, 
                                                mvnpdf, asMom, bsMom, pMom ) ,
                                         opts = [{'limit' : 10,
                                                  'epsabs' : absErr,
                                                  'epsrel' : relErr}]*nd )

        value.append(v)
        error.append(e)
        finfo.append(numpy.nan)
    value, error, finfo = map( lambda x: numpy.array(x), (value, error, finfo) )
    return value, error, finfo

if __name__ == '__main__':
    
    #**test pyAllMoment**
    softpdftype = 2
    nl = numpy.array([[4],
       [3],
       [3]])
    limi = numpy.array([[ 0.01,  0.03,  0.2 ,  1.  ],
       [ 0.01,  0.09,  0.9 ,   numpy.nan],
       [ 0.02,  0.1 ,  1.1 ,   numpy.nan]])
    probdens = numpy.array([[ 0.        ,  1.72413793,  1.72413793,  0.        ],
       [ 0.        ,  2.24719101,  0.        ,         numpy.nan],
       [ 0.        ,  1.85185185,  0.        ,         numpy.nan]])
    meanMat = numpy.array([[ 0.34726041],
       [ 1.06617265],
       [ 0.74422407]])
    covMat = numpy.array([[ 0.98539833,  0.12142031,  0.30809047],
       [ 0.12142031,  0.44104065,  0.2722152 ],
       [ 0.30809047,  0.2722152 ,  0.75328421]])
    nMom=2
    As = numpy.array([[ 0.        ,  0.20520445],
       [ 0.        ,  0.08117701],
       [ 0.        ,  0.62566278]])
    Bs = numpy.array([[ 1.        ,  0.03398353]])
    P = numpy.array([[ 1.,  1.]])

    absErr = 0
    relErr = 0.02
    maxEval = 1000000
    sss = time.time()
    v,e,f = pyAllMoments( softpdftype, nl, limi, probdens,
                          meanMat, covMat, nMom, As, Bs, P,
                          absErr, relErr, maxEval )
    print ('Time Cost:', time.time() - sss)
    print (v)
    print (e)
    print (f)

    # #**Test cubature integrate function**
    # softpdftype = 2
    # nl = numpy.array([[4],
    #    [3],
    #    [3]])
    # limi = numpy.array([[ 0.01,  0.03,  0.2 ,  1.  ],
    #    [ 0.01,  0.09,  0.9 ,   numpy.nan],
    #    [ 0.02,  0.1 ,  1.1 ,   numpy.nan]])
    # probdens = numpy.array([[ 0.        ,  1.72413793,  1.72413793,  0.        ],
    #    [ 0.        ,  2.24719101,  0.        ,         numpy.nan],
    #    [ 0.        ,  1.85185185,  0.        ,         numpy.nan]])
    # meanMat = numpy.array([[ 0.34726041],
    #    [ 1.06617265],
    #    [ 0.74422407]])
    # covMat = numpy.array([[ 0.98539833,  0.12142031,  0.30809047],
    #    [ 0.12142031,  0.44104065,  0.2722152 ],
    #    [ 0.30809047,  0.2722152 ,  0.75328421]])
    # mvnpdf = scipy.stats.multivariate_normal( meanMat.T[0], covMat ).pdf

    # asMom = numpy.array([[ 0.],
    #    [ 0.],
    #    [ 0.]])

    # bsMom = 1.0
    # pMom = 1.0
    # args = (softpdftype, nl, limi, probdens, mvnpdf, asMom, bsMom, pMom)

    
    # for i in xrange(1000):
    #     x_array = list(numpy.random.rand(3))
    #     v1 = integrate_function_cubature( numpy.array(x_array), *args )


    #     v2 = integrate_function( *(x_array + list(args)) )
    #     if v1-v2 != 0:
    #         print v1,v2, v1-v2
    # x_array = [0.5,0.5,0.5]
    # v = integrate_function_cubature( numpy.array(x_array), *args )
    # print v

    # v = integrate_function( *(x_array + list(args)) )
    # print v
