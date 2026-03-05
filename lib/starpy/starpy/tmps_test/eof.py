# -*- coding: utf-8 -*-
"""
Created on Tue May 26 18:57:18 2015

@author: hdragon689
"""
import numpy as np
import scipy.sparse.linalg as ssl
import scipy.linalg
import pandas as pd  
import warnings


def _robust_svd(a, full_matrices=True):
    """SVD with automatic gesvd fallback when dgesdd fails."""
    try:
        return np.linalg.svd(a, full_matrices=full_matrices)
    except np.linalg.LinAlgError:
        warnings.warn(
            "[STARBME] np.linalg.svd (dgesdd) failed; "
            "falling back to scipy.linalg.svd (gesvd).",
            RuntimeWarning, stacklevel=2)
        return scipy.linalg.svd(
            a, full_matrices=full_matrices, lapack_driver='gesvd')


def eof(U, n='all', norm=0, *args):

  '''
  EOF - computes EOF of a matrix.
  
  Usage: [L, lambda, PC, EOFs, EC, error, norms] = EOF( M, num, norm, ... )
  
  Input: 
  M     m by n          the matrix with m obs and n items on which to perform 
                        the EOF.  
  num   scalar/string   the number of EOFs to return.  If num='all'(default), 
                        then all EOFs are returned.  
  norm  bool            normlaization flag. If it is true, then all time series 
                        are normalized by their standard deviation before EOFs 
                        are computed.  Default is false.  In this case,the 7-th 
                        output argument will be the standard deviations of each column.
  Others 
  ... are extra arguments to be given to the svds function.  These will
  be ignored in the case that all EOFs are to be returned, in which case
  the svd function is used instead. Use these with care. 
  Try scipy.sparse.linalg.svds?
  
  Output: 
  
  L       1 by k          1D array for the eigenvalues of the covariance matrix 
                          ( i.e. they are normalized by 1/(m-1), where m is the 
                          number of rows ).  
  lambdaU 1 by k          1D array for singular values 
  PC      m by k          unitary matrix having left singular vectors as columns
  EOFs    n by k          principal components. unitary matrix haveing right 
                          sigular vectors as rows
  EC      m by k          expansion coefficients
  error   1 by k          1D array of the reconstruction error (L2-norm) for 
                          each item
  norms   1 by n          1D array for standard deviation of each item or one                    
  coefficients (PCs in other terminology) and error is the reconstruction
  error (L2-norm).
  
  Remark:
  Data is not detrended before handling.  If needed, perform the detrending before 
  using this function to fix that.
  This code is modified from the Matlab code by David M. Kaplan in 2003 by 
  Hwa-Lung Yu 2015/5/31
  
  '''  

  s=U.shape
  ss=np.min(s)    
  
  # Normalized by standard deviation if desired
  
  if norm:
    norms=np.std(U,0)
  else:
    norms=np.ones((1,s[1]))
        
  U=U*np.diag(1/norms)   
    
  if (type(n)==str and n=='all') or n>=ss:
    # Use SVD in case we want all EOFs
    # Assume U is a full matrix not sparse
    C, lambdaU, EOFs=_robust_svd(U, full_matrices=True) 
  else:
    C, lambdaU, EOFs=ssl.svds(U,n)

  # Reverse the results to comply with results of the Matlab corresponding 
  #function
  lambdaU=lambdaU[::-1]
  C=C[:,::-1]
  EOFs=EOFs[::-1,:].T
  lambdaU2=np.diag(lambdaU)
  # Change the 1-D array of lambda into 2-D basis
  # lambdaU2=np.zeros([np.shape(C)[0],np.size(lambdaU)])
  # lam_n=np.size(lambdaU)
  # lambdaU2[:lam_n,:lam_n]=np.diag(lambdaU)
  
  EC = np.dot(C, lambdaU2)
  L= lambdaU**2/(s[0]-1) 
  
  # Check computation errors
  diff=U-np.dot(EC,EOFs.T)
  error=np.sqrt(sum(diff*np.conj(diff)))
  
  PC=C
  
  return L, lambdaU, PC, EOFs, EC, error, norms
    
''' varimax function'''   
def varimax_(Phi, gamma = 1, q = 20, tol = 1e-6):
  
#  from numpy import eye, asarray, dot, sum
#  from numpy.linalg import svd
  p,k = Phi.shape
  R = np.eye(k)
  d=0
  for i in range(q):
    d_old = d
    Lambda = np.dot(Phi, R)
    u,s,vh = _robust_svd(np.dot(Phi.T,np.asarray(Lambda)**3 \
          - (gamma/p) * np.dot(Lambda, np.diag(np.diag(np.dot(Lambda.T,Lambda))))))
    R = np.dot(u,vh)
    d = np.sum(s)
    if d/d_old < tol: break
  return np.dot(Phi, R),R    


def sreof(U, m='all', norm=0, *args):
  '''
  Scaled and rotaed EOF - computes scaled and rotated EOF of a matrix. 
  
  Usage: [L, lambda, PC, EOFs, EC, error, norms] = SREOF( M, num, norm, ... )
  
  Input: 
  M     m by n          the 2D array with m obs and n items on which to perform 
                        the EOF.  
  num   scalar/string   the number of EOFs to return.  If num='all'(default), 
                        then all EOFs are returned.  
  norm  bool            normlaization flag. If it is true, then all time series 
                        are normalized by their standard deviation before EOFs 
                        are computed.  Default is false.  In this case,the 7-th 
                        output argument will be the standard deviations of each column.
  Others 
  ... are extra arguments to be given to the svds function.  These will
  be ignored in the case that all EOFs are to be returned, in which case
  the svd function is used instead. Use these with care. 
  Try scipy.sparse.linalg.svds?
  
  Output: 
  
  EOF   m by num        the EOF results are listed in the columns  
  EC    n by num        the correponding EC results are listed in the columns 

  
  Remark:
  The result is re-scaled from the original EOF results by considering the 
  eigenvalues of each EOFs. The rotation is performed on the scaled EOFs.
  By doing this, the EOF rotation can have relatively low impacts from the number
  of EOFs to be rotated and therefore the results can be stabilized. The 
  rotation is based upon the 

  '''  
    
  L,lambdaU,PC,EOFs,EC,error,norms=eof(U,m,norm,*args)

  SEOF=EOFs*lambdaU # scaled EOFs by eigenvalues

  # rotate the EOFs by using varimax method  
  rotm,REOF= varimax(SEOF)
  REOF=np.dot(EOFs,rotm)

  # rotate the corresponding ECs
  NewEOFs=REOF
  NewEC=np.dot(EC,np.linalg.inv(rotm.T))

  for i in range(m):
    maxi=np.where((np.abs(NewEOFs[:,i]).max()==np.abs(NewEOFs[:,i])))
    signi=float(NewEOFs[:,i][maxi]/np.abs(NewEOFs[:,i][maxi]))
    NewEOFs[:,i]=signi*NewEOFs[:,i]
    NewEC[:,i]=signi*NewEC[:,i]
    
  return NewEOFs,NewEC  


def varimax(amat,target_basis=None):
  '''
  [ROTM,OPT_AMAT] = varimax(AMAT,TARGET_BASIS)
  
  Gives a (unnormalized) VARIMAX-optimal rotation of matrix AMAT:
  The matrix  AMAT*ROTM  is optimal according to the VARIMAX
  criterion, among all matricies of the form  AMAT*R  for  
  R  an orthogonal matrix. Also (optionally) returns the rotated AMAT matrix
  OPT_AMAT = AMAT*ROTM.
  
  Uses the standard algorithm of Kaiser(1958), Psychometrika.
  
  Inputs:
  
  AMAT          N by K     matrix of "K component loadings"
  TARGET_BASIS  N by N     (optional) an N by N matrix whose columns 
                           represent a basis toward which the rotation will 
                           be oriented; the default is the identity matrix 
                           (the natural coordinate system); this basis need 
                           not be orthonormal, but if it isn't, it should be
                           used with great care!
  Outputs: 
  
  ROTM         K by K      Optimizing rotation matrix
  OPT_AMAT     N by K      Optimally rotated matrix  (AMAT*ROTM)
  
  Modified by Trevor Park in April 2002 from an original file by J.O. Ramsay  
  Modified by H-L Yu into python code in June 2015 
  '''
  MAX_ITER=50
  EPSILON=1e-7
  
  amatd=amat.shape
  
  if np.size(amatd) != 2:
    raise RuntimeError('AMAT must be two-dimensional')
    
  n=amatd[0]
  k=amatd[1]
  rotm=np.eye(k)
  
  if k==1:
    return
    
  if target_basis==None:
    target_basis_flag=0
    target_basis=np.eye(n)    
  else:
    target_basis_flag=1
    if np.size(target_basis.shape) !=2:
      raise RuntimeError('TARGET_BASIS must be two-dimensional')
    if target_basis.shape==(n,n):
      amat=np.dot(np.linalg.inv(target_basis),amat)
    else:
      raise RuntimeError('TARGET_BASIS must be a basis for the column space')
  
  varnow=np.sum(np.var(amat**2,0))
  not_converged=1
  iterx=0
  while not_converged and iterx < MAX_ITER:
    for j in range(k-1):
      for l in range(j+1,k):
        # Calculate optimal 2-D planar rotation angle for columns j,l
        phi_max=np.angle(n*np.sum(np.vectorize(complex)(amat[:,j],amat[:,l])**4) \
                 - np.sum(np.vectorize(complex)(amat[:,j],amat[:,l])**2)**2)/4
        sub_rot = np.array([[np.cos(phi_max),-np.sin(phi_max)],\
                      [np.sin(phi_max),np.cos(phi_max)]])
        amat[:,[j,l]]=np.dot(amat[:,[j,l]],sub_rot)
        rotm[:,[j,l]]=np.dot(rotm[:,[j,l]],sub_rot)   
        
    varold = varnow
    varnow = np.sum(np.var(amat**2,0))      
  
    if varnow==0:
      return 
    
    not_converged = ((varnow-varold)/varnow > EPSILON)
    iterx= iterx +1
    
  if iterx >= MAX_ITER:
    warnings.warn('Maximum number of iterations reached in function')
  
  if target_basis_flag:  
    opt_amat=target_basis*amat
  else:
    opt_amat=np.dot(amat,rotm)

  return rotm, opt_amat  

def princomp(A):
    """ 
    coeff,score,latent=princomp(A)   
    
    This function performs principal components analysis (PCA) 
    on the n-by-p data matrix A. Rows of A correspond to observations, 
    columns to variables. 
    
    Input:
    
    A       n by p      matrix of n observations of p variables
     
    Output:  
    
    coeff   p by p      a p-by-p matrix, each column containing coefficients 
                        for one principal component.
    score   n by p      the principal component scores; that is, the 
                        representation of A in the principal component space. 
                        Rows of SCORE correspond to observations, columns to 
                        components.
    latent : 
        a vector containing the eigenvalues 
        of the covariance matrix of A.
        
     Ref: this function is downloaded from the link
     http://glowingpython.blogspot.tw/2011/07/principal-component-analysis-with-numpy.html
     """
    # computing eigenvalues and eigenvectors of covariance matrix
    M = (A-np.mean(A.T,axis=1)).T # subtract the mean (along columns)
    [latent,coeff] = np.linalg.eig(np.cov(M)) # attention:not always sorted
    score = np.dot(coeff.T,M) # projection of the data in the new space
    return coeff,score,latent

'''
#!/usr/bin/env python
# -*- coding: ascii -*-

"""Higher order singular value decomposition routines

as introduced in:
    Lieven de Lathauwer, Bart de Moor, Joos Vandewalle,
    'A multilinear singular value decomposition',
    SIAM J. Matrix Anal. Appl. 21 (4), 2000, 1253-1278

implemented by Jiahao Chen <jiahao@mit.edu>, 2010-06-11

Disclaimer: this code may or may not work.
"""

__author__ = 'Jiahao Chen <jiahao@mit.edu>'
__copyright__ = 'Copyright (c) 2010 Jiahao Chen'
__license__ = 'Public domain'

try:
    import numpy as np
except ImportError:
    print("Error: HOSVD requires numpy")
    raise ImportError



def unfold(A,n):
    """Computes the unfolded matrix representation of a tensor

    Parameters
    ----------

    A : ndarray, shape (M_1, M_2, ..., M_N)

    n : (integer) axis along which to perform unfolding,
                  starting from 1 for the first dimension

    Returns
    -------

    Au : ndarray, shape (M_n, M_(n+1)*M_(n+2)*...*M_N*M_1*M_2*...*M_(n-1))
         The unfolded tensor as a matrix

    Raises
    ------
    ValueError
        if A is not an ndarray

    LinAlgError
        if axis n is not in the range 1:N

    Notes
    -----
    As defined in Definition 1 of:

        Lieven de Lathauwer, Bart de Moor, Joos Vandewalle,
        "A multilinear singular value decomposition",
        SIAM J. Matrix Anal. Appl. 21 (4), 2000, 1253-1278
    """

    if type(A) != type(np.zeros((1))):
        print("Error: Function designed to work with numpy ndarrays")
        raise ValueError
    
    if not (1 <= n <= A.ndim):
        print("Error: axis %d not in range 1:%d" % (n, A.ndim))
        raise np.linalg.LinAlgError

    s = A.shape

    m = 1
    for i in range(len(s)):
        m *= s[i]
    m //= s[n-1]

    #The unfolded matrix has shape (s[n-1],m)
    Au = np.zeros((s[n-1],m))

    index = [0]*len(s)

    for i in range(s[n-1]):
        index[n-1] = i
        for j in range(m):
            Au[i,j] = A[tuple(index)]

            #increment (n-1)th index first
            index[n-2] += 1

            #carry over: exploit python's automatic looparound of addressing!
            for k in range(n-2,n-1-len(s),-1):
                if index[k] == s[k]:
                    index[k-1] += 1
                    index[k] = 0

    return Au



def fold(Au, n, s):
    """Reconstructs a tensor given its unfolded matrix representation

    Parameters
    ----------

    Au : ndarray, shape (M_n, M_(n+1)*M_(n+2)*...*M_N*M_1*M_2*...*M_(n-1))
         The unfolded matrix representation of a tensor

    n : (integer) axis along which to perform unfolding,
                  starting from 1 for the first dimension

    s : (tuple of integers of length N) desired shape of resulting tensor

    Returns
    -------
    A : ndarray, shape (M_1, M_2, ..., M_N)

    Raises
    ------
    ValueError
        if A is not an ndarray

    LinAlgError
        if axis n is not in the range 1:N

    Notes
    -----
    Defined as the natural inverse of the unfolding operation as defined in Definition 1 of:

        Lieven de Lathauwer, Bart de Moor, Joos Vandewalle,
        "A multilinear singular value decomposition",
        SIAM J. Matrix Anal. Appl. 21 (4), 2000, 1253-1278
    """

    m = 1
    for i in range(len(s)):
        m *= s[i]
    m //= s[n-1]

    #check for shape compatibility
    if Au.shape != (s[n-1], m):
        print("Wrong shape: need", (s[n-1], m), "but have instead", Au.shape)
        raise np.linalg.LinAlgError

    A = np.zeros(s)

    index = [0]*len(s)

    for i in range(s[n-1]):
        index[n-1] = i
        for j in range(m):
            A[tuple(index)] = Au[i,j]

            #increment (n-1)th index first
            index[n-2] += 1

            #carry over: exploit python's automatic looparound of addressing!
            for k in range(n-2,n-1-len(s),-1):
                if index[k] == s[k]:
                    index[k-1] += 1
                    index[k] = 0

    return A



def HOSVD(A):
    """Computes the higher order singular value decomposition of a tensor

    Parameters
    ----------

    A : ndarray, shape (M_1, M_2, ..., M_N)

    Returns
    -------
    U : list of N matrices, with the nth matrix having shape (M_n, M_n)
        The n-mode left singular matrices U^(n), n=1:N

    S : ndarray, shape (M_1, M_2, ..., M_N)
        The core tensor

    D : list of N lists, with the nth list having length M_n
        The n-mode singular values D^(n), n=1:N

    Raises
    ------
    ValueError
        if A is not an ndarray

    LinAlgError
        if axis n is not in the range 1:N

    Notes
    -----
    Returns the quantities in Equation 22 of:

        Lieven de Lathauwer, Bart de Moor, Joos Vandewalle,
        "A multilinear singular value decomposition",
        SIAM J. Matrix Anal. Appl. 21 (4), 2000, 1253-1278
    """

    Transforms = []
    NModeSingularValues = []

    #--- Compute the SVD of each possible unfolding
    for i in range(len(A.shape)):
        U,D,V = _robust_svd(unfold(A,i+1))
        Transforms.append(np.asmatrix(U))
        NModeSingularValues.append(D)

    #--- Compute the unfolded core tensor
    axis = 1 #An arbitrary choice, really
    Aun = unfold(A,axis)

    #--- Computes right hand side transformation matrix
    B = np.ones((1,))
    for i in range(axis-A.ndim,axis-1):
        B = np.kron(B, Transforms[i])

    #--- Compute the unfolded core tensor along the chosen axis
    Sun = Transforms[axis-1].transpose().conj() * Aun * B

    S = fold(Sun, axis, A.shape)

    return Transforms, S, NModeSingularValues


if __name__ == '__main__':
    print()
    print("Higher order singular value decomposition routines")
    print()
    print("as introduced in:")
    print("    Lieven de Lathauwer, Bart de Moor, Joos Vandewalle,")
    print("    'A multilinear singular value decomposition',")
    print("    SIAM J. Matrix Anal. Appl. 21 (4), 2000, 1253-1278")

    print()
    print("Here are some worked examples from the paper.")

    print()
    print()
    print("Example 1 from the paper (p. 1256)")

    A = np.zeros((3,2,3))

    A[0,0,0]=A[0,0,1]=A[1,0,0]=1
    A[1,0,1]=-1
    A[1,0,2]=A[2,0,0]=A[2,0,2]=A[0,1,0]=A[0,1,1]=A[1,1,0]=2
    A[1,1,1]=-2
    A[1,1,2]=A[2,1,0]=A[2,1,2]=4
    #other elements implied zero

    #test: compute unfold(A,1)
    print()
    print("The input tensor is:")
    print(A)
    print()
    print("Its unfolding along the first axis is:")
    print(unfold(A,1))

    """
    print()
    print()
    print("Example 2 from the paper (p. 1257)""

    A = np.zeros((2,2,2))
    A[0,0,0] = A[1,1,0] = A[0,0,1] = 1
    #other elements implied zero
    """

    """
    print()
    print()
    print("Example 3 from the paper (p. 1257)""

    A = np.zeros((2,2,2))
    A[1,0,0] = A[0,1,0] = A[0,0,1] = 1
    #other elements implied zero
    """
    print()
    print()
    print("Example 4 from the paper (pp. 1264-5)")
    A = np.zeros((3,3,3))

    A[:,0,:] = np.asmatrix([[0.9073, 0.8924, 2.1488],
    [0.7158, -0.4898, 0.3054],
    [-0.3698, 2.4288, 2.3753]]).transpose()

    A[:,1,:] = np.asmatrix([[1.7842, 1.7753, 4.2495],
    [1.6970, -1.5077, 0.3207],
    [0.0151, 4.0337, 4.7146]]).transpose()

    A[:,2,:] = np.asmatrix([[2.1236, -0.6631, 1.8260],
    [-0.0740, 1.9103, 2.1335],
    [1.4429, -1.7495,-0.2716]]).transpose()

    print("The input tensor has matrix unfolding along axis 1:")
    print(unfold(A,1))
    print()

    U, S, D = HOSVD(A)

    print("The left n-mode singular matrices are:")
    print(U[0])
    print()
    print(U[1])
    print()
    print(U[2])
    print()

    print("The core tensor has matrix unfolding along axis 1:")
    print(unfold(S, 1))
    print()

    print("The n-mode singular values are:")
    print(D[0])
    print(D[1])
    print(D[2])
'''


  
if __name__ == "__main__":
  
  import eof 
  
  datapath='/Users/hdragon689/MyMacDoc/MyDoc/Research/CurrentWork/'+\
      'Groundwater_Chu/Groundwater_EOF'  
  data=datapath+'/GeoData.xls'    
  
  datadf=pd.ExcelFile(data).parse('Sheet1',header=None)
  datadf.insert(loc=0,column='Time',value=pd.to_datetime(datadf[2]*100+datadf[3],format='%Y%m'))

  # performs valstv2stg
  dtable=pd.pivot_table(datadf, values=datadf.columns[5], index=[0, 1], columns=['Time'])
  # cMS
  cMS=zip(*np.array(dtable.index))
  cMS=np.array([np.asarray(cMS[0]),np.asarray(cMS[1])])
  cMS=cMS.T
  
  #tME
  tME=np.array(dtable.columns,dtype='datetime64[M]')
  
  # Z
  Z=dtable.values
  
  # Simple linear reression for missing data restore
  # Coefficients are b0=-26.3724653739771 b1=0.968464993459824
  b=np.empty((0,0))
  b=np.append(b,-26.3724653739771)
  b=np.append(b,0.968464993459824)
  Z[18,0]=b[0]+b[1]*Z[23,0]
  
  Zmean=np.mean(Z,1)
  Zmean=np.reshape(Zmean,(Zmean.size,1)) # Convert 1-D array to 2-D array
  
  Xst=(Z-Zmean).T
  
  m=25
  
  L,lambdaU,PC,EOFs,EC,error,norms=eof.EOF(Xst,m)
  
  SEOF=EOFs*lambdaU # scaled EOFs by eigenvalues

  # rotate the EOFs by using varimax method  
  rotm,REOF= eof.varimaxTP(SEOF)
  REOF=np.dot(EOFs,rotm)
  
  # rotate the corresponding ECs
  NewEOFs=REOF
  NewEC=np.dot(EC,np.linalg.inv(rotm.T))
  
  col=[]
  col2=[]
  for i in range(1,m+1):
    col.append('EOF%d' % i)
    col2.append('EC%d' % i)
    
  EOFdf=pd.DataFrame(NewEOFs,index=dtable.index,columns=col)
  ECdf=pd.DataFrame(NewEC,index=tME,columns=col2)
  
  # EOF plots  
  
#  import matplotlib
#  matplotlib.style.use('ggplot')  
  import matplotlib.pyplot as plt
  from scipy.interpolate import griddata  
  import matplotlib.dates as dates
  
  maxx=cMS[:,0].max()
  maxy=cMS[:,1].max()
  minx=cMS[:,0].min()
  miny=cMS[:,1].min()
  xx=np.linspace(minx,maxx,100)
  yy=np.linspace(miny,maxy,100)
#  xi, yi = np.mgrid[minx:maxx:40j, miny:maxy:40j]
  xi, yi=np.meshgrid(xx,yy) 
  
  for i in range(5):          
    zi_b=griddata(cMS,-EOFdf[col[i]].values,(xi,yi),method='nearest')
    zi=griddata(cMS,-EOFdf[col[i]].values,(xi,yi),method='linear')
    
    zi[np.isnan(zi)]=zi_b[np.isnan(zi)] # fill nans in zi  
    
    plt.figure()
    plt.pcolormesh(xi,yi,zi,cmap='hot')
    plt.title(col[i])
    plt.axis([minx, maxx, miny, maxy])
    plt.colorbar()
    plt.show()
    plt.savefig('./Figs/%s.png' % col[i], format='png', dpi=300)    
    
    # EC plot
    ax = plt.figure().add_subplot(111)
    ax.plot(tME,ECdf[col2[i]])
  #  xlocator=dates.YearLocator(1,month=7)
    xlocator=dates.MonthLocator([1,7],interval=1)
    ax.xaxis.set_major_locator(xlocator)
  #  ax.xaxis.set_minor_locator(x2locator)
    ax.xaxis.set_major_formatter(dates.DateFormatter('%b\n%Y')) 
  #  ax.xaxis.set_minor_formatter(dates.DateFormatter('%b\n%Y'))
    # Format can refer to http://linux.die.net/man/3/strftime 
    plt.show()
    plt.savefig('./Figs/%s.png' % col2[i], format='png', dpi=300)  
    plt.close('all')
  
  

