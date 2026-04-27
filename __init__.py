import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
def classFactory(iface):
  from .stbme import BMEPlugin
  BMEdebug=BMEPlugin(iface)
  iface.BMEdebug=BMEdebug
  return BMEdebug



