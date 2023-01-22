from typing import Iterable

from qtpy.QtCore import Signal, Qt, Slot, QPoint, QModelIndex, QMimeData, QItemSelection

from qtpy.QtWidgets import (
    QAbstractItemView,
    QListView, 
    QMenu,
    QGraphicsItem,
    QStyleOptionGraphicsItem
)

from qtpy.QtGui import (
    QStandardItemModel,
    QStandardItem,
    QPixmap,
    QPainter,
    QIcon,
    QAction,
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
    


class LegendModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.configs = {}

    def addItem(
        self,
        config
    ):
        list_item = QStandardItem(config["name"])
        list_item.setData(config["id"], Qt.UserRole)

        # create icon
        pixmap = QPixmapFromItem(ItemSample(config["plotDataItem"]))
        list_item.setIcon(QIcon(pixmap))

        self.invisibleRootItem().appendRow(list_item)

        self.configs[config["id"]] = config

    @Slot(str)
    def removeItem(
        self,
        id: str
    ):
        for row in range(self.invisibleRootItem().rowCount()):
            list_item = self.invisibleRootItem().child(row, 0)

            itemid = list_item.data(Qt.UserRole)

            if itemid == id:
                self.removeRow(list_item.row())
                self.configs.pop(id)
                return

    def updateItem(
        self,
        id: str
    ):
        for row in range(self.invisibleRootItem().rowCount()):
            list_item = self.invisibleRootItem().child(row, 0)
            itemid = list_item.data(Qt.UserRole)

            if itemid == id:
                list_item.setIcon(QIcon(QPixmapFromItem(
                    ItemSample(self.configs[id]["plotDataItem"])
                )))

                list_item.setText(self.configs[id]["name"])

    def mimeData(
        self,
        indexes: Iterable[QModelIndex]
    ) -> QMimeData:
        """Send hdf5 path of the item as QMimeData text"""
        item = self.itemFromIndex(indexes[0])
        config = item.data(Qt.UserRole)

        data = QMimeData()
        data.setText(config["path"])

        return data

class LegendView(QListView):

    deleteRequested = Signal(str)
    """emitted if an element should be remove from the plot, provides id"""

    selected = Signal(str)
    """emitted if the selection changes, provides the id or "" if there
    are no longer any elements"""

    def __init__(
        self,
        dragEnabled=True,
        customContextMenu=True
    ):
        super().__init__()

        self.legend_model = LegendModel()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setMinimumWidth(100)
        self.setModel(self.legend_model)

        ## wrap functions from legend model
        for fn in ['addItem', 'removeItem', 'updateItem']:
            setattr(self, fn, getattr(self.legend_model, fn))

        # delete keyboard shortcut
        shortcut = QShortcut(QKeySequence.Delete, self)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self._onDelShortcut)

        # connect new signal
        self.selectionModel().selectionChanged.connect(self._selectionChanged)

        if dragEnabled:
            # enable dragging
            self.setDragEnabled(True)

        if customContextMenu:
            # enable custom context menu
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._onCustomContextMenu)

    def _onDelShortcut(self):
        """remove all items currently selected."""
        indexes = self.selectedIndexes()

        #TODO: does this work with multiple    
        for ind in indexes:
            list_item = self.legend_model.itemFromIndex(ind)
            itemid = list_item.data(Qt.UserRole)

            self.deleteRequested.emit(itemid)

    @Slot(QPoint)
    def _onCustomContextMenu(
        self,
        point: QPoint
    ):
        index = self.indexAt(point)
        list_item = self.model().itemFromIndex(index)

        if list_item is None:
            return 

        itemid = list_item.data(Qt.UserRole)

        menu = QMenu()

        remove_action = QAction("remove")
        remove_action.triggered.connect(lambda: self.deleteRequested.emit(itemid))

        menu.addAction(remove_action)
        menu.exec(self.viewport().mapToGlobal(point))


    @Slot(QItemSelection, QItemSelection)
    def _selectionChanged(
        self,
        selected: QItemSelection,
        deselected: QItemSelection
    ):
        """Emit selected if the seleciton changes"""
        indexes = selected.indexes()

        if len(indexes) > 0:
            index = indexes[0]
            item = self.model().itemFromIndex(index)

            itemid = item.data(Qt.UserRole)

            self.selected.emit(itemid)

        else:
            self.selected.emit("")
