"""
This file defines the class AttributesTableView, which shows
the attributes of a element in the hdf5 file and lets you edit them.

ExtendableAttributesTableView extends this and lets you add and remove attributes.
"""
import logging
from typing import Any

from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot, Signal, QObject
from qtpy.QtWidgets import (
    QTableView, QHeaderView, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
)

from ..threadcontrol import rpyc_thread
from ...gateway import DataGateway
from ...util import name_generator

logger = logging.getLogger(__name__)

class _AttributesTableModelWorker(QObject):
    new_attr = Signal(str, str, object)

    def __init__(self, dgw, parent=None):
        super().__init__(parent)
        self.dgw = dgw

    def get_attributes(
        self,
        path: str,
    ):
        # not optimized
        for key, value in self.dgw.get(path).attrs.items():
            self.new_attr.emit(path, key, value)

class AttributesTableModel(QAbstractTableModel):
    """Model representing the attributes a group or dataset in the
    hdf5 can have.
    
    Parameters
    ----------
    dgw : DataGateway
        the gateway to the data server
    editable : bool, optional
        whether entries can be edited    
    """
    update_requested = Signal(str)

    def __init__(
        self,
        dgw: DataGateway,
        editable: bool = True
    ):
        super().__init__()

        self.dgw = dgw
        self.editable = editable

        self.worker = _AttributesTableModelWorker(self.dgw)
        self.worker.moveToThread(rpyc_thread)

        self.worker.new_attr.connect(self.add_attr)
        self.update_requested.connect(self.worker.get_attributes)

        self.node = None
        self.path = None
        self.column_count = 3

        self.attrs_list = []

    def update_node(self, path):
        """
        Update the hdf5 path and then update model

        Parameters
        ----------
        path : str
            hdf5 path for the inspected group or dataset
        """
        self.node = self.dgw.get(path)
        self.path = path

        # reset model
        self.beginResetModel()
        self.attrs_list = []
        self.endResetModel()

        self.update_requested.emit(path)

    def add_attr(
        self,
        path: str,
        key: str,
        value: object
    ):
        # skip attributs which do not belong to this path
        if path != self.path:
            return

        self.beginInsertRows(
            self.index(self.rowCount(), 0),
            self.rowCount() + 1,
            self.rowCount() + 1
        )

        self.attrs_list.append(
            [key, value, value.__class__.__name__]
        )

        self.endInsertRows()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.attrs_list)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return self.column_count

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = ...
        ) -> Any:
        """responsible for setting the header names"""
        HEADERS = ('Name', 'Value', 'Type')

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return HEADERS[section]
            return str(section)

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        """return the data which should be shown at index"""
        if index.isValid():
            column = index.column()
            row = self.attrs_list[index.row()]

            if role in (Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole):

                if column == 0:
                    return row[0]
                elif column == 1:
                    return str(row[1])
                elif column == 2:
                    return row[2]

    def flags(self, index):
        """return flags to make attributes editable or not"""
        if self.editable:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        return Qt.NoItemFlags

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        """Called when setting data. Performs some checks and if they are successful,
        sets the data both on the data server and in the local model."""
        if index.isValid():
            column = index.column()
            row = index.row()

            # only handle non emtpy values
            value = value.strip()
            if len(value) == 0:
                return False

            old_key = self.attrs_list[row][0]
            old_value = self.attrs_list[row][1]
            old_class = self.attrs_list[row][2]

            if column == 0:
                if value in (x[0] for x in self.attrs_list):
                    # stop overwriting of data, this key already exists
                    return False

                # try removing old entry
                if self.node.attrs.pop(old_key):
                    # add new entry to database
                    self.node.attrs[value] = old_value
                    # update model
                    self.attrs_list[row][0] = value

                    self.dataChanged.emit(index, index, [])
                    return True
            elif column == 1 or column == 2:
                # when changing value or class, assure that class(value) still
                # makes sense and then accept it
                new_value = value if column == 1 else old_value
                new_class = value if column == 2 else old_class

                if new_class == 'str':
                    new_value = str(new_value)
                elif new_class in ['int', 'int32']:
                    try:
                        new_value = int(new_value)
                    except ValueError:
                        logger.info('Failed to convert "%s" to int', new_value)
                        return False
                elif new_class in ['float', 'float32', 'float64']:
                    try:
                        new_value = float(new_value)
                    except ValueError:
                        logger.info('Failed to convert "%s" to float', new_value)
                        return False
                else:
                    # unknown class, skipping
                    logger.info("Unknown class %s", new_class)
                    return False

                # change database entry
                self.node.attrs[old_key] = new_value
                # update model
                self.attrs_list[row][1] = new_value
                self.attrs_list[row][2] = new_class

                self.dataChanged.emit(index, index, [])
                return True

        return False

    def add_row(self):
        """Add an extra row to the attributes, row is filled
        with a standard key and value."""
        # a node has to be selected
        if not self.node:
            return
        
        gen = name_generator("key", width=2)
        key = next(gen)

        # search for new key
        while True:
            if key in (x[0] for x in self.attrs_list):
                key = next(gen)
            else:
                break

        # add database entry
        self.node.attrs[key] = "new"

        # update model
        self.add_attr(self.path, key, "new")

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        """remove row specified with ``row`` from the attributes"""
        if row < self.rowCount():
            # remove it on data server
            self.node.attrs.pop(self.keys[row])

            # reload model from server
            self.update_node(self.path)


class AttributesTableView(QTableView):
    """``QTableView`` configured to show the attributes.
    
    Parameters
    ----------
    dgw : DataGateway
        gateway to the data server
    editable : bool = True
        whether the elements in the table should be editable
    """

    def __init__(
        self,
        dgw: DataGateway,
        *args,
        editable: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.dgw = dgw
        self.editable = editable

        self.attrs_model = AttributesTableModel(self.dgw, editable)
        self.setModel(self.attrs_model)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()

    @Slot(str)
    def update_node(
        self,
        path: str
    ):
        """Call this function to update for which node the attributes are shown.

        Parameters
        ----------
        path : str
            hdf5 node path
        """
        self.attrs_model.update_node(path)

    def remove_selected_rows(self):
        """Remove all rows which are currently selected."""
        indices = self.selectionModel().selectedIndexes()

        rows = list(set([i.row() for i in indices]))
        rows.sort(reverse=True)

        for r in rows:
            self.attrs_model.removeRow(r)

class ExtendableAttributesTableView(QWidget):
    """Extends ``AttributesTableView`` by adding two buttons to
    either add or remove rows.
    
    Parameters
    ----------
    dgw : DataGateway
        gateway to the data server
    """

    def __init__(
        self,
        dgw: DataGateway,
    ):
        super().__init__()

        self.dgw = dgw

        self.attrs_view = AttributesTableView(self.dgw, editable=True)

        self.remove_button = QPushButton("Remove entry", self)
        self.remove_button.pressed.connect(self.remove_pressed)

        self.add_button = QPushButton("Add entry", self)
        self.add_button.pressed.connect(self.add_pressed)

        # layout
        row2 = QWidget()
        row2_lay = QHBoxLayout()
        row2_lay.addWidget(self.remove_button)
        row2_lay.addWidget(self.add_button)
        row2_lay.setContentsMargins(0, 0, 0, 0)
        row2.setLayout(row2_lay)

        layout = QVBoxLayout()
        layout.addWidget(self.attrs_view)
        layout.addWidget(row2)

        self.setLayout(layout)

    @Slot(str)
    def update_node(
        self,
        path: str
    ):
        """Call this function to update for which node the attributes are shown.

        Parameters
        ----------
        path : str
            hdf5 node path
        """
        self.attrs_view.update_node(path)

    @Slot()
    def remove_pressed(self):
        self.attrs_view.remove_selected_rows()

    @Slot()
    def add_pressed(self):
        self.attrs_view.attrs_model.add_row()

    def scrollToTop(self):
        self.attrs_view.scrollToTop()