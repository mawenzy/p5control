import threading
import logging
from pathlib import Path

from rpyc.utils.classic import obtain
from rpyc import ThreadedServer

from ..settings import DATASERV_DEFAULT_PORT, DEFAULT_DATA_DIR
from ..data import HDF5FileInterface
from ..util import new_filename_generator
from .baseserv import BaseServer, BaseServerError

logger = logging.getLogger(__name__)


# event used for waiting until the rpyc server thread has finished
RPYC_SERVER_STOP_EVENT = threading.Event()

# event used for waiting until the rpyc server thread has finished
class DataServerError(BaseServerError):
    """Exception related to the DataServer"""

class DataServer(BaseServer):
    """rpyc service that collects and shares data"""

    def __init__(
        self,
        port: int = DATASERV_DEFAULT_PORT,
        filename: str = None,
    ):
        super().__init__(port)

        if not filename:
            # generate new filename
            self._filename = next(new_filename_generator(DEFAULT_DATA_DIR.joinpath("session")))
            logger.info(f'no filename provided, generated filename "%s"', self._filename)

            # make sure parent folder exitsts, if not create it
            Path(self._filename).parent.mkdir(parents=True, exist_ok=True)
        else:
            self._filename = filename
        
        logger.info(f'DataServer using file "%s"', self._filename)

        self._handler = None

    def _rpyc_server_thread(self):
        self._rpyc_server = ThreadedServer(
            self,
            port=self._port,
            protocol_config={
                'allow_public_attrs': True,
                'allow_pickle': True,
            },
        )
        self._rpyc_server.start()
        # start is blocking, set the event when the server has closed
        self.RPYC_SERVER_STOP_EVENT.set()

    def start(self):
        """Start the RPyC server"""
        super().start()

        """Open hdf5 file"""
        self._handler = HDF5FileInterface(self._filename)

    def stop(self):
        """Close hdf5 file"""
        self._handler.close()

        """Stop the RPyC server"""
        super().stop()

    """
    Data operation
    """

    def append(self, path, arr, **kwargs):
        # copy array to the local machine
        logger.debug('obtaining array for path "%s"', path)
        arr = obtain(arr)
        
        return self._handler.append(path, arr, **kwargs)

    @property
    def filename(self):
        return self._filename

    def __getattr__(
        self,
        attr: str,
    ):
        """Allow the client to access the handler objects directly using
        server.method"""
        try:
            return getattr(self._handler, attr)
        except AttributeError:
            # let default python implementation handle all other cases
            return self.__getattribute__(attr)


    