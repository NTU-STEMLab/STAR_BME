from qgis.PyQt import QtGui, QtWidgets
import matplotlib
# matplotlib.use("Qt5Agg")  # Not needed when running inside QGIS
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg \
  import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
  import NavigationToolbar2QT as NavigationToolbar
from matplotlib import cm
class MplCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        # FigureCanvas.setSizePolicy(self,
        #                  QtWidgets.QSizePolicy.Expanding,
        #                  QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

class MplWidget(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtWidgets.QVBoxLayout()
        self.vbl.addWidget(self.canvas) 
        self.ntb = NavigationToolbar(self.canvas,self)
        self.vbl.addWidget(self.ntb)
        self.setLayout(self.vbl)
        
class MplWidgetWithoutNavTools(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtWidgets.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
