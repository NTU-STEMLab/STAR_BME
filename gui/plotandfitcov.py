#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
import os, sys
import numpy
from mpl_toolkits.mplot3d import axes3d

from lib import pybme
from .ui.ui_PlotAndFitCovDlg import Ui_PlotAndFitCovDlg

from . import star_math
currentPath = os.path.dirname(__file__)
sys.path.append(os.path.abspath(currentPath))
from STAR_BME import star_variable 

class PlotAndFitCovDlg(QDialog,Ui_PlotAndFitCovDlg):
    def __init__(self,iface = None, MainDlg = None):
        def tryToLoadLastSetting():
            if self.bme.covariance.models:
                #set param
                cov = self.bme.covariance #rename
                self.ui.lineEdit_sl.setText(str(cov.spatial_lags[0][-1]))
                self.ui.lineEdit_sn.setText(str(len(cov.spatial_lags[0])))
                self.ui.lineEdit_sr.setText(str(cov.spatial_tolerant_ranges[0][0]))
                self.ui.lineEdit_tl.setText(str(cov.temporal_lags[0][-1]))
                self.ui.lineEdit_tn.setText(str(len(cov.temporal_lags[0])))
                self.ui.lineEdit_tr.setText(str(cov.temporal_tolerant_ranges[0][0]))
                #set model
                self.ui.comboBox_nestnumber.setCurrentIndex(len(cov.models)-1)
                for index,covmodel in enumerate(cov.models):
                    index = index+1
                    c,ks,s,kt,t = covmodel
                    eval('self.ui.lineEdit_c'+str(index)).setText(str(c))
                    idx_s = eval('self.ui.comboBox_s'+str(index)).findText(ks.capitalize())
                    eval('self.ui.comboBox_s'+str(index)).setCurrentIndex(idx_s)
                    eval('self.ui.lineEdit_s'+str(index)).setText(str(s))
                    idx_t = eval('self.ui.comboBox_t'+str(index)).findText(kt.capitalize())
                    eval('self.ui.comboBox_t'+str(index)).setCurrentIndex(idx_t)
                    eval('self.ui.lineEdit_t'+str(index)).setText(str(t))
            else: #set default
                h = self.bme.hard_data
                s = self.bme.soft_data

                h_d = h.hasData()
                s_d = s.hasData()

                if h_d and s_d:
                    xmin = min( h.time_x_min, s.time_x_min )
                    xmax = max( h.time_x_max, s.time_x_max )
                    ymin = min( h.time_y_min, s.time_y_min )
                    ymax = max( h.time_y_max, s.time_y_max )
                    tmin = min( h.station_t_min, s.station_t_min )
                    tmax = max( h.station_t_max, s.station_t_max )
                elif h_d:
                    xmin = h.time_x_min 
                    xmax = h.time_x_max
                    ymin = h.time_y_min
                    ymax = h.time_y_max
                    tmin = h.station_t_min
                    tmax = h.station_t_max
                elif s_d:
                    xmin = s.time_x_min 
                    xmax = s.time_x_max
                    ymin = s.time_y_min
                    ymax = s.time_y_max
                    tmin = s.station_t_min
                    tmax = s.station_t_max

                
                s_n = 8
                s_l = ( ( xmax - xmin ) **2 + ( ymax - ymin ) ** 2 ) ** (1./2) * 2 / 3.
                s_l = star_math.round_by_significant_feature( s_l )
                s_r = s_l / (s_n - 1)
                s_r = star_math.round_by_significant_feature( s_r )

                t_n = 8
                t_l = ( tmax - tmin ) * 2 / 3.
                t_l = star_math.round_by_significant_feature( t_l )
                t_r = t_l / (t_n - 1)
                t_r = star_math.round_by_significant_feature( t_r )
                

                self.ui.lineEdit_sl.setText( str( s_l ) )
                self.ui.lineEdit_sn.setText( str( s_n ) )
                self.ui.lineEdit_sr.setText( str( s_r ) )
                self.ui.lineEdit_tl.setText( str( t_l ) )
                self.ui.lineEdit_tn.setText( str( t_n ) )
                self.ui.lineEdit_tr.setText( str( t_r ) )
        
        def changeFormForSpatialOnly():
            if self.MainDlg.isSpatialOnly():
                self.ui.lineEdit_tl.setText('0')
                self.ui.lineEdit_tn.setText('1')
                self.ui.lineEdit_tr.setText('0.1')
                #self.ui.temporalcalcovwgt.setDisabled(True)
                self.ui.temporalcalcovwgt.hide()
                
                for i in ['1','2','3']:
                    eval('self.ui.lineEdit_t'+i).setText('74208') #not used number for spatial only case
                    eval('self.ui.temporalfitcovwgt_'+i).hide()

                self.ui.label_1.setText('C1*K(S1)')
                self.ui.label_2.setText('+C2*K(S2)')
                self.ui.label_3.setText('+C3*K(S3)')
                self.ui.tabWidget.removeTab(1) #remove 3d
                
        super(PlotAndFitCovDlg,self).__init__(MainDlg)
        self.iface=iface
        self.MainDlg=MainDlg
        
        self.ui = Ui_PlotAndFitCovDlg()
        self.ui.setupUi(self) 
    
        #make Covariance obj
        self.cov = pybme.Covariance()
        #rename
        self.bme = MainDlg.bmeobj
        
        self.pso_dlg = SelectParamByPsoDlg(self)
        self.bobyqa_dlg = SelectParamByBobyqaDlg(self)
        
        
        self.ui.pushButton_ok.clicked.connect( self.ok)
        self.ui.pushButton_cancel.clicked.connect( self.reject )

        self.ui.pushButton_plot.clicked.connect( self.plot )
        self.ui.pushButton_fit.clicked.connect( self.fit )
        self.ui.comboBox_nestnumber.currentIndexChanged[int].connect( self.changeNestModelGui )
        self.ui.pushButton_show.clicked.connect( self.showSelectParamDlg )

        #prepare instant time fit
        for i in ['c','s','t']:
            for j in ['1','2','3']:
                le = getattr( self.ui, 'lineEdit_{i}{j}'.format( i = i, j = j) )
                le.editingFinished.connect( self.instantFit )
                le.textEdited.connect( self.setTextEdited )
        
        self.has_nan_included = False
        self.text_edit = False
        #try to load last setting
        tryToLoadLastSetting()
        changeFormForSpatialOnly()

    def plot(self):
        self.qpgd = QProgressDialog(self)
        self.qpgd.setWindowModality(Qt.WindowModal)
      
        self.cov.setProgressDialog(self.qpgd, QApplication.processEvents)
        self.cov.setProgressAutoClose(False)
        self.cov.progress_dialog.show()

        result = self.checkPlotParameters()
        if result is False:
            return
        else:
            sl, sn, sr, tl, tn, tr = result
        #set parameters
        self.bme.setProgressDialog(self.qpgd)
        result_z = self.bme.getDetrendData() #get z_grid
        if result_z is False:
            return
        result_tr = self.bme.getCovarianceData() #get tr_grid
        if result_tr is False:
            return
        result_re = result_z[2] - result_tr[2] #get residual
        self.cov.setData((result_z[0],result_z[1],result_re))
        self.cov.setSpatialLags( numpy.linspace(0, sl, sn) )
        self.cov.setSpatialTolerantRanges( numpy.array([sr] * sn) )
        self.cov.setTemporalLags( numpy.linspace(0, tl, tn) )
        self.cov.setTemporalTolerantRanges( numpy.array([tr] * tn) )

        try:
            result = self.cov.calculate() # lagSS,lagTT,lagCOVv,lagCOVn
        except MemoryError as e:
            self.cov.setProgressAutoClose(True)
            self.cov.progress_dialog.close()
            QMessageBox.critical(
                self, 'MemoryError',
                'Data is Too Big, Maybe Add Some RAM or Reduce your Data Set.')
            return
        except ValueError as e:
            self.cov.setProgressAutoClose(True)
            self.cov.progress_dialog.close()
            QMessageBox.critical(
                self, 'ValueError',
                'Array is Too Big, Maybe Add Some RAM'\
                ' or Reduce your Data Set or Change Parameters.')
            return

        if result is False:
            return
        
        #test one point as certain axis
        # lagCOVn = result[3]
        # numpy 1.5.1 don't have count_nonzero
        # if numpy.count_nonzero(lagCOVn[:,0]) == 1 or\
        #    numpy.count_nonzero(lagCOVn[0]) == 1:
        # alternative resolution:
        if self.MainDlg.isSpatialOnly():
            self.plotCov2d(result)
        else:
            self.plotCov2d(result)
            self.plotCov3d(result)
        
        self.cov.setProgressAutoClose(True)
        self.cov.progress_dialog.close()
        self.ui.pushButton_fit.setDisabled(False)
        self.ui.pushButton_show.setDisabled(False)
        self.ui.checkBox_autofit.setDisabled(False)
        
    def fit(self):
        models = self.getCovModels() #get models
        if models is False:
            return
        else:
            self.cov.setModels(models)
        objv = self.cov.fit() #objective function value
        #get plot data
        result = self.cov.calculateFit()
        
        if self.MainDlg.isSpatialOnly():
            self.plotCovFit2d(result)
        else:
            self.plotCovFit2d(result)
            self.plotCovFit3d(result)
        #get AIC
        AIC_n = result[0].size
        mdl_n = self.ui.comboBox_nestnumber.currentIndex() + 1
        AIC = 2* mdl_n + AIC_n * numpy.log(objv/AIC_n)
        
        # QMessageBox.information(self,"Fitting","The Objective Function Value is\n"+str(objv)+
        #                   "\n(The smaller is better)")
        QMessageBox.information(self,"Fitting","The AIC Value is\n"+str(AIC))
        self.ui.pushButton_ok.setDisabled(False)
        
    def hasTextEdit( self ):
        return self.text_edit

    def instantFit( self ):
        if self.ui.checkBox_autofit.isChecked():
            if self.hasTextEdit():
                #disable all plot signal
                for i in ['c','s','t']:
                    for j in ['1','2','3']:
                        le = getattr( self.ui, 'lineEdit_{i}{j}'.format( i = i, j = j) )
                        le.editingFinished.disconnect( self.instantFit )
                
                self.fit()

                self.setTextEdited( False )
                #connect back
                for i in ['c','s','t']:
                    for j in ['1','2','3']:
                        le = getattr( self.ui, 'lineEdit_{i}{j}'.format( i = i, j = j) )
                        le.editingFinished.connect( self.instantFit )

    def ok(self):
        if self.cov.models == []:
             QMessageBox.critical(None,"Error","Covariance Model not yet be determined\n")
             return False
        self.bme.covariance = self.cov
        
        QMessageBox.information(None,"Done","Covariance Model is Created!\n")
        self.MainDlg.dirty = True
        
        #whether to show estimate dialog
        if self.bme.estimated_data.hasData():
            self.MainDlg.stage = 30
            self.MainDlg.buttonsUpdate()
        
        self.accept()
        
    def getCovModels(self):
        nestnumber = self.ui.comboBox_nestnumber.currentIndex() + 1 
        cov_models = []

        #set fit_models
        for i in range(1,nestnumber+1):
            try:
                c = float(eval("self.ui.lineEdit_c"+str(i)+".text()"))
            except ValueError:
                QMessageBox.critical(None,"Value Error","C Must be float")
                return False
            sf = str(eval("self.ui.comboBox_s"+str(i)+".currentText()")).lower()
            try:
                sb = float(eval("self.ui.lineEdit_s"+str(i)+".text()"))
            except ValueError:
                QMessageBox.critical(None,"Value Error","S Must be float")
                return False
            tf = str(eval("self.ui.comboBox_t"+str(i)+".currentText()")).lower()
            try:
                tb = float(eval("self.ui.lineEdit_t"+str(i)+".text()"))
            except ValueError:
                QMessageBox.critical(None,"Value Error","T Must be float")
                return False
            cov_models.append([c,sf,sb,tf,tb])
        return cov_models
      
    def changeNestModelGui(self, index):
        if index == 0:
            self.ui.label_2.setDisabled(True)
            self.ui.label_3.setDisabled(True)
            self.ui.widget_4.setDisabled(True)
            self.ui.widget_5.setDisabled(True)
        elif index == 1:
            self.ui.label_2.setDisabled(False)
            self.ui.label_3.setDisabled(True)
            self.ui.widget_4.setDisabled(False)
            self.ui.widget_5.setDisabled(True)
        elif index == 2:
            self.ui.label_2.setDisabled(False)
            self.ui.label_3.setDisabled(False)
            self.ui.widget_4.setDisabled(False)
            self.ui.widget_5.setDisabled(False)
            
        self.pso_dlg._setUiByNestNumber(index + 1)
        self.bobyqa_dlg._setUiByNestNumber(index + 1)
        return
    
    def plotCov2d(self, result):
        cov_s, cov_t, cov_v, cov_n = result
        
        #detect numpy.nan
        if numpy.isnan(cov_v).any(): #has nan
            self.has_nan_included = True
            cov_v_s = cov_v[:,0][~numpy.isnan(cov_v[:,0])]
            cov_s_s = cov_s[:,0][~numpy.isnan(cov_v[:,0])]
            cov_v_t = cov_v[0][~numpy.isnan(cov_v[0])]
            cov_t_t = cov_t[0][~numpy.isnan(cov_v[0])]
        else:
            self.has_nan_included = False
            cov_v_s = cov_v[:,0]
            cov_s_s = cov_s[:,0]
            cov_v_t = cov_v[0]
            cov_t_t = cov_t[0]
        
        self.ui.mplWidget_2d.canvas.fig.clear()
        
        if self.MainDlg.isSpatialOnly():          
            self.ui.mplWidget_2d.canvas.ax = \
                self.ui.mplWidget_2d.canvas.fig.add_subplot(111)
        else:
            self.ui.mplWidget_2d.canvas.ax = \
                self.ui.mplWidget_2d.canvas.fig.add_subplot(211)
        self.ui.mplWidget_2d.canvas.ax.plot(cov_s_s, cov_v_s,"ro")
        self.ui.mplWidget_2d.canvas.ax.set_xlabel('Spatial Lag')
        self.ui.mplWidget_2d.canvas.ax.set_ylabel('Covariance')
        self.ui.mplWidget_2d.canvas.ax.grid(True)
        ymin1, ymax1 = self.ui.mplWidget_2d.canvas.ax.axis()[2:4]
        ymin = ymin1
        ymax = ymax1
        
        if not self.MainDlg.isSpatialOnly():   
            self.ui.mplWidget_2d.canvas.ax2 = \
                self.ui.mplWidget_2d.canvas.fig.add_subplot(212)
            self.ui.mplWidget_2d.canvas.ax2.plot(cov_t_t, cov_v_t,"bo")
            self.ui.mplWidget_2d.canvas.ax2.set_xlabel('Temporal Lag')
            self.ui.mplWidget_2d.canvas.ax2.set_ylabel('Covariance')
            self.ui.mplWidget_2d.canvas.ax2.grid(True)
            ymin2, ymax2 = self.ui.mplWidget_2d.canvas.ax2.axis()[2:4]
            ymin = sorted([ymin1,ymin2])[0]
            ymax = sorted([ymax1,ymax2])[-1]
            self.ui.mplWidget_2d.canvas.ax2.axis(ymin =ymin , ymax = ymax)
            
        self.ui.mplWidget_2d.canvas.fig.subplots_adjust(hspace=0.40)
        self.ui.mplWidget_2d.canvas.ax.axis(ymin =ymin , ymax = ymax)
        
        
        self.ui.mplWidget_2d.canvas.draw()
    
    def plotCov3d(self, result):
        def delNanRC(ary,r_idx,c_idx):
            ary = numpy.delete(ary,r_idx,0)
            ary = numpy.delete(ary,c_idx,1)
            return ary 
        cov_s, cov_t, cov_v, cov_n = result
        if self.has_nan_included:
            s_idx_nan = numpy.where(numpy.isnan(cov_v[:,0]))[0]
            t_idx_nan = numpy.where(numpy.isnan(cov_v[0]))[0]
            cov_s = delNanRC(cov_s,s_idx_nan,t_idx_nan)
            cov_t = delNanRC(cov_t,s_idx_nan,t_idx_nan)
            cov_v = delNanRC(cov_v,s_idx_nan,t_idx_nan)
            
        self.ui.mplWidget_3d.canvas.fig.clear()
        self.ui.mplWidget_3d.canvas.ax =\
            self.ui.mplWidget_3d.canvas.fig.add_subplot(111, projection='3d')
        self.ui.mplWidget_3d.canvas.ax.plot_wireframe(cov_s, cov_t, cov_v)
        self.ui.mplWidget_3d.canvas.ax.set_xlabel('Spatial Lag')
        self.ui.mplWidget_3d.canvas.ax.set_ylabel('Temporal Lag')
        self.ui.mplWidget_3d.canvas.ax.set_zlabel('Covariance')
        self.ui.mplWidget_3d.canvas.draw()
        
    def plotCovFit2d(self, result):
        cov_s, cov_t, cov_v, cov_n = self.cov.stvn
        plotlagSS, plotlagTT, plotlagCOV = result
        if len(self.ui.mplWidget_2d.canvas.ax.lines) == 2:
            self.ui.mplWidget_2d.canvas.ax.lines[-1].remove()
            for txt in self.ui.mplWidget_2d.canvas.ax.texts[:]:
                txt.remove()
            
        #self.ui.mplWidget_2d.canvas.ax.plot(cov_s[0:,], cov_v[:,0],"ro")

        #detect numpy.nan
        if numpy.isnan(cov_v).any(): #has nan
            self.has_nan_included = True
            cov_v_s = cov_v[:,0][~numpy.isnan(cov_v[:,0])]
            cov_s_s = cov_s[:,0][~numpy.isnan(cov_v[:,0])]
            cov_n_s = cov_n[:,0][~numpy.isnan(cov_v[:,0])]
            cov_v_t = cov_v[0][~numpy.isnan(cov_v[0])]
            cov_t_t = cov_t[0][~numpy.isnan(cov_v[0])]
            cov_n_t = cov_n[0][~numpy.isnan(cov_v[0])]
        else:
            self.has_nan_included = False
            cov_v_s = cov_v[:,0]
            cov_s_s = cov_s[:,0]
            cov_n_s = cov_n[:,0]
            cov_v_t = cov_v[0]
            cov_t_t = cov_t[0]
            cov_n_t = cov_n[0]
        for i,j,k in zip( cov_s_s, cov_v_s, cov_n_s ):
            self.ui.mplWidget_2d.canvas.ax.text(i,j,str(int(k)))
            
            
            
        self.ui.mplWidget_2d.canvas.ax.plot(plotlagSS[:,0],plotlagCOV[:,0],"r-")

        # self.ui.mplWidget_2d.canvas.ax.set_xlabel('Spatial Lag')
        # self.ui.mplWidget_2d.canvas.ax.set_ylabel('Covariance')
        # self.ui.mplWidget_2d.canvas.ax.grid(True)   
 
        if not self.MainDlg.isSpatialOnly():
            if len(self.ui.mplWidget_2d.canvas.ax2.lines) == 2:
                self.ui.mplWidget_2d.canvas.ax2.lines[-1].remove()
                for txt in self.ui.mplWidget_2d.canvas.ax2.texts[:]:
                    txt.remove()
        

            #self.ui.mplWidget_2d.canvas.ax2.plot(cov_t[0], cov_v[0],"bo")
            for i,j,k in zip(cov_t_t, cov_v_t, cov_n_t ):
                self.ui.mplWidget_2d.canvas.ax2.text(i,j,str(int(k)))
            self.ui.mplWidget_2d.canvas.ax2.plot(plotlagTT[0],plotlagCOV[0],"b-")
    
        self.ui.mplWidget_2d.canvas.draw()
            # self.ui.mplWidget_2d.canvas.ax.set_xlabel('Temporal Lag')
            # self.ui.mplWidget_2d.canvas.ax.set_ylabel('Covariance')
            # self.ui.mplWidget_2d.canvas.ax.grid(True)
        
    def plotCovFit3d(self, result):
        plotlagSS, plotlagTT, plotlagCOV = result
        
        self.plotCov3d(self.cov.stvn)
        self.ui.mplWidget_3d.canvas.ax.plot_wireframe(
            plotlagSS, plotlagTT, plotlagCOV, color = (1,0,0,1)) #red line
        
        self.ui.mplWidget_3d.canvas.draw()
        # self.ui.mplWidget_3d.canvas.ax.set_xlabel('Spatial Lag')
        # self.ui.mplWidget_3d.canvas.ax.set_ylabel('Temporal Lag')
        # self.ui.mplWidget_3d.canvas.ax.set_zlabel('Covariance')
            
    def checkPlotParameters(self):
        try:
            sl = float(float(self.ui.lineEdit_sl.text()))
        except ValueError:
            QMessageBox.critical(None,"Value Error","Spatial Lag Limits Should be a Number.")
            return False
        try:
            sn = int(float(self.ui.lineEdit_sn.text()))
        except ValueError:
            QMessageBox.critical(None,"Value Error","Number of Spatial Lag Should be an Integer.")
            return False
        try:
            sr = float(self.ui.lineEdit_sr.text())
        except ValueError:
            QMessageBox.critical(None,"Value Error","Spatial Lag Tolerant Range Should be a Number.")
            return False
        try:
            tl = float(self.ui.lineEdit_tl.text())
        except ValueError:
            QMessageBox.critical(None,"Value Error","Temporal Lag Limits Should be a Number.")
            return False
        try:
            tn = int(float(self.ui.lineEdit_tn.text()))
        except ValueError:
            QMessageBox.critical(None,"Value Error","Number of Spatial Lag Should be an Integer.")
            return False
        try:
            tr = float(self.ui.lineEdit_tr.text())
        except ValueError:
            QMessageBox.critical(None,"Value Error","Temporal Lag Tolerant Range Should be a Number.")
            return False
        
        return sl, sn, sr, tl, tn, tr
    
    def setTextEdited( self, bool_ = True ):
        if self.ui.checkBox_autofit.isChecked():
            self.text_edit = bool_

    def showSelectParamDlg(self):
        method_name = self.ui.comboBox_method.currentText()
        if method_name == "BOBYQA":
            if not star_variable.isModuleExists('nlopt'):
                msg_str = [
                    "Cannot import module 'nlopt', ",
                    "BOBQYA method cannot be used.\n",
                    "Please install nlopt first if you want to use BOBYQA."]
                QMessageBox.warning(
                    self, "Import error",
                    "".join(msg_str)
                    )
                return False
            else:
                self.bobyqa_dlg._setUiByNestNumber(self.ui.comboBox_nestnumber.currentIndex() + 1)
                self.bobyqa_dlg.show_()
        elif method_name == "PSO":
            self.pso_dlg._setUiByNestNumber(self.ui.comboBox_nestnumber.currentIndex() + 1)
            self.pso_dlg.show_()
        
    def keyPressEvent( self, event ):
        if event.key == Qt.Key_Return or event.key == Qt.Key_Enter:
                pass
        else:
            QWidget.keyPressEvent( self, event )

from ui.ui_SelectParamByPsoDlg import Ui_SelectParamByPsoDlg
class SelectParamByPsoDlg(QDialog,Ui_SelectParamByPsoDlg):
    def __init__(self, parent_dlg):
        super(SelectParamByPsoDlg,self).__init__(parent_dlg)
        
        self.ui = Ui_SelectParamByPsoDlg()
        self.ui.setupUi(self) 
    
        self.parent_dlg = parent_dlg
         
        self.first_show = True
        #make Covariance obj
        self.cov = self.parent_dlg.cov #rename
        self.bme = self.parent_dlg.MainDlg.bmeobj # rename
        
        self.ui.pushButton_calculate.clicked.connect( self.calculate )
        self.ui.pushButton_close.clicked.connect( self.reject )

    def show_(self):
        if self.first_show:
             
            #find cov max
            lagSmax = self.cov.stvn[0][:,0][-1]
            lagTmax = self.cov.stvn[1][0][-1]
            lagCmax = self.cov.stvn[2][0][0]
            
            #set variable for auto fit
            self.c1small, self.c2small, self.c3small = (lagCmax/10.,) *3
            self.s1small, self.s2small, self.s3small = (lagSmax/10.,) *3
            self.t1small, self.t2small, self.t3small = (lagTmax/10.,) *3
            self.c1large, self.c2large, self.c3large = (lagCmax*5.,) *3
            self.s1large, self.s2large, self.s3large = (lagSmax*5.,) *3
            self.t1large, self.t2large, self.t3large = (lagTmax*5.,) *3
            
            #set PSO Parameters
            self.pn = 100
            self.ct = 10
            self.iw = 0.3
            self.sc = 1.0
            self.si = 1.3
            
            #Tab1
            #set PSO Objective Function Variables
            forloopitem1=["c","s","t"]
            forloopitem2=["1","2","3"]
            forloopitem3=["small","large"]
            for i in forloopitem1:
              for j in forloopitem2:
                for k in forloopitem3:
                  eval("self.ui.lineEdit_"+i+j+k).setText(str(eval("self."+i+j+k)))
                  eval("self.ui.lineEdit_"+i+j+k).setCursorPosition(0)
            #Tab2
            #set PSO Parameters
            self.ui.lineEdit_pn.setText(str(self.pn))
            self.ui.lineEdit_ct.setText(str(self.ct))
            self.ui.lineEdit_iw.setText(str(self.iw))
            self.ui.lineEdit_sc.setText(str(self.sc))
            self.ui.lineEdit_si.setText(str(self.si))
            
            self.first_show = False
        
        self.show()

    def calculate(self):
        # lump variable
        #set xb
        xb=[]
        index=self.parent_dlg.ui.comboBox_nestnumber.currentIndex()
    
        forloopitem1=["1","2","3"]
        forloopitem2=["c","s","t"]
        forloopitem3=["small","large"]
        for i in forloopitem1[0:index+1]:
          for j in forloopitem2:
            a=[]
            for k in forloopitem3:
                try:
                    a.append(float(eval('self.ui.lineEdit_'+j+i+k).text()))
                except ValueError:
                    QMessageBox.critical( self, 'Value Error',
                                                'Bound input should be a number.')
                    return
            xb.append(a)
        models = self._setModelByNestNumber(index + 1)
        args = (models,) #models
        flag = "m"

        try:
            pn = int(self.ui.lineEdit_pn.text())
            it = int(self.ui.lineEdit_ct.text())
            iw = float(self.ui.lineEdit_iw.text())
            sc = float(self.ui.lineEdit_sc.text())
            si = float(self.ui.lineEdit_si.text())
            vmp = None # will auto set by pso function later
        except ValueError:
            QMessageBox.critical( self, 'Value Error',
                                        'Parameters should be all number.')
            return

        #check  low_bnd and up_bnd
        for low_bnd, up_bnd in xb:
            if not up_bnd >= low_bnd:
                QMessageBox.critical( self, 'Value Error',
                                            'Upper bound should not be smaller than lower bound')
                return

        opt_location, opt_value = self.cov.selectParamByPso(xb,args,flag,pn,it,iw,sc,si,vmp)
        self._setUiByOptLocation(opt_location)
        
        self.parent_dlg.fit()
        
    def _setUiByNestNumber(self, nn):
        if nn == 1:
            self.ui.widget_2.setDisabled(True)
            self.ui.widget_3.setDisabled(True)
        elif nn == 2:
            self.ui.widget_2.setDisabled(False)
            self.ui.widget_3.setDisabled(True)
        elif nn == 3:
            self.ui.widget_2.setDisabled(False)
            self.ui.widget_3.setDisabled(False)    

    def _setModelByNestNumber(self, nn):
        models = []
        for i in range(nn):
            model = [None] * 5
            models.append(model)
        
        if nn == 1:
            models[0][1] = str(self.parent_dlg.ui.comboBox_s1.currentText()).lower()
            models[0][3] = str(self.parent_dlg.ui.comboBox_t1.currentText()).lower()
        elif nn == 2:
            models[0][1] = str(self.parent_dlg.ui.comboBox_s1.currentText()).lower()
            models[0][3] = str(self.parent_dlg.ui.comboBox_t1.currentText()).lower()
            models[1][1] = str(self.parent_dlg.ui.comboBox_s2.currentText()).lower()
            models[1][3] = str(self.parent_dlg.ui.comboBox_t2.currentText()).lower()
        elif nn == 3:
            models[0][1] = str(self.parent_dlg.ui.comboBox_s1.currentText()).lower()
            models[0][3] = str(self.parent_dlg.ui.comboBox_t1.currentText()).lower()
            models[1][1] = str(self.parent_dlg.ui.comboBox_s2.currentText()).lower()
            models[1][3] = str(self.parent_dlg.ui.comboBox_t2.currentText()).lower()
            models[2][1] = str(self.parent_dlg.ui.comboBox_s3.currentText()).lower()
            models[2][3] = str(self.parent_dlg.ui.comboBox_t3.currentText()).lower()
            
        return models
    
    def _setUiByOptLocation(self,opt_location):
        cstlist = opt_location
        nn = len(opt_location) // 3
        sigftr = star_math.round_by_significant_feature
        sigftr_n = 4
    
        if nn >= 1:
            self.parent_dlg.ui.lineEdit_c1.setText(str(sigftr(cstlist[0],sigftr_n)))
            self.parent_dlg.ui.lineEdit_s1.setText(str(sigftr(cstlist[1],sigftr_n)))
            self.parent_dlg.ui.lineEdit_t1.setText(str(sigftr(cstlist[2],sigftr_n)))
            if nn >= 2:
                self.parent_dlg.ui.lineEdit_c2.setText(str(sigftr(cstlist[3],sigftr_n)))
                self.parent_dlg.ui.lineEdit_s2.setText(str(sigftr(cstlist[4],sigftr_n)))
                self.parent_dlg.ui.lineEdit_t2.setText(str(sigftr(cstlist[5],sigftr_n)))
                if nn == 3:
                    self.parent_dlg.ui.lineEdit_c3.setText(str(sigftr(cstlist[6],sigftr_n)))
                    self.parent_dlg.ui.lineEdit_s3.setText(str(sigftr(cstlist[7],sigftr_n)))
                    self.parent_dlg.ui.lineEdit_t3.setText(str(sigftr(cstlist[8],sigftr_n)))


from ui.ui_SelectParamByBobyqaDlg import Ui_SelectParamByBobyqaDlg
class SelectParamByBobyqaDlg(QDialog,Ui_SelectParamByBobyqaDlg):
    def __init__(self, parent_dlg):
        super(SelectParamByBobyqaDlg,self).__init__(parent_dlg)
        
        self.ui = Ui_SelectParamByBobyqaDlg()
        self.ui.setupUi(self) 
    
        self.parent_dlg = parent_dlg
         
        self.first_show = True
        #make Covariance obj
        self.cov = self.parent_dlg.cov #rename
        self.bme = self.parent_dlg.MainDlg.bmeobj # rename

        self.ui.pushButton_calculate.clicked.connect( self.calculate )
        self.ui.pushButton_close.clicked.connect( self.reject )
        self.ui.pushButton_lastfitting.clicked.connect( self.setInitialGuessFromLastFitting )

    def show_(self):
        if self.first_show:
             
            #find cov max
            lagSmax = self.cov.stvn[0][:,0][-1]
            lagTmax = self.cov.stvn[1][0][-1]
            lagCmax = self.cov.stvn[2][0][0]
            
            #set variable for auto fit
            self.c1small, self.c2small, self.c3small = (lagCmax/10.,) *3
            self.s1small, self.s2small, self.s3small = (lagSmax/10.,) *3
            self.t1small, self.t2small, self.t3small = (lagTmax/10.,) *3
            self.c1large, self.c2large, self.c3large = (lagCmax*5.,) *3
            self.s1large, self.s2large, self.s3large = (lagSmax*5.,) *3
            self.t1large, self.t2large, self.t3large = (lagTmax*5.,) *3
            self.c1guess = (self.c1small + self.c1large)/2.
            self.c2guess = (self.c2small + self.c2large)/2.
            self.c3guess = (self.c3small + self.c3large)/2.
            self.s1guess = (self.s1small + self.s1large)/2.
            self.s2guess = (self.s2small + self.s2large)/2.
            self.s3guess = (self.s3small + self.s3large)/2.
            self.t1guess = (self.t1small + self.t1large)/2.
            self.t2guess = (self.t2small + self.t2large)/2.
            self.t3guess = (self.t3small + self.t3large)/2.
            
            if self.parent_dlg.MainDlg.isSpatialOnly():
                for i in ['1','2','3']:
                    setattr(self,'t'+i+'small',11111)
                    setattr(self,'t'+i+'large',99999)
                    setattr(self,'t'+i+'guess',74208)
                    eval('self.ui.twgt'+i).hide()
                
            

            
            #Tab1
            #set BOBYQA Objective Function Variables
            forloopitem1=["c","s","t"]
            forloopitem2=["1","2","3"]
            forloopitem3=["small","large"]
            for i in forloopitem1:
              for j in forloopitem2:
                eval("self.ui.lineEdit_"+i+j+"guess").setText(str(eval("self."+i+j+"guess")))
                eval("self.ui.lineEdit_"+i+j+"guess").setCursorPosition(0)
                for k in forloopitem3:
                  eval("self.ui.lineEdit_"+i+j+k).setText(str(eval("self."+i+j+k)))
                  eval("self.ui.lineEdit_"+i+j+k).setCursorPosition(0)
            
            self.first_show = False
        
        self.show()

    def calculate(self):
        # lump variable
        #set xb and xinit
        xb=[]
        xinit=[]
        index=self.parent_dlg.ui.comboBox_nestnumber.currentIndex()
    
        forloopitem1=["1","2","3"]
        forloopitem2=["c","s","t"]
        forloopitem3=["small","large"]
        for i in forloopitem1[0:index+1]:
          for j in forloopitem2:
            a=[]
            try:
                xinit.append( float( eval( 'self.ui.lineEdit_' + j+i+"guess" ).text() ))
            except ValueError:
                QMessageBox.critical( self, 'Value Error',
                                     'Initial guess should be a number.')
                return
            for k in forloopitem3:
                try:
                    a.append( float( eval( 'self.ui.lineEdit_' + j+i+k ).text() ) )
                except ValueError:
                    QMessageBox.critical( self, 'Value Error',
                                                'Lower or upper bound should be a number.')
                    return
            xb.append( a )
     
        init_guess = numpy.array( xinit )
        low_bnd, up_bnd = zip(*xb)
        low_bnd = numpy.array(low_bnd)
        up_bnd = numpy.array(up_bnd)

        #check init_guess is between low_bnd and up_bnd
        if not ( up_bnd >= low_bnd ).all():
            QMessageBox.critical( self, 'Value Error',
                                        'Upper bound should not be smaller than lower bound')
            return

        if not ( init_guess >= low_bnd ).all():
            QMessageBox.critical( self, 'Value Error',
                                        'Initial guess should be larger than lower bound')
            return
        if not ( up_bnd >= init_guess ).all():
            QMessageBox.critical( self, 'Value Error',
                                        'Initial guess should be smaller than upper bound')
            return


        
        models = self._setModelByNestNumber(index + 1)
        args = (models,) #models
        
        opt_location, opt_value = self.cov.selectParamByBobyqa( init_guess, (models,), low_bnd, up_bnd )
        self._setUiByOptLocation( opt_location )
        
        self.parent_dlg.fit()
      
    def setInitialGuessFromLastFitting( self ):

        #set BOBYQA Initial Guess
        forloopitem1=["c","s","t"]
        forloopitem2=["1","2","3"]
        forloopitem3=["guess"]
        for i in forloopitem1:
          for j in forloopitem2:
            content = getattr( self.parent_dlg.ui, 'lineEdit_{i}{j}'.format( i = i, j = j ) )
            eval("self.ui.lineEdit_"+i+j+"guess").setText( content.text() )
            eval("self.ui.lineEdit_"+i+j+"guess").setCursorPosition(0)

    def _setUiByNestNumber(self, nn):
        if nn == 1:
            self.ui.widget_2.setDisabled(True)
            self.ui.widget_3.setDisabled(True)
        elif nn == 2:
            self.ui.widget_2.setDisabled(False)
            self.ui.widget_3.setDisabled(True)
        elif nn == 3:
            self.ui.widget_2.setDisabled(False)
            self.ui.widget_3.setDisabled(False)    

    def _setModelByNestNumber(self, nn):
        models = []
        for i in range(nn):
            model = [None] * 5
            models.append(model)
        
        if nn == 1:
            models[0][1] = str(self.parent_dlg.ui.comboBox_s1.currentText()).lower()
            models[0][3] = str(self.parent_dlg.ui.comboBox_t1.currentText()).lower()
        elif nn == 2:
            models[0][1] = str(self.parent_dlg.ui.comboBox_s1.currentText()).lower()
            models[0][3] = str(self.parent_dlg.ui.comboBox_t1.currentText()).lower()
            models[1][1] = str(self.parent_dlg.ui.comboBox_s2.currentText()).lower()
            models[1][3] = str(self.parent_dlg.ui.comboBox_t2.currentText()).lower()
        elif nn == 3:
            models[0][1] = str(self.parent_dlg.ui.comboBox_s1.currentText()).lower()
            models[0][3] = str(self.parent_dlg.ui.comboBox_t1.currentText()).lower()
            models[1][1] = str(self.parent_dlg.ui.comboBox_s2.currentText()).lower()
            models[1][3] = str(self.parent_dlg.ui.comboBox_t2.currentText()).lower()
            models[2][1] = str(self.parent_dlg.ui.comboBox_s3.currentText()).lower()
            models[2][3] = str(self.parent_dlg.ui.comboBox_t3.currentText()).lower()
            
        return models
    
    def _setUiByOptLocation(self,opt_location):
        cstlist = opt_location
        nn = len(opt_location) // 3
    
        if nn == 1:
            self.parent_dlg.ui.lineEdit_c1.setText(str(round(cstlist[0],2)))
            self.parent_dlg.ui.lineEdit_s1.setText(str(round(cstlist[1],2)))
            self.parent_dlg.ui.lineEdit_t1.setText(str(round(cstlist[2],2)))
        elif nn == 2:
            self.parent_dlg.ui.lineEdit_c1.setText(str(round(cstlist[0],2)))
            self.parent_dlg.ui.lineEdit_s1.setText(str(round(cstlist[1],2)))
            self.parent_dlg.ui.lineEdit_t1.setText(str(round(cstlist[2],2)))
            self.parent_dlg.ui.lineEdit_c2.setText(str(round(cstlist[3],2)))
            self.parent_dlg.ui.lineEdit_s2.setText(str(round(cstlist[4],2)))
            self.parent_dlg.ui.lineEdit_t2.setText(str(round(cstlist[5],2)))
        elif nn == 3:
            self.parent_dlg.ui.lineEdit_c1.setText(str(round(cstlist[0],2)))
            self.parent_dlg.ui.lineEdit_s1.setText(str(round(cstlist[1],2)))
            self.parent_dlg.ui.lineEdit_t1.setText(str(round(cstlist[2],2)))
            self.parent_dlg.ui.lineEdit_c2.setText(str(round(cstlist[3],2)))
            self.parent_dlg.ui.lineEdit_s2.setText(str(round(cstlist[4],2)))
            self.parent_dlg.ui.lineEdit_t2.setText(str(round(cstlist[5],2)))
            self.parent_dlg.ui.lineEdit_c3.setText(str(round(cstlist[6],2)))
            self.parent_dlg.ui.lineEdit_s3.setText(str(round(cstlist[7],2)))
            self.parent_dlg.ui.lineEdit_t3.setText(str(round(cstlist[8],2)))
