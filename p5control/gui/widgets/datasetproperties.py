"""
This file defines the class DatasetPropertiesTableView, which shows information
about a dataset, e.g. name, dtype, ndim ...
"""
import logging 
from typing import Any

import h5py
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot
from qtpy.QtWidgets import QTableView

from ...gateway import DataGateway

logger = logging.getLogger(__name__)

class DatasetPropertiesTableModel(QAbstractTableModel):
    """Model representing information about the dataset, e.g. name, dtype, ndim...
    
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

        self.keys = []
        self.values = []

        self.beginResetModel()

        if isinstance(self.node, h5py.Dataset):
            self.keys = (
                'name', 'dtype', 'ndim', 'shape',
                'maxshape', 'chunks', 'compression', 'shuffle',
                'fletcher32', 'scaleoffset',
            )

            self.values = (
                str(self.node.name), str(self.node.dtype), str(self.node.ndim), str(self.node.shape),
                str(self.node.maxshape), str(self.node.chunks), str(self.node.compression), str(self.node.shuffle),
                str(self.node.fletcher32), str(self.node.scaleoffset),
            )

        self.row_count = len(self.keys)
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
        HEADERS = ('Name', 'Value')

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
        if index.isValid() and role in (Qt.DisplayRole, Qt.ToolTipRole):
            column = index.column()
            row = index.row()

            if column == 0:
                return self.keys[row]
            elif column == 1:
                return self.values[row]

class DatasetPropertiesTableView(QTableView):
    """``QTableView`` configured to show the properties of the dataset
    
    Parameters
    ----------
    dgw : DataGateway
        gateway to the data server
    """

    def __init__(
        self,
        dgw : DataGateway,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.dgw = dgw

        self.dataset_model = DatasetPropertiesTableModel(self.dgw)
        self.setModel(self.dataset_model)

        # self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        self.dataset_model.update_node(path)