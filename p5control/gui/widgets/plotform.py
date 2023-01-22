import h5py
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import QFormLayout, QWidget, QComboBox, QLineEdit
from qtpy.QtGui import QColor

from pyqtgraph import ColorButton

from ...gateway import DataGateway


class PlotForm(QWidget):

    updatedConfig = Signal(str)
    """emitted if the config is updated, provides the config dict"""

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

        self.name = QLineEdit()
        self.xbox = QComboBox()
        self.ybox = QComboBox()
        self.pen = ColorButton()

        layout.addRow("name", self.name)
        layout.addRow("x", self.xbox)
        layout.addRow("y", self.ybox)
        layout.addRow("pen", self.pen)

        self.setLayout(layout)

        # init signals
        self.name.editingFinished.connect(self._onNameEditFinished)
        self.xbox.activated.connect(self._onXBoxActivated)
        self.ybox.activated.connect(self._onYBoxActivated)
        self.pen.sigColorChanged.connect(self._onPenChanged)

        self.clear()

    def clear(self):
        """Clear widget back to an emtpy state and disable widgets
        which should not be editable in this state."""
        self.name.clear()
        self.name.setEnabled(False)

        self.xbox.clear()
        self.ybox.clear()

        self.pen.setEnabled(False)
        self.pen.setColor(QColor("gray"))

        self.config = {}

    @Slot(object)
    def _onPenChanged(self, color: ColorButton):
        color = color.color()

        if "lock" in self.config and self.pen.isEnabled():
            with self.config["lock"]:
                self.config["pen"] = color
                self.config["plotDataItem"].setPen(color)
            # self.updatedConfig.emit(self.config)
            self.updatedConfig.emit(self.config["id"])


    @Slot()
    def _onNameEditFinished(self):
        text = self.name.text()
        with self.config["lock"]:
            self.config["name"] = text
        # self.updatedConfig.emit(self.config)
        self.updatedConfig.emit(self.config["id"])

    def _onXBoxActivated(self, index):
        text = self.xbox.itemText(index)
        with self.config["lock"]:
            self.config["x"] = text
        # self.updatedConfig.emit(self.config)
        self.updatedConfig.emit(self.config["id"])

    def _onYBoxActivated(self, index):
        text = self.ybox.itemText(index)
        with self.config["lock"]:
            self.config["y"] = text
        # self.updatedConfig.emit(self.config)
        self.updatedConfig.emit(self.config["id"])


    def set_config(self, config):
        if len(config) == 0:
            self.clear()
            return

        node = self.dgw.get(config["path"])

        if not isinstance(node, h5py.Dataset):
            return

        self.clear()
        self.config = config

        # name
        self.name.setText(config["name"])
        self.name.setEnabled(True)

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

        # pen
        self.pen.setColor(config["pen"])
        self.pen.setEnabled(True)
