# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
import sys
import os
import shutil


####copy ftools####
# Set up current path, so that we know where to look for modules
# Use realpath to resolve symlinks and get absolute path
currentPath = os.path.dirname(os.path.realpath(__file__))
plugin_dir = currentPath  # Alias for clarity
sys.path.append(os.path.abspath(currentPath))

# initialize Qt resources from file resouces.py
import resources
import star_variable

if star_variable.USE_STAR_PACKAGES:
    sys.path.append(
        os.path.abspath(os.path.join(currentPath, 'star-packages'))
        )

class BMEPlugin:
  def __init__(self, iface):
    # save reference to the QGIS interface
    self.iface = iface
  def initGui(self):
    # Check and install dependencies if needed (first-time setup)
    try:
        from starbme_installer import check_dependencies_silent
        self.dependencies_ok = check_dependencies_silent()
    except Exception as e:
        print(f"[STAR_BME] Error checking dependencies: {e}")
        self.dependencies_ok = False
    
    # create action that will start plugin configuration
    # Use absolute path for icon (more robust than Qt resources)
    icon_path = os.path.join(plugin_dir, 'image', 'stemlab.png')
    if not os.path.exists(icon_path):
        # Fallback: try Qt resource path
        icon_path = ":/stemlab.png"
    self.action = QAction(
        QIcon(icon_path), "STAR-BME", self.iface.mainWindow())
    #self.action.setWhatsThis("Configuration for test plugin BMEBMEBME")
    self.action.setStatusTip(
        "Modern spatiotemporal modelling and mapping"
        )
    self.action.triggered.connect(self.run)
    # add toolbar button and menu item
    # Use the new QGIS 3 API
    self.iface.addPluginToVectorMenu("&STAR", self.action)
    self.iface.addVectorToolBarIcon(self.action)

  def unload(self):
    # remove the plugin menu item and icon
    # Use the new QGIS 3 API
    self.iface.removePluginVectorMenu("&STAR", self.action)
    self.iface.removeVectorToolBarIcon(self.action)

  def run(self):
    # Check dependencies before running
    if not getattr(self, 'dependencies_ok', False):
        try:
            from starbme_installer import ensure_dependencies
            if not ensure_dependencies(self.iface):
                # User declined or installation failed
                return
            # Dependencies installed, but need restart
            return
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            
            QMessageBox.critical(
                self.iface.mainWindow(),
                "STAR-BME: Dependency Check Failed",
                f"Could not verify dependencies: {str(e)}\n\n"
                f"Debug Info:\n"
                f"  sys.executable: {sys.executable}\n"
                f"  sys.prefix: {sys.prefix}\n\n"
                f"Please install manually in QGIS Python Console:\n"
                f"import subprocess, sys, os\n"
                f"python_exe = os.path.join(sys.prefix, 'bin', 'python3')\n"
                f"print(f'Using: {{python_exe}}')\n"
                f"subprocess.run([python_exe, '-m', 'pip', 'install', '--user', 'pandas', 'scipy', 'numpy', 'matplotlib'])"
            )
            print(f"[STAR_BME] Dependency check error:\n{error_details}")
            return
    
    #clean workspace

    if hasattr(self,"maindlg"):
        if self.maindlg.isHidden():
            self.maindlg.show()
        self.maindlg.raise_()
    else:
        #try to create temp folder
        if os.path.isdir(star_variable.WORKING_PATH):
            pass
        else:
            os.mkdir(star_variable.WORKING_PATH)
        try:
            root, dir_, file_ = next(os.walk(star_variable.WORKING_PATH))
            for d in dir_:
                shutil.rmtree(os.path.join(root, d))
            for f in file_:
                os.remove(os.path.join(root, f))
        except Exception as e:
            raise e
            QMessageBox.critical(
                None, "Clean Workspace Error",
                "Some file still in used, please close other STAR-BME first.")
            return
        # REMOVED ERROR MASKING - Let it crash with real traceback!
        # Force imports to happen NOW - will show real error if they fail
        import pandas as pd
        import scipy
        scipy_ver = scipy.__version__
        if int(scipy_ver.split('.')[1]) < 18 and\
            int(scipy_ver.split('.')[0]) < 1:
            # we need scipy 0.18 above
            msg_str = [
                "The scipy module version is low ({v}), ".format(
                    v=scipy_ver
                    ),
                "STARBME cannot be used.\n",
                "Please install scipy >= 0.18 first to use STARBME."]
            QMessageBox.critical(
                self.iface.mainWindow(), "Scipy version is not enough",
                "".join(msg_str)
                )
            return
        from gui import main
        self.maindlg =\
            main.MainWindow(self.iface, None) # for Mac "strange jump down window" problem 
            # main.MainWindow(self.iface, self.iface.mainWindow())
        self.maindlg.show()
        
    
    
