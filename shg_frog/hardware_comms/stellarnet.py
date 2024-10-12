import stellarnet_driver3 as sn

'''
Class is deprecated. Re-implement using the interface in device_interfaces.py
'''


class Spectrometer:
    def __init__(self):
        self.spec, self.wl_nm = sn.array_get_spec(0)
        self.wl_nm = self.wl_nm.flatten()

        # carried over from emulator
        self.integration_time_micros_limits = [2e3, 65535e3]

    def print_info(self):
        self.spec['device'].print_info()

    def set_config_int_time(self, int_time_ms):
        self.spec['device'].set_config(int_time=int(int_time_ms))

    # carried over from emulator
    def wavelengths(self):
        return self.wl_nm

    # carried over from emulator
    def spectrum(self):
        return self.wl_nm, self.spec['device'].read_spectrum()

    # carried over from emulator
    def integration_time_micros(self, time_micros):
        self.set_config_int_time(int_time_ms=time_micros * 1e-3)
        print(self.spec['device'].get_config())

    def set_scans_to_average(self, N):
        self.spec['device'].set_config(scans_to_avg=int(N))
        print(self.spec['device'].get_config())
