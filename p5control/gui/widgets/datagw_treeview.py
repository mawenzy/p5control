"""
This file defines the class DataGatewayTreeView, which is a Widget which shows
the directory structure of the hdf5 file behind the gateway in a customized `QTreeView`.
"""
from typing import Union, Iterable, Optional

import h5py

from qtpy.QtCore import Qt, Signal, Slot, QModelIndex, QItemSelection, QMimeData, QPoint, QAbstractItemModel, QObject, QThread
from qtpy.QtWidgets import QTreeView, QAbstractItemView, QMenu
from qtpy.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction

from ...gateway import DataGateway

class DataGatewayTreeModel(QStandardItemModel):
    """
    QStandardItemModel which holds the directory structure of the hdf5 file
    on the DataServer.

    The data tree is only ever populated one layer deeper than what
    is expanded by the user and further children are loaded after expansion.

    Note that a node has to have children when it is first seen on screen
    such that Qt automatically adds the ability to expand it.

    Each item has data stored with it:

        -   Qt.UserRole     path
        -   Qt.UserRole+1   "h5py.Group" or "h5py.Dataset"

    Parameters
    ----------
    dgw : DataGateway
        gateway to the data server
    """
    def __init__(
        self,
        dgw: DataGateway
    ):
        super().__init__()

        self.dgw = dgw
        self.init_model()

    def init_model(self):
        """Initialize the item model two layers deep."""
        self.setHorizontalHeaderLabels(['Objects'])
        self.invisibleRootItem().setData("/", Qt.UserRole)
        self.invisibleRootItem().setData("h5py.Group", Qt.UserRole+1)

        # top level nodes
        for node in self.dgw.get("/").values():
            parent = self.add_node(self, node)

            # add children if they are groups so they can be expanded
            if isinstance(node, h5py.Group):
                self.update_children(parent)

    def add_node(
        self,
        parent_item: QStandardItem,
        node: Union[h5py.Group, h5py.Dataset]
    ):
        """
        Add node to the tree, by creating a corresponding `QStandardItem` for the node and
        appending it in a new row to parent_item.

        Parameters
        ----------
        parent_item : QStandardItem
            the parent item the node should be added to
        node : h5py.Group, h5py.Dataset
            the node in the hdf5 path which is added to the model
        """
        node_path = node.name
        node_name = node_path.split('/')[-1]

        if not node_name:
            node_name = node_path

        tree_item = QStandardItem(node_name)
        tree_item.setData(node_path, Qt.UserRole)

        if isinstance(node, h5py.Dataset):
            tree_item.setIcon(QIcon('icons:dataset.svg'))
            tree_item.setData("h5py.Dataset", Qt.UserRole+1)
        elif isinstance(node, h5py.Group):
            tree_item.setIcon(QIcon('icons:folder.svg'))
            tree_item.setData("h5py.Group", Qt.UserRole+1)

        parent_item.appendRow([tree_item])

        return tree_item

    def visit_update_children(self, item):
        """
        Update children for the item and recursively for all children. Newly added children
        are not visited, but their children are also added.

        Parameters
        ----------
        item : QStandardItem
        """
        try:
            new_items = self.update_children(item)
        except KeyError:
            # model in a broken state, should only happen if the DataServer
            # is new and does not have the same data as the old one
            self.removeRows(0, self.rowCount())
            self.init_model()
            return

        # update children
        if item.hasChildren():
            for row in range(item.rowCount()):
                child_item = item.child(row, 0)

                if not child_item:
                    continue

                # recursively update child_item
                if child_item.hasChildren():
                    self.visit_update_children(child_item)
                # if the item is new, it does not have children
                # but we need to add them so QTreeView correctly
                # lets us expand the folder
                elif child_item in new_items:
                    self.update_children(child_item)

    def update_children(self, item):
        """
        Adds all the children from the dataserver which item
        does not already have

        Parameters
        ----------
        item : QStandardItem

        Returns
        -------
        the new items: List[items]
        """
        item_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)

        # skip datasets
        if item_type == "h5py.Group":
            names = []
            # collect the names of all the existing children
            if item.hasChildren():
                for row in range(item.rowCount()):
                    child_item = item.child(row, 0)

                    if not child_item:
                        continue

                    path = child_item.data(Qt.UserRole)
                    name = path.split('/')[-1]

                    names.append(name)

            new_items = []
            # iterate over children on data server
            for name in self.dgw.get(item_path).keys():
                # skip for children which already exist
                if name in names:
                    continue

                node = self.add_node(item, self.dgw.get(f"{item_path}/{name}"))
                new_items.append(node)

            return new_items

    def handle_expanded(self, index):
        """
        Update folder icon to expanded and update children.

        Parameters
        ----------
        index
            the index of the item which is being expanded
        """
        item = self.itemFromIndex(index)
        try:
            self.update_children(item)
        except KeyError:
            # model in a broken state, should only happen if the DataServer
            # is new and does not have the same data as the old one
            self.removeRows(0, self.rowCount())
            self.init_model()
            return

        if not item.hasChildren():
            return

        item.setIcon(QIcon('icons:folder-open.svg'))

        # iterate over the children, such that their children
        # are added to the tree such that qt allows the user
        # to expand the TreeView
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)

            if not child_item or child_item.hasChildren():
                continue

            try:
                self.update_children(child_item)
            except KeyError:
                # model in a broken state, should only happen if the DataServer
                # is new and does not have the same data as the old one
                self.removeRows(0, self.rowCount())
                self.init_model()
                return

    def handle_collapsed(self, index):
        """
        Update folder icon to closed.

        Parameters
        ----------
        index
            index of the item which has been closed.
        """
        item = self.itemFromIndex(index)
        item.setIcon(QIcon('icons:folder.svg'))

    def update_data(self):
        """
        Update all expanded nodes with children which might have been added to the dataserver.
        """
        self.visit_update_children(self.invisibleRootItem())

    def supportedDragActions(self) -> Qt.DropAction:
        """
        Only allow dragging to copy the element, so it will not be removed.
        """
        return Qt.CopyAction

    def mimeData(
        self,
        indexes: Iterable[QModelIndex]
    ) -> QMimeData:
        """
        Send hdf5 path of the item as QMimeData text. Allows for the dragging of an element.
        """
        item = self.itemFromIndex(indexes[0])
        path = item.data(Qt.UserRole)

        data = QMimeData()
        data.setText(path)

        return data

class Worker(QObject):
    
    new_node = Signal(str, str, bool)

    def __init__(self, dgw, parent=None):
        super().__init__(parent)
        self.dgw = dgw

    def get_children(self, path, children_names):
        for name, node in self.dgw.get(path).items():
            if name in children_names:
                continue

            if isinstance(node, h5py.Group):
                print("emitting", path, name, True)
                self.new_node.emit(path, name, True)
            else:
                print("emitting", path, name, False)
                self.new_node.emit(path, name, False)

class AsyncDataGatewayTableModel(QStandardItemModel):

    update_children_requested = Signal(str, list)

    def __init__(
        self,
        dgw: DataGateway,
        parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)

        self.dgw = dgw

        self.worker_thread = QThread()
        self.worker = Worker(self.dgw)
        self.worker.moveToThread(self.worker_thread)

    
        self.worker.new_node.connect(self.add_node)
        self.update_children_requested.connect(self.worker.get_children)

        self.worker_thread.start()

        self.invisibleRootItem().setData("/", Qt.UserRole)
        self.invisibleRootItem().setData(True, Qt.UserRole+1)

        self.update_children_requested.emit("/", [])


    def add_node(self, parent_path, name, is_group):
        path = f"/{name}" if parent_path == "/" else f"{parent_path}/{name}"

        tree_item = QStandardItem(name)
        tree_item.setData(path, Qt.UserRole)
        tree_item.setData(is_group, Qt.UserRole + 1)

        if is_group:
            tree_item.setIcon(QIcon('icons:folder.svg'))
        else:
            tree_item.setIcon(QIcon('icons:dataset.svg'))

        parent_indexes = self.match(self.index(0, 0), Qt.UserRole, parent_path, hits=1, flags=Qt.MatchExactly | Qt.MatchRecursive)

        if len(parent_indexes) == 0:
            parent = self.invisibleRootItem()
        else:
            parent = self.itemFromIndex(parent_indexes[0])

        parent.appendRow([tree_item])

        if is_group:
            self.update_children_requested.emit(path, [])

    def handle_expanded(self, index):
        item = self.itemFromIndex(index)

        if not item.hasChildren():
            return
        
        item.setIcon(QIcon('icons:folder-open.svg'))

    def handle_collapsed(self, index):
        item = self.itemFromIndex(index)
        item.setIcon(QIcon('icons:folder.svg'))

    def visit_item(self, item):
        # skip datasets
        if not item.data(Qt.UserRole + 1):
            return

        path = item.data(Qt.UserRole)

        child_names = []
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            child_names.append(child_item.text())

            if child_item.data(Qt.UserRole + 1) == True:
                self.visit_item(child_item)

        self.update_children_requested.emit(path, child_names)


    def update_data(self):
        self.visit_item(self.invisibleRootItem())


class DataGatewayTreeView(QTreeView):
    """
    Custom `QTreeView` which shows the directory structure of the hdf5 file
    on the dataserver using DataGatewayTreeModel.

    Parameters
    ----------
    dgw : DataGateway
        Gateway to the data server where the data is stored in hdf5 format
    dragEnabled : Optional, True
        Whether to enable dragging. If enabled, the hdf5 path of the element
        dragged is send as mimeData text
    customContextMenu : Optional, False
        Experimentally enables a custom context menu
    *args, **kwargs
        passed to super().__init__
    """

    doubleClickedDataset = Signal(str)
    """
    **Signal(str)** - emitted if a dataset is double clicked, provides path to dataset
    """

    selected = Signal(str)
    """
    **Signal(str)** - emitted if the selection changes, provides path to the newly selected item
    """

    def __init__(
        self,
        dgw,
        *args,
        dragEnabled=True,
        customContextMenu=False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.dgw = dgw

        # set up the file tree view
        self.tree_model = DataGatewayTreeModel(self.dgw)
        # self.tree_model = AsyncDataGatewayTableModel(self.dgw)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setHeaderHidden(True)
        self.setModel(self.tree_model)

        # connect signals to update model icon + children
        self.expanded.connect(self.tree_model.handle_expanded)
        self.collapsed.connect(self.tree_model.handle_collapsed)

        # connect new signals
        self.doubleClicked.connect(self._double_click)
        self.selectionModel().selectionChanged.connect(self._selection_changed)

        if dragEnabled:
            # enable dragging
            self.setDragDropMode(QAbstractItemView.DragOnly)
            self.setDragEnabled(True)

        if customContextMenu:
            # enable custom context menu
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._onCustomContextMenu)

    @Slot(QPoint)
    def _onCustomContextMenu(
        self,
        point: QPoint
    ):
        index = self.indexAt(point)
        item = self.model().itemFromIndex(index)

        item_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)

        if item_type == "h5py.Dataset":
            menu = QMenu()

            plot_action = QAction("plot")
            plot_action.triggered.connect(lambda: print(f"plot {item_path}"))

            new_plot_action = QAction("plot in new tab")
            new_plot_action.triggered.connect(lambda: print(f"plot in new tab {item_path}"))

            menu.addAction(plot_action)
            menu.addAction(new_plot_action)
            menu.exec(self.viewport().mapToGlobal(point))

    @Slot(QModelIndex)
    def _double_click(
        self,
        index: QModelIndex
    ):
        """
        Emit doubleClickedDataset on doubleClick if the node is a dataset
        """
        item = self.model().itemFromIndex(index)

        item_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)

        if item_type == "h5py.Dataset":
            self.doubleClickedDataset.emit(item_path)

    @Slot(QItemSelection, QItemSelection)
    def _selection_changed(
        self,
        selected: QItemSelection,
        _: QItemSelection
    ):
        """
        Emit selected if the selection changes
        """
        indexes = selected.indexes()

        if len(indexes) > 0:
            index = selected.indexes()[0]
            item = self.model().itemFromIndex(index)

            item_path = item.data(Qt.UserRole)

            self.selected.emit(item_path)

    def update_data(self):
        """
        Update the model by pulling newly added groups and datasets from the data server.
        """
        self.tree_model.update_data()
