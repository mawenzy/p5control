import threading

import numpy as np
from rpyc.utils.classic import obtain

from ..gateway import DataGateway
from .guisettings import DATA_BUFFER_MAX_LENGTH, DOWN_SAMPLE, id_generator

class DataBuffer:
    """DataBuffer which subscribes to a path on the dataserver and buffers
    the incoming new data."""
    
    def __init__(
        self,
        dgw: DataGateway,
        path: str,
        max_length: int = DATA_BUFFER_MAX_LENGTH,
        down_sample: int = DOWN_SAMPLE,
    ):
        """
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
        self.dgw = dgw
        self.max_length = max_length
        self.down_sample = down_sample

        self.id = next(id_generator)
        self.data = None
        self.data_lock = threading.Lock()

        # try to get existing data
        try:
            data = self.dgw.get_dataset_slice(path, slice(-self.max_length*self.down_sample, None, self.down_sample))
            self.data = data
        except KeyError:
            pass

        self.dgw.register_callback(self.id, path, self.callback)

    def callback(self, arr):
        """Callback which extends the array and deletes starting values
        if is gets too long."""
        arr = obtain(arr)
        if self.down_sample > 1:
            arr = arr[::self.down_sample]

        with self.data_lock:
            if self.data is None:
                self.data = arr
            else:
                self.data = np.concatenate((self.data, arr))

            if self.data.shape[0] > self.max_length:
                self.data = self.data[len(arr):]

    def cleanup(self):
        """Remove callback"""
        self.dgw.remove_callback(self.id)

    def clear(self):
        """Clear data"""
        with self.data_lock:
            self.data = None