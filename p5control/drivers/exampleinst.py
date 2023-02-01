"""
Test driver to illustrate the inner workings of *p5control*.
"""
import logging
import time

import numpy as np

from .basedriver import BaseDriver

logger = logging.getLogger(__name__)

class ExampleInst(BaseDriver):
    """Represents an instrument which magically measures a sine wave. Both the frequency and the amplitude can be changed.

    Parameters
    ----------
    name : str
        name for this instance
    """

    def __init__(self, name: str):
        self._name = name
        self._offset = np.random.rand() * 50

        self._amplitude = 1.1
        self._freq = 1.0

    def open(self):
        """Just logs the call to debug."""
        logger.debug(f'{self._name}.open()')

    def close(self):
        """Just logs the call to debug."""
        logger.debug(f'{self._name}.close()')

    """
    Status measurement
    """
    def get_status(self):
        """Returns the current amplitude and frequency."""
        logger.debug(f'{self._name}, ampl: {self._amplitude}, freq: {self._freq}')
        return {
            "ampl": self._amplitude,
            "freq": self._freq
        }

    """
    Measurement
    """
    def start_measuring(self):
        """Start the measurement. Saves the current time such
        that we can keep track of how much time has passed
        when :meth:`ExampleInst.get_data` gets called.
        """
        self.last_time = time.time()

    def get_data(self):
        """Calculates sine wave over the time passed since the
        last call and adds some noise to it.
        """
        logger.debug(f'{self._name}.get_data()')

        now = time.time()

        times = np.arange(self.last_time, now, 0.1)
        values = [self._amplitude * np.sin(self._freq*(t + 0.1*np.random.rand()) + self._offset) + 0.3*np.random.rand() for t in times]
        values = np.array(values)

        # set time for next cycle
        self.last_time = now

        return {
            "time": list(times),
            "V": list(values),
        }


    """
    change parameters
    """
    def setAmplitude(self, value: float):
        """Set amplitude to ``value``."""
        self._amplitude = value

    def setFrequency(self, value: float):
        """Set frequency to ``value``."""
        self._freq = value
