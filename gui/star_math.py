import math 

def round_by_significant_feature( value, sf_n = 4 ):
	'''
	Round to significant feature.
	e.g. Round value to sf_n digit.
	e.x. value = 3.14159 sf_n = 4
	return 3.141.
	'''
	try:
		log_value = math.log10( abs( value ) ) # value = a*10**b
	except ValueError as e:
		if value == 0:
			return 0
		else:
			raise e
	b = int( math.floor( log_value ) )
	return round( value, -b + ( sf_n - 1 ) )


if __name__ == '__main__':

	print (round_by_significant_feature( 0.0 ))
	print (round_by_significant_feature( 1234567 ))
	print (round_by_significant_feature( 123.4567 ))
	print (round_by_significant_feature( -1234567 ))
	print (round_by_significant_feature( -123.4567 ))
	print (round_by_significant_feature( '5a' ))