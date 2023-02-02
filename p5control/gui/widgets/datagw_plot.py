"""
This module provides a plot widget, which consists out of a `pyqtgraph` `PlotWidget` with an added
external legend. Each line is represented by a config dictionary, which is automatically generated
from the attributes of the dataset and can be edited with :class:`PlotForm`

Plot config
-----------

* **id** (``str``)
    Unique id for this config.
* **lock** (``threading.Lock``)
    Acquire this lock when making changes to the config or objects references within.
* **plotDataItem** (``pyqtgraph.PlotDataItem``)
    the actual item which is plotted in the `PlotWidget`.
* **path** (``str``)
    hdf5 path of the dataset to plot

to be continued...
"""
import threading

import h5py
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import QSplitter, QHBoxLayout, QWidget, QCheckBox, QVBoxLayout
from qtpy.QtGui import QDragEnterEvent, QDropEvent
from pyqtgraph import PlotWidget

from .legend import LegendView
from .plotform import PlotForm
from ..models import PlotConfig, DsetMultPlotConfig

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
        # self.plot_widget.setLimits(xMax=0)
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
        self.legend.selected.connect(self._on_legend_selected)

        # layout + buttons
        if showButtons:
            self.btn_update = QCheckBox("Update time", self)
            self.btn_update.setChecked(True)

            self.btn_legend = QCheckBox("Legend", self)
            self.btn_legend.setChecked(showLegend)
            self.btn_legend.stateChanged.connect(self._on_legend_checkbox_changed)

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
    def _on_legend_checkbox_changed(self, state:int):
        if state == 2:
            # checked
            self.legend.setVisible(True)
        else:
            self.legend.setVisible(False)

    @Slot(str)
    def _on_legend_selected(self, plotid:str):
        for plot in self.plots:
            if plot["id"] == plotid:
                self.selectedConfig.emit(plot)
                return

        if plotid == "":
            self.selectedConfig.emit({})

    def add_plot(
        self,
        path: str,
        *args,
        **kwargs
    ):
        """
        Add new plot from the dataset at ``path``.

        Parameters
        ----------
        path : str
            hdf5 path to plot
        *args, **kwargs
            see :class:`PlotConfig` for options which can be used.
        """
        node = self.dgw.get(path)
        config = None
        if "plotConfig" in node.attrs:
            plotConfig = node.attrs["plotConfig"]

            if plotConfig == "dset_mult":
                config = DsetMultPlotConfig(self.dgw, path, *args, **kwargs)

        if config is None:
            config = PlotConfig(self.dgw, path, *args, **kwargs)

        with self.lock:
            self.plot_widget.addItem(config["plotDataItem"])
            self.plots.append(config)
            self.legend.addItem(config)

    @Slot(str)
    def remove_plot(
        self,
        plotid: str
    ):
        """
        Remove plot by its id.

        Parameters
        ----------
        plotid : str
            unique id of the plot config.
        """
        index = None
        with self.lock:
            for i, config in enumerate(self.plots):
                if config["id"] == plotid:
                    index = i
                    break

            if index is not None:

                if config["plotDataItem"] in self.plot_widget.listDataItems():
                    self.plot_widget.removeItem(config["plotDataItem"])

                self.legend.removeItem(plotid)

                lock = config["lock"]

                with lock:
                    del self.plots[index]


    def update(self):
        if not self.btn_update.isChecked():
            return

        with self.lock:
            for config in self.plots:
                config.update()

    def cleanup(self):
        with self.lock:
            for config in self.plots:
                config.cleanup()

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