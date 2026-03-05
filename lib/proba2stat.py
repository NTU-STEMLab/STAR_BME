import numpy
from .pystks_variable import get_standard_soft_pdf_type

def proba2stat(softpdftype, nl, limi, probdens):
    def range_include_end(start, end, step):
        include_end_indexs = numpy.where( (end - start)%step == 0 )[0]
        revised_end = end.copy()
        revised_end[ include_end_indexs ] += step[ include_end_indexs ]
        result = list(map( lambda x:numpy.arange(*x), zip(start, revised_end, step) ))
        return result

    softpdftype = get_standard_soft_pdf_type(softpdftype)
    if nl.shape[0] == 0:
        return numpy.array([]).reshape( (0,1) ), numpy.array([]).reshape( (0,1) )
        
    if softpdftype == 1 or softpdftype == 2:
    	L1 = limi[:,:-1]
    	L2 = limi[:,1:]
    elif softpdftype == 3 or softpdftype == 4: #grid
        nlMax = nl.max()
        limi_expand = numpy.zeros( (nl.shape[0], nlMax) )
        for idx, i in enumerate( range_include_end(limi[:,0], limi[:,2], limi[:,1]) ):
            limi_expand[idx][:i.size] = i
        L1 = limi_expand[:,:-1]
        L2 = limi_expand[:,1:]

    if softpdftype == 1 or softpdftype == 3:
        P1 = probdens
        XsMean_mat = (1/2.) * P1 * (L2**2 - L1**2)
        Xs2Mean_mat = (1/3.) * P1 * (L2**3 - L1**3)
    elif softpdftype == 2 or softpdftype == 4:
        P1 = probdens[:,:-1]
        P2 = probdens[:,1:]
        dL = L2 - L1
        # Guard against divide-by-zero when consecutive limi values are equal
        safe_dL = numpy.where(numpy.abs(dL) < 1e-30, 1.0, dL)
        fsp = numpy.where(numpy.abs(dL) < 1e-30, 0.0, (P2 - P1) / safe_dL)
        fso = P1 - L1 * fsp

        L1p2 = L1 * L1
        L1p3 = L1p2 * L1
        L1p4 = L1p3 * L1

        L2p2 = L2 * L2
        L2p3 = L2p2 * L2
        L2p4 = L2p3 * L2
        
        XsMean_mat = ( 1 / 2. ) * ( fso * (L2p2 - L1p2) ) + ( 1 / 3. ) * (fsp * (L2p3 - L1p3) )
        Xs2Mean_mat = ( 1 / 3. ) * ( fso * (L2p3 - L1p3) ) + ( 1 / 4. ) * ( fsp * (L2p4 - L1p4) )
        # Replace any residual NaN/Inf from degenerate intervals with zero
        numpy.nan_to_num(XsMean_mat, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        numpy.nan_to_num(Xs2Mean_mat, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

    XsMean = []
    Xs2Mean = []
    for nl_i, XsMean_i, Xs2Mean_i in zip( nl, XsMean_mat, Xs2Mean_mat ):
        XsMean.append( [ XsMean_i[ : int(nl_i[0]) - 1].sum()] )
        Xs2Mean.append( [ Xs2Mean_i[ : int(nl_i[0]) - 1].sum()] )

    XsMean, Xs2Mean = numpy.array( XsMean ), numpy.array( Xs2Mean )
    softmean = XsMean
    softvar = Xs2Mean - XsMean**2

    return softmean, softvar
