import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
def classFactory(iface):
  # load QtBMEobj class from file QtBME.py
  from STAR_BME.stbme import BMEPlugin
  BMEdebug=BMEPlugin(iface)
  iface.BMEdebug=BMEdebug
  return BMEdebug



