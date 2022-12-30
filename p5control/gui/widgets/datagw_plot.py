import threading
import time

import numpy as np
import h5py

from qtpy.QtCore import QSemaphore, Signal
from qtpy.QtWidgets import QHBoxLayout, QWidget
from qtpy.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent, QDragLeaveEvent

from pyqtgraph import PlotWidget, mkColor, mkPen

from .legend import LegendListView


class CustomPlotWidget(QWidget):

    new_data = Signal(str)

    def __init__(self, dgw):
        super().__init__()

        self.dgw = dgw

        self.plots = {}
        self.lock = threading.Lock()

        # plot
        self.plot_widget = PlotWidget()
        self.plot_widget.setClipToView(True)
        self.plot_widget.setLimits(xMax=0)
        self.plot_widget.setRange(xRange=[-100, 0])
        self.plot_widget.setLabel('bottom','Time', 's')

        # legend
        self.legend = LegendListView(customContextMenu=True, dragEnabled=True)
        self.legend.connectToPlotItem(self.plot_widget.plotItem)

        # layout
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.plot_widget)
        self.layout.addWidget(self.legend)
        self.setLayout(self.layout)

        self.new_data.connect(self._process_data)

        self.setAcceptDrops(True)

    def add_dataset(self, path):
        with self.lock:
            name = path.split("/")[-1]

            # if name in self.plots:
            if path in self.plots:
                print(f"Plot with name {name} already exists, skipping..")
                return

            # self.add_plot(name)
            # self.plots[name]['path'] = path
            self.add_plot(path)
            self.plots[path]['path'] = path

    def add_plot(self, name):
        plt = self.plot_widget.plot(name=name, pen=mkPen(mkColor('k')))
        self.plots[name] = {
            'x': [],
            'y': [],
            'plt': plt,
            'sem': QSemaphore(n=1)
        }

    def remove_plot(self, name):
        if name not in self.plots:
            raise ValueError(f'A plot with the name [{name}] does not exist.')
        # acquire the semaphore to make it isn't currently plotting
        sem = self.plots[name]['sem']
        sem.acquire()
        # check again in case the plot was just deleted
        if name not in self.plots:
            raise ValueError(f'A plot with the name [{name}] does not exist.')
        plt = self.plots[name]['plot']
        if plt in self.plot_widget.listDataItems():
            self.plot_widget.removeItem(plt)
        del self.plots[name]
        sem.release()

    def set_data(self, name: str, xdata, ydata):

        self.plots[name]['sem'].acquire()
        self.plots[name]['x'] = xdata
        self.plots[name]['y'] = ydata
        
        self.new_data.emit(name)

    def _process_data(self, name):
        try:
            self.plots[name]['plt'].setData(
                self.plots[name]['x'], self.plots[name]['y']
            )
        except Exception as exc:
            raise exc
        finally:
            self.plots[name]['sem'].release()

    def update(self):
        with self.lock:
            for plot_name in self.plots:
                path = self.plots[plot_name]['path']

                data = np.rollaxis(self.dgw.get_dataset_slice(path, slice(-1000, None)), axis=1)

                self.set_data(plot_name, (data[0] - time.time()), data[1])
        
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
                    self.add_dataset(path)
                    return
            except KeyError:
                pass

        e.ignore()

    # def dragLeaveEvent(self, e: QDragLeaveEvent) -> None:
    #     print("dragLeaveEvent")
    #     return super().dragLeaveEvent(e)

    # def dragMoveEvent(self, e: QDragMoveEvent) -> None:
    #     print("dragMoveEvent")
    #     return super().dragMoveEvent(e)