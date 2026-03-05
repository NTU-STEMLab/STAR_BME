# -*- coding:utf-8 -*-
import numpy
import multiprocessing as mp
CPU_COUNT = mp.cpu_count()

try:
    from scipy.spatial.distance import cdist as _cdist
except ImportError:
    _cdist = None


def coord2dist_mp(c1, c2, workers=max(1, CPU_COUNT - 1)):
    '''
    workers    int    number of workers
    '''

    if c1.shape[0] * c2.shape[0] <= 10 ** 7 or workers == 1:
        return coord2dist(c1, c2)
    else:
        print ('used worker:', workers)
        d_c1 = int(numpy.ceil(c1.shape[0] / float(workers)))
        d_c2 = int(numpy.ceil(c2.shape[0] / float(workers)))
        c12 = [(c1[d_c1 * i:d_c1 * (i + 1)],
                c2[d_c2 * i:d_c2 * (i + 1)]) for i in range(workers)]
        res_ij = [(c12[i][0], c12[j][1]) for i in range(workers)
                  for j in range(workers)]
        pool = mp.Pool(processes=workers)
        result = pool.map(_warp_coord2dist, res_ij)

        result = [numpy.vstack(result[i::workers]) for i in range(workers)]
        result = numpy.hstack(result)
        return result

    return result


def _warp_coord2dist(args):
    return coord2dist(*args)


def coord2dist(c1, c2):
    '''
    Calculate the distance between c1 and c2

    Input 
        c1    [r1 x d]    numpy.array
        c2    [r2 x d]    numpy.array
    Output
        result    [r1 x r2]    numpy.array
    '''

    # Use scipy cdist for ~10-100x speed-up over Kronecker-product method
    if _cdist is not None:
        try:
            return _cdist(c1, c2, 'euclidean')
        except Exception:
            pass

    # Fallback: Kronecker-product based distance (slow but always works)
    ones_c1 = numpy.ones((c1.shape[0], 1))
    ones_c2 = numpy.ones((c2.shape[0], 1))
    a = numpy.kron(c1, ones_c2)
    b = numpy.kron(ones_c1, c2)
    result = ((a - b) ** 2)
    result = result.sum(axis=1)
    result = numpy.sqrt(result)
    result = result.reshape((c1.shape[0], c2.shape[0]))
    return result

if __name__ == "__main__":
    import time

    a = numpy.random.random((10, 2))
    b = numpy.random.random((10, 2))

    start_time = time.time()
    try:
        result = coord2dist(a, b)
    except MemoryError:
        pass
    print ('Time cost:', time.time() - start_time)
    print (result[:3, :])
    start_time = time.time()
    result2 = coord2dist_mp(a, b)
    print ('Time cost:', time.time() - start_time)
    print (result2[:3, :])
