"""
This file defines the class :class:`.CleanupApp`, which subclasses ``QApplication`` with some
usefull additions. When the signal ``aboutToQuit`` is emitted, ``widget.cleanup()`` is called
for every widget, such that you can implement some custom functionality before the widget gets
destroyed, e.g. removing installed callbacks.
"""
import gc
import sys
import logging

from qtpy.QtWidgets import QApplication

from pyqtgraph import _connectCleanup, setConfigOption

logger = logging.getLogger(__name__)

class CleanupApp(QApplication):
    """
    Extends ``QApplication`` with some customization.

    Parameters
    ----------
    app_name : str = "p5control"
        app name to use
    """

    def __init__(
        self,
        app_name: str = 'p5control',
    ):
        super().__init__(sys.argv)

        self.setApplicationName(app_name)

        # make sure pyqtgraph gets cleaned up properly
        _connectCleanup()
        # enable plot antialiasing
        setConfigOption("antialias", True)
        setConfigOption("background", "w")
        setConfigOption("foreground", "k")

        self.aboutToQuit.connect(self.call_cleanup)

    def exec(self, *args, **kwargs):
        """
        Overwrites exec to explicitly call the garbage collector after the app
        has been closed and then logs any leaked_widgets.
        """
        super().exec(*args, **kwargs)
        # invoke garbage collector to make sure we don't get any false leak reports
        gc.collect()
        # report Qt leaks
        leaked_widgets = self.allWidgets()
        if leaked_widgets:
            leaked_str = f'Leaked {len(leaked_widgets)} Qt widgets:\n'
            for w in leaked_widgets:
                leaked_str += repr(w) + '\n'
            logger.debug(leaked_str)
        else:
            logger.debug('No Qt widgets leaked.')

    def call_cleanup(self):
        """
        Allows for last second cleanup when closing the gui. For all widgets, the
        method ``cleanup`` is called. This can as an example be use to remove callbacks
        when closing the gui.
        """
        for widget in self.allWidgets():
            try:
                widget.cleanup()
            except AttributeError:
                pass
