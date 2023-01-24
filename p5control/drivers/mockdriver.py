# exampleinst.py
import time
import logging

import numpy as np
from .basedriver import BaseDriver

logger = logging.getLogger(__name__)

class MockInst(BaseDriver):
    """your custom driver"""
    def __init__(self, name):
        self._name = name
        self._offset = np.random.rand() * 50

        self._amplitude = 1.1
        self._freq = 1

    def open(self):
        logger.debug(f'{self._name}.open()')

    def close(self):
        logger.debug(f'{self._name}.close()')

    def get_status(self):
        return np.array([[self._amplitude, self._freq]])   

    def start_measuring(self):
        self.last_time = time.time()

    def get_data(self):
        logger.debug(f'{self._name}.get_data()')

        now = time.time()

        times = np.arange(self.last_time, now, 0.1)
        values = [self._amplitude * np.sin(self._freq*(t + 0.1*np.random.rand()) \
        + self._offset) + 0.3*np.random.rand() for t in times]
        values = np.array(values)

        # set time for next cycle
        self.last_time = now

        # format data to shape (length, 2)
        return np.concatenate((
            np.reshape(times, (len(times), 1)),
            np.reshape(values, (len(values), 1))
        ), axis=1)

    def setAmplitude(self, value):
        self._amplitude = value

    def setFrequency(self, value):
        self._freq = value