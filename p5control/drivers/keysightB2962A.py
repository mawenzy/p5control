"""
Driver for KEYSIGHT B2962A Power Source
"""
from .basedriver import BaseDriver
from logging import getLogger

logger = getLogger(__name__)

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

    def setup_offset_measurement(self, max_current =.1):
        self._inst.write("*RST")
        self._inst.write(":sour1:func:mode volt")
        self._inst.write(":sour2:func:mode volt")

        self._inst.write(":sour1:volt 0")
        self._inst.write(":sour2:volt 0")

        self._inst.write(f":SENSe1:CURRent:DC:PROTection:LEVel:BOTH {max_current}")
        self._inst.write(f":SENSe2:CURRent:DC:PROTection:LEVel:BOTH {max_current}")

        self._inst.write(":outp on")

        error = self._inst.query(":SYSTem:ERRor:CODE:ALL?")
        if error!='+0':
            logger.error(f'{self._name}.setup_offset_measurement() ERROR: {error}')

        logger.debug(f'{self._name}.setup_offset_measurement()')

    def setup_sweep_measurement(self, 
                                amplitude = .25,
                                frequency = 1,
                                sweep_counts = 10, 
                                max_current = .1):

        _half_amplitude = amplitude / 2
        _half_frequency = frequency / 2

        self._inst.write("*RST")

        self._inst.write(f":sour1:func:mode volt")
        self._inst.write(f":sour2:func:mode volt")
        self._inst.write(f":sour1:volt {-_half_amplitude}")
        self._inst.write(f":sour2:volt {_half_amplitude}")
        self._inst.write(f":sour1:volt:mode arb")
        self._inst.write(f":sour2:volt:mode arb")
        self._inst.write(f":sour1:arb:func tri")
        self._inst.write(f":sour2:arb:func tri")
        self._inst.write(f":sour1:arb:volt:tri:star {-_half_amplitude}")
        self._inst.write(f":sour2:arb:volt:tri:star {_half_amplitude}")
        self._inst.write(f":sour1:arb:volt:tri:top {_half_amplitude}")
        self._inst.write(f":sour2:arb:volt:tri:top {-_half_amplitude}")
        self._inst.write(f":sour1:arb:volt:tri:star:time 0")
        self._inst.write(f":sour2:arb:volt:tri:star:time 0")
        self._inst.write(f":sour1:arb:volt:tri:rtim {_half_frequency}")
        self._inst.write(f":sour2:arb:volt:tri:rtim {_half_frequency}")
        self._inst.write(f":sour1:arb:volt:tri:ftim {_half_frequency}")
        self._inst.write(f":sour2:arb:volt:tri:ftim {_half_frequency}")
        self._inst.write(f":sour1:arb:volt:tri:end:time 0")
        self._inst.write(f":sour2:arb:volt:tri:end:time 0")
        
        self._inst.write(f":trig1:tran:coun {sweep_counts}")
        self._inst.write(f":trig2:tran:coun {sweep_counts}")
        self._inst.write(f":trig1:tran:sour aint")
        self._inst.write(f":trig2:tran:sour aint")
        
        self._inst.write(f":SENSe1:CURRent:DC:PROTection:LEVel:BOTH {max_current}")
        self._inst.write(f":SENSe2:CURRent:DC:PROTection:LEVel:BOTH {max_current}")

        self._inst.write(":outp on")
        
        error = self._inst.query(":SYSTem:ERRor:CODE:ALL?")
        if error!='+0':
            logger.error(f'{self._name}.setup_sweep_measurement() ERROR: {error}')

        logger.debug(f'{self._name}.setup_sweep_measurement()')

    def trigger_measurment(self, ch='BOTH'):
        if ch == 'BOTH':
            self._inst.write(f":INIT (@1, 2)")
        else: 
            self._inst.write(f":INIT {ch}")

    def get_error_message(self):
        return self._inst.query(":SYSTem:ERRor:CODE:ALL?")

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

    def timeout(self, timeout):
        self._inst.timeout = int(timeout)