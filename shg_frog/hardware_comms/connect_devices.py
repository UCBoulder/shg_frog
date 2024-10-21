from pylablib.devices.Thorlabs.kinesis import list_kinesis_devices
from seabreeze.spectrometers import Spectrometer as ooSpec

from .device_interfaces import LinearMotor, Spectrometer, DeviceCommsException
from .kinesis import ThorlabsKinesisMotor
from .ocean import OceanOpticsSpectrometer

'''
Create and initialize desired subclass of LinearMotor and Spectrometer

returns: tuple of the fully initialized motor and spectrometer devices 

raises: DeviceCommsException if there is a failure in the
connection/initialization of either device
'''


def connect_devices() -> tuple[LinearMotor, Spectrometer]:
    try:
        motor = ThorlabsKinesisMotor(list_kinesis_devices()[0][0])
    except:
        raise DeviceCommsException('Motor did not connect')

    try:
        spectrometer = OceanOpticsSpectrometer(ooSpec.from_first_available())
    except:
        raise DeviceCommsException('Spectrometer did not connect')

    spectrometer.scans_to_avg = 1
    motor.travel_limits = (0, 2e-2)

    return motor, spectrometer
