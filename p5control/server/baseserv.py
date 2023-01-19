"""
This file provides a basic rpyc service which is wrapped to allow for a ThreadedServer to be started and stopped
"""
import time
import threading
import logging

from rpyc import Service, ThreadedServer

logger = logging.getLogger(__name__)


class BaseServerError(Exception):
    """Exception related to a Server"""

class BaseServer(Service):
    """rpyc server with a service which exposes basic functionality.
    Implements the python context manager protocoll. The server is configured
    to only allow public attributes (not starting with "_") to be accessed by
    the client.

    Parameters
    ----------
    port : int
        port of the server
    """

    def __init__(
        self, 
        port: int,
    ):
        self._port = port
        self._rpyc_server = None

        # event used for waiting until the rpyc server thread has finished
        self.RPYC_SERVER_STOP_EVENT = threading.Event()

    def _rpyc_server_thread(self):
        self._rpyc_server = ThreadedServer(
            self,
            port=self._port,
            protocol_config={
                'allow_public_attrs': True,
            },
        )
        self._rpyc_server.start()
        # start is blocking, set the event when the server has closed
        self.RPYC_SERVER_STOP_EVENT.set()


    def start(self):
        """Start the RPyC server"""
        if self._rpyc_server:
            raise BaseServerError(
                f'Can\'t start the rpyc server at port {self._port} because one is already running.'
            )
        
        thread = threading.Thread(target=self._rpyc_server_thread)
        thread.start()

        # wait for the server to start
        while not (self._rpyc_server and self._rpyc_server.active):
            time.sleep(0.1)

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self

    def stop(self):
        """Stop the RPyC server"""
        if not self._rpyc_server:
            raise BaseServerError(
                f'Can\'t stop the rpyc server at port {self._port} because there isn\'t one running.'
            )
        
        self._rpyc_server.close()

        # block until the server is actually closed
        self.RPYC_SERVER_STOP_EVENT.wait()
        self.RPYC_SERVER_STOP_EVENT.clear()
        self._rpyc_server = None

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()

