import threading
import time

import h5py
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import QWidget, QHBoxLayout
from qtpy.QtGui import QDragEnterEvent, QDropEvent, QColor
from pyqtgraph import PlotWidget, mkColor, mkPen

from .legend import LegendView
from ..databuffer import DataBuffer
from ...util import name_generator, color_cycler

# generate unique ids for the plots
plot_id_generator = name_generator(
    "plot",
    width=4
)

# cycle through a set of colors
pen_colors = color_cycler() 


class DataGatewayPlot(QWidget):

    selectedConfig = Signal(dict)
    """emitted if a plot is selected, provides the config dictionary"""

    def __init__(self, dgw):
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

        # signals
        self.legend.deleteRequested.connect(self.remove_plot)
        self.legend.selected.connect(self._onLegendSelected)

        # layout
        layout = QHBoxLayout()
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.legend)
        self.setLayout(layout)

        # drag and drop support
        self.setAcceptDrops(True)

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
            name = path

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