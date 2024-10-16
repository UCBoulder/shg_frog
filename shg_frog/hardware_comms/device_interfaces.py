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

        returns: (lower bound, upper bound), in microns
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
        
        limits: listlike containing (lower bound, upper bound), in microns
        '''
        self._travel_limits = limits[:2]

    @property
    def T0_um(self) -> float:
        '''
        Location of the stage corresponding to time zero 
        (i.e. the center of the FROG trace). Calls self._read_T0_from_file()
        and self._write_T0_to_file() to save T0 to persistent storage between
        program executions.

        returns: float of stage displacement at time zero, in microns
        '''
        try:
            return self._T0_um
        except AttributeError:
            try:
                self._read_T0_from_file()
            except FileNotFoundError:
                self._T0_um = self.position()
                self._write_T0_to_file()
            return self._T0_um

    @T0_um.setter
    def T0_um(self, dist_um: float):
        '''
        Sets the stage location corresponding to time zero.
        
        dist_um: stage location in microns
        '''
        self._T0_um = dist_um
        self._write_T0_to_file()

    @property
    @abstractmethod
    def position(self) -> float:
        '''
        Get stage position in microns

        returns: location of the stage, in microns
        '''
        pass


    def pos_fs(self) -> float:
        '''
        Get stage location in femtoseconds, with respect to time zero.

        returns: float of the stage location, in femtoseconds
        '''
        return dist_um_to_T_fs(self.position - self.T0_um)


    @abstractmethod
    def move_by(self, value: float) -> None:
        '''
        Move the relative position of the stage (micron units).

        value_um: distance of relative move (positive or negative), in microns
        raises: StageOutOfBoundException if the move would exceed
        the software limits of the stage.
        '''
        pass


    def move_by_fs(self, value_fs: float) -> None:
        '''
        Move the relative position of the stage (femtosecond units)
        
        value_fs: distance of the relative move (positive or negative), in
        femtoseconds
        raises: StageOutOfBoundException if the move would exceed
        the software limits of the stage.
        '''
        self.move_by(T_fs_to_dist_um(value_fs))

    @abstractmethod
    def move_abs(self, value: float) -> None:
        '''
        Move to an absolute location (micron units).

        value_um: desired stage location, in microns
        raises: StageOutOfBoundException if the move would exceed
        the software limits of the stage.
        '''
        pass


    def move_to_um(self, value_fs: float) -> None:
        '''
        Move to an absolute location (femtosecond units).

        value_fs: desired stage location, in femtoseconds
        raises: StageOutOfBoundException if the move would exceed
        the software limits of the stage.
        '''
        self.move_to_um(T_fs_to_dist_um(value_fs))

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

    @property
    def datapath(self) -> Path:
        '''
        Location on the filesystem for persistent storage of configuration information
        
        returns: pathlib Path to the directory for persistent storage
        '''
        return user_data_path(appname='frogware', appauthor='FCxQM')


    def _read_T0_from_file(self) -> None:
        '''
        Saves T0 to T0_um.txt in the directory defined by self.datapath
        '''
        with open(self.datapath / "T0.txt", "r") as file:
            self._T0_um = float(file.readline())


    def _write_T0_to_file(self) -> None:
        '''
        Reads T0 from T0_um.txt in the directory defined by self.datapath
        '''
        with open(self.datapath / "T0_um.txt", "w") as file:
            file.write(f'{self._T0_um}')




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
    def integration_time_micros(self) -> int:
        '''
        Reads the integration time in microseconds.
        
        return: hardware integration time, in microseconds
        '''
        pass

    @integration_time_micros.setter
    @abstractmethod
    def integration_time_micros(self, value) -> None:
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
    def integration_time_micros_limit(self) -> tuple[int, int]:
        '''
        Returns the integration time in microseconds.

        return: listlike of (lower bound, upper bound) in microseconds
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
