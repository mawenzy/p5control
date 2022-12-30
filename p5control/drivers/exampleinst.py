"""
Test driver to test data saving
"""
import logging
import time

import numpy as np

from .basedriver import BaseDriver

logger = logging.getLogger(__name__)

class ExampleInst(BaseDriver):
    def __init__(self, name):
        self._name = name
        self.refresh_delay = 0.5
        self._offset = np.random.rand() * 50
        self._amplitude = 1.1

    def open(self):
        logger.debug(f'{self._name}.open()')
        pass

    def close(self):
        logger.debug(f'{self._name}.close()')
        pass

    """
    Status measurement
    """
    def get_status(self):
        logger.debug(f'{self._name}.get_status()')
        # return np.array([[np.sin(time.time() * 0.01 + self._offset + 0.1*np.random.rand())]])
        return np.array([[self._amplitude]])


    """
    Measurement
    """
    def start_measuring(self):
        self.last_time = time.time()

    def get_data(self):
        logger.debug(f'{self._name}.get_data()')

        now = time.time()

        times = np.arange(self.last_time, now, 0.1)
        values = [self._amplitude * np.sin(t + 0.1*np.random.rand() + self._offset) + 0.3*np.random.rand() for t in times]
        values = np.array(values)

        # set time for next cycle
        self.last_time = now

        # format data to shape (length, 2)
        return np.concatenate((
            np.reshape(times, (len(times), 1)),
            np.reshape(values, (len(values), 1))
        ), axis=1)

    """
    change amplitude
    """
    def setAmplitude(self, value):
        self._amplitude = value
