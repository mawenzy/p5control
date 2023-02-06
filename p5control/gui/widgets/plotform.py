"""
This file provides a form to edit the config associated with a single
plotDataItem
"""
import h5py
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import QFormLayout, QWidget, QComboBox, QLineEdit
from qtpy.QtGui import QColor, QIntValidator

from pyqtgraph import ColorButton

from ...gateway import DataGateway


class PlotForm(QWidget):
    """Widget with QFormLayout which lets the user edit the config associated with a single
    `plotDataItem`.
    
    Parameters
    ----------
    dgw: DataGateway
        gateway to the data server
    *args, **kwargs
        passed to `super().__init__`
    """

    updatedConfig = Signal(str)
    """
    **Signal(str)** - emitted if the config is updated, provides the id
    """

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

        self.name = QLineEdit()
        self.xbox = QComboBox()
        self.ybox = QComboBox()
        self.pen = ColorButton()

        self.max_length = QLineEdit()
        self.max_length.setValidator(QIntValidator(1, 100000))
        self.down_sample = QLineEdit()
        self.down_sample.setValidator(QIntValidator(1, 100))

        layout = QFormLayout(self)

        layout.addRow("name", self.name)
        layout.addRow("x", self.xbox)
        layout.addRow("y", self.ybox)
        layout.addRow("pen", self.pen)
        layout.addRow("bufferLen", self.max_length)
        layout.addRow("down_sample", self.down_sample)

        # init signals
        self.name.editingFinished.connect(self._handle_name)
        self.xbox.activated.connect(self._handle_x)
        self.ybox.activated.connect(self._handle_y)
        self.pen.sigColorChanged.connect(self._handle_pen)
        self.max_length.editingFinished.connect(self._handle_max_length)
        self.down_sample.editingFinished.connect(self._handle_down_sample)

        self.clear()

    def clear(self):
        """Clear widget back to an emtpy state and disable widgets which should not be editable
        in this state."""
        self.name.clear()
        self.name.setEnabled(False)

        self.xbox.clear()
        self.ybox.clear()

        self.pen.setEnabled(False)
        self.pen.setColor(QColor("gray"))

        self.max_length.clear()
        self.max_length.setEnabled(False)

        self.down_sample.clear()
        self.down_sample.setEnabled(False)

        self.config = {}

    def set_config(self, config):
        """Put the widget in a state to allow the user the edit ``config``.
        
        Parameters
        ----------
        config : BasePlotConfig
            the config which the user should be able to edit.
        """
        if len(config) == 0:
            self.clear()
            return

        node = self.dgw.get(config["path"])

        if not isinstance(node, h5py.Dataset):
            return

        self.clear()
        self.config = config

        # now look at config an initialize the values. If values are not found, they are skipped
        # and the corresponding form element is hidden.

        if "name" in config:
            self.name.setText(config["name"])
            self.name.setEnabled(True)
            self.layout().setRowVisible(self.name, True)
        else:
            self.layout().setRowVisible(self.name, False)

        if "x" in config and "y" in config:
            #Note: Only works with compound_names for now
            compound_names = node.dtype.names

            self.xbox.addItems(compound_names)
            self.ybox.addItems(compound_names)

            self.xbox.setCurrentText(config["x"])
            self.ybox.setCurrentText(config["y"])

            self.layout().setRowVisible(self.xbox, True)
            self.layout().setRowVisible(self.ybox, True)
        else:
            self.layout().setRowVisible(self.xbox, False)
            self.layout().setRowVisible(self.ybox, False)

        if "pen" in config:
            self.pen.setColor(config["pen"])
            self.pen.setEnabled(True)
            self.layout().setRowVisible(self.pen, True)
        else:
            self.layout().setRowVisible(self.pen, False)

        if "max_length" in config:
            self.max_length.setText(str(config["dataBuffer"].max_length))
            self.max_length.setEnabled(True)
            self.layout().setRowVisible(self.max_length, True)
        else:
            self.layout().setRowVisible(self.max_length, False)

        if "down_sample" in config:
            self.down_sample.setText(str(config["dataBuffer"].down_sample))
            self.down_sample.setEnabled(True)
            self.layout().setRowVisible(self.down_sample, True)
        else:
            self.layout().setRowVisible(self.down_sample, False)

    @Slot(object)
    def _handle_pen(self, color: ColorButton):
        color = color.color()
        # the `sigColorChanged` is emitted when putting the widget in the clear state, but in that
        # case we do not want to actually do something
        if "lock" in self.config and self.pen.isEnabled():
            with self.config["lock"]:
                self.config["pen"] = color
                self.config["plotDataItem"].setPen(color)
            self.updatedConfig.emit(self.config["id"])

    @Slot()
    def _handle_name(self):
        text = self.name.text()
        with self.config["lock"]:
            self.config["name"] = text
        self.updatedConfig.emit(self.config["id"])

    @Slot()
    def _handle_max_length(self):
        text = self.max_length.text()
        with self.config["lock"]:
            self.config["dataBuffer"].reload(
                max_length = int(text)
            )
        self.updatedConfig.emit(self.config["id"])

    @Slot()
    def _handle_down_sample(self):
        text = self.down_sample.text()
        with self.config["lock"]:
            self.config["dataBuffer"].reload(
                down_sample = int(text)
            )
        self.updatedConfig.emit(self.config["id"])

    def _handle_x(self, index):
        text = self.xbox.itemText(index)
        with self.config["lock"]:
            self.config["x"] = text
        self.updatedConfig.emit(self.config["id"])

    def _handle_y(self, index):
        text = self.ybox.itemText(index)
        with self.config["lock"]:
            self.config["y"] = text
        self.updatedConfig.emit(self.config["id"])
