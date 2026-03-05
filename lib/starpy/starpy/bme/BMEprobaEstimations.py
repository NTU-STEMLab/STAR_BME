# -*- coding: utf-8 -*-
import copy
import warnings as _warnings_mod

from six.moves import range
import numpy as np
import scipy.stats
import scipy.linalg
from scipy.spatial.distance import pdist
from scipy.spatial import cKDTree

from STAR_BME.lib.starpy.starpy.bme.softconverter import proba2stat
from STAR_BME.lib.starpy.starpy.bme.softconverter import pdf2cdf
from STAR_BME.lib.starpy.starpy.general.coord2K import coord2K, coord2Ksplit

from STAR_BME.lib.proba2stat import proba2stat
from STAR_BME.lib.pystks_variable import get_standard_order, get_standard_soft_pdf_type
from STAR_BME.lib.BMEprobaMoments import BMEprobaMoments
from STAR_BME.lib.starpy.starpy.bme.BMEoptions import BMEoptions
from STAR_BME.lib.starpy.starpy.stats.mepdf import maxentpdf_gc, maxentcondpdf_gc
from STAR_BME.lib.starpy.starpy.general.valstvgx import valstv2stg,valstg2stv
from STAR_BME.lib.starpy.starpy.general.neighbours import neighbours, neighbours_index_kd
from STAR_BME.lib.starpy.starpy.mvn.pyAllMoments import pyAllMomentsNG
from STAR_BME.lib.starpy.starpy.mvn.qmc import qmc


# ===================================================================
# Robust SVD wrapper – Fix A: dgesdd → gesvd fallback
# ===================================================================

def _robust_svd(a, full_matrices=True):
    """Drop-in replacement for ``np.linalg.svd`` that automatically
    falls back to the more robust ``gesvd`` LAPACK driver when the
    default ``dgesdd`` driver fails to converge.

    NumPy's ``np.linalg.svd`` uses the divide-and-conquer algorithm
    ``dgesdd``, which is fast but can raise ``LinAlgError: SVD did not
    converge`` on ill-conditioned or near-singular matrices common in
    spatiotemporal BME covariance matrices.  SciPy exposes
    ``scipy.linalg.svd(lapack_driver='gesvd')`` which uses the older
    QR-iteration algorithm that is slower but substantially more robust.

    Parameters
    ----------
    a : array_like
        Matrix to decompose.
    full_matrices : bool, optional
        If True (default), U and Vh have shapes (M, M) and (N, N).
        If False, the shapes are (M, K) and (K, N) where K = min(M, N).

    Returns
    -------
    U, s, Vh : ndarray
        Same as ``np.linalg.svd``.
    """
    try:
        return np.linalg.svd(a, full_matrices=full_matrices)
    except np.linalg.LinAlgError:
        _warnings_mod.warn(
            "[STARBME] np.linalg.svd (dgesdd) failed to converge; "
            "falling back to scipy.linalg.svd (gesvd).",
            RuntimeWarning, stacklevel=2)
        return scipy.linalg.svd(
            a, full_matrices=full_matrices, lapack_driver='gesvd')


def _robust_pinv(a, rcond=1e-15):
    """Pseudo-inverse using ``_robust_svd`` instead of ``np.linalg.svd``.

    ``np.linalg.pinv`` delegates to the default dgesdd SVD driver which
    can raise ``LinAlgError`` or produce overflow/invalid-value warnings
    on ill-conditioned covariance matrices.  This function follows the
    same algorithm (truncated SVD) but uses ``_robust_svd`` so that it
    automatically falls back to the more stable gesvd driver.

    Parameters
    ----------
    a : array_like, shape (M, N)
        Matrix to pseudo-invert.
    rcond : float, optional
        Singular values smaller than ``rcond * max(s)`` are set to zero.

    Returns
    -------
    a_pinv : ndarray, shape (N, M)
        The pseudo-inverse of *a*.
    """
    a = np.asarray(a)
    if a.size == 0:
        return a.T  # empty matrix edge case
    U, s, Vh = _robust_svd(a, full_matrices=False)
    # Threshold small singular values (same logic as np.linalg.pinv)
    cutoff = rcond * s.max()
    large = s > cutoff
    s_inv = np.zeros_like(s)
    s_inv[large] = 1.0 / s[large]
    return (Vh.T * s_inv[np.newaxis, :]) @ U.T


KHS_DICT = {'k': 0, 'h': 1, 's': 2}


def _bme_posterior_pdf(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None,
    general_knowledge='gaussian',
    #  specific_knowledge='unknown',  
    pdfk=None, pdfh=None, pdfs=None, hk_k=None, hk_h=None, hk_s=None,
    gui_args=None):

    def __get_zs_integration_limits(zs):
        '''get soft data integration limit''' 
        ranges = []
        for zsi in zs:
            pdftype = get_standard_soft_pdf_type(zsi[0])
            if pdftype in  [1, 2]: # nl, limi, probdens
                nl = zsi[1]
                limi = zsi[2]
                ranges.append((limi[0], limi[nl[0]-1]))
            elif pdftype in [10]:
                zm = zsi[1]
                zstd = np.sqrt(zsi[2])
                ranges.append((zm-3*zstd, zm+3*zstd))
        ranges = np.array(ranges)
        return ranges.copy()
    order = get_standard_order(order)
    nk = ck.shape[0]
    nh = ch.shape[0] if ch is not None else 0
    ns = cs.shape[0] if cs is not None else 0

    # --- Auto-Gaussian fallback for _bme_posterior_pdf ---
    # Same logic as in _bme_posterior_moments: when the number of
    # non-Gaussian soft data exceeds a threshold, convert them to
    # Gaussian (mean, variance) to avoid intractable high-dimensional
    # QMC integration.
    if zs and general_knowledge == 'gaussian':
        _NS_AUTO_GAUSS_PDF = 20
        _use_gauss_approx_pdf = (
            options is not None and options.get('soft_approx_gaussian', False))
        if not _use_gauss_approx_pdf:
            _ns_nongauss_pdf = sum(
                1 for zsi in zs
                if get_standard_soft_pdf_type(zsi[0]) != 10)
            if _ns_nongauss_pdf > _NS_AUTO_GAUSS_PDF:
                import warnings
                warnings.warn(
                    "[_bme_posterior_pdf] ns_nongaussian={} exceeds "
                    "auto-Gaussian threshold ({}). Approximating "
                    "non-Gaussian soft PDFs as Gaussian.".format(
                        _ns_nongauss_pdf, _NS_AUTO_GAUSS_PDF))
                _use_gauss_approx_pdf = True
        if _use_gauss_approx_pdf:
            zs_converted = []
            for zsi in zs:
                pdftype = get_standard_soft_pdf_type(zsi[0])
                if pdftype in [1, 2]:
                    zs_gau_m, zs_gau_v = proba2stat(
                        zsi[0],
                        np.array([zsi[1]]),
                        np.array([zsi[2]]),
                        np.array([zsi[3]]))
                    zs_converted.append(
                        (10, float(np.asarray(zs_gau_m).flat[0]),
                         float(np.asarray(zs_gau_v).flat[0])))
                else:
                    zs_converted.append(zsi)
            zs = zs_converted

    x_all_split = _get_x_all_split(nk, zh, zs)
    Xh = _get_x(x_all_split, 'h')
    mean_all_split = _get_mean_all_split(x_all_split, order)
    #get cov_all_split
    if covmat is None:
        cov_all_split = _get_cov_all_split(ck, ch, cs, covmodel, covparam)
        cov_k_khs = np.hstack([i for i in cov_all_split[0] if i is not None])
        cov_h_khs = np.hstack([i for i in cov_all_split[1] if i is not None])
        cov_s_khs = np.hstack([i for i in cov_all_split[2] if i is not None])
        covmat = np.vstack([cov_k_khs, cov_h_khs, cov_s_khs])
    else:
        cov_all_split = np.vsplit(
            covmat, [nk, nk+nh, nk+nh+ns]
            )[:-1] #exclude final empty array
        cov_all_split = \
            [np.hsplit(c, [nk, nk+nh, nk+nh+ns][:-1])\
            for c in cov_all_split]

    #find duplicated point (covariance-based + exact coordinate match)
    if ns:
        # Covariance-based detection (unit-free)
        _ck_dup_pdf, _cs_dup_pdf, _ = _find_ck_cs_near_duplicates(
            covmat, nk, nh, ns)
        # Also check exact coordinate equality
        _exact_pairs = np.array(
            np.all((ck[:, None, :] == cs[None, :, :]), axis=-1).nonzero()
            ).T
        if _ck_dup_pdf.size > 0:
            _cov_pairs = np.column_stack([_ck_dup_pdf, _cs_dup_pdf])
            if _exact_pairs.size > 0:
                dup_ck_cs_idx = np.unique(
                    np.vstack([_cov_pairs, _exact_pairs]), axis=0)
            else:
                dup_ck_cs_idx = _cov_pairs
        else:
            dup_ck_cs_idx = _exact_pairs if _exact_pairs.size > 0 \
                else np.array([]).reshape(0, 2).astype(int)
    else:
        dup_ck_cs_idx = np.array([[]])

    if general_knowledge == 'gaussian':
        
        def __get_fG_Xkh_each_ck(fG_Xkh_):
            if Xh is None:
                def fG_Xkh_each_ck(xk):
                    xk_origin_shape = xk.shape
                    xk = xk.flatten()
                    input_xk = xk.T
                    return fG_Xkh_(input_xk).reshape(xk_origin_shape)
            else:
                def fG_Xkh_each_ck(xk):
                    xk_origin_shape = xk.shape
                    xk = xk.flatten()
                    input_xk = np.vstack(
                        (xk, np.tile(Xh, xk.size))
                        ).T
                    return fG_Xkh_(input_xk).reshape(xk_origin_shape)
            return fG_Xkh_each_ck     
        
        #fG_Xh: const
        if nh == 0:
            fG_Xh = 1.
        else:
            fG_Xh = _get_multivariate_normal_pdf(
                x_all_split, mean_all_split, cov_all_split, 'h')(
                    _get_x(x_all_split, 'h').T)

        def __get_fG_Xs_gvn_Xh_all_ck():
            fG_Xs_gvn_Xh = _get_multivariate_normal_pdf(
                x_all_split, mean_all_split, cov_all_split, 's_h')
            def fG_Xs_gvn_Xh_all_ck(xs):
                xs_origin_shape = xs.shape
                xs = xs.reshape(-1, xs_origin_shape[-1])
                output = fG_Xs_gvn_Xh(xs)
                return output.reshape(xs_origin_shape[:-1]+(1,))
            return fG_Xs_gvn_Xh_all_ck
        fG_Xs_gvn_Xh = __get_fG_Xs_gvn_Xh_all_ck()

        zs_limits = __get_zs_integration_limits(zs)

        # --- Importance-sampling transform for ALL qmc variants ---
        # Compute conditional Gaussian f(xs|xh) parameters for IS.
        m_s_given_h_is = _get_mean_a_given_b(
            x_all_split, mean_all_split,
            cov_all_split, 's', 'h')
        cov_s_given_h_is = _get_sigma_a_given_b(
            cov_all_split, 's', 'h')
        # Ensure PSD
        _eigvals_is = np.linalg.eigvalsh(cov_s_given_h_is)
        if np.any(_eigvals_is < 0):
            _eps_is = max(abs(_eigvals_is.min()) * 2, 1e-12)
            cov_s_given_h_is += np.eye(cov_s_given_h_is.shape[0]) * _eps_is

        from scipy.special import erfinv as _erfinv_1
        _u1, _s1, _vh1 = _robust_svd(cov_s_given_h_is)
        _s1 = np.maximum(_s1, 1e-14)
        _A_is1_full = _vh1.T * np.sqrt(_s1)
        _mu_is1 = m_s_given_h_is.ravel()

        # --- PCA dimension reduction for _bme_posterior_pdf ---
        _pca_thr1 = options.get('pca_integration_threshold', 0.999) \
            if options is not None else 0.999
        _total_var1 = _s1.sum()
        if _total_var1 > 0 and _pca_thr1 < 1.0:
            _cumvar1 = np.cumsum(_s1) / _total_var1
            _ns_eff1 = int(np.searchsorted(_cumvar1, _pca_thr1) + 1)
            _ns_eff1 = max(1, min(_ns_eff1, ns))
        else:
            _ns_eff1 = ns

        if _ns_eff1 < ns:
            import warnings
            warnings.warn(
                "[PCA-pdf] Reducing QMC integration dimension from "
                "{ns} to {ne} (threshold={thr}, variance retained="
                "{vr:.4f})".format(
                    ns=ns, ne=_ns_eff1, thr=_pca_thr1,
                    vr=_s1[:_ns_eff1].sum() / _total_var1))
            _A_is1 = _A_is1_full[:, :_ns_eff1]
        else:
            _A_is1 = _A_is1_full

        _ns_qmc1 = _ns_eff1  # QMC integration dimension

        fS_Xs = _get_fs(zs)

        if options['integration method'] in ('qmc', 'qmc_T'):
            # Importance sampling: absorb Gaussian into sampling measure
            def __qmc_int_fG_Xs_gvn_Xh__fS_Xs(u_array):
                u_c = np.clip(u_array, 1e-6, 1.0 - 1e-6)
                z = np.sqrt(2.0) * _erfinv_1(2.0 * u_c - 1.0)
                xs_array = (_A_is1.dot(z.T) + _mu_is1.reshape(-1, 1)).T
                return fS_Xs(xs_array)
            xmin = np.zeros(_ns_qmc1)
            xmax = np.ones(_ns_qmc1)

        elif options['integration method'] == 'qmc_F':
            Fsinv = _get_Fsinv(zs)
            def __qmc_int_fG_Xs_gvn_Xh__fS_Xs(Fx_array):
                return fG_Xs_gvn_Xh(Fsinv(Fx_array))
            xmin = np.zeros(zs_limits[:,0].shape)
            xmax = np.ones(zs_limits[:,1].shape)

        else:
            # Fallback: unknown method → use IS as default
            def __qmc_int_fG_Xs_gvn_Xh__fS_Xs(u_array):
                u_c = np.clip(u_array, 1e-6, 1.0 - 1e-6)
                z = np.sqrt(2.0) * _erfinv_1(2.0 * u_c - 1.0)
                xs_array = (_A_is1.dot(z.T) + _mu_is1.reshape(-1, 1)).T
                return fS_Xs(xs_array)
            xmin = np.zeros(_ns_qmc1)
            xmax = np.ones(_ns_qmc1)

        int_fG_Xs_gvn_Xh__fS_Xs, e, info = qmc(
            __qmc_int_fG_Xs_gvn_Xh__fS_Xs,
            xmin, xmax,
            abserr=options[1,0],
            relerr=options[3,0],
            maxeval=int(options[2,0]),
            pow2min=10,
            showinfo=options['qmc_showinfo']
            )

        if int_fG_Xs_gvn_Xh__fS_Xs == 0 or np.isnan(int_fG_Xs_gvn_Xh__fS_Xs) or np.isinf(int_fG_Xs_gvn_Xh__fS_Xs):
            import warnings
            warnings.warn(
                "[STARBME] PDF normalization constant NC={:.4e} (ns={:d}). "
                "IS integration may have failed.  Posterior PDF values "
                "at these estimation locations may be unreliable.".format(
                    float(int_fG_Xs_gvn_Xh__fS_Xs), ns))
            # Set to a tiny positive value to avoid division-by-zero
            # downstream.  The posterior PDF will be nearly zero, but at
            # least it won't produce NaN.
            int_fG_Xs_gvn_Xh__fS_Xs = 1e-300


        def __get_fSk_Xk_each_ck(zsk):
            def fSk_Xk_each_ck(xk):
                if zsk is None:
                    return np.ones(xk.shape)
                else:
                    xk_origin_shape = xk.shape
                    xk = xk.flatten()
                    pdf_type = get_standard_soft_pdf_type(zsk[0])
                    if pdf_type == 2:
                        nl = zsk[1][0]
                        limi = zsk[2]
                        probdens = zsk[3]
                        y_i = np.interp(
                            xk, limi[:nl], probdens[:nl],
                            left = 0., right = 0.)
                    elif pdf_type == 1:
                        # BUG FIX: was using zs[1],zs[2],zs[3] (global list)
                        # instead of zsk[1],zsk[2],zsk[3] (individual soft datum)
                        nl = int(zsk[1][0])
                        limi = zsk[2]
                        probdens = zsk[3]
                        # Histogram PDF: probdens[j] is constant for limi[j] <= x < limi[j+1]
                        bin_idx = np.searchsorted(limi[:nl], xk, side='right') - 1
                        y_i = np.where(
                            (bin_idx >= 0) & (bin_idx < nl - 1),
                            probdens[np.clip(bin_idx, 0, nl - 2)],
                            0.0)
                    elif pdf_type == 10:
                        zm = zsk[1]
                        zstd = np.sqrt(zsk[2])
                        try:
                            y_i = scipy.stats.norm.pdf(
                                xk, loc=zm, scale=zstd)
                        except FloatingPointError:
                            y_i = np.zeros(xk.shape)
                      
                    return y_i.reshape(xk_origin_shape)
            return fSk_Xk_each_ck

        def __get_fG_Xs_gvn_Xkh_each_ck(ck_i, cs, zs,
            x_all_split_each_ck, mean_all_split_each_ck, cov_all_split_each_ck):
            idx_result = np.where(np.all(ck_i == cs, axis=1))[0]
            if idx_result.size == 0:
                x_all_split_each_ck_dup = x_all_split_each_ck
                mean_all_split_each_ck_dup = mean_all_split_each_ck
                cov_all_split_each_ck_dup = cov_all_split_each_ck
            elif idx_result.size == 1:
                x_all_split_each_ck_dup =\
                    x_all_split_each_ck[:2] +\
                    [np.delete(x_all_split_each_ck[2], idx_result, axis=0)]
                mean_all_split_each_ck_dup =\
                    mean_all_split_each_ck[:2] +\
                    [np.delete(mean_all_split_each_ck[2], idx_result, axis=0)]
                cov_all_split_each_ck_dup = copy.deepcopy(cov_all_split_each_ck)
                cov_all_split_each_ck_dup[0][2] =\
                    np.delete(cov_all_split_each_ck[0][2], idx_result, axis=1)
                cov_all_split_each_ck_dup[1][2] =\
                    np.delete(cov_all_split_each_ck[1][2], idx_result, axis=1)
                cov_all_split_each_ck_dup[2][0] =\
                    np.delete(cov_all_split_each_ck[2][0], idx_result, axis=0)
                cov_all_split_each_ck_dup[2][1] =\
                    np.delete(cov_all_split_each_ck[2][1], idx_result, axis=0)
                cov_all_split_each_ck_dup[2][2] =\
                    np.delete(cov_all_split_each_ck[2][2], idx_result, axis=0)
                #be careful below
                cov_all_split_each_ck_dup[2][2] =\
                    np.delete(cov_all_split_each_ck_dup[2][2], idx_result, axis=1)
            elif idx_result.size > 1: #strange
                raise ValueError('ck match cs twice. (strange)')
            def __get_fG_Xs_gvn_Xkh_each_ck_eack_xk(xk):
                fG_Xs_gvn_Xkh_container = []
                xk_origin_shape = xk.shape
                xk = xk.flatten()
                if options['integration method'] == 'qmc_T':
                    for xk_i in xk:
                        x_all_split_each_ck_dup[0] = np.array([[xk_i]])
                        m = _get_mean_a_given_b(
                            x_all_split_each_ck_dup,
                            mean_all_split_each_ck_dup,
                            cov_all_split_each_ck_dup, 's', 'kh')
                        v = _get_sigma_a_given_b(cov_all_split_each_ck_dup, 's', 'kh')
                        u, s, vh = _robust_svd(v)
                        A = vh.T*np.sqrt(s)

                        fG_Xs_gvn_Xkh_ = lambda xs, A=A, m=m: (A, m)

                        def fG_Xs_gvn_Xkh_each_ck_eack_xk(xs, ff):
                            xs_origin_shape = xs.shape
                            xs = xs.reshape(-1, xs_origin_shape[-1])
                            A, m = ff(xs)
                            xs[xs==0.] = 10**-5
                            xs[xs==1.] = 1 - 10**-5
                            xs2 = np.sqrt(2) * erfinv(2*xs - 1)
                            xs_array = (A.dot(xs2.T) + m).T
                            return xs_array

                        fG_Xs_gvn_Xkh_container.append(
                            lambda xs, ff=fG_Xs_gvn_Xkh_: fG_Xs_gvn_Xkh_each_ck_eack_xk(xs, ff))
                else:
                    for xk_i in xk:
                        x_all_split_each_ck_dup[0] = np.array([[xk_i]])
                        fG_Xs_gvn_Xkh_ = _get_multivariate_normal_pdf(
                        x_all_split_each_ck_dup,
                        mean_all_split_each_ck_dup,
                        cov_all_split_each_ck_dup, 's_kh')
                        def fG_Xs_gvn_Xkh_each_ck_eack_xk(xs, ff):
                            xs_origin_shape = xs.shape
                            xs = xs.reshape(-1, xs_origin_shape[-1])
                            output = ff(xs)
                            return output.reshape(xs_origin_shape[:-1]+(1,))
                        fG_Xs_gvn_Xkh_container.append(
                            lambda xs, ff=fG_Xs_gvn_Xkh_: fG_Xs_gvn_Xkh_each_ck_eack_xk(xs, ff))
                return np.array(
                    fG_Xs_gvn_Xkh_container).reshape(xk_origin_shape)
            return __get_fG_Xs_gvn_Xkh_each_ck_eack_xk

        def __get_fS_Xs_dup(ck_i, cs, zs):
            idx_result = np.where(np.all(ck_i == cs, axis=1))[0]
            if idx_result.size == 0:
                if options['integration method'] == 'qmc_F':
                    return Fsinv
                else:
                    return fS_Xs
            elif idx_result.size == 1:
                if options['integration method'] == 'qmc_F':
                    return _get_Fsinv(
                        [zs_i for i, zs_i in enumerate(zs) if i != idx_result])
                else:
                    return _get_fs(
                        [zs_i for i, zs_i in enumerate(zs) if i != idx_result])
            elif idx_result.size > 1: #strange
                raise ValueError('ck match cs twice. (strange)')

        def __get_pdf_each_ck(i):
            ck_i = ck[i]
            idx_result = np.where(np.all(ck_i == cs, axis=1))[0]
            if idx_result.size == 0:
                zs_dup = zs
            elif idx_result.size == 1:
                zs_dup = [zs_i for ii, zs_i in enumerate(zs) if ii != idx_result]
            elif idx_result.size > 1: #strange
                raise ValueError('ck match cs twice. (strange)')
            # Precompute IS parameters for the dup version if needed
            _is_dup_available = (idx_result.size == 0)
            # When no duplicate, zs_dup == zs and the IS parameters
            # from the first site (_A_is1, _mu_is1) apply directly.
            # When duplicate exists (idx_result.size == 1), dimensions
            # differ so we fall back to the original integration domain.

            def _fK_Xk(xk):
                xk_origin_shape = xk.shape
                xk = xk.flatten()
                zs_limits = __get_zs_integration_limits(zs_dup)
                if options['integration method'] == 'qmc':
                    if _is_dup_available:
                        # --- IS: absorb f(xs|xh) into sampling measure ---
                        # Integrand becomes f(xs|xk,xh)/f(xs|xh) * fS(xs)
                        # over [0,1]^ns_eff (IS with PCA-reduced f(xs|xh)).
                        def __qmc_int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup(u_array):
                            u_c = np.clip(u_array, 1e-6, 1.0 - 1e-6)
                            z = np.sqrt(2.0) * _erfinv_1(2.0 * u_c - 1.0)
                            x_array = (_A_is1.dot(z.T) + _mu_is1.reshape(-1, 1)).T
                            G_Xs_gvn_Xkh_dup_i = np.hstack(
                                [fi(x_array) for fi in fG_Xs_gvn_Xkh_dup[i](xk)])
                            fS_Xs_dup_i = fS_Xs_dup[i](x_array)
                            # Evaluate f(xs|xh) for IS correction
                            fG_Xs_gvn_Xh_val = fG_Xs_gvn_Xh(x_array)
                            # Ratio = f(xs|xk,xh) * fS(xs) / f(xs|xh)
                            return G_Xs_gvn_Xkh_dup_i * fS_Xs_dup_i / (fG_Xs_gvn_Xh_val + 1e-300)
                        xmin = np.zeros(_ns_qmc1)
                        xmax = np.ones(_ns_qmc1)
                    else:
                        # Dup case: dimensions differ, use original integration domain
                        def __qmc_int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup(x_array):
                            G_Xs_gvn_Xkh_dup_i =\
                                np.hstack(
                                    [fi(x_array) for fi in fG_Xs_gvn_Xkh_dup[i](xk)])
                            fS_Xs_dup_i = fS_Xs_dup[i](x_array)
                            return G_Xs_gvn_Xkh_dup_i * fS_Xs_dup_i
                        xmin = zs_limits[:,0].copy()
                        xmax = zs_limits[:,1].copy()

                elif options['integration method'] == 'qmc_F':
                    def __qmc_int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup(Fx_array):
                        G_Xs_gvn_Xkh_dup_i =\
                            np.hstack(
                                [fi(fS_Xs_dup[i](Fx_array)) for fi in fG_Xs_gvn_Xkh_dup[i](xk)])
                        return G_Xs_gvn_Xkh_dup_i
                    xmin = np.zeros(zs_limits[:,0].shape)
                    xmax = np.ones(zs_limits[:,1].shape)

                elif options['integration method'] == 'qmc_T':
                    def __qmc_int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup(Fx_array):
                        G_Xs_gvn_Xkh_dup_i =\
                            [fi(Fx_array) for fi in fG_Xs_gvn_Xkh_dup[i](xk)]
                        fS_Xs_dup_i =\
                            np.hstack(
                                [fS_Xs_dup[i](xs_array_i) for xs_array_i in G_Xs_gvn_Xkh_dup_i] )
                        return fS_Xs_dup_i
                    xmin = np.zeros(zs_limits[:,0].shape)
                    xmax = np.ones(zs_limits[:,1].shape)

                int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup , e, info = qmc(
                    __qmc_int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup,
                    xmin, xmax,
                    abserr=options[1,0],
                    relerr=options[3,0],
                    maxeval=int(options[2,0]),
                    pow2min=10,
                    showinfo=options['qmc_showinfo']
                    )
                int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup =\
                    int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup.reshape(xk_origin_shape)
                xk = xk.reshape(xk_origin_shape)
                if options['ck pdf debug']:
                    print('fG_Xkh[i](xk):', fG_Xkh[i](xk))
                    print('fSk_Xk[i](xk):', fSk_Xk[i](xk))
                    print('int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup:', int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup)
                    print('fG_Xh:', fG_Xh)
                    print('int_fG_Xs_gvn_Xh__fS_Xs:', int_fG_Xs_gvn_Xh__fS_Xs)
                    
                return (fG_Xkh[i](xk) * fSk_Xk[i](xk)
                    * int_fG_Xs_gvn_Xkh_dup__fS_Xs_dup
                    / fG_Xh / int_fG_Xs_gvn_Xh__fS_Xs)
            return _fK_Xk

        cov_hs_range = range(nk, nk+nh+ns)
        
        fG_Xkh = [] # a list contains each ck's fG_Xkh
        fSk_Xk = [] # a list contains each ck's fSk_Xk
        fS_Xs_dup = []
        fG_Xs_gvn_Xkh_dup = [] # a list contains each ck's fG_Xs_gvn_Xkh_dup
        fK_Xk = []
        for i in range(nk):
            #get x/mean/cov_all_split at each ck point
            x_all_split_each_ck =\
                [x_all_split[0][i:i+1,:]] + x_all_split[1:]
            mean_all_split_each_ck =\
                [mean_all_split[0][i:i+1,:]] + mean_all_split[1:]
            covmat_each_ck =\
                covmat[np.ix_(
                    [i]+cov_hs_range,
                    [i]+cov_hs_range
                    )]
            cov_all_split_each_ck = np.vsplit(
                covmat_each_ck, [1, 1+nh, 1+nh+ns]
                )[:-1] #exclude final empty array
            cov_all_split_each_ck = \
                [np.hsplit(c, [1, 1+nh, 1+nh+ns][:-1])\
                for c in cov_all_split_each_ck]

            # get fG_Xkh each ck part
            fG_Xkh_ = _get_multivariate_normal_pdf(
                x_all_split_each_ck,
                mean_all_split_each_ck,
                cov_all_split_each_ck, 'kh')
            fG_Xkh.append(
                __get_fG_Xkh_each_ck(fG_Xkh_))

            # get fSk_Xk
            idx_result = np.where(np.all(ck[i] == cs, axis=1))[0]
            if idx_result.size == 0:
                fSk_Xk.append(__get_fSk_Xk_each_ck(None))
            elif idx_result.size == 1:
                fSk_Xk.append(__get_fSk_Xk_each_ck(zs[idx_result[0]]))
            elif idx_result.size > 1: #strange
                raise ValueError('ck match cs twice. (strange)')

            # get fS_Xs_dup
            fS_Xs_dup.append(__get_fS_Xs_dup(ck[i], cs, zs))

            # get fG_Xs_gvn_Xkh
            fG_Xs_gvn_Xkh_dup.append(
                __get_fG_Xs_gvn_Xkh_each_ck(ck[i], cs, zs,
                    x_all_split_each_ck,
                    mean_all_split_each_ck,
                    cov_all_split_each_ck))

            fK_Xk.append(__get_pdf_each_ck(i))

        return np.array([fK_Xk]).reshape((-1, 1))
    else: #general knowledge is not gaussian
        pass

def _bme_posterior_moments(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None,
    general_knowledge='gaussian',
    #  specific_knowledge='unknown',
    pdfk=None, pdfh=None, pdfs=None, hk_k=None, hk_h=None, hk_s=None,
    gui_args=None, ck_cov_output=False):

    '''
        no neighbour considered, so spatial-temporal range
        should be transform first (no dmax support).

        covmat:
            covariance matrix, a np 2d array
            with shape (nk+nh+ns) by (nk+nh+ns)
        if covmat provieded, covmodel and covparam are simply skipped.
    '''

    if general_knowledge == 'gaussian':
        if zs:
            # --- Fast Gaussian Approximation ---
            # When enabled, convert non-Gaussian soft PDFs (histogram/linear)
            # to Gaussian (mean, variance) so the fast analytical path is used
            # instead of the expensive QMC integration.
            _use_gauss_approx = (
                options is not None and options['soft_approx_gaussian'])

            # --- Auto-Gaussian fallback for very high dimensions ---
            # When the number of non-Gaussian soft data in the
            # neighbourhood exceeds a threshold, even importance-sampling
            # QMC can struggle because the integrand fs(xs) in
            # high-dimensional space still requires many samples.
            # In that case, automatically approximate non-Gaussian
            # soft PDFs as Gaussian and use the fast analytical path.
            _NS_AUTO_GAUSS = 20  # threshold for auto-approximation
            if not _use_gauss_approx:
                _ns_nongauss = sum(
                    1 for zsi in zs
                    if get_standard_soft_pdf_type(zsi[0]) != 10)
                if _ns_nongauss > _NS_AUTO_GAUSS:
                    import warnings
                    warnings.warn(
                        "ns_nongaussian={} exceeds auto-Gaussian threshold "
                        "({}). Approximating non-Gaussian soft PDFs as "
                        "Gaussian for numerical stability.".format(
                            _ns_nongauss, _NS_AUTO_GAUSS))
                    _use_gauss_approx = True

            if _use_gauss_approx:
                zs_converted = []
                for zsi in zs:
                    pdftype = get_standard_soft_pdf_type(zsi[0])
                    if pdftype in [1, 2]:  # histogram or linear -> convert
                        zs_gau_m, zs_gau_v = proba2stat(
                            zsi[0],
                            np.array([zsi[1]]),
                            np.array([zsi[2]]),
                            np.array([zsi[3]])
                        )
                        zs_converted.append(
                            (10, float(np.asarray(zs_gau_m).flat[0]),
                             float(np.asarray(zs_gau_v).flat[0])))
                    else:
                        zs_converted.append(zsi)
                zs = zs_converted

            all_zs_type = np.array(
                [get_standard_soft_pdf_type(zsi[0]) for zsi in zs]
                )
            if (all_zs_type==10).all(): # all soft type are gaussian
                # --- Covariance-based near-duplicate detection ---
                # Use row-correlation of the covariance matrix (unit-free)
                # instead of exact coordinate equality.
                nk_g = ck.shape[0]
                nh_g = ch.shape[0] if ch is not None else 0
                ns_g = cs.shape[0] if cs is not None else 0
                if covmat is not None:
                    _covmat_g = covmat
                else:
                    _cov_tmp_g = _get_cov_all_split(
                        ck, ch, cs, covmodel, covparam)
                    _rows_g = [np.hstack([b for b in row if b is not None])
                               for row in _cov_tmp_g]
                    _covmat_g = np.vstack(_rows_g)
                _ck_dup_g, _cs_dup_g, _rank_def_g = \
                    _find_ck_cs_near_duplicates(
                        _covmat_g, nk_g, nh_g, ns_g)

                # Also check exact equality as before (catches the exact case
                # even if corrcoef has numerical noise)
                _exact_dup = np.where((ck==cs[:,None]).all(-1))[1]
                dup_index = np.unique(np.concatenate(
                    [_ck_dup_g, _exact_dup]))

                if dup_index.size > 0: #has duplicated point
                    if not ck_cov_output:
                        mask = np.ones(ck.shape[0], dtype=bool)
                        mask[dup_index] = False
                        mvs = np.empty((ck.shape[0],3))
                        mvs[:] = np.nan
                        ck_dup = ck[dup_index, :]
                        ck_no_dup = ck[mask]
                        mvs[dup_index, :] =\
                            _bme_proba_gaussian_dup(
                                ck_dup, ch, cs, zh, zs,
                                covmodel, covparam, covmat, order, options)
                        if ck_no_dup.size > 0:
                            if covmat is not None:
                                _keep_g = np.concatenate([
                                    np.where(mask)[0],
                                    np.arange(nk_g, nk_g + nh_g),
                                    np.arange(nk_g + nh_g,
                                              nk_g + nh_g + ns_g)])
                                covmat_no_dup = covmat[
                                    np.ix_(_keep_g, _keep_g)]
                            else:
                                covmat_no_dup = None
                            mvs[mask, :] =\
                                _bme_proba_gaussian(
                                    ck_no_dup, ch, cs, zh, zs,
                                    covmodel, covparam, covmat_no_dup,
                                    order, options)
                        return mvs
                    else:
                        raise ValueError('We can not do ck_cov_output with duplicated point.')
                else:
                    if not ck_cov_output:
                        mvs = _bme_proba_gaussian(
                            ck, ch, cs, zh, zs,
                            covmodel, covparam, covmat, order, options)
                        return mvs
                    else:
                        mvs, ckcov = _bme_proba_gaussian(
                            ck, ch, cs, zh, zs,
                            covmodel, covparam, covmat, order, options, ck_cov_output)
                        return mvs, ckcov
            else: # has non-gaussian
                nk = ck.shape[0]
                nh = ch.shape[0] if ch is not None else 0
                ns = cs.shape[0] if cs is not None else 0

                # ============================================================
                # COVARIANCE-BASED NEAR-DUPLICATE DETECTION (unit-free)
                # ============================================================
                # When ck ≈ cs_i, the covariance matrix loses rank because
                # their rows become nearly identical. We detect this via
                # np.corrcoef (Pearson row-correlation), which is dimensionless.
                # Near-duplicate ck's are routed to the analytical Gaussian
                # dup path; the remaining ck's proceed with QMC IS.
                # ============================================================
                if covmat is not None:
                    _covmat_for_check = covmat
                else:
                    _cov_tmp = _get_cov_all_split(
                        ck, ch, cs, covmodel, covparam)
                    _rows = [np.hstack([b for b in row if b is not None])
                             for row in _cov_tmp]
                    _covmat_for_check = np.vstack(_rows)

                _ck_dup_idx, _cs_dup_partner, _is_rank_def = \
                    _find_ck_cs_near_duplicates(
                        _covmat_for_check, nk, nh, ns)

                if _ck_dup_idx.size > 0:
                    import warnings
                    warnings.warn(
                        "[STARBME] Covariance-based near-duplicate detection: "
                        "{} ck point(s) nearly co-located with cs. "
                        "Routing to analytical dup path.".format(
                            _ck_dup_idx.size))

                    # Convert non-Gaussian soft data to Gaussian for the
                    # analytical dup path
                    zs_gauss_dup = []
                    for zsi in zs:
                        pdftype = get_standard_soft_pdf_type(zsi[0])
                        if pdftype == 10:
                            zs_gauss_dup.append(zsi)
                        else:
                            zs_gau_m, zs_gau_v = proba2stat(
                                zsi[0],
                                np.array([zsi[1]]),
                                np.array([zsi[2]]),
                                np.array([zsi[3]]))
                            zs_gauss_dup.append(
                                (10, float(np.asarray(zs_gau_m).flat[0]),
                                 float(np.asarray(zs_gau_v).flat[0])))

                    _nondup_mask = np.ones(nk, dtype=bool)
                    _nondup_mask[_ck_dup_idx] = False

                    mvs = np.empty((nk, 4))
                    mvs[:] = np.nan
                    mvs[:, 3] = 0.0  # default delta_mu=0

                    # --- Dup ck's: analytical Gaussian dup path (delta_mu=0) ---
                    mvs[_ck_dup_idx, :3] = _bme_proba_gaussian_dup(
                        ck[_ck_dup_idx], ch, cs, zh, zs_gauss_dup,
                        covmodel, covparam, covmat, order, options)

                    # --- Non-dup ck's: QMC IS (recursive call) ---
                    if _nondup_mask.any():
                        ck_nondup = ck[_nondup_mask]
                        if covmat is not None:
                            # Rebuild covmat without the dup ck rows/cols
                            _keep = np.concatenate([
                                np.where(_nondup_mask)[0],           # ck
                                np.arange(nk, nk + nh),             # ch
                                np.arange(nk + nh, nk + nh + ns)])  # cs
                            covmat_nondup = covmat[np.ix_(_keep, _keep)]
                        else:
                            covmat_nondup = None
                        mvs_nondup = _bme_posterior_moments(
                            ck_nondup, ch, cs, zh, zs,
                            covmodel, covparam, covmat_nondup,
                            order, options, general_knowledge,
                            pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
                            gui_args, ck_cov_output=False)
                        # mvs_nondup may be 3-col (Gaussian) or 4-col (QMC)
                        if mvs_nondup.shape[1] == 4:
                            mvs[_nondup_mask] = mvs_nondup
                        else:
                            mvs[_nondup_mask, :3] = mvs_nondup

                    if not ck_cov_output:
                        return mvs
                    else:
                        # For ck_cov_output, fall back to Gaussian approx
                        zs_gau_all = []
                        for zsi in zs:
                            zs_gau_m, zs_gau_v = proba2stat(
                                zsi[0],
                                np.array([zsi[1]]),
                                np.array([zsi[2]]),
                                np.array([zsi[3]]))
                            zs_gau_all.append((10, zs_gau_m, zs_gau_v))
                        _, ckcov = _bme_proba_gaussian(
                            ck, ch, cs, zh, zs_gau_all,
                            covmodel, covparam, covmat,
                            order, options, ck_cov_output=True)
                        return mvs, ckcov

                # If rank-deficient but no ck-cs dups, regularise covmat
                if _is_rank_def and covmat is not None:
                    _eigvals_cm = np.linalg.eigvalsh(covmat)
                    _eps_cm = max(abs(min(_eigvals_cm.min(), 0)) * 2, 1e-12)
                    covmat = covmat + np.eye(covmat.shape[0]) * _eps_cm

                x_all_split = _get_x_all_split(nk, zh, zs)
                mean_all_split = _get_mean_all_split(x_all_split, order)
                if covmat is not None:
                    cov_all_split = np.vsplit(
                        covmat, [nk, nk+nh, nk+nh+ns]
                        )[:-1] #exclude final empty array
                    cov_all_split = \
                        [np.hsplit(c, [nk, nk+nh, nk+nh+ns][:-1])\
                        for c in cov_all_split]
                else:
                    cov_all_split = _get_cov_all_split(
                        ck, ch, cs, covmodel, covparam)

                # --- Compute conditional Gaussian f(xs|xh) ---
                # Used for (a) importance-sampling transform, and
                # (b) fallback clipped-box integration when ns == 1.
                m_s_given_h = _get_mean_a_given_b(
                    x_all_split, mean_all_split,
                    cov_all_split, 's', 'h')
                cov_s_given_h = _get_sigma_a_given_b(
                    cov_all_split, 's', 'h')
                # --- FIX B: Eigenvalue floor for cov_s_given_h ---
                # Not just fixing negatives — near-zero eigenvalues make
                # pinv(cov_s_given_h) huge, so the Fused-Gaussian proposal
                # is dominated by the prior and ignores the soft data.
                # A proportional floor keeps the proposal balanced.
                _eigvals = np.linalg.eigvalsh(cov_s_given_h)
                _min_eigval_floor = max(_eigvals.max() * 1e-8, 1e-12)
                if np.any(_eigvals < _min_eigval_floor):
                    _eps = _min_eigval_floor - min(_eigvals.min(), 0)
                    cov_s_given_h += np.eye(cov_s_given_h.shape[0]) * _eps

                fs = _get_fs(zs)

                #split hard and soft of m_k_gvn_hs
                m_k = _get_mean(mean_all_split, 'k')
                # --- FIX A: Regularise Σ_{hs,hs} before inversion ---
                # When data locations are close together the joint
                # covariance matrix Σ_{hs,hs} becomes ill-conditioned.
                # An ill-conditioned pinv amplifies noise in xs,
                # making m_k|hs swing wildly (key cause of low/NaN
                # estimates even for small ns).
                _sigma_hs_hs = _get_sigma(cov_all_split, 'hs', 'hs')
                _cond_hs = np.linalg.cond(_sigma_hs_hs)
                if _cond_hs > 1e10:
                    _eigvals_hs = np.linalg.eigvalsh(_sigma_hs_hs)
                    _floor_hs = max(_eigvals_hs.max() * 1e-10, 1e-12)
                    _sigma_hs_hs = (
                        _sigma_hs_hs
                        + np.eye(_sigma_hs_hs.shape[0]) * _floor_hs
                    )
                _inv_sigma_hs_hs = _robust_pinv(_sigma_hs_hs)
                Bm_sigma_inv_multi = (
                    _get_sigma(cov_all_split, 'k', 'hs').dot(
                        _inv_sigma_hs_hs)
                    )
                m_hs = _get_mean(mean_all_split, 'hs')
                m_k_gvn_hs_part = m_k - Bm_sigma_inv_multi.dot(m_hs)
                x_hs = _get_x(x_all_split, 'hs') #put true Xs later

                sigma_k_given_hs = _get_sigma_a_given_b(
                    cov_all_split, 'k', 'hs')
                diag_sigma_k_given_hs =\
                    np.diag(sigma_k_given_hs)

                # ============================================================
                # IMPORTANCE-SAMPLING QMC INTEGRATION (Fused Gaussian Proposal)
                # ============================================================
                # The integral is I = ∫ g(xs) · f(xs|xh) · fs(xs) dxs
                #
                # IMPROVED PROPOSAL ("Fused Gaussian"):
                # We approximate fs(xs) as N(μ_soft, Σ_soft) and construct
                #   q(xs) ∝ f(xs|xh) · N(μ_soft, Σ_soft)  =  N(μ_IS, Σ_IS)
                # where:
                #   Σ_IS^{-1} = Σ_{s|h}^{-1} + Σ_soft^{-1}
                #   μ_IS      = Σ_IS (Σ_{s|h}^{-1} μ_{s|h} + Σ_soft^{-1} μ_soft)
                #
                # KEY IDENTITY:  f_prior(x)/q(x) = Z_fused / N_soft_approx(x)
                # where Z_fused is a constant that cancels in Mon/Mon_NC.
                # So the IS weight simplifies to:
                #   w(x) = fs(x) / N_soft_approx(x)
                # This avoids ALL multivariate logpdf computations.
                # ============================================================
                from scipy.special import erfinv as _erfinv

                # 1. Approximate each soft datum as Gaussian (mean, variance)
                _mu_soft_list = []
                _var_soft_list = []
                for zsi in zs:
                    if get_standard_soft_pdf_type(zsi[0]) == 10:  # Gaussian
                        _mu_soft_list.append(float(np.asarray(zsi[1]).flat[0]))
                        _var_soft_list.append(float(np.asarray(zsi[2]).flat[0]))
                    else:
                        _m, _v = proba2stat(
                            zsi[0], np.array([zsi[1]]),
                            np.array([zsi[2]]), np.array([zsi[3]]))
                        _mu_soft_list.append(float(np.asarray(_m).flat[0]))
                        _var_soft_list.append(float(np.asarray(_v).flat[0]))

                _mu_soft = np.array(_mu_soft_list)          # (ns,)
                _var_soft = np.maximum(np.array(_var_soft_list), 1e-14)  # (ns,)
                _sigma_soft = np.sqrt(_var_soft)             # (ns,)

                # 2. Calculate Fused Gaussian Parameters (μ_IS, Σ_IS)
                _prec_prior = _robust_pinv(cov_s_given_h)
                _prec_soft = np.diag(1.0 / _var_soft)

                _cov_IS = _robust_pinv(_prec_prior + _prec_soft)

                # Ensure _cov_IS is PSD
                _eigvals_is = np.linalg.eigvalsh(_cov_IS)
                if np.any(_eigvals_is < 0):
                    _eps_is = max(abs(_eigvals_is.min()) * 2, 1e-12)
                    _cov_IS += np.eye(_cov_IS.shape[0]) * _eps_is

                _term_prior = _prec_prior.dot(m_s_given_h)
                _term_soft = (_mu_soft / _var_soft).reshape(-1, 1)
                _mu_IS = _cov_IS.dot(_term_prior + _term_soft)

                # 3. SVD factorisation of Σ_IS (for sampling)
                _u_svd, _s_svd, _vh_svd = _robust_svd(_cov_IS)
                _s_svd = np.maximum(_s_svd, 1e-14)
                _A_is_full = _vh_svd.T * np.sqrt(_s_svd)
                _mu_is_ravel = _mu_IS.ravel()

                # --------------------------------------------------------
                # PCA DIMENSION REDUCTION (on Σ_IS)
                # --------------------------------------------------------
                _pca_thr = options.get('pca_integration_threshold', 0.999)
                _total_var = _s_svd.sum()
                if _total_var > 0 and _pca_thr < 1.0:
                    _cumvar = np.cumsum(_s_svd) / _total_var
                    _ns_eff = int(np.searchsorted(_cumvar, _pca_thr) + 1)
                    _ns_eff = max(1, min(_ns_eff, ns))
                else:
                    _ns_eff = ns

                if _ns_eff < ns:
                    _A_is = _A_is_full[:, :_ns_eff]
                else:
                    _A_is = _A_is_full

                _ns_qmc = _ns_eff

                # Non-negativity inside the QMC integrand is DISABLED.
                # The full truncated-normal mean  μ_T = μ + σλ  inflates
                # near-zero estimates to ~0.8σ ("yellow floor" artifact)
                # in data-sparse regions where μ ≈ 0 but σ is large.
                # Instead, _apply_nonneg_truncation handles nonneg
                # post-hoc with zero-clamping for mean + truncated-normal
                # variance, avoiding the constant-background problem.
                _nonneg_in_integrand = False

                # Pre-compute σ_{k|hs} per estimation point (for truncation)
                if _nonneg_in_integrand:
                    _sigma_khs_vec = np.sqrt(
                        np.maximum(diag_sigma_k_given_hs, 1e-30)
                    ).reshape(1, -1)  # (1, nk)

                def func_moments_is(u_array):
                    """Importance-sampling integrand over [0,1]^ns_eff.

                    Samples xs from the Fused Gaussian q(xs) = N(μ_IS, Σ_IS).
                    The IS weight is w(xs) = ∏_i f_{s,i}(x_i) / N_soft_i(x_i).
                    Computed PER-COMPONENT in log-space to avoid product
                    underflow (Fix C).  The Z_fused constant cancels in
                    Mon/Mon_NC.

                    When _nonneg_in_integrand is True, replaces the raw
                    conditional moments with truncated-normal moments
                    (Z_k ≥ 0) at each sample point, so the final QMC
                    integral directly gives E[Z|data, Z≥0] and
                    Var[Z|data, Z≥0].
                    """
                    nMon = 3
                    npts = u_array.shape[0]

                    # --- Transform [0,1]^ns_eff → N(μ_IS, Σ_IS) ---
                    u_clamped = np.clip(u_array, 1e-6, 1.0 - 1e-6)
                    z_std = np.sqrt(2.0) * _erfinv(2.0 * u_clamped - 1.0)
                    x_array = (_A_is.dot(z_std.T) + _mu_is_ravel.reshape(-1, 1)).T

                    if _nonneg_in_integrand:
                        # Per-point NC: 3 moment columns × nk + nk NC columns
                        res = np.empty((npts, nMon * nk + nk))
                    else:
                        # Shared NC: 3 moment columns × nk + 1 shared NC column
                        res = np.empty((npts, nMon * nk + 1))

                    x_hs_npts = np.tile(x_hs, (1, npts))
                    x_hs_npts[nh:, :] = x_array.T

                    m_k_gvn_hs_npts = (
                        m_k_gvn_hs_part + Bm_sigma_inv_multi.dot(x_hs_npts)
                    ).T

                    # --- FIX C: Per-component log-space IS weight ---
                    # log w(x) = Σ_i [ log f_{s,i}(x_i) - log N_soft_i(x_i) ]
                    # where N_soft_i is the 1-D Gaussian approximation of
                    # soft datum i.  Each ratio f_{s,i}/N_soft_i is O(1),
                    # so the sum of logs is well-behaved even for large ns.
                    log_weight = np.zeros(npts)
                    valid = np.ones(npts, dtype=bool)
                    _log_2pi = np.log(2.0 * np.pi)

                    for _i_s, _zsi in enumerate(zs):
                        _xi = x_array[:, _i_s]  # (npts,)

                        # Evaluate 1-D soft PDF f_{s,i}(x_i)
                        _ptype = get_standard_soft_pdf_type(_zsi[0])
                        if _ptype == 2:   # linear
                            _nl = int(_zsi[1][0])
                            _y = np.interp(
                                _xi, _zsi[2][:_nl], _zsi[3][:_nl],
                                left=0.0, right=0.0)
                        elif _ptype == 1:  # histogram
                            _nl = int(_zsi[1][0])
                            _limi = _zsi[2]
                            _pd = _zsi[3]
                            _bidx = np.searchsorted(
                                _limi[:_nl], _xi, side='right') - 1
                            _y = np.where(
                                (_bidx >= 0) & (_bidx < _nl - 1),
                                _pd[np.clip(_bidx, 0, _nl - 2)], 0.0)
                        elif _ptype == 10:  # Gaussian soft
                            _zm = _zsi[1]
                            _zstd = np.sqrt(_zsi[2])
                            _y = scipy.stats.norm.pdf(
                                _xi, loc=_zm, scale=_zstd)
                        else:
                            _y = np.ones(npts)

                        # Points where f_{s,i} = 0 → total weight = 0
                        _ok = _y > 0
                        valid &= _ok

                        # Accumulate log(f_{s,i}) - log(N_soft_i)
                        # log(N_soft_i) = -0.5*((x-μ)/σ)² - log(σ√(2π))
                        _d = (_xi - _mu_soft[_i_s]) / _sigma_soft[_i_s]
                        _log_n = (-0.5 * _d**2
                                  - np.log(_sigma_soft[_i_s])
                                  - 0.5 * _log_2pi)

                        # Only accumulate where f_{s,i} > 0 (avoid log(0))
                        log_weight[_ok] += np.log(_y[_ok]) - _log_n[_ok]
                        # Where _ok is False, this point is already dead
                        # (valid=False), so the value doesn't matter.

                    # Clip and exponentiate
                    log_weight = np.clip(log_weight, -500, 500)
                    total_weight = np.where(
                        valid, np.exp(log_weight), 0.0
                    ).reshape(npts, 1)

                    if _nonneg_in_integrand:
                        # --------------------------------------------------
                        # TRUNCATED-NORMAL moments at each sample (Z_k ≥ 0)
                        # --------------------------------------------------
                        # For Z_k|xs,xh ~ N(μ, σ²), truncated to [0,∞):
                        #   α   = −μ/σ
                        #   Φ₊  = Φ(μ/σ) = P(Z ≥ 0)
                        #   λ   = φ(α)/Φ₊           (inverse Mills ratio)
                        #   δ   = λ(λ−α)            (variance reduction)
                        #   μ_T = μ + σλ
                        #   σ²_T = σ²(1−δ)
                        #   E[Z²|Z≥0] = σ²_T + μ_T²
                        # --------------------------------------------------
                        _alpha = -m_k_gvn_hs_npts / _sigma_khs_vec
                        _Phi_pos = scipy.stats.norm.cdf(
                            m_k_gvn_hs_npts / _sigma_khs_vec)
                        _phi_alpha = scipy.stats.norm.pdf(_alpha)

                        # Safe inverse Mills ratio (avoid div-by-zero)
                        _safe_Phi = np.maximum(_Phi_pos, 1e-12)
                        _lam = _phi_alpha / _safe_Phi
                        _delta = _lam * (_lam - _alpha)

                        _mu_trunc = (
                            m_k_gvn_hs_npts + _sigma_khs_vec * _lam)
                        _var_trunc = (
                            diag_sigma_k_given_hs.reshape(1, -1)
                            * np.maximum(1.0 - _delta, 0.0))

                        # Where almost no mass above 0, clamp to 0
                        _dead = _Phi_pos < 1e-12
                        _mu_trunc = np.where(_dead, 0.0, _mu_trunc)
                        _var_trunc = np.where(_dead, 0.0, _var_trunc)

                        # Φ₊-weighted IS weight per estimation point.
                        # The correct truncated integrals are:
                        #   E[Z|data,Z≥0] = E_q[μ_T · Φ₊ · w] / E_q[Φ₊ · w]
                        #   E[Z²|data,Z≥0] = E_q[(σ²_T+μ_T²) · Φ₊ · w] / E_q[Φ₊ · w]
                        # where Φ₊ = P(Z_k≥0 | xs, xh) depends on k.
                        _tw_nonneg = total_weight * _Phi_pos  # (npts, nk)

                        # E[Z|Z≥0] · Φ₊ · w
                        res[:, 0*nk:1*nk] = _mu_trunc * _tw_nonneg
                        # E[Z²|Z≥0] · Φ₊ · w
                        res[:, 1*nk:2*nk] = (
                            (_var_trunc + _mu_trunc**2) * _tw_nonneg)
                        # Skewness (set to 0)
                        res[:, 2*nk:3*nk] = 0.0
                        # Per-point NC: Φ₊ · w  (nk columns)
                        res[:, 3*nk:4*nk] = _tw_nonneg
                    else:
                        res[:, 0*nk:1*nk] = (
                            m_k_gvn_hs_npts * total_weight)
                        res[:, 1*nk:2*nk] = (
                            res[:, :nk] * m_k_gvn_hs_npts)
                        res[:, 2*nk:3*nk] = (
                            3 * diag_sigma_k_given_hs * res[:, :nk]
                            - 2 * res[:, nk:2*nk] * m_k_gvn_hs_npts)
                        # Shared NC (one column)
                        res[:, -1:] = total_weight
                    return res

                # QMC integration over the unit cube [0,1]^ns_eff
                xmin = np.zeros(_ns_qmc)
                xmax = np.ones(_ns_qmc)

                Mon, e, info = qmc(
                    func_moments_is, xmin, xmax,
                    abserr=options[1,0],
                    relerr=options[3,0],
                    maxeval=int(options[2,0]),
                    showinfo=options['qmc_showinfo'])

                # =============================================================
                # Helper: Gaussian fallback (used by both NC paths)
                # =============================================================
                def _gauss_fallback(reason_msg):
                    import warnings
                    warnings.warn(reason_msg)
                    zs_gauss_fb = []
                    for zsi in zs:
                        pdftype = get_standard_soft_pdf_type(zsi[0])
                        if pdftype == 10:
                            zs_gauss_fb.append(zsi)
                        else:
                            zs_gau_m, zs_gau_v = proba2stat(
                                zsi[0],
                                np.array([zsi[1]]),
                                np.array([zsi[2]]),
                                np.array([zsi[3]]))
                            zs_gauss_fb.append(
                                (10, float(np.asarray(zs_gau_m).flat[0]),
                                 float(np.asarray(zs_gau_v).flat[0])))
                    mvs_fb = _bme_proba_gaussian(
                        ck, ch, cs, zh, zs_gauss_fb,
                        covmodel, covparam, covmat,
                        order, options, ck_cov_output)
                    return mvs_fb

                # =============================================================
                # Helper: covariance output via Gaussian
                # =============================================================
                def _cov_output_from_gaussian():
                    zs_gau = []
                    for zsi in zs:
                        zs_gau_m, zs_gau_v = proba2stat(
                            zsi[0],
                            np.array([zsi[1]]),
                            np.array([zsi[2]]),
                            np.array([zsi[3]]))
                        zs_gau.append((10, zs_gau_m, zs_gau_v))
                    _mvs22, _ckcov22 = _bme_proba_gaussian(
                        ck, ch, cs, zh, zs_gau,
                        covmodel, covparam, covmat,
                        order, options, ck_cov_output)
                    return _ckcov22

                if _nonneg_in_integrand:
                    # =========================================================
                    # Nonneg path: per-point NC from Φ₊-weighted integrand
                    # Mon has 4*nk elements: 3*nk moments + nk per-point NCs
                    # =========================================================
                    Mon_NC_per_k = Mon[3*nk:4*nk]        # (nk,)
                    e_NC_per_k   = e[3*nk:4*nk]          # (nk,)

                    # Guard: fall back if worst per-point NC is bad
                    _nc_min = np.nanmin(Mon_NC_per_k)
                    _nc_max_err = np.nanmax(e_NC_per_k)
                    if (_nc_min == 0
                            or np.any(np.isnan(Mon_NC_per_k))
                            or np.any(np.isinf(Mon_NC_per_k))
                            or _nc_min < 3.0 * _nc_max_err
                            or _nc_min < 1e-100):
                        return _gauss_fallback(
                            "[STARBME] QMC nonneg per-point NC min={:.4e} "
                            "+/- {:.4e} (ns={:d}). Falling back to Gaussian "
                            "approximation.".format(
                                float(_nc_min), float(_nc_max_err), ns))

                    # Normalise moments per point
                    Mon_mom = Mon[:3*nk].reshape((3, nk)).T  # (nk, 3)
                    e_mom   = e[:3*nk].reshape((3, nk)).T    # (nk, 3)
                    for j in range(nk):
                        Mon_mom[j, :] /= Mon_NC_per_k[j]

                    M1 = Mon_mom[:, 0:1]
                    M2 = Mon_mom[:, 1:2]

                    # Per-point error propagation
                    _delta_mu = np.zeros((nk, 1))
                    for j in range(nk):
                        _nc_j = Mon_NC_per_k[j]
                        _delta_mu[j, 0] = np.sqrt(
                            (e_mom[j, 0] / _nc_j) ** 2
                            + (M1[j, 0] * e_NC_per_k[j] / _nc_j) ** 2)

                    mvs = np.empty((nk, 4))
                    mvs[:, 0:1] = M1
                    mvs[:, 1:2] = np.maximum(
                        M2 - M1**2 - _delta_mu**2, 0.0)
                    mvs[:, 2:3] = 0.0
                    mvs[:, 3:4] = -1.0  # flag: nonneg already applied

                    if not ck_cov_output:
                        return mvs
                    else:
                        return mvs, _cov_output_from_gaussian()

                else:
                    # =========================================================
                    # Standard path: shared NC (single column)
                    # =========================================================
                    Mon_NC = Mon[-1]
                    Mon_NC_err = e[-1]
                    # Guard against zero / NaN / Inf normalisation constant
                    if (Mon_NC == 0 or np.isnan(Mon_NC) or np.isinf(Mon_NC) or
                            Mon_NC < 3 * Mon_NC_err or Mon_NC < 1e-100):
                        return _gauss_fallback(
                            "[STARBME] QMC normalization constant Mon_NC="
                            "{:.4e} +/- {:.4e} (ns={:d}). IS integration "
                            "unstable. Falling back to Gaussian "
                            "approximation.".format(
                                float(Mon_NC), float(Mon_NC_err), ns))

                    Mon_raw = Mon.copy()
                    e_raw = e.copy()

                    Mon = Mon_raw[:-1].reshape((-1, nk)).T  # (nk, nMon)
                    Mon /= Mon_NC
                    # Add unconditional σ²_{k|hs} (law of total variance)
                    Mon[:, 1:2] += diag_sigma_k_given_hs.reshape((-1, 1))

                    M1 = Mon[:, 0:1]
                    M2 = Mon[:, 1:2]
                    M3 = Mon[:, 2:3]

                    # Per-point QMC error via error propagation
                    e_mom = e_raw[:-1].reshape((-1, nk)).T  # (nk, 3)
                    _e_num = e_mom[:, 0:1]
                    _e_den = Mon_NC_err
                    _delta_mu = np.sqrt(
                        (_e_num / Mon_NC)**2
                        + (M1 * _e_den / Mon_NC)**2)

                    mvs = np.empty((nk, 4))
                    mvs[:, 0:1] = M1
                    mvs[:, 1:2] = np.maximum(
                        M2 - M1**2 - _delta_mu**2, 0.0)
                    mvs[:, 2:3] = M3 - 3*M2*M1 + 2*M1**3
                    mvs[:, 3:4] = _delta_mu

                    if not ck_cov_output:
                        return mvs
                    else:
                        return mvs, _cov_output_from_gaussian()
        else:
            if not ck_cov_output:
                mvs = _bme_proba_gaussian(
                    ck, ch, cs, zh, zs, covmodel, covparam, covmat, order, options)
                return mvs
            else:
                mvs, ckcov = _bme_proba_gaussian(
                    ck, ch, cs, zh, zs,
                    covmodel, covparam, covmat, order, options, ck_cov_output)
                return mvs, ckcov
    else:
        raise ValueError("Now we can not consider non-gaussian GK." )

def _bme_proba_gaussian(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None, ck_cov_output=False):
    '''
    no neighbour consider, no data format transform.

    ch, cs, zh: np.2darray or None
    zs: new zs data or None, see softconverter.py for detail.
    ck_cov_output: if True, result will additionally return
        covariance between ck
    NOTE zs there should gaussian type e.g.
        zs = ((10, mean1, var1),...,(10, mean2, var2))
    '''

    nk, nh, ns = __get_khs_size(ck, ch, cs)
    x_all_split, mean_all_split, cov_all_split, covmat =\
        __get_all_split(
            ck, ch, cs, zh, zs, covmodel, covparam, covmat, order)
    
    has_remove_index, remove_index =\
        __get_covmat_remove_index(covmat)

    if has_remove_index: #need change data
        s_remove_index = remove_index-(nk+nh)
        if (s_remove_index >= 0).all():
            cs = np.delete(cs, s_remove_index, axis=0)
            zs = [zs_i for idx, zs_i in enumerate(zs) if idx not in s_remove_index]
            covmat = np.delete(covmat, nk+nh+s_remove_index, axis=0)
            covmat = np.delete(covmat, nk+nh+s_remove_index, axis=1)

            x_all_split, mean_all_split, cov_all_split, covmat =\
                __get_all_split(
                ck, ch, cs, zh, zs, covmodel, covparam, covmat, order)
        else: # need remove k or h — use covariance-based dup detection
            # The heuristic flagged a ck (or ch) index for removal, which
            # means ck is nearly co-located with cs. Detect via row
            # correlation and route those ck's through the dup path.
            _ck_dup_idx, _cs_dup_partner, _ = \
                _find_ck_cs_near_duplicates(covmat, nk, nh, ns)

            if _ck_dup_idx.size > 0:
                import warnings
                warnings.warn(
                    "[STARBME] _bme_proba_gaussian: {} ck point(s) "
                    "nearly co-located with cs (covariance-based). "
                    "Routing to dup path.".format(_ck_dup_idx.size))

                _nondup_mask = np.ones(nk, dtype=bool)
                _nondup_mask[_ck_dup_idx] = False
                mvs = np.empty((nk, 3))
                mvs[:] = np.nan

                # Near-duplicate ck's → analytical dup path
                mvs[_ck_dup_idx, :] = _bme_proba_gaussian_dup(
                    ck[_ck_dup_idx], ch, cs, zh, zs,
                    covmodel, covparam, covmat, order, options)

                # Non-duplicate ck's → standard Gaussian path
                if _nondup_mask.any():
                    ck_nd = ck[_nondup_mask]
                    if covmat is not None:
                        _keep = np.concatenate([
                            np.where(_nondup_mask)[0],
                            np.arange(nk, nk + nh),
                            np.arange(nk + nh, nk + nh + ns)])
                        covmat_nd = covmat[np.ix_(_keep, _keep)]
                    else:
                        covmat_nd = None
                    mvs[_nondup_mask, :] = _bme_proba_gaussian(
                        ck_nd, ch, cs, zh, zs,
                        covmodel, covparam, covmat_nd,
                        order, options)
                return mvs
            else:
                # Rank-deficient but no ck-cs dups (cs-cs or ch-ch dups).
                # Regularise the matrix and continue.
                _eigvals_r = np.linalg.eigvalsh(covmat)
                _eps_r = max(abs(min(_eigvals_r.min(), 0)) * 2, 1e-12)
                covmat = covmat + np.eye(covmat.shape[0]) * _eps_r
                x_all_split, mean_all_split, cov_all_split, covmat = \
                    __get_all_split(
                        ck, ch, cs, zh, zs,
                        covmodel, covparam, covmat, order)
    nk, nh, ns = __get_khs_size(ck, ch, cs)

    if ns == 0 and nh == 0:
        mvs = np.empty((ck.shape[0],3))
        mvs[:] = np.nan
        return mvs
        #raise ValueError('hard and soft data can not both without input')

    if ns == 0: # only hard data
        mean_k_given_h = _get_mean_a_given_b(
            x_all_split, mean_all_split,
            cov_all_split, sub_a='k', sub_b='h')
        sigma_k_given_h = _get_sigma_a_given_b(
            cov_all_split, sub_a='k', sub_b='h')

        skewness = np.zeros(mean_k_given_h.shape)
        mvs = np.hstack(
            (mean_k_given_h, sigma_k_given_h.diagonal().reshape((-1,1)),
            skewness)
            )
        if ck_cov_output:
            return mvs, sigma_k_given_h
        else:
            return mvs
    else: # both hard and soft data (hard data can be empty)
        mean_k = _get_mean(mean_all_split, 'k')
        
        #check outlier data
        mean_s_given_h = _get_mean_a_given_b(
            x_all_split, mean_all_split,
            cov_all_split, sub_a='s', sub_b='h')
        sigma_s_given_h = _get_sigma_a_given_b(cov_all_split, 's', 'h')
        general_mean = mean_s_given_h.ravel()
        general_var = np.diag(sigma_s_given_h)
        del sigma_s_given_h
        soft_mean = np.array([zs_i[1] for zs_i in zs])
        soft_var = np.array([zs_i[2] for zs_i in zs])

        problem_bool = (np.abs(general_mean - soft_mean)\
            > 3*(np.sqrt(general_var) + np.sqrt(soft_var))
            )
        if problem_bool.any():
            problem_index = np.where(problem_bool)[0]
            print('warning: the soft data at index(es) {i} '\
                'are far from its general marginal pdf'.format(
                    i=str(problem_index)))
            #remove and re calculate
            problem_index
            cs = np.delete(cs, problem_index, axis=0)
            zs = [zs_i for idx, zs_i in enumerate(zs) if idx not in problem_index]
            covmat = np.delete(covmat, nk+nh+problem_index, axis=0)
            covmat = np.delete(covmat, nk+nh+problem_index, axis=1)

            x_all_split, mean_all_split, cov_all_split, covmat =\
                __get_all_split(
                ck, ch, cs, zh, zs, covmodel, covparam, covmat, order)
            nk, nh, ns = __get_khs_size(ck, ch, cs)

            mean_s_given_h = _get_mean_a_given_b(
                x_all_split, mean_all_split,
                cov_all_split, sub_a='s', sub_b='h')

        mean_hs = _get_mean(mean_all_split, 'hs')

        NC, useful_args = _get_int_fg_a_given_b_fs_s(
            x_all_split, mean_all_split,
            cov_all_split, zs,
            sub_multi = 's_h', sub_s='s'
            )

        NC = __check_normalized_constant(NC, options)
        if NC == 0 or np.isnan(NC) or np.isinf(NC):
            # --- Fallback: Gaussian approximation when analytical NC fails ---
            # This typically happens when the soft PDFs have very narrow
            # support that doesn't overlap well with the conditional Gaussian.
            # Instead of returning NaN, approximate the soft data as Gaussian
            # and use the hard+soft-Gaussian analytical path.
            import warnings
            warnings.warn(
                "[STARBME] Analytical normalization constant NC={:.4e} "
                "(nk={}, nh={}, ns={}). Falling back to Gaussian "
                "approximation of soft data for this batch.".format(
                    float(NC) if not np.isnan(NC) else float('nan'),
                    nk, nh, ns))
            zs_gauss_fb = []
            for zsi in zs:
                pdftype = get_standard_soft_pdf_type(zsi[0])
                if pdftype == 10:
                    zs_gauss_fb.append(zsi)
                else:
                    zs_gau_m, zs_gau_v = proba2stat(
                        zsi[0],
                        np.array([zsi[1]]),
                        np.array([zsi[2]]),
                        np.array([zsi[3]]))
                    zs_gauss_fb.append(
                        (10, float(np.asarray(zs_gau_m).flat[0]),
                         float(np.asarray(zs_gau_v).flat[0])))
            # Re-run with all-Gaussian soft data (analytical solution)
            x_all_split_fb, mean_all_split_fb, cov_all_split_fb, covmat_fb = \
                __get_all_split(
                    ck, ch, cs, zh, zs_gauss_fb,
                    covmodel, covparam, covmat, order)
            nk_fb, nh_fb, ns_fb = __get_khs_size(ck, ch, cs)

            # --- Part 3 fix: Add soft noise to covariance diagonal ---
            # Without this, the conditional variance Σ_k|hs treats the
            # Gaussian-approximated soft data as exact observations,
            # producing a Kriging variance that ignores soft uncertainty.
            # Adding the soft variance σ²_i to the (i,i) diagonal of
            # the soft data block makes the inversion account for noise.
            for i_s, zsi_fb in enumerate(zs_gauss_fb):
                soft_var_i = zsi_fb[2]  # variance from Gaussian approx
                if soft_var_i > 0:
                    idx = nk_fb + nh_fb + i_s
                    covmat_fb[idx, idx] += soft_var_i
            # Re-split the modified covariance matrix
            cov_all_split_fb = np.vsplit(
                covmat_fb,
                [nk_fb, nk_fb + nh_fb, nk_fb + nh_fb + ns_fb]
                )[:-1]
            cov_all_split_fb = [
                np.hsplit(c, [nk_fb, nk_fb + nh_fb, nk_fb + nh_fb + ns_fb][:-1])
                for c in cov_all_split_fb]

            mean_k_fb = _get_mean(mean_all_split_fb, 'k')
            mean_k_given_hs_fb = _get_mean_a_given_b(
                x_all_split_fb, mean_all_split_fb,
                cov_all_split_fb, sub_a='k', sub_b='hs')
            sigma_k_given_hs_fb = _get_sigma_a_given_b(
                cov_all_split_fb, sub_a='k', sub_b='hs')
            skewness_fb = np.zeros(mean_k_given_hs_fb.shape)
            mvs = np.hstack((
                mean_k_given_hs_fb,
                sigma_k_given_hs_fb.diagonal().reshape((-1, 1)),
                skewness_fb))
            if ck_cov_output:
                return mvs, sigma_k_given_hs_fb
            else:
                return mvs

        (sigma_t_prime, inv_sigma_s_given_h,
            inv_sigma_tilde_s, mean_tilde_s,
            alias_c, alias_fgfs1234, alias_mean_d, alias_sigma_d
            ) = useful_args

        # ============================================================
        # NC-FREE FORMULATION  (NC cancels algebraically in all terms)
        # ============================================================
        # Previously the code multiplied by NC and then divided by NC
        # in every formula.  For large ns the NC can underflow to 0,
        # but every ratio  (hat_x_hs / NC),  (tt / NC)  is finite.
        # We now compute the NC-free quantities directly.
        #
        #   mean_t_s  = sigma_t' · (Σ_s|h⁻¹ · m_s|h  +  R⁻¹ · μ̃_s)
        #   mean_t_hs = [ x_h ; mean_t_s ]          (NC-free)
        #   BME_mean  = cond_k_hs · mean_t_hs + (m_k - cond_k_hs · m_hs)
        #   aa_nc[ss] = sigma_t'       (the posterior soft cov, NC-free)
        #   bb_nc     = (mean_t_hs - m_hs)(mean_t_hs - m_hs)^T
        #   tt_nc     = cond_k_hs · (aa_nc + bb_nc) · cond_k_hs^T
        #   BME_var   = diag(Σ_k|hs) - BME_mean² + m_k²
        #             - 2 m_k · cond_k_hs · m_hs
        #             + 2 m_k · cond_k_hs · mean_t_hs
        #             + diag(tt_nc)
        # ============================================================
        mean_t_s = sigma_t_prime.dot(
            inv_sigma_s_given_h.dot(mean_s_given_h)
            + inv_sigma_tilde_s.dot(mean_tilde_s)
            )
        if not nh:
            mean_t_hs = mean_t_s
        else:
            x_h = _get_x(x_all_split, 'h')
            mean_t_hs = np.vstack((x_h, mean_t_s))

        sigma_k_hs = _get_sigma(
            cov_all_split, sub_a='k', sub_b='hs')
        inv_sigma_hs_hs = _get_sigma(
            cov_all_split, sub_a='hs', sub_b='hs', inv=True)
        cond_k_hs = sigma_k_hs.dot(inv_sigma_hs_hs)

        BME_mean_k_given_hs_b = mean_k - cond_k_hs.dot(mean_hs)
        BME_mean_k_given_hs = (
            cond_k_hs.dot(mean_t_hs) + BME_mean_k_given_hs_b)

        sigma_k_given_hs = _get_sigma_a_given_b(
            cov_all_split, sub_a='k', sub_b='hs')

        # NC-free variance correction terms
        n_hs = nh + ns
        aa_nc = np.zeros((n_hs, n_hs))
        aa_nc[nh:nh+ns, nh:nh+ns] = sigma_t_prime
        bb_nc = (mean_t_hs - mean_hs).dot((mean_t_hs - mean_hs).T)
        tt_nc = cond_k_hs.dot(aa_nc + bb_nc).dot(cond_k_hs.T)

        if not ck_cov_output:
            sigma_k_given_hs_diag = \
                sigma_k_given_hs.diagonal().reshape((-1, 1))
            tt_nc_diag = tt_nc.diagonal().reshape((-1, 1))
            BME_var_k_given_hs = (
                sigma_k_given_hs_diag - BME_mean_k_given_hs**2
                + mean_k**2
                - 2 * mean_k * cond_k_hs.dot(mean_hs)
                + 2 * mean_k * cond_k_hs.dot(mean_t_hs)
                + tt_nc_diag
                )
        else:
            exm = cond_k_hs.dot(mean_t_hs).dot(mean_k.T)
            emm = cond_k_hs.dot(mean_hs).dot(mean_k.T)
            BME_var_k_given_hs_cov = (
                sigma_k_given_hs
                - BME_mean_k_given_hs.dot(BME_mean_k_given_hs.T)
                + mean_k.dot(mean_k.T)
                + 2 * exm - 2 * emm
                + tt_nc
                )
            BME_var_k_given_hs = \
                BME_var_k_given_hs_cov.diagonal().reshape((-1, 1))
            
        skewness = np.zeros(BME_mean_k_given_hs.shape)
        mvs = np.hstack(
            (BME_mean_k_given_hs, BME_var_k_given_hs, skewness)
            )
        if ck_cov_output:
            return mvs, BME_var_k_given_hs_cov
        else:
            return mvs

def _bme_proba_gaussian_dup(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None, ck_cov_output=False):

    nk, nh, ns = __get_khs_size(ck, ch, cs)
    x_all_split, mean_all_split, cov_all_split, covmat =\
        __get_all_split(
            ck, ch, cs, zh, zs, covmodel, covparam, covmat, order)

    if ns == 0: #strange, should have ck duplicates with cs
        raise ValueError('no cs, strange.')
    else:
        NC, (sigma_d, inv_sigma_s_given_h,
            inv_sigma_tilde_s, mean_tilde_s,
            alias_c, alias_fgfs1234, alias_mean_d, alias_sigma_d
            ) =\
            _get_int_fg_a_given_b_fs_s(
                x_all_split, mean_all_split, cov_all_split, zs, 
                sub_multi = 's_h', sub_s='s'
                )

        # no used but give a warning   
        #NC = __check_normalized_constant(NC)
        if NC == 0:
            print('warning: NC found to be 0.')
            if options['debug']:
                # import pdb
                # pdb.set_trace()
                pass
        # --- Find ck→cs partner mapping (covariance-based + exact) ---
        # Use row-correlation of covmat to find the closest cs for each ck.
        _ck_dup_d, _cs_dup_d, _ = _find_ck_cs_near_duplicates(
            covmat, nk, nh, ns)
        # Also try exact coordinate match
        _exact_ck, _exact_cs = np.where((cs == ck[:, None]).all(-1))
        # Merge: prefer exact match, fill in from covariance-based
        _cs_for_ck = np.full(nk, -1, dtype=int)
        for ci, si in zip(_ck_dup_d, _cs_dup_d):
            _cs_for_ck[ci] = si
        for ci, si in zip(_exact_ck, _exact_cs):
            _cs_for_ck[ci] = si  # exact takes precedence

        # For any ck without a partner, find the closest cs
        # via highest row-correlation
        _unmatched = np.where(_cs_for_ck < 0)[0]
        if _unmatched.size > 0:
            _corrmat_d = np.corrcoef(covmat)
            for ui in _unmatched:
                # ck index ui, cs block starts at nk+nh
                _corr_row = np.abs(
                    _corrmat_d[ui, nk + nh: nk + nh + ns])
                _cs_for_ck[ui] = int(np.argmax(_corr_row))

        cs_dup_index = _cs_for_ck
        return np.hstack((
            alias_mean_d[cs_dup_index,:],
            np.diagonal(alias_sigma_d).reshape((-1,1))[cs_dup_index,:],
            np.zeros((nk, 1))
            ))

        # NC, (sigma_d, inv_sigma_s_given_h,
        #     inv_sigma_tilde_s, mean_tilde_s,
        #     alias_c, alias_fgfs1234, alias_mean_d, alias_sigma_d
        #     ) =\
        #     _get_int_fg_a_given_b_fs_s(
        #         x_all_split, mean_all_split, cov_all_split, zs, 
        #         sub_multi = 's_h', sub_s='s'
        #         )
        # NC = __check_normalized_constant(NC)
        
        # #get top part
        # #ns x 1
        # top_part2 = NC * alias_mean_d
        # top_part = alias_c * alias_fgfs1234 * alias_mean_d
        # import pdb
        # pdb.set_trace()
        # #get each nc_dup
        # dup_NC = np.ones(top_part.shape)
        # # find ck in cs index
        # ck_dup_index, cs_dup_index = np.where((cs==ck[:,None]).all(-1))
        # for ck_i, cs_i in zip(ck_dup_index, cs_dup_index):
        #     #get x/mean/cov_all_split at each ck by remove dup cs point
        #     x_all_split_each_ck =\
        #         x_all_split[:2]\
        #         + [np.delete(x_all_split[2], cs_i, axis=0)]
        #     mean_all_split_each_ck =\
        #         mean_all_split[:2]\
        #         + [np.delete(mean_all_split[2], cs_i, axis=0)]

        #     covmat_each_ck = np.delete(covmat, nk+nh+cs_i, axis=0)
        #     covmat_each_ck = np.delete(covmat_each_ck, nk+nh+cs_i, axis=1)
           
        #     cov_all_split_each_ck = np.vsplit(
        #         covmat_each_ck, [nk, nk+nh, nk+nh+ns-1]
        #         )[:-1] #exclude final empty array
        #     cov_all_split_each_ck = \
        #         [np.hsplit(c, [nk, nk+nh, nk+nh+ns-1][:-1])\
        #         for c in cov_all_split_each_ck]
        #     zs_each_ck = [z for idx_z, z in enumerate(zs) if idx_z != cs_i]

        #     dup_NC[cs_i, 0] = __check_normalized_constant(
        #         __get_normalized_constant(
        #             x_all_split_each_ck,
        #             mean_all_split_each_ck,
        #             cov_all_split_each_ck, zs_each_ck, 
        #             sub_multi = 's_h', sub_s='s'
        #             )
        #         )
        # return (top_part/dup_NC)[cs_dup_index,:]

def _apply_nonneg_truncation(mvs):
    """Non-negativity correction: zero-clamp mean + truncated-normal variance.

    For a posterior N(μ, σ²) truncated to [0, ∞), the truncated
    distribution has:

        α  = −μ/σ
        Φ₊ = Φ(μ/σ) = P(Z ≥ 0)   (survival probability)
        λ  = φ(α) / Φ₊            (inverse Mills ratio)
        δ  = λ(λ − α)             (variance reduction factor, ∈ [0, 1])

        Mean_trunc = μ + σλ        (always ≥ 0)
        Var_trunc  = σ²(1 − δ)    (always ≤ σ²)

    **Mean**: We use zero-clamping  max(μ, 0)  rather than the full
    truncated-normal mean  μ + σλ.  The latter inflates near-zero
    estimates to ~0.8σ ("yellow floor" artifact) in data-sparse
    regions where μ ≈ 0 but σ is large.  Zero-clamping is
    conservative but honest.

    **Variance**: We DO apply the truncated-normal formula  σ²(1−δ)
    for every point, even those with μ > 0.  Knowing Z ≥ 0 always
    reduces uncertainty, and the reduction is smooth and physically
    meaningful:

        μ ≫  0  →  δ ≈ 0  →  Var ≈ σ²   (constraint irrelevant)
        μ  =  0  →  δ ≈ 0.64 →  Var ≈ 0.36σ²
        μ ≪  0  →  δ → 1   →  Var → 0   (almost all mass < 0)

    Parameters
    ----------
    mvs : ndarray, shape (nk, 3) or (nk, 4)
        Columns: [mean, variance, skewness, (delta_mu)].
        If delta_mu == -1 for a point, that point's nonneg correction
        was already applied inside the QMC integrand; skip it here.

    Returns
    -------
    mvs_out : ndarray, shape (nk, 3)
        Corrected array with truncated variance; delta_mu column removed.
    """
    nk = mvs.shape[0]
    mu  = mvs[:, 0].copy()
    var = mvs[:, 1].copy()

    # Check for the "already handled" flag in column 3
    _has_flag = mvs.shape[1] >= 4
    if _has_flag:
        _delta_col = mvs[:, 3].copy()
    else:
        _delta_col = np.zeros(nk)

    for i in range(nk):
        # If the QMC integrand already computed truncated moments,
        # the delta_mu column is set to -1 as a flag.  Skip these
        # points — their mean and variance are already correct.
        if _has_flag and _delta_col[i] < 0:
            continue

        # Skip NaN / invalid points
        if np.isnan(mu[i]) or np.isnan(var[i]) or var[i] <= 0:
            if not np.isnan(mu[i]) and mu[i] < 0:
                mvs[i, 0] = 0.0
            continue

        sigma_i = np.sqrt(var[i])
        # α = −μ/σ  (positive when μ < 0)
        alpha = -mu[i] / sigma_i

        # Φ₊ = Φ(μ/σ) = P(Z ≥ 0)
        Phi_pos = scipy.stats.norm.cdf(mu[i] / sigma_i)

        if Phi_pos < 1e-12:
            # Almost no probability above 0 → clamp both mean and var
            mvs[i, 0] = 0.0
            mvs[i, 1] = 0.0
            continue

        # Inverse Mills ratio  λ = φ(α) / Φ₊
        phi_alpha = scipy.stats.norm.pdf(alpha)
        lam = phi_alpha / Phi_pos

        # Variance reduction factor  δ = λ(λ − α) = λ(λ + μ/σ)
        delta = lam * (lam - alpha)

        # Truncated-normal variance:  σ²(1 − δ)
        mvs[i, 1] = var[i] * max(1.0 - delta, 0.0)

        # Zero-clamp the mean (avoid yellow-floor inflation)
        if mu[i] < 0:
            mvs[i, 0] = 0.0

    # Remove delta_mu column (return 3-col array)
    return mvs[:, :3]


def _get_x_all_split(nk, zh, zs):
    '''
        Create the "estimated" observed values 
    for the estimation and observations
        For now, zero is used for estimation points
    (which should be specified as NaN)
        mean values are used for soft data
    '''
    x_all_split = []
    xk = np.empty((nk, 1))  # will be replaced later
    x_all_split.append(xk)
    x_all_split.append(zh) # e.g. xh
    if zs:
        xs = np.empty((len(zs), 1))
        for i, zsi in enumerate(zs):
            if get_standard_soft_pdf_type(zsi[0]) == 10:  # gaussian/normal
                xs[i] = zsi[1] #z_mean
            else:
                xs[i], dummy_v = proba2stat(
                    zsi[0],
                    np.array([zsi[1]]),
                    np.array([zsi[2]]),
                    np.array([zsi[3]])
                    )
        x_all_split.append(xs)
    else:
        x_all_split.append(None)
    return x_all_split

def _get_mean_all_split(x_all_split, order):
    '''
    Obtain the trend estimations at the estimation and data locations based 
    upon the specified trend order
    '''
    if isinstance(order, np.ndarray):  # user defined general knowledge, (row x 1 2d array)
        start_i = 0
        mean_all_split = []
        for i in x_all_split:
            if i is not None:
                end_i = start_i + i.size
                mean_all_split.append(order[start_i:end_i, :])
                start_i = end_i
            else:
                mean_all_split.append(None)   
    elif order == 0:  # constant mean, exclude zk, average h and s
        xx=[x for x in x_all_split[1:] if x is not None]
        constant_mean_ = np.vstack(xx).mean()
        mean_all_split = []
        for i in x_all_split:
            if i is not None:
                mean_all_split.append(np.ones(i.shape)*constant_mean_)
            else:
                mean_all_split.append(None)
        #for means in mean_all_split:
        #  means[:] = constant_mean_
    elif np.isnan(order):  # zero mean: 
        mean_all_split = []
        for i in x_all_split:
            if i is not None:
                mean_all_split.append(np.zeros(i.shape))
            else:
                mean_all_split.append(None)
    return mean_all_split

def _get_cov_all_split(ck, ch, cs, covmodel, covparam):
  '''
  Obtain the covariance in the split ways.
  See coord2K
  '''
  return coord2Ksplit((ck, ch, cs), (ck, ch, cs),
                      covmodel, covparam)[0]

def _get_x(x_all_split, sub):
  '''
  Retrieve the estimated observed values given specified class, i.e., sub
  sub can be k, h, and s for estimation, hard, and soft data
  '''
  idx = [KHS_DICT[i] for i in sub]
  output=[x_all_split[i] for i in idx if x_all_split[i] is not None]
  if len(output)>0:
    return np.vstack(output)
  else:
    return None

def _get_mean(mean_all_split, sub):
  '''
  Retrieve the expected values given specified class, i.e., sub
  sub can be k, h, and s for estimation, hard, and soft data
  '''
  idx = [KHS_DICT[i] for i in sub]     
  output=[mean_all_split[i] for i in idx if mean_all_split[i] is not None]
  if len(output)>0:
    return np.vstack(output)
  else:
    return None

def _get_sigma(cov_all_split, sub_a, sub_b, inv=False):
  '''
  Retrieve the cross-covaiance between specified class, i.e., sub_a and sub_b
  sub_a and sub_b can be k, h, and s for estimation, hard, and soft data
  '''
  idx_a = [KHS_DICT[i] for i in sub_a]
  idx_b = [KHS_DICT[i] for i in sub_b]

  cov_a_b = []
  for i in idx_a:
    output=[cov_all_split[i][j] for j in idx_b if cov_all_split[i][j] is not None]
    if len(output)>0:
      cov_a_b.append(np.hstack(output))
  # Filter out any None entries (rows where all covariance blocks were None)
  cov_a_b = [x for x in cov_a_b if x is not None]
  if len(cov_a_b) == 0:
    # All covariance blocks are None — return an empty 2D array
    return np.array([]).reshape((0, 0))
  cov_a_b = np.vstack(cov_a_b)
  if not inv:
    return cov_a_b
  else:
    # Check for singularity before computing pseudo-inverse
    if cov_a_b.size == 0:
      return cov_a_b
    cond = np.linalg.cond(cov_a_b)
    if cond > 1e12:
      import warnings
      warnings.warn(
        "Covariance matrix for sub ({a},{b}) is nearly singular "
        "(condition number = {c:.2e}). Estimation results at this "
        "location may be unreliable. Consider checking whether the "
        "estimation point overlaps with data locations or whether "
        "the covariance model parameters are appropriate.".format(
          a=sub_a, b=sub_b, c=cond))
    return _robust_pinv(cov_a_b)

def _get_mean_a_given_b(x_all_split, mean_all_split,
    cov_all_split, sub_a, sub_b):
    '''
    Obtain the conditonal mean a given b by using conditonal Gaussian formula
    '''      

    if 'k' not in sub_b:                    
        x_b = _get_x(x_all_split, sub_b)
        mean_a = _get_mean(mean_all_split, sub_a)
        mean_b = _get_mean(mean_all_split, sub_b)
        if mean_b is not None: # consider the case that data in sub_b does not exist
            sigma_a_b = _get_sigma(cov_all_split, sub_a, sub_b)
            inv_sigma_b_b = _get_sigma(cov_all_split, sub_b, sub_b, inv=True)
            output=mean_a + sigma_a_b.dot(inv_sigma_b_b).dot(x_b - mean_b)
        else:
           output=mean_a
        return output
    else:
        nlim=np.asarray(x_all_split[0]).size
        smtx=np.ones((1,nlim))
        if nlim>1:
            idx = [KHS_DICT[i] for i in sub_b if i != 'k']
            xhs=np.vstack([x_all_split[i] for i in idx])
            x_b=[x_all_split[0].reshape((1,nlim)),xhs.dot(smtx)]
            x_b=np.vstack(x_b)
        else:            
           x_b = _get_x(x_all_split, sub_b)
        
        mean_a = _get_mean(mean_all_split, sub_a)
        mean_b = _get_mean(mean_all_split, sub_b)
        if mean_b is not None: # consider the case that data in sub_b does not exist
            sigma_a_b = _get_sigma(cov_all_split, sub_a, sub_b)
            inv_sigma_b_b = _get_sigma(cov_all_split, sub_b, sub_b, inv=True)
            output=mean_a + sigma_a_b.dot(inv_sigma_b_b).dot(x_b - mean_b)
        else:
            output=mean_a
        return output

def _get_sigma_a_given_b(cov_all_split, sub_a, sub_b):
  '''
  Obtain the conditional covariance a given b by using conditonal Gaussian 
  formula
  '''
  sigma_a_a = _get_sigma(cov_all_split, sub_a, sub_a)
  sigma_a_b = _get_sigma(cov_all_split, sub_a, sub_b)
  if sigma_a_b.size > 0:
    sigma_b_b = _get_sigma(cov_all_split, sub_b, sub_b)
    if sigma_b_b.size == 0:
      # sub_b data does not exist; return unconditional covariance
      return sigma_a_a
    inv_sigma_b_b = _get_sigma(cov_all_split, sub_b, sub_b, inv=True)
    sigma_b_a = _get_sigma(cov_all_split, sub_b, sub_a)
    return sigma_a_a - sigma_a_b.dot(inv_sigma_b_b).dot(sigma_b_a)
  else:
    return sigma_a_a

def _get_multivariate_normal_pdf(x_all_split, mean_all_split,
    cov_all_split, sub_multi):
    '''
    Obtain multivariate Gaussian pdf or conditional multivariate Gaussian
    based upon the specified notations, i.e., sub_multi
    
    Note:
    sub_multi     string    h, s, and k for hard, soft and estimation locations
                            a_b represents a given b, e.g., k_h
    '''                                   
    if "_" in sub_multi:  # "given" type
        sub_a, sub_b = sub_multi.split('_')#x_sub.split('_') (temporarily change by HL)
        m = _get_mean_a_given_b(x_all_split, mean_all_split,
                                cov_all_split, sub_a, sub_b)
        v = _get_sigma_a_given_b(cov_all_split, sub_a, sub_b)
    else:  # single_sub
        sub_a = sub_multi
        m = _get_mean(mean_all_split, sub_a)
        v = _get_sigma(cov_all_split, sub_a, sub_a)
    return scipy.stats.multivariate_normal(m.T[0], v).pdf

def _get_fs(zs):
    '''
    the product of fs distributions
    x   ndim(e.g. npts) by ns
            x is a 2-D np array with the dimension of 
            ndim(number of samples at each integral) 
            by ns (the number of integrals, i.e., number 
            of soft data)      
    '''
    def fs(x):
        res = np.ones((x.shape[0],1))
        for idx_k, zsi in enumerate(zs):
            pdf_type = get_standard_soft_pdf_type(zsi[0])
            if pdf_type == 2:
                nl = int(zsi[1][0])
                limi = zsi[2]
                probdens = zsi[3]
                y_i = np.interp(
                    x[:,idx_k:idx_k+1], limi[:nl], probdens[:nl],
                    left = 0., right = 0.)
            elif pdf_type == 1:
                # BUG FIX: was using zs[1],zs[2],zs[3] (global list)
                # instead of zsi[1],zsi[2],zsi[3] (individual soft datum)
                nl = int(zsi[1][0])
                limi = zsi[2]
                probdens = zsi[3]
                # Histogram PDF: probdens[j] is constant for limi[j] <= x < limi[j+1]
                # There are nl limit values defining nl-1 bins
                xi = x[:, idx_k].ravel()
                bin_idx = np.searchsorted(limi[:nl], xi, side='right') - 1
                # Clip to valid bin range [0, nl-2]; values outside get 0
                y_i = np.where(
                    (bin_idx >= 0) & (bin_idx < nl - 1),
                    probdens[np.clip(bin_idx, 0, nl - 2)],
                    0.0
                ).reshape(-1, 1)
            elif pdf_type == 10:
                zm = zsi[1]
                zstd = np.sqrt(zsi[2])
                try:
                    y_i = scipy.stats.norm.pdf(
                        x[:,idx_k:idx_k+1], loc=zm, scale=zstd)
                except FloatingPointError:
                    y_i = np.zeros((x.shape[0], 1))
              
            if not (y_i.all() or y_i.any()):
                return np.zeros((x.shape[0], 1))
            else:
                res *= y_i
        return res
    return fs

def _get_Fsinv(zs):

    Fs = pdf2cdf(zs)
    def Fsinv(x):  
        res = np.zeros(x.shape)
        for idx_k, Fsi in enumerate(Fs):
            pdf_type = get_standard_soft_pdf_type(Fsi[0])
            if pdf_type == 2:
                nl = Fsi[1][0]
                limi = Fsi[2]
                probdens = Fsi[3]
                probCDFs = Fsi[4]

                alpha = np.diff(probdens) / np.diff(limi)
                i = np.searchsorted(probCDFs[1:],x[:,idx_k:idx_k+1])
                D = np.abs(probdens[i]**2 + 2*alpha[i] * (x[:,idx_k:idx_k+1] - probCDFs[i]))
                y_i = limi[i] + (-probdens[i] + np.sqrt(D)) / alpha[i]
                
            res[:,idx_k:idx_k+1] = y_i
        return res
    return Fsinv

def _get_int_fg_a_given_b_fs_s(x_all_split, mean_all_split,
  cov_all_split, zs, sub_multi, sub_s='s'):
  '''
  The upper right part and lower right part of the last row of formula (1)
  The evaluation is based upon Eqns. (8) or (9) in the cases of s_h and s_kh 
  respectively
  '''

  #fg='s_kh', fs='s'
  sub_a, sub_b = sub_multi.split('_')
  sigma_a_given_b = _get_sigma_a_given_b(cov_all_split, sub_a, sub_b)
  try:
      inv_sigma_a_given_b = _robust_pinv(sigma_a_given_b)
  except np.linalg.LinAlgError as e:
      # import pdb
      # pdb.set_trace()
      raise e
  # mean_tilde_s = zs[1]  # mean
  # sigma_tilde_s = np.diag(zs[2].T[0])  # cov matrix
  mean_tilde_s = []
  sigma_tilde_s = []
  for zsi in zs:
      mean_tilde_s.append([zsi[1]])
      sigma_tilde_s.append(zsi[2])
  mean_tilde_s = np.array(mean_tilde_s) # mean
  sigma_tilde_s = np.diag(sigma_tilde_s)  # cov matrix
  try:
      inv_sigma_tilde_s = _robust_pinv(sigma_tilde_s)
  except np.linalg.LinAlgError as e:
      # import pdb
      # pdb.set_trace()
      raise e

  sigma_t = _robust_pinv(inv_sigma_a_given_b + inv_sigma_tilde_s)
  ns = mean_tilde_s.shape[0]

  # --- Use log-space determinants (slogdet) to avoid underflow/overflow ---
  # For large ns (e.g., 19), np.linalg.det() of ns×ns covariance matrices
  # can underflow to 0 or overflow to Inf, making NC = 0/NaN/Inf even
  # though the final BME formulas are well-conditioned (NC cancels).
  _sign_t, _logdet_t = np.linalg.slogdet(sigma_t)
  _sign_ab, _logdet_ab = np.linalg.slogdet(sigma_a_given_b)
  _sign_ts, _logdet_ts = np.linalg.slogdet(sigma_tilde_s)

  # log(alias_c) = 0.5*logdet_t - 0.5*(logdet_ab + logdet_ts) - (ns/2)*log(2π)
  _log_fgfs_front = (0.5 * _logdet_t
                     - 0.5 * (_logdet_ab + _logdet_ts)
                     - (ns / 2.0) * np.log(2 * np.pi))
  # Check sign: all covariance matrices should be PSD, so signs should be +1
  _det_sign = _sign_t * _sign_ab * _sign_ts
  if _det_sign <= 0:
      # Singular or negative determinant — fall back to old-style det
      import warnings as _w
      _w.warn("[STARBME] slogdet sign issue in NC computation "
              "(signs: t={}, ab={}, ts={}). NC may be unreliable.".format(
                  _sign_t, _sign_ab, _sign_ts))
  alias_c = _log_fgfs_front  # store log-space value for now
  fgfs_front = _log_fgfs_front  # log-space
  # fgfs_front = np.sqrt(det_sigma_t) /\
  #       ((2*np.pi)**(ns/2.) *
  #        np.sqrt(det_sigma_a_given_b * det_sigma_tilde_s)
  #        )

  mean_a_given_b = _get_mean_a_given_b(
        x_all_split, mean_all_split, cov_all_split, sub_a, sub_b)
  fgfs_1 = np.diag((mean_a_given_b.T).dot(
        inv_sigma_a_given_b).dot(mean_a_given_b))
  fgfs_2 = (mean_tilde_s.T).dot(inv_sigma_tilde_s).dot(mean_tilde_s)
  fgfs_3 = (mean_a_given_b.T).dot(inv_sigma_a_given_b) +\
        (mean_tilde_s.T).dot(inv_sigma_tilde_s)
  fgfs_4 = inv_sigma_tilde_s.dot(mean_tilde_s) +\
        inv_sigma_a_given_b.dot(mean_a_given_b)
  alias_sigma_d = sigma_t
  alias_mean_d = alias_sigma_d.dot(fgfs_4)
  # 1 x 1 array (scalar)
  _quadratic_form = (
      (fgfs_1 + fgfs_2 - np.diag(fgfs_3.dot(sigma_t).dot(fgfs_4)))
      ).item()

  # --- Compute NC in log-space, then exponentiate ---
  # log(NC) = log(fgfs_front) + (-1/2) * quadratic_form
  _log_NC = _log_fgfs_front + (-0.5) * _quadratic_form
  # Clamp to prevent overflow (exp(709) is near double max)
  _log_NC = np.clip(_log_NC, -700, 700)
  NC = _det_sign * np.exp(_log_NC)

  # Store the exponential part for backward compatibility
  fgfs_end = np.exp(np.clip(-0.5 * _quadratic_form, -700, 700))
  alias_c = NC / fgfs_end if abs(fgfs_end) > 1e-300 else 0.0
  alias_fgfs1234 = fgfs_end

  return NC, \
        (sigma_t, inv_sigma_a_given_b, inv_sigma_tilde_s, mean_tilde_s,
            alias_c, alias_fgfs1234, alias_mean_d, alias_sigma_d)

def _changetimeform(ck,ch=None,cs=None):
  '''
  Change the time format into float while it is in datetime format
  '''  
  
  if type(ck[0,-1])==np.datetime64:
    origin=ck[0,-1]
    ck[:,-1]=np.double(np.asarray(ck[:,-1],dtype='datetime64')-origin)
    ck=ck.astype(np.double)
    if ch is not None and ch.size>0:
      if (not type(ch[0,-1]==np.datetime64)):
        print ('Time format of ch is not consistent with ck (np.datetime64)')
        raise
      ch[:,-1]=np.double(np.asarray(ch[:,-1],dtype='datetime64')-origin)
      ch=ch.astype(np.double)
    if cs is not None and cs.size>0:
      if (not type(cs[0,-1]==np.datetime64)):
        print ('Time format of cs is not consistent with ck (np.datetime64)')
        raise
      cs[:,-1]=np.double(np.asarray(cs[:,-1],dtype='datetime64')-origin)
      cs=cs.astype(np.double)
      
  return ck,ch,cs

def _set_nh_ns(ck,ch,cs,nhmax,nsmax,dmax):
  '''
  Set the size of nhmax and nsmax that limits the size of matrix to be allocated
  it can be important for an efficient S/T estimation
  '''
  if dmax is not None and np.all(dmax):
    nhmax = int(nhmax)
    nsmax = int(nsmax)
    dmax = np.array(dmax,ndmin=2)
    return nhmax,nsmax,dmax
  
  if ck[0,:].size<3:
    if dmax is None:
      dmax_=0
      if ch is not None:
        ch=np.array(ch,ndmin=2)
        maxd_h=pdist(ch).max()
        dmax_=np.max([dmax_,maxd_h])
      if cs is not None:
        cs=np.array(cs,ndmin=2)
        maxd_s=pdist(cs).max()
        dmax_=np.max([dmax_,maxd_s])
      dmax=np.array(dmax_).reshape(1,1)

    if nhmax is None:
      if ch is not None:
        nhmax=ch.shape[0]
      else:
        nhmax=0

    if nsmax is None:
      if cs is not None:
        nsmax=cs.shape[0]
      else:
        nsmax=0

    
  else:
    maxd=0
    maxt=0
    if dmax is None:
      if ch is not None:
        dummy=np.random.rand(ch.shape[0],1)
        _,cMS_h,tME_h,_=valstv2stg(ch,dummy)
        if nhmax is None:
          nhmax=cMS_h.shape[0]*3
        maxd_h=pdist(cMS_h).max()
        maxt_h=pdist(tME_h.reshape((tME_h.size,1))).max()
      else:
        maxd_h=0
        maxt_h=0
        nhmax=0
      maxd=np.max([maxd_h,maxd]) 
      maxt=np.max([maxt_h,maxt])
      if cs is not None: 
        dummy=np.random.rand(cs.shape[0],1)
        _,cMS_s,tME_s,_=valstv2stg(cs,dummy)
        if nsmax is None:
          if zs[0]==10 or zs[0] == 'gaussian':
            nsmax=cMS_s.shape[0]*3
          else:
            nsmax=3
        maxd_s=pdist(cMS_s).max()
        maxt_s=pdist(tME_s.reshape((tME_s.size,1))).max()
        maxd=np.max([maxd_s,maxd])
        maxt=np.max([maxt_s,maxt])
      else:
        nsmax=0
        maxd_s=0
        maxt_s=0
      maxd=np.max([maxd_s,maxd])
      maxt=np.max([maxt_s,maxt])
    dmax=np.array([maxd,maxt,np.nan]).reshape(1,3)

  return nhmax,nsmax,dmax

def _stratio(covparam):
  '''
  Estimate the S/T ratio for dmax
  '''
  nm=len(covparam)
  sills= np.array([covparam[k][0] for k in range(nm)])  
  hrange = np.array([covparam[k][1][0] for k in range(nm)]) 
  idx0 = np.where([hrange[k] is not None for k in range(nm)])[0]
  idx=np.where(sills[idx0]==sills.max())[0]
  ratio=covparam[idx0[idx]][1][0]/covparam[idx0[idx]][2][0]
  return ratio

def _bme_posterior_prepare(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None,
    nhmax=None, nsmax=None, dmax=None,
    general_knowledge='gaussian',
    #  specific_knowledge='unknown',  
    pdfk=None,pdfh=None,pdfs=None,hk_k=None,hk_h=None,hk_s=None,
    gui_args=None):

    '''
    check and configure arguments and 
        find neighbor ckhs index for bme posterior calculation

    ckhs_idx_list:  [ck_idx, ch_idx, cs_idx] represents
        these ck have the same neighbors ch and cs

    return (output_arguments, configured_arguments):
        a tuple contain arguments
    '''
    print('preparing...', end='')
    if covmat is None:
        if (covmodel is None) or (covparam is None):
            raise ValueError(
                'Covariance model and their associated parameters '\
                'should be specified if no covarinace matrix provided.')


    dk = ck.shape[1]
    nk = ck.shape[0]
    nh = ch.shape[0] if ch is not None else 0
    ns = cs.shape[0] if cs is not None else 0

    ck, ch, cs = _changetimeform(ck, ch, cs)
    nhmax, nsmax, dmax = _set_nh_ns(ck, ch, cs, nhmax, nsmax, dmax)
    if dmax.size == 3 and np.isnan(dmax[0][2]):
        dmax[0][2] = _stratio(covparam)
    stratio = dmax[0][2] if dk == 3 else 1.
      
    if options is None:
        options = BMEoptions()

    if gui_args:
        qpgd = gui_args[0]
    
    if general_knowledge == 'gaussian':
        order = get_standard_order(order)

        if covmat is not None: #consider covmat if exists, not distance, no need to calculate distance
            ckhs_idx_list = []
            if nh != 0:
                covmat_k_h = covmat[:nk, nk:nk+nh] # slice cov(k x h)
                # sort from big to small, clip with nhmax
                k_by_h_idx = (-covmat_k_h).argsort(axis=1)[:, :nhmax]
                # sort h index (inplace)
                k_by_h_idx.sort(axis=1)
                # make ch_ck_dict
                ch_ck_dict = {}
                for k_idx, h_idx in enumerate(k_by_h_idx):
                    tuple_h_idx = tuple(h_idx)
                    if tuple_h_idx not in ch_ck_dict.keys():
                        k_idx_mul = np.where(
                            np.all(h_idx == k_by_h_idx, axis=1)
                            )[0]
                        ch_ck_dict[tuple_h_idx] = list(k_idx_mul)
                    else:
                        continue #skip duplicated row
                if ns != 0:
                    # slice cov(k x s)
                    covmat_k_s = covmat[:nk, nk+nh:nk+nh+ns]
                    for ch_idx, ck_idx in ch_ck_dict.items():
                        picked_covmat_k_s = covmat_k_s[ck_idx, :]
                        # sort from big to small, clip with nsmax
                        picked_k_by_s_idx =\
                            (-picked_covmat_k_s).argsort(axis=1)[:, :nsmax]
                        # sort s index (inplace)
                        picked_k_by_s_idx.sort(axis=1)
                        # make ch_ck_dict
                        cs_ck_dict = {}
                        for picked_k_idx, s_idx in enumerate(picked_k_by_s_idx):
                            tuple_s_idx = tuple(s_idx)
                            if tuple_s_idx not in cs_ck_dict.keys():
                                picked_k_idx_mul = np.where(
                                    np.all(s_idx == picked_k_by_s_idx, axis=1)
                                    )[0]
                                cs_ck_dict[tuple_s_idx] = list(picked_k_idx_mul)
                            else:
                                continue #skip duplicated row
                        for cs_idx, ck2_idx in cs_ck_dict.items():
                            ck_idx = np.array(ck_idx)
                            ckhs_idx_list.append(
                                [ck_idx[ck2_idx,], ch_idx, cs_idx]
                                )
                else: # ns = 0
                    for ch_idx, ck_idx in ch_ck_dict.items():
                        ckhs_idx_list.append([ck_idx, ch_idx, ()])
            elif nh == 0 and ns != 0: # nh = 0, ns != 0
                covmat_k_s = covmat[:nk, nk+nh:nk+nh+ns] # slice cov(k x s)
                # sort from big to small, clip with nsmax
                k_by_s_idx = (-covmat_k_s).argsort(axis=1)[:, :nsmax]
                # sort s index (inplace)
                k_by_s_idx.sort(axis=1)
                # make cs_ck_dict
                cs_ck_dict = {}
                for k_idx, s_idx in enumerate(k_by_s_idx):
                    tuple_s_idx = tuple(s_idx)
                    if tuple_s_idx not in cs_ck_dict.keys():
                        k_idx_mul = np.where(
                            np.all(s_idx == k_by_s_idx, axis=1)
                            )[0]
                        cs_ck_dict[tuple_s_idx] = list(k_idx_mul)
                    else:
                        continue #skip duplicated row
                for cs_idx, ck_idx in cs_ck_dict.items():
                    ckhs_idx_list.append([ck_idx, (), cs_idx])
            else: # nh = 0, ns = 0
                raise ValueError("nh and ns shouldn't be both 0.")
        else:
            #aggregate ck for same hard data and soft data
            # chs = np.vstack(ch, cs)
            ck_norm = np.copy(ck)
            ck_norm[:, -1] = ck_norm[:, -1] * stratio
            if dk == 3:
                dmax_norm = (dmax[0][0]**2 + (dmax[0][1] * stratio)**2)**0.5
            else:
                dmax_norm = dmax[0][0]

            if isinstance(ch, np.ndarray) and nhmax != 0:
                ch_norm = np.copy(ch)
                ch_norm[:, -1] = ch_norm[:, -1] * stratio
                ch_tree = cKDTree(ch_norm)
            if isinstance(cs, np.ndarray) and nsmax != 0:
                cs_norm = np.copy(cs)
                cs_norm[:, -1] = cs_norm[:, -1] * stratio
                cs_tree = cKDTree(cs_norm)

            ckhs_idx_list = []
            if isinstance(ch, np.ndarray) and nhmax != 0: #has harddata
                ch_ck_dict =\
                    neighbours_index_kd(ck_norm, ch_tree, nhmax, dmax_norm)
                for ch_idx, ck_idx in ch_ck_dict.items():
                    if isinstance(cs, np.ndarray) and nsmax != 0: #both hard and soft
                        picked_ck_norm = ck_norm[ck_idx, :]
                        cs_ck_dict =\
                            neighbours_index_kd(
                                picked_ck_norm, cs_tree, nsmax, dmax_norm
                                )
                        for cs_idx, ck2_idx in cs_ck_dict.items():
                            ck_idx = np.array(ck_idx)
                            ckhs_idx_list.append(
                                [ck_idx[ck2_idx,], ch_idx, cs_idx]
                                )
                    else: #only harddata
                        ckhs_idx_list.append([ck_idx, ch_idx, ()])
            elif isinstance(cs, np.ndarray) and nsmax != 0: #only softdata
                cs_ck_dict =\
                    neighbours_index_kd(ck_norm, cs_tree, nsmax, dmax_norm)
                for cs_idx, ck_idx in cs_ck_dict.items():
                    ckhs_idx_list.append([ck_idx, (), cs_idx])
    else:
        raise ValueError("Now we can not consider non-gaussian GK." )

    configured_arguments =\
        (ck, ch, cs, zh, zs,
        covmodel, covparam, covmat,
        order, options,
        nhmax, nsmax, dmax,
        general_knowledge,
        pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
        gui_args)
    output_arguments = \
        (ckhs_idx_list,)
    print('done')
    return (output_arguments, configured_arguments)

def __get_khs_size(k,h,s):
    if k.shape[0] == 0:
        raise ValueError('ck can not be empty.')
    else:
        return list(map(__get_coord_size,[k, h, s]))

def __get_coord_size(c):
    n = c.shape[0] if c is not None else 0
    return n

def __get_all_split(ck, ch, cs, zh, zs, covmodel, covparam, covmat, order):
    nk, nh, ns = __get_khs_size(ck, ch, cs)
    x_all_split = _get_x_all_split(nk, zh, zs)
    mean_all_split = _get_mean_all_split(x_all_split, order)
    if covmat is not None:
        cov_all_split = np.vsplit(
            covmat, [nk, nk+nh, nk+nh+ns]
            )[:-1] #exclude final empty array
        cov_all_split = \
            [np.hsplit(c, [nk, nk+nh, nk+nh+ns][:-1])\
            for c in cov_all_split]
    else:
        cov_all_split =\
            _get_cov_all_split(ck, ch, cs, covmodel, covparam)
        cov_k_khs = np.hstack([i for i in cov_all_split[0] if i is not None])
        if len([i for i in cov_all_split[1] if i is not None]) != 0:
            cov_h_khs = np.hstack([i for i in cov_all_split[1] if i is not None])
        else:
            cov_h_khs = np.array([]).reshape((-1, cov_k_khs.shape[1]))
        if len([i for i in cov_all_split[2] if i is not None]) != 0:
            cov_s_khs = np.hstack([i for i in cov_all_split[2] if i is not None])
        else:
            cov_s_khs = np.array([]).reshape((-1, cov_k_khs.shape[1]))
        covmat = np.vstack([cov_k_khs, cov_h_khs, cov_s_khs])
    return x_all_split, mean_all_split, cov_all_split, covmat

def __get_normalized_constant(
    x_all_split, mean_all_split, cov_all_split, zs, 
    sub_multi = 's_h', sub_s='s'):

    NC, useful_args = _get_int_fg_a_given_b_fs_s(
        x_all_split, mean_all_split,
        cov_all_split, zs, 
        sub_multi = 's_h', sub_s='s'
        )
    return NC

def __get_covmat_remove_index(covmat):
    if np.linalg.matrix_rank(covmat) < covmat.shape[0]:
        # print('warning: matrix rank less than covmat row')
        has_remove_index = True
        diff_n = covmat.shape[0] - np.linalg.matrix_rank(covmat)
        corrmat = np.corrcoef(covmat)
        remove_index = np.vstack(
            np.unravel_index(
                (np.abs(corrmat).ravel()).argsort(),
                covmat.shape
                )
            ).T
        remove_index = remove_index[
            remove_index[:, 0] < remove_index[:, 1]
            ]
        remove_index_res = np.unique(remove_index[:, 1][-diff_n:])
        remove_index_len = remove_index_res.size
        i = 1
        while remove_index_len < diff_n:
            remove_index_res = np.unique(remove_index[:, 1][-(diff_n+i):])
            remove_index_len = remove_index_res.size
            i += 1
        # print('warning: remove_index_res:', remove_index_res)
    else:
        has_remove_index = False
        remove_index_res = np.array([])
    return has_remove_index, remove_index_res


def _find_ck_cs_near_duplicates(covmat, nk, nh, ns):
    """Detect near-duplicate ck-cs pairs using covariance matrix row
    correlation.

    This is a unit-free, scale-free criterion: when two locations are
    nearly co-located, their covariance rows become nearly identical,
    so ``np.corrcoef`` (Pearson correlation between rows) approaches 1.
    No distance threshold or coordinate-unit knowledge is needed.

    Parameters
    ----------
    covmat : (n, n) ndarray
        Joint covariance matrix ordered as [ck, ch, cs].
    nk, nh, ns : int
        Number of estimation, hard, and soft data points.

    Returns
    -------
    ck_dup_idx : 1-D int array
        Indices into ck that are near-duplicates of some cs.
    cs_dup_partner : 1-D int array
        For each entry in *ck_dup_idx*, the index into cs of its partner.
    is_rank_deficient : bool
        True if covmat is rank-deficient (regardless of whether
        ck-cs duplicates were found).
    """
    _CORR_THRESH = 1.0 - 1e-6   # dimensionless threshold

    rank = np.linalg.matrix_rank(covmat)
    n_total = covmat.shape[0]
    if rank >= n_total:
        return (np.array([], dtype=int),
                np.array([], dtype=int),
                False)

    # Row-correlation matrix (unit-free)
    corrmat = np.corrcoef(covmat)

    # Extract the ck-vs-cs block:
    #   ck indices  = [0, nk)
    #   ch indices  = [nk, nk+nh)
    #   cs indices  = [nk+nh, nk+nh+ns)
    ck_cs_corr = np.abs(corrmat[:nk, nk + nh: nk + nh + ns])

    # Find (ck_i, cs_j) pairs with near-perfect correlation
    dup_pairs = np.argwhere(ck_cs_corr > _CORR_THRESH)

    if dup_pairs.size == 0:
        return (np.array([], dtype=int),
                np.array([], dtype=int),
                True)  # rank-deficient but no ck-cs dups

    # Each ck should map to at most one cs partner (take the first)
    ck_dup_idx = []
    cs_dup_partner = []
    _seen_ck = set()
    for ck_i, cs_j in dup_pairs:
        if ck_i not in _seen_ck:
            ck_dup_idx.append(ck_i)
            cs_dup_partner.append(cs_j)
            _seen_ck.add(ck_i)

    return (np.array(ck_dup_idx, dtype=int),
            np.array(cs_dup_partner, dtype=int),
            True)


# ===================================================================
# Adaptive Neighborhood Selection & Assimilation
# ===================================================================

def _pivoted_cholesky_select(cov_dd, relevance, n_select,
                             min_pivot_ratio=1e-8):
    """Relevance-weighted pivoted Cholesky decomposition for selecting
    a linearly independent, informative subset of data points.

    The algorithm greedily picks the data point whose *residual variance*
    (diagonal of the Schur complement) times *relevance weight* is
    largest, then deflates.  This naturally avoids selecting near-
    duplicate points because deflation drives their residual variance to
    zero.

    Parameters
    ----------
    cov_dd : (n, n) ndarray
        Covariance matrix of the candidate data neighbourhood
        (hard *and* soft combined, ordered [ch; cs]).
    relevance : (n,) ndarray
        Per-point relevance score (e.g. |cov(ck, d_i)| averaged over
        ck batch).  Must be >= 0.
    n_select : int
        Maximum number of points to retain.
    min_pivot_ratio : float, optional
        Stop early when the best weighted pivot drops below
        ``min_pivot_ratio * first_pivot``.

    Returns
    -------
    selected : 1-D int array of length <= n_select
        Indices (into ``cov_dd``) of the selected data points, in
        selection order.
    """
    n = cov_dd.shape[0]
    n_select = min(n_select, n)
    if n_select <= 0:
        return np.array([], dtype=int)

    # Work on a copy – we modify the diagonal during deflation
    diag = np.diag(cov_dd).copy()
    diag = np.maximum(diag, 0.0)          # safety: clip any -ε artefact
    relevance = np.asarray(relevance, dtype=float).copy()
    relevance = np.maximum(relevance, 0.0)

    L = np.zeros((n, n_select), dtype=float)  # Cholesky factor (col-major)
    selected = np.empty(n_select, dtype=int)
    remaining = np.ones(n, dtype=bool)

    first_pivot = None

    for j in range(n_select):
        # Weighted residual variance
        score = diag * relevance
        score[~remaining] = -1.0

        best = int(np.argmax(score))
        best_val = score[best]

        if first_pivot is None:
            first_pivot = best_val if best_val > 0 else 1.0
        if best_val < min_pivot_ratio * first_pivot:
            selected = selected[:j]
            break

        selected[j] = best
        remaining[best] = False

        pivot_std = np.sqrt(max(diag[best], 1e-300))
        L[best, j] = pivot_std

        # Deflate: compute column j of the Cholesky factor
        col = cov_dd[best, :].copy()
        if j > 0:
            col -= L[:, :j] @ L[best, :j]
        col /= pivot_std
        L[:, j] = col
        # Update residual diagonal
        diag -= col ** 2
        diag = np.maximum(diag, 0.0)

    return selected


def _build_merge_map(cov_dd, selected, n_data):
    """Map each discarded point to its most-correlated retained partner.

    Parameters
    ----------
    cov_dd : (n, n) ndarray
        Covariance matrix of the full neighbourhood (before selection).
    selected : 1-D int array
        Indices of retained points.
    n_data : int
        Total number of candidate data points (``n``).

    Returns
    -------
    merge_map : dict  {int -> int}
        ``merge_map[discarded_idx] = retained_idx``.
        Only contains entries for *discarded* points.
    """
    all_idx = np.arange(n_data)
    sel_set = set(selected)
    discarded = np.array([i for i in all_idx if i not in sel_set], dtype=int)

    merge_map = {}
    if discarded.size == 0 or selected.size == 0:
        return merge_map

    # Use absolute correlation to handle negative cross-covariance
    sel_arr = np.asarray(selected)
    for d_i in discarded:
        # Covariance between d_i and each retained point
        cov_row = np.abs(cov_dd[d_i, sel_arr])
        best_partner = sel_arr[int(np.argmax(cov_row))]
        merge_map[int(d_i)] = int(best_partner)

    return merge_map


def _assimilate_neighborhood(picked_ck, picked_ch, picked_cs,
                             picked_zh, picked_zs, picked_covmat,
                             nhmax_nsmax_total=None,
                             min_pivot_ratio=1e-8, min_merge_var=1e-6):
    """Adaptive neighbourhood selection + information-preserving assimilation.

    1. **Select** the most informative, linearly independent subset of
       data via relevance-weighted pivoted Cholesky.
    2. **Assimilate** each discarded point into its most-correlated
       retained partner so that observational information is *not* lost.

    Assimilation rules (type-aware)
    -------------------------------
    * **Hard + Hard** → Soft Gaussian: mean = average of two values,
      var = (difference / 2)² + ``min_merge_var``.
    * **Hard + Soft** → The hard datum dominates (informational certainty);
      the soft datum is dropped to avoid double-counting.
    * **Soft + Soft** → Equal-weight Gaussian mixture approximated as a
      single Gaussian via moment matching.  Works for all soft types
      (histogram, linear, Gaussian) because ``proba2stat`` extracts
      (mean, var) from any of them.

    Parameters
    ----------
    picked_ck : (nk_batch, d) ndarray  – estimation points for this batch.
    picked_ch : (nh_local, d) ndarray or None – local hard-data coords.
    picked_cs : (ns_local, d) ndarray or None – local soft-data coords.
    picked_zh : (nh_local, 1) ndarray or None – hard observations.
    picked_zs : list of soft-data tuples or None
        Each element is ``(pdf_type, nl, limi, probdens)`` for histogram/
        linear, or ``(pdf_type, mean, var)`` for Gaussian (type 10).
    picked_covmat : (nk+nh+ns, nk+nh+ns) ndarray or None
        Joint covariance matrix ordered [ck; ch; cs].
    nhmax_nsmax_total : int or None
        Budget for total retained data points (hard + soft).
        If None, defaults to nh + ns (no budget limit, only linear-
        independence pruning).
    min_pivot_ratio : float
        Passed to ``_pivoted_cholesky_select``.
    min_merge_var : float
        Minimum variance injected when merging two hard data points
        into a soft Gaussian.

    Returns
    -------
    new_ck, new_ch, new_cs, new_zh, new_zs, new_covmat
        Possibly smaller arrays after assimilation.  ``new_ch`` may
        shrink and ``new_cs`` / ``new_zs`` may grow when Hard+Hard
        merges create new soft data.
    """
    nk = picked_ck.shape[0]
    nh = picked_ch.shape[0] if picked_ch is not None else 0
    ns = picked_cs.shape[0] if picked_cs is not None else 0
    n_data = nh + ns

    # Nothing to do if already tiny
    if n_data <= 1:
        return (picked_ck, picked_ch, picked_cs,
                picked_zh, picked_zs, picked_covmat)

    # ---- 1. Build relevance vector (|mean cov(ck, d_i)|) ----
    if picked_covmat is not None:
        cov_k_d = picked_covmat[:nk, nk:]          # (nk, n_data)
        relevance = np.abs(cov_k_d).mean(axis=0)   # (n_data,)
        cov_dd = picked_covmat[nk:, nk:]            # (n_data, n_data)
    else:
        # If no precomputed covmat we cannot do Cholesky; just pass through
        return (picked_ck, picked_ch, picked_cs,
                picked_zh, picked_zs, picked_covmat)

    # ---- 2. Budget ----
    if nhmax_nsmax_total is None:
        budget = n_data
    else:
        budget = min(int(nhmax_nsmax_total), n_data)

    # ---- 3. Pivoted Cholesky selection ----
    selected = _pivoted_cholesky_select(
        cov_dd, relevance, budget, min_pivot_ratio=min_pivot_ratio)

    if selected.size >= n_data:
        # Everything kept – nothing to do
        return (picked_ck, picked_ch, picked_cs,
                picked_zh, picked_zs, picked_covmat)

    # ---- 4. Build merge map ----
    merge_map = _build_merge_map(cov_dd, selected, n_data)

    # ---- 5. Assimilate ----
    # Represent every datum in a unified indexing: 0..nh-1 = hard,
    # nh..nh+ns-1 = soft.
    # After assimilation we collect final_hard and final_soft lists.

    # Pre-extract (mean, var) for every soft datum
    soft_stats = []  # list of (mean_float, var_float) for each soft point
    for si in range(ns):
        zsi = picked_zs[si] if picked_zs is not None else None
        if zsi is None:
            soft_stats.append((np.nan, np.nan))
            continue
        ptype = get_standard_soft_pdf_type(zsi[0])
        if ptype in (1, 2):
            # histogram / linear → moment-match via proba2stat
            _nl = np.array(zsi[1]).reshape(1, 1)
            _limi = np.array(zsi[2]).reshape(1, -1)
            _pd = np.array(zsi[3]).reshape(1, -1)
            _m, _v = proba2stat(ptype, _nl, _limi, _pd)
            soft_stats.append((float(np.asarray(_m).flat[0]),
                               float(np.asarray(_v).flat[0])))
        elif ptype == 10:
            soft_stats.append((float(np.asarray(zsi[1]).flat[0]),
                               float(np.asarray(zsi[2]).flat[0])))
        else:
            soft_stats.append((np.nan, np.nan))

    # Buckets: for each retained index, collect what gets merged into it
    retained_set = set(int(s) for s in selected)
    merge_buckets = {int(s): [] for s in selected}
    for d_from, d_to in merge_map.items():
        merge_buckets[d_to].append(d_from)

    # Final data lists
    final_ch_list = []    # coordinates
    final_zh_list = []    # observations
    final_cs_list = []    # coordinates
    final_zs_list = []    # soft data tuples
    retained_data_indices = []   # original data indices for covmat slicing

    def _is_hard(idx):
        return idx < nh

    def _get_hard_val(idx):
        return float(picked_zh[idx].flat[0])

    def _get_hard_coord(idx):
        return picked_ch[idx]

    def _get_soft_coord(idx):
        return picked_cs[idx - nh]

    def _get_soft_mean_var(idx):
        return soft_stats[idx - nh]

    def _get_soft_tuple(idx):
        return picked_zs[idx - nh]

    def _make_gaussian_zs(mean, var):
        """Create a Gaussian soft datum tuple (type=10, mean, var)."""
        return (10, float(mean), max(float(var), min_merge_var))

    for ret_idx in sorted(retained_set):
        to_merge = merge_buckets[ret_idx]

        if not to_merge:
            # --- No merges: keep datum as-is ---
            if _is_hard(ret_idx):
                final_ch_list.append(_get_hard_coord(ret_idx))
                final_zh_list.append(_get_hard_val(ret_idx))
            else:
                final_cs_list.append(_get_soft_coord(ret_idx))
                final_zs_list.append(_get_soft_tuple(ret_idx))
            retained_data_indices.append(ret_idx)
            continue

        # --- Merge required ---
        # Collect all participants: retained + discarded
        participants = [ret_idx] + to_merge

        n_hard_parts = sum(1 for p in participants if _is_hard(p))
        n_soft_parts = len(participants) - n_hard_parts

        if n_hard_parts == len(participants):
            # ---- All Hard → convert to Soft Gaussian ----
            vals = np.array([_get_hard_val(p) for p in participants])
            merge_mean = float(np.mean(vals))
            merge_var = float(np.var(vals)) + min_merge_var
            # Use coordinate of the retained point
            final_cs_list.append(_get_hard_coord(ret_idx))
            final_zs_list.append(_make_gaussian_zs(merge_mean, merge_var))
            retained_data_indices.append(ret_idx)

        elif n_hard_parts > 0 and n_soft_parts > 0:
            # ---- Hard + Soft mixture → Hard dominates ----
            # Keep the hard datum as-is; soft information is approximately
            # captured by the hard observation.  (Hard is delta-function,
            # which overwhelms any soft PDF in the posterior.)
            hard_parts = [p for p in participants if _is_hard(p)]
            # If multiple hard data merge here, average them into soft
            if len(hard_parts) == 1:
                h_idx = hard_parts[0]
                final_ch_list.append(_get_hard_coord(h_idx))
                final_zh_list.append(_get_hard_val(h_idx))
            else:
                vals = np.array([_get_hard_val(p) for p in hard_parts])
                merge_mean = float(np.mean(vals))
                merge_var = float(np.var(vals)) + min_merge_var
                final_cs_list.append(_get_hard_coord(hard_parts[0]))
                final_zs_list.append(_make_gaussian_zs(merge_mean, merge_var))
            retained_data_indices.append(ret_idx)

        else:
            # ---- All Soft → Gaussian mixture moment matching ----
            means_vars = [_get_soft_mean_var(p) for p in participants]
            # Filter out NaN entries
            valid = [(m, v) for m, v in means_vars
                     if np.isfinite(m) and np.isfinite(v) and v > 0]
            if not valid:
                # Fallback: keep retained datum as-is
                final_cs_list.append(_get_soft_coord(ret_idx))
                final_zs_list.append(_get_soft_tuple(ret_idx))
                retained_data_indices.append(ret_idx)
                continue
            # Equal-weight mixture → moment matching
            mix_means = np.array([m for m, _ in valid])
            mix_vars = np.array([v for _, v in valid])
            w = 1.0 / len(valid)
            merged_mean = float(np.sum(w * mix_means))
            merged_var = float(
                np.sum(w * (mix_vars + mix_means ** 2)) - merged_mean ** 2)
            merged_var = max(merged_var, min_merge_var)
            final_cs_list.append(_get_soft_coord(ret_idx))
            final_zs_list.append(_make_gaussian_zs(merged_mean, merged_var))
            retained_data_indices.append(ret_idx)

    # ---- 6. Rebuild arrays ----
    new_nh = len(final_ch_list)
    new_ns = len(final_cs_list)
    new_ch = (np.array(final_ch_list) if new_nh > 0 else None)
    new_cs = (np.array(final_cs_list) if new_ns > 0 else None)
    new_zh = (np.array(final_zh_list).reshape(-1, 1) if new_nh > 0
              else None)
    new_zs = final_zs_list if new_ns > 0 else None

    # ---- 7. Rebuild covmat ----
    # We keep the rows/cols of the retained data points.
    # New soft data created from merges re-use the retained point's row
    # (since they occupy the same spatial location → same covariance).
    retained_data_indices = np.array(retained_data_indices, dtype=int)
    # Map back to original covmat indices: ck part stays, data part maps
    keep_ck = np.arange(nk)
    keep_data = nk + retained_data_indices  # offset into full covmat
    keep_all = np.concatenate([keep_ck, keep_data])
    new_covmat = picked_covmat[np.ix_(keep_all, keep_all)]

    # The new covmat ordering is [ck; mixed_h_s].
    # We need to reorder it to [ck; new_ch; new_cs].
    # Since we appended hard then soft in order, this is already correct
    # *if* the output ch/cs arrays match the retained_data_indices order.
    # But merges can change hard→soft.  We need a proper reorder.

    # Build the mapping: which of the retained_data_indices are hard
    # and which are soft in the *output*.
    # After the loop above, data in new_covmat[nk:] corresponds to
    # retained_data_indices order (which is sorted).
    # We just need to know: in the output, which positions are hard and
    # which are soft (they may have changed due to Hard+Hard→Soft merges).
    # The caller (_bme_posterior_moments) expects covmat ordered as
    # [ck, ch, cs].  We've built ch_list first, then cs_list, so let's
    # reorder the data block of the covmat accordingly.

    # The retained_data_indices entries that contributed to final_ch_list
    # come first, then those that contributed to final_cs_list.
    # We tracked this via the order we appended:
    # We rebuild a permutation.
    perm_data = []  # indices into retained_data_indices
    _cur = 0
    # We go through retained_data_indices in order, same order as the
    # final_*_list construction (sorted retained_set order).
    # So perm_data is just 0..len(retained_data_indices)-1 split into
    # hard-slots first, soft-slots second.
    # Actually, we need to track this more carefully.

    # Simpler approach: since we're iterating retained_set in sorted order
    # and appending to ch or cs lists, let's just record which output
    # slot each retained_data_index maps to.
    # Re-derive: go through sorted retained, flag H or S.
    _h_perm = []
    _s_perm = []
    for i, ret_idx in enumerate(sorted(retained_set)):
        to_merge = merge_buckets[ret_idx]
        participants = [ret_idx] + to_merge
        n_hard_parts = sum(1 for p in participants if _is_hard(p))
        n_soft_parts = len(participants) - n_hard_parts
        if not to_merge:
            if _is_hard(ret_idx):
                _h_perm.append(i)
            else:
                _s_perm.append(i)
        elif n_hard_parts == len(participants):
            _s_perm.append(i)   # became soft
        elif n_hard_parts > 0 and n_soft_parts > 0:
            hard_parts = [p for p in participants if _is_hard(p)]
            if len(hard_parts) == 1:
                _h_perm.append(i)
            else:
                _s_perm.append(i)   # became soft
        else:
            _s_perm.append(i)

    data_perm = np.array(_h_perm + _s_perm, dtype=int)
    # Reorder the data block of new_covmat
    n_kept = retained_data_indices.size
    data_block_idx = nk + data_perm
    full_perm = np.concatenate([np.arange(nk), data_block_idx])
    new_covmat = new_covmat[np.ix_(full_perm, full_perm)]

    _msg_parts = []
    if nh != new_nh or ns != new_ns:
        _msg_parts.append(
            "nh: {} -> {}, ns: {} -> {}".format(nh, new_nh, ns, new_ns))
    if n_data - int(selected.size) > 0:
        _msg_parts.append("{} points discarded, {} merged".format(
            n_data - int(selected.size), len(merge_map)))
    if _msg_parts:
        print("[STARBME] Assimilation: " + "; ".join(_msg_parts))

    return (picked_ck, new_ch, new_cs, new_zh, new_zs, new_covmat)


def __check_normalized_constant(NC, options):
    if NC == 0:
        print('Warning NC is equals to zero.')
        if options['debug']:
            pass
    elif np.isnan(NC):
        print('NC is equals to NaN.')
        if options['debug']:
            pass
    elif np.isinf(NC):
        print('NC is equals to Inf.')
        if options['debug']:
            pass
    return NC

def _process_estimation_chunk(
    ck_idx_piece, picked_ch, picked_cs, picked_zh, picked_zs,
    ck, ch, cs, zh, zs,
    covmat, covmodel, covparam, order, options,
    general_knowledge, has_user_defined_general_knowledge,
    pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
    ck_cov_output, ch_idx, cs_idx, nk, nh):
    """Process a single chunk of estimation points for parallel dispatch.

    This is a standalone function that can be called from a thread pool.
    It performs assimilation, order picking, and BME estimation for one
    chunk of estimation locations sharing the same neighborhood.

    Returns
    -------
    (ck_idx_piece, picked_mvs) : tuple
        The original index array and the estimated moments (4-column).
    """
    picked_ck = ck[ck_idx_piece, :]
    if covmat is not None:
        covidx = np.hstack(
            (ck_idx_piece, nk + ch_idx, nk + nh + cs_idx))
        picked_covmat = covmat[np.ix_(covidx, covidx)]
    else:
        picked_covmat = covmat

    # --- Adaptive neighbourhood assimilation ---
    if picked_covmat is not None:
        try:
            (picked_ck, picked_ch, picked_cs,
             picked_zh, picked_zs,
             picked_covmat) = _assimilate_neighborhood(
                picked_ck, picked_ch, picked_cs,
                picked_zh, picked_zs, picked_covmat)
        except Exception as _assim_err:
            import warnings as _w
            _w.warn(
                "[STARBME] Assimilation skipped: {}"
                .format(_assim_err))

    # picked order for specified general knowledge
    if has_user_defined_general_knowledge:
        _nh_a = picked_ch.shape[0] if picked_ch is not None else 0
        _ns_a = picked_cs.shape[0] if picked_cs is not None else 0
        _nk_a = picked_ck.shape[0]
        order_idx = np.hstack(
            (ck_idx_piece, nk + ch_idx, nk + nh + cs_idx))
        if order_idx.shape[0] == _nk_a + _nh_a + _ns_a:
            picked_order = order[order_idx, :]
        else:
            picked_order = order[ck_idx_piece, :]
            _remaining = _nh_a + _ns_a
            if _remaining > 0 and order.shape[0] > nk:
                _data_order = order[nk:, :]
                _mean_row = np.mean(_data_order, axis=0,
                                    keepdims=True)
                picked_order = np.vstack([
                    picked_order,
                    np.tile(_mean_row, (_remaining, 1))])
    else:
        picked_order = order

    try:
        picked_mvs = _bme_posterior_moments(
            picked_ck, picked_ch, picked_cs,
            picked_zh, picked_zs,
            covmodel, covparam, picked_covmat,
            picked_order, options, general_knowledge,
            pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
            None, ck_cov_output)  # gui_args=None for thread safety
    except (np.linalg.LinAlgError, TypeError, ValueError) as e:
        import warnings
        _nh = picked_ch.shape[0] if picked_ch is not None else 0
        _ns = picked_cs.shape[0] if picked_cs is not None else 0
        warn_msg = (
            "BME estimation failed for estimation location(s):\n"
            "  ck = {ck}\n"
            "  Number of hard data in neighborhood: {nh}\n"
            "  Number of soft data in neighborhood: {ns}\n"
            "  Error: {err}\n"
            "This may indicate a singular or ill-conditioned "
            "covariance matrix."
        ).format(ck=picked_ck, nh=_nh, ns=_ns, err=str(e))
        warnings.warn(warn_msg)
        picked_mvs = np.empty((picked_ck.shape[0], 4))
        picked_mvs[:] = np.nan

    # Pad Gaussian-path results (3-col) to 4-col with delta_mu=0
    if (isinstance(picked_mvs, np.ndarray)
            and picked_mvs.ndim == 2
            and picked_mvs.shape[1] == 3):
        picked_mvs = np.hstack([
            picked_mvs,
            np.zeros((picked_mvs.shape[0], 1))])

    return (ck_idx_piece, picked_mvs)


def BMEPosteriorMoments(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None,
    nhmax=None, nsmax=None, dmax=None,
    general_knowledge='gaussian',
    #  specific_knowledge='unknown',  
    pdfk=None,pdfh=None,pdfs=None,hk_k=None,hk_h=None,hk_s=None,
    gui_args=None, ck_cov_output=False, n_workers=1):
    '''
    ck: n by d np 2d array
        the estimated data coordinate, usually, d = 3 for spatial-temporal
        coordinate, first two column for spatial, e.g. x, y, and last column
        for temporal, e.g. t.

    ch: n by d np 2d array
        the hard data coordinate.

    cs: n by d np 2d array
        the soft data coordinate.

    zh: n by 1 np 2d array
        the hard data measurement.

    zs: a sequence of soft data record, e.g. (zs1, zs2, zs3, ..., zsn)
        each zsi(i=1~n) is a sequence of data arguments,
        first item should be softpdftype to determind
        the other rest arguments format, e.g.
        syntax: (softdata_type, *softdata_args)
            zs1 = (1, nl, limi, probdens)
            zs2 = (10, zm, zstd)
        if element is emtpy, put None
            e.g. (zs1, zs2, None, ..., zsn)

    covmodel: 

    covmat:
        covariance matrix, a np 2d array
        with shape (nk+nh+ns) by (nk+nh+ns)
    if covmat provieded, covmodel and covparam are simply skipped.
    
    #SI = integrate (fg_s_given_kh * fs_s) dx_s
    #NC = integrate (fg_s_given_h * fs_s) dx_s
    #pdf_k = (fg_kh * SI) / (fg_h * NC)  # eq.1
    #exp_k = ... # eq.2
    #exp_kp = ... # eq.3
    #if general_knowledge == gaussian and specific_knowledge == unknown
    #exp_k = ... # eq.4
    #var_k = ... # eq.5

    gui_args: a tuple with gui arguments

    
    return 
    '''
    (output_arguments, configured_arguments) = _bme_posterior_prepare(
        ck, ch, cs, zh, zs,
        covmodel, covparam, covmat,
        order, options,
        nhmax, nsmax, dmax,
        general_knowledge,
        pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
        gui_args)
    (ckhs_idx_list,) = output_arguments

    (ck, ch, cs, zh, zs,
        covmodel, covparam, covmat,
        order, options,
        nhmax, nsmax, dmax,
        general_knowledge,
        pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
        gui_args) = configured_arguments

    if isinstance(order, np.ndarray):
        has_user_defined_general_knowledge = True
    elif order == 0 or np.isnan(order):
        has_user_defined_general_knowledge = False
    else:
        raise ValueError('order type error')

    nk = ck.shape[0]
    nh = ch.shape[0] if ch is not None else 0
    ns = cs.shape[0] if cs is not None else 0
    zk = np.empty((nk, 4))  # [mean, variance, skewness, delta_mu (QMC error)]
    zk[:, 3] = 0.0  # default delta_mu = 0 (Gaussian path has no QMC noise)
    cur_cnt = 0
    cum_cnt = 0

    # --- Performance logging ---
    import time as _time
    _t_start = _time.time()
    _approx_mode = (options is not None
                    and options['soft_approx_gaussian'])
    if ns > 0:
        _all_types = set(
            get_standard_soft_pdf_type(zsi[0]) for zsi in zs if zsi is not None)
        _has_nongaussian = bool(_all_types - {10})
        print("[STARBME] BME estimation: nk={}, nh={}, ns={}, "
              "soft types={}, approx_gaussian={}".format(
                  nk, nh, ns, _all_types, _approx_mode))
        if _has_nongaussian and not _approx_mode:
            print("[STARBME] WARNING: Non-Gaussian soft data detected. "
                  "Using QMC integration (slow). Enable 'Fast Gaussian "
                  "Approximation' in Prediction > Configures for speed-up.")
    else:
        print("[STARBME] BME estimation: nk={}, nh={}, ns=0".format(nk, nh))

    # --- Ensure n_workers is sane ---
    n_workers = max(1, int(n_workers))

    if general_knowledge == 'gaussian':
        # ---- Build list of independent work items ----
        _work_items = []
        for ck_idx, ch_idx, cs_idx in ckhs_idx_list:
            ck_idx = np.array(ck_idx, dtype=int)
            ch_idx = np.array(ch_idx, dtype=int)
            cs_idx = np.array(cs_idx, dtype=int)
            # Fresh copies per neighborhood group so that assimilation
            # in one chunk does not corrupt data for sibling chunks.
            picked_ch = (
                ch[ch_idx, :].copy() if isinstance(ch, np.ndarray) else None)
            picked_cs = (
                cs[cs_idx, :].copy() if isinstance(cs, np.ndarray) else None)
            picked_zh = (
                zh[ch_idx, :].copy() if isinstance(zh, np.ndarray) else None)
            picked_zs = (
                [zs[cs_idx_i] for cs_idx_i in cs_idx]
                if zs is not None else None)
            ck_count = ck_idx.shape[0]
            split_count = np.ceil(ck_count / 250.)
            for ck_idx_piece in np.array_split(ck_idx, split_count):
                # Each chunk gets its own copy of neighbourhood data
                # to prevent cross-chunk corruption from assimilation.
                _work_items.append(dict(
                    ck_idx_piece=ck_idx_piece,
                    picked_ch=picked_ch.copy() if picked_ch is not None else None,
                    picked_cs=picked_cs.copy() if picked_cs is not None else None,
                    picked_zh=picked_zh.copy() if picked_zh is not None else None,
                    picked_zs=list(picked_zs) if picked_zs is not None else None,
                    ch_idx=ch_idx,
                    cs_idx=cs_idx,
                ))

        _n_chunks = len(_work_items)

        # ---- Parallel or sequential dispatch ----
        if n_workers > 1 and _n_chunks > 1:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading

            _actual_workers = min(n_workers, _n_chunks)
            print("[STARBME] Parallel estimation: {} chunks across {} "
                  "threads".format(_n_chunks, _actual_workers))

            _cancel_event = threading.Event()

            def _submit_chunk(item):
                """Wrapper to check cancellation before heavy work."""
                if _cancel_event.is_set():
                    return (item['ck_idx_piece'], None)
                return _process_estimation_chunk(
                    ck_idx_piece=item['ck_idx_piece'],
                    picked_ch=item['picked_ch'],
                    picked_cs=item['picked_cs'],
                    picked_zh=item['picked_zh'],
                    picked_zs=item['picked_zs'],
                    ck=ck, ch=ch, cs=cs, zh=zh, zs=zs,
                    covmat=covmat, covmodel=covmodel,
                    covparam=covparam, order=order, options=options,
                    general_knowledge=general_knowledge,
                    has_user_defined_general_knowledge=has_user_defined_general_knowledge,
                    pdfk=pdfk, pdfh=pdfh, pdfs=pdfs,
                    hk_k=hk_k, hk_h=hk_h, hk_s=hk_s,
                    ck_cov_output=ck_cov_output,
                    ch_idx=item['ch_idx'], cs_idx=item['cs_idx'],
                    nk=nk, nh=nh)

            with ThreadPoolExecutor(max_workers=_actual_workers) as executor:
                futures = {
                    executor.submit(_submit_chunk, item): item
                    for item in _work_items
                }
                for future in as_completed(futures):
                    ck_idx_piece, picked_mvs = future.result()
                    if picked_mvs is None:
                        # Cancelled
                        _cancel_event.set()
                        return False
                    zk[ck_idx_piece, :] = picked_mvs
                    cur_cnt += ck_idx_piece.size
                    # Update progress on the main thread
                    if gui_args:
                        qpgd = gui_args[0]
                        if qpgd.wasCanceled():
                            _cancel_event.set()
                            # Cancel remaining futures
                            for f in futures:
                                f.cancel()
                            return False
                        else:
                            qpgd.setValue(qpgd.value() + ck_idx_piece.size)
                    else:
                        if cur_cnt - cum_cnt >= 2000:
                            print(cur_cnt, '/', nk)
                            cum_cnt = cur_cnt

        else:
            # ---- Sequential execution (original path) ----
            if n_workers > 1 and _n_chunks <= 1:
                print("[STARBME] Only {} chunk(s) — running "
                      "sequentially".format(_n_chunks))
            for item in _work_items:
                ck_idx_piece, picked_mvs = _process_estimation_chunk(
                    ck_idx_piece=item['ck_idx_piece'],
                    picked_ch=item['picked_ch'],
                    picked_cs=item['picked_cs'],
                    picked_zh=item['picked_zh'],
                    picked_zs=item['picked_zs'],
                    ck=ck, ch=ch, cs=cs, zh=zh, zs=zs,
                    covmat=covmat, covmodel=covmodel,
                    covparam=covparam, order=order, options=options,
                    general_knowledge=general_knowledge,
                    has_user_defined_general_knowledge=has_user_defined_general_knowledge,
                    pdfk=pdfk, pdfh=pdfh, pdfs=pdfs,
                    hk_k=hk_k, hk_h=hk_h, hk_s=hk_s,
                    ck_cov_output=ck_cov_output,
                    ch_idx=item['ch_idx'], cs_idx=item['cs_idx'],
                    nk=nk, nh=nh)
                zk[ck_idx_piece, :] = picked_mvs
                if gui_args:
                    qpgd = gui_args[0]
                    if qpgd.wasCanceled():
                        return False
                    else:
                        qpgd.setValue(qpgd.value() + ck_idx_piece.size)
                else:
                    cur_cnt += ck_idx_piece.size
                    if cur_cnt - cum_cnt >= 2000:
                        print(cur_cnt, '/', nk)
                        cum_cnt = cur_cnt

        print(cur_cnt, '/', nk)
        _elapsed = _time.time() - _t_start
        _n_nan = int(np.sum(np.isnan(zk[:, 0])))
        print("[STARBME] BME estimation completed in {:.1f}s "
              "({:.3f}s per point)".format(_elapsed, _elapsed / max(nk, 1)))
        if _n_nan > 0:
            import warnings
            warnings.warn(
                "[STARBME] {:d} of {:d} estimation locations produced NaN "
                "results. This typically occurs when estimation points are "
                "very close to (but not exactly at) soft data locations, "
                "causing the QMC integration to fail. Consider:\n"
                "  1. Enabling 'Fast Gaussian Approximation' to bypass QMC.\n"
                "  2. Reducing the PCA threshold to lower integration dimension.\n"
                "  3. Checking that estimation grid does not nearly overlap "
                "with soft data locations.".format(_n_nan, nk))

        # --- QMC noise diagnostic ---
        _delta_mu_col = zk[:, 3]
        _valid_delta = ~np.isnan(_delta_mu_col) & (_delta_mu_col > 0)
        if np.any(_valid_delta):
            _dmu = _delta_mu_col[_valid_delta]
            _mu_abs = np.abs(zk[_valid_delta, 0])
            _rel_err = np.where(_mu_abs > 0, _dmu / _mu_abs, np.inf)
            _rel_err_finite = _rel_err[np.isfinite(_rel_err)]
            print("[STARBME] QMC noise diagnostic: "
                  "delta_mu  median={:.4g}, max={:.4g}; "
                  "rel_err  median={:.2%}, max={:.2%} "
                  "({} of {} points had QMC error info)".format(
                      np.median(_dmu), np.max(_dmu),
                      np.median(_rel_err_finite) if len(_rel_err_finite) > 0 else 0,
                      np.max(_rel_err_finite) if len(_rel_err_finite) > 0 else 0,
                      int(np.sum(_valid_delta)), nk))

        # --- Non-negativity constraint ---
        # When QMC IS was used with nonneg_estimate, the integrand
        # already computed truncated-normal moments (flagged by
        # delta_mu == -1).  For Gaussian-fallback and analytical
        # points, post-hoc truncation is still applied by
        # _apply_nonneg_truncation (which skips flagged points).
        if options is not None and options.get('nonneg_estimate', False):
            _n_neg_before = int(np.nansum(zk[:, 0] < 0))
            _n_qmc_nonneg = int(np.sum(zk[:, 3] < 0)) if zk.shape[1] >= 4 else 0
            zk = _apply_nonneg_truncation(zk)  # returns 3-col
            print("[STARBME] Non-negativity correction: {} points total, "
                  "{} via QMC integrand, {} via post-hoc truncation. "
                  "{} had negative means (clamped to 0).".format(
                      nk, _n_qmc_nonneg, nk - _n_qmc_nonneg,
                      _n_neg_before))
        else:
            zk = zk[:, :3]  # strip delta_mu column

        return zk
    else:
      nk=len(pdfk)
      moments=np.empty((nk,3))

      for k in range(nk):
        print ('BME MOMENTS:' + str(k+1) + '/' + str(nk))
        
        cklocal=ck[k:k+1,:]
        pdfk_local=[pdfk[k]]
        hk_k_local=[hk_k[k]]
        
        pdf_k=BMEPosteriorPDF(cklocal, ch, cs, zh, zs, covmodel, covparam,
              order, options, nhmax, nsmax, dmax, general_knowledge,
              pdfk=pdfk_local,pdfh=pdfh,pdfs=pdfs,
              hk_k=hk_k_local,hk_h=hk_h,hk_s=hk_s)[0]
          
        zmin=hk_k[k][0]-6*np.sqrt(hk_k[k][1])
        zmax=hk_k[k][0]+6*np.sqrt(hk_k[k][1])
        # Non-negativity: restrict integration domain to [0, ∞)
        if options is not None and options.get('nonneg_estimate', False):
            zmin = max(zmin, 0.0)
        
        xxx=np.linspace(zmin,zmax,100)
        aaa=pdf_k(xxx,0)

        maxpts = options[2][0]
        aEps = 0
        rEps = options[3][0]

        from cubature import cubature

        mon1_for_cubature = lambda x_array: x_array[:,0] * pdf_k(x_array[:,0],0)[:,0]
        mon1,mon1_err = cubature(
            func=mon1_for_cubature, ndim=1, fdim=1, xmin=np.array([zmin]),
            xmax=np.array([zmax]), adaptive='h', maxEval = maxpts,
            abserr = 0, relerr = rEps, vectorized = True)
        mon2_for_cubature = lambda x_array: x_array[:,0]**2 * pdf_k(x_array[:,0],0)[:,0]
        mon2,mon2_err = cubature(
            func=mon2_for_cubature,ndim=1, fdim=1, xmin=np.array([zmin]),
            xmax=np.array([zmax]), adaptive='h', maxEval = maxpts,
            abserr = 0, relerr = rEps, vectorized = True)  
        mon3_for_cubature = lambda x_array: x_array[:,0]**3 * pdf_k(x_array[:,0],0)[:,0]
        mon3,mon3_err = cubature(
            func=mon3_for_cubature,ndim=1, fdim=1, xmin=np.array([zmin]),
            xmax=np.array([zmax]), adaptive='h', maxEval = maxpts,
            abserr = 0, relerr = rEps, vectorized = True)

        moments[k,0]=mon1
        moments[k,1]=mon2-mon1**2
        moments[k,2]=mon3-3*mon1*mon2-mon1**3

      return moments[:,0], moments[:,1], moments[:,2]

def BMEPosteriorPDF(
    ck, ch=None, cs=None, zh=None, zs=None,
    covmodel=None, covparam=None, covmat=None,
    order=np.nan, options=None,
    nhmax=None, nsmax=None, dmax=None,
    general_knowledge='gaussian',
    #  specific_knowledge='unknown',  
    pdfk=None,pdfh=None,pdfs=None,hk_k=None,hk_h=None,hk_s=None,
    gui_args=None):

    (output_arguments, configured_arguments) = _bme_posterior_prepare(
        ck, ch, cs, zh, zs,
        covmodel, covparam, covmat,
        order, options,
        nhmax, nsmax, dmax,
        general_knowledge,
        pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
        gui_args)
    (ckhs_idx_list,) = output_arguments

    (ck, ch, cs, zh, zs,
        covmodel, covparam, covmat,
        order, options,
        nhmax, nsmax, dmax,
        general_knowledge,
        pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
        gui_args) = configured_arguments
   
    if isinstance(order, np.ndarray):
        has_user_defined_general_knowledge = True
    elif order == 0 or np.isnan(order):
        has_user_defined_general_knowledge = False
    else:
        raise ValueError('order type error')
    nk = ck.shape[0]
    nh = ch.shape[0] if ch is not None else 0
    ns = cs.shape[0] if cs is not None else 0
    zk = np.empty((ck.shape[0],1), dtype=object) # to 1 pdf function
    if general_knowledge == 'gaussian':
        for ck_idx, ch_idx, cs_idx in ckhs_idx_list:
            ck_idx = np.array(ck_idx, dtype=int)
            ch_idx = np.array(ch_idx, dtype=int)
            cs_idx = np.array(cs_idx, dtype=int)
            picked_ch =\
                ch[ch_idx, :] if isinstance(ch, np.ndarray) else None
            picked_cs =\
                cs[cs_idx, :] if isinstance(cs, np.ndarray) else None
            picked_zh =\
                zh[ch_idx, :] if isinstance(zh, np.ndarray) else None
            picked_zs =\
                [zs[cs_idx_i] for cs_idx_i in cs_idx] if zs is not None else None
            ck_count = ck_idx.shape[0]
            split_count = np.ceil(ck_count/250.)
            for ck_idx_piece in np.array_split(ck_idx, split_count):
                picked_ck = ck[ck_idx_piece, :]
                if covmat is not None:
                    covidx = np.hstack(
                        (ck_idx_piece, nk+ch_idx, nk+nh+cs_idx)
                        )
                    picked_covmat = covmat[np.ix_(covidx, covidx)]
                else:
                    picked_covmat = covmat

                # --- Adaptive neighbourhood assimilation (PDF path) ---
                if picked_covmat is not None:
                    try:
                        (picked_ck, picked_ch, picked_cs,
                         picked_zh, picked_zs,
                         picked_covmat) = _assimilate_neighborhood(
                            picked_ck, picked_ch, picked_cs,
                            picked_zh, picked_zs, picked_covmat)
                    except Exception:
                        pass  # fall through with original data

                #picked order for specified general knowledge
                if has_user_defined_general_knowledge:
                    order_idx = np.hstack(
                        (ck_idx_piece, nk+ch_idx, nk+nh+cs_idx)
                        )
                    picked_order = order[order_idx, :]
                else:
                    picked_order = order

                try:
                    picked_mvs = _bme_posterior_pdf(
                        picked_ck, picked_ch, picked_cs,
                        picked_zh, picked_zs,
                        covmodel, covparam, picked_covmat,
                        picked_order, options, general_knowledge,
                        pdfk, pdfh, pdfs, hk_k, hk_h, hk_s,
                        gui_args)
                except Exception as e:
                    # import pdb
                    # pdb.set_trace()
                    raise e
                zk[ck_idx_piece, :] = picked_mvs
                if gui_args:
                    if gui_args[0].wasCanceled(): #cancel by user
                        return False
                    else:
                        gui_args[0].setValue(gui_args[0].value()+ck_idx_piece.size)
        return zk

def BMEPosteriorPDF_backup(
  ck, ch, cs, zh, zs=None,
  covmodel=None, covparam=None,
  order=np.nan, options=None,
  nhmax=None, nsmax=None, dmax=None,
  general_knowledge='gaussian',
  pdfk=None,pdfh=None,pdfs=None,hk_k=None,hk_h=None,hk_s=None):
  '''
  To obtain the BME posterior PDF with specified general and specific 
  knowledge PDFs
    
  Input:
  ck    N by 3    2D array of the S/T coordinates of estimation points
  ch    N by 3    2D array of the S/T coordinates of hard data
  cs    N by 3    2D array of the S/T coordinates of soft data
  zh    N by 1    2D array to specify the observed values at ch
  zs    N by k    2D array to specify the uncertain observed values at cs 
                  with the format as follows. 
                  zs = (softpdftype, mean, variance)
                  zs = (softpdftype, nl, limi, probadens)
                  The more details can go to see the function 
                  get_standard_soft_pdf_type function in starpy.bme.pystks_variable.py
  order integer   to specify the trend forms. NaN and 0 for zero and contant     
                  or string means respectively        
  options         BME options (look into BMEprobaMoments?)



  Note: the Gaussian part should be moved back into the proper places in order
  to generalize this function         
                    
  '''

    #SI = integrate (fg_s_given_kh * fs_s) dx_s
    #NC = integrate (fg_s_given_h * fs_s) dx_s
    #pdf_k = (fg_kh * SI) / (fg_h * NC)  # eq.1
    #exp_k = ... # eq.2
    #exp_kp = ... # eq.3
    #if general_knowledge == gaussian and specific_knowledge == unknown
    #exp_k = ... # eq.4
    #var_k = ... # eq.5

  # fg is gaussian, i.e., the Matlab version case

  ck,ch,cs=_changetimeform(ck,ch,cs)
  
  nhmax,nsmax,dmax=_set_nh_ns(ck,ch,cs,nhmax,nsmax,dmax)
  if dmax.size == 3 and dmax[0][2] is np.nan:
    dmax[0][2]=_stratio(covparam)

  if options is None:
    options=BMEoptions()
  
  if general_knowledge == 'gaussian':
    
    if (covmodel is None) or (covparam is None):
      print ('covariance model and their associated parameters should be specified')

    else:
      order = get_standard_order(order)
      nk = ck.shape[0]
      x_all_split = _get_x_all_split(nk, zh, zs)
      mean_all_split = _get_mean_all_split(x_all_split, order)
      cov_all_split = _get_cov_all_split(ck, ch, cs, covmodel, covparam)
      
      def fg_kh(xk):
        xk=np.array(xk)
        nlim=xk.size
        if nlim==1:
          output=_get_multivariate_normal_pdf(
              x_all_split, mean_all_split, cov_all_split, 'kh')(
                  np.vstack((xk, _get_x(x_all_split, 'h'))).T)
        else:
          xlim=[xk.reshape((nlim,1)),\
                np.ones((nlim,1)).dot(_get_x(x_all_split,'h').T)]
          output=_get_multivariate_normal_pdf(
              x_all_split, mean_all_split, cov_all_split, 'kh')(
              np.hstack(xlim))
        return output
              
      # fg_kh = lambda xk: _get_multivariate_normal_pdf(
      #         x_all_split, mean_all_split, cov_all_split, 'kh')(
      #            np.vstack((xk, _get_x(x_all_split, 'h'))).T)
      fg_h = _get_multivariate_normal_pdf(
              x_all_split, mean_all_split, cov_all_split, 'h')(
                  _get_x(x_all_split, 'h').T)
      if zs is None:
        return lambda xk: (fg_kh(xk)/fg_h)#[0][0]
      else:
        softpdftype = get_standard_soft_pdf_type(zs[0])
        if softpdftype == 10: #specific_knowledge == 'gaussian':
          SI = lambda xk: _get_int_fg_a_given_b_fs_s(
                  [xk] + x_all_split[1:], mean_all_split,
                  cov_all_split, zs, 's_kh', 's')[0]
          NC = _get_int_fg_a_given_b_fs_s(
                  x_all_split, mean_all_split,
                  cov_all_split, zs, 's_h', 's')[0]
          return lambda xk: (fg_kh(xk) * SI(xk) / fg_h / NC)#[0][0]
        elif softpdftype == 1:
          pass # to do
        elif softpdftype == 2:
          pass # to do
  else:
    nk = ck.shape[0]
    if len(pdfk) != nk:
      print ('The number of pdfk functions is not equal'+\
            'to the number of estimation locations')
      raise
    if len(hk_k) != nk:
      print ('Then number of hk_k is not equal to the number of estimation locations')
      raise
    

    mpdf=[None]*nk
    pdf_k=[None]*nk
    pdfs_kh=[None]*nk
    pdfs_h=[None]*nk
    zhlocal=[None]*nk
    zslocal=[None]*nk
    nklocal=1
    
    
    maxpts = options[2][0]
    aEps = 0
    rEps = options[3][0]
        
    for k in range(nk):
      
      if nk>1:
        print ('BMEPDF:' + str(k+1) + '/' + str(nk))
      
      cklocal=ck[k:k+1,:]
      pdfklocal=[pdfk[k]]
      hk_k_local=[hk_k[k]]
      
      chlocal, zhlocal[k], dhlocal, sumnhlocal, idxhlocal = \
            neighbours( cklocal, ch, zh, nhmax, dmax )
      pdfhlocal=[pdfh[m] for m in idxhlocal]
      hk_h_local=[hk_h[m] for m in idxhlocal]
      
      if cs is not None:
        zsdummy=np.empty((cs.shape[0],1))
        cslocal, zslocals, dslocal, sumnslocal, idxslocal = \
              neighbours( cklocal, cs, zsdummy, nsmax, dmax )
        pdfslocal=[pdfs[m] for m in idxslocal]
        hk_s_local=[hk_s[m] for m in idxslocal]
        idxslocal=idxslocal.flat
        if len(idxslocal)>0:
          zslocal[k]=[zs[0],zs[1][idxslocal,:],zs[2][idxslocal,:],zs[3][idxslocal,:]]#[zs[1][m],zs[2][m],zs[3][m]] for m in idxslocal]#[zs[m] for m in idxslocal]#              
      else:
        cslocal=cs
        zslocal=zs
        hk_s_local=hk_s
        pdfslocal=None
      
      x_all_split = _get_x_all_split(nklocal, zhlocal[k], zslocal[k])
      mean_all_split = _get_mean_all_split(x_all_split, order)
      
      # Make the covariance function into correlation function
      
      var=np.sum([covparam[m][0] for m in range(len(covparam))]) 
      for m in range(len(covparam)):
        covparam[m][0]=covparam[m][0]/var   
      
      cov_all_split = _get_cov_all_split(cklocal, chlocal, cslocal, covmodel, covparam)  
      
      if ch is not None:
        cov_kh=_get_sigma(cov_all_split, 'kh', 'kh', inv=False)
       # cov_hh=_get_sigma(cov_all_split, 'h', 'h', inv=False)
        cov_skh = _get_sigma(cov_all_split, 'skh', 'skh', inv=False)
        cov_sh = _get_sigma(cov_all_split, 'sh', 'sh', inv=False)
        
      if not isinstance(pdfk,list):
        pdfk=[pdfk]
      if not isinstance(hk_k,list):
        hk_k=[hk_k]

      pdf_k[k],_=maxentcondpdf_gc(ppdf=pdfklocal+pdfhlocal,R=cov_kh,
                             hk=hk_k_local+hk_h_local,k_num=len(pdfklocal))  
      if zslocal[k] is not None:                       
        pdfs_kh[k],_=maxentcondpdf_gc(ppdf=pdfslocal+pdfklocal+pdfhlocal,R=cov_skh,
                             hk=hk_s_local+hk_k_local+hk_h_local,
                             k_num=len(pdfslocal))
        pdfs_h[k],_=maxentcondpdf_gc(ppdf=pdfslocal+pdfhlocal,R=cov_sh,
                             hk=hk_s_local+hk_h_local,
                             k_num=len(pdfslocal))


                            
      # write up a pyallmoments here 
      # to integrate the softdata into the equation (1) calculation 
      # in the BME_OP_chapter


      #pdfs_h[k]                       

      # mpdf_kh,_=maxentpdf_gc(ppdf=pdfklocal+pdfhlocal,R=cov_kh,
      #                       hk=hk_k_local+hk_h_local)
      # mpdf_hh,_=maxentpdf_gc(pdfhlocal,cov_hh,hk_h)

      def mpdfk(xk,k):
        xk=np.array(xk)
        xk=xk.reshape((xk.size,1))
        nlim=xk.size
        up=np.empty((nlim,1))
        
        zh_n=np.ones((nlim,1)).dot(zhlocal[k].T)
        xkzh=np.hstack([xk,zh_n])
        pdfk=pdf_k[k](xkzh)
        
        if zslocal[k] is not None:
          up,_,_=pyAllMomentsNG(zslocal[k], xkzh, pdfs_kh[k],aEps,rEps,maxpts)
          bottom,_,_=pyAllMomentsNG(zslocal[k], zhlocal[k].T, pdfs_h[k],aEps,rEps,maxpts)                
          pdfk=pdfk*up/bottom

        return pdfk

      mpdf[k] = mpdfk
    
    return mpdf

def BMEprobaGaussian(ck, ch, cs, zh, zs=None,
  covmodel=None, covparam=None, order=np.nan,
  nhmax=None, nsmax=None, dmax=None, gui_args=None):
    
  '''
  The BME function considers both general and specific knowledges are Gaussian
  This function can consider the hard-only or soft-only data cases

  zs maybe = [] (empty list for no soft data)
  'if zs is not None' should' be 'if zs'
  '''
  
  ck, ch, cs = _changetimeform(ck, ch, cs)
  if nhmax is None:
      nhmax, nsmax, dmax = _set_nh_ns(ck, ch, cs, nhmax, nsmax, dmax)
    
  if zs:
      # should add GUI from here
      order = get_standard_order(order)
      #softpdftype = get_standard_soft_pdf_type(zs[0])
      nk = ck.shape[0]
      if zh is not None:
          nh = zh.shape[0]
      else:
          nh = 0
      # ns = zs[1].shape[0]
      ns = cs.shape[0] if cs is not None else 0
      x_all_split = _get_x_all_split(nk, zh, zs)
      mean_all_split = _get_mean_all_split(x_all_split, order)
      cov_all_split = _get_cov_all_split(ck, ch, cs, covmodel, covparam)
      
      mean_k = _get_mean(mean_all_split, 'k')
      mean_hs = _get_mean(mean_all_split, 'hs')
      mean_s_given_h = _get_mean_a_given_b(
                x_all_split, mean_all_split,
                cov_all_split,sub_a='s', sub_b='h')

      NC, (sigma_t_prime, inv_sigma_s_given_h,inv_sigma_tilde_s, mean_tilde_s) =\
          _get_int_fg_a_given_b_fs_s(x_all_split, mean_all_split,
                                     cov_all_split, zs, 
                                     sub_multi = 's_h', sub_s='s')

      hat_x_s = NC * sigma_t_prime.dot(
          inv_sigma_s_given_h.dot(mean_s_given_h)
          + inv_sigma_tilde_s.dot(mean_tilde_s)
          )
      if nh>0:
        hat_x_h = _get_x(x_all_split, 'h') * NC
        hat_x_hs = np.vstack((hat_x_h, hat_x_s))
      else:
        hat_x_hs = hat_x_s

      sigma_k_hs = _get_sigma(
          cov_all_split, sub_a='k', sub_b='hs')

      inv_sigma_hs_hs = _get_sigma(
          cov_all_split, sub_a='hs', sub_b='hs', inv=True)

      cond_k_hs = sigma_k_hs.dot(inv_sigma_hs_hs)

      BME_mean_k_given_hs_a = cond_k_hs.dot(hat_x_hs)

      BME_mean_k_given_hs_b = mean_k - cond_k_hs.dot(mean_hs)

      BME_mean_k_given_hs =\
          BME_mean_k_given_hs_a / NC + BME_mean_k_given_hs_b

      sigma_k_given_hs = _get_sigma_a_given_b(
          cov_all_split, sub_a='k', sub_b='hs')

      sigma_k_given_hs_diag =\
            sigma_k_given_hs.diagonal().reshape((-1,1))

      mean_t = hat_x_hs/NC
      aa = np.zeros(inv_sigma_hs_hs.shape)
      aa[nh:nh+ns, nh:nh+ns] = sigma_t_prime*NC
      bb = (mean_t - mean_hs).dot((mean_t - mean_hs).T) * NC
      tt = cond_k_hs.dot(aa + bb).dot(cond_k_hs.T)
      tt_diag = tt.diagonal().reshape((-1,1))

      BME_var_k_given_hs = (
        sigma_k_given_hs_diag - BME_mean_k_given_hs**2 + mean_k**2
        - 2*mean_k * cond_k_hs.dot(mean_hs)
        + 2*mean_k * cond_k_hs.dot(hat_x_hs) / NC
        + tt_diag / NC
        )
      
      skewness = np.zeros(BME_mean_k_given_hs.shape)
      mvs = np.hstack(
          (BME_mean_k_given_hs, BME_var_k_given_hs, skewness)
          )
      return mvs
  else: # only hard data
    order = get_standard_order(order)
    #softpdftype = get_standard_soft_pdf_type(zs[0])
    nk = ck.shape[0]
    dm = ck[0].size
    
    if dm<3 or nk<100:
        nh = zh.shape[0]
        x_all_split = _get_x_all_split(nk, zh, zs)
        mean_all_split = _get_mean_all_split(x_all_split, order)
        cov_all_split = _get_cov_all_split(ck, ch, cs, covmodel, covparam)
          
        # mean_k=_get_mean(mean_all_split,'k')   
        mean_k_given_h = _get_mean_a_given_b(
            x_all_split, mean_all_split,
            cov_all_split,sub_a='k', sub_b='h')
        sigma_k_given_h = _get_sigma_a_given_b(
            cov_all_split, sub_a='k', sub_b='h')
        return mean_k_given_h, sigma_k_given_h
    else:
        dummy = np.random.rand(ck.shape[0],1)
        _, cMS_k, tME_k, _ = valstv2stg(ck, dummy)
        nklocal = cMS_k.shape[0]
        mean_k_given_h = np.empty((nklocal, 0))
        sigma_k_given_h = np.empty((nklocal, 0))

        # Here should add spatial split for large spatial data at a time
        # or GUI will become freezed
        for tt in range(tME_k.size):
            cklocal =\
                np.hstack([
                    np.mean(cMS_k,0), tME_k[tt]
                    ]).reshape(1, 3)
            cklocals =\
                np.hstack([
                    cMS_k, np.ones((nklocal, 1))*tME_k[tt]
                    ])
            chlocal, zhlocal, dhlocal, sumnhlocal, idxhlocal = \
                neighbours(cklocal, ch, zh, nhmax, dmax)
            cslocal = cs
            zslocal = zs

            x_all_split = _get_x_all_split(nklocal, zhlocal, zslocal)
            mean_all_split = _get_mean_all_split(x_all_split, order)
            cov_all_split = _get_cov_all_split(
                cklocals, chlocal, cslocal, covmodel, covparam)
          
            mean_k_given_h_ = _get_mean_a_given_b(
                      x_all_split, mean_all_split,
                      cov_all_split,sub_a='k', sub_b='h')
            sigma_k_given_h_ = np.diag(
                _get_sigma_a_given_b(
                    cov_all_split, sub_a='k', sub_b='h'
                    )
                ).reshape(nklocal, 1)
                      
            mean_k_given_h=np.hstack([mean_k_given_h,mean_k_given_h_])
            sigma_k_given_h=np.hstack([sigma_k_given_h,sigma_k_given_h_])
            print (str(tt+1) + '/' + str(tME_k.size))
            if gui_args:
                gui_args[0].setValue(cMS_k.shape[0]*(tt+1))
        ck2,mean_k_given_h_v=valstg2stv(mean_k_given_h, cMS_k, tME_k)
        ck2,sigma_k_given_h_v=valstg2stv(sigma_k_given_h, cMS_k, tME_k)
        
        # ck != ck2 will occur when ck is not get from grid input
        # need to be fixed ASAP.
        if not np.all(ck2==ck):
            print ('warning: ck and ck2 are not the same')
            raise ValueError('Now ck only can input with grid.')

        return mean_k_given_h_v, sigma_k_given_h_v
