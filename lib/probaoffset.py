import numpy


def probaoffset( softpdftype, nl ,limi, offset ):
	ns = nl.shape[0]
	if len(offset) == 1:
		offset = offset * numpy.ones((ns,1))

	if softpdftype in [1, 2]:
		return limi - offset
	elif softpdftype in [3, 4]:
		limi[:,[0,2]] -= offset 
		return limi