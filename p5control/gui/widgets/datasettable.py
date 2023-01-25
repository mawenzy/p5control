"""
This file defines the class DatasetTableView, which shows the contents of
a dataset
"""
import logging
from typing import Any

import h5py
import numpy as np
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot
from qtpy.QtWidgets import QTableView, QHeaderView

from ...gateway import DataGateway

logger = logging.getLogger(__name__)


class DatasetTableModel(QAbstractTableModel):
    """Model representing the contents of the dataset. Implements lazy loading
    of rows, all columns are always loaded.
    
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
        self.row_count = 0
        self.column_count = 0
        self.ndim = 0
        self.dims = ()
        self.compound_names = None
        self.data_buffer = None

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

        self.beginResetModel()

        self.row_count = 0
        self.column_count = 0
        self.dims = ()
        self.data_buffer = None

        if isinstance(self.node, h5py.Dataset):
            self.ndim = self.node.ndim
            shape = self.node.shape
            self.compound_names = self.node.dtype.names

            if self.ndim == 1:
                self.row_count = shape[0]

                if self.compound_names:
                    self.column_count = len(self.compound_names)
                else:
                    self.column_count = 1
            elif self.ndim >= 2:
                self.row_count = shape[-2]
                self.column_count = shape[-1]

                # this indexes the first ten rows and all columns for the 
                # last two dimensions
                self.dims = tuple(([0] * (self.ndim - 2)) + [slice(0, 10), slice(None)])

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
        if role == Qt.DisplayRole:
            if self.compound_names and orientation == Qt.Horizontal:
                return self.compound_names[section]
            else:
                return str(section)

        super().headerData(section, orientation, role)

    def data(
        self,
        index: QModelIndex,
        role: int = ...
    ) -> Any:
        """return the data which should be shown at index. Works with 
        ``data_buffer``, such that the amount of requests made to the data
        server is limited, which would hinder performance.
        """
        if index.isValid() and role in (Qt.DisplayRole, Qt.ToolTipRole):
            column = index.column()
            row = index.row()

            # fill buffer such that ``row`` is contained
            if self.ndim <= 2:
                # fill buffer
                if self.data_buffer is None:
                    self.data_buffer = self.dgw.get_data(self.node.name, slice(0, 10))

                # extend buffer if new rows are requested
                while row >= len(self.data_buffer):
                    arr = self.dgw.get_data(
                        self.node.name,
                        slice(len(self.data_buffer), len(self.data_buffer) + 10)
                    )

                    if len(arr) == 0:
                        break

                    self.data_buffer.resize((self.data_buffer.shape[0] + arr.shape[0],) + self.data_buffer.shape[1:])

                    self.data_buffer[-arr.shape[0]:] = arr
            else:
                # fill buffer
                if self.data_buffer is None:
                    self.data_buffer = self.dgw.get_data(
                        self.node.name,
                        self.dims
                    )

                # extend data_buffer buffer
                while row >= len(self.data_buffer):

                    arr = self.dgw.get_data(
                        self.node.name,
                        self.dims[:-2] + (slice(len(self.data_buffer), len(self.data_buffer) + 10), slice(None))
                    )

                    if len(arr) == 0:
                        break

                    self.data_buffer.resize((self.data_buffer.shape[0] + arr.shape[0],) + self.data_buffer.shape[1:])

                    self.data_buffer[-arr.shape[0]:] = arr

            # access data from the buffer and return it
            if self.ndim == 1:
                if self.compound_names:
                    name = self.compound_names[column]
                    return str(self.data_buffer[name][row])
                else:
                    return str(self.data_buffer[row])
            
            elif self.ndim == 2:
                return str(self.data_buffer[row, column])

            elif self.ndim > 2:
                if self.data_buffer.ndim == 0:
                    return str(self.data_buffer)
                elif self.data_buffer.ndim == 1:
                    return str(self.data_buffer[row])
                elif self.data_buffer.ndim >= 2:
                    return str(self.data_buffer[row, column])

    def set_dims(self, dims):
        self.beginResetModel()

        self.dims = []
        self.shape = self.node.shape

        for i, value in enumerate(dims):

            try:
                v = int(value)
                self.dims.append(v)
            except (ValueError, TypeError):
                if ":" in value:
                    value = value.strip()
                    # https://stackoverflow.com/questions/680826/python-create-slice-object-from-string/23895339
                    s = slice(*map(lambda x: int(x.strip()) if x.strip() else None, value.split(':')))
                    self.dims.append(s)

        self.dims = tuple(self.dims)
        # self.data_view = self.node[self.dims]
        self.data_view = self.dgw.get_data(
            self.node.name,
            self.dims
        )

        try:
            self.row_count = self.data_view.shape[0]
        except IndexError:
            self.row_count = 1

        try:
            self.column_count = self.data_view.shape[1]
        except IndexError:
            self.column_count = 1

        self.endResetModel()


class DatasetTableView(QTableView):
    """``QTableView`` configured to show the contents of the dataset
    
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

        self.data_model = DatasetTableModel(self.dgw)
        self.setModel(self.data_model)


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
        self.data_model.update_node(path)

    @Slot(list)
    def update_dims(
        self,
        dims: list
    ):
        self.data_model.set_dims(dims)