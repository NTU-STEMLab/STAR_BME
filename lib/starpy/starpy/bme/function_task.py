# -*- coding: utf-8 -*-
import subprocess
import pickle
import os


def _function_decorator(func):
    args, kwargs = pickle.loads(eval(input()))
    res = func(*args, **kwargs)
    print(repr(pickle.dumps(res)))

def start_function(popen, args = (), kwargs = {}):
    #repack args,kwargs
    wrapped_args = repr(pickle.dumps((args, kwargs))) + os.linesep
    popen.stdin.write(wrapped_args)

def get_result(popen):
    res = popen.communicate()
    if res[1]: #has error
        err_msg = os.linesep.join([os.linesep+'PID: {pid}','Error Detail:','{msg}']).format(pid=popen.pid, msg = res[1])
        raise Exception(err_msg)
    else: #no error
        return pickle.loads(eval(res[0]))

def create_func_task(module_name, func_name, sys_path_append = ()):
    def get_self_module_name():
        return os.path.splitext(os.path.split(__file__)[1])[0]

    def get_pkg_mdle_syntax():
        abs__file__ = os.path.abspath(__file__)
        c_dir, c_file = os.path.split(abs__file__)
        if "__init__.py" not in list(os.walk(c_dir))[0][2]:
            return os.path.splitext(c_file)[0] #only mdle name
        else:          
            GET_ROOT = False
            pkg_mdle_list = [os.path.splitext(c_file)[0]] #mdle name
            while not GET_ROOT:
                c_dir, c_dir2 = os.path.split(c_dir)
                pkg_mdle_list.insert(0, c_dir2)
                if "__init__.py" in list(os.walk(c_dir))[2]:
                    continue
                else:
                    c_dir, c_dir2 = os.path.split(c_dir)
                    pkg_mdle_list.insert(0, c_dir2)
                    return ".".join(pkg_mdle_list)


    #make no flash window
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    #make process
    python_script = \
'''import sys
sys.path += {other_sys_path}
from {this_module_name} import _function_decorator
from {module_name} import {func_name}
_function_decorator({func_name})
'''.format(other_sys_path = str(sys_path_append),
           this_module_name = get_pkg_mdle_syntax(),
           module_name = module_name,
           func_name = func_name)

    command_seq = ['python', '-W', 'ignore', '-c', python_script]
    proc = subprocess.Popen(command_seq,
                            stdin = subprocess.PIPE,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE, 
                            startupinfo = startupinfo,
                            universal_newlines = True)
    return proc

if __name__ == "__main__":
    import numpy
    p_list = []
    for i in range(2):
        p_list.append(create_func_task('starpy.general.coord2dist','coord2dist'))
        
    for idx,i in enumerate(p_list):
        start_function(i,(numpy.array([[1,2],[3,4],[5,6]]),
                          numpy.array([[7,12],[33,24],[45,76]])))

    r_list = []
    for i in p_list:
        r_list.append( get_result(i) )

    print (r_list)
