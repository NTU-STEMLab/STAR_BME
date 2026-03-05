import numpy

from .coord2dist import coord2dist
from .isspacetime import isspacetime
from .modelslib import get_model


def coord2K(c1, c2, models, params):
    '''

    models    list of string       covmodels, a sequence contains covariance models string
    params    list of 
              sequence of float    covparams, a list contains a sequence of covariance parameters values

    isST
        isSTsep
            models: ['exponentialC','exponentialC','...'] 
            params: [(3,None), (21.9, 35.8)] 
        not isSTsep
            models: ["gaussianCST", "exponentialCST", "..." ]
            params: [(sill1, bs1, stratio),
                     (sill2, bs2, stratio)]
    not isST
        models: ["gaussian", "exponential", "..."" ]
        params: [(sill1, bs1),
                 (sill2, bs2)]

    return 
    sum(Ki): all value
    Ki: list of i_th model value

    '''

    if c1.size == 0 or c2.size == 0:
        Ki = []
        for model in models:
            Ki.append( numpy.array( [] ).reshape( (c1.shape[0], c2.shape[0]) ) )
        return sum(Ki), Ki

    isST, isSTsep, modelS, modelT = isspacetime(models)
    if isST:
        if isSTsep:
            dist_s = coord2dist(c1[:, 0:2], c2[:, 0:2])
            dist_t = coord2dist(c1[:, 2:3], c2[:, 2:3])
            Ki = []
            for model_s, model_t, param_i in zip(modelS, modelT, params):
                sill, param_s, param_t = param_i
                model_s = get_model(model_s)
                model_t = get_model(model_t)
                Ki.append(
                    sill * model_s(dist_s, 1., param_s) * model_t(dist_t, 1., param_t))
            return sum(Ki), Ki  # K, KK in matlab
        else:
            dist_s = coord2dist(c1[:, 0:2], c2[:, 0:2])
            dist_t = coord2dist(c1[:, 2:3], c2[:, 2:3])
            Ki = []
            for model_s, param_i in zip(modelS, params):
                sill, param_s, s_t_ratio = param_i
                model_s = get_model(model_s)
                Ki.append(
                    sill * model_s(dist_s + s_t_ratio * dist_t, 1., param_s))
            return sum(Ki), Ki  # K, KK in matlab
    else:
        Ki = []
        dist_s = coord2dist(c1, c2)
        for model_s, param_i in zip(modelS, params):
            sill, param_s = param_i
            model_s = get_model(model_s)
            Ki.append(sill * model_s(dist_s, 1., param_s))
        return sum(Ki), Ki  # K, KK in matlab

def coord2Ksplit(c1_split, c2split, models, params):
    '''
    split dataset for estimated/hard/soft data split.

    models    list of string       covmodels, a sequence contains covariance models string
    params    list of 
              sequence of float    covparams, a list contains a sequence of covariance parameters values

    isST
        isSTsep
            models: ['exponentialC','exponentialC','...'] 
            params: [(3,None), (21.9, 35.8)] 
        not isSTsep
            models: ["gaussianCST", "exponentialCST", "..." ]
            params: [(sill1, bs1, stratio),
                     (sill2, bs2, stratio)]
    not isST
        models: ["gaussian", "exponential", "..."" ]
        params: [(sill1, bs1),
                 (sill2, bs2)]

    return 
    sum(Ki): all value
    Ki: list of i_th model value

    '''
    sum_k_split = []
    ki_split = []
    for c1_i in c1_split:
        sum_k_j = []
        ki_split_j = []
        for c2_j in c2split:
            sum_k, ki = coord2K( c1_i, c2_j, models, params )
            sum_k_j.append( sum_k )
            ki_split_j.append( ki )
        sum_k_split.append( sum_k_j )
        ki_split.append( ki_split_j )
        
    return sum_k_split, ki_split


if __name__ == "__main__":
    print ('--Test coord2K--- ')
    import time
    start_time = time.time()
    c1 = numpy.array(
        [[1, 1, 1], [1, 2, 1], [1, 1, 2.], [2, 2, 1], [2, 1, 2], [2, 2, 2]])
    c2 = numpy.array([[0, 1, 0], [1, 1, 0], [0, 0, 1.], [1, 0, 0]])
    models = ["exponentialC/exponentialC", "gaussianC/gaussianC"]
    params = [(1, 0.5, 0.5), (0.8, 2, 2)]
    A, B = coord2K(c1, c2, models, params)
    for b in B:
        print (b)

    print (A)
    print ('Time cost:', time.time() - start_time)

    print ('--Test coord2Ksplit--- ')
    x=numpy.array([]).reshape((0,3))
    A, B = coord2Ksplit([c1,x,c2], [c1,x], models, params)
    for i in A:
        for j in i:
            print (j.shape)


    print ('test c1 or c2 is empty')
    start_time = time.time()
    c2 = numpy.array([],ndmin=2).reshape((0,3))
    print (c2.shape)
    A, B = coord2K( c1, c2, models, params )
    for b in B:
        print (b)

    print (A)
    print ('Time cost:', time.time()-start_time)
