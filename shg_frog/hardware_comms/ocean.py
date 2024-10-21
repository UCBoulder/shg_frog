from .device_interfaces import Spectrometer, SpectrometerIntegrationException, SpectrometerAverageException
from seabreeze.spectrometers import Spectrometer as ooSpec
import seabreeze
import numpy as np
seabreeze.use('cseabreeze')


class OceanOpticsSpectrometer(Spectrometer):
    def __init__(self, spectrometer: ooSpec):
        self.spectrometer = spectrometer

    def intensities(self):
        return self.spectrometer.intensities()

    def wavelengths(self):
        return self.spectrometer.wavelengths() * 1e-9

    def spectrum(self):
        spectrum = self.spectrometer.spectrum()
        spectrum[0,:] = spectrum[0,:] *1e-9
        return spectrum

    @property
    def integration_time(self):
        if self._integration_time is None:
            raise SpectrometerIntegrationException('''Spectrometer integration time 
                                                   not initialized''')
        return self._integration_time

    @integration_time.setter
    def integration_time(self, value):
        if not (self.integration_time_limits[0] <= value <= self.integration_time_limits[1]):
            raise SpectrometerIntegrationException(
                '''Integration time exceeds limits''')
        else:
            self._integration_time = value
            self.spectrometer.integration_time_micros(value * 1e6)

    @property
    def scans_to_avg(self):
        return self._scans_to_avg

    @scans_to_avg.setter
    def scans_to_avg(self, N: int):
        '''
        Currently non-functional with the USB2000 and cseabreeze backend
        '''
        if N <= 0:
            raise SpectrometerAverageException(
                "Spectrometer must average at least 1 scan")
        else:
            pass
            #self._scans_to_avg = N
            #self.spectrometer.f.spectrum_processing.set_scans_to_average(N)

    @property
    def integration_time_limits(self):
        us = self.spectrometer.integration_time_micros_limits 
        s = np.array(us[:2])*1e-6
        return s

    @property
    def idn(self):
        return self.spectrometer.serial_number

    def close(self):
        self.spectrometer.close()