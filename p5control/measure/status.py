"""
Class to facilitate measurement of the status of the instruments while the instrument server is running. A thread with this measurement is automatically started with the instrument server.
"""
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
    """Call ``get_status`` on all provided devices. Implements the python context manager.

    Parameters
    ----------
    devices : Dict[str, Any]
        the devices for which the status should be recorded
    refresh_delay: float, default = 10
        pause between collecting status, by default 10s
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
        """Start the status measurement thread. Does not block but returns after starting the thread."""
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
        """Stop the status measurement thread. Blocks until the thread has finished."""
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
        logger.info("thread started")

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

                # skip emtpy data
                if isinstance(res, dict) and len(res) == 0:
                    continue

                # append time stamp
                if isinstance(res, dict):
                    res = {k: [v] for k,v in res.items()}
                    res["time"] = [time.time()]
                else:
                    res = np.concatenate(([[time.time()]], res), axis=1)

                if hasattr(dev, '_save_status'):
                    dev._save_status(f"{STATUS_MEASUREMENT_BASE_PATH}/{name}", res, dgw)
                else:
                    dgw.append(
                        f"{STATUS_MEASUREMENT_BASE_PATH}/{name}",
                        res
                    )

        logger.info('stopping, disconnecting from data server.')
        dgw.disconnect()

        # reset stop flag
        stop_event.clear()

        logger.info("stopped, setting event")
        self.STATUS_THREAD_STOP_EVENT.set()