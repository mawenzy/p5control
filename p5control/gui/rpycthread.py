"""
This module defines a QThread subclass, into which you should push worker objects that use rpyc
requests, such that these do not block the gui event loop.
"""

from typing import Optional

from qtpy.QtCore import QThread, QObject

class RPyCThread(QThread):
    """
    subclasses `QThread`, and deletes itself after it has finished. Use
    """
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.finished.connect(self.deleteLater)

rpyc_thread = RPyCThread()
"""
The thread instance which should handle calls to the rpyc servers which should not block the gui.
To move a worker to the thread, use:

.. code-block::py

    class Worker(QObject):

        finished = Signal(int)

        def calc(self):
            time.sleep(1)
            self.finished.emit(2)

    worker = SomeWorker()
    worker.moveToThread(rpyc_thread)

    request = Signal()

    request.connect(worker.calc)
    worker.finished.connect(lambda x: print(x))

Now every time you emit the request signal, the worker will do its work in the ``rpyc_thread`` and
then emit a signal if it has finished. Have a look at ``DataGatewayTreeModel`` to see it in action.
"""
