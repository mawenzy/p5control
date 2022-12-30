"""
Class to facilitate a measurement, e.g. using a script with a context manager
"""
import os
import logging
import threading
from typing import Dict, Any

from ..util import name_generator
from ..settings import MEASUREMENT_BASE_PATH

logger = logging.getLogger(__name__)

# experiment file name generator
exp_name_generator = name_generator(
    "m",
    width=6,
)

class MeasurementError(Exception):
    """Exception related to an Measurement"""


class Measurement:
    """Measure all the provided devices.
    
    Implements the python context manager.
    """

    def __init__(
        self,
        devices: Dict[str, Any],
        name: str = None,
    ):
        """
        Parameters
        ----------
        devices: 
            which devices the data should be recorded from
        filename : str, optional 
            output file for the recorded data. If omitted, will be generated
            automatically
        """
        self._devices = devices

        self._name = name if name else next(exp_name_generator)
        self._name = os.path.join(MEASUREMENT_BASE_PATH, self._name)
        logger.info(f'measurement with filename "{self._name}"')

        # amount of devices
        cnt = len(self._devices)

        # setup thread control
        self._running = False
        self.STOP_EVENT = threading.Event()

        # barriers (+1 since this thread waits for the other threads to initalize or stop)
        self.entry_barrier = threading.Barrier(cnt + 1)
        self.exit_barrier = threading.Barrier(cnt + 1)


    def start(self):
        """Start measurement by starting all the separate measuring threads of the devices.
        
        Blocks until all have run their setup and then releases them at the same time."""  
        if self._running:
            raise MeasurementError(
                'Can\'t start the measurement because it is already running.'
            )
        
        logger.info(f'starting measurement {self._name}')

        # start threads
        for dev, _ in self._devices.values():
            thread = threading.Thread(
                    target=dev._measuring_thread, 
                    args=[self.STOP_EVENT, 
                          self.entry_barrier, 
                          self.exit_barrier,
                          self._name],
                    )
            thread.start()

        # wait for all threads to initialize
        logger.info('All threads started, waiting at entry_barrier.')
        self.entry_barrier.wait()
        self._running = True
        logger.info('Passed entry_barrier.')

    def stop(self):
        """Stop all measurements threads. Blocks until all are finished."""
        if not self._running:
            raise MeasurementError(
                'Can\'t stop the measurement because it is not running.'
            )

        logger.info('Setting measurement stop flag.')
        self.STOP_EVENT.set()

        # wait for all threads to finish
        logger.info('Waiting at exit_barrier.')
        self.exit_barrier.wait()
        logger.info('Passed exit barrier.')

        # reset
        self.STOP_EVENT.clear()
        self.entry_barrier.reset()
        self.exit_barrier.reset()
        self._running = False

    def __str__(self):
        return f'Measurement<"{self._name}">'

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Pyton context manager teardown"""
        self.stop()
 