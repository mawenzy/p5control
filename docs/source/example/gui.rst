
Visualization
-------------

*p5control* provides some basic qt widgets which can help you rapidly develop your own gui for your experiment. As an example :class:`.DataGatewayTreeView` provides a simple widget which shows you the current directory structure on the running data server. The following script is all that is needed to show this widget, which allows you to visualize the directory structure 

.. code-block:: py

    import sys
    from p5control.gui import CleanupApp, GuiDataGateway, DataGatewayTreeView

    app = CleanupApp()

    with GuiDataGateway() as dgw:

        widget = DataGatewayTreeView(dgw)
        widget.show()

        sys.exit(app.exec())

Live plotting status
====================

This simple example shows the data server content in a treeview on the left side. In the center there is a plot widget, where you can plot any dataset by dragging it from the treeview or double clicking. In the right column, you can edit the values of the frequency and the amplitude for the two drivers.


.. code-block:: py

    import sys

    from qtpy.QtCore import (
        QTimer
    )

    from qtpy.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QHBoxLayout
    )

    from p5control import ( 
        InstrumentGateway
    )

    from p5control.gui import (
        CleanupApp,
        GuiDataGateway,
        DataGatewayTreeView,
        CustomPlotWidget,
        ValueBoxForm,
    )

    class LivePlotMainWindow(QWidget):

        def __init__(
            self,
            app: QApplication,
            dgw: GuiDataGateway,
            gw: InstrumentGateway
        ):
            super().__init__()

            self.app = app
            self.dgw = dgw
            self.gw = gw

            self.tree_view = DataGatewayTreeView(self.dgw, dragEnabled=True)
            self.tree_view.expandAll()

            self.plot = CustomPlotWidget(dgw)

            self.form = ValueBoxForm(dgw, [
                ('inst1<sub>ampl</sub>', 'status/inst1', gw.inst1.setAmplitude),
                ('inst1<sub>freq</sub>', 'status/inst1', gw.inst1.setFrequency),
                ('inst2<sub>ampl</sub>', 'status/inst2', gw.inst2.setAmplitude),
                ('inst2<sub>freq</sub>', 'status/inst2', gw.inst2.setFrequency)
            ])

            # layout
            row3 = QWidget()
            row3_lay = QVBoxLayout()
            row3_lay.addWidget(self.form)
            row3_lay.addStretch()
            row3.setLayout(row3_lay)

            lay = QHBoxLayout()
            lay.addWidget(self.tree_view)
            lay.addWidget(self.plot)
            lay.addWidget(row3)

            self.setLayout(lay)

            # signal
            self.tree_view.doubleClickedDataset.connect(self.plot.add_dataset)

        def update(self):
            self.plot.update()


    if __name__ == '__main__':
        with GuiDataGateway(allow_callback=True) as dgw, InstrumentGateway() as gw:

            app = CleanupApp()

            window = LivePlotMainWindow(app, dgw, gw)
            window.show()

            timer = QTimer()
            timer.timeout.connect(window.update)
            timer.start(30)

            sys.exit(app.exec())