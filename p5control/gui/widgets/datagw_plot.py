import threading
import time

import h5py
from qtpy.QtCore import Slot, Signal, Qt
from qtpy.QtWidgets import QSplitter, QHBoxLayout, QWidget, QCheckBox, QVBoxLayout
from qtpy.QtGui import QDragEnterEvent, QDropEvent, QColor
from pyqtgraph import PlotWidget

from .legend import LegendView
from .plotform import PlotForm
from ..databuffer import DataBuffer
from ...util import name_generator, color_cycler

# generate unique ids for the plots
plot_id_generator = name_generator(
    "plot",
    width=4
)

# cycle through a set of colors
pen_colors = color_cycler() 


class DataGatewayPlot(QSplitter):

    selectedConfig = Signal(dict)
    """emitted if a plot is selected, provides the config dictionary"""

    def __init__(
        self,
        dgw,
        showLegend=True,
        showButtons=True,
    ):
        super().__init__()

        self.dgw = dgw

        self.plots = []
        self.lock = threading.Lock()

        # plot 
        self.plot_widget = PlotWidget()
        self.plot_widget.setClipToView(True)
        self.plot_widget.setLimits(xMax=0)
        self.plot_widget.setRange(xRange=[-100, 0])
        self.plot_widget.setLabel('bottom', 'Time', 's')

        # legend
        self.legend = LegendView(
            customContextMenu=True,
            dragEnabled=True)

        if not showLegend:
            self.legend.hide()

        # signals
        self.legend.deleteRequested.connect(self.remove_plot)
        self.legend.selected.connect(self._onLegendSelected)

        # layout + buttons
        if showButtons:
            self.btn_update = QCheckBox("Update time", self)
            self.btn_update.setChecked(True)

            self.btn_legend = QCheckBox("Legend", self)
            self.btn_legend.setChecked(showLegend)
            self.btn_legend.stateChanged.connect(self._onLegendCheckboxChanged)

            buttonLayout = QHBoxLayout()
            buttonLayout.addWidget(self.btn_update)
            buttonLayout.addWidget(self.btn_legend)
            buttonLayout.addStretch()
            buttonLayout.setContentsMargins(4, 4, 4, 4)

            buttonRow = QWidget()
            buttonRow.setLayout(buttonLayout)

            plotboxLayout = QVBoxLayout()
            plotboxLayout.setContentsMargins(0, 0, 0, 0)
            plotboxLayout.addWidget(self.plot_widget)
            plotboxLayout.addWidget(buttonRow)

            plotbox = QWidget()
            plotbox.setLayout(plotboxLayout)

            self.addWidget(plotbox)
        else:
            self.addWidget(self.plot_widget)
        self.addWidget(self.legend)

        # drag and drop support
        self.setAcceptDrops(True)

    @Slot(int)
    def _onLegendCheckboxChanged(self, state:int):
        if state == 2:
            # checked
            self.legend.setVisible(True)
        else:
            self.legend.setVisible(False)

    @Slot(str)
    def _onLegendSelected(self, id:str):
        for plot in self.plots:
            if plot["id"] == id:
                self.selectedConfig.emit(plot)
                return

        if id == "":
            self.selectedConfig.emit({})

    @Slot(str)
    def add_plot(
        self,
        path: str,    
        name: str = None,
        pen: QColor = None,
        symbolBrush=(255, 255, 255, 100),
        symbolPen=(255, 255, 255, 100),
        symbol: str = None,
        symbolSize: int = 5,
    ):
        """
        Add new plot from the dataset at ``path``.
        """
        node = self.dgw.get(path)

        if not isinstance(node, h5py.Dataset):
            return

        # set default values
        if name is None:
            name = path.split("/")[-1]

        if pen is None:
            pen = next(pen_colors)

        compound_names = node.dtype.names
        ndim = node.shape

        with self.lock:
            id = next(plot_id_generator)
            plotDataItem = self.plot_widget.plot(
                name=id,
                pen=pen,
                symbolBrush=symbolBrush,
                symbolPen=symbolPen,
                symbol=symbol,
                symbolSize=symbolSize,
            )

            config = {
                "id": id,
                "lock": threading.Lock(),
                "plotDataItem": plotDataItem,
                "path": path,
                "dataBuffer": DataBuffer(self.dgw, path),
                # settings
                "name": name,
                "pen": pen,
                "symbolBrush": symbolBrush,
                "symbolPen": symbolPen,
                "symbol": symbol,
                "symbolSize": symbolSize,
            }

            # set defaults for x and y indexing
            if compound_names:
                if "time" in compound_names:
                    config["x"] = "time"
                    config["y"] = compound_names[0] if compound_names[0] != "time" else compound_names[1]
                else:
                    config["x"] = compound_names[0]
                    config["y"] = compound_names[1]
            else:
                if ndim[-1] <= 1:
                    return
                config["x"] = 0
                config["y"] = 1

            self.plots.append(config)
            self.legend.addItem(config)

    @Slot(str)
    def remove_plot(self, id:str):

        index = None
        with self.lock:
            for i,config in enumerate(self.plots):
                if config["id"] == id:
                    index = i
                    break

            if index is not None:

                if config["plotDataItem"] in self.plot_widget.listDataItems():
                    self.plot_widget.removeItem(config["plotDataItem"])

                self.legend.removeItem(id)

                lock = config["lock"]

                with lock:
                    del self.plots[index]


    def update(self):
        if not self.btn_update.isChecked():
            return

        with self.lock:
            for config in self.plots:
                dataBuffer = config["dataBuffer"]
                plotDataItem = config["plotDataItem"]

                xdata = dataBuffer.data[config["x"]]
                ydata = dataBuffer.data[config["y"]]

                plotDataItem.setData(
                    (xdata - time.time()),
                    ydata
                )

    def cleanup(self):
        with self.lock:
            for config in self.plots:
                config["dataBuffer"].cleanup()

    def connectPlotForm(self, plotForm: PlotForm):
        """Convenience function to setup signal connections
        between legend, plotForm and self"""
        self.selectedConfig.connect(plotForm.set_config)
        plotForm.updatedConfig.connect(self.legend.updateItem)

    """
    Dragging support
    """
    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        """Accept event if the path in mimeData text refers to a dataset."""
        data = e.mimeData()

        if data.hasText():
            path = data.text()

            try:
                node = self.dgw.get(path)
                if isinstance(node, h5py.Dataset):
                    e.accept()
                    return
            except KeyError:
                pass
        
        e.ignore()

    def dropEvent(self, e: QDropEvent) -> None:
        """Try to add plot from path"""
        data = e.mimeData()

        if data.hasText():
            path = data.text()

            try:
                node = self.dgw.get(path)
                if isinstance(node, h5py.Dataset):
                    e.accept()
                    self.add_plot(path)
                    return
            except KeyError:
                pass

        e.ignore()