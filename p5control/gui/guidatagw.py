"""
Wrap DataGateway to open Dialog if Connection errors occur, such that
the gui can assume the dataserver to always answer
"""
import time
import logging
import sys
import pickle
from typing import Any

from rpyc.utils.classic import obtain
from rpyc.core.netref import BaseNetref
from qtpy.QtWidgets import QMessageBox, QSpacerItem

from ..gateway import DataGateway
from ..gateway.basegw import BaseGatewayError
from ..settings import DATASERV_DEFAULT_PORT

logger = logging.getLogger(__name__)

class WrapNetref():
    """Wrap netref"""
    def __init__(self, netref, dgw) -> None:
        logger.debug("wrapping %s", str(netref))
        self._secret_netref = netref
        self._secret_class = dgw.network_safe_getattr(netref, '__class__')
        self.dgw = dgw

    def __str__(self) -> str:
        return f"<WrapNetref wrapping {self._secret_class}>"

    def __call__(self, *args, **kwargs):
        logger.debug('Calling %s with args %s and kwargs %s',
            self._secret_netref, str(args), str(kwargs))
        try:
            res = self._secret_netref(*args, **kwargs)

            if isinstance(res, BaseNetref):
                return WrapNetref(res, self.dgw)
            return res

        except EOFError as error:
            # make sure the connection is closed
            self.dgw.disconnect()
            old_filename = self.dgw.dataserv_filename

            # loop until success:
            while True:

                # wait for connection to establish again
                while not self.dgw.connected:
                    self.dgw.connect_to_filename(error, old_filename)

                    # try operation again, if it fails again, return to retrying
                    try:
                        res = self._secret_netref(*args, **kwargs)

                        if isinstance(res, BaseNetref):
                            return WrapNetref(res, self.dgw)
                        return res
                    except EOFError as newerror:
                        self.dgw.disconnect()
                        logger.error(str(error))
                        error = newerror

    def __getattr__(
        self,
        attr: str
    ):
        return self.dgw.network_safe_getattr(self._secret_netref, attr)

    def __reduce__(self):
        """Allow for pickling of the wrapped netref."""
        return pickle.loads, (pickle.dumps(self._secret_netref),)


class GuiDataGatewayError(Exception):
    """related to errors specifig to GuiDataGateway"""

class GuiDataGateway(DataGateway):
    """Wrapper for DataGateway to use in a GUI application.

    Opens a message box if the connection to the dataserver fails
    and assures that the request returns something.

    !! This is not thread safe, make sure that this gateway is only
    used by a single thread !!"""
    def __init__(
        self,
        addr: str = 'localhost',
        port: int = DATASERV_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        allow_callback: bool = False
    ):
        super().__init__(addr, port, conn_timeout, allow_callback)
        self.dataserv_filename = None

    def connect(self, config=None):
        super().connect(config)
        self.dataserv_filename = self.filename

    def __getattr__(
            self,
            attr: str
    ):
        """Allow shorthand gateway.attribute for gateway.root.attribute"""
        logger.debug('dgw.__getattr__("%s")', attr)
        if self._connection:
            root = self.network_safe_getattr(self._connection, 'root')
            return self.network_safe_getattr(root, attr)
        # default python implementation
        return self.__getattribute__(attr)

    def network_safe_getattr(
        self,
        obj: Any,
        attr: Any,
    ):
        """
        Tries ``getattr(obj, attr)`` and handles any connection problems, assures that
        the object is returned or the application is closed.
        """
        logger.debug('safe getattr, obj: %s, attr: "%s"', str(obj), attr)
        try:
            res = getattr(obj, attr)

            if attr in ['__iter__', '__next__']:
                res = res()

            if isinstance(res, BaseNetref):
                return WrapNetref(res, self)
            return res

        except EOFError as error:
            logger.warning('EOFError %s', error)
            # make sure the connection is closed
            self.disconnect()
            old_filename = self.dataserv_filename

            # loop until success:
            while True:

                # wait for connection to establish again
                while not self.connected:
                    self.connect_to_filename(error, old_filename)
                    logger.info('connect status: %s', self.connected)

                    # try operation again, if it fails again, return to retrying
                    try:
                        logger.debug('retrying obj: %s, attr: "%s"', obj, attr)
                        res = getattr(obj, attr)

                        if attr in ['__iter__', '__next__']:
                            res = res()

                        if isinstance(res, BaseNetref):
                            return WrapNetref(res, self)
                        return res

                    except EOFError as newerror:
                        logger.warning('EOFError %s', error)
                        self.disconnect()
                        error = newerror

    def connect_to_filename(
        self,
        error: Exception,
        filename: str
    ):
        """blocks until the gateway is connected again, to a data server
        which serves the same hdf5 file as to one connection was lost to.
        """
        while not self.connected:
            # btn = self.message_reconnect(error, filename).exec()
            btn = QMessageBox.Retry
            
            time.sleep(0.5)

            if btn == QMessageBox.Abort:
                sys.exit()
            else:
                try:
                    self.connect()

                    if filename != self.dataserv_filename:
                        # reject the connection to this data server, this is because
                        # a different hdf5 file means that it will not have the same
                        # content which the gui is expecting and has loaded references
                        # to and therefore it might break. so we disconnect and want
                        # the user to host the old file again.
                        self.disconnect()
                        raise GuiDataGatewayError(
                            'Dataserver which is running hosts hdf5 file '
                            f'"{self.dataserv_filename}" which is different from the '
                            f'file the gui worked with: "{filename}".')

                except (BaseGatewayError, GuiDataGatewayError) as newerror:
                    error = newerror
        print("reconnect returning...")

    def message_reconnect(
        self,
        error: Exception,
        filename: str
    ):
        """
        return ``QMessageBox`` which informs the user about the lost connection
        to the data server and lets him press retry.

        Parameters
        ----------
        error: Exception
            the exception which led to the message box to be shown
        filename: str
            the hdf5 file the old dataserver used
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle('Dataserver connection error')
        msg.setText(f'<b>{error.__class__.__name__}:</b> {error}')
        msg.setInformativeText('Could not connect to the dataserver. '
            'Make sure that the dataserver is running and then click <i>Retry</i> to reconnect '
            'to the data server. Possible errors:'
            ' <ul>'
            f'  <li>data server is not running on "{self.addr}":{self.port}</li>'
            f'  <li>data server is not using hdf5 file "{filename}"</li>'
            '</ul> '
            'Click <i>Abort</i> or close the window to close the gui.')

        msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Abort)
        msg.setDefaultButton(QMessageBox.Retry)

        # make message box bigger
        layout = msg.layout()
        layout.addItem(QSpacerItem(500, 0), layout.rowCount(), 0, 1, layout.columnCount())

        return msg

    def get_data(self, path, indices: slice = (), field: str = None):
        """Overwrite get_data to include gui error handling."""
        logger.debug('"%s", %s, %s', path, indices, field)

        root = self.network_safe_getattr(self._connection, 'root')
        func = self.network_safe_getattr(root, 'get_data')
        res = func(path, indices, field)

        return obtain(res)

    def register_callback(self, path, func, is_group: bool = False):
        """Overwrite register_callback to include gui error handling."""
        if not self.allow_callback:
            raise BaseGatewayError(
                'Can\'t register callback, because callbacks are not enabled for the gateway.'
            )

        logger.debug('"%s", %s, %s', path, func, is_group)

        root = self.network_safe_getattr(self._connection, 'root')
        f = self.network_safe_getattr(root, 'get_data')
        res = f(path, func, is_group)

        return res
