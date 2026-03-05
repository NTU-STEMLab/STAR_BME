import numpy
import scipy.stats
from .coord2K import coord2Ksplit
from .proba2stat import proba2stat
from .pystks_variable import get_standard_order, get_standard_soft_pdf_type

KHS_DICT = {'k': 0, 'h': 1, 's': 2}


def _get_x_all_split(nk, zh, zs):
    xk = numpy.empty((nk, 1))  # will replace later
    xh = zh
    if get_standard_soft_pdf_type(zs[0]) == 10:  # gaussian/normal
        xs = zs[1]
    else:
        xs, dummy_v = proba2stat(*zs)
    return [xk, xh, xs]


def _get_mean_all_split(x_all_split, order):
    if numpy.isnan(order):  # zero mean
        mean_all_split = []
        for i in x_all_split:
            mean_all_split.append(numpy.zeros(i.shape))
    elif order == 0:  # constant mean, exclude zk, average h and s
        constant_mean_ = numpy.vstack(x_all_split[1:]).mean()
        for i in mean_all_split:
            i[:] = constant_mean_
    return mean_all_split


def _get_cov_all_split(ck, ch, cs, covmodel, covparam):
    return coord2Ksplit((ck, ch, cs), (ck, ch, cs),
                        covmodel, covparam)[0]


def _get_x(x_all_split, sub):
    idx = [KHS_DICT[i] for i in sub]
    return numpy.vstack([x_all_split[i] for i in idx])


def _get_mean(mean_all_split, sub):
    idx = [KHS_DICT[i] for i in sub]
    return numpy.vstack([mean_all_split[i] for i in idx])


def _get_sigma(cov_all_split, sub_a, sub_b, inv=False):
    idx_a = [KHS_DICT[i] for i in sub_a]
    idx_b = [KHS_DICT[i] for i in sub_b]

    cov_a_b = []
    for i in idx_a:
        cov_a_b.append(
            numpy.hstack([cov_all_split[i][j] for j in idx_b]))
    cov_a_b = numpy.vstack(cov_a_b)
    if not inv:
        return cov_a_b
    else:
        return numpy.linalg.inv(cov_a_b)


def _get_mean_a_given_b(x_all_split, mean_all_split,
                        cov_all_split, sub_a, sub_b):
    x_b = _get_x(x_all_split, sub_b)
    mean_a = _get_mean(mean_all_split, sub_a)
    mean_b = _get_mean(mean_all_split, sub_b)
    sigma_a_b = _get_sigma(cov_all_split, sub_a, sub_b)
    inv_sigma_b_b = _get_sigma(cov_all_split, sub_b, sub_b, inv=True)
    return mean_a + sigma_a_b.dot(inv_sigma_b_b).dot(x_b - mean_b)


def _get_sigma_a_given_b(cov_all_split, sub_a, sub_b):
    sigma_a_a = _get_sigma(cov_all_split, sub_a, sub_a)
    sigma_a_b = _get_sigma(cov_all_split, sub_a, sub_b)
    inv_sigma_b_b = _get_sigma(cov_all_split, sub_b, sub_b, inv=True)
    sigma_b_a = _get_sigma(cov_all_split, sub_b, sub_a)
    return sigma_a_a - sigma_a_b.dot(inv_sigma_b_b).dot(sigma_b_a)


def _get_multivariate_normal_pdf(x_all_split, mean_all_split,
                                 cov_all_split, sub_multi):
    if "_" in sub_multi:  # "given" type
        sub_a, sub_b = x_sub.split('_')
        m = _get_mean_a_given_b(x_all_split, mean_all_split,
                                cov_all_split, sub_a, sub_b)
        v = _get_sigma_a_given_b(cov_all_split, sub_a, sub_b)
    else:  # single_sub
        sub_a = sub_multi
        m = _get_mean(mean_all_split, sub_a)
        v = _get_sigma(cov_all_split, sub_a, sub_a)
    return scipy.stats.multivariate_normal(m.T[0], v).pdf


def _get_int_fg_a_given_b_fs_s(x_all_split, mean_all_split,
                               cov_all_split, zs, sub_multi, sub_s='s'):

    #fg='s_kh', fs='s'
    sub_a, sub_b = sub_multi.split('_')
    sigma_a_given_b = _get_sigma_a_given_b(cov_all_split, sub_a, sub_b)
    inv_sigma_a_given_b = numpy.linalg.inv(sigma_a_given_b)
    mean_tilde_s = zs[1]  # mean
    sigma_tilde_s = numpy.diag(zs[2].T[0])  # cov matrix
    inv_sigma_tilde_s = numpy.linalg.inv(sigma_tilde_s)

    sigma_t = numpy.linalg.inv(inv_sigma_a_given_b + inv_sigma_tilde_s)
    det_sigma_t = numpy.linalg.det(sigma_t)
    det_sigma_a_given_b = numpy.linalg.det(sigma_a_given_b)
    det_sigma_tilde_s = numpy.linalg.det(sigma_tilde_s)
    ns = mean_tilde_s.shape[0]
    fgfs_front = numpy.sqrt(det_sigma_t) /\
        ((2*numpy.pi)**(ns/2.) *
         numpy.sqrt(det_sigma_a_given_b * det_sigma_tilde_s)
         )

    mean_a_given_b = _get_mean_a_given_b(
        x_all_split, mean_all_split, cov_all_split, sub_a, sub_b)
    fgfs_1 = mean_a_given_b.T.dot(
        inv_sigma_a_given_b).dot(mean_a_given_b)
    fgfs_2 = (mean_tilde_s.T).dot(inv_sigma_tilde_s).dot(mean_tilde_s)
    fgfs_3 = (mean_a_given_b.T).dot(inv_sigma_a_given_b) +\
        (mean_tilde_s.T).dot(inv_sigma_tilde_s)
    fgfs_4 = inv_sigma_tilde_s.dot(mean_tilde_s) +\
        inv_sigma_a_given_b.dot(mean_a_given_b)
    fgfs_end = numpy.exp(
        (-1/2.) * (fgfs_1 + fgfs_2 - fgfs_3.dot(sigma_t).dot(fgfs_4)))

    return fgfs_front * fgfs_end, \
        (sigma_t, inv_sigma_a_given_b, inv_sigma_tilde_s, mean_tilde_s)


def BMEPosteriorMoment(
    ck, ch, cs, zh, zs,
    covmodel, covparam,
    order, options=None,
    general_knowledge='gaussian',
    specific_knowledge='unknown'):
    #SI = integrate (fg_s_given_kh * fs_s) dx_s
    #NC = integrate (fg_s_given_h * fs_s) dx_s
    #pdf_k = (fg_kh * SI) / (fg_h * NC)  # eq.1
    #exp_k = ... # eq.2
    #exp_kp = ... # eq.3
    #if general_knowledge == gaussian and specific_knowledge == unknown
    #exp_k = ... # eq.4
    #var_k = ... # eq.5

    if general_knowledge == 'gaussian' and specific_knowledge == 'gaussian':
    # fg_s_given_kh ~ n(mean_s_given_kh, sigma_s_given_kh),
    # fs_s ~ n(mean_s, sigma_s)

        # mean_s_given_kh = get_mean_a_given_b(a='s', b='kh')
        # sigma_s_given_kh = get_sigma_a_given_b(a='s', b='kh')
        # mean_tilde_s = zs[:, 0:1]
        # sigma_tilde_s = numpy.diag(zs[:, 1])

        # SI, (sigma_t, inv_sigma_s_given_kh, inv_sigma_tilde_s) =\
        #     fgfs(fg='s_kh', fs='s')

        order = get_standard_order(order)
        softpdftype = get_standard_soft_pdf_type(zs[0])
        nk = ck.shape[0]
        x_all_split = _get_x_all_split(nk, zh, zs)
        mean_all_split = _get_mean_all_split(x_all_split, order)
        cov_all_split = _get_cov_all_split(ck, ch, cs, covmodel, covparam)

        mean_s_given_h = _get_mean_a_given_b(
            x_all_split, mean_all_split,
            cov_all_split,sub_a='s', sub_b='h')
        sigma_s_given_h = _get_sigma_a_given_b(
            cov_all_split, sub_a='s', sub_b='h')

        #mean_tilde_s = ...
        #sigma_tilde_s = ...
        NC, (sigma_t_prime, inv_sigma_s_given_h,
            inv_sigma_tilde_s, mean_tilde_s) =\
                _get_int_fg_a_given_b_fs_s(
                    x_all_split, mean_all_split,
                    cov_all_split, zs,
                    sub_multi = 's_h', sub_s='s')

        hat_x_h = _get_x(x_all_split, 'h') * NC
        hat_x_s = NC * sigma_t_prime.dot(inv_sigma_s_given_h.dot(mean_s_given_h) +
                                   inv_sigma_tilde_s.dot(mean_tilde_s))
        hat_x_hs = numpy.vstack((hat_x_h, hat_x_s))

        sigma_k_hs = _get_sigma(
            cov_all_split, sub_a='k', sub_b='hs')

        inv_sigma_hs_hs = _get_sigma(
            cov_all_split, sub_a='hs', sub_b='hs', inv=True)

        BME_mean_k_given_hs_a =\
            sigma_k_hs.dot(
                inv_sigma_hs_hs).dot(
                    hat_x_hs)

        BME_mean_k_given_hs_b =\
            _get_mean(mean_all_split, 'k') - sigma_k_hs.dot(
                inv_sigma_hs_hs).dot(
                    _get_mean(mean_all_split, 'hs'))

        BME_mean_k_given_hs =\
            BME_mean_k_given_hs_a / NC + BME_mean_k_given_hs_b

        sigma_k_given_hs = _get_sigma_a_given_b(
            cov_all_split, sub_a='k', sub_b='hs')

        BME_var_k_given_hs =\
            sigma_k_given_hs - BME_mean_k_given_hs**2

        return BME_mean_k_given_hs, BME_var_k_given_hs


def BMEPosteriorPDF(
    ck, ch, cs, zh, zs,
    covmodel, covparam,
    order, options=None,
    general_knowledge='gaussian',
    specific_knowledge='unknown'):
    '''
    zs = (softpdftype, mean, variance)
    zs = (softpdftype, nl, limi, probadens)
    '''

    #SI = integrate (fg_s_given_kh * fs_s) dx_s
    #NC = integrate (fg_s_given_h * fs_s) dx_s
    #pdf_k = (fg_kh * SI) / (fg_h * NC)  # eq.1
    #exp_k = ... # eq.2
    #exp_kp = ... # eq.3
    #if general_knowledge == gaussian and specific_knowledge == unknown
    #exp_k = ... # eq.4
    #var_k = ... # eq.5
    order = get_standard_order(order)
    softpdftype = get_standard_soft_pdf_type(zs[0])
    nk = ck.shape[0]
    x_all_split = _get_x_all_split(nk, zh, zs)
    mean_all_split = _get_mean_all_split(x_all_split, order)
    cov_all_split = _get_cov_all_split(ck, ch, cs, covmodel, covparam)

    if general_knowledge == 'gaussian':  # fg is gaussian
        fg_kh = lambda xk: _get_multivariate_normal_pdf(
            x_all_split, mean_all_split, cov_all_split, 'kh')(
                numpy.vstack((xk, _get_x(x_all_split, 'h'))).T)
        fg_h = _get_multivariate_normal_pdf(
            x_all_split, mean_all_split, cov_all_split, 'h')(
                _get_x(x_all_split, 'h').T)
        if specific_knowledge == 'gaussian':
            SI = lambda xk: _get_int_fg_a_given_b_fs_s(
                [xk] + x_all_split[1:], mean_all_split,
                cov_all_split, zs, 's_kh', 's')[0]
            NC = _get_int_fg_a_given_b_fs_s(
                x_all_split, mean_all_split,
                cov_all_split, zs, 's_h', 's')[0]
            return lambda xk: (fg_kh(xk) * SI(xk) / fg_h / NC)[0][0]
        else:
            pass  # to do
            # fg_s_given_kh = get_multivariate_normal_pdf('s_kh')
            # fg_s_given_h = get_multivariate_normal_pdf('s_h')
   
if __name__ == "__main__":
    order = numpy.nan
    covmodel = ['exponentialC']
    covparam = [(1., 5.)]

    ck = numpy.array([[1., 1.]])
    ch = numpy.array([[0.1, 4.], [5., 2.]])
    cs = numpy.array([[1, 0.9], [2, 1.5]])
    zh = numpy.array([[1.2], [1.7]])
    mean = numpy.array([0,1],ndmin=2).T
    var = numpy.array([1,2],ndmin=2).T
    zs = [10, mean, var]#numpy.array([[0., 1.], [0., 1.]])
    ns = 2

    # fg_kh, fg_h, SI, NC = BMEPosteriorPDF(ck, ch, cs, zh, zs,
    #                        covmodel, covparam,
    #                        order, options=None,
    #                        general_knowledge='gaussian',
    #                        specific_knowledge='gaussian')
    ppdf = BMEPosteriorPDF(ck, ch, cs, zh, zs,
                          covmodel, covparam,
                          order, options=None,
                          general_knowledge='gaussian',
                          specific_knowledge='gaussian')

    from cubature import cubature
    # mon1_for_cubature = lambda x: numpy.array([x[0]*ppdf(x[0])])
    # exv,mon1_err = cubature(1, mon1_for_cubature, numpy.array([-10.]),
    #     numpy.array([10.]))

    mon1_for_cubature = lambda x: x[0]*ppdf(x[0])
    exv,mon1_err = cubature(mon1_for_cubature, 1, 1, numpy.array([-10.]),
        numpy.array([10.]))
    print ("----BMEPosteriorPDF----")
    print ("Expect Value:\n\t", exv)
    print ("Expect Integrate Error:\n\t", mon1_err)

    # mon2_for_cubature = lambda x: numpy.array([(x[0]**2)*ppdf(x[0])])
    # mon2,mon2_err = cubature(1, mon2_for_cubature,numpy.array([-6.]),
    #     numpy.array([7.]))

    mon2_for_cubature = lambda x: (x[0]**2)*ppdf(x[0])
    mon2,mon2_err = cubature( mon2_for_cubature, 1, 1, numpy.array([-6.]),
        numpy.array([7.]))


    print ("Moment(2):\n\t", mon2)
    print ("Moment(2) Integrate Error:\n\t", mon2_err)
    print ("Variance(by method 1):\n\t", mon2 - exv**2)

    # mon2_for_cubature = lambda x: numpy.array([(x[0]-exv[0])**2*ppdf(x[0])])
    # mon2,mon2_err = cubature(1, mon2_for_cubature,numpy.array([-6.]),
    #     numpy.array([7.]))

    mon2_for_cubature = lambda x: (x[0]-exv[0])**2*ppdf(x[0])
    mon2,mon2_err = cubature( mon2_for_cubature, 1, 1, numpy.array([-6.]),
        numpy.array([7.]))

    print ("Variance(by method 2):\n\t", mon2)
    print ("Variance Integrate Error:\n\t", mon2_err)

    print ("--------"*2)
    aa=BMEPosteriorMoment(ck, ch, cs, zh, zs,
                       covmodel, covparam,
                       order, options=None,
                       general_knowledge='gaussian',
                       specific_knowledge='gaussian')
    print ("----BMEPosteriorMoment----")
    print ("Expect Value:\n\t", aa[0][0][0])
    print ("Variance(by method 3):\n\t", aa[1][0][0])
    print ("--------"*2)
    # a, b = BMEPosteriorPDF(ck, ch, cs, zh, zs,
    #                        covmodel, covparam,
    #                        order, options=None,
    #                        general_knowledge='gaussian',
    #                        specific_knowledge='gaussian')
    # print a, numpy.array(numpy.diag(b), ndmin=2).T
