import numpy

from .coord2dist import coord2dist


def findpairs(c1, c2):
    '''return index pair'''

    if c1.shape[0] <= c2.shape[0]:
        smaller_c = c1
        bigger_c = c2
        smaller_is_c1 = True
    else:
        smaller_c = c2
        bigger_c = c1
        smaller_is_c1 = False

    pair_idx_list = []
    for small_idx, row_i in enumerate(smaller_c):
        big_idx = numpy.where(numpy.all(row_i == bigger_c, axis=1))[0]
        if len(big_idx):
            pair_idx_list.append([small_idx, big_idx[0]])

    if pair_idx_list:
        pair_idx_list = numpy.array(pair_idx_list)
        if smaller_is_c1:
            return pair_idx_list
        else:
            pair_idx_list[:, [0, 1]] = pair_idx_list[:, [1, 0]]
            return pair_idx_list
    else:
        return pair_idx_list

if __name__ == "__main__":
    import time
    c1 = numpy.array([[1, 1, 1], [1, 2, 1], [1, 1, 2.], [2, 2, 1]])
    c2 = numpy.array(
        [[1, 2, 5], [2, 2, 2.], [0, 0, 1.], [1, 0, 0], [2, 1, 2], [2, 2, 2]])
    res = findpairs(c1, c2)
    print (res)
