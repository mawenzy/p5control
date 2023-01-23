from qtpy.QtWidgets import QFormLayout, QWidget

from ...gateway import DataGateway
from .monitorvaluebox import MonitorValueBox
from .editvaluebox import EditValueBox

class ValueBoxForm(QWidget):

    def __init__(
        self,
        dgw: DataGateway,
        rows=None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.dgw = dgw

        self.layout = QFormLayout()

        for row in rows:
            self.addRow(row)

        self.setLayout(self.layout)

    def addRow(self, row):
        """Add a row to the layout, row is given by
        
        row = (label: str, path: str, selector: Union[str, slice], Optional[setter: func])
        """
        if len(row) == 3:
            self.layout.addRow(row[0], MonitorValueBox(self.dgw, row[1], row[2]))
        elif len(row) == 4:
            self.layout.addRow(row[0], EditValueBox(self.dgw, row[1], row[2], row[3]))
        else:
            raise Exception(
                f"row {row} has wrong format."
                ) 

