# -*- coding: utf-8 -*-
import numpy as np


def proba2probdens(softpdftype, nl, limi, probdens):
    '''
    proba2probdens            - Normalizes the probability density function (Jan 1, 2001)
  
    Calculates the norm (area under the curve) of a function template, and returns
    a normalized pdf. This function uses the syntax of probabilistic data (see 
    probasyntax) to define the pdf.
   
    SYNTAX :
   
    [probdens,norm]=proba2probdens(softpdftype,nl,limi,probdenstemplate);
   
    INPUT :
   
    softpdftype scalar      indicates the type of soft pdf representing the  
                            probabilitic soft data.  
                            softpdftype may take value 1, 2, 3 or 4, as follow:
                            1 for Histogram, 2 for Linear, 3 for Grid histogram, 
                            and 4 for Grid Linear.
                            In current status, only softpdftype 2 is avaiable for use 
    nl          ns by 1     2D array of the number of interval limits. nl(i) is the number  
                            of interval limits used to define the soft pdf for soft data 
                            point i. (see probasyntax for more explanations)
    limi        ns by l     2D array of interval limits, where l is equal to
                            either max(nl) or 3 depending of the softpdftype.
                            limi(i,:) are the limits of intervals for the i-th 
                            soft data. (see probasyntax for more explanations)
    probdenstemplate        ns by p matrix of non-normalized probability density values,  
                            where p is equal to either max(nl)-1 or max(nl), depending on 
                            the softpdftype. probdenstemplate(i,:) are the values of the  
                            non-normalized probability density corresponding to the intervals  
                            for the i-th soft data defined in limi(i,:). (see probasyntax for 
                            more explanations)
   
    OUTPUT :
    nl          ns by 1     2D array of the number of interval limits. nl(i) is the number  
                            of interval limits used to define the soft pdf for soft data 
                            point i. (see probasyntax for more explanations)
    limi        ns by l     2D array of interval limits, where l is equal to
                            either max(nl) or 3 depending of the softpdftype.
                            limi(i,:) are the limits of intervals for the i-th 
                            soft data. (see probasyntax for more explanations)
    probdens    ns by p     2D array of normalized probability density values,
                            each row of probadens is equal to the corresponding row
                            of probadenstemplate divided by its normalization constant
    norm        ns by 1     2D array of the normalization constants (area under the curve)
                            of each row of probadenstemplat, e.g. norm(is) is the
                            normalization constant for probdenstemplate(is,:)  
    ''' 
    softpdftype = 2 # always 2 for now
    
    if type(nl) is int: # only one soft data
      limi=limi.reshape(1,limi.size)
      probdens=probdens.reshape(1,probdens.size)
      nl=np.array(nl).reshape(1,1)
    elif limi.shape != probdens.shape:
      limi=limi.reshape((len(nl),limi.size//len(nl)))
      probdens=probdens.reshape((len(nl),limi.size//len(nl)))
      nl=nl.reshape((len(nl),1))
    norm_probdens = np.zeros(probdens.shape)  
    area=np.zeros(nl.shape)
    m=0  
    for nl_i, limi_i, probdens_i in zip( nl, limi, probdens):
        nl_i = int( nl_i[ 0 ] )
        limi_i = limi_i[ : nl_i ]
        probdens_i_original = probdens_i[:] #copy
        probdens_i = probdens_i[ :nl_i ]

        height = limi_i[ 1: ] - limi_i[ :-1 ]
        sum_up_low = probdens_i[ :-1 ] + probdens_i[ 1: ]
        area[m] = (sum_up_low * height / 2.).sum()
        norm_probdens_i = probdens_i / area[m]
        probdens_i_original[ :nl_i] = norm_probdens_i
        norm_probdens[m]=probdens_i_original#.append( probdens_i_original )
        m=m+1
    
    if len(nl)==1: 
      limi=limi.reshape(limi.size,)
      norm_probdens=norm_probdens.reshape(limi.size,)    
      
    return nl, limi, norm_probdens, area
    
if __name__ == "__main__":
  import matplotlib.pyplot as plt
  
  proba=np.array([  1.18902751e-006,   3.21525965e-017,   2.93199363e-016,
         2.12361242e-012,   1.97580507e-008,   2.52489451e-005,
         2.72805628e-003,   3.41667876e-002,   9.48013134e-002,
         1.16841170e-001,   1.08457969e-001,   8.84783314e-002,
         3.99929961e-002,   2.44856280e-003,   1.15554125e-006,
         2.34363978e-014,   2.18806404e-030,   5.78955132e-062,
         1.45778998e-123,   2.04210672e-252])
  limi=np.array([-42.9142662 , -39.65987025, -36.92398652, -34.44556903,
       -32.12435339, -29.90783854, -27.76355236, -25.6689865 ,
       -23.60705191, -21.56367491, -19.52632509, -17.48294809,
       -15.4210135 , -13.32644764, -11.18216146,  -8.96564661,
        -6.64443097,  -4.16601348,  -1.43012975,   1.8242662 ])
  softpdftype=2
  nl=np.array([limi.size]).reshape(1,1)      
        
  nl,limi2,probdens,_=proba2probdens(softpdftype,nl,limi,proba)
  print (nl)
  print (limi)
  print (probdens)
  
  plt.figure()
  plt.plot(limi2,probdens)
  plt.show()  
  
  
  