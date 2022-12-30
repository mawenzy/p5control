from typing import Iterable

from qtpy.QtCore import Signal, Qt, Slot, QPoint, QModelIndex, QMimeData

from qtpy.QtWidgets import (
    QAbstractItemView,
    QListView, 
    QMenu,
    QGraphicsItem,
    QStyleOptionGraphicsItem
)

from qtpy.QtGui import (
    QDragMoveEvent,
    QDragLeaveEvent,
    QStandardItemModel,
    QStandardItem,
    QPixmap,
    QPainter,
    QIcon,
    QAction,
    QDrag,
    QShortcut,
    QKeySequence
)

from pyqtgraph import ItemSample, PlotItem


def QPixmapFromItem(item: QGraphicsItem) -> QPixmap:
    """paint QGraphicsItem to QPixmap, can e.g. be used to create an
    QIcon from the Item, as in the legend
    
    item needs to implement item.paint function
    """
    pixmap = QPixmap(item.boundingRect().size().toSize())
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    item.paint(painter, QStyleOptionGraphicsItem())
    return pixmap

class LegendItemModel(QStandardItemModel):
    """
    Model to hold entries for a Legend.
    """

    def addItem(
        self,
        item,
        name: str
    ):
        """
        Add a new entry to the legend.

        Parameters
        ----------
        item: pyqtgraph.PlotDataItem
            used to determine the line and point style, used to create
            an Icon representing it
        name: str
            The name to display for this item
        """
        list_item = QStandardItem(name)
        list_item.setData(item, Qt.UserRole)

        # create icon
        pixmap = QPixmapFromItem(ItemSample(item))
        list_item.setIcon(QIcon(pixmap))

        self.invisibleRootItem().appendRow(list_item)

    def removeItem(
        self,
        item_or_name
    ):
        """
        Remove item by item or its name
        """
        if isinstance(item_or_name, str):
            for item in self.findItems(item_or_name):
                self.removeRow(item.row())
        # iterate over all items
        elif self.invisibleRootItem().hasChildren():
            for row in range(self.invisibleRootItem().rowCount()):
                list_item = self.invisibleRootItem().child(row, 0)
                # test if item_or_name corresponds to item
                item = list_item.data(Qt.UserRole)
                if item is item_or_name:
                    self.removeRow(list_item.row())
                    return

    def mimeData(
        self,
        indexes: Iterable[QModelIndex]
    ) -> QMimeData:
        """Send hdf5 path of the item as QMimeData text"""
        
        item = self.itemFromIndex(indexes[0])
        path = item.text()

        data = QMimeData()
        data.setText(path)

        return data

        
class LegendListView(QListView):
    """
    ListView of a legend. Intended to replace pyqtgraph's LegendItem such that
    the legend can be placed seperately as a standalone widget. Usage:

    ```py
    from pyqtgraph import PlotWidget()
    
    plot = PlotWidget()
    legend = LegendListView()

    # connect legend
    legend.connectToPlotItem(plot.plotItem)
    ```
    """

    def __init__(
        self,
        dragEnabled=False,
        customContextMenu=False
    ):
        super().__init__()

        self.list_model = LegendItemModel()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setMinimumWidth(150)
        self.setModel(self.list_model)

        self.plot_item = None

        ## wrap functions from list model
        for fn in ['addItem', 'removeItem']:
            setattr(self, fn, getattr(self.list_model, fn))

        # keyboard shortcut
        shortcut = QShortcut(QKeySequence.Delete, self)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.onDelShortcut)

        if dragEnabled:
            # enable dragging
            self.setDragEnabled(True)

        if customContextMenu:
            # enable custom context menu
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._onCustomContextMenu)

    def onDelShortcut(
        self,
    ):
        """if called, removes all items currently selected."""
        indexes = self.selectedIndexes()

        for ind in indexes:
            list_item = self.model().itemFromIndex(ind)
            item = list_item.data(Qt.UserRole)
            self.plot_item.removeItem(item)

    def connectToPlotItem(
        self,
        plot_item: PlotItem,
    ):
        """
        Connect this legend to plot_item
        
        Plots added after this will be automatically displayed in the legend if
        they are created with a 'name' argument.
        """
        plot_item.legend = self
        self.plot_item = plot_item

    @Slot(QPoint)
    def _onCustomContextMenu(
        self,
        point: QPoint
    ):
        if self.plot_item:
            index = self.indexAt(point)
            list_item = self.model().itemFromIndex(index)

            if list_item is None:
                return 

            name = list_item.text()
            item = list_item.data(Qt.UserRole)

            menu = QMenu()

            remove_action = QAction("remove")
            remove_action.triggered.connect(lambda: self.plot_item.removeItem(item))

            menu.addAction(remove_action)
            menu.exec(self.viewport().mapToGlobal(point))

    def dragLeaveEvent(self, e: QDragLeaveEvent) -> None:
        print("dragLeaveEvent")
        return super().dragLeaveEvent(e)

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        print("dragMoveEvent")
        return super().dragMoveEvent(e)

    """
    Code below can be used to remove the item after dragging, but has some problems
    """
    # def startDrag(self, supportedActions: Qt.DropAction) -> None:
    #     # translated c++ code from https://codebrowser.dev/qt5/qtbase/src/widgets/itemviews/qabstractitemview.cpp.html#1029
    #     indexes = self.selectedIndexes()
    #     if len(indexes) > 0:
    #         data = self.model().mimeData(indexes)
    #         if not data:
    #             return
    #         drag = QDrag(self)
    #         drag.setMimeData(data)

    #         res = drag.exec(supportedActions)

    #         if res == Qt.DropAction.MoveAction:
    #             list_item = self.model().itemFromIndex(indexes[0])
    #             item = list_item.data(Qt.UserRole)

    #             self.plot_item.removeItem(item)

