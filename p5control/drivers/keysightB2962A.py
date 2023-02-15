"""
Driver for KEYSIGHT B2962A Power Source
"""
import logging

from .basedriver import ThreadSafeBaseDriver

logger = logging.getLogger(__name__)

class KeysightB2962A(ThreadSafeBaseDriver):
    """
    Driver for KEYSIGHT B2962A Power Source
    """

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

        self._setting = ""

    def timeout(self, timeout):
        self._inst.timeout = int(timeout)

    def get_error_message(self):
        return self.query(":SYSTem:ERRor:CODE:ALL?")

    def trigger_measurment(self, channel=None):
        if channel is None:
            self.write(f"INIT (@1,2)")
        else:
            self.write(f"INIT (@{channel})")

    def setup_offset_measurement(self, max_current =.1):
        if self._setting != "offset":
            with self.lock:
                self._inst.write("*RST")
                self._inst.write(":sour1:func:mode volt")
                self._inst.write(":sour2:func:mode volt")

                self._inst.write(":sour1:volt 0")
                self._inst.write(":sour2:volt 0")

                self._inst.write(f":SENSe1:CURRent:DC:PROTection:LEVel:BOTH {max_current}")
                self._inst.write(f":SENSe2:CURRent:DC:PROTection:LEVel:BOTH {max_current}")

                self._inst.write(":outp1 on")
                self._inst.write(":outp2 on")

            error = self._inst.query(":SYSTem:ERRor:CODE:ALL?")
            if error!='+0':
                logger.error('%s.setup_offset_measurement() ERROR: %s', self._name, error)

            self._setting = "offset"
            logger.debug('%s.setup_offset_measurement()', self._name)
        else:
            logger.debug('%s already setup for offset measurement.', self._name)

    def setup_sweep_measurement(
        self,
        amplitude = .25,
        frequency = 1,
        sweep_counts = 10,
        max_current = .1
    ):
        if self._setting != "sweep":
            _half_amplitude = amplitude / 2
            _half_time = .5/frequency
            with self.lock:
                self._inst.write("*RST")

                self._inst.write(":sour1:func:mode volt")
                self._inst.write(":sour2:func:mode volt")

                self._inst.write(f":sour1:volt {-1. * _half_amplitude}")
                self._inst.write(f":sour2:volt {_half_amplitude}")

                self._inst.write(f":SENSe1:CURRent:DC:PROTection:LEVel:BOTH {max_current}")
                self._inst.write(f":SENSe2:CURRent:DC:PROTection:LEVel:BOTH {max_current}")

                self._inst.write(":outp1 on")
                self._inst.write(":outp2 on")

                self._inst.write(":sour1:volt:mode arb")
                self._inst.write(":sour1:arb:func tri")
                self._inst.write(f":sour1:arb:volt:tri:star {-1. * _half_amplitude}")
                self._inst.write(f":sour1:arb:volt:tri:top {_half_amplitude}")
                self._inst.write(":sour1:arb:volt:tri:star:time 0")
                self._inst.write(":sour1:arb:volt:tri:end:time 0")
                self._inst.write(f":sour1:arb:volt:tri:rtim {_half_time}")
                self._inst.write(f":sour1:arb:volt:tri:ftim {_half_time}")

                self._inst.write(":sour2:volt:mode arb")
                self._inst.write(":sour2:arb:func tri")
                self._inst.write(f":sour2:arb:volt:tri:star {_half_amplitude}")
                self._inst.write(f":sour2:arb:volt:tri:top {-1. * _half_amplitude}")
                self._inst.write(":sour2:arb:volt:tri:star:time 0")
                self._inst.write(":sour2:arb:volt:tri:end:time 0")
                self._inst.write(f":sour2:arb:volt:tri:rtim {_half_time}")
                self._inst.write(f":sour2:arb:volt:tri:ftim {_half_time}")

                self._inst.write(f":trig1:tran:coun {sweep_counts}")
                self._inst.write(f":trig2:tran:coun {sweep_counts}")
                self._inst.write(":trig1:tran:sour aint")
                self._inst.write(":trig2:tran:sour aint")

            error = self._inst.query(":SYSTem:ERRor:CODE:ALL?")
            if error!='+0':
                logger.error(f'{self._name}.setup_sweep_measurement() ERROR: {error}')
            
            self._setting = "sweep"
            logger.debug(f'{self._name}.setup_sweep_measurement()')
        else:
            logger.debug(f'{self._name} already setup for sweep measurement.')
 
    def setup_sinus_measurement(self, channel=None, freq=0.1, ampl=1):
        if self._setting != "sinus":
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
            
            self._setting = "sinus"
            logger.debug('%s.setup_sweep_measurement()', self._name)
        else:
            logger.debug('%s already setup for sinus measurement.', self._name)
