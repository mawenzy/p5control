"""
Driver for KEYSIGHT 34461A Digit Multimeter
"""
import time

import numpy as np

from .basedriver import BaseDriver

class Keysight34461A(BaseDriver):
    """Driver for the Keysight34461A. Since it is MessageBased, we can use much
    of the BaseDriver class.
    """

    def open(self):
        """Open connection to the device.
        
        Overwritten to add the termination characters and reset the device after it has been
        connected.
        """
        super().open()

        # setup termination
        self._inst.write_termination = "\n"
        self._inst.read_termination = "\n"

        # copied from olli driver
        self._inst.timeout = 10000
        self._inst.write("*CLS") # clear status command
        self._inst.write("*RST") # reset the instrument for SCPI operation
        self._inst.query("*OPC?") # wait for the operation to complete

        self.batch = 0

        self._inst.write("DISP:TEXT 'connected'")

    """
    Measuring setup
    """

    def setup_measuring(self):
        self._inst.write("*CLS") # clear status command
        self._inst.write("*RST") # reset the instrument for SCPI operation
        self._inst.query("*OPC?")  # wait for the operation to complete

        # copied from messprogramm
        self._inst.write('VOLT:DC:NPLC MIN')
        #don't do autorange, else time axis doesnt work
        # self._inst.write('VOLT:DC:RANG:AUTO ON')
        self._inst.write('VOLT:DC:RANG:AUTO OFF')
        self._inst.write('VOLT:DC:RANG 10')
        self._inst.write(':SENS:VOLT:DC:ZERO:AUTO OFF')
        self._inst.write('TRIG:SOUR IMM') 
        self._inst.write("TRIG:COUN INF")
        self._inst.write("SAMP:COUN MAX")
        self._inst.write('DISP:TEXT "measuring    "')
        self.textcnt = 0

    def start_measuring(self):
        self._inst.write("INIT")
        self.last_time = time.time()

    def get_data(self):
        # create time stamps
        # now davor, weil intrument brauch verschieden lang zum antworten
        now = time.time()

        data = self._inst.query("R?")
        # see page 205 in programmer manual
        data = np.fromstring(data[2+int(data[1]):], sep=",", dtype='f')
        times = np.linspace(self.last_time, now, len(data), endpoint=False)

        # set time for next cycle
        self.last_time = now
        
        # update display text
        self._inst.write(f'DISP:TEXT "measuring{"."*self.textcnt:4s}"')
        self.textcnt = (self.textcnt + 1) % 4

        self.batch += 1     
        self.batch = self.batch%10   
        return {
            "time": list(times),
            "V": list(data),
            "trig": list(np.ones(np.shape(times))*self.batch*.1)
        }

    def _save_data(self, hdf5_path, array, dgw):
        """save data and set attributes for default values for buffers."""
        path = f"{hdf5_path}/{self._name}"
        dgw.append(
            path,
            array,
            max_length=int(10000),
            down_sample=int(10)
        )

    def stop_measuring(self):
        self._inst.write("*CLS") # clear status command
        self._inst.write("*RST") # reset the instrument for SCPI operation
        self._inst.query("*OPC?")  # wait for the operation to complete

        self._inst.write("DISP:TEXT ''")

    """
    Additional custom functionality
    """

    # TODO: remove temporary stuff...
    def write(self, str):
        return self._inst.write(str)
    
    def query(self, str):
        return self._inst.query(str)
    