"""
Driver for KEYSIGHT B2962A Power Source
"""
from .basedriver import BaseDriver

class KeysightB2962A(BaseDriver):

    def open(self):
        super().open()

        # setup termination
        self._inst.write_termination = "\n"
        self._inst.read_termination = "\n"

        # copied from olli driver
        self._inst.timeout = 10000
        self._inst.write("*CLS") # clear status command
        self._inst.write("*RST") # reset the instrument for SCPI operation
        self._inst.query("*OPC?") # wait for the operation to complete

    """
    Additional custom functionality
    """
    def setup_voltage_sinus_mode(self, channel=None, freq=0.1, ampl=1):
        self._inst.write("*RST")

        if channel is None:
            channel = [1, 2]
        for ch in channel:
            self._inst.write(f":SOURce{ch}:FUNC:MODE VOLT")
            self._inst.write(f":SOURce{ch}:VOLT:MODE ARB")
            self._inst.write(f":SOURce{ch}:ARB:FUNC SIN")
            self._inst.write(f":SOURce{ch}:ARB:VOLT:SIN:AMPL {ampl}")
            self._inst.write(f":SOURce{ch}:ARB:VOLT:SIN:FREQ {freq}")

            self._inst.write(f":TRIGger{ch}:TRAN:SOURce AINT")
            self._inst.write(f":TRIGger{ch}:TRAN:COUNt INF")
            self._inst.write(f":ARM{ch}:TRAN:COUNt INF")
        self._inst.query("*OPC?")

    def initialize(self, channel=None):
        if channel is None:
            self._inst.write(f"INIT (@1,2)")
        else:
            self._inst.write(f"INIT (@{channel})")

    def query(self, query):
        return self._inst.query(query)
    def write(self, write):
        self._inst.write(write)
    def read(self):
        return self._inst.read()