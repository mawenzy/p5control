"""
Simple GUI Application to view the contents of the data server 
"""
import sys
import logging

from qtpy.QtCore import (
    Qt,
    QTimer
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

from p5control.gui import (
    CleanupApp,
    GuiDataGateway,
    DataGatewayTreeView,
    ExtendableAttributesTableView,
    DatasetPropertiesTableView,
    DatasetTableView
)

logging.basicConfig(
    level=logging.DEBUG,
    filename="viewer.log",
    filemode="w"
)


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
        self.dataset_dock.hide()

        # add dock widgets
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tree_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.attrs_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dataset_dock)

        self.view_menu.addActions([
            self.tree_dock.toggleViewAction(),
            self.attrs_dock.toggleViewAction(),
            self.dataset_dock.toggleViewAction()
        ])

    def init_signals(self):
        """
        Initialize signals
        """
        self.tree_view.selected.connect(self.attrs_view.update_node)
        self.tree_view.selected.connect(self.dataset_view.update_node)
        self.tree_view.selected.connect(self.data_view.update_node)

    def handle_refresh(self):
        self.tree_view.update_data()


if __name__ == "__main__":
    with GuiDataGateway(allow_callback=True) as dgw:

        app = CleanupApp()
        app.setOrganizationName('p5control-team')
        app.setApplicationName('Data server viewer')

        window = ViewerMainWindow(app, dgw)
        window.show()

        sys.exit(app.exec())