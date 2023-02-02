from typing import Optional

from qtpy.QtCore import QSize, Slot, Qt, QEvent
from qtpy.QtWidgets import QTabBar, QTabWidget, QWidget, QLabel, QStyle, QAbstractButton, QStyleOption
from qtpy.QtGui import QEnterEvent, QPaintEvent, QPainter

from ...gateway import DataGateway
from .datagw_plot import DataGatewayPlot
from .plotform import PlotForm


class CustomButton(QAbstractButton):
    """
    Python version of CloseButton defined in
    https://codebrowser.dev/qt5/qtbase/src/widgets/widgets/qtabbar.cpp.html#79
    """
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        prim_element = QStyle.PE_IndicatorTabClose,
    ) -> None:
        super().__init__(parent)
        self.prim_element = prim_element

    def sizeHint(self) -> QSize:
        self.ensurePolished()
        width = self.style().pixelMetric(QStyle.PM_TabCloseIndicatorWidth, None, self)
        height = self.style().pixelMetric(QStyle.PM_TabCloseIndicatorHeight, None, self)
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def enterEvent(self, event: QEnterEvent) -> None:
        if self.isEnabled():
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, a0: QEvent) -> None:
        if self.isEnabled():
            self.update()
        super().leaveEvent(a0)

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        opt = QStyleOption()
        opt.initFrom(self)
        opt.state |= QStyle.State_AutoRaise
        if self.isEnabled() and self.underMouse() and not self.isChecked() and not self.isDown():
            opt.state |= QStyle.State_Raised
        if self.isChecked():
            opt.state |= QStyle.State_On
        if self.isDown():
            opt.state |= QStyle.State_Sunken

        if self.parent():
            # parent is QTabBar
            index = self.parent().currentIndex()
            position = self.style().styleHint(QStyle.SH_TabBar_CloseButtonPosition)
            # convert int result to the right type
            position = QTabBar.LeftSide if position == 0 else QTabBar.RightSide

            if self.parent().tabButton(index, position) == self:
                opt.state |= QStyle.State_Selected

        self.style().drawPrimitive(self.prim_element, opt, p, self)


class PlotTabWidget(QTabWidget):
    """
    Tab Widget which holds multiple DataGatewayPlot widgets
    """
    def __init__(
        self,
        dgw: DataGateway,
        plot_form: Optional[PlotForm] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)

        self.dgw = dgw
        self.plot_form = plot_form

        # tabBar needs to be created in python such that we can access the private method
        # tabLayoutChange in setTabsClosable
        self.setTabBar(QTabBar())
        self.closeButtonOnTabs = False

        # place a plot
        self._handle_add_plot()

        # add + button
        self.plus_btn = CustomButton(self.tabBar(), prim_element=QStyle.PE_IndicatorSpinPlus)
        self.addTab(QLabel('Add tabs by pressing "+"'), "")
        self.setTabEnabled(self.count() - 1, False)
        self.tabBar().setTabButton(self.count() - 1, QTabBar.RightSide, self.plus_btn)

        # connect signals
        self.tabCloseRequested.connect(self._handle_tab_close)
        self.currentChanged.connect(self._handle_tab_current_changed)
        self.plus_btn.pressed.connect(self._handle_add_plot)

    @Slot(str)
    def plot_path(self, path: str):
        self.currentWidget().add_plot(path)

    def update(self):
        self.currentWidget().update()

    def setTabsClosable(self, closeable: bool) -> None:
        """
        Overwrites the default behaviour to ignore the plus tab. See
        https://codebrowser.dev/qt5/qtbase/src/widgets/widgets/qtabbar.cpp.html
        for the c++ source code.
        """
        if self.closeButtonOnTabs == closeable:
            return
        self.closeButtonOnTabs = closeable
        # which side the buttons are on, platform dependent, 0 -> left, 1 -> right
        closeSide = self.style().styleHint(QStyle.SH_TabBar_CloseButtonPosition)
        closeSide = QTabBar.LeftSide if closeSide == 0 else QTabBar.RightSide

        if not closeable:
            for i in range(self.count() - 1): # skip last button
                if closeSide == QTabBar.LeftSide and self.tabBar().tabButton(i, QTabBar.LeftSide):
                    self.tabBar().tabButton(i, QTabBar.LeftSide).deleteLater()
                    self.tabBar().setTabButton(i, QTabBar.LeftSide, None)
                if closeSide == QTabBar.RightSide and self.tabBar().tabButton(i, QTabBar.RightSide):
                    self.tabBar().tabButton(i, QTabBar.RightSide).deleteLater()
                    self.tabBar().setTabButton(i, QTabBar.RightSide, None)
            self.tabBar().tabLayoutChange()
        else:
            newButtons = False
            for i in range(self.count() - 1): # skip last button
                if self.tabBar().tabButton(i, closeSide):
                    continue
                newButtons = True
                closeButton = CustomButton(self.tabBar())
                closeButton.clicked.connect(self._handle_close_btn)
                self.tabBar().setTabButton(i, closeSide, closeButton)
            if newButtons:
                self.tabBar().tabLayoutChange()

    def addTab(self, widget: QWidget, a1: str) -> int:
        index = super().addTab(widget, a1)

        if self.closeButtonOnTabs:
            closeSide = self.style().styleHint(QStyle.SH_TabBar_CloseButtonPosition)
            closeSide = QTabBar.LeftSide if closeSide == 0 else QTabBar.RightSide
            closeButton = CustomButton(self.tabBar())
            closeButton.clicked.connect(self._handle_close_btn)
            self.tabBar().setTabButton(index, closeSide, closeButton)

        return index

    @Slot()
    def _handle_close_btn(self):
        sender = self.sender()
        tabToClose = -1
        closeSide = self.style().styleHint(QStyle.SH_TabBar_CloseButtonPosition)
        closeSide = QTabBar.LeftSide if closeSide == 0 else QTabBar.RightSide
        for i in range(self.count()):
            if closeSide == QTabBar.LeftSide:
                if self.tabBar().tabButton(i, QTabBar.LeftSide) == sender:
                    tabToClose = i
                    break
            else:
                if self.tabBar().tabButton(i, QTabBar.RightSide) == sender:
                    tabToClose = i
                    break
        if tabToClose != -1:
            self.tabCloseRequested.emit(tabToClose)

    @Slot()
    def _handle_add_plot(self):
        """
        Add a new plot in a tab. Makes them closable.
        """
        plot_view = DataGatewayPlot(self.dgw)

        if self.plot_form:
            plot_view.connectPlotForm(self.plot_form)

        self.addTab(plot_view, 'Plot')
        self.tabBar().moveTab(self.count() - 1, self.count() - 2)
        self.setCurrentIndex(self.count() - 2)

        if self.count() > 2:
            self.setTabsClosable(True)

    @Slot(int)
    def _handle_tab_close(self, index: int):
        """
        Close tab at index. If only one is remaining, makes it no longer closable
        """
        plot_view = self.widget(index)
        self.removeTab(index)
        plot_view.deleteLater()

        if self.count() <= 2:
            self.setTabsClosable(False)

    @Slot(int)
    def _handle_tab_current_changed(self, index: int):
        if index == self.count() - 1 and self.count() >= 2:
            # don't select the plus tab
            self.setCurrentIndex(self.count() - 2)
            return

        if self.plot_form:
            self.plot_form.clear()

            # set plot_form to the config if one is selected
            # in the legend
            legend = self.currentWidget().legend
            rows = legend.selectionModel().selectedRows()

            if len(rows) > 0:
                index = rows[0]
                item = legend.model().itemFromIndex(index)

                itemid = item.data(Qt.UserRole)
                legend.selected.emit(itemid)
