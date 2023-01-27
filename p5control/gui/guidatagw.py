"""
Wrap DataGateway to open Dialog if Connection errors occur, such that
the gui can assume the dataserver to always answer 
"""
from rpyc.core.netref import NetrefClass, BaseNetref, LOCAL_ATTRS
from rpyc.core.protocol import Connection
from rpyc.utils.classic import obtain
from qtpy.QtWidgets import QMessageBox

from ..gateway import DataGateway

class WrapNetref():
    def __init__(self, netref) -> None:
        self._secret_netref = netref

    def __str__(self) -> str:
        return f"<p5control.gui.guidatagw.WrapNetref wrapping {self._secret_netref}>"

    def __call__(self, *args, **kwargs):
        try:
            res = self._secret_netref(*args, **kwargs)
            # print(f"WrapNetref call res {res}, {type(res)}")
            if isinstance(res, BaseNetref):
                return WrapNetref(res)
            return res
        except Exception as e:
            print(f"__call__ exc {type(e)} caught: {e}")
            raise

    def __getattr__(
        self,
        attr: str
    ):
        # print(f"__getattr__ {attr}")
        try:
            res = getattr(self._secret_netref, attr)

            if isinstance(res, BaseNetref):
                return WrapNetref(res)
            return res
        except Exception as e:
            print(f"__getattr__ {attr} exc {type(e)} caught: {e}")
            raise

    def __iter__(self):
        res = getattr(self._secret_netref, '__iter__')()
        # print(f"WrapNetref iter res {res}, {type(res)}")

        if isinstance(res, BaseNetref):
            return WrapNetref(res)
        return res

    def __next__(self):
        res = getattr(self._secret_netref, '__next__')()
        # print(f"WrapNetref next res {res}, {type(res)}")

        if isinstance(res, BaseNetref):
            return WrapNetref(res)
        return res

    @property
    def __class__(self):
        print("getting class")
        res = getattr(self._secret_netref, '__class__')
        return res


class GuiDataGateway(DataGateway):
    """Wrapper for DataGateway to use in a GUI application.
    
    Opens a message box if the connection to the dataserver fails
    and assures that the request returns something.
    
    !! This is not thread safe, make sure that this gateway is only
    used by a single thread !!"""

    def __getattr__(
            self,
            attr: str
    ):
        """Allow shorthand gateway.attribute for gateway.root.attribute"""
        if self._connection:
            try:
                res = getattr(self._connection.root, attr)
                
                if isinstance(res, BaseNetref):
                    print(f"req: {attr}, wrapping return type")
                    return WrapNetref(res)
                else:
                    return res

            except EOFError as e:
                # make sure the connection is closed
                self.disconnect()

                # loop until success
                while True:

                    # wait for connection to establish again
                    while not self.connected:
                        self.message_reconnect(e).exec()

                    # try operation again, if it fails again,
                    #   return to retrying
                    try: 
                        return getattr(self._connection.root, attr)
                    except EOFError as e:
                        pass
        else:
            # default python implementation
            self.__getattribute__(attr)


    def message_reconnect(self, e):

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle('Dataserver connection error')
        msg.setText('<p>{}</p>'.format(e))
        msg.setInformativeText('The gateway could not connect to the dataserver. Make sure that the dataserver is restarted and then click retry.')

        # msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Abort)
        msg.setStandardButtons(QMessageBox.Retry)

        msg.buttonClicked.connect(self.msgbtn)

        return msg

    def msgbtn(self, i):
        if i.text() == "Retry":
            try:
                self.connect()
            except Exception:
                pass



