"""
This module provides an interface to the data server
"""
import logging

from rpyc.utils.classic import obtain

from .basegw import BaseGateway, BaseGatewayError
from ..settings import DATASERV_DEFAULT_PORT

logger = logging.getLogger(__name__)

class DataGateway(BaseGateway):
    def __init__(
        self,
        addr: str = 'localhost',
        port: int = DATASERV_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        allow_callback: bool = False,
    ):
        super().__init__(addr, port, conn_timeout, allow_callback)

    def connect(self):
        # we need to allow pickling for the transfer of numpy arrays
        config={'allow_pickle': True}
        super().connect(config=config)

    def get_dataset(self, path):
        #!!! use obtain with numpy arrays
        return obtain(self._connection.root.get_dataset(path))

    def get_dataset_slice(self, path, slice):
        #!!! use obtain with numpy arrays
        return obtain(self._connection.root.get_dataset_slice(path, slice))

    def get_dataset_field(self, path, field, slice):
        #!!! use obtain with numpy arrays
        return obtain(self._connection.root.get_dataset_field(path, field, slice))

    def register_callback(self, id, path, func):
        logger.info(f'register_callback("{id}", "{path}", {func})')

        if not self.allow_callback:
            raise BaseGatewayError(
                f'Can\'t register callback "{id}" because callbacks are not enabled for the gateway')

        self._connection.root.register_callback(id, path, func)

    def remove_callback(self, id):
        logger.info(f'remove_callback("{id}")')
        self._connection.root.remove_callback(id)