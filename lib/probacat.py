import numpy

def probacat( softpdftype1, nl1, limi1, probdens1,
              softpdftype2, nl2, limi2, probdens2 ):
    if softpdftype1 != softpdftype2:
        raise ValueError( 'softpdftype1 must be same as softpdftype2' )
    softpdftype = softpdftype1

    n1 = nl1.shape[0]
    n2 = nl2.shape[0]

    m1 = limi1.shape[1]
    m2 = limi2.shape[1]

    mp1 = probdens1.shape[1]
    mp2 = probdens2.shape[1]

    if m1 >= m2:
        mlimi = m1
    else:
        mlimi = m2

    if mp1 >= mp2:
        mprob = mp1
    else:
        mprob = mp2

    nl = numpy.vstack( (nl1, nl2) )

    if m1 == m2:
        limi = numpy.vstack( (limi1, limi2) )
    else:
        limi = numpy.empty( (n1+n2, mlimi) )
        limi[:n1, :m1] = limi1
        limi[n1:n1+n2, :m2] = limi2

    if mp1 == mp2:
        probdens = numpy.vstack( ( probdens1, probdens2) )
    else:
        probdens = numpy.empty( (n1+n2, mprob) )
        probdens[:n1, :mp1] = probdens1
        probdens[n1:n1+n2, :mp2] = probdens2

    return softpdftype, nl, limi, probdens