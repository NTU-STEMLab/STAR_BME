'''
Created on 2013/12/29
I want to change all variable that use in all module to here
for maintain code speed
@author: KSJ
'''
import os
import sys
import numpy
import platform
import importlib
import importlib.util
WORKING_FOLDER = r'.stbme'

PF = platform.platform()

USE_STAR_PACKAGES = False

if PF.startswith( 'Windows' ): #windows system

    #from bsddb.db import DBPermissionsError as DBPERMISSIONSERROR
    WORKING_PATH = os.path.join( os.environ['USERPROFILE'], WORKING_FOLDER )
    SYS_ENCODING = "mbcs"
    DEFAULT_ENCODING = "utf8"
    GDALWARP = 'gdalwarp'

    if PF.startswith( 'Windows-XP' ): #xp
        SHELVE_ENCODING = 'cp950'
    else: #win7, win8, win-others
        SHELVE_ENCODING = 'utf8'

    USE_STAR_PACKAGES = True
    
    os_platform = 'Windows'

elif PF.startswith( 'Darwin' ): #Mac
    SHELVE_ENCODING = 'utf8'
    WORKING_PATH = os.path.join( os.environ['HOME'], WORKING_FOLDER )
    from dbm import error as DBPERMISSIONSERROR
    SYS_ENCODING = "utf8"
    DEFAULT_ENCODING = "utf8"
    # Prefer QGIS-bundled gdalwarp; fall back to standalone GDAL framework
    _gdalwarp_candidates = [
        '/Applications/QGIS.app/Contents/MacOS/gdalwarp',
        '/Library/Frameworks/GDAL.framework/Programs/gdalwarp',
    ]
    GDALWARP = next((p for p in _gdalwarp_candidates if os.path.isfile(p)), 'gdalwarp')
    
    os_platform = 'Mac'
elif PF.startswith( 'Linux' ): #Ubuntu
    SHELVE_ENCODING = 'utf8'
    WORKING_PATH = os.path.join( os.environ['HOME'], WORKING_FOLDER )
    from dbm import error as DBPERMISSIONSERROR
    SYS_ENCODING = "utf8"
    DEFAULT_ENCODING = "utf8"
    GDALWARP = '/usr/bin/gdalwarp'

    os_platform = 'Linux'
else:
    SHELVE_ENCODING = 'utf8'
    WORKING_PATH = os.path.join( os.environ['HOME'], WORKING_FOLDER)
    from dbm import error as DBPERMISSIONSERROR
    SYS_ENCODING = "utf8"
    DEFAULT_ENCODING = "utf8"
    GDALWARP = '/Library/Frameworks/GDAL.framework/Programs/gdalwarp'
    
    os_platform = 'Mac' #unkown, use mac
    

def loadDynamicModule( name, dirs ):
    try:
        # Check if module is already loaded
        return sys.modules[ name ]
    except KeyError:
        dir_name = os.path.join( os.path.abspath( os.path.dirname( __file__ ) ),
                                 'lib',
                                 name,
                                 os_platform,
                                 *dirs )
        if not os.path.exists(dir_name):
            raise ImportError( "Sorry, We don't have %s module for %s" % ( name, 'and'.join(dirs) ) )                  
    
        # Use importlib instead of deprecated imp module
        sys.path.append(dir_name)
        try:
            # Try to find the module file
            module_file = None
            for ext in ['.so', '.pyd', '.py', '.pyc']:
                potential_file = os.path.join(dir_name, name + ext)
                if os.path.exists(potential_file):
                    module_file = potential_file
                    break
            
            if not module_file:
                raise ImportError('Can not find %s for %s' % ( name, 'and'.join(dirs) ) )
            
            # Load the module using importlib
            spec = importlib.util.spec_from_file_location(name, module_file)
            if spec is None:
                raise ImportError('Cannot create module spec for %s' % name)
            
            dynamic_lib = importlib.util.module_from_spec(spec)
            sys.modules[name] = dynamic_lib
            spec.loader.exec_module(dynamic_lib)
            return dynamic_lib
            
        except Exception as e:
            raise ImportError('Strange Error:%s' % str(e))  
        
           
py_v = str( sys.version_info[ 0 ] )+str( sys.version_info[ 1 ] )
np_v = numpy.__version__[0]+numpy.__version__[2]


def isModuleExists(module_syntax):
    """
    Check if a module can be imported.
    Returns (bool, error_message) tuple.
    """
    try:
        importlib.import_module(module_syntax)
        return True
    except ImportError as e:
        # Module genuinely doesn't exist
        return False
    except Exception as e:
        # Some other error during import - this is the real problem!
        # Re-raise it so we can see what's actually wrong
        import traceback
        error_msg = f"Error importing {module_syntax}: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Also print to console for debugging
        raise ImportError(error_msg) from e

HAS_MODULE_NLOPT = isModuleExists('nlopt')
HAS_MODULE_PANDAS = isModuleExists('pandas')