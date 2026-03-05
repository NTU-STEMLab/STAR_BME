# -*- coding: utf-8 -*-
import numpy

from ..mvn.pyAllMoments import pyAllMoments
from .probacat import probacat
from ..bme.softconverter import ud2zs

def momentsFun(zh, zs,
               options, BsIFh, KsIFh, BkIFhs, KkIFhs):

    nh = zh.size
    ns = len(zs[0])
    maxpts = options[2][0]
    aEps = 0
    rEps = options[3][0]
    nMom = options[7][0]

    intg_method = options['integration method']

    if nMom not in [1, 2, 3]:
        raise ValueError('Illegal value for nMom')

    # Case with no soft data points
    #
    # m1=meank=BkIFhs*zh
    # m2=vark=KkIFhs
    # stdDev=sqrt(vark)
    # m3=0;
    # skewCoef=m3/sdtDev^3; ??stdDev^3

    if ns == 0:
        normConstant = 1
        if nh == 0:
            BMEmean = 0
        else:
            BMEmean = BkIFhs.dot(zh)
        stdDev = numpy.sqrt(KkIFhs)
        skewCoef = 0
        info = numpy.array([[0., 0., 0.]])
        return BMEmean, stdDev, skewCoef, info

    # Case with soft data points
    #
    # A=Int[ dXs fS(Xs) mvnpdf(Xs|h)]
    # m1=meank=1/A * Int[dXs fS(Xs) Bk|hs*Xsh mvnpdf(Xs|h)]
    # m2=vark=Kk|sh + 1/A * Int[dXs fS(Xs) (Bk|hs*Xhs-meank)^2 mvnpdf(Xs|h)]
    # stdDev=sqrt(vark)

    BsMean = numpy.array([[1., numpy.nan]])
    if nh == 0:
        msIFh = numpy.zeros((ns, 1))
        BsMean[0][1] = 0.
    else:
        msIFh = BsIFh.dot(zh)
        BsMean[0][1] = BkIFhs[:,:nh].dot(zh)

    # Initialize As
    As = numpy.zeros((ns, 2))
    As[:ns, 1:2] = BkIFhs[0:1, nh : nh + ns].T

    Pmean = numpy.ones((1, 2))
    nMomMean = 2;
    
    Val, Err, fInfo = pyAllMoments(
        zs, msIFh, KsIFh, nMomMean, As,
        BsMean, Pmean, absErr=aEps, relErr=rEps, maxEval=maxpts,
        intg_method=intg_method )
    # here should add some warning info

    normConstant = Val[0]
    if normConstant == 0:
        #raise ValueError( 'Error: Normalization constant found to be 0.')
        print ('Error: Normalization constant found to be 0.'\
            ' Please check the bounds of soft data')
        BMEmean=numpy.nan
        stdDev=numpy.nan
        skewCoef=numpy.nan  
        info=numpy.array([ numpy.nan, numpy.nan, numpy.nan ]).reshape(1,3)
        return BMEmean, stdDev, skewCoef, info 
    else:
        BMEmean = Val[1] / normConstant
        info = numpy.array([ fInfo[-1], numpy.nan, numpy.nan ]).reshape(1,3)
   
    if nMom == 1:
        stdDev = numpy.nan
        skewCoef = numpy.nan
        return BMEmean, stdDev, skewCoef, info

    As = numpy.kron( As[:,1:2], numpy.ones( (1, nMom - 1) ) )
    Bs = numpy.array( [ [BsMean[0][1] - BMEmean]])#, numpy.nan] ] )
    P = numpy.array( [ [ 2.]])#, numpy.nan ] ] )

    if nMom == 3:
        #Bs[0][1] = Bs[0][0]
        Bs=numpy.hstack([Bs,Bs])
        #P[0][1] = 3.
        P=numpy.hstack([P,[[3.]]])

    Val, Err, fInfo = pyAllMoments(
        zs, msIFh, KsIFh, int(nMom-1), As,
        Bs, P, absErr = aEps, relErr = rEps, maxEval = maxpts,
        intg_method=intg_method )
    # here should add some warning info

    stdDev = KkIFhs[0][0] + Val[0]/normConstant
    if stdDev < 0:
        print ('Warning: Negative variance={v}'.format( v = stdDev ))
    else:
        stdDev = numpy.sqrt(stdDev)
        info[0][1] = fInfo[0]

    if nMom == 2:
        skewCoef = numpy.nan
        info[0][2] = numpy.nan
    else:
        if stdDev > 0: # > EPS
            skewCoef = (Val[1] / normConstant ) / stdDev **3
        else:
            skewCoef = numpy.nan
        info[0][2] = fInfo[-1]

    return BMEmean, stdDev, skewCoef, info


def momentsDupFun( zh, softpdftype, nl, limi, probdens, options,
                   BksIFh, KksIFh, nlest, limiest, probdensest ):
    nh = zh.size
    ns = nl.size
    maxpts = options[2][0]
    aEps = 0
    rEps = options[3][0]
    nMom = options[7][0]

    if nMom not in [1, 2, 3]:
        raise ValueError('Illegal value for nMom')

    intg_method = options['integration method']

    m1 = limiest.shape[1]
    m2 = limi.shape[1]
    mp1 = probdensest.shape[1]
    mp2 = probdens.shape[1]

    if m1 >= m2:
        mlimi = m1
    else:
        mlimi = m2

    if mp1 >= mp2:
        mprob = mp1
    else:
        mprob = mp2

    nn = nlest.shape[0] + nl.shape[0]

    dummy, nlks, limiks, probdensks =\
        probacat( softpdftype, nlest, limiest, probdensest,
                  softpdftype, nl, limi, probdens )

    if nh == 0:
        mksIFh = numpy.zeros( (ns+1, 1) )
    else:
        mksIFh = BksIFh.dot( zh )

    Bs = numpy.array( [ [1., 0.] ] )
    As = numpy.zeros( (ns+1, 2) )

    As[0][1] = 1.
    P =  numpy.array( [ [1., 1.] ] )
    zs = ud2zs(softpdftype, nlks, limiks, probdensks)
    Val, Err, fInfo = pyAllMoments(
        zs, mksIFh, KksIFh, 2, As,
        Bs, P, absErr = aEps, relErr = rEps, maxEval = maxpts,
        intg_method=intg_method )

    #here should add some warning

    normConstant = Val[0]
    if normConstant == 0:
        print ('Error: Normalization constant found to be 0.')
        BMEmean = numpy.nan
        stdDev = numpy.nan
        skewCoef = numpy.nan
        info = numpy.array( [ [fInfo[-1], numpy.nan, numpy.nan ] ] )
        return BMEmean, stdDev, skewCoef, info
        # raise ValueError( 'Error: Normalization constant found to be 0.' )
    BMEmean = Val[1] / normConstant
    info = numpy.array( [ [fInfo[-1], numpy.nan, numpy.nan ] ] )

    if nMom == 1:
        stdDev = numpy.nan
        skewCoef = numpy.nan
        return BMEmean, stdDev, skewCoef, info

    Bs[:] = 0.
    P[:] = 0.
    As = numpy.zeros( (ns+1, 1) )
    Bs[0][0] = -BMEmean
    P[0][0] = 2.
    As[0][0] = 1.

    if nMom == 3:
        Bs[0][1] = -BMEmean
        P[0][1] = 3.
        tempAs = numpy.zeros( (As.shape[0],1) )
        As = numpy.hstack( (As, tempAs) )
        As[0][1] = 1.

    Val, Err, fInfo = pyAllMoments(
        zs, mksIFh, KksIFh, nMom-1, As,
        Bs, P, absErr = aEps, relErr = rEps, maxEval = maxpts,
        intg_method=intg_method )

    #here add some warning

    stdDev = Val[0] / normConstant
    if stdDev < 0:
        print ('Warning: Negative variance={v}'.format( v = stdDev ))
    else:
        stdDev = numpy.sqrt(stdDev)
        info[0][1] = fInfo[0]

    if nMom == 2:
        skewCoef = numpy.nan
        info[0][2] = numpy.nan
    else:
        # if skewCoef > 0 :
        #     skewCoef = (Val[1] / normConstant ) / stdDev **3
        # else:
        skewCoef = numpy.nan
        info[0][2] = fInfo[-1]

    return BMEmean, stdDev, skewCoef, info