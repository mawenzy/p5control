import threading
import logging
from typing import Dict, Any, List

from .dataserv import DataServer
from .baseserv import BaseServer, BaseServerError
from ..settings import INSERV_DEFAULT_PORT, DATASERV_DEFAULT_PORT
from ..measure import Measurement, StatusMeasurement, MeasurementError

logger = logging.getLogger(__name__)

class InstrumentServerError(BaseServerError):
    """Exception related to the InstrumentServer"""

class InstrumentServer(BaseServer):
    """rpyc service that loads devices and exposes them to the client

    only public attributes (not starting with "_") can be called by the client
    """

    def __init__(
        self, 
        port: int = INSERV_DEFAULT_PORT,
        data_server_port: int = DATASERV_DEFAULT_PORT,
        data_server_filename: str = None,
    ):
        super().__init__(port)

        self._devices: Dict[str, Any] = {}

        # Status mesaurement
        self._status_measurement = None
        self._status_thread_stop_event = threading.Event()

        # Data server
        self._data_server_port = data_server_port
        self._data_server_filename = data_server_filename
        self._data_server = None

        # Measurement
        self._measurement = None

    def _add(
        self,
        name: str,
        class_ref,
        *args,
        **kwargs,
    ) -> None:
        """Create an instance of the specified class and add it to the instrument server.

        Parameters
        ----------
        name: str
            Alias for the device
        """
        if name in self._devices:
            raise InstrumentServerError(f'device with name "{name}" already exists.')
        
        # create instance of the device
        try:
            instance = class_ref(name, *args, **kwargs)
        except Exception as exc:
            raise InstrumentServerError(
                f'Failed to create an instance of device "{name}" of class'
                f' "{class_ref}"',
            ) from exc
    
        # save the device and config info
        config = {
            'class_ref': class_ref,
            'args': args,
            'kwargs': kwargs,
        }
        self._devices[name] = (instance, config)

    def _remove(
        self,
        name: str,
    ):
        try:
            dev, _ = self._devices.pop(name)
        except Exception as exc:
            raise InstrumentServerError(f'Failed deleting device "{name}"') from exc
        
        # exit driver
        try:
            dev.close()
        except AttributeError:
            pass

    def _restart(
        self,
        name: str
    ):
        config_dict = self._devices[name][1]
        class_ref = config_dict["class_ref"]
        args = config_dict["args"]
        kwargs = config_dict["kwargs"]

        self._remove(name)
        self._add(name, class_ref, *args, **kwargs)

    def start(self):
        """Starts the RPyC instrument server, then a data server and then
        starts the status measurement thread
        """

        # start the RPyC server
        logger.debug('start() starting instrument server')
        super().start()

        # Start the data server
        logger.debug('start() starting data server')
        self._data_server = DataServer(
            self._data_server_port,
            filename=self._data_server_filename)
        self._data_server.start()

        # start status thread
        logger.debug('start() starting StatusMeasurement')
        self._status_measurement = StatusMeasurement(self._devices)
        self._status_measurement.start()


    def stop(self):
        """Stop the instrument server and the status measurement and dataserver
        if they are running.

        Order ist important, first stop the status thread so it does no longer 
        write data to the data server, then the data server can be stopped
        """
        logger.debug('stop() called')

        # stop an ongoing measurement
        if self._measurement and self._measurement._running:
            logger.debug('stop() stopping running measurement')
            self._measurement.stop()

        # stop status thread
        if self._status_measurement:
            logger.debug('stop() stopping status measurement thread')
            self._status_measurement.stop()
            self._status_measurement = None
        else:
            logger.debug('stop() no status measurement running, so nothing to stop')

        # stop the data server
        if self._data_server:
            logger.debug('stop() stopping data server')
            self._data_server.stop()
            self._data_server = None
        else:
            logger.debug('stop() no data server running, so nothing to stop')

        # stop the RPyC server
        logger.debug('stopping instrument server')
        super().stop()


    def __getattr__(
        self,
        attr: str,
    ):
        """Allow the client to access the driver objects directly using
        server.device"""
        if attr in self._devices:
            return self._devices[attr][0]
        else:
            # let default python implementation handle all other cases
            return self.__getattribute__(attr)
        
    def measure(
        self,
        name: str = None,
        include: List[str] = None,
        exclude: List[str] = None,
    ):
        """Get a measurement of all the specified devices.If either name or the devices
        are different than the last measurement, a new one is returned 

        Parameters
        ----------
        name : str, optional
            name of the measurement, will determine the path under which the results are
            safed in the hdf5 path. I no name is provided, a generic name is automatically
            generated, which updates with every call.
        include : List[str], optional
            specify the instruments to measure, given their names.
        exclude : List[str], optional
            if include is not specified, this can be used to exclude some instruments, all
            others will be measured.
        """
        # get devices
        if include is not None:
            devices = {name: self._devices[name] for name in include}
        elif exclude is not None:
            devices = self._devices.copy()
            for name in exclude:
                devices.pop(name)
        else:
            devices = self._devices

        # create measurement if none exists
        if not self._measurement:
            self._measurement = Measurement(devices, name)
            return self._measurement

        # decide if a new measurement is needed
        ndev = set(devices.keys())
        odev = set(self._measurement._devices.keys())

        if name and name == self._measurement._name and ndev-odev == set() and odev-ndev == set():
            print("returning existing one")
            return self._measurement
        elif self._measurement._running:
            raise MeasurementError(
                'Can\'t create new measurement because the old one is still runing.'
            )
        else:
            self._measurement = Measurement(devices, name)
            return self._measurement