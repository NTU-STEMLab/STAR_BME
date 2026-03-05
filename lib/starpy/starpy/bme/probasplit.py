# -*- coding: utf-8 -*-
import numpy


def probasplit( c, nl, limi, probdens, index ):
    idx = index.flatten() #flat
    c1, nl1, limi1, probdens1 = list(map( lambda x: x[ idx ], ( c, nl, limi, probdens ) ))
    idx2 = numpy.delete( range( c.shape[ 0 ] ), idx )
    c2, nl2, limi2, probdens2 = list(map( lambda x: x[ idx2 ], ( c, nl, limi, probdens ) ))
    return c1, nl1, limi1, probdens1, c2, nl2, limi2, probdens2

if __name__ == "__main__":
    row = 10
    c = numpy.random.rand( row , 3 )
    nl = numpy.random.rand( row, 1 )
    limi = numpy.random.rand( row,5 )
    probdens = numpy.random.rand( row,8 )
    index = numpy.array( [[3]] )

    print (c)
    print (nl)
    print (limi)
    print (probdens)

    res = probasplit( c, nl, limi, probdens, index )
    print (res)

