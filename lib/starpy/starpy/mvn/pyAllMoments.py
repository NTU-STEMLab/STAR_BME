import warnings as _warnings_mod

import numpy
import scipy.stats
import scipy.integrate
import scipy.linalg
from scipy.special import erfinv
import time
import os

HAS_CUBATURE = True
try:
    from cubature import cubature
except ImportError:
    HAS_CUBATURE = False

from .qmc import qmc

def pdf2cdf(zsdata):
    '''
    Convert probapdfs into their cumulative distributions (probaCDFs)
    The format and definition of probaCDFs are very similar to those of probapdfs in 
    all probapdf types
    The only difference is that the probdens now contain 
    the cumulative probabilities
    
    Regarding to the detailed definition of zsdata
    please refer to BMEPosteriorPDF function in BMEprobaEstimation
    '''
    
    Fsdata=[None]*len(zsdata)
    Fsdata[0]=zsdata[0][:]
    Fsdata[1]=zsdata[1][:]
    Fsdata[2]=zsdata[2][:]
    Fsdata[3]=[None]*len(zsdata[1])
    for k in range(len(zsdata[1])):
        if zsdata[0][k]==2:
             #limi=zsdata[2][k]
            probdens=zsdata[3][k]
            h=Fsdata[2][k][1:]-Fsdata[2][k][:-1]
            upbot=probdens[:-1]+probdens[1:]    
            Fsdata[3][k]=numpy.hstack([0,numpy.cumsum(h*upbot/2)])
            Fsdata[3][k] = Fsdata[3][k]/float(Fsdata[3][k][zsdata[1][k][0]-1])
        elif zsdata[0][k]==1:
            #limi=zsdata[2][k]
            h=Fsdata[2][k][1:]-Fsdata[2][k][:-1]
            probdens=zsdata[3][k]
            Fsdata[3][k]=numpy.hstack([0,numpy.cumsum(h*probdens)])

    return Fsdata


def integrate_function_MomentVec_qmc( x_array, *args ):
    '''
    x_array     ndim by nsdim       ndim is the number of samples from each 
                                    integral, and nsdim is 
                                    number of multivariate integrals 
    '''
    zs, mvnpdf, As, Bs, P = args
    vectorizedCall = True
    if x_array.ndim == 1: # single point, npts=1, not a vectorized call
        x_array = x_array.reshape(1, x_array.shape[0])
        vectorizedCall = False    
    
    fdim=As.shape[1]
    #    ndim=x_array.shape[0] # number of sample combination from every intergrals
    inshape  = x_array.shape
    outshape = inshape[:-1] + (fdim,) 
    # normally input shape is same as output shape
    # but with last dimension ndim replaced by fdim
    res = numpy.ones(outshape)
    res = numpy.ones((x_array.shape[0], fdim))
    res *= fsprod(x_array, zs)
    res *= ((As.T.dot(x_array.T)).T + Bs)**P
    res *= mvnpdf(x_array).reshape(inshape[:-1] + (1,))
    if not vectorizedCall: res = res.reshape(fdim)
    if fdim == 1: return res.reshape(outshape[:-1])
    else: return res
    
    #   mvn=mvnpdf( x_array ).reshape(ndim,1)
    #    eeps=(numpy.finfo(numpy.float128).eps)**10
    #    idxres=numpy.where(res<eeps)[0]
    #    res[idxres,:]=0   
    #    idxmvn=numpy.where(mvn<eeps)[0]
    #    mvn[idxmvn,:]=0.
    #    #res *= mvn
        
    #    if (mvn).all() and (res > eeps).all():
    #        res *= mvn
    #    else:
    #        res = 0.0    
        
    #    try:
    #        res *= mvn#mvnpdf( x_array ).reshape(ndim,1)
    #        #print res
    #    except FloatingPointError, e:
    #        #print numpy.min(res), numpy.min(mvn)  
    #        print 'PyAllMoments WARNING:', e
    #    return res

def integrate_function_MomentVec_cubature( x_array, *args ):
    '''
    x_array     ndim by nsdim       ndim is the number of samples from each 
                                    integral, and nsdim is 
                                    number of multivariate integrals 
    '''
    
    res=integrate_function_MomentVec_qmc( x_array, *args ) 

    #    zs, mvnpdf, As, Bs, P = args
    #    fdim=As.shape[1]
    #    ndim=x_array.shape[0] # number of sample combination from every intergrals
    #    res=numpy.ones((x_array.shape[0], fdim))
    #    res *= fsprod(x_array, zs)
    #    res *= ((As.T.dot(x_array.T)).T + Bs)**P
    #    mvn=mvnpdf( x_array ).reshape(ndim,1)
    #    eeps=(numpy.finfo(numpy.float128).eps)**3
    #    idxres=numpy.where(res<eeps)[0]
    #    res[idxres,:]=0   
    #    idxmvn=numpy.where(mvn<eeps)[0]
    #    mvn[idxmvn,:]=0.
    #    res *= mvn
         
    if res.shape[1] == 1: #fdim == 1:
        return res.flatten()
    else:
        return res

def integrate_function_MomentVec_F_qmc( Fx_array, *args ):
    '''
    x_array     ndim by nsdim       ndim is the number of samples from each 
                                    integral, and nsdim is 
                                    number of multivariate integrals 
    '''

    Fzs, mvnpdf, As, Bs, P = args
    fdim = As.shape[1]
    ndim = Fx_array.shape[0] # number of sample combination from every intergrals

    x_array = Fsinv(Fx_array, Fzs)
    res = numpy.ones((x_array.shape[0], fdim))
    res *= ((As.T.dot(x_array.T)).T + Bs) **P
    res *= mvnpdf(x_array).reshape(ndim, 1)
    
    return res

def integrate_function_MomentVec_F_cubature( x_array, *args ):
    '''
    x_array     ndim by nsdim       ndim is the number of samples from each 
                                    integral, and nsdim is 
                                    number of multivariate integrals 
    '''
    
    res=integrate_function_MomentVec_F_qmc( x_array, *args )            
    if res.shape[1] == 1: #fdim == 1:
        return res.flatten()
    else:
        return res

def integrate_function_MomentVec_T_qmc( Fx_array, *args ):
    '''
    x_array     ndim by nsdim       ndim is the number of samples from each 
                                    integral, and nsdim is 
                                    number of multivariate integrals 
    '''

    A, meanMat, zs, As, Bs, P = args

    vectorizedCall = True
    if Fx_array.ndim == 1: # single point, npts=1, not a vectorized call
        Fx_array = Fx_array.reshape(1, Fx_array.shape[0])
        vectorizedCall = False    
    
    fdim = As.shape[1]
    # ndim = Fx_array.shape[0] # number of sample combination from every intergrals
    Fx_array[Fx_array==0.] = 10**-5
    Fx_array[Fx_array==1.] = 1 - 10**-5
    x_array = numpy.sqrt(2) * erfinv(2*Fx_array - 1)
    #x_array = scipy.stats.norm.ppf(Fx_array)
    #res = numpy.ones((x_array.shape[0], fdim))
    inshape  = Fx_array.shape
    outshape = inshape[:-1] + (fdim,) # normally input shape is same as output shape but with last dimension ndim replaced by fdim
    res = numpy.ones(outshape)
    
    xs_array = (A.dot(x_array.T)+meanMat).T
    res *= fsprod(xs_array, zs)
    res *= ((As.T.dot(xs_array.T)).T + Bs) **P
    
    if not vectorizedCall: res = res.reshape(fdim)
    if fdim == 1: return res.reshape(outshape[:-1])
    else: return res

def integrate_function_MomentVec_T_cubature( Fx_array, *args ):
    '''
    x_array     ndim by nsdim       ndim is the number of samples from each 
                                    integral, and nsdim is 
                                    number of multivariate integrals 
    '''
    
    res=integrate_function_MomentVec_T_qmc( Fx_array, *args )            
    if res.shape[1] == 1: #fdim == 1:
        return res.flatten()
    else:
        return res

def pyAllMoments(zs,
    meanMat, covMat, nMom, As, Bs, P,
    absErr, relErr, maxEval, intg_method='qmc'):

    nd = len(zs[0]) # length of softpdftype
    fdim = As.shape[1]
    ranges = []
    for idx in range(len(zs[1])):
        pdftype = zs[0][idx]
        if pdftype in  [1, 2]: # nl, limi, probdens
            nl = zs[1][idx]
            limi = zs[2][idx]
            ranges.append((limi[0], limi[nl[0]-1]))
        elif pdftype in [10]:
            zm = zs[1][idx][0]
            zstd = numpy.sqrt(zs[2][idx])[0]
            ranges.append((zm-5*zstd, zm+5*zstd))

    ranges = numpy.array(ranges)
    xmin = ranges[:,0].copy()#+numpy.finfo(numpy.float32).eps
    xmax = ranges[:,1].copy()#-numpy.finfo(numpy.float32).eps
    mvnpdf = scipy.stats.multivariate_normal( meanMat.T[0], covMat ).pdf
    value = []
    error = []
    finfo = []

    # nMom=1
    intg_base = 'integrate_function_MomentVec'
    module_str = intg_method.split('_')[0] # 'cubature' or 'qmc'
    intg_module = eval(module_str)
    intg_suffix = '_' + module_str
    if intg_method.endswith('_F'):
        xmin = numpy.zeros(xmin.shape)
        xmax = numpy.ones(xmax.shape)
        if pdftype in [1, 2]:
            Fzs = pdf2cdf(zs)
        elif pdftype in [10]:
            Fzs = zs
        intg_suffix = '_F' + intg_suffix # _F_cubature or _F_qmc
        args=(Fzs, mvnpdf, As, Bs, P )
    elif intg_method.endswith('_T'):
        xmin = numpy.zeros(xmin.shape)+numpy.finfo(float).eps
        xmax = numpy.ones(xmax.shape)-numpy.finfo(float).eps
        #A=numpy.linalg.cholesky(covMat)
        try:
            u,s,vh=numpy.linalg.svd(covMat)
        except numpy.linalg.LinAlgError:
            _warnings_mod.warn(
                "[STARBME] np.linalg.svd (dgesdd) failed; "
                "falling back to scipy.linalg.svd (gesvd).",
                RuntimeWarning, stacklevel=2)
            u,s,vh=scipy.linalg.svd(covMat, lapack_driver='gesvd')
        A=vh.T*numpy.sqrt(s)
        intg_suffix = '_T' + intg_suffix
        args=(A, meanMat, zs, As, Bs, P)
    else:
        args=(zs, mvnpdf, As, Bs, P )

    intg_func = eval(intg_base + intg_suffix)

    kwargs = dict(func= intg_func,
        xmin=xmin, xmax=xmax,
        args=args, abserr=absErr, relerr=relErr)


    if module_str == 'cubature':
        adap = 'p' if nd <= 3 else 'h'
        kwargs.update(
            ndim=nd, fdim=fdim,
            adaptive=adap, maxEval=maxEval, vectorized=True)
    elif intg_method.startswith('qmc'):
        kwargs.update(
            maxeval=maxEval,
            showinfo=False)
    else:
        raise ValueError(
            'Integration method is not recognized,'\
            ' (input method: {m})'.format(m=intg_method)
            )
    intg_res = intg_module(**kwargs)
    if module_str == 'cubature':
        value, error = intg_res
    elif intg_method.startswith('qmc'):
        value, error, infos = intg_res

    finfo=[numpy.nan]

    value, error, finfo = list(map( lambda x: numpy.array(x), (value, error, finfo) ))
    return value, error, finfo

    
def integrate_function_cubature_NG( x_array, *args ):

    zsdata, zkhdata, pdf_g = args
    fdim = zkhdata.shape[0]

    res = numpy.ones((x_array.shape[0], fdim))

    res *= fsprod( x_array, zsdata )
    if numpy.logical_not(res).all():
        res = numpy.zeros((x_array.shape[0], fdim)) #instead of use res, 0. make sure array type
    else:
        sdata=numpy.kron(numpy.ones((fdim,1)),x_array)
        khdata=numpy.kron(zkhdata,numpy.ones((x_array.shape[0],1)))
        xskh=numpy.hstack([sdata,khdata])
        res *= pdf_g( xskh ).reshape((fdim,x_array.shape[0])).T

    if fdim == 1:
        return numpy.array(res[:,0])
    else:
        return numpy.array(res)

def fsprod( x, zsdata):
    '''
    the product of fs distributions
    x   ndim by ns      x is a 2-D np array with the dimension of 
                        ndim(number of samples at each integral) 
                        by ns (the number of integrals, i.e., number 
                        of soft data)      
    '''

    #res=numpy.ones((x.shape[0],1))
    res=numpy.ones(x.shape[:-1] + (1,))
    
    for k in range(len(zsdata[1])):
        if zsdata[0][k]==2:
            nl=zsdata[1][k,0]
            limi=zsdata[2][k]
            probdens=zsdata[3][k]
            #y_i = numpy.interp(x[:,k:k+1], limi[:nl], probdens[:nl],
            y_i = numpy.interp(x[...,k:k+1], limi[:nl], probdens[:nl],                   
                    left = 0., right = 0.)

        elif zsdata[0][k]==1:
            nl=zsdata[1][k]
            limi=zsdata[2][k]
            probdens=zsdata[3][k]
            #idd=numpy.where(x[:,k:k+1]-limi[:nl]>0)[0]
            idd=numpy.where(x[...,k:k+1]-limi[:nl]>0)[0]
            y_i = probdens[idd]
        elif zsdata[0][k]==10:
            zm=zsdata[1][k]
            zstd=numpy.sqrt(zsdata[2][k])
            try:
                y_i = scipy.stats.norm.pdf(x[...,k:k+1],loc=zm,scale=zstd)
                #y_i = scipy.stats.norm.pdf(x[:,k:k+1],loc=zm,scale=zstd)
            except FloatingPointError:
                # import pdb
                # pdb.set_trace()
                pass
          
        if not (y_i.all() or y_i.any()):
            return numpy.zeros((x.shape[0],1))
        else:
            res *= y_i

    return res

def Fsinv(x,Fsdata):
    '''
    Convert Fs into xs

    Syntax: xs=Fsinv(Fs,Fsdata):

    Fs        ndim by ns     Fs is a 2-D np array with the dimension of 
                             ndim(number of samples at each integral) 
                             by ns (the number of integrals, i.e., number 
                             of soft data). In this case, the samples are 
                             the cumulative distributions. 

    Fsdata    list           list contains softpdftype, nl, limi, and probCDFs 
                             respectively. Each one has a numpy array with 
                             dimension of ns by N, where ns is number of 
                             softdata and N is the size of limi number or 1.                                                                                                                    
    '''
    res=numpy.zeros(x.shape)
    for k in range(len(Fsdata[1])):
      if Fsdata[0][k]==2:
        nl=Fsdata[1][k]
        limi=Fsdata[2][k]
        probCDFs=Fsdata[3][k]
        y_i = numpy.interp( x[:,k:k+1], probCDFs[:nl], limi[:nl],  
            left = 0., right = 1.)
      elif Fsdata[0][k]==1:
        nl=Fsdata[1][k]
        limi=Fsdata[2][k]
        probCDFs=Fsdata[3][k]
        y_i = numpy.interp( x[:,k:k+1], probCDFs[:nl], limi[:nl], 
            left = 0., right = 1.)
      elif Fsdata[0][k]==10:
        zm=Fsdata[1][k]
        zstd=numpy.sqrt(Fsdata[2][k])
        # y_i = (numpy.sqrt(2) * erfinv(2*x[:,k:k+1] - 1) * zstd)+zm 
        # y_i = scipy.stats.norm.ppf(x[:,k:k+1],loc=zm,scale=zstd)
        xx = x[:,k:k+1]
        xx[xx==0.] = 10**-5
        xx[xx==1.] = 1 - 10**-5
        y_i = scipy.stats.norm.ppf(xx,loc=zm,scale=zstd)
        
      res[:,k:k+1]=y_i
    return res

def pyAllMomentsNG(zsdata, zkhdata, pdf_g, absErr, relErr, maxEval):
    '''
    Soft data integration for Non-Gaussian general knowledge PDFs
    '''               
                   
    nd = len(zsdata[1])
    fdim=zkhdata.shape[0]
    if nd <= 3:
        adap = 'p'
    else:
        adap = 'h'
    ranges = []

    for k in range(nd):
      if isinstance(zsdata[0],int):
        zsdata[0]=zsdata[0]*numpy.ones((len(zsdata[1]),1))            
      if zsdata[0][k] == 2 or zsdata[0][k] == 1:
        nl=zsdata[1][k]
        limi=zsdata[2][k]
        ranges.append( (limi[0], limi[nl[0]-1]) )
      if zsdata[0][k] == 10:
        zsm=zsdata[1][k]
        zsstd=numpy.sqrt(zsdata[k][2])
        ranges.append( (zsm-4.*zsstd, zsm+4.*zsstd) )

    ranges = numpy.array(ranges)
    xmin = ranges[:,0].copy()
    xmax = ranges[:,1].copy()

    value = []
    error = []
    finfo = []

    v, e = cubature( ndim = nd, fdim=fdim, func = integrate_function_cubature_NG,
                     xmin = xmin, xmax = xmax,
                     args = ( zsdata, zkhdata, pdf_g),
                     adaptive = adap,
                     abserr = absErr,
                     relerr = relErr,
                     maxEval = maxEval,
                     vectorized=True)
    value = v.reshape((fdim,1))
    error = e.reshape((fdim,1))
    finfo = numpy.nan

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

    import os, sys
    #add starpy import path dynamically
    sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..'))
    from bme.softconverter import ud2zs

    zs = ud2zs(softpdftype, nl, limi, probdens)



    print ('Using Cubature')
    absErr = 0
    relErr = 10**-6
    maxEval = 10**7
    sss = time.time()
    v,e,f = pyAllMoments( zs,
                          meanMat, covMat, nMom, As, Bs, P,
                          absErr, relErr, maxEval, 'cubature' )
    print ('Time Cost:', time.time() - sss)
    print (v)
    print (e)
    print (f)

    print ('Using Cubature_F')
    absErr = 0
    relErr = 10**-6
    maxEval = 10**7
    sss = time.time()
    v,e,f = pyAllMoments( zs,
                          meanMat, covMat, nMom, As, Bs, P,
                          absErr, relErr, maxEval, 'cubature_F' )
    print ('Time Cost:', time.time() - sss)
    print (v)
    print (e)
    print (f)

    print ('Using QMC')
    absErr = 0
    relErr = 10**-6
    maxEval = 1000000 #no use here
    sss = time.time()
    v,e,f = pyAllMoments( zs,
                          meanMat, covMat, nMom, As, Bs, P,
                          absErr, relErr, maxEval, 'qmc' )
    print ('Time Cost:', time.time() - sss)
    print (v)
    print (e)
    print (f)

    print ('Using QMC_F')
    absErr = 0
    relErr = 10**-6
    maxEval = 1000000 #no use here
    sss = time.time()
    v,e,f = pyAllMoments( zs,
                          meanMat, covMat, nMom, As, Bs, P,
                          absErr, relErr, maxEval, 'qmc_F' )
    print ('Time Cost:', time.time() - sss)
    print (v)
    print (e)
    print (f)
