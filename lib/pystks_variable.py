import numpy


def get_standard_soft_pdf_type(pdf_type):
    if isinstance(pdf_type, str):
        if 'histogram'.startswith(pdf_type.lower()):
            return 1
        elif 'linear'.startswith(pdf_type.lower()):
            return 2
        elif 'gaussian'.startswith(pdf_type.lower()) or\
             'normal'.startswith(pdf_type.lower()):
            return 10
        else:
            raise ValueError('No supported pdftype found')
    else:
        if pdf_type in [1]:
            return 1
        elif pdf_type in [2] :
            return 2
        elif pdf_type in [10] :
            return 10


def get_standard_order(order):
    if isinstance(order, str): #base string
        if order.lower() == 'zero mean':
            return numpy.nan
        elif order.lower() == 'constant mean':
            return 0
        else:
            raise ValueError('No supported order (string) found')
    else: #int
        if numpy.isnan(order):
            return order
        elif order in  [0, 0.0]:
            return 0
        else:
            raise ValueError('No supported order (number) found')


if __name__ == "__main__":
    print (get_standard_soft_pdf_type(1))
    print (get_standard_soft_pdf_type('hist'))
    print (get_standard_soft_pdf_type('h'))
    print (get_standard_soft_pdf_type('H'))
    print (get_standard_soft_pdf_type(1))
    print (get_standard_soft_pdf_type('li'))
    print (get_standard_soft_pdf_type('l'))
    print (get_standard_soft_pdf_type('LineAr'))

    print (get_standard_order('Zero Mean'))
