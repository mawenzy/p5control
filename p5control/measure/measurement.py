"""
Class to facilitate a measurement, e.g. using a script with a context manager. For a brief introduction, take a look at the sample project:

* :ref:`example_measurement`
"""
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
    """Measure all the provided devices. Implements the python context manager. Make sure that only one measurement is running at a time, because otherwise the calls to ``get_data`` of the drivers will interfere with each other.

    Parameters
    ----------
    devices :  Dict[str, Any]
        which devices the data should be recorded from
    name : str, optional 
        output name for the recorded data. If omitted, will be generated
        automatically
    """

    def __init__(
        self,
        devices: Dict[str, Any],
        name: str = None,
    ):
        self._devices = devices

        self._name = name if name else next(exp_name_generator)
        self._path = f"{MEASUREMENT_BASE_PATH}/{self._name}"
        logger.info(f'measurement with name "{self._name}" and path "{self._path}"')

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
                          self._path],
                    )
            thread.start()

        # wait for all threads to initialize
        logger.info('All threads started, waiting at entry_barrier.')
        self.entry_barrier.wait()
        self._running = True
        logger.info('Passed entry_barrier, measurement is running.')

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

    def path(self):
        return self._path
 
    def name(self):
        return self._name

    def running(self):
        return self._running