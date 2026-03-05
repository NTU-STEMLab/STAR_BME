import numpy
import time
def diffarray(x,include=True):
    '''
    x: row for data and col for dimention
    include: means diff include self
    return left index, right index, delta value
           left and right index is a row of dim = 1 numpy array
    '''
    lenx=len(x)
    diff=[]

    index_head=[]
    index_tail=[]
        
    if include == True:
        for i in range(lenx):
            index_head+=[i]*(lenx-i)
            index_tail+=range(lenx)[i:]
        for i in range(lenx):  
            for j in range(i,lenx):
                #index_head.append(i)
                #index_tail.append(j)
                diff.append(x[i]-x[j])
    elif include == False:
        for i in range(lenx-1):
            index_head+=[i]*(lenx-i-1)
            index_tail+=range(lenx)[i+1:]
        for i in range(lenx): 
            for j in range(i+1,lenx):
                #index_head.append(i)
                #index_tail.append(j)
                diff.append(x[i]-x[j])
    
    index_head,index_tail,diff=map(numpy.array,(index_head,index_tail,diff))

        
    return index_head,index_tail,diff

def multiarray(x,include=True):
    '''
    like diffarray but operator is multilize
    '''
    lenx=len(x)
    diff=[]

    index_head=[]
    index_tail=[]
        
    if include == True:
        for i in range(lenx):
            index_head+=[i]*(lenx-i)
            index_tail+=range(lenx)[i:]
        for i in range(lenx):  
            for j in range(i,lenx):
                #index_head.append(i)
                #index_tail.append(j)
                diff.append(x[i]*x[j])
    elif include == False:
        for i in range(lenx-1):
            index_head+=[i]*(lenx-i-1)
            index_tail+=range(lenx)[i+1:]
        for i in range(lenx): 
            for j in range(i+1,lenx):
                #index_head.append(i)
                #index_tail.append(j)
                diff.append(x[i]*x[j])
    
    index_head,index_tail,diff=map(numpy.array,(index_head,index_tail,diff))
    return index_head,index_tail,diff

if __name__ == "__main__":
    #x=numpy.array(numpy.random.random((3000,2)))
    #x=numpy.array([[1,2],[4,3],[5,6],[9,1]])
    x=numpy.array([[1],[4],[6],[7]])
    a,b,c=diffarray(x,include=True)
    #a,b,c=multiarray(x,include=True)
    print (a)
    print (b)
    print (c)