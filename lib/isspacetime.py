import numpy


def isspacetime(model):
    if '/' in model[0]:
        isST = True
        isSTsep = True
    else:
        isSTsep = False
        if 'ST' in model[0]:
            isST = True
        else:
            isST = False

    modelS = []
    modelT = []
    if isST:
        if isSTsep:
            for model_i in model:
                m_s, m_t = model_i.split('/')
                modelS.append(m_s)
                modelT.append(m_t)
        else:
            modelS = model
            modelT = model
    else:
        for model_i in model:
            m_s = model_i
            modelS.append(m_s)
            modelT.append(None)  # 0 NO_MODEL

    return isST, isSTsep, modelS, modelT


if __name__ == "__main__":
    models = numpy.array(["exponential/exponential", "gaussian/gaussian"])
    res = isspacetime(models)
    for i in res:
        print (i)

    models = numpy.array(["nugget", "exponential"])
    res = isspacetime(models)
    for i in res:
        print (i)
