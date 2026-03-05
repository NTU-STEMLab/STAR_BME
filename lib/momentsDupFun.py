from .probacat import probacat
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

    Val, Err, fInfo = pyAllMoments( softpdftype, nlks, limiks, probdensks, msIFh, KsIFh, 2, As,
                                    Bs, P, absErr = aEps, relErr = rEps, maxEval = maxpts )

    #here should add some warning

    normConstant = Val[0]
    if normConstant == 0:
        raise ValueError( 'Error: Normalization constant found to be 0.' )
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

    Val, Err, fInfo = pyAllMoments( softpdftype, nlks, limiks, probdensks, msIFh, KsIFh, nMom-1, As,
                                    Bs, P, absErr = aEps, relErr = rEps, maxEval = maxpts )

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
        if skewCoef > 0 :
            skewCoef = (Val[1] / normConstant ) / stdDev **3
        else:
            skewCoef = numpy.nan
        info[0][2] = finfo[-1]

    return BMEmean, stdDev, skewCoef, info