import os
import sys
import numpy
#from PyQt4.QtCore import *
from qgis.PyQt.QtCore import *
#from PyQt4.QtGui import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from multiprocessing import cpu_count
MAX_CPU_COUNT = cpu_count()

from ui.ui_BmeEstDlg import Ui_BmeEstDlg


import star_math

current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(current_dir,'..','lib'))
from rawdata2griddata import rawdata2griddata
import function_task

class BmeEstDlg(QDialog,Ui_BmeEstDlg):
    def __init__(self,iface = None, MainDlg = None):
        def tryToLoadLastSetting():
            if self.bme.nhmax:
                order_load_idx = self.ui.comboBox_order.findText( self.bme.order )
                self.ui.comboBox_order.setCurrentIndex( order_load_idx )
                self.ui.lineEdit_spatialrange.setText(str(self.bme.dmax[0][0]))
                self.ui.lineEdit_temporalrange.setText(str(self.bme.dmax[0][1]))
                self.ui.lineEdit_nhmax.setText(str(self.bme.nhmax))
                self.ui.lineEdit_nsmax.setText(str(self.bme.nsmax))
                self.ui.lineEdit_stratio.setText(str(self.bme.dmax[0][2]))

            else: #set default value
                main_cov_models = sorted( self.bme.covariance.models, 
                                          key = lambda x:x[0] )[-1]
                s_range = main_cov_models[2]
                t_range = main_cov_models[4]
                self.ui.lineEdit_spatialrange.setText( str( star_math.round_by_significant_feature( s_range ) ) )
                self.ui.lineEdit_temporalrange.setText( str( star_math.round_by_significant_feature( t_range ) ) )
                self.ui.lineEdit_nhmax.setText( str( 5 ) )
                self.ui.lineEdit_nsmax.setText( str( 3 ) )
                self.ui.lineEdit_stratio.setText( str( star_math.round_by_significant_feature( s_range / float(t_range) ) ) )

            #congifures
            MAX_CPU_count = cpu_count()
            self.ui.comboBox_worker_n.addItems(list(map(str, range(1, MAX_CPU_COUNT + 1) )))
            self.ui.comboBox_worker_n.setCurrentIndex(MAX_CPU_COUNT - 1)
            maxevalnum = self.bme.options[2][0]
            relerr = self.bme.options[3][0]
            self.ui.lineEdit_max_eval_num.setText(str(maxevalnum))
            self.ui.lineEdit_rel_err.setText(str(relerr))
            # Restore fast approx setting
            self.ui.checkBox_fast_approx.setChecked(
                bool(self.bme.options['soft_approx_gaussian']))
            # Restore PCA integration threshold
            pca_thr = self.bme.options.get('pca_integration_threshold', 0.999)
            self.ui.lineEdit_pca_threshold.setText(str(pca_thr))
            # Restore non-negativity constraint
            self.ui.checkBox_nonneg.setChecked(
                bool(self.bme.options.get('nonneg_estimate', False)))



        super(BmeEstDlg,self).__init__(MainDlg)
        self.iface=iface
        self.MainDlg=MainDlg
        
        self.ui=Ui_BmeEstDlg()
        self.ui.setupUi(self)
        
        #rename
        self.bme = self.MainDlg.bmeobj

        self.ui.pushButton_estimate.clicked.connect( self.estimate )
        self.ui.pushButton_cancel.clicked.connect( self.reject )
        
        tryToLoadLastSetting()

    def addProgressCount(self, args):
        self.qpgd.setValue( self.qpgd.value() + 1 )

    def setProgressRange(self, args):
        min_, max_ = args
        self.qpgd.setRange(int(min_), int(max_))

    def setCurrentProgress(self, args):
        value, text = args
        if text:
            self.qpgd.setLabelText(text)
        if value:
            self.qpgd.setValue(value)

    def threadFinished(self, args):
        #calculate trend
        moments_temp, info_temp = args #rename
        self.bme.moments_temp = moments_temp
        self.bme.info_temp = info_temp
        
        # get estimatedtrend
        result = self.bme.estimated_data.estimateTrend(self.bme.trend)
        if not result:
            return False
        else:
            pass #setting tr and tr_grid for estimated_data success
        moments_np = numpy.array(moments_temp)
        info_np = numpy.array(info_temp)
        self.bme.estimated_data.z_mean = (moments_np[:,0] + self.bme.estimated_data.tr.flatten()).reshape((-1,1))
        self.bme.estimated_data.z_variance =  moments_np[:,1].reshape((-1,1))
        
        
        mean_grid = rawdata2griddata(self.bme.estimated_data.x,
                                     self.bme.estimated_data.y,
                                     self.bme.estimated_data.t,
                                     self.bme.estimated_data.z_mean, self.bme)
        if not mean_grid:
            return False
        else:
            pass 
        self.bme.estimated_data.z_mean_grid = mean_grid[2]
        
        variance_grid = rawdata2griddata(self.bme.estimated_data.x,
                                         self.bme.estimated_data.y,
                                         self.bme.estimated_data.t,
                                         self.bme.estimated_data.z_variance, self.bme)
        if not variance_grid:
            return False
        else:
            pass 
        self.bme.estimated_data.z_variance_grid = variance_grid[2]
        
        self.bme.estimated_data.updateDataInfo()

        self.bme.setProgressAutoClose(True)
        self.bme.progress_dialog.close()
        self.bme.estimated_data.setProgressAutoClose(True)
        self.bme.estimated_data.progress_dialog.close()
        
        self.ui.pushButton_cancel.setText("Close")
        self.MainDlg.setStage(40)
        self.MainDlg.buttonsUpdate()
        self.MainDlg.dirty = True
        
        QMessageBox.information(self,"OK","BME Estimation is Finished!\n") 
        self.accept()

    def threadCanceled(self, args):
        return False

    def canceledByUser(self):
        self.bmethread.was_canceled = True
        self.bmethread.wait()
    
    def estimate(self):
        
        self.qpgd = QProgressDialog(self)
        self.qpgd.setWindowTitle('BME Estimation')
        self.qpgd.setWindowModality(Qt.WindowModal)
        # self.qpgd.canceled.connect( self.canceledByUser )
        self.qpgd.show()
        
        try:
            order = str(self.ui.comboBox_order.currentText())
        except ValueError:
            QMessageBox.critical(self, "Type Error", "Order should be string.")
            return
        try:
            nhmax = int(self.ui.lineEdit_nhmax.text())
        except ValueError:
            QMessageBox.critical(self, "Type Error", "Nhmax should be int.")
            return
        try:
            nsmax = int(self.ui.lineEdit_nsmax.text())
        except ValueError:
            QMessageBox.critical(self, "Type Error", "Nsmax should be int.")
            return
        try:
            dmax = numpy.array(
                [
                    float(self.ui.lineEdit_spatialrange.text()),
                    float(self.ui.lineEdit_temporalrange.text()),
                    float(self.ui.lineEdit_stratio.text())
                ]
            )
        except ValueError:
            QMessageBox.critical(self, "Type Error", "range or(and) ratio should be float.")
            return
        
        selected_cpu_count = int(self.ui.comboBox_worker_n.currentText())
        try:
            maxevalnum = int(float(self.ui.lineEdit_max_eval_num.text()))
        except ValueError:
            QMessageBox.critical(self, "Type Error", "MaxEvalNum should be int.")
            return
        try:
            relerr = float(self.ui.lineEdit_rel_err.text())
        except ValueError:
            QMessageBox.critical(self, "Type Error", "RelErr should be float.")
            return

        self.bme.setOptions(2, maxevalnum)
        self.bme.setOptions(3, relerr)

        # Fast Gaussian Approximation toggle
        fast_approx = self.ui.checkBox_fast_approx.isChecked()
        self.bme.options['soft_approx_gaussian'] = fast_approx

        # PCA integration threshold
        try:
            pca_thr = float(self.ui.lineEdit_pca_threshold.text())
            if not (0.0 < pca_thr <= 1.0):
                raise ValueError
        except ValueError:
            QMessageBox.critical(
                self, "Type Error",
                "PCA Variance Threshold must be a float between 0 and 1 "
                "(e.g. 0.999). Set to 1.0 to disable PCA truncation.")
            return
        self.bme.options['pca_integration_threshold'] = pca_thr

        # Non-negativity constraint
        self.bme.options['nonneg_estimate'] = self.ui.checkBox_nonneg.isChecked()

        self.bme.setOrder(order)
        self.bme.setNhmax(nhmax)
        self.bme.setNsmax(nsmax)
        self.bme.setDmax(dmax)
        
        self.bme.setProgressDialog(self.qpgd)
        self.bme.setProgressAutoClose(False)
        self.bme.estimated_data.setProgressDialog(self.qpgd)
        self.bme.estimated_data.setProgressAutoClose(False)

        if self.bme.estimate(n_workers=selected_cpu_count):
            self.bme.setProgressAutoClose(True)
            self.bme.progress_dialog.close()
            self.bme.estimated_data.setProgressAutoClose(True)
            self.bme.estimated_data.progress_dialog.close()
            
            self.ui.pushButton_cancel.setText("Close")
            self.MainDlg.setStage(40)
            self.MainDlg.buttonsUpdate()
            self.MainDlg.dirty = True
            
            QMessageBox.information(self,"OK","BME Estimation is Finished!\n") 
            self.accept()
        else:
            return
            


class BMEProbaMomentsThread(QThread):

    sig_progress_count = pyqtSignal(object)
    sig_set_progress_range = pyqtSignal(object)
    sig_set_current_progress = pyqtSignal(object)
    sig_finished = pyqtSignal(object)
    sig_canceled = pyqtSignal(object)

    def __init__(
        self, bmeobj, other_process_number = max(0, MAX_CPU_COUNT - 1),
        parent = None
        ):
        super(BMEProbaMomentsThread,self).__init__(parent)

        self.bmeobj = bmeobj
        self.other_process_number = other_process_number
        self.total_process_number = other_process_number + 1
        self.parent = parent
        self.was_canceled = False

        self.sig_progress_count[object].connect(parent.addProgressCount)
        self.sig_set_progress_range[object].connect(parent.setProgressRange)
        self.sig_set_current_progress[object].connect(parent.setCurrentProgress)
        self.sig_finished[object].connect(parent.threadFinished)
        self.sig_canceled[object].connect(parent.threadCanceled)

    def wasCanceled(self):
        return self.was_canceled

    def run(self):
        ck_i = self.bmeobj.getDividedCk(self.total_process_number)
        constant_args = self.bmeobj.getFunctionParameters()[1:] #skip ck
        args_list = [ [ i ] + constant_args for i in ck_i ]

        #make other_process subprocess
        current_dir = os.path.abspath(os.path.dirname(__file__))
        task_search_path = (os.path.join(current_dir,'..','lib'),)
        non_gui_process_list = []
        for i in range(self.other_process_number):
            non_gui_process_list.append(
                function_task.create_func_task(
                    'BMEprobaMoments',
                    'BMEprobaMoments',
                    task_search_path
                    )
                )
        #start subprocess
        for proc, args in zip(non_gui_process_list, args_list[:-1]):
            function_task.start_function(proc, args)

        if self.wasCanceled(): #user cancelled immediately
            #kill other process
            for proc in non_gui_process_list:
                proc.kill()
            self.sig_canceled.emit(None)
            return False
        #do the gui part
        self.gui_args = args_list[-1]+[None,self] #None for qpgd
        self.sig_set_progress_range.emit( (0,len(ck_i[-1])) )
        self.sig_set_current_progress.emit( (0, "BME Estimation Starts...") )

        result = self.bmeobj.calculateBMEprobaMomentsResult(self.gui_args)
        if result: #can use
            #collect all result
            r_list = []
            for proc in non_gui_process_list:
                r_list.append(function_task.get_result(proc))
            r_list.append(result)
            moments, info = zip(*r_list)
            moments = numpy.vstack(moments)
            info = numpy.vstack(info)

            self.sig_finished.emit((moments, info))
            return True
        else: #canceled by user
            #kill other process
            for proc in non_gui_process_list:
                proc.kill()
            self.sig_canceled.emit(None)
            return False
