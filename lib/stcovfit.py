import numpy

def fitcovariance(fit_models,lag_cov_s,lag_cov_t,
                  lag_cov_v,lag_cov_n):
    lag_cov_est = estimatecovariance(lag_cov_s,lag_cov_t,fit_models)
    ersqr = (lag_cov_v - lag_cov_est) ** 2
    wt = lag_cov_n / (lag_cov_est[0][0] ** 2 + lag_cov_est ** 2)
    wt /= wt.sum()
    objfv = wt * ersqr
    objfv = objfv[numpy.where(~numpy.isnan(objfv))].sum()
    
    return objfv

#===============================================================================
# def autofitcov(CSTguess,COVparams,Smodels,Tmodels):
#    CSTguess=CSTguess.reshape((-1,3)).tolist()
#    fittingmodels=[]
#    for cst,smodel,tmodel in zip(CSTguess,Smodels,Tmodels):
#        cst.insert(1,smodel)
#        cst.insert(3,tmodel)
#        fittingmodels.append(cst)
# 
#    fittingmodels = tuple(fittingmodels)
#    return fitcovariance(fittingmodels,COVparams)
#===============================================================================

def estimatecovariance(lag_cov_s,lag_cov_t,fit_models):
    lagS = lag_cov_s[:,0]
    lagT = lag_cov_t[0]
    lagCOV_est=numpy.zeros(lag_cov_s.shape)
    lengthS=len(lagS)
    for i in range(len(fit_models)):
        fittingfuncS = _index_to_fit_func(fit_models[i][1])
        fittingfuncSvalue = fittingfuncS(fit_models[i][2],lagS)
        fittingfuncT = _index_to_fit_func(fit_models[i][3])
        fittingfuncTvalue = fittingfuncT(fit_models[i][4],lagT)
        temp = numpy.kron(fittingfuncSvalue,fittingfuncTvalue)
        temp = temp.reshape(lengthS,-1)
        lagCOV_est+=fit_models[i][0] * temp
    return lagCOV_est
  
  
def _index_to_fit_func(index):
    dictionary={"gaussian":_Gau,
                "exponential":_Exp,
                "spherical":_Sph,
                "holecos":_HoC,
                "nugget":_Nug,
                "gau":_Gau,
                "exp":_Exp,
                "sph":_Sph,
                "hoc":_HoC,
                "nug":_Nug,}
    return dictionary[index]
  

def _Gau(bandwidth,lag):
    value = numpy.exp(-3*(lag/bandwidth)**2)
    return value

def _Exp(bandwidth,lag):
    value = numpy.exp(-3*(lag/bandwidth))
    return value

def _Sph(bandwidth,lag):
    value=lag.copy()
    boollag = lag <= bandwidth
    value[boollag] = 1.0-1.5*(lag[boollag]/bandwidth)\
                    +0.5*(lag[boollag]/bandwidth)**3;
    boollag = lag > bandwidth 
    value[boollag] = 0.0
    return value;

def _HoC(bandwidth,lag):
    value = numpy.cos(3.1415926*lag/bandwidth)
    return value

def _Nug(bandwidth,lag):
    value=lag.copy()
    boollag = lag == 0
    value[boollag] = 1.
    boollag = lag != 0
    value[boollag] = 0.
    return value;

if __name__ == "__main__":
    pass
