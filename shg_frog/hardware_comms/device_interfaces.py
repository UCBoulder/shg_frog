from abc import ABC, abstractmethod
import numpy as np
from platformdirs import user_data_path
from pathlib import Path
from time import sleep

from .utilities import T_fs_to_dist_um, dist_um_to_T_fs



class LinearMotor(ABC):
    '''
    Abstract class for linear motors. Implement this with a subclass for
    new motor devices.
    '''
    @property
    def travel_limits(self) -> tuple[float]:
        '''
        Software limits for the stage

        returns: (lower bound, upper bound), in meters 
        raises: StageLimitsNotSetException if limits are not
        set
        '''
        try:
            return self._travel_limits
        except AttributeError:
            raise StageLimitsNotSetException(
                "Motor software limits not initialized")


    @travel_limits.setter
    def travel_limits(self, limits: tuple[float]) -> None:
        '''
        Sets software limits of the stage. Should be initialized in 
        .connect_devices.connect_devices() or the constructor for the
        subclass.
        
        limits: listlike containing (lower bound, upper bound), in meters 
        '''
        self._travel_limits = limits[:2]

    @property
    @abstractmethod
    def position(self) -> float:
        '''
        Get stage position in microns

        returns: location of the stage, in microns
        '''
        pass

    @abstractmethod
    def move_by(self, value: float) -> None:
        '''
        Move the relative position of the stage (micron units).

        value_um: distance of relative move (positive or negative), in meters
        raises: StageOutOfBoundException if the move would exceed
        the software limits of the stage.
        '''
        pass


    @abstractmethod
    def move_abs(self, value: float) -> None:
        '''
        Move to an absolute location (micron units).

        value: desired stage location, in meters
        raises: StageOutOfBoundException if the move would exceed
        the software limits of the stage.
        '''
        pass


    @abstractmethod
    def home(self, blocking=False) -> None:
        '''
        Home the stage. 

        blocking: True if program should pause until the stage is homed.
        False otherwise.
        '''
        pass

    @abstractmethod
    def is_in_motion(self) -> bool:
        '''
        Checks if the stage is in motion.
        
        returns: True if stage is in motion. False otherwise.
        '''
        pass

    def wait_move_finish(self, interval):
        '''override this if there is a built-in method'''
        while self.is_in_motion():
            sleep(interval)

    @abstractmethod
    def stop(self, blocking=True) -> None:
        '''
        Stops the stage, interrupting any current operations.

        blocking: True if program should pause until the stage is homed.
        False otherwise.
        '''
        pass

    @abstractmethod
    def close(self) -> None:
        '''
        Closes the backend to avoid hanging processes.
        '''
        pass


class Spectrometer(ABC):

    '''
    Abstract class for spectrometers
    '''
    @abstractmethod
    def intensities(self) -> np.ndarray[np.float64]:
        '''
        The intensities read by each pixel in the spectrometer (in arbitrary units).

        returns: NDArray of floats corresponding to the intensity in arbitrary units
        '''
        pass

    @abstractmethod
    def wavelengths(self) -> np.ndarray[np.float64]:
        '''
        Returns the wavelength bins (in meters).
        
        returns: NDArray of floats enumerating the wavelength bins in meters
        '''
        pass

    @abstractmethod
    def spectrum(self) -> np.ndarray[np.float64]:
        '''
        Returns a 2-D list of the wavelengths (0) and intensities (1)

        returns: 2DArray where,
                [0] = wavelengths
                [1] = intensities
        '''
        pass
    @property
    @abstractmethod
    def idn(self) -> int:
        pass

    @property
    @abstractmethod
    def integration_time(self) -> int:
        '''
        Reads the integration time in seconds.
        
        return: hardware integration time, in seconds
        '''
        pass

    @integration_time.setter
    @abstractmethod
    def integration_time(self, value) -> None:
        '''
        Sets the integration time in microseconds
        
        value: integration time, in microseconds
        '''
        pass

    @property
    @abstractmethod
    def scans_to_avg(self) -> int:
        '''
        Reads the number of scans averaged together in each
        spectrum.
        
        returns: number of averages per spectrum
        '''
        pass

    @scans_to_avg.setter
    @abstractmethod
    def scans_to_avg(self, N) -> None:
        '''
        Sets the number of scans averaged together in each spectrum.

        N: number of averages per spectrum
        '''
        pass

    @property
    @abstractmethod
    def integration_time_limits(self) -> tuple[int, int]:
        '''
        Returns the integration time in seconds.

        return: listlike of (lower bound, upper bound) in seconds
        '''
        pass

    @integration_time_limits.setter
    @abstractmethod
    def integration_time_limits(self) -> tuple[int, int]:
        '''
        Returns the integration time in seconds.

        return: listlike of (lower bound, upper bound) in seconds
        '''
        pass

    @abstractmethod
    def close(self) -> None:
        '''
        Closes the backend to avoid hanging processes.
        '''
        pass


class StageOutOfBoundsException(Exception):
    def __init__(self, message):
        self.message = message


class StageLimitsNotSetException(Exception):
    def __init__(self, message):
        self.message = message


class StageNotCalibratedException(Exception):
    def __init__(self, message):
        self.message = message


class SpectrometerIntegrationException(Exception):
    def __init__(self, message):
        self.message = message


class SpectrometerAverageException(Exception):
    def __init__(self, message):
        self.message = message


class DeviceCommsException(Exception):
    def __init__(self, message):
        self.message = message
