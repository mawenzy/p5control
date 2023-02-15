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
        self.timeout(10000)
        self.reset()

        self.triangle_mode()
        self.set_max_current(.1)
        self.set_frequency(2.003)
        self.set_amplitude(.33)
        self.set_sweep_count(5)

        self.output_on()

    def timeout(self, timeout):
        self._inst.timeout = int(timeout)

    def get_error_message(self):
        return self.query(":SYSTem:ERRor:CODE:ALL?")
        
    def check_for_error(self):
        error = self.get_error_message()
        if error!='+0':
            logger.error('"%s" ERROR: %s', self._name, error)

    def reset(self):
        with self.lock:
            self._inst.write("*CLS") # clear status command
            self._inst.write("*RST") # reset the instrument for SCPI operation
            self._inst.query("*OPC?") # wait for the operation to complete
            self.output = False
            self.max_current = 0
            self.frequency = 0
            self.amplitude = 0
            self.sweep_count = 0

    def _get_channel(self, ch=None):
        """
        Convenience function to convert ``ch`` argument to the desired format of a list of ints.
        Options include:
            -   **None** - default, both channels are addressed, returns ``[1,2]``
            -   **i** - with i being a integer returns ``[i]`` to specify which channel to use
            -   **other** - returns ch

        Parameters
        ----------
        ch : Optional
            specifies the channels
        """
        if ch is None:
            return [1,2]
        if type(ch) == int:
            return [ch]
        return ch

    def triangle_mode(self, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            with self.lock:
                self._inst.write(f":sour{c}:func:mode volt")
                self._inst.write(f":sour{c}:volt:mode arb")
                self._inst.write(f":sour{c}:arb:func tri")
                self._inst.write(f":sour{c}:arb:volt:tri:star:time 0")
                self._inst.write(f":sour{c}:arb:volt:tri:end:time 0")
                self._inst.write(f":trig{c}:tran:sour aint")
            
    def trigger(self, ch=None):
        if ch is None:
            self.write(f"INIT (@1,2)")
        else:
            self.write(f"INIT (@{ch})")

    def output_on(self, val=True, ch=None):
        ch = self._get_channel(ch)
        if val:
            outp = 'on'
        else:
            outp = 'off'
        for c in ch:
            self.write(f":outp{c} {outp}")
        self.output = val

    def output_off(self, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":outp{c} off")
        self.output = False

    def set_max_current(self, max_current, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":SENSe{c}:CURRent:DC:PROTection:LEVel:BOTH {max_current}")
        self._max_current = max_current

    def set_rise_time(self, t, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":sour{c}:arb:volt:tri:rtim {t}")

    def set_fall_time(self, t, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":sour{c}:arb:volt:tri:ftim {t}")

    def set_frequency(self, frequency):
        _half_time = .5/frequency
        self.set_rise_time(_half_time)
        self.set_fall_time(_half_time)
        self.frequency = frequency
        
    def set_voltage(self, V, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":sour{c}:volt {V}")
    
    def set_triangle_top(self, V, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":sour{c}:arb:volt:tri:top {V}")

    def set_triangle_btm(self, V, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":sour{c}:arb:volt:tri:star {V}")

    def set_amplitude(self, amplitude):
        _half_amplitude = amplitude / 2
        self.set_voltage(-_half_amplitude, ch=1)
        self.set_voltage(_half_amplitude, ch=2)

        self.set_triangle_btm(-_half_amplitude, ch=1)
        self.set_triangle_btm(_half_amplitude, ch=2)

        self.set_triangle_top(_half_amplitude, ch=1)
        self.set_triangle_top(-_half_amplitude, ch=2)
        self.amplitude = amplitude
    
    def set_sweep_count(self, N: int, ch=None):
        ch = self._get_channel(ch)
        for c in ch:
            self.write(f":trig{c}:tran:coun {N}")
        self.sweep_count = N

