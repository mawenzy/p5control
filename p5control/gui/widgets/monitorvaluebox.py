from typing import Union

from rpyc.utils.classic import obtain

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDoubleSpinBox, QAbstractSpinBox

from ...gateway import DataGateway

class MonitorValueBox(QDoubleSpinBox):
    """Widget which subscribes to a value on the dataserver and
    displays it"""

    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        selector: str,
        *args,
        **kwargs
    ):
        """
        Parameters
        ----------
        dgw : DataGateway
            gateway to the dataserver
        path : str
            dataset path in the hdf5 file
        selector : str
            which column to use
        """
        super().__init__(*args, **kwargs)

        self.dgw = dgw
        self.selector = selector

        self.setDecimals(4)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignRight)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.setMaximum(10000)
        self.setMinimum(-10000)

        # try getting already existing value
        try:
            data = self.dgw.get_data(path, slice(-1, None), selector)[0]
            self.setValue(data)
        except KeyError:
            # start with "--" before value is set 
            self.setSpecialValueText("--")  
            self.setValue(-10000)

        self.id = self.dgw.register_callback(path, self._callback)


    def _callback(self, arr):
        """Callback which extracts the value from the appended array."""
        arr = obtain(arr)

        val = arr[self.selector][-1]

        # interesting value
        self.setDisabled(False)
        self.setValue(val)

    def cleanup(self):
        """Remove callback."""
        self.dgw.remove_callback(self.id)