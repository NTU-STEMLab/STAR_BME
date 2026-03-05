# -*- coding: utf-8 -*-
import numpy
from .neighbours import neighbours
from .coord2K import coord2K

def kriging ( ck, ch, zh, model, param, nhmax, dmax, order = 0, options = None ):
    ''' 
    input
    ck: nk by d float
    ch: nh by d float
    zh: nh by 1 float
    model: mn by 1 string
    param: mn by 3 float
    nhmax: int
    dmax: 1 by 3 float
    order: always 0
    options: not no use here
    
    return
    zk: mn+1 by 1 float
    vk: mn+1 by 1 float
    '''
    
    #initial return variable
    nk = ck.shape[0]
    zk = numpy.zeros( ( nk, 1 ) )
    vk = numpy.zeros( ( nk, 1 ) )
    zk[:] = numpy.nan
    vk[:] = numpy.nan
    
    for i in range( ck.shape[0] ):
        ci = ck[i:i+1]
        ci_nebr, zi_nebr, di_nebr, ni_nebr, idxi_nebr = neighbours(ci, ch, zh, nhmax, dmax )
        if ni_nebr > 0:
            K, dummyKK = coord2K( ci_nebr, ci_nebr, model, param )
            k, dummykk = coord2K( ci_nebr, ci, model, param ) #kk is a list contain ki
            k0, dummykk0 = coord2K(ci, ci, model, param)
#            unit = numpy.ones(k.shape) # n by 1, X in matlab
#            unit_t_add = numpy.append( unit.T, [[0]], axis = 1 ) # 1 by n+1, x in matlab
                 
            #change shape for kriging
#            Kadd = numpy.hstack( ( K, unit ) )
#            Kadd = numpy.vstack( ( Kadd, unit_t_add ) )
            Kadd = K
#            kadd = numpy.append( k, [[0]], axis = 0 )
            kadd = k
            weight = numpy.dot( numpy.linalg.inv( Kadd ), kadd )#[:-1,:]
            weight_t = weight.T
            #compute zk, vk
            zk[i] = weight_t.dot( zi_nebr )
            vk[i] = ( k0 - 2 * weight_t.dot( k ) + weight_t.dot( K ).dot( weight ) )[0]
            
        else:
            pass #already give NaN
    return zk, vk
    
def factorial_kriging( ck, ch, zh, model, param, nhmax, dmax, order = 0, options = None):

    ''' 
    input
    ck: nk by d float
    ch: nh by d float
    zh: nh by 1 float
    model: mn by 1 string ( ex. "exponential/gaussian" )
    param: mn by 3 float (ex. [ c, s, t ] )
    nhmax: int
    dmax: 1 by 3 float
    order: always 0, equals NaN in matlab
    options: not no use here, 0 or 1 in matlab for display echo 
    
    return
    zk: mn+1 by 1 float
    vk: mn+1 by 1 float
    '''
    
    #initial return variable
    nk = ck.shape[0]
    mn = model.shape[0]
    zk = numpy.zeros( ( nk, mn+1 ) )
    vk = numpy.zeros( ( nk, mn+1 ) )
    zk[:] = numpy.nan
    vk[:] = numpy.nan
    
    for i in range( ck.shape[0] ):
        ci = ck[i:i+1]
        ci_nebr, zi_nebr, di_nebr, ni_nebr, idxi_nebr = neighbours(ci, ch, zh, nhmax, dmax )
        if ni_nebr > 0:
            K, dummyKK = coord2K( ci_nebr, ci_nebr, model, param )
            dummyk, kk = coord2K( ci_nebr, ci, model, param ) #kk is a list contain ki
            dummyk0, kk0 = coord2K(ci, ci, model, param)
            unit = numpy.ones(kk[0].shape) # n by 1
            unit_t_add = numpy.append( unit.T, [[0]], axis = 1 ) # 1 by n+1
            for idx_k, (ki,k0i) in enumerate( zip( kk, kk0 ) ):          
                #change shape for kriging
                Kadd = numpy.hstack( ( K, unit ) )
                Kadd = numpy.vstack( ( Kadd, unit_t_add ) )
                kkadd = numpy.append( ki, [[0]], axis = 0 )
                weight = numpy.dot( numpy.linalg.inv( Kadd ), kkadd )[:-1,:]
                weight_t = weight.T
                #compute zk, vk
                zk[i:i+1,idx_k:idx_k+1] = weight_t.dot( zi_nebr )
                vk[i:i+1,idx_k:idx_k+1] = ( k0i - 2 * weight_t.dot( ki ) + weight_t.dot( K ).dot( weight ) )[0]
            #compute local mean trend
            kkadd = numpy.append( numpy.zeros( kk[0].shape ), [[1]], axis = 0 )
            weight = numpy.dot( numpy.linalg.inv( Kadd ), kkadd )[:-1,:]
            weight_t = weight.T
            zk[i:i+1,-1:] = weight_t.dot( zi_nebr )
            vk[i:i+1,-1:] = weight_t.dot( K ).dot( weight )[0]
        else:
            pass #already give NaN
    return zk, vk
    
            
if __name__ == "__main__":
    data = numpy.loadtxt("BBS4matlab.csv", delimiter = "," ,skiprows = 1)
    ch = data[:,0:3]
    zh = data[:,3:4]
    ck = numpy.array([[333112.30 ,2778240.50 ,2011],
                      [35958.55 ,2777069.47 ,2011],
                      [329671.77 ,2772200.62 ,2011],
                      [337802.26 ,2716083.23 ,2011],
                      [281568.72 ,2771548.28 ,2011]])
    model = numpy.array([["exponential/exponential"],["gaussian/gaussian"]])
    param = numpy.array([[10.,80000,4],[1.5,20000,4]])
    nhmax = 20
    import time
    dmax = numpy.array([[10000.,20000.,5000.]])
    aaa=time.time()
    zk, vk = kriging( ck, ch, zh, model, param, nhmax, dmax, order = 0)
    print (time.time() - aaa)
    #zk, vk = factorial_kriging( ck, ch, zh, model, param, nhmax, dmax, order = 0)
    print(zk)
    print(vk)
    
    #zk, vk = kriging( ck, ch, zh, model, param, nhmax, dmax, order = 0)
    zk, vk = factorial_kriging( ck, ch, zh, model, param, nhmax, dmax, order = 0)
    print (zk[:,0:2].sum(axis = 1))
    print (vk[:,0:2].sum(axis = 1))
