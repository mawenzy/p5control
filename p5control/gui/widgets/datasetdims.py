"""
This file defines the class DatasetDimsTableView, which lets you select
which dimensions should be shown in datasettable for a dataset.
"""
import logging 
from typing import Any, Iterable

import h5py
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot, Signal
from qtpy.QtWidgets import QTableView

from ...gateway import DataGateway

logger = logging.getLogger(__name__)

class DatasetDimsTableModel(QAbstractTableModel):
    """Model representing the slices for a dataset.
    
    Parameters
    ----------
    dgw : DataGateway
        the gateway to the data server
    """

    def __init__(
        self,
        dgw: DataGateway
    ):
        super().__init__()

        self.dgw = dgw

        self.node = None
        self.column_count = 2
        self.row_count = 0
        self.shape = ()

    def update_node(self, path):
        """
        Update the hdf5 path and then update model

        Parameters
        ----------
        path : str
            hdf5 path for the dataset
        """
        self.node = self.dgw.get(path)
        self.update_model()

    def update_model(self):
        """
        Reset model and refetch the information from the data server.
        """
        if not self.node:
            return

        self.row_count = 0
        self.shape = ()

        self.beginResetModel()

        if isinstance(self.node, h5py.Dataset) and self.node.ndim > 2:
            self.shape = (['0'] * (self.node.ndim - 2)) + [':', ':']
            self.row_count = len(self.shape)

        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return self.row_count

    def columnCount(self, parent=QModelIndex()):
        return self.column_count

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = ...
        ) -> Any:
        """responsible for setting the header names."""
        HEADERS = ('Dim', 'Index')

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return HEADERS[section]
            else:
                return str(section)

    def data(
        self,
        index: QModelIndex,
        role: int = ...
    ) -> Any:
        """return the data which should be shown at index."""
        if index.isValid() and role in (Qt.DisplayRole, Qt.ToolTipRole, Qt.EditRole):
            column = index.column()
            row = index.row()

            if column == 0:
                return str(row)
            elif column == 1:
                return self.shape[row]

    def flags(self, index):
        """make second column editable"""
        flags = super().flags(index)
        if index.column() == 1:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = ...
    ) -> bool:
        """Called when setting data"""
        if index.isValid() and role == Qt.EditRole:
            row = index.row()
            value = value.strip()

            if ':' not in value:
                try:
                    num = int(value)
                    if num < 0 or num >= self.node.shape[row]:
                        return False
                except ValueError:
                    return False
            else:
                # try conversion which will be performed in DatasetTableModel
                # ``set_dims`` make sure it works 
                try:
                    s = slice(*map(lambda x: int(x.strip()) if x.strip() else None, value.split(':')))
                except ValueError:
                    return False
            
            self.shape[row] = value
            self.dataChanged.emit(index, index, [])
            return True

        return False


class DatasetDimsTableView(QTableView):
    """``QTableView`` configured to show the properties of the dataset
    
    Parameters
    ----------
    dgw : DataGateway
        gateway to the data server
    """

    dimsChanged = Signal(list)
    """emitted if the dims are changed"""

    def __init__(
        self,
        dgw : DataGateway,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.dgw = dgw

        self.dims_model = DatasetDimsTableModel(self.dgw)
        self.setModel(self.dims_model)

        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()

        self.dims_model.dataChanged.connect(self._onDataChanged)

    def _onDataChanged(
        self,
        topLeft: QModelIndex,
        bottomRight: QModelIndex,
        roles: Iterable[int] = ...
    ):
        dims = self.dims_model.shape

        self.dimsChanged.emit(dims)

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
        self.dims_model.update_node(path)