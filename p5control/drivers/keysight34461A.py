"""
Driver for KEYSIGHT 34461A Digit Multimeter
"""
import time

import numpy as np

from .basedriver import BaseDriver

class Keysight34461A(BaseDriver):
    """Driver for the Keysight34461A. Since it is MessageBased, we can use much
    of the BaseDriver class
    """

    def open(self):
        """Open connection to the device.
        
        Overwritten to add the termination characters."""
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
    Measuring setup
    """

    def setup_measuring(self):
        self._inst.write("*CLS") # clear status command
        self._inst.write("*RST") # reset the instrument for SCPI operation
        self._inst.query("*OPC?")  # wait for the operation to complete

        # copied from messprogramm
        self._inst.write('VOLT:DC:NPLC 0.02')
        self._inst.write('VOLT:DC:RANG:AUTO ON')
        self._inst.write(':SENS:VOLT:DC:ZERO:AUTO OFF')
        self._inst.write('TRIG:SOUR IMM') 
        self._inst.write("TRIG:COUN 10")
        self._inst.write("SAMP:COUN MAX")

    def start_measuring(self):
        self._inst.write("INIT")
        self.last_time = time.time()

    def get_data(self):
        data = self._inst.query("R?")
        # see page 205 in programmer manual
        data = np.fromstring(data[2+int(data[1]):], sep=",", dtype='f')
        # create time stamps
        now = time.time()
        times = np.linspace(self.last_time, now, len(data), endpoint=False)

        # set time for next cycle
        self.last_time = now

        # format data to shape (length, 2)
        return np.concatenate((
            np.reshape(times, (len(times), 1)),
            np.reshape(data, (len(data), 1))
        ), axis=1)

    
    def stop_measuring(self):
        self._inst.write("*CLS") # clear status command
        self._inst.write("*RST") # reset the instrument for SCPI operation
        self._inst.query("*OPC?")  # wait for the operation to complete

    """
    Additional custom functionality
    """

    # TODO: remove temporary stuff...
    def write(self, str):
        return self._inst.write(str)
    
    def query(self, str):
        return self._inst.query(str)
    