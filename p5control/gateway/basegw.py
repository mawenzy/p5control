"""
This module provides an interface to control devices on an instrument server.
"""
import logging
import time

import rpyc

from ..settings import INSERV_DEFAULT_PORT

logger = logging.getLogger(__name__)

class BaseGatewayError(Exception):
    """Raised for failures related to the BaseGateway."""

class BaseGateway:
    def __init__(
        self,
        addr: str = 'localhost',
        port: int = INSERV_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        allow_callback: bool = False,
    ):
        """
        Args:
            addr: Network address of the instrument server.
            port: Port number of the instrument server
            connt_timeout: time to wait for the connection to be established
        """
        self.addr = addr
        self.port = port
        self.conn_timeout = conn_timeout
        
        self._connection = None

        self.allow_callback = allow_callback
        self._bgsrv = None

    def connect(self, config=None):
        """Attempt connection to an InstrumentServer.
        
        Raises
        ------
        BaseGatewayError
            Connection to the Server failed
        """
        timeout = time.time() + self.conn_timeout
        while True:
            try:
                # connect to the rpyc server
                if config:
                    self._connection = rpyc.connect(
                        self.addr,
                        self.port,
                        config=config,
                    )
                else:    
                    self._connection = rpyc.connect(
                        self.addr,
                        self.port,
                    )

                if self.allow_callback:
                    self._bgsrv = rpyc.BgServingThread(self._connection)

            except OSError as exc:

                logger.debug(
                    f'Gateway couldn\'t connect to server at "{self.addr}:{self.port}" - retrying...'
                )

                if time.time() > timeout:
                    raise BaseGatewayError(
                        f'Failed to connect to server at "{self.addr}:{self.port}"'
                    ) from exc
                
                # limit the retrying rate
                time.sleep(0.5)
            else:
                logger.info(f'Gateway connected to server at "{self.addr}:{self.port}"')
                break 

    def disconnect(self):
        """Disconnect form the server"""
        self._connection.close()
        self._connection = None

        if self._bgsrv:
            self._bgsrv.stop()
            self._bgsrv = None

        logger.info(f'Gateway disconnected from server at {self.addr}:{self.port}')

    def reconnect(self):
        """Reconnect to the server"""
        self.disconnect()
        self.connect()

    @property
    def connected(self):
        if self._connection:
            try:
                self._connection.ping()
                return True
            except EOFError:
                return False

    def __enter__(self):
        """Python context manager setup"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect()

    def __getattr__(
        self,
        attr: str,
    ):
        """Allow shorthand gateway.attribute for gateway.root.attribute"""
        if self._connection:
            try:
                return getattr(self._connection.root, attr)
            except EOFError:
                # the server might have disconnected - try reconnecting
                self.reconnect()
                return getattr(self._connection.root, attr)
        else:
            # default python implementation
            self.__getattribute__(attr)

            