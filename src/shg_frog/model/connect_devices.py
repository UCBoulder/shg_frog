from hardware_comms.devices import DeviceCommsException
from hardware_comms.linear_motors.kinesis import ThorlabsKinesisMotor
from hardware_comms.spectrometers.ocean import OceanOpticsSpectrometer
from hardware_comms.linear_motors.linear_motor import LinearMotor
from hardware_comms.spectrometers.spectrometer import Spectrometer

'''
Create and initialize desired subclass of LinearMotor and Spectrometer

returns: tuple of the fully initialized motor and spectrometer devices 

raises: DeviceCommsException if there is a failure in the
connection/initialization of either device
'''


def connect_devices() -> tuple[LinearMotor, Spectrometer]:
    # try:
    motor = ThorlabsKinesisMotor()
    # except:
        # raise DeviceCommsException('Motor did not connect')

    try:
        spectrometer = OceanOpticsSpectrometer()
    except:
        raise DeviceCommsException('Spectrometer did not connect')

    spectrometer.scans_to_avg = 1
    motor.travel_limits = (0, 2e-2)

    return motor, spectrometer
