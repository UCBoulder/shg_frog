"""
Model for the FROG setup

File name: frog.py
Author: Julian Krauth
Date created: 2019/12/02
Python Version: 3.7
"""
import pathlib
from datetime import datetime
import numpy as np
from hardware_comms.linear_motors.linear_motor import LinearMotor
from hardware_comms.spectrometers.spectrometer import Spectrometer
from pyqtgraph.parametertree import Parameter
from . import acquisition
from .connect_devices import connect_devices
from . import phase_retrieval
from ..helpers.file_handler import FileHandler
from ..helpers.data_types import Data

C_MKS = 299792458. #m/



class FROG:
    """Top level class for the FROG experiment definition."""

    def __init__(self, test: bool=True):
        """
        Arguments:
        test -- whether to run with dummy devices for testing or not.
        """
        self.files = FileHandler()
        self._config = self.files.get_main_config()
        # stage_port = self._config['stage port']
        # camera_id = self._config['camera id']
        # spectrometer_id = self._config['spectrometer id']
        # Load the FROG devices (optional: virtual devices for testing)
        if test:
            # Instantiate dummies
            # self.stage = newport.SMC100Dummy(port=stage_port, dev_number=1)
            # self.camera = acquisition.CameraDummy(camera_id)
            # self.stage, self.spectrometer = connect_devices()
            pass
        else:
            # self.stage, self.spectrometer = connect_devices()
            pass

        # Will contain the measurement data and settings
        self._data = None
        self.stop_measure = False
        self.background = 0

        self.algo = phase_retrieval.PhaseRetrieval(prep_size=64)
        self.parameters = FrogParams(self._config['pxls width'], self._config['pxls height'])
    def initialize(self) -> None:
        """Connect to the devices."""
        # self.stage.initialize()
        # self.camera.initialize()
        self.stage, self.spectrometer = connect_devices()
        print("Devices connected!")

    def close(self):
        """Close connection with devices."""
        self.stage.close()
        self.spectrometer.close()
        # self.camera.close()
        print("Devices disconnected!")
    
    def measure_background(self):
        self.background = self.spectrometer.intensities()
        

    def measure_spectrum(self, sig_measure):
        '''Carries out the continuous spectrum collection'''
        self.stop_spectrum_measure = False
        while not self.stop_spectrum_measure:
            if self.stop_spectrum_measure:
                return
            spectrum = self.spectrometer.spectrum()
            spectrum[1,:] = spectrum[1,:] -self.background
            sig_measure.emit(3, spectrum.transpose())

    
    def measure_slow(self, sig_progress, sig_measure):
        self.measure(sig_progress, sig_measure, method='slow')

    # TODO implement a faster process (desync spectrum w/ stage)
    def measure_fast(self, sig_progress, sig_measure):
        self.measure(sig_progress, sig_measure, method='fast')

    def measure(self, sig_progress, sig_measure, method='slow'):
        """Carries out the frog measurement loop."""
        self.stop_measure = False
        # Get measurement settings
        meta = self._get_settings()
        # Delete possible previous measurement data.
        self._data = None
        # Move stage to Start Position and wait for end of movement
        self.stage.move_abs(meta['start position'] + meta['center position'])
        wavelengths = self.spectrometer.wavelengths()
        # find the extent of the span
        wlrange = np.where((wavelengths >= self.center -self.span/2) & (wavelengths<= self.center + self.span/2))
        wavelengths = wavelengths[wlrange]
        self.stage.wait_move_finish(.05)
        for i in range(meta['step number']):
            print(f"Loop {i}...")
            # Move stage
            if method=="slow":
                self.stage.move_abs(meta['start position'] + meta['center position'] + i * meta['step size'])
                self.stage.wait_move_finish(.05)
            elif method=="fast":
                self.stage.move_by(meta['step size'])
                self.stage.wait_move_finish(.01)

            # Record spectrum
            spectrum = self.spectrometer.spectrum()
            spectrum[1,:] = spectrum[1,:] -self.background
            intensities = spectrum[1, wlrange]
            # Create 2d frog-array to fill with data
            if i==0:
                frog_array = np.zeros((len(intensities[0]), meta['step number']))
            # Stitch data together
            frog_array[:,i] = intensities
            # Send data to plot
            sig_measure.emit(3, spectrum.transpose())
            sig_measure.emit(2, frog_array)
            sig_progress.emit(i+1)
            print(self.stage.position)
            if self.stop_measure:
                print("Measurement aborted, data discarded!")
                return
        # Save Frog trace and measurement settings as instance attributes,
        # they are then available for save button of GUI.
        if self._config['spectral device'] == 'Camera':
            frog_trace = self.scale_pxl_values(frog_array)
        elif self._config['spectral device'] == 'Spectrometer':
            frog_trace = self.scale_wl_to_freq(wavelengths, frog_array)
        # maybe add possibility to add a comment to the meta data at
        # end of measurement.
        self._data = Data(frog_trace, meta)
        print("Measurement finished!")

    def scale_wl_to_freq(self, wavelengths: np.ndarray, frog_array: np.ndarray):
        '''scales the trace with the lambda^2 Jacobian to correct intensities
        for converting from wavelength to a frequency axis'''
        frog_array_copy = np.copy(frog_array)
        for i in range(frog_array_copy.shape[1]):
            wl_x = wavelengths
            old_y = frog_array_copy[:, i]
            f_x_lin = np.flip(np.linspace(C_MKS/np.min(wl_x), C_MKS/np.max(wl_x), len(wl_x)))
            f_x_hyp = np.flip(C_MKS/wl_x)
            old_y_flipped = np.flip(old_y)
            new_y = np.interp(f_x_lin, f_x_hyp, old_y_flipped)
            new_y = new_y / np.power(f_x_lin, 2)
            frog_array_copy[:,i] = new_y 
        return np.fliplr(frog_array_copy)
        
    

    def _get_settings(self) -> dict:
        """Returns the settings for the current measurement as dictionary.
        Everything listed here will be saved in the metadata .yml file."""
        date = datetime.now().strftime('%Y-%m-%d')
        time = datetime.now().strftime('%H:%M:%S')
        step_size = self.parameters.get_step_size()
        # Time step per pixel in s
        ccddt = 2*step_size/(C_MKS)
        # in future maybe write also exposure time, gain, max Intensity, bit depth
        settings = {
            'date': date,
            'time': time,
            'center position': self.parameters.get_center_position(),
            'start position': self.parameters.get_start_position(),
            'step number': self.parameters.get_step_num(),
            'step size': step_size,
            'ccddt': ccddt,
            'comment': '', # is added afterwards
        }
        if self._config['spectral device'] == 'Camera':
            ccddv = self.freq_step_per_pixel()
            settings.update({
                'camera': self.camera.idn,
                'bit depth': self.camera.pix_format,
                'ccddv': ccddv,
            })
        elif self._config['spectral device'] == 'Spectrometer':
            ccddv = self.freq_bin_size()
            settings.update({
                'spectrometer': self.spectrometer.idn,
                'ccddv': ccddv,
                'span': self.span,
                'center': self.center 
            })
            
        return settings

    def set_span(self, value):
        '''Slot for updating spectrometer span'''
        self.span = value

    def set_center(self, value):
        '''Slot for updating spectrometer center wl'''
        self.center = value

    def set_integration_time(self, value):
        self.spectrometer.integration_time = value
    
    def scale_pxl_values(self, frog_array: np.ndarray) -> np.ndarray:
        """Scale Mono12 image to 16bit, else don't do anything."""
        # Scale image according to bit depth
        if self.camera.pix_format == 'Mono12':
            factor = 2**4 # to scale from 12 bit to 16 bit
            frog_array *= factor
        return np.rint(frog_array).astype(int)

    def freq_step_per_pixel(self) -> float:
        """Returns the frequency step per bin/pixel of the taken trace.
        Needed for phase retrieval.
        Returns:
        float -- in THz
        """
        wl_at_center = self._config['center wavelength']
        # Wavelength step per pixel:
        # I assume that over the size of the CCD chip
        # (for small angles) the wavelength scale is linear
        # The number is calculated using the wavelength spread per mrad
        # specified for the grating.
        # This is then divided by the number of pixels which fit
        # into a 1mrad range at the focal distance of the lens:
        # Grating spec: 0.81nm/mrad => 0.81nm/0.2mm (for a 200mm focal lens)
        # =>0.81nm/34.13pixels (for 5.86micron pixelsize)
        mm_per_mrad = 1. * self._config['focal length'] / 1000.
        pxls_per_mrad = mm_per_mrad/(self._config['pixel size'] \
            /1000) # yields 34
        nm_per_px = self._config['grating']/pxls_per_mrad # yields 0.0237nm
        # Frequency step per pixel
        freq_per_px_GHz = C_MKS * (1/(wl_at_center) \
            -1/(wl_at_center + nm_per_px)) # GHz
        freq_per_px = freq_per_px_GHz * 1.e-3 # THz
        # Also here I assume that for small angles the frequency can be
        # considered to be linear on the CCD plane.
        return freq_per_px
    
    def freq_bin_size(self) -> float:
        '''Gives the size of the spectrometer's frequency bins in Hz.
        Assumes that the FROG trace will be interpolated onto a 
        linear frequency grid.'''
        wavelengths = self.spectrometer.wavelengths()
        return float(C_MKS * (1/np.min(wavelengths) - 1/np.max(wavelengths))/(len(wavelengths)-1))

    def retrieve_phase(self, sig_retdata, sig_retlabels, sig_rettitles, sig_retaxis):
        """Execute phase retrieval algorithm."""
        if self.data_available:
            # Get data
            ccddt = self._data.meta['ccddt']
            ccddv = self._data.meta['ccddv']
            data = self._data.image
            # prepare FROG image
            self.algo.prepFROG(ccddt=ccddt, ccddv=ccddv, \
                ccdimg=data, flip=0)
            # Retrieve phase, algorithm is chosen in GUI
            if self.parameters.get_algorithm_type() == 'GP':
                self.algo.retrievePhase(
                    signal_data=sig_retdata, signal_label=sig_retlabels, \
                    signal_title=sig_rettitles, signal_axis=sig_retaxis)
            else:
                self.algo.ePIE_fun_FROG(
                    signal_data=sig_retdata, signal_label=sig_retlabels, \
                    signal_title=sig_rettitles, signal_axis=sig_retaxis)
        else:
            raise Exception('No recorded trace in buffer!')

    def save_measurement_data(self, comment: str):
        """ Saves Frog image, meta data, and the config file """
        if self._data is None:
            print('No data saved, do a measurement first!')
            return
        self._data.meta['comment'] = comment
        self.files.save_new_measurement(self._data, self._config)
        print('All data saved!')

    def load_measurement_data(self, path: pathlib.Path) -> np.ndarray:
        """ Load data of an old measurement and save them in self._data.
        Returns:
        np.ndarray -- the FROG image."""
        self._data = self.files.get_measurement_data(path)
        return self._data.image

    @property
    def data_available(self) -> bool:
        """ Check if measurement data are in memory. """
        if self._data is None:
            return False
        return True




class FrogParams:
    """
    Class which implements the parameters used by the parametertree widget.
    """

    def __init__(self, sensor_width: int, sensor_height: int):
        """
        The two arguments are needed to set the limits of the ROI
        parameters correctly.
        Arguments:
        sensor_width -- pixels along horizontal
        sensor_height -- pixels along vertical
        """
        # Define parameters for parametertree
        self._sensor_width = sensor_width
        self._sensor_height = sensor_height

        # Create parameter objects
        self.par = Parameter.create(
            name='params',
            type='group',
            children=FileHandler().load_parameters(),
            )


        ### Some settings regarding camera parameters ###
        # Create limits for crop settings
        crop_par = self.par.param('Camera').child('Crop Image')
        width_par = crop_par.child('Width')
        height_par = crop_par.child('Height')
        xpos_par = crop_par.child('Xpos')
        ypos_par = crop_par.child('Ypos')
        width_par.setLimits([1, self._sensor_width-xpos_par.value()])
        height_par.setLimits([1, self._sensor_height-ypos_par.value()])
        xpos_par.setLimits([0, self._sensor_width-width_par.value()])
        ypos_par.setLimits([0, self._sensor_height-height_par.value()])
        crop_par.sigTreeStateChanged.connect(self.set_crop_limits)

        ''' Settings for Spectrometers '''

        spec_par = self.par.param('Spectrometer')
        int_time_par = spec_par.child('Integration Time')
        avgs_par = spec_par.child('Averages')

        ### Some settings regarding the Stage parameters ###
        stage_par = self.par.param('Stage')
        start_par = stage_par.child('Start Position')
        step_par = stage_par.child('Step Size')
        off_par = stage_par.child('Offset')

        # Set limits of Start Position, depending on offset
        start_par.setLimits([-off_par.value(),-0.2])
        off_par.sigValueChanged.connect(self.set_start_pos_limits)

        # Set limits of Step Size, depending on Start Position
        step_par.setLimits([0.2,abs(start_par.value())])
        start_par.sigValueChanged.connect(self.set_step_limits)

        # Always update number of steps, given by start pos and step size
        start_par.sigValueChanged.connect(self.show_steps)
        step_par.sigValueChanged.connect(self.show_steps)

    def save_state(self):
        """ Save current parameter tree settings into a file. """
        FileHandler().save_settings(self.par.saveState())

    def restore_state(self):
        """ Load previously save parameter tree settings from file. """
        settings = FileHandler().load_last_settings()
        if settings is not None:
            self.par.restoreState(settings)

    def set_crop_limits(self, param, changes):
        max_width, max_height = self.get_sensor_size()
        for param, change, data in changes:
            path = self.par.childPath(param)
            par = self.par.param(path[0]).child(path[1])
            if path[2]=='Width':
                par.child('Xpos').setLimits([0, max_width-par.child(path[2]).value()])
            elif path[2]=='Height':
                par.child('Ypos').setLimits([0, max_height-par.child(path[2]).value()])
            elif path[2]=='Xpos':
                par.child('Width').setLimits([1, max_width-par.child(path[2]).value()])
            elif path[2]=='Ypos':
                par.child('Height').setLimits([1, max_height-par.child(path[2]).value()])

    def get_crop_par(self):
        """ Get the crop parameters from parameter tree"""
        roi_par = self.par.param('Camera').child('Crop Image')
        xpos = roi_par.child('Xpos').value()
        ypos = roi_par.child('Ypos').value()
        width = roi_par.child('Width').value()
        height = roi_par.child('Height').value()
        return xpos, ypos, width, height

    def update_crop_param(self, roi):
        """Used as action when changing roi in roi window"""
        pos = roi.pos()
        size = roi.size()
        # Update the CROP parameters regarding region of interest
        roi_par = self.par.param('Camera').child('Crop Image')
        # Create even numbers. Odd numbers crash with some cameras
        # and make sure that offset and size stays in allowed range
        max_size = self.get_sensor_size()
        for i in range(2):
            if pos[i] < 0:
                pos[i] = 0
            if size[i] > max_size[i]:
                size[i] = max_size[i]
                pos[i] = 0
            if size[i]+pos[i] > max_size[i]:
                size[i] = max_size[i] - pos[i]
            pos[i] = round(pos[i]/2.)*2
            size[i] = round(size[i]/2.)*2
        roi_par.child('Xpos').setValue(int(pos[0]))
        roi_par.child('Ypos').setValue(int(pos[1]))
        roi_par.child('Width').setValue(int(size[0]))
        roi_par.child('Height').setValue(int(size[1]))

    def set_step_limits(self, param, val):
        step_par = self.par.param('Stage').child('Step Size')
        step_par.setLimits([0.2,abs(val)])

    def set_start_pos_limits(self, param, val):
        start_pos = self.par.param('Stage').child('Start Position')
        start_pos.setLimits([-val,-0.2])

    def show_pos(self, val):
        pos = self.par.param('Stage').child('Position')
        pos.setValue(val)

    def show_steps(self, dummy):
        start_pos = self.par.param('Stage').child('Start Position')
        step_size = self.par.param('Stage').child('Step Size')
        val = int(round(2*abs(start_pos.value())/step_size.value()))

        num = self.par.param('Stage').child('Number of steps')
        num.setValue(val)

    def print_par_changes(self, val: bool=True):
        if val:
            # Do print changes in parametertree
            self.par.sigTreeStateChanged.connect(self._change)
        else:
            self.par.sigTreeStateChanged.disconnect(self._change)

    def _change(self, param, changes):
        ## If anything changes in the parametertree, print a message
        for param, change, data in changes:
            path = self.par.childPath(param)
            if path is not None:
                child_name = '.'.join(path)
            else:
                child_name = param.name()
            print("tree changes:")
            print('  parameter: %s'% child_name)
            print('  change:    %s'% change)
            print('  data:      %s'% str(data))
            print('  ----------')

    def get_algorithm_type(self) -> str:
        return self.par.param('Phase Retrieval').child('Algorithm').value()

    def get_sensor_size(self) -> list:
        return self._sensor_width, self._sensor_height

    def get_start_position(self) -> float:
        return self.par.param('Stage').child('Start Position').value() * 1e-6

    def get_step_num(self) -> int:
        return self.par.param('Stage').child('Number of steps').value()

    def get_step_size(self) -> float:
        return self.par.param('Stage').child('Step Size').value() * 1e-6

    def get_center_position(self) -> float:
        return self.par.param('Stage').child('Offset').value() * 1e-6
