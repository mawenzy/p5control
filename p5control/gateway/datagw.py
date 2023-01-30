"""
This module provides an interface to the data server
"""
import logging

from rpyc.utils.classic import obtain

from .basegw import BaseGateway, BaseGatewayError
from ..settings import DATASERV_DEFAULT_PORT

logger = logging.getLogger(__name__)

class DataGateway(BaseGateway):
    """Gateway to the data server. Use this to add and retrieve data as well
    as install callbacks.

    Parameters
    ----------
    addr : str = 'localhost'
        address of the data server
    port : int = DATASERV_DEFAULT_PORT
        port of the data server
    conn_timeout : float = 0.0
        how long to try to connect to the server, at least one try is made
    allow_callback : bool = False
        whether to allow registering of callbacks.
    """
    def __init__(
        self,
        addr: str = 'localhost',
        port: int = DATASERV_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        allow_callback: bool = False,
    ):
        super().__init__(addr, port, conn_timeout, allow_callback)

    def connect(self, config=None):
        # we need to allow pickling for the transfer of numpy arrays
        if config:
            config["allow_pickle"] = True
        else:
            config={'allow_pickle': True}
        super().connect(config=config)

    def get_data(self, path, indices: slice = (), field: str = None):
        """Wraps ``self._connection.root.get_data`` to use ``obtain`` on the result
        in order to transfer the data to a local object.
        """
        logger.debug('obtaining result for "%s", %s, %s', path, indices, field)
        return obtain(self._connection.root.get_data(path, indices, field))

    def register_callback(self, path, func, is_group: bool = False):
        """Wraps ``self._connection.root.register_callback`` to check whether callbacks are
        enabled.
        """
        if not self.allow_callback:
            raise BaseGatewayError(
                'Can\'t register callback, because callbacks are not enabled for the gateway')

        logger.debug('"%s", %s, %s', path, func, is_group)
        return self._connection.root.register_callback(path, func, is_group)
