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
    """
    Base class for a connection to an rpyc server.

    Parameters
    ----------
    addr : str = 'localhost'
        address of the server
    port : inst = INSERV_DEFAULT_PORT
        port of the server
    conn_timeout: float = 0.0
        how long to try to connect to the server before raising an exception
    allow_callback: bool = False
        whether callbacks are allowed. If True, starts `rpyc.BgServingThread` to handle
        incoming callbacks
    """

    def __init__(
        self,
        addr: str = 'localhost',
        port: int = INSERV_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        allow_callback: bool = False,
    ):
        self.addr = addr
        self.port = port
        self.conn_timeout = conn_timeout

        self._connection = None

        self.allow_callback = allow_callback
        self._bgsrv = None

    def connect(
        self,
        config=None
    ):
        """Attempt connection to the rpyc server.

        Parameters
        ----------
        config : dict = None
            can be used to configure the connection to the rpyc server.

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
                    logger.debug('starting BgServingThread')
                    self._bgsrv = rpyc.BgServingThread(
                        self._connection,
                        callback=lambda: print("bg stopped")
                    )

            except OSError as exc:
                logger.debug(
                    'Gateway couldn\'t connect to server at "%s":%s - retrying...',
                    self.addr, self.port
                )

                if time.time() > timeout:
                    raise BaseGatewayError(
                        f'Failed to connect to server at "{self.addr}:{self.port}"'
                    ) from exc

                # limit the retrying rate
                time.sleep(0.5)
            else:
                logger.info('Gateway connected to server at "%s":%s', self.addr, self.port)
                break

    def disconnect(self):
        """Disconnect form the server"""
        if self._connection:
            self._connection.close()
            self._connection = None

            logger.info('Gateway disconnected from server at "%s":%s', self.addr, self.port)

        if self._bgsrv and self._bgsrv._active: # pylint: disable=protected-access
            self._bgsrv.stop()
            self._bgsrv = None

    def reconnect(self):
        """Reconnect to the server"""
        logger.info('reconnecting to "%s":%s', self.addr, self.port)
        self.disconnect()
        self.connect()

    @property
    def connected(self):
        """Pings the connection and returns True if connected to the server."""
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
        # default python implementation
        return self.__getattribute__(attr)
