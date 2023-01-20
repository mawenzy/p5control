"""
This file defines the class AttributesTableView, which shows
the attributes of a element in the hdf5 file and lets you edit them.

ExtendableAttributesTableView extends this and lets you add and remove attributes.
"""
import logging
from typing import Any

from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot
from qtpy.QtWidgets import (
    QTableView, QHeaderView, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
)

from ...gateway import DataGateway
from ...util import name_generator

logger = logging.getLogger(__name__)

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

    def __init__(
        self,
        dgw: DataGateway,
        editable: bool = True
    ):
        super().__init__()

        self.dgw = dgw
        self.editable = editable

        self.node = None
        self.column_count = 3
        self.row_count = 0

    def update_node(self, path):
        """
        Update the hdf5 path and then update model

        Parameters
        ----------
        path : str
            hdf5 path for the inspected group or dataset
        """
        self.node = self.dgw.get(path)
        self.update_model()
 
    def update_model(self):
        """Reset model and refetch the attributes from the data server. Since the order
        of the elements depends on the iterate order of the dictionary, this might change
        the order in which things appear in the table."""
        if not self.node:
            return

        self.beginResetModel()

        self.keys = list(self.node.attrs.keys())
        self.values = list(self.node.attrs.values())
        self.classes = [val.__class__.__name__ for val in self.values]

        self.row_count = len(self.keys)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return self.row_count
    
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
            else:
                return str(section)

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        """return the data which should be shown at index"""
        if index.isValid():
            column = index.column()
            row = index.row()

            if role in (Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole):

                if column == 0:
                    return self.keys[row]
                elif column == 1:
                    return str(self.values[row])
                elif column == 2:
                    return self.classes[row]

    def flags(self, index):
        """return flags to make attributes editable or not"""
        if self.editable:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        else:
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

            old_key = self.keys[row]
            old_value = self.values[row]
            old_class = self.classes[row]

            if column == 0:
                if value in self.keys:
                    # stop overwriting of data
                    return False

                # try removing old entry
                if self.node.attrs.pop(old_key):
                    # add new entry to database
                    self.node.attrs[value] = old_value
                    # update model
                    self.keys[row] = value

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
                        logger.info(
                            f'Failed to convert "{new_value}" to int'
                        )
                        return False
                elif new_class in ['float', 'float32', 'float64']:
                    try:
                        new_value = float(new_value)
                    except ValueError:
                        logger.info(
                            f'Failed to convert "{new_value}" to float'
                        )
                        return False
                else:
                    # unknown class, skipping
                    logger.info(f"Unknown class {new_class}")
                    return False

                # change database entry
                self.node.attrs[old_key] = new_value
                # update model
                self.values[row] = str(new_value)
                self.classes[row] = new_class

                self.dataChanged.emit(index, index, [])
                return True              

        return False

    def add_row(self):
        """Add an extra row to the attributes, row is filled
        with a standard key and value."""
        # a node has to be selected
        if not self.node:
            return 

        self.beginInsertRows(
            self.index(self.row_count, 0),
            self.row_count + 1,
            self.row_count + 1
        )
        
        gen = name_generator("key", width=2)
        key = next(gen)

        # search for new key
        while True:
            if key in self.keys:
                key = next(gen)
            else:
                break

        # add database entry
        self.node.attrs[key] = "new"

        # update model
        self.keys.append(key)
        self.values.append("new")
        self.classes.append("str")

        self.row_count += 1

        self.endInsertRows()

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        """remove row specified with ``row`` from the attributes"""
        if row < self.row_count:
            # remove it on data server
            self.node.attrs.pop(self.keys[row])

            # reload model from server
            self.update_model()


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