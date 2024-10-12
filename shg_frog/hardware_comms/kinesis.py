from pylablib.devices.Thorlabs import KinesisMotor
from pylablib.devices.Thorlabs.base import ThorlabsError

from .device_interfaces import LinearMotor, StageOutOfBoundsException, StageNotCalibratedException
'''
Class for all Thorlabs linear motors which 
use the Kinesis software stack
'''


class ThorlabsKinesisMotor(LinearMotor):
    '''
    Instantiate by the serial number of the control module
    '''

    def __init__(self, serial_no: int):
        # auto-detect stage step -> distance calibration
        self.motor = KinesisMotor(serial_no, scale="stage")
        if self.motor.get_scale_units() != 'm':
            raise StageNotCalibratedException(
                "No step to distance calibration found. Input this manually.")

    def pos_um(self):
        # default units are (m)
        try:
            self._pos_um = 1e6 * self.motor.get_position()
        except ThorlabsError:
            pass
        return self._pos_um

    def is_in_motion(self) -> bool:
        try:
            return self.motor.is_moving()
        except ThorlabsError:
            return True

    def move_abs(self, loc: float):
        if not (self.travel_limits[0] <= loc <= self.travel_limits[1]):
            raise StageOutOfBoundsException(
                "Location would exceed software limits")
        else:
            # default units are (m)
            try:
                self.motor.move_to(loc, scale=True)
            except ThorlabsError:
                pass

    def move_by_um(self, dist_um):
        dist_m = dist_um * 1e-6

        # move the motor to the new position and update the position in micron
        if not (self.travel_limits_um[0] <= (dist_um + self.pos_um()) <= self.travel_limits_um[1]):
            raise StageOutOfBoundsException(
                "Location would exceed software limits")
        else:
            try:
                self.motor.move_by(distance=dist_m)
            except ThorlabsError:
                pass

    def stop(self, blocking=True) -> None:
        try:
            self.motor.stop(sync=blocking)
        except ThorlabsError:
            pass

    def home(self, blocking=False) -> None:
        try:
            self.motor.home(sync=blocking)
        except ThorlabsError:
            pass

    def close(self) -> None:
        self.motor.close()
