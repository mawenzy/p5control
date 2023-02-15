"""
This file provides a form to edit the config associated with a single
plotDataItem
"""
import h5py
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import QFormLayout, QWidget, QComboBox, QLineEdit, QCheckBox
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

    IGNORE_KEYS = ['plotDataItem', 'id', 'lock', 'dataBuffer', 'path', 'symbol', 'symbolBrush',
                   'symbolPen', 'symbolSize', 'data', 'x_data']
    """
    List of keys in config which should be ignored in this form
    """

    def __init__(
        self,
        dgw: DataGateway,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.dgw = dgw

        self.config = {}
        self.node = None

        self._widget_pen = ColorButton()

        self.max_length = QLineEdit()
        self.max_length.setValidator(QIntValidator(1, 100000))
        self.down_sample = QLineEdit()
        self.down_sample.setValidator(QIntValidator(1, 100))

        layout = QFormLayout(self)

        self.get_widget("name", "")

        self._widget_x = QComboBox()
        self._widget_x.activated.connect(self._handle_x)
        layout.addRow("x", self._widget_x)

        self._widget_y = QComboBox()
        self._widget_y.activated.connect(self._handle_y)
        layout.addRow("y", self._widget_y)

        layout.addRow("pen", self._widget_pen)
        self._widget_pen.sigColorChanged.connect(self._handle_pen)
        
        self.get_widget("max_length", 1, label="buffer_length")
        self.get_widget("down_sample", 1, label="buffer_sample")

        self.clear()

    def clear(self):
        """Clear widget back to an emtpy state and disable widgets which should not be editable
        in this state."""
        self._widget_name.clear()
        self._widget_name.setEnabled(False)

        self._widget_x.clear()
        self._widget_y.clear()

        self._widget_pen.setEnabled(False)
        self._widget_pen.setColor(QColor("gray"))

        self._widget_max_length.clear()
        self._widget_max_length.setEnabled(False)

        self._widget_down_sample.clear()
        self._widget_down_sample.setEnabled(False)

        self.config = {}
        self.node = None


    def set_config(self, config):
        """Put the widget in a state to allow the user the edit ``config``.
        
        Parameters
        ----------
        config : BasePlotConfig
            the config which the user should be able to edit. At a minimum, this needs to contain
            the keys 'path', 'lock' and 'id'
        """
        if len(config) == 0:
            self.clear()
            return

        node = self.dgw.get(config["path"])

        if not isinstance(node, h5py.Dataset):
            return

        self.clear()
        self.config = config
        self.node = node

        for i in range(self.layout().rowCount()):
            self.layout().setRowVisible(i, False)

        # now look at config an initialize the values. If values are not found, they are skipped
        # and the corresponding form element is hidden.

        for (key, value) in config.items():
            if key in self.IGNORE_KEYS:
                continue

            widget = self.get_widget(key, value)

            if widget:
                try:
                    getattr(self, f'_update_{key}')(value)
                except AttributeError:
                    self._update_value(widget, value)
                self.layout().setRowVisible(widget, True)

    def get_widget(self, key, value, label=None):
        try:
            return getattr(self, f'_widget_{key}')
        except AttributeError:
            if isinstance(value, bool):
                # needs to be before int beause bool subclasses int
                widget = QCheckBox()
                if label:
                    self.layout().addRow(label, widget)
                else:
                    self.layout().addRow(key, widget)

                setattr(widget, '_get_value', widget.isChecked)
                setattr(self, f'_widget_{key}', widget)

                widget.stateChanged.connect(lambda: getattr(self, f"_handle_{key}"))
                return widget

            elif isinstance(value, str):
                widget = QLineEdit()
                if label:
                    self.layout().addRow(label, widget)
                else:
                    self.layout().addRow(key, widget)

                setattr(widget, '_get_value', getattr(widget, 'text'))
                setattr(self, f'_widget_{key}', widget)

                widget.editingFinished.connect(lambda: getattr(self, f"_handle_{key}"))
                return widget

            elif isinstance(value, int):
                widget = QLineEdit()
                widget.setValidator(QIntValidator(1, 100000))
                if label:
                    self.layout().addRow(label, widget)
                else:
                    self.layout().addRow(key, widget)

                setattr(widget, '_get_value', lambda: int(getattr(widget, 'text')()))
                setattr(self, f'_widget_{key}', widget)

                widget.editingFinished.connect(lambda: getattr(self, f"_handle_{key}"))
                return widget

            print(f"skipping {key} : {value}")

        return None

    def _update_value(self, widget, value):
        getattr(self, f"_update_{value.__class__.__name__}")(widget, value)

    def _update_str(self, widget, value):
        widget.setText(value)
        widget.setEnabled(True)
        self.layout().setRowVisible(widget, True)

    def _update_int(self, widget, value):
        widget.setText(str(value))
        widget.setEnabled(True)
        self.layout().setRowVisible(widget, True)

    def _update_bool(self, widget, value):
        widget.setChecked(value)
        widget.setEnabled(True)
        self.layout().setRowVisible(widget, True)

    def _update_pen(self, value):
        self._widget_pen.setColor(value)
        self._widget_pen.setEnabled(True)
        self.layout().setRowVisible(self._widget_pen, True)

    def _update_x(self, value):
        #Note: Only works with compound_names for now
        compound_names = self.node.dtype.names

        self._widget_x.addItems(compound_names)
        self._widget_x.setCurrentText(value)
        self.layout().setRowVisible(self._widget_x, True)

    def _update_y(self, value):
        #Note: Only works with compound_names for now
        compound_names = self.node.dtype.names

        self._widget_y.addItems(compound_names)
        self._widget_y.setCurrentText(value)
        self.layout().setRowVisible(self._widget_y, True)

    def __getattr__(self, attr):
        if attr.startswith("_handle_"):
            key = attr[8:]
            widget = getattr(self, f"_widget_{key}")
            value = widget._get_value()
            with self.config["lock"]:
                self.config[key] = value
            self.config.config_update()
            self.updatedConfig.emit(self.config["id"])
        else:
            return self.__getattribute__(attr)

    @Slot(object)
    def _handle_pen(self, color: ColorButton):
        color = color.color()
        # the `sigColorChanged` is emitted when putting the widget in the clear state, but in that
        # case we do not want to actually do something
        if "lock" in self.config and self._widget_pen.isEnabled():
            with self.config["lock"]:
                self.config["pen"] = color
                self.config["plotDataItem"].setPen(color)
            self.updatedConfig.emit(self.config["id"])

    def _handle_x(self, index):
        text = self._widget_x.itemText(index)
        with self.config["lock"]:
            self.config["x"] = text
        self.updatedConfig.emit(self.config["id"])

    def _handle_y(self, index):
        text = self._widget_y.itemText(index)
        with self.config["lock"]:
            self.config["y"] = text
        self.updatedConfig.emit(self.config["id"])
