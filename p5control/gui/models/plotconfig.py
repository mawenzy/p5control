import threading
import time
from collections.abc import MutableMapping

from qtpy.QtGui import QColor
from pyqtgraph import PlotDataItem

from ...gateway import DataGateway
from ..guisettings import DATA_BUFFER_MAX_LENGTH, DOWN_SAMPLE
from ..databuffer import DataBuffer
from ...util import name_generator, color_cycler

# generate unique ids for the plots
plot_id_generator = name_generator(
    "plot",
    width=4
)

# cycle through a set of colors
pen_colors = color_cycler()

class BasePlotConfig(MutableMapping):
    """
    Wrapper around a dictionary which holds the config for a single pyqtgraph.PlotDataItem
    """
    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        name: str = None,
        pen: QColor = None,
        symbolBrush=(255, 255, 255, 100),
        symbolPen=(255, 255, 255, 100),
        symbol: str = None,
        symbolSize: int = 5,
    ):
        self.dgw = dgw
        self._config = {}

        # set default values
        if name is None:
            name = path.split("/")[-1]

        if pen is None:
            pen = next(pen_colors)

        plotid = next(plot_id_generator)
        plotDataItem = PlotDataItem(
            name=plotid,
            pen=pen,
            symbolBrush=symbolBrush,
            symbolPen=symbolPen,
            symbol=symbol,
            symbolSize=symbolSize,
        )

        self._config = {
            "id": plotid,
            "lock": threading.Lock(),
            "plotDataItem": plotDataItem,
            "path": path,
            # settings
            "name": name,
            "pen": pen,
            "symbolBrush": symbolBrush,
            "symbolPen": symbolPen,
            "symbol": symbol,
            "symbolSize": symbolSize,
        }

        self._config["x"] = 0
        self._config["y"] = 1

    def __setitem__(self, key, value):
        self._config[key] = value

    def __getitem__(self, key):
        return self._config[key]

    def __delitem__(self, key):
        del self._config[key]

    def __iter__(self):
        return iter(self._config)

    def __len__(self):
        return len(self._config)

    def update(self):
        """
        Implement this function to update the plotDataItem
        """
        raise NotImplementedError()

    def cleanup(self):
        pass

class PlotConfig(BasePlotConfig):
    """
    Standard plot config
    """
    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        *args,
        **kwargs
    ):
        super().__init__(dgw, path, *args, **kwargs)

        node = dgw.get(path)
        attrs = node.attrs

        # databuffer settings
        attrs = node.attrs
        if "max_length" in attrs:
            self._config["max_length"] = int(attrs["max_length"])
        else:
            self._config["max_length"] = DATA_BUFFER_MAX_LENGTH
        if "down_sample" in attrs:
            self._config["down_sample"] = int(attrs["down_sample"])
        else:
            self._config["down_sample"] = DOWN_SAMPLE

        self._config["dataBuffer"] = DataBuffer(
            dgw,
            path,
            max_length=self._config["max_length"],
            down_sample=self._config["down_sample"]
        )

        compound_names = node.dtype.names
        ndim = node.shape

        # set defaults for x and y indexing
        if compound_names:
            if "time" in compound_names:
                self._config["x"] = "time"
                self._config["y"] = compound_names[0] if compound_names[0] != "time" else compound_names[1]
            else:
                self._config["x"] = compound_names[0]
                self._config["y"] = compound_names[1]
        else:
            if ndim[-1] <= 1:
                return
            self._config["x"] = 0
            self._config["y"] = 1

    def update(self):
        """
        Implement this function to update the plotDataItem
        """
        with self._config["lock"]:

            dataBuffer = self._config["dataBuffer"]
            plotDataItem = self._config["plotDataItem"]

            with dataBuffer.data_lock:
                xdata = dataBuffer.data[self._config["x"]]
                ydata = dataBuffer.data[self._config["y"]]

            plotDataItem.setData(
                (xdata - time.time()),
                ydata
            )

    def cleanup(self):
        self._config["dataBuffer"].cleanup()


class DsetMultPlotConfig(BasePlotConfig):
    """
    Plot config which subscribes to the parent group and plots incoming new datasets
    """
    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        *args,
        **kwargs
    ):
        super().__init__(dgw, path, *args, **kwargs)

        self.dgw = dgw

        self._config["data"] = self.dgw.get_data(path)

        node = dgw.get(path)
        parent_path = node.parent.name

        compound_names = node.dtype.names
        ndim = node.shape

        # set defaults for x and y indexing
        if compound_names:
            if "time" in compound_names:
                self._config["x"] = "time"
                self._config["y"] = compound_names[0] if compound_names[0] != "time" else compound_names[1]
            else:
                self._config["x"] = compound_names[0]
                self._config["y"] = compound_names[1]
        else:
            if ndim[-1] <= 1:
                return
            self._config["x"] = 0
            self._config["y"] = 1

        self.callid = self.dgw.register_callback(parent_path, self.callback, is_group=True)

    def callback(self, path):
        data = self.dgw.get_data(path)

        with self._config["lock"]:
            self._config["data"] = data

    def cleanup(self):
        self.dgw.remove_callback(self.callid)

    def update(self):
        with self._config["lock"]:
            data = self._config["data"]
            plotDataItem = self._config["plotDataItem"]

            plotDataItem.setData(
                data[self._config["x"]],
                data[self._config["y"]]
            )