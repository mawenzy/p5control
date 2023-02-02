from typing import Optional

from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QGridLayout, QWidget, QToolButton, QStyle, QLineEdit

from ...gateway import InstrumentGateway

class StatusIndicator(QToolButton):
    """
    ``QToolButton``, which indicates a status, with either red or green background color.
    """
    def __init__(self):
        super().__init__()
        self.setDisabled(True)

        # start in off state
        self.state = False
        self._update_color()

    def _update_color(self):
        if self.state:
            self.setStyleSheet("background-color: green")
        else:
            self.setStyleSheet("background-color: red")

    def set_state(self, state: bool):
        """
        Set the state.

        Parameters
        ----------
        state : bool
            True -> green, False -> red
        """
        if self.state == state:
            return
        self.state = state
        self._update_color()

class PlayPauseButton(QToolButton):
    """
    QToolButton which switches beteen play and pause icon.
    """

    changed = Signal(bool)
    """
    **Signal(bool)** - emits ``self.playing`` if it changes
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.playing = False
        self._update_icon()

        self.clicked.connect(self._handle_click)

    def _handle_click(self):
        self.playing = not self.playing
        self._update_icon()
        self.changed.emit(self.playing)

    def _update_icon(self):
        if self.playing:
            self.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def set_playing(self, playing: bool):
        """
        Change playing parameter and upate icon

        Parameters
        ----------
        playing : bool
            state to set the button in
        """
        if self.playing == playing:
            return
        self.playing = playing
        self._update_icon()
        self.changed.emit(self.playing)


class MeasurementControl(QWidget):
    """
    Widget to control measurements. Lets you run and pause them and change the name.
    """
    def __init__(
        self,
        gw: InstrumentGateway,
        show_selector=True,
        parent: Optional['QWidget'] = None
    ):
        super().__init__(parent)

        self.gw = gw

        # widgets
        self.status_indicator = StatusIndicator()
        self.btn = PlayPauseButton()
        self.name = QLineEdit()

        self.btn.changed.connect(self._handle_btn_change)
        # couple status indicator to btn
        self.btn.changed.connect(self.status_indicator.set_state)

        # layout
        layout = QGridLayout()
        layout.addWidget(self.status_indicator, 0, 0)
        layout.addWidget(self.btn, 0, 1)
        layout.addWidget(self.name, 0, 2)

        self.setLayout(layout)

        # get first measurement
        self.gw_update()

    @Slot(bool)
    def _handle_btn_change(self, playing: bool):
        # disable button while we handle operation
        self.btn.setEnabled(False)

        # disable line edit when measurement is running
        if playing:
            self.name.setEnabled(False)
        else:
            self.name.setEnabled(True)

        measure = self.gw.measure(self.name.text())
        if playing and not measure.running():
            measure.start()
        elif not playing and measure.running():
            measure.stop()

        self.btn.setEnabled(True)

    def gw_update(self):
        """
        Update the widget by requesting the Measurement object from the instrument server and
        reading its state into this widget.
        """
        measure = self.gw.measure()
        self.last_name = measure.name()

        self.name.setText(measure.name())
        self.btn.set_playing(measure.running())
