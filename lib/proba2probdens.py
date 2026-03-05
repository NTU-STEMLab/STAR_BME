import numpy as np

def proba2probdens( softpdftype, nl, limi, probdens ):
    softpdftype = 2 # always 2 for now
    norm_probdens = [ ]
    area_list = [ ]
    for nl_i, limi_i, probdens_i in zip( nl, limi, probdens):
        nl_i = int( nl_i[ 0 ] )
        limi_i = limi_i[ : nl_i ]
        probdens_i_original = probdens_i[:] #copy
        probdens_i = probdens_i[ :nl_i ]

        height = limi_i[ 1: ] - limi_i[ :-1 ]
        sum_up_low = probdens_i[ :-1 ] + probdens_i[ 1: ]
        area = (sum_up_low * height / 2.).sum()
        norm_probdens_i = probdens_i / area
        probdens_i_original[ :nl_i] = norm_probdens_i
        norm_probdens.append( probdens_i_original )
        area_list.append( [area] )

    return nl, limi, np.array( norm_probdens ), np.array( area_list )