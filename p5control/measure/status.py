"""
Class to facilitate measurement of the status of the instruments
"""
import os
import logging
import threading
import time
from typing import Dict, Any

import numpy as np

from ..gateway import DataGateway
from ..gateway.basegw import BaseGatewayError
from ..settings import STATUS_MEASUREMENT_BASE_PATH

logger = logging.getLogger(__name__)

class StatusMeasurementError(Exception):
    """Exception related to the status measurement"""

class StatusMeasurement:
    """Call get_status on all provided devices.

    Implements the python context manager.
    """

    def __init__(
        self,
        devices: Dict[str, Any],
        refresh_delay: float = 10,
    ):
        self._devices = devices
        self.refresh_delay = refresh_delay

        self._thread = None
        self.STOP_EVENT = threading.Event()
        # this event gets set when _status_measurement_thread has stopped 
        self.STATUS_THREAD_STOP_EVENT = threading.Event()

    def start(self):
        """Start the status measurement thread"""
        if self._thread:
            raise StatusMeasurementError(
                'Can\'t start the status measurement because it is already running.'
            )

        self._thread = threading.Thread(
            target=self._status_measurement_thread,
            args=[self.STOP_EVENT]
        )
        self._thread.start()

    def stop(self):
        if not self._thread:
            raise StatusMeasurementError(
                f'Can\'t stop the status measurement because it is not running.'
            )

        self.STOP_EVENT.set()

        # block until the thread is actually stopped
        self.STATUS_THREAD_STOP_EVENT.wait()
        self.STATUS_THREAD_STOP_EVENT.clear()
        self._thread = None

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()

    def _status_measurement_thread(
        self,
        stop_event: threading.Event,
        refresh_delay: float = None,
    ):
        delay = refresh_delay if refresh_delay else self.refresh_delay
        logger.info("_status_measurement_thread started")

        dgw = DataGateway()
        dgw.connect()

        # data cache used to cache the data if the data server is somehow down
        # format {name: res,...}
        data_cache = {}

        # Thread block
        while not stop_event.wait(delay):
            logger.debug("collecting status")

            """get status of all the devices"""
            for name, (dev, _) in self._devices.items():

                try:
                    res = dev.get_status()
                except NotImplementedError:
                    continue

                # save data to cache  
                if name in data_cache:
                    data_cache[name] = np.concatenate((
                        data_cache[name], 
                        np.concatenate(([[time.time()]], res), axis=1)))
                else:
                    data_cache[name] = np.concatenate(([[time.time()]], res), axis=1)

            """try reconnecting if connection is down"""
            if not dgw._connection:
                try:
                    logger.info('connection to data server down, retrying...')
                    # blocks for 2 second and the fails if it fails to establish a connection
                    dgw.connect()
                except BaseGatewayError:
                    # server is still down, just keep caching...
                    logger.info('failed to reestablish connection to the data server')
                    continue

            """sending data"""
            if dgw._connection:
                for name in list(data_cache.keys()):
                    try:
                        dgw.append(
                            os.path.join(STATUS_MEASUREMENT_BASE_PATH, name),
                            data_cache[name]
                        )
                        # data has been send, can delete it from cache
                        data_cache.pop(name)

                    except BaseGatewayError:
                        logger.info('connection to data server lost, continuuing caching')
                        # connection might be down and reconnect has timed out
                        # in this case we just continue and cache the data
                        break

        dgw.disconnect()

        # reset stop flag
        stop_event.clear()

        logger.info("_status_thread ended, setting event")
        self.STATUS_THREAD_STOP_EVENT.set()