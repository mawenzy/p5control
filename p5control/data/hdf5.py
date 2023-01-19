"""
This file provides an interface around an hdf5 file.
"""
import time
import logging
import threading
from typing import Tuple

import h5py
import numpy as np

logger = logging.getLogger(__name__)

class HDF5FileInterfaceError(Exception):
    """Exceptions concerning the HDF5FileInterface"""

class HDF5FileInterface():
    """Wrapper around an h5py.File with some added functionality for convenience. The file will be open after this class is initialized.
    
    Parameters
    ----------
    filename : str
        filename to use for storing the data
    """

    def __init__(
        self,
        filename: str,
    ):
        self._filename = filename

        self._f = None
        self._lock = threading.Lock()

        self._callbacks = {}
        self._callback_lock = threading.Lock()

        # open file
        self.open()

    def open(self):
        """Open file"""
        if self._f:
            raise Exception("Can't open h5py.File because it is already open")

        logger.info(f'opening file {self._filename}')
        self._f = h5py.File(self._filename, "a", libver="latest")

    def close(self):
        """Close file"""
        if not self._f:
            raise Exception("Can't close h5py.File because there is none open")

        logger.info(f'closing file {self._filename}')
        self._f.close()
        self._f = None

    def _create_dataset(
        self,
        path: str,
        arr: np.ndarray,
        maxshape: Tuple = None,
        chunks=True,
        **kwargs
    ):
        """Create hdf5 dataset at the specified path with data arr.

        Defaults to a datasest where the first axis is infinitely extendable.

        Parameters
        ----------
        path : str
            path in the hdf5 file
        arr : np.ndarray
            the array to save to the dataset
        maxshape : Tuple, optional
            specify maxshape for the dataset, defaults to shape of arr with
            first axis infinitely extendable
        chunks :
            wheter to use chunks
        **kwargs :
            set as attributes of the dataset
        """
        if maxshape is None:
            # make first axis appendable
            maxshape = (None,) + arr.shape[1:]

        dset = self._f.create_dataset(path, data=arr, maxshape=maxshape, chunks=chunks)
        
        # set attributes
        dset.attrs["created_on"] = time.ctime()

        for (key, value) in kwargs.items():
            dset.attrs[key] = value

        return dset

    def append(
        self,
        path: str,
        arr: np.ndarray,
    ) -> None:
        """Append ``arr`` to the dataset specified with ``path`` along the first axis. Create the dataset if no dataset at ``path`` exists. This one will have the dimensions of the array with the first axis being infinitely extendable.

        Any callback pointing to this path will be called and provided with the newly appended data.

        Parameters
        ----------
        path : str
            path in the hdf5 file
        arr : np.ndarray
            the array to append to the dataset
        
        Raises
        ------
        ValueError : if the secondary dimensions are not the same
        """
        # need this lock so that if two threads want to access a dataset
        # which has to be created do not both create it, raising a error
        with self._lock:
            try:
                dset = self._f[path]

                dset.resize(dset.shape[0] + arr.shape[0], axis=0)
                dset[-arr.shape[0]:] = arr

            except KeyError:
                dset = self._create_dataset(path, arr)
        # callbacks
        with self._callback_lock:
            for (id, (p, func)) in self._callbacks.copy().items():
                if p == path:
                    try:
                        func(arr)
                    except EOFError:
                        logger.info(
                            f'Can\'t connect to callback "{id}", removing it.'
                        )
                        self._callbacks.pop(id) 

    def register_callback(
        self,
        id: str,
        path: str,
        func
    ) -> None:
        """Add a callback to call when data is appended to the dataset at `path`,
        called with func(arr)

        Parameters
        ----------
        id : str
            used to identify this callback and be able to remove it
        path : str
            path in the hdf5 file
        func : function(np.ndarray)
            function to call
        """
        if id in self._callbacks:
            raise Exception(
                f'Can\'t register_callback with id "{id}", because it already exists.'
            )

        logger.info(f'registering callback "{id}" for dataset: "{path}"')
        self._callbacks[id] = [path, func]

    def remove_callback(
        self,
        id: str,
    ):
        """remove callback specified by ``id``.
        
        Raises
        ------
        KeyError
            if there exists no callback with ``id``
        """
        with self._callback_lock:
            logger.info(f'removing callback "{id}"')
            self._callbacks.pop(id)

    def get_dataset(
        self, 
        path: str,
    ):
        """Return the data from the specified dataset. If is preffered to use :meth:`p5control.data.hdf5.HDF5FileInterface.get_dataset_slice` to not transfer to much data. 
        
        Parameters
        ----------
        path : str
            path in the hdf5 file
            
        Raises
        ------
        HDF5FileInterfaceError
            if the hdf5 object is not a dataset
        KeyError
            if there exists no object at the path
        """
        dset = self._f[path]

        if not isinstance(dset, h5py.Dataset):
            raise HDF5FileInterfaceError(
                f'hdf5 object at path "{path}" is not a Dataset'
            )

        return dset[()]

    def get_dataset_slice(
        self,
        path: str,
        slice,
    ):
        """Return the data from the specified dataset, indexed with the slice.

        Parameters
        ----------
        path : str
            path in the hdf5 file
        slice
            slice to index the desired data

        Raises
        ------
        HDF5FileInterfaceError
            if the hdf5 object is not a dataset
        KeyError
            if there exists no object at the path
        """
        dset = self._f[path]

        if not isinstance(dset, h5py.Dataset):
            raise HDF5FileInterfaceError(
                f'hdf5 object at path "{path}" is not a Dataset'
            )

        return dset[slice]

    def values(
        self,
        path: str,
    ):
        return self._f[path].values()

    def items(
        self,
        path: str,
    ):
        return self._f[path].items()

    def keys(
        self,
        path: str,
    ):
        return self._f[path].keys()

    def get(
        self,
        path: str,
    ):
        return self._f[path]

    def shape(
        self,
        path: str,
    ):
        return self._f[path].shape

    def get_file_handle(self):
        """do not use!!! bad!!"""
        return self._f
