# setup logging
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='scheer2.log',
    level=logging.DEBUG,
    filemode='w', # overwrites logs every time this script is started
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

import sys

from qtpy.QtCore import (
    Qt,
    QTimer,
    Slot
)

from qtpy.QtWidgets import (
    QMainWindow,
    QApplication,
    QDockWidget,
    QTabWidget,
    QAction
)

from qtpy.QtGui import (
    QKeySequence
)

from p5control import (
    InstrumentGateway
)

from p5control.gui import (
    CleanupApp,
    GuiDataGateway,
    DataGatewayTreeView,
    ValueBoxForm,
    PlotForm,
    DataGatewayPlot,
)

class Scheer2MainWindow(QMainWindow):
    
    def __init__(
        self,
        app: QApplication,
        dgw: GuiDataGateway,
        gw: InstrumentGateway
    ):
        super().__init__()

        self.app = app
        self.dgw = dgw
        self.gw = gw

        self.init_actions()
        self.init_menus()
        self.init_toolbars()
        self.init_statusbar()
        self.init_widgets()
        self.init_docks()
        self.init_signals()

    def init_actions(self):
        """
        Initialize actions
        """
        pass

    def init_menus(self):
        """
        Initialize actions
        """
        menu = self.menuBar()

        # file menu
        self.file_menu = menu.addMenu('&File')

        self.file_menu.addAction(QAction(
            "Refresh",
            self,
            shortcut=QKeySequence.Refresh,
            statusTip='Refresh TreeView',
            triggered=self.handle_refresh
        ))

        # view menu
        self.view_menu = menu.addMenu('&View')

        # plot menu
        self.plot_menu = menu.addMenu('&Plot')

        self.plot_menu.addAction(QAction(
            "Add plot",
            self,
            statusTip='Add Tab with new plot',
            triggered=self.handle_add_plot
        ))

    def init_toolbars(self):
        """
        Initialize toolbars
        """
        pass

    def init_statusbar(self):
        """
        Initialize statusbar
        """
        pass

    def init_widgets(self):
        """
        Initialize widgets
        """
        self.tree_view = DataGatewayTreeView(self.dgw)
        self.tree_view.expandAll()

        self.form_view = ValueBoxForm(dgw, [
            ('inst1<sub>ampl</sub>', '/status/inst1', "ampl", gw.inst1.setAmplitude),
            ('inst1<sub>freq</sub>', '/status/inst1', "freq", gw.inst1.setFrequency),
            ('inst2<sub>ampl</sub>', '/status/inst2', "ampl", gw.inst2.setAmplitude)
        ])

        self.plot_form = PlotForm(self.dgw)

        self.tabs = QTabWidget()

        plot_view = DataGatewayPlot(self.dgw)
        plot_view.connectPlotForm(self.plot_form)

        self.tabs.addTab(plot_view, 'Plot 1')

        self.setCentralWidget(self.tabs)

    def init_docks(self):
        """
        Initialize docks
        """
        MIN_DOCK_WIDTH = 240

        self.tree_dock = QDockWidget('Data structure', self)
        self.tree_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.tree_dock.setWidget(self.tree_view)

        self.form_dock = QDockWidget('ValueBoxForm', self)
        self.form_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.form_dock.setWidget(self.form_view)

        self.plot_form_dock = QDockWidget('Plot config', self)
        self.plot_form_dock.setMinimumWidth(MIN_DOCK_WIDTH)
        self.plot_form_dock.setWidget(self.plot_form)

        # add dock widgets
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tree_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.form_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.plot_form_dock)

        self.view_menu.addActions([
            self.tree_dock.toggleViewAction(),
            self.form_dock.toggleViewAction(),
            self.plot_form_dock.toggleViewAction()
        ])

    def init_signals(self):
        """
        Initialize signals
        """
        self.tree_view.doubleClickedDataset.connect(self.handle_tree_view_double_click)
    
        self.tabs.tabCloseRequested.connect(self.handle_tab_close)
        self.tabs.currentChanged.connect(self.handle_tab_current_changed)

    @Slot(str)
    def handle_tree_view_double_click(self, path: str):
        self.tabs.currentWidget().add_plot(path)

    @Slot()
    def handle_refresh(self):
        self.tree_view.update_data()

    @Slot()
    def handle_add_plot(self):
        """
        Add a new plot in a tab. Makes them closable
        """
        plot_view = DataGatewayPlot(self.dgw)
        plot_view.connectPlotForm(self.plot_form)

        self.tabs.addTab(plot_view, f"Plot {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

        self.tabs.setTabsClosable(True)

    @Slot(int)
    def handle_tab_close(self, index: int):
        """
        Close tab at index. If only one is remaining, makes it no longer closable
        """
        plot_view = self.tabs.widget(index)
        self.tabs.removeTab(index)
        plot_view.deleteLater()

        if self.tabs.count() == 1:
            self.tabs.setTabsClosable(False)

        # rename plots
        for i in range(self.tabs.count()):
            self.tabs.setTabText(i, f"Plot {i + 1}")

    @Slot(int)
    def handle_tab_current_changed(self, index: int):
        self.plot_form.clear()

        # set plot_form to the config if one is selected
        # in the legend
        legend = self.tabs.currentWidget().legend
        rows = legend.selectionModel().selectedRows()
        
        if len(rows) > 0:
            index = rows[0]
            item = legend.model().itemFromIndex(index)

            itemid = item.data(Qt.UserRole)
            legend.selected.emit(itemid)

    def update(self):
        self.tabs.currentWidget().update()


if __name__ == '__main__':
    with GuiDataGateway(allow_callback=True) as dgw, InstrumentGateway() as gw:

        app = CleanupApp()
        app.setOrganizationName('Scheer2-team')
        app.setApplicationName('Scheer2 GUI')

        window = Scheer2MainWindow(app, dgw, gw)
        window.show()

        timer = QTimer()
        timer.timeout.connect(window.update)
        timer.start(30)

        sys.exit(app.exec())