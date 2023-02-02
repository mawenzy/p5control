from typing import Optional

from qtpy.QtWidgets import QGridLayout, QRadioButton, QWidget

from ...gateway import InstrumentGateway

class StatusIndicator(QRadioButton):
    pass



class MeasurementControl(QWidget):
    def __init__(
        self,
        gw: InstrumentGateway,
        parent: Optional['QWidget'] = None
    ):
        super().__init__(parent)

        self.gw = gw

        # widgets
        self.status_indicator = StatusIndicator()

        # layout
        layout = QGridLayout()
        layout.addWidget(self.status_indicator, 0, 0)

        self.setLayout(layout)

