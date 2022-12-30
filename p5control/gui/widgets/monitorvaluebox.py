from rpyc.utils.classic import obtain

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDoubleSpinBox, QAbstractSpinBox

from ...gateway import DataGateway
from ..guisettings import id_generator

class MonitorValueBox(QDoubleSpinBox):
    """Widget which subscribes to a value on the dataserver and
    displays it"""

    def __init__(
        self,
        dgw: DataGateway,
        path: str,
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
        """
        super().__init__(*args, **kwargs)

        self.id = next(id_generator)
        self.dgw = dgw

        self.setDecimals(4)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignRight)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.setMaximum(10000)
        self.setMinimum(-10000)

        # try getting already existing value
        try:
            data = self.dgw.get_dataset_slice(
                path,
                slice(-1, None)
            )
            self.setValue(data[-1][-1])
        except KeyError:
            # start with "--" before value is set 
            self.setSpecialValueText("--")  
            self.setValue(-10000)

        self.dgw.register_callback(self.id, path, self._callback)


    def _callback(self, arr):
        """Callback which extracts the value from the appended array."""
        arr = obtain(arr)

        # interesting value
        val = arr[-1][-1]
        self.setDisabled(False)
        self.setValue(val)

    def cleanup(self):
        """Remove callback."""
        self.dgw.remove_callback(self.id)