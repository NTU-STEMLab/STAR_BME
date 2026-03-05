import os
import io
import contextlib
import time as _time
import numpy
import multiprocessing as mp
CPU_COUNT = mp.cpu_count()

from .softpdftypecheckargs import softpdftypecheckargs
from .starpy.starpy.bme.BMEoptions import BMEoptions as bmeoptions
# NOTE: BMEPosteriorMoments is imported lazily inside _cv_worker_mp()
# to avoid a circular import with BMEprobaEstimations.py (which imports
# BMEprobaMoments from this module).
from .neighbours import neighbours
from .probaneighbours import probaneighbours
from .findpairs import findpairs
from .probasplit import probasplit
from .coord2K import coord2K
from .proba2stat import proba2stat
from .localmeanBME import localmeanBME
from .probaoffset import probaoffset
from .momentsFun import momentsFun
from .proba2probdens import proba2probdens
from .pystks_variable import get_standard_order

#import function_task
from .function_task import get_result,create_func_task,start_function


def _getDividedCk(ck, n):
    d_ck = int(numpy.ceil(ck.shape[0] / float(n)))
    ck_i = [ ck[d_ck*i:d_ck*(i+1),:] for i in range(n) ]
    return ck_i


def BMEprobaMoments( ck, ch, cs, zh, softpdftype,
                     nl, limi, probdens,
                     covmodel, covparam,
                     nhmax, nsmax, dmax,
                     order, options, qpgd = None, qthread = None ):
    '''
    
    ck             nk by d              estimated coordinate
    ch             nh by d              hard data coordinate
    cs             ns by d              soft data coordinate
    zh             nh by 1              hard data value
    softpdftype    string or int        if string, can be 'h', 'hi', 'his...', 'histogram'
                                                          'l', 'li', 'lin...', 'linear'
                                                          'g', 'ga', 'gau...', 'gaussian'
                                                          'n', 'no', 'nor...', 'normal'
                                                          it's CasE-insensitive
                                        if int, 1 for histogram, 2 for linear, 10 for gaussian and normal
    nl             ns by 1              number of limit
    limi           ns by l              matrix of interval limits, where l is equal to max(nl)
    probdens       ns by p              matrix of probability density values, where p is 
                                        equal to either max(nl)-1 if softpdftype is histogram,
                                                     or max(nl)   if softpdftype is linear
    covmodel:      list of string       covmodels, a sequence contains covariance models string, ex.
                                        ['exponentialC','exponentialC']
    covparam:      list of 
                   sequence of float    covparams, a list contains a sequence of covariance parameters values, ex.
                                        [(3,None), (21.9, 35.8)]
    nhmax          int                  maximum number of hard data values that are considered for 
                                        the estimation at the locations specified in ck.
    nsmax          int                  maximum number of soft data values that are considered for
                                        the estimation at the locations specified in ck.
                                        As the computation time is exponentially increasing with nsmax,
                                        it is not advised to use more than few soft data locations.
                                        In any case, nsmax should be lower than 20 in order to
                                        avoid numerical computation problems.
    dmax           list of float        maximum distance between an estimation location and
                                        existing hard/soft data locations. All hard/soft data
                                        locations separated by a distance smaller than dmax from an
                                        estimation location will be included in the estimation process
                                        for that location, whereas other data locations are neglected.
                                        (--: need to add a float support <-- compare with Matlab)
    order          string or int        order of the polynomial drift along the spatial axes at the
                                        estimation locations. For the zero-mean case, NaN (Not-a-Number)
                                        is used.
                                        order             = numpy.nan,     'Zero Mean' for a zero mean
                                                          =         0, 'Constant Mean' for a constant mean
                                        (X: need to work) = 1 for a constant+linear mean along each axis
                                        (X: need to work) = 2 for a constant+linear+quadratic mean along each axis, etc.
    options        29 by 1 array        need to work on

                                        ---- Matlab ----
                                        1 by 1 or 14 vector of optional parameters that can be used if default
                                        values are not satisfactory (otherwise this vector can simply be
                                        omitted from the input list of variables), where :
                                        options(1), options(2) and options(14) are values used by the
                                        fmin.m MATLAB optimization routine that finds the mode of the
                                        probability distribution function (default values are the same
                                        as for fmin.m),
                                        options(3) specifies the maximum number of evaluation that can
                                        be done by the FORTRAN77 subroutines for the integrals (default
                                        value is 50 000 ; this value should be increased if a warning
                                        message appears on the screen during the computation),
                                        options(4) specifies the maximum admissible relative error on the
                                        estimation of these integrals (default value is 1e-4). 
                                        options(8) number of moments to calculate (1, 2 or 3)
                                                =1 to calculate the mean of the BME posterior pdf,
                                                =2 for the mean and estimation error variance
                                                =3 for the mean, estimation variance and coef of skewness.
                                        The default value for options(8) is 2
    qpgd           QprogressDialog      For GUI usage in QGIS, no use in this libaray
    qthread        QThread              For Gui usage in QGIS, no use in this libaray
    '''

    if not qpgd:
        if not qthread:
            canceledByUser = lambda: False
            setValue = lambda qpgd: None
            addValue = lambda qpgd: None
            gui_object = None
        else: #has qthread
            canceledByUser = lambda: qthread.wasCanceled()
            setValue = lambda qthread: None
            addValue = lambda qthread: qthread.sig_progress_count.emit(None)
            gui_object = qthread
    else:
        if not qthread:
            canceledByUser = qpgd.wasCanceled
            setValue = lambda qpgd: qpgd.setValue( qpgd.value() )
            addValue = lambda qpgd: qpgd.setValue( qpgd.value() +1 )
            gui_object = qpgd
        else: #has qpgd and qthread, very strange
            raise ValueError('qpgd and qthread exist at the same time.')

    # check and normalize softpdftype, order
    softpdftype = softpdftypecheckargs(softpdftype, nl, limi, probdens)
    order = get_standard_order(order)

    # --- Fast Gaussian Approximation flag ---
    # When enabled, non-Gaussian soft PDFs are approximated by their mean and
    # variance (Gaussian) so the analytical path is used instead of expensive
    # numerical integration via momentsFun / pyAllMoments.
    _approx_gaussian = False
    try:
        _approx_gaussian = (options is not None and options['soft_approx_gaussian'])
    except (TypeError, KeyError):
        pass

    options1 = options[0, 0]
    nkall = ck.shape[0]
    nk = 1
    nd = ck.shape[1]

    moments = numpy.empty( ( nkall, 3 ) )
    info = moments.copy()

    _t_start = _time.time()

    # Compute statistical moments
    for i in range( nkall ):
        ck_point = ck[ i : i + 1 ]
        chlocal, zhlocal, dhlocal, sumnhlocal, idxhlocal = \
            neighbours( ck_point, ch, zh, nhmax, dmax )

        if canceledByUser():
            return False
        setValue(gui_object)

        cslocal, nllocal, limilocal, probdenslocal,\
            dslocal, sumnslocal, idxslocal = \
            probaneighbours( ck_point, cs, nl, limi, probdens,
                             nsmax, dmax )

        if canceledByUser():
            return False
        setValue(gui_object)

        nh = sumnhlocal
        ns = sumnslocal

        iscompute = 0
        #Test whether  local neighbourhood is empty
        if nh == 0 and ns == 0:
            moments[i,0] = numpy.nan
            moments[i,1] = numpy.nan
            moments[i,2] = numpy.nan
            info[i,0] = numpy.nan
            info[i,1] = numpy.nan
            info[i,2] = numpy.nan
            addValue( gui_object )
            continue

        #Test whether there is a hard data at estimation point
        idxpairs = findpairs( ck_point , chlocal )
        if len( idxpairs ) > 0:
            moments[i,0] = zhlocal[ idxpairs[0,1], 0 ]
            moments[i,1] = 0.
            moments[i,2] = 0.
            info[i] = 4. #assgin all values of ith row with 4
            addValue( gui_object )
            continue

        #Test if there are any soft data at estimation point
        isduplicate = False;
        idxpairs = findpairs( ck_point, cslocal)
        if len( idxpairs ) > 0:
            cest, nlest, limiest, probdensest, cslocal,\
                nllocal, limilocal, probdenslocal = \
                probasplit( cslocal, nllocal, limilocal,
                            probdenslocal, idxpairs[:, 1:2] )

            sumnslocal -= 1
            ns = sumnslocal
            isduplicate = True #Specify there is a soft datum at pred point

        call = numpy.vstack( (ck_point , chlocal, cslocal) )
        Kall, dummyK = coord2K(call, call, covmodel, covparam)

        if canceledByUser():
            return False
        setValue(gui_object)

        K1, K2, K3, dummyK = numpy.hsplit(Kall, [nk, nk+nh, nk+nh+ns])
        if nh == 0:
            K2 = K2.reshape( (nk+ns,0) )
        if ns == 0:
            K3 = K3.reshape( (nk+nh,0) )
        
        Kk, dummyK = numpy.vsplit( K1, [nk] )
        Kk_h, Kh, Ks_h, dummyK = numpy.vsplit( K2, [ nk, nk+nh, nk+nh+ns ] )
        if nh == 0:
            Kk_h = Kk_h.reshape( (nk,0) )
            Kh = Kh.reshape( (0,0) )
            Ks_h = Ks_h.reshape( (ns,0) )
        elif ns == 0:
            Ks_h = Ks_h.reshape( (0,nh) )
        Kk_s, dummyK, Ks, dummyK = numpy.vsplit( K3, [ nk, nk+nh, nk+nh+ns ] )
        if ns == 0:
            Kk_s = Kk_s.reshape( (nk,0) )
            Ks = Ks.reshape( (0,0) )

        #Compute the mean trend and remove it from the data
        mslocal, vslocal = proba2stat( softpdftype, nllocal, limilocal, probdenslocal )

        if canceledByUser():
            return False
        setValue(gui_object)

        mkest, mhest, msest, vkest = localmeanBME(ck_point, chlocal, cslocal, zhlocal, mslocal, 
                                                  vslocal, Kh, Ks_h, Ks, order)

        if sumnhlocal > 0:
            zhlocal -= mhest
        if sumnslocal > 0:
            limilocal = probaoffset( softpdftype, nllocal, limilocal, -msest )
        if isduplicate:
            limiest = probaoffset( softpdftype, nlest, limiest, -mkest, limiest )

        # ====================================================================
        # Fast Gaussian Approximation path
        # ====================================================================
        # When soft_approx_gaussian is True and there is local soft data, we
        # bypass the expensive numerical integration (momentsFun / pyAllMoments)
        # by treating each soft datum as a noisy Gaussian observation with
        #   observed value  = soft mean  (from proba2stat)
        #   noise variance  = soft variance (from proba2stat)
        # This is equivalent to simple kriging with heteroscedastic noise.
        # The soft data variance is added to the diagonal of Ks, then the
        # system is solved analytically—exactly like the hard-data-only path.
        # ====================================================================
        if _approx_gaussian and ns > 0 and not isduplicate:
            # zslocal_approx: treat de-meaned soft means as "observations"
            zslocal_approx = mslocal - msest  # ns x 1

            # Add soft variance to diagonal of Ks (noisy observations)
            Ks_noisy = Ks.copy()
            for si in range(ns):
                Ks_noisy[si, si] += vslocal[si, 0]

            # Build the combined "hard+soft" system analytically
            n_hs = nh + ns
            Khs_aug = numpy.empty((n_hs, n_hs))
            Kk_hs_aug = numpy.empty((nk, n_hs))

            if nh > 0:
                Khs_aug[:nh, :nh] = Kh
                Khs_aug[:nh, nh:] = Ks_h.T  # Kh_s = Ks_h.T
                Khs_aug[nh:, :nh] = Ks_h
                Kk_hs_aug[:, :nh] = Kk_h
            Khs_aug[nh:, nh:] = Ks_noisy
            Kk_hs_aug[:, nh:] = Kk_s

            # Combine observation vectors
            if nh > 0:
                z_hs = numpy.vstack((zhlocal, zslocal_approx))
            else:
                z_hs = zslocal_approx

            try:
                invKhs_aug = numpy.linalg.inv(Khs_aug)
            except numpy.linalg.LinAlgError:
                # Singular matrix fallback: use robust pseudoinverse
                try:
                    invKhs_aug = numpy.linalg.pinv(Khs_aug)
                except numpy.linalg.LinAlgError:
                    # dgesdd SVD failed; fall back to gesvd via scipy
                    import scipy.linalg as _spla
                    U, s, Vh = _spla.svd(Khs_aug, full_matrices=False,
                                         lapack_driver='gesvd')
                    cutoff = 1e-15 * s.max()
                    s_inv = numpy.where(s > cutoff, 1.0 / s, 0.0)
                    invKhs_aug = (Vh.T * s_inv[numpy.newaxis, :]) @ U.T

            BkIFhs = Kk_hs_aug.dot(invKhs_aug)
            KkIFhs = Kk - BkIFhs.dot(Kk_hs_aug.T)

            BMEmean = float(BkIFhs.dot(z_hs).flat[0])
            variance = float(KkIFhs.flat[0])
            if variance < 0:
                variance = 0.0
            stdDev = numpy.sqrt(variance)
            skewCoef = 0.0

            moments[i, 0] = BMEmean + mkest
            moments[i, 1] = variance
            moments[i, 2] = skewCoef
            info[i] = numpy.array([0., 0., 0.])

            addValue(gui_object)
            continue

        if not isduplicate:
            if sumnhlocal == 0:
                KsIFh = Ks
                BsIFh = None #shouldn't be used but need initial
            else:
                invKh = numpy.linalg.inv(Kh)
                if ns > 0:
                    BsIFh = Ks_h.dot(invKh)
                    KsIFh = Ks - BsIFh.dot(Ks_h.T)
                else: #ns == 0
                    BsIFh = None #initial, no use
                    KsIFh = None #initial, no use
            Khs = Kall[nk:,nk:]
            Kk_hs = Kall[0:nk,nk:]
            invKhs = numpy.linalg.inv(Khs) # Get inverse of Khs
            BkIFhs = Kk_hs.dot(invKhs)
            KkIFhs = Kk - BkIFhs.dot(Kk_hs.T)  # Multiply by transpose of Kk_hs

            if canceledByUser():
                return False
            setValue(gui_object)

            BMEmean, stdDev, skewCoef, infot =\
                momentsFun(zhlocal, softpdftype, nllocal, limilocal, probdenslocal,
                           options, BsIFh, KsIFh, BkIFhs, KkIFhs)

            if canceledByUser():
                return False
            setValue(gui_object)

            moments[i,0] = BMEmean
            moments[i,1] = stdDev**2
            moments[i,2] = skewCoef
            info[i] = infot.copy()
        else:
            Kks = numpy.empty( (nk+ns, nk+ns) )
            Kks_h = numpy.empty( (nk+ns, nh) )

            Kks[:nk, :nk] = Kk
            Kks[:nk, nk:nk+ns] = Kk_s
            Kks[nk:nk+ns, :nk] = Kk_s.T
            Kks[nk:nk+ns, nk:nk+ns] = Ks

            if sumnhlocal == 0:
                KksIFh = Kks
            else:
                invKh = numpy.linalg.inv( Kh )
                Kks_h[:nk, :nh] = Kk_h
                Kks_h[nk:nk+ns, :nh] = Ks_h
                BksIFh = Kks_h.dot( invKh )
                KksIFh = Kks - BksIFh.dot( Kks_h.T )

            if canceledByUser():
                return False
            setValue(gui_object)

            BMEmean, stdDev, skewCoef, infot =\
                momentsDupFun( zhlocal, softpdftype, nllocal, limilocal, 
                               probdenslocal, options, BksIFh, KksIFh, nlest, 
                               limiest, probdensest )

            if canceledByUser():
                return False
            setValue(gui_object)

            moments[i,0] = BMEmean
            moments[i,1] = stdDev**2
            info[i] = infot.copy()

        moments[i,0] += mkest

        addValue( gui_object )

    _elapsed = _time.time() - _t_start
    if nkall > 0:
        print("[STARBME] BMEprobaMoments completed: {} points in {:.1f}s ({:.3f}s/point)".format(
            nkall, _elapsed, _elapsed / nkall))

    return moments, info


def BMEprobaMoments_mp( ck, ch, cs, zh, softpdftype,
                     nl, limi, probdens,
                     covmodel, covparam,
                     nhmax, nsmax, dmax,
                     order, options, workers=max(1, CPU_COUNT - 1) ):

    ck_i = _getDividedCk( ck, workers )
    args = [ch, cs, zh, softpdftype,
                     nl, limi, probdens,
                     covmodel, covparam,
                     nhmax, nsmax, dmax,
                     order, options]
    res_i = [ [ i ] + args for i in ck_i ]
    pool = mp.Pool(processes=workers)
    result = pool.map(_warp_BMEprobaMoments, res_i)
    moments, info = zip( *result )
    moments = numpy.vstack( moments )
    info = numpy.vstack( info )
    return moments, info


def BMEprobaMoments_mp_qgis( ck, ch, cs, zh, softpdftype,
                             nl, limi, probdens,
                             covmodel, covparam,
                             nhmax, nsmax, dmax,
                             order, options, workers=max(1, CPU_COUNT - 1) ):
   
    ck_i = _getDividedCk( ck, workers )
    constant_args = [ch, cs, zh, softpdftype,
                     nl, limi, probdens,
                     covmodel, covparam,
                     nhmax, nsmax, dmax,
                     order, options]
    args_list = [ [ i ] + constant_args for i in ck_i ]

    #add function_task search path
    dir_here = os.path.abspath(os.path.dirname(__file__))
    search_path = (dir_here,)

    job_list = []
    for i in range(workers):
        job_list.append(create_func_task('BMEprobaMoments', 'BMEprobaMoments', search_path))
    for job,args in zip(job_list, args_list):
        start_function(job, args)
    res_list = []
    for job in job_list:
        res_list.append(get_result(job))
    
    moments, info = zip( *res_list )
    moments = numpy.vstack( moments )
    info = numpy.vstack( info )
    return moments, info


def _warp_BMEprobaMoments( args ):
    return BMEprobaMoments( *args )


# ============================================================
# Cross-validation worker  (ThreadPoolExecutor)
# ============================================================
# Module-level storage populated once by _cv_init_worker()
# (called from the main thread before creating the pool).
# All ThreadPoolExecutor workers share the same process memory,
# so _cv_shared is read directly — no pickling needed.
_cv_shared = {}


def _cv_init_worker(shared_dict):
    """Initializer for ThreadPoolExecutor cross-validation workers.

    Called once in the main process before submitting tasks.
    Stores shared read-only data and limits BLAS internal
    threads to 1 so each worker thread acts as a single parallel
    unit (avoiding N_workers × N_blas_threads explosion).
    """
    global _cv_shared
    _cv_shared = shared_dict
    import os

    # ---- limit BLAS threading ----
    for var in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[var] = '1'


def _cv_worker_mp(item):
    """Thread-safe cross-validation worker.

    Reconstructs leave-one-out arrays from *_cv_shared* + the exclude
    index carried in *item*, then calls BMEPosteriorMoments for a single
    estimation point.  This uses the same fast QMC + importance-sampling
    engine as the prediction module, replacing the old (slow) cubature-
    based BMEprobaMoments path.

    Parameters
    ----------
    item : dict
        'data_type' : 'hard' or 'soft'
        'idx'       : int – row to exclude from the matching dataset

    Returns
    -------
    tuple (data_type, idx, value)
        *value* is the BME posterior mean (float), nan on error, or
        None if the call was cancelled.
    """
    try:
        shared = _cv_shared
        dt = item['data_type']
        idx = item['idx']

        # -- reconstruct leave-one-out hard data --
        full_ch = shared['hard_coords']
        full_zh = shared['hard_zh']

        if dt == 'hard':
            mask_h = numpy.arange(full_ch.shape[0]) != idx
            ch = full_ch[mask_h]
            zh = full_zh[mask_h]
            ck = full_ch[idx:idx + 1]
        else:
            ch = full_ch
            zh = full_zh
            ck = shared['soft_coords'][idx:idx + 1]

        # -- reconstruct leave-one-out soft data (zs format) --
        cs_full = shared['soft_coords']
        zs_full = shared['zs']  # list of [softpdftype, nl_i, limi_i, probdens_i]

        if dt == 'soft' and len(zs_full) > 0:
            cs = numpy.delete(cs_full, idx, axis=0)
            zs = [z for i, z in enumerate(zs_full) if i != idx]
        else:
            cs = cs_full if cs_full.size > 0 else None
            zs = list(zs_full) if zs_full else None

        # Handle empty arrays → None for BMEPosteriorMoments
        if ch is not None and ch.size == 0:
            ch = None
            zh = None
        if cs is not None and cs.size == 0:
            cs = None
            zs = None

        # Lazy import to break circular dependency:
        # BMEprobaEstimations imports BMEprobaMoments (this module),
        # so we cannot import BMEPosteriorMoments at module level.
        from .starpy.starpy.bme.BMEprobaEstimations import BMEPosteriorMoments

        # Suppress verbose prints from BMEPosteriorMoments inside workers
        with contextlib.redirect_stdout(io.StringIO()):
            res = BMEPosteriorMoments(
                ck, ch, cs, zh, zs,
                shared['covmodel'], shared['covparam'],
                None,                    # covmat (not pre-computed)
                shared['order'], shared['options'],
                shared['nhmax'], shared['nsmax'], shared['dmax'],
                gui_args=None,           # no progress dialog in workers
                n_workers=1,             # single thread inside each worker
            )

        if isinstance(res, numpy.ndarray):
            # res shape is (1, 4): [mean, variance, skewness, delta_mu]
            return (dt, idx, float(res[0, 0]))
        else:
            return (dt, idx, None)
    except Exception:
        import traceback
        traceback.print_exc()
        return (item.get('data_type', '?'), item.get('idx', -1), float('nan'))


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('error')
    import time
    nk = 1
    nh = 1
    ns = 1
    n = [nk, nh, ns]

    ck = numpy.array([ [0.5, 0.5] ])
    ch = numpy.array([ [0, 0] ])
    cs = numpy.array([ [1, 0.9] ])
    zh = numpy.array([ [1.4] ])
    
    softpdftype = 1

    nl = numpy.array([ [4] ])
    limi = numpy.array([ [0.1, 0.3, 0.7, 1.1] ])
    probdens = numpy.array([ [1, 1.5, 0.5] ])
    
    options=bmeoptions()


    #parameters for BMEprobaMoments
    cNugget = 0.05
    cc = 1
    aa = 1
    at = 1
    maxpts = 1000000
    aEps = 0.0

    #testtype 1
    rEps = 0.02
    nBMEpdfpts = 50

    nhmax = 4
    nsmax = 4


    covmodel = numpy.array(["nuggetC","exponentialC"])
    covparam = numpy.array([[cNugget, None],
                 [cc, 3*aa]])
    dmax = numpy.array([[100]])
    #PCI = 'dummy'
    order = numpy.nan
    options[0] = 0
    options[2] = maxpts
    options[3] = rEps
    options[5] = nBMEpdfpts
    options[6] = 0.001
    options[7] = 3
    #options[19] = PCI?!?!?





    #case 4
    rEps = 0.02
    options[3] = rEps
    ns = 3
    cs = numpy.vstack( (cs, [[0.1, 0.2]], [[0.3, 0.5]]) )
    softpdftype = 2
    nl = numpy.array([ [4],
                       [3],
                       [3] ])
    limi = numpy.array([ [0.01, 0.03, 0.2, 1.0],
                         [0.01, 0.09, 0.9, numpy.nan],
                         [0.02, 0.1, 1.1, numpy.nan] ])
    probdens = numpy.array([ [0, 1, 1, 0],
                             [0, 1, 0, numpy.nan],
                             [0, 1, 0, numpy.nan] ])
    nl, limi, probdens, _ = proba2probdens( softpdftype, nl, limi, probdens )
    #print probdens 
    options[5] = 25

    if ns == 1:
        rEps = rEps/1000.
        options[3] = rEps

    print("Test BMEprobaMoments...")
    start_time = time.time()
    mmm, iii = BMEprobaMoments( ck, ch, cs, zh, softpdftype,
                                    nl, limi, probdens,
                                    covmodel, covparam,
                                    nhmax, nsmax, dmax,
                                    order, options )
    print ('Time Cost:', time.time() - start_time)
    print (mmm)
    print (iii)


    TEST_MP = False
    if TEST_MP:
        TEST_N = 50
        nk = TEST_N
        n = [nk, nh, ns]
        ck = numpy.ones((TEST_N,1))*ck

        print ("Test BMEprobaMoments_mp...")
        start_time = time.time()
        mmm, iii = BMEprobaMoments_mp( ck, ch, cs, zh, softpdftype,
                                    nl, limi, probdens,
                                    covmodel, covparam,
                                    nhmax, nsmax, dmax,
                                    order, options )
        print( 'Time Cost:', time.time() - start_time)
        print (mmm)
        print (iii)
        print (len(mmm))



    TEST_MP_QGIS = True
    if TEST_MP_QGIS:
        TEST_N = 50
        nk = TEST_N
        n = [nk, nh, ns]
        ck = numpy.ones((TEST_N,1))*ck

        print ("Test BMEprobaMoments_mp_qgis...")
        start_time = time.time()
        mmm, iii = BMEprobaMoments_mp_qgis( ck, ch, cs, zh, softpdftype,
                                    nl, limi, probdens,
                                    covmodel, covparam,
                                    nhmax, nsmax, dmax,
                                    order, options )
        print ('Time Cost:', time.time() - start_time)
        print (mmm)
        print (iii)
        print (len(mmm))
