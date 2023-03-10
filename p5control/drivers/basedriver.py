"""Base Class for a driver, as an example using pyvisa
"""
import logging
import threading

import pyvisa

from ..gateway import DataGateway

logger = logging.getLogger(__name__)

class BaseDriverError(Exception):
    """Exception related to the Driver"""

class BaseDriver:
    """Base class for a driver. Implements some common funcionality for a message base driver with
    a given address.

    Inherit this class when implementing your own driver. Overwrite the different functions as
    detailed below to allow the server to automatically collect data and track the status of the
    instrument.

    **Thread-Safety:**

    pyvisa itself is not thread safe, even if the faq on their docs states this, see
    https://github.com/pyvisa/pyvisa/issues/726. Thus it is necessary to think about thread safety.
    If you use a different library, make sure that it is thread safe or implement a driver-wide
    lock to stop weird behavior.
    """

    def __init__(
        self,
        name: str,
        address: str,
        refresh_delay: float = 0.5,
    ):
        """Init the device and change constant settings, 
        for example termination of requests and replies. After this, call
        `self.open()` to open the connection to the device

        **Inheritance**: parameter `name` is required, `InstrumentServer._add` creates an instance
        by calling class_ref(name, \*args, \*\*kwargs). This is done such that
        different instances of the driver can be dinstinguished if you own an 
        instrument multiple times

        Parameters
        ----------
        name : str
            name for the device this driver is for
        address : str
            visa adress of the resource
        refresh_delay : float, default = 0.5
            time spend asleep between self.get_data() calls in the measuremet thread
        """
        self._name = name
        self._address = address
        self._inst = None

        self.refresh_delay = refresh_delay

        # connect to device
        self.open()


    def open(self):
        """Open connection to the device.
        
        Raises
        ------
        BaseDriverError
            if an connecton has already been established.
        """
        if self._inst:
            raise BaseDriverError(
                f'connection to device {self._name} already established.'
            )

        # setup device
        rem = pyvisa.ResourceManager()
        self._inst = rem.open_resource(self._address)

        logger.info('opened resource "%s" at address "%s"', self._name, self._address)

    def close(self):
        """Close connection to the device and reset self._inst variable to None
        
        Raises
        ------
        BaseDriverError
            if no connection exists which can be closed
        """
        if not self._inst:
            raise BaseDriverError(
                f'connection to device {self._name} cannot be closed since it is not open.'
            )

        logger.info('closing resource "%s" at address "%s"', self._name, self._address)
        self._inst.close()
        self._inst = None

    def __str__(self):
        """Description of the device"""
        if hasattr(self, "_address"):
            return f'Device "{self._name}" at address "{self._address}"'
        return f'Device "{self._name}"'

    def _measuring_thread(
        self,
        stop_event: threading.Event,
        entry_barrier: threading.Barrier = None,
        exit_barrier: threading.Barrier = None,
        hdf5_path: str = "",
        refresh_delay: float = None,
    ):
        """Measurement thread which periodically asks the instrument for its data and saves it. 
        Starts by calling setup_measuring and calls stop_measuring after the stop event is set.

        Parameters
        ----------
        stop_event : threading.Event
            Event which signals the thread to end
        entry_barrier : threading.Barrier, optional
            if specified, entry_barrier.wait() is called after setup. can be used to synchronise
            different measurements on different devices.
        exit_barrier : threading.Barrier, optional
            if specified, exit_barrier.wait() is called after measurements have been stopped, can 
            be used detect when all threads have stopped measuring
        hdf5_path : str, optional
            specify a path to store the data under, will be stored at hdf5_path/name
        refresh_delay : float, optional
            specify the time period after which new data is requested, can be used to overwrite
            the value from initialization
        """
        if refresh_delay:
            delay = refresh_delay
        else:
            # automatically set delay if attribute 'refresh_delay' is not set
            if hasattr(self, 'refresh_delay'):
                delay = getattr(self, 'refresh_delay')
            else:
                delay = 0.5
        logger.info('device "%s" measuring with delay %5.3fs', self._name, delay)

        try:
            self.setup_measuring()
        except NotImplementedError:
            logger.info('device "%s" does not implement setup_measuring, skipped.', self._name)

        # Connect to data server
        dgw = DataGateway()
        dgw.connect()

        if entry_barrier:
            logger.info('device "%s" waiting at entry_barrier in _measurement_thread.', self._name)
            entry_barrier.wait()
            logger.info('device "%s" released at entry_barrier', self._name)

        try:
            self.start_measuring()
        except NotImplementedError:
            logger.info('device "%s" does not implement start_measuring, skipped.', self._name)

        # Measurement block
        while not stop_event.wait(delay):

            try:
                # get data and save it
                res = self.get_data()
                self._save_data(hdf5_path, res, dgw)

            # this device cannot be measured
            except NotImplementedError:
                logger.info(
                    'device "%s" does not implement get_data, stopping measurement.', self._name)
                break

        # save any remaining data
        try:
            res = self.get_data()
            self._save_data(hdf5_path, res, dgw)
        except NotImplementedError:
            pass

        logger.info('stopping measurement of device "%s"', self._name)

        try:
            self.stop_measuring()
        except NotImplementedError:
            logger.info('device "%s" does not implement stop_measuring, skipped.', self._name)

        dgw.disconnect()

        if exit_barrier:
            logger.info('device "%s" waiting at exit_barrier in _measurement_thread.', self._name)
            exit_barrier.wait()
            logger.info('device "%s" released at exit_barrier', self._name)

    def _save_data(
        self,
        hdf5_path: str,
        array,
        dgw: DataGateway,
        **kwargs
    ):
        """Save data to hdf5 through a gateway. Overwrite this method if you want to change how or
        where this driver saves it data when being measured.
        
        Parameters
        ----------
        hdf5_path : str
            base hdf5_path under which you should save the data
        array
            data to save
        dgw : DataGateway
            gateway to the dataserver
        """
        if array is None:
            return
        path = f"{hdf5_path}/{self._name}"
        dgw.append(path, array, **kwargs)

    def stop_measuring(self):
        """In this method, write the commands necessary to restore the original state of the device
        after a measurement has been completed."""
        raise NotImplementedError(f'device "{self._name}" does not implement "stop_measuring".')

    def setup_measuring(self):
        """Setup the device prior to measurement, for example the rate of acquisition etc..."""
        raise NotImplementedError(f'device "{self._name}" does not implement "setup_measuring".')

    def start_measuring(self):
        """Start the measurement"""
        raise NotImplementedError(f'device "{self._name}" does not implement "start_measuring".')

    def get_data(self):
        """Request data from the device and process it. This can for example include the creation
        of time stamps for the corresponding time points."""
        raise NotImplementedError(f'device "{self._name}" does not implement "get_data".')

    def get_status(self):
        """Query the status of the device, including parameters which you want to be logged during
        to whole uptime of the instrument server, this can include temperature measurement of just
        the status of the device. 
        
        This method is called periodically but with a significant longer period than `get_data`
        during an actual measurment.
        
        If this method is not implemented, nothing will get logged.
        
        This method should return a dictionary of the form:
        {"ampl": 1.2, "freq": 2.3},
        note that "time" will be automatically added in the status_measurement_thread.
        """
        raise NotImplementedError(f'device "{self._name}" does not implement "get_status".')


class ThreadSafeBaseDriver(BaseDriver):
    """
    Extends ``BaseDriver`` with thread safe ``read``, ``write`` and ``query`` methods.
    """
    def open(self):
        super().open()
        self.lock = threading.Lock()

    def write(self, message: str):
        """Write a string message to the device, thread safe."""
        with self.lock:
            logger.debug('"%s" write "%s"', self._name, message)
            return self._inst.write(message)

    def read(self):
        """Read a message from the device, thread safe."""
        with self.lock:
            logger.debug('"%s" read', self._name)
            return self._inst.read()

    def query(self, message: str):
        """Write a message to the device and read a response."""
        with self.lock:
            logger.debug('"%s" query "%s"', self._name, message)
            return self._inst.query(message)
