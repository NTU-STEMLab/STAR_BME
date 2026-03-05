import numpy


def get_model(m_name):
    try:
        return eval(m_name)
    except NameError as e:
        #must be do something...
        raise e


def exponentialC(dist, sill, range):
    return sill * numpy.exp(-3 * dist / range)


def gaussianC(dist, sill, range):
    return sill * numpy.exp(-3 * (dist / range) ** 2)


def sphericalC(dist, sill, range):
    value = dist / range
    result = sill * (1 - ((3 / 2.) * value - (1 / 2.) * (value) ** 3))
    result[dist > range] = 0.
    return result


def holecosC(dist, a_half, p_half):
    return a_half * numpy.cos(numpy.pi * dist / p_half)


def nuggetC(dist, sill, no_used_range=None):
    result = numpy.zeros(dist.shape)
    result[dist == 0] = 1.
    return result

if __name__ == '__main__':
    print (get_model('exponentialC'))
