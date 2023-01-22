import sys

from qtpy.QtCore import (
    Qt,
    QTimer
)

from qtpy.QtWidgets import (
    QMainWindow,
    QApplication,
    QDockWidget
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

        # view menu
        self.view_menu = menu.addMenu('&View')

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

        # self.plot_view = CustomPlotWidget(self.dgw)
        self.plot_view = DataGatewayPlot(self.dgw)

        self.setCentralWidget(self.plot_view)

        self.form_view = ValueBoxForm(dgw, [
            ('inst1<sub>ampl</sub>', '/status/inst1', "ampl", gw.inst1.setAmplitude),
            ('inst1<sub>freq</sub>', '/status/inst1', "freq"),
            ('inst2<sub>ampl</sub>', '/status/inst2', "ampl", gw.inst2.setAmplitude)
        ])

        self.plot_form = PlotForm(self.dgw)

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
        self.tree_view.doubleClickedDataset.connect(self.plot_view.add_plot)
        self.plot_view.selectedConfig.connect(self.plot_form.set_config)




    def update(self):
        self.plot_view.update()



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