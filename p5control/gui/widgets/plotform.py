import h5py
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QFormLayout, QWidget, QComboBox

from ...gateway import DataGateway


class PlotForm(QWidget):

    def __init__(
        self,
        dgw: DataGateway,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self.dgw = dgw

        self.node = None
        self.config = {}

        layout = QFormLayout()

        self.xbox = QComboBox()
        self.ybox = QComboBox()

        layout.addRow("x", self.xbox)
        layout.addRow("y", self.ybox)

        self.setLayout(layout)

        # init signal
        self.xbox.activated.connect(self._onXBoxActivated)
        self.ybox.activated.connect(self._onYBoxActivated)

    def _onXBoxActivated(self, index):
        text = self.xbox.itemText(index)
        with self.config["lock"]:
            self.config["x"] = text

    def _onYBoxActivated(self, index):
        text = self.ybox.itemText(index)
        with self.config["lock"]:
            self.config["y"] = text

    def clear(self):
        self.xbox.clear()
        self.ybox.clear()

        self.config = None


    def set_config(self, config):
        if len(config) == 0:
            self.clear()
            return

        node = self.dgw.get(config["path"])

        if not isinstance(node, h5py.Dataset):
            return

        self.clear()
        self.config = config

        compound_names = node.dtype.names
        shape = node.shape
        

        if compound_names:
            self.xbox.addItems(compound_names)
            self.ybox.addItems(compound_names)

            self.xbox.setCurrentText(config["x"])
            self.ybox.setCurrentText(config["y"])

        else:
            # TODO
            pass
