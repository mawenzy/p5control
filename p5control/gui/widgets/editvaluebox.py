from qtpy.QtCore import Slot
from qtpy.QtWidgets import QAbstractSpinBox

from ...gateway import DataGateway
from .monitorvaluebox import MonitorValueBox

class EditValueBox(MonitorValueBox):
    """
    Widget which subscribes to a value on the dataserver and dispalys it and can be edited by
    the user to change it.

    Parameters
    ----------
    dgw : DataGateway
        gateway to the dataserver
    path : str
        dataset path in the hdf5 file
    setter : callable
        function to call with setter(new_value) whenever the value is changed by the user
    """
    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        selector: str,
        setter,
        *args,
        **kwargs
    ):
        super().__init__(dgw, path, selector, *args, **kwargs)
        self.setter = setter

        # editable
        self.setReadOnly(False)
        self.setSingleStep(0.01)
        self.setButtonSymbols(QAbstractSpinBox.UpDownArrows)

        self.editingFinished.connect(self.onEditingFinished)
        self.last_value = self.value()


    def _callback(self, arr):
        """Only update the value if it is not currently edited."""
        if not self.hasFocus():
            super()._callback(arr)

            self.last_value = self.value()

    @Slot()
    def onEditingFinished(self):
        """Call self.setter with new value if it has changed."""
        new_value = self.value()

        # only call if value has changed
        if new_value != self.last_value:
            self.setter(new_value)
            self.last_value = new_value
