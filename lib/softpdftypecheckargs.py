import numpy as np
from .pystks_variable import get_standard_soft_pdf_type

def softpdftypecheckargs( softpdftype, nl, limi, probdens ):
    '''
    Check softpdftype, raise ValueError if failed.
    If limi/probdens have more columns than nlMax (e.g. after row exclusion),
    they are automatically trimmed to match.
    Returns standard softpdftype, e.g. 1/2/3/4 (int) if succeeded.
    '''
    def range_include_end( start, end, step ):
        r = range( start, end, step )
        if r[-1] + step == end:
            return r + [ end ]
        else:
            return r
    
    softpdftype = get_standard_soft_pdf_type( softpdftype )
    ns = nl.size
    if ns == 0 and limi.size == 0 and probdens.size == 0: # no softdata
        return softpdftype

    if int( softpdftype ) not in [ 1, 2, 3, 4 ]:
        raise ValueError( 'softpdftype must be 1, 2, 3, or 4.' )
    if len( limi ) != ns or len( probdens ) != ns:
        raise ValueError(
            'nl, limi, and probdens must have same number of rows. '
            'nl.size={}, len(limi)={}, len(probdens)={}'.format(
                ns, len(limi), len(probdens)) )
    if ns > 0:
        nlMax = int(nl.max())
        if softpdftype in [ 1, 2 ]:
            # Auto-trim columns when limi has more columns than nlMax
            # (can happen when a row with the largest nl is removed,
            #  e.g. during cross-validation leave-one-out)
            if limi.shape[0] == ns and limi.shape[1] > nlMax:
                limi = limi[:, :nlMax]
            if limi.shape[0] != ns or limi.shape[1] != nlMax:
                raise ValueError(
                    'limi must be a ns({}) by nlMax({}) matrix, '
                    'got shape {}'.format(ns, nlMax, limi.shape) )
        elif softpdftype in [ 3, 4 ]:
            if limi.shape[0] != ns or limi.shape[1] != 3:
                raise ValueError(
                    'limi must be a ns({}) by 3 matrix, '
                    'got shape {}'.format(ns, limi.shape) )
        if softpdftype in [ 1, 3 ]:
            # Auto-trim probdens columns too
            if probdens.shape[0] == ns and probdens.shape[1] > nlMax - 1:
                probdens = probdens[:, :nlMax - 1]
            if probdens.shape[0] != ns or probdens.shape[1] != nlMax - 1:
                raise ValueError(
                    'probdens must be a ns({}) by nlMax-1({}) matrix, '
                    'got shape {}'.format(ns, nlMax - 1, probdens.shape) )
        elif softpdftype in [ 2, 4 ]:
            # Auto-trim probdens columns too
            if probdens.shape[0] == ns and probdens.shape[1] > nlMax:
                probdens = probdens[:, :nlMax]
            if probdens.shape[0] != ns or probdens.shape[1] != nlMax:
                raise ValueError(
                    'probdens must be a ns({}) by nlMax({}) matrix, '
                    'got shape {}'.format(ns, nlMax, probdens.shape) )

    if softpdftype in [ 3, 4 ]:
        for row_i, nl_i, limi_i in enumerate( zip( nl, limi ) ):
            nlcalc = len( range_include_end( limi_i[0], limi_i[2], limi_i[1] ) )
            if nl_i[0] != nlcalc:
                raise ValueError( 'row {i} of limi nees nl("{i}") = {n}'.\
                                  format( i = nl_i, n = nlcalc ) )

    return softpdftype
