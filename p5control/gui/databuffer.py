"""
This file defines a data buffer which collects data for a dataset on the
data server.
"""
import threading
import logging

import numpy as np
from rpyc.utils.classic import obtain

from ..gateway import DataGateway
from .guisettings import DATA_BUFFER_MAX_LENGTH, DOWN_SAMPLE

logger = logging.getLogger(__name__)

class DataBuffer:
    """
    DataBuffer which subscribes to a path on the dataserver and buffers
    the incoming new data.

    Parameters
    ----------
    dgw : DataGateway
        gateway to the dataserver
    path : str
        dataset path in the hdf5 file
    max_length : int
        upper limit for the buffer length
    down_sample : int
        only safe every down_sample'th value
    """

    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        max_length: int = DATA_BUFFER_MAX_LENGTH,
        down_sample: int = DOWN_SAMPLE,
    ):
        self.dgw = dgw
        self.path = path
        self.max_length = max_length
        self.down_sample = down_sample

        self.data = None
        self.data_lock = threading.Lock()

        # try to get existing data
        try:
            data = self.dgw.get_data(path, 
                    slice(-self.max_length*self.down_sample, None, self.down_sample))
            self.data = data
        except KeyError:
            pass

        self.callid = self.dgw.register_callback(path, self.callback)

    def callback(self, arr):
        """
        Callback which extends the array. If the buffer gets longer than the maximum length,
        the starting values are deleted and the buffer length is limited to the maximum length.

        Parameters
        ----------
        arr : np.array, dict
            the new data to append to the dataset
        """
        with self.data_lock:
            arr = obtain(arr)
            if self.down_sample > 1:
                if isinstance(arr, dict):
                    arr = {k: v[::self.down_sample] for k,v in arr.items()}
                else:
                    arr = arr[::self.down_sample]

            if self.data is None:
                self.data = arr
            else:
                self.data = np.concatenate((self.data, arr))

            if self.data.shape[0] > self.max_length:
                self.data = self.data[len(arr):]

    def cleanup(self):
        """
        Remove callback
        """
        self.dgw.remove_callback(self.callid)

    def clear(self):
        """
        Clear data buffer
        """
        with self.data_lock:
            self.data = None

    def reload(
        self,
        max_length: int = None,
        down_sample: int = None,
    ):
        """
        update ``max_length`` and/or ``down_sample`` and reload the buffered data from the dataset.
        """
        max_length = self.max_length if max_length is None else max_length
        down_sample = self.down_sample if down_sample is None else down_sample

        # this should ideally be in the locked part, but it runs into problems, see:
        # https://github.com/tomerfiliba-org/rpyc/issues/522,
        # because the dgw request can handle an incoming callback, which then also tries to lock,
        # which then does no longer work
        try:
            data = self.dgw.get_data(self.path, slice(-max_length*down_sample, None, down_sample))
        except KeyError:
            return

        with self.data_lock:
            self.max_length = max_length
            self.down_sample = down_sample

            self.data = data
