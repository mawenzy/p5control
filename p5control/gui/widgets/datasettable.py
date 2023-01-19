"""
This file defines the class DatasetTableView, which shows the contents of
a dataset
"""
import logging
from typing import Any

import h5py
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot
from qtpy.QtWidgets import QTableView, QHeaderView

from ...gateway import DataGateway

logger = logging.getLogger(__name__)


class DatasetTableModel(QAbstractTableModel):
    """Model representing the contents of the dataset
    
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
        self.data_view = None
        self.compound_names = None