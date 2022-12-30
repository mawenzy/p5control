import gc
import sys
import logging

from qtpy.QtWidgets import QApplication

from pyqtgraph import _connectCleanup, setConfigOption

logger = logging.getLogger(__name__)

class CleanupApp(QApplication):

    def __init__(
        self,
        app_name: str = 'pycontrol',
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
        """last second cleanup. Implement cleanup for a widget to make use of it."""
        for widget in self.allWidgets():
            try:
                widget.cleanup()
            except AttributeError:
                pass