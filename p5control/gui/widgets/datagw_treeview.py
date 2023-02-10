"""
This file defines the class DataGatewayTreeView, which is a Widget which shows
the directory structure of the hdf5 file behind the gateway in a customized `QTreeView`.
"""
from typing import Iterable, Optional, List

import h5py

from qtpy.QtCore import Qt, Signal, Slot, QModelIndex, QItemSelection, QMimeData, QPoint, QObject, QThread
from qtpy.QtWidgets import QTreeView, QAbstractItemView, QMenu
from qtpy.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction

from ...gateway import DataGateway

class _DataGatewayTreeModelWorker(QObject):
    """
    Worker which has a slot to trigger it to get the children of a group on the data server
    and emits a signal if new nodes are found.
    """

    new_node = Signal(str, str, bool)
    """
    **Signal(str, str, bool)** - emitted if a new node should be added to the treeview model.
    Comes with path of parent, name of the node and bool whether node is a group. 
    """

    def __init__(self, dgw, parent=None):
        super().__init__(parent)
        self.dgw = dgw

    def get_children(
        self,
        path: str,
        children_names: List[str]
    ):
        """
        Request the children for a group in the hdf5 file and emit ``new_node`` if there are new
        ones. This method is optimized to minimize the amount of requests send.

        Parameters
        ----------
        path : str
            hdf5 path of the group
        children_names : List[str]
            names of the children which already exist and should not be added again
        """
        # function call which returns tuple -> 3 requests
        # converted to list for .remove in next step
        names = list(self.dgw.get_keys(path))

        for name in children_names:
            names.remove(name)

        if len(names) > 0:
            # create netref this function only once
            func_get = self.dgw.get

            for name in names:
                node = func_get(f"{path}/{name}")

                if isinstance(node, h5py.Group):
                    self.new_node.emit(path, name, True)
                else:
                    self.new_node.emit(path, name, False)

class DataGatewayTreeModel(QStandardItemModel):
    """
    Model for the TreeView of the data server hdf5 contents

    Parameters
    ----------
    dgw : DataGateway
        gateway to the data server
    parent : Optional[QObject]
        parent qt object
    """

    update_children = Signal(str, list)
    """
    **Signal(str, list)** - emitted if the children should be updated, with path and an existing
    list of children names provided.
    """

    def __init__(
        self,
        dgw: DataGateway,
        parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)

        self.dgw = dgw

        # worker + thread
        self.worker = _DataGatewayTreeModelWorker(self.dgw)
        self.worker_thread = QThread(self)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.worker.new_node.connect(self.add_node)
        self.update_children.connect(self.worker.get_children)

        self.invisibleRootItem().setData("/", Qt.UserRole)
        self.invisibleRootItem().setData(True, Qt.UserRole+1)

        self.update_children.emit("/", [])

    def add_node(
        self,
        parent_path: str,
        name: str,
        is_group: bool
    ):
        """
        Add node to the tree, by creating a corresponding `QStandardItem` for the node and
        appending it in a new row to parent_item. If node is a group, emits the
        ``update_children`` signal for this node.

        Parameters
        ----------
        parent_path : str
            the parent path the node should be added to
        name : str
            name of the node
        is_groupe : bool
            True -> group, False -> dataset
        """
        path = f"/{name}" if parent_path == "/" else f"{parent_path}/{name}"

        # check if node with path is already present
        if len(self.match(self.index(0, 0), Qt.UserRole, path, hits=1,
                            flags=Qt.MatchExactly | Qt.MatchRecursive)) != 0:
            return

        tree_item = QStandardItem(name)
        tree_item.setData(path, Qt.UserRole)
        tree_item.setData(is_group, Qt.UserRole + 1)

        if is_group:
            tree_item.setIcon(QIcon('icons:folder.svg'))
        else:
            tree_item.setIcon(QIcon('icons:dataset.svg'))

        parent_indexes = self.match(self.index(0, 0), Qt.UserRole, parent_path, hits=1,
                                    flags=Qt.MatchExactly | Qt.MatchRecursive)

        if len(parent_indexes) == 0:
            parent = self.invisibleRootItem()
        else:
            parent = self.itemFromIndex(parent_indexes[0])

        parent.appendRow([tree_item])

        if is_group:
            self.update_children.emit(path, [])

    def handle_expanded(self, index):
        """
        Update folder icon to expanded.

        Parameters
        ----------
        index
            the index of the item which is being expanded
        """
        item = self.itemFromIndex(index)
        item.setIcon(QIcon('icons:folder-open.svg'))

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

    def visit_item(self, item):
        """
        Update children for the item and recursively for all children

        Parameters
        ----------
        item : QStandardItem
        """
        # skip datasets
        if not item.data(Qt.UserRole + 1):
            return

        path = item.data(Qt.UserRole)

        child_names = []
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            child_names.append(child_item.text())

            if child_item.data(Qt.UserRole + 1):
                self.visit_item(child_item)

        self.update_children.emit(path, child_names)

    def update_data(self):
        """
        Update all expanded nodes with children which might have been added to the dataserver.
        """
        self.visit_item(self.invisibleRootItem())

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
            self.customContextMenuRequested.connect(self._on_custom_context_menu)

    def cleanup(self):
        """
        Assure that the model worker thread is quit before exiting the application.
        """
        self.tree_model.worker_thread.quit()
        self.tree_model.worker_thread.wait()

    @Slot(QPoint)
    def _on_custom_context_menu(
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
        is_group = item.data(Qt.UserRole + 1)

        if not is_group:
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
