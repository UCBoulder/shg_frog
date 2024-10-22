"""
This module loads the MainWindow of the GUI from a QTdesigner file
and connects all widgets to the methods of the devices.

File name: main_window.py
Author: Julian Krauth
Date created: 2019/12/02
Python Version: 3.7
"""
import pathlib
import numpy as np

from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QTransform
from pyqtgraph.parametertree import ParameterTree
import pyqtgraph as pg
from scipy.constants import c as C_MKS

from . import general_worker
from .roi_window import ROIGraphics
from .retrieval_window import RetrievalWindow
from ..model.frog import FROG
from ..helpers.file_handler import DATA_DIR, INTERNAL_DATA_DIR

class MainWindow(QtWidgets.QMainWindow):
    """This is the main window of the GUI for the FROG interface.
    The window is designed with Qt Designer and loaded into this class.
    """

    DEFAULTS = {
        'dev': {
            0: 'Spectrometer',
            1: 'Camera',
        },
        'btn_connect': {
            True: 'Disconnect',
            False: 'Connect',
        },
        'btn_color': {
            True: 'rgb(239, 41, 41)',
            False: 'rgb(138, 226, 52)',
        },
        'btn_measure': {
            True: 'Stop',
            False: 'Measure',
        },
    }


    def __init__(self, frog: FROG=None, parent=None, test: bool=False):
        super().__init__(parent)

        # The object which is connected to the window
        self.frog = frog

        # Loading the GUI created with QTdesigner
        gui_path = pathlib.Path(__file__).parent / 'GUI'
        uic.loadUi(gui_path / 'main_window.ui', self)

        # Change window title if running in test mode
        if test:
            self.setWindowTitle('SHG FROG (test)')

        # Set window icon
        self.setWindowIcon(QtGui.QIcon(str(gui_path / 'icon.png')))

        self.menu_exit.triggered.connect(self.save_and_close_action)

        # Timer used to update certain values with a fixed interval (Timer starts after connecting)
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(500) #ms
        self.update_timer.timeout.connect(self.update_values)

        # Connect button
        self.btn_connect.toggled.connect(self.connect_action)

        # Measure button
        self.btn_measure.toggled.connect(self.measure_action)

        # Save measurement button
        self.btn_save.clicked.connect(self.save_action)

        # Load measurement button
        self.btn_load.clicked.connect(self.load_action)

        # Take spectrum button
        self.btn_collect_spectrum.clicked.connect(self.start_spectrum_action)

        # Take spectrum background button
        self.btn_subtract_background.clicked.connect(self.spectrum_background_action)

        # Create Parametertree from FrogParams class
        self.par_class = self.frog.parameters
        self.par = self.par_class.par
        self.print_changes(True)
        # Create ParameterTree widget filled with above parameters
        self.parameter_tree = ParameterTree()
        self.parameter_tree.setParameters(self.par, showTop=False)
        self.gridLayout.addWidget(self.parameter_tree, 1, 0, 1, 2)
        # Implement Actions for ParameterTree
        self.tree_retrieval_actions()
        self.tree_stage_actions()
        self.tree_camera_actions()
        self.tree_spectrometer_actions()

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Create the plot window
        self.graphics_widget = FrogGraphics()
        self.gridLayout_2.addWidget(self.graphics_widget,1,0,1,3)

        # Create instance for region of interest (ROI) window
        # This window will be opened and closed by the class' methods
        self.roi_win = ROIGraphics()
        self.btn_roi.clicked.connect(self.roi_action)

        # Attribute for measurement thread
        self.measure_thread = None

        # Attribute for spectrum thread
        self.spectrum_thread = None

        # Attribute for phase retrieval window and thread
        self.retrieval_win = None
        self.phase_thread = None

        # Phase retrieve button
        self.btn_phase.clicked.connect(self.phase_action)

        # Load recent settings
        self.frog.parameters.restore_state()
        # Load test trace at start up
        self.load_test_trace()

    def closeEvent(self, event):
        self.save_and_close_action()

    def print_changes(self, val: bool):
        """ Control whether parameter changes are printed. """
        self.par_class.print_par_changes(val)

    def save_and_close_action(self):
        """ (Disconnect devices, ) Save parameter state and close window. """
        if self.btn_connect.isChecked():
            self.btn_connect.toggle()
        self.frog.parameters.save_state()
        self.close()

    @QtCore.pyqtSlot(bool)
    def connect_action(self, checked):
        """Connect to devices selected in the dropdown menu.
        Adapt button color and text accordingly."""
        # Get dictionaries
        dev = self.DEFAULTS['dev']
        btn = self.DEFAULTS['btn_connect']
        col = self.DEFAULTS['btn_color']
        # Get dropdown position
        index = self.dropdown.currentIndex() # not used at the moment.
        # Do GUI actions
        self.dropdown.setEnabled(not checked) # only use once ANDO implemented
        if dev[index]=="Camera":
            self.btn_roi.setEnabled(checked)
        self.btn_connect.setText(btn[checked])
        self.btn_connect.setStyleSheet(f"background-color:{col[checked]}")
        self.btn_measure.setEnabled(checked)
        self.btn_collect_spectrum.setEnabled(checked)
        self.btn_subtract_background.setEnabled(checked)
        # Open device and respective branch of parameter tree
        if checked:
            self.frog.initialize()
            self.frog.spectrometer.integration_time = self.par.param('Spectrometer').child('Integration Time').value() * 1e-3
            device = dev[index]
            self.par.param(device).show()
            self.par.param('Stage').show()
            self.frog._config['spectral device'] = device
            self.update_timer.start()
        else:
            self.update_timer.stop()
            self.frog.close()
            self.par.param(dev[index]).hide()
            self.par.param('Stage').hide()
        # needed for updating par tree in GUI
        self.parameter_tree.setParameters(self.par, showTop=False)

    def tree_retrieval_actions(self):
        """ Connect retrieval options. """
        retrieval_par = self.par.child('Phase Retrieval')
        size_par = retrieval_par.child('prepFROG Size')
        size_par.sigValueChanged.connect(lambda _, val: self.frog.algo.set_size(val))
        iter_seed_par = retrieval_par.child('Seed')
        iter_seed_par.sigValueChanged.connect(lambda _, val: self.frog.algo.set_seed_mode(val))
        iter_max_par = retrieval_par.child('Max. Iterations')
        iter_max_par.sigValueChanged.connect(lambda _, val: self.frog.algo.set_max_iterations(val))
        tolerance_par = retrieval_par.child('G Tolerance')
        tolerance_par.sigValueChanged.connect(lambda _, val: self.frog.algo.set_tolerance(val))

    def tree_stage_actions(self):
        stage_par = self.par.param('Stage')
        # Stage Position
        go_par = stage_par.child('GoTo')
        go_par.sigValueChanged.connect(lambda _, val: self.frog.stage.move_abs(val * 1e-6))

    def tree_camera_actions(self):
        """ Connect camera functionality. """
        camera_par = self.par.param('Camera')
        expos_par = camera_par.child('Exposure')
        expos_par.sigValueChanged.connect(lambda _, val: self.frog.camera.set_exposure(val))
        gain_par = camera_par.child('Gain')
        gain_par.sigValueChanged.connect(lambda _, val: self.frog.camera.set_gain(val))
        crop_par = camera_par.child('Crop Image')
        crop_par.sigTreeStateChanged.connect(self.crop_action)
        tsource_par = camera_par.child('Trigger').child('Source')
        tsource_par.sigValueChanged.connect(lambda _, val: self.frog.camera.set_trig_source(val))

    #TODO
    def tree_spectrometer_actions(self):
        """ Connect ando functionality. """
        spectrometer_par = self.par.param('Spectrometer')
        ctr_par = spectrometer_par.child('Center')
        ctr_par.sigValueChanged.connect(lambda param, val: self.frog.set_center(val * 1e-9))
        self.frog.set_center(ctr_par.value() * 1e-9)
        span_par = spectrometer_par.child('Span')
        span_par.sigValueChanged.connect(lambda param, val: self.frog.set_span(val * 1e-9))
        self.frog.set_span(span_par.value() * 1e-9)
        int_time_par = spectrometer_par.child('Integration Time')
        int_time_par.sigValueChanged.connect(lambda param, val: self.frog.set_integration_time(val * 1e-3))



    def crop_action(self, param, changes):
        """Define what happens when changing the crop/roi parameters in the parameter tree"""
        dictio = {'Width':'width','Height':'height',
                'Xpos':'offsetx','Ypos':'offsety'}
        for param, change, data in changes:
            if change=='value':
                self.frog.camera.set_roi(**{dictio[param.name()]:data})
                #print dict[param.name()], data

    def roi_action(self):
        """Defines the actions when calling the ROI button"""
        # Create ROI window with a full image taken by the camera
        self.roi_win.show()
        self.roi_win.set_image(self.frog.camera.take_full_img())
        # Set the ROI frame according to the crop parameters in parameter tree
        self.roi_win.update_ROI_frame(*self.par_class.get_crop_par())
        # If ROI changes, update parameters, update_crop_param() makes sure that crop parameters
        # don't extend over edges of image. This means that the crop parameters which are set
        # can differ from the roi frame in the roi window. In a second step the roi frame is then
        # updated to reflect the actual crop parameters.
        self.roi_win.roi.sigRegionChangeFinished.connect(self.par_class.update_crop_param)
        self.par.sigTreeStateChanged.connect(\
            lambda param,changes: self.roi_win.update_ROI_frame(*self.par_class.get_crop_par()))

    def start_spectrum_action(self):
        ''' Retrievs the spectrum outside the context of a FROG measuremnt '''
        self.spectrum_thread = general_worker.SpectrometerThread(self.frog.measure_spectrum)
        self.spectrum_thread.sig_measure.connect(self.graphics_widget.update_graphics)
        self.spectrum_thread.finished.connect(self.del_specthread)
        self.spectrum_thread.start()

        self.btn_collect_spectrum.setText("Stop Collection")
        self.btn_collect_spectrum.clicked.disconnect()
        self.btn_collect_spectrum.clicked.connect(self.stop_spectrum_action)
    
    def stop_spectrum_action(self):
        ''' Stops spectrum retrieval '''
        self.frog.stop_spectrum_measure = True
        self.btn_collect_spectrum.setText("Collect Spectrum")
        self.btn_collect_spectrum.clicked.disconnect()
        self.btn_collect_spectrum.clicked.connect(self.start_spectrum_action)

    def spectrum_background_action(self):
        '''Takes background spectrum'''
        measuring = self.spectrum_thread is not None
        if measuring:
            self.spectrum_thread.finished.connect(self.frog.measure_background)
            self.spectrum_thread.finished.connect(self.start_spectrum_action)
            self.frog.stop_spectrum_measure = True
        else:
            self.frog.measure_background()

    @QtCore.pyqtSlot(bool)
    def measure_action(self, checked):
        """Executed when measure/stop button is pressed"""
        btn = self.DEFAULTS['btn_measure']
        self.btn_measure.setText(btn[checked])
        if checked:
            # Stop the spectrum collection thread
            self.stop_spectrum_action()
            self.progress.setValue(0)
            # Do actual measurement loop (in separate thread)
            self.start_measure()
        if not checked:
            self.frog.stop_measure = True

    def start_measure(self):
        """Retrieves measurement settings and wraps the measure function
        into a thread. Then the signals are implemented."""
        # Create thread
        self.measure_thread = general_worker.MeasureThread(self.frog.measure)
        # Actions when measurement finishes
        self.measure_thread.finished.connect(self.measure_thread.deleteLater)
        self.measure_thread.finished.connect(self.del_mthread)
        self.measure_thread.finished.connect(self.uncheck_btn_measure)
        # Connect progress button with progress signal
        self.measure_thread.sig_progress.connect(self.modify_progress)
        # Connect plot update with measure signal
        self.measure_thread.sig_measure.connect(self.graphics_widget.update_graphics)
        #TODO do the scale update here
        self.update_frog_axes()
        # Run measurement
        self.measure_thread.start()
    
    def update_frog_axes(self):
        wavelengths = self.frog.spectrometer.wavelengths() 
        wlrange = np.where((wavelengths >= self.frog.center -self.frog.span/2) & (wavelengths<= self.frog.center + self.frog.span/2))
        wavelengths=wavelengths[wlrange]
        meta = self.frog._get_settings()
        start_pos = meta['start position'] 
        start_time = 2*start_pos/C_MKS
        self.graphics_widget.update_frog_axes([start_time, -start_time],[np.min(wavelengths),np.max(wavelengths)], meta['step number'], len(wavelengths))
    

    def del_mthread(self):
        self.measure_thread = None
    
    def del_specthread(self):
        self.spectrum_thread = None

    def uncheck_btn_measure(self):
        self.btn_measure.setChecked(False)

    def save_action(self):
        """ Open dialog to request a comment, then save the data. """
        # Ask user for a measurement comment
        dialog = CommentDialog(self)
        if dialog.exec():
            comment = dialog.get_comment()
            self.frog.save_measurement_data(comment)
        else:
            print('Data not saved.')


    def load_test_trace(self):
        """ Load the test trace """
        plot_data = self.frog.load_measurement_data(INTERNAL_DATA_DIR)
        self.graphics_widget.update_graphics(2, plot_data)

    def load_action(self):
        """ Open dialog to choose a measurement data to load. """
        load_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select measurement folder', str(DATA_DIR)
            )
        # If user presses cancel, an empty string is returned.
        if load_dir == "":
            return
        try:
            plot_data = self.frog.load_measurement_data(pathlib.Path(load_dir))
            self.graphics_widget.update_graphics(2, plot_data)
        except FileNotFoundError:
            print(
                "Error: This directory does not contain the files " + \
                "with the correct file names."
                )

    def update_values(self):
        """Used for values which are continuously updated using QTimer"""
        pos_par = self.par.param('Stage').child('Position')
        pos_par.setValue(self.frog.stage.position * 1e6)

    def modify_progress(self, iter_val):
        """For changing the progress bar, using an iteration value"""
        max_val = self.par.param('Stage').child('Number of steps').value()
        val = int(100*(float(iter_val)/float(max_val)))
        self.progress.setValue(val)

    def phase_action(self):
        """ Create Retrieval window and start phase retrieval loop in separate thread. """
        if not self.frog.data_available:
            print('Error: No data for phase retrieval found.')
            return
        # Open retrieval window, if necessary close previous one to avoid warning.
        if self.retrieval_win is not None:
            # This avoids a warning when you start a retrieval while the
            # window is still open.
            self.retrieval_win.close()
        self.retrieval_win = RetrievalWindow(self.frog.algo)
        self.retrieval_win.show()
        # Create thread
        self.phase_thread = general_worker.RetrievalThread(self.frog.retrieve_phase)
        # Actions when retrieval finishes
        self.phase_thread.finished.connect(self.phase_thread.deleteLater)
        self.phase_thread.finished.connect(self.del_pthread)
        # Connect signals
        self.phase_thread.sig_retdata.connect(self.retrieval_win.graphics.update_graphics)
        self.phase_thread.sig_retlabels.connect(self.retrieval_win.graphics.update_labels)
        self.phase_thread.sig_rettitles.connect(self.retrieval_win.graphics.update_title)
        self.phase_thread.sig_retaxis.connect(self.retrieval_win.graphics.set_axis)
        # Run phase retrieval
        self.phase_thread.start()

    def del_pthread(self):
        """Delete phase retrieval thread"""
        self.phase_thread = None


class FrogGraphics(pg.GraphicsLayoutWidget):
    """
    Class which implements the content for the graphics widget.
    It shows the recorded data and updates during measurement.
    """
    def __init__(self):
        super().__init__()
        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        data_slice = self.addPlot(title='Single Slice')
        
        data_slice.setLabel('bottom', "Wavelength", units='m')
        data_slice.setLabel('left', "Intensity", units='AU')
        self.spectrum_plot = data_slice.plot()

        vb_full = self.addPlot(title='FROG Trace')
        vb_full.setLabel('bottom',"Time Delay", units='s')
        vb_full.setLabel('left',"Wavelength", units='m')
        self.spectrogram_plot = pg.ImageItem()
        vb_full.addItem(self.spectrogram_plot)
        cm = pg.colormap.getFromMatplotlib("rainbow")
        lut = cm.getLookupTable(nPts=512)
        self.spectrogram_plot.setLookupTable(lut)


    def update_graphics(self, plot_num: int, data):
        """ Update single Slice and FROG trace plots in main window
        Arguments:
        plot_num -- 3: Slice plot
        plot_num -- 2: FROG plot
        """
        if plot_num==3:
            self.spectrum_plot.setData(data)
        if plot_num==2:
            # data = np.flipud(data)
            self.spectrogram_plot.setImage(data)


    def update_frog_axes(self, time_limits: list[float,float], wavelength_limits: list[float,float], time_bins: int, wavelength_bins: int):
        tr = QTransform()
        tr.translate(time_limits[0], wavelength_limits[0])
        tr.scale(np.diff(time_limits)/time_bins, np.diff(wavelength_limits)/wavelength_bins)
        self.spectrogram_plot.setTransform(tr)

class CommentDialog(QtWidgets.QDialog):
    """ For adding a comment when saving the measurement. """
    def __init__(self, parent):
        """ Setting up the window. """
        super().__init__(parent=parent)
        self.setWindowTitle('Add a comment (optional)')
        self.setFixedSize(300, 80)
        dialog_layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()
        self.comment = QtWidgets.QLineEdit()
        form_layout.addRow('Name:', self.comment)
        dialog_layout.addLayout(form_layout)

        standard_buttons = QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        self.button_box = QtWidgets.QDialogButtonBox(standard_buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        #self.buttons.setStandardButtons(self.buttons)
        dialog_layout.addWidget(self.button_box)
        self.setLayout(dialog_layout)


    def get_comment(self) -> str:
        """ Return the comment """
        return self.comment.text()
