"""
Simple GUI Application to view the contents of the data server 
"""
import sys

from qtpy.QtCore import (
    Qt,
    Slot
)

from qtpy.QtWidgets import (
    QMainWindow,
    QApplication,
    QDockWidget,
    QAction
)

from qtpy.QtGui import (
    QKeySequence
)

from .cleanupapp import CleanupApp
from .guidatagw import GuiDataGateway
from .widgets import (
    DataGatewayTreeView,
    ExtendableAttributesTableView,
    DatasetPropertiesTableView,
    DatasetTableView,
    DatasetDimsTableView
)

# import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(
#     filename='client.log',
#     level=logging.DEBUG,
#     filemode='w', # overwrites logs every time this script is started
#     format='%(asctime)s.%(msecs)03d %(levelname)-8s %(thread)6d %(name)-30s '
#            '%(funcName)-20s %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
# )


class ViewerMainWindow(QMainWindow):
    """Main Window, holds the individual elements in docks"""

    def __init__(
        self,
        app: QApplication,
        dgw: GuiDataGateway
    ):
        super().__init__()

        self.app = app
        self.dgw = dgw

        self.init_menus()
        self.init_widgets()
        self.init_docks()
        self.init_signals()

    def init_menus(self):
        """
        Initialize menus
        """
        menu = self.menuBar()

        # file menu
        self.file_menu = menu.addMenu('&File')

        self.file_menu.addAction(QAction(
            "Refresh",
            self,
            shortcut=QKeySequence.Refresh,
            statusTip='Refresh Folder View',
            triggered=self.handle_refresh
        ))

        # view menu
        self.view_menu = menu.addMenu('&View')

    def init_widgets(self):
        """
        Initialize widgets
        """
        self.tree_view = DataGatewayTreeView(self.dgw)
        self.attrs_view = ExtendableAttributesTableView(self.dgw)
        self.dataset_view = DatasetPropertiesTableView(self.dgw)
        self.dims_view = DatasetDimsTableView(self.dgw)
        
        self.data_view = DatasetTableView(self.dgw)
        self.setCentralWidget(self.data_view)

    def init_docks(self):
        """
        Initialize docks
        """
        MIN_DOCK_WIDTH = 240

        self.tree_dock = QDockWidget('Data structure', self)
        self.tree_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.tree_dock.setWidget(self.tree_view)

        self.attrs_dock = QDockWidget('Attributes', self)
        self.attrs_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.attrs_dock.setWidget(self.attrs_view)

        self.dataset_dock = QDockWidget('Dataset', self)
        self.dataset_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.dataset_dock.setWidget(self.dataset_view)
        # self.dataset_dock.hide()

        self.dims_dock = QDockWidget('Dimensions', self)
        self.dims_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.dims_dock.setWidget(self.dims_view)

        # add dock widgets
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tree_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.attrs_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dataset_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dims_dock)

        self.view_menu.addActions([
            self.tree_dock.toggleViewAction(),
            self.attrs_dock.toggleViewAction(),
            self.dataset_dock.toggleViewAction(),
            self.dims_dock.toggleViewAction(),
        ])

    def init_signals(self):
        """
        Initialize signals
        """
        self.tree_view.selected.connect(self.handle_treeview_selection_changed)

        self.dims_view.dimsChanged.connect(self.data_view.update_dims)

    def handle_refresh(self):
        self.tree_view.update_data()

    @Slot(str)
    def handle_treeview_selection_changed(self, path):

        self.attrs_view.update_node(path)
        self.dataset_view.update_node(path)
        self.data_view.update_node(path)
        self.dims_view.update_node(path)

        self.attrs_view.scrollToTop()
        self.dataset_view.scrollToTop()
        self.data_view.scrollToTop()
        self.dims_view.scrollToTop()


def main():
    """
    Viewer application entry point.
    """
    with GuiDataGateway(allow_callback=True) as dgw:

        app = CleanupApp()
        app.setOrganizationName('p5control-team')
        app.setApplicationName('Data server viewer')

        window = ViewerMainWindow(app, dgw)
        window.show()

        sys.exit(app.exec())

if __name__ == "__main__":
    main()
