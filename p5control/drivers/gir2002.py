import logging
import time
from pyvisa import ResourceManager
from pyvisa.constants import StopBits, Parity

import numpy as np

from .basedriver import BaseDriver

logger = logging.getLogger(__name__)

class GIR2002(BaseDriver):
    def __init__(self, name, address='COM3', res: float = 0.1):
        self._name = name
        self._address = address
        self._res = res
        self.refresh_delay = 1
        self.open()

    def open(self):
        rm = ResourceManager()
        self._inst = rm.open_resource(self._address)
        self._inst.baud_rate = 4800
        self._inst.data_bits = 8
        self._inst.parity = Parity.none
        self._inst.stop_bits = StopBits.one
        self._inst.send_end = False
        self._inst.read_termination = ''
        self._inst.write_termination = ''
        logger.debug(f'{self._name}.open()')

    def close(self):
        self._inst.close()
        logger.debug(f'{self._name}.close()')

    """
    Status measurement
    """
    def get_status(self):
        logger.debug(f'{self._name}.get_status()')
        return np.array([[self.read()]])


    """
    Measurement
    """
    def get_data(self):
        logger.debug(f'{self._name}.get_data()')

        return {
            "time": time.time(),
            "val": self.read()
        }


    """
    change parameters
    """
    
    def read(self):
        try:
            self._inst.write_raw(b'\xfe\x00=')
            response = self._inst.read_bytes(6)
            integer = (256 * (255 - response[3]) + response[4]) & 16383 - 2048
            value = float((int(integer)+280)%2048-280) * self._res
        except:
            value=np.nan

        return value

    def getResolution(self):
        return self._res
    
    def setResolution(self, value:float):
        self._res = value
