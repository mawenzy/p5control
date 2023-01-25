"""
This file provides an interface around an hdf5 file.
"""
import time
import logging
import threading
from typing import Tuple, Union, Any

import h5py
import numpy as np

from ..util import name_generator

logger = logging.getLogger(__name__)

# unique id generator for callbacks
id_generator = name_generator(
    "id",
    width=4,
)
id_generator_lock = threading.Lock()

def get_callback_id():
    """Thread save id generator for unique callback ids."""
    with id_generator_lock:
        newid = next(id_generator)
    return newid

class HDF5FileInterfaceError(Exception):
    """Exceptions concerning the HDF5FileInterface"""

class HDF5FileInterface():
    """Wrapper around an h5py.File with some added functionality for convenience. The file will be
    open after this class is initialized.

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

        # callbacks for adding data to a dataset
        self._dset_callbacks = {}
        self._dset_callback_lock = threading.Lock()

        # callbacks for adding new elements below a group
        self._grp_callbacks = {}
        self._grp_callback_lock = threading.Lock()

        # open file
        self.open()

    def open(self):
        """Open file in mode 'a'"""
        if self._f:
            raise Exception("Can't open h5py.File because it is already open")

        logger.info('opening file %s', self._filename)
        self._f = h5py.File(self._filename, "a", libver="latest")

    def close(self):
        """Close file"""
        if not self._f:
            raise Exception("Can't close h5py.File because there is none open")

        logger.info('closing file %s', self._filename)
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
        arr: Union[np.ndarray, dict[str, list[Any]]],
        **kwargs,
    ) -> None:
        """Append ``arr`` to the dataset specified with ``path`` along the first
        axis. Create the dataset if no dataset at ``path`` exists. This one will
        have the dimensions of the array with the first axis being infinitely extendable.

        Any callback pointing to this path will be called and provided with the newly appended data.

        Parameters
        ----------
        path : str
            path in the hdf5 file
        arr : np.ndarray or dic
            the array to append to the dataset
            if a dictionary is povided, it should be of the form dict[str, list[Any]]
        **kwargs :
            set as attributes of the dataset

        Raises
        ------
        ValueError : if the secondary dimensions are not the same
        """
        # need this lock so that if two threads want to access a dataset which has to be created
        # do not both create it, raising a error
        with self._lock:
            try:
                dset = self._f[path]

                if isinstance(arr, dict):
                    # convert dict to compound type array, making sure to use the
                    # same tuple ordering as in dset
                    arr = np.fromiter(
                        zip(*[arr[k] for k in dset.dtype.names]),
                        dtype = dset.dtype
                    )

                dset.resize(dset.shape[0] + arr.shape[0], axis=0)
                dset[-arr.shape[0]:] = arr

            except KeyError:
                # dataset does not exist, create it
                if isinstance(arr, dict):
                    # convert dict to compound type array
                    def get_type(k, xorarray):
                        try:
                            return (k, xorarray.dtype, xorarray.shape)
                        except AttributeError:
                            return (k, type(xorarray))

                    arr = np.fromiter(
                        zip(*arr.values()),
                        dtype=[get_type(k, arr[k][0]) for k in arr.keys()]
                    )

                dset = self._create_dataset(path, arr)

        # set attributes
        for (key, value) in kwargs.items():
            dset.attrs[key] = value

        # callbacks
        with self._dset_callback_lock:
            for (callid, (callpath, func)) in self._dset_callbacks.copy().items():
                if callpath == path:
                    try:
                        logger.debug('calling callback %s for %s', callid, path)
                        #TODO: as this code stands, if a dict comes in, at this
                        # point arr is no longer a dict but converted to a
                        # compound array, is this intentional???
                        func(arr)
                    except EOFError:
                        logger.info('Can\'t connect to callback "%s", removing it.', callid)
                        self._dset_callbacks.pop(callid)

    def register_callback(
        self,
        path: str,
        func,
        is_group: bool = False,
    ) -> None:
        """Add a callback to call when data is appended to the dataset at `path`,
        called with func(arr)

        Parameters
        ----------
        path : str
            path in the hdf5 file
        func : function(np.ndarray)
            function to call

        Returns
        -------
        id : str
            unique id to identify this callback and be able to remove it
        """
        callid = get_callback_id()

        if is_group:
            logger.info('registering callback "%s" for group: "%s"', callid, path)
            with self._grp_callback_lock:
                self._grp_callbacks[callid] = (path, func)
        else:
            logger.info('registering callback "%s" for dataset: "%s"', callid , path)
            with self._dset_callback_lock:
                self._dset_callbacks[callid] = (path, func)

        return callid

    def remove_callback(
        self,
        callid: str,
    ):
        """remove callback specified by ``id``.

        Raises
        ------
        KeyError
            if there exists no callback with ``id``
        """
        with self._dset_callback_lock:
            if callid in self._dset_callbacks:
                logger.info('removing callback "%s"', callid)
                self._dset_callbacks.pop(callid)
                return

        with self._grp_callback_lock:
            if callid in self._grp_callbacks:
                logger.info('removing callback "%s"', callid)
                self._grp_callbacks.pop(callid)
                return

        raise HDF5FileInterfaceError(
            f'Can\'t remove callback with id "{id}" because non exists.'
        )

    def get_data(
        self,
        path: str,
        indices: slice = (),
        field: str = None,
    ):
        """Return the data from a dataset, indexed with field and
        then slice:

        .. code-block:: py

            if field:
                return dset[field][slice]
            else:
                return dset[slice]

        Parameters
        ----------
        path : str
            path in the hdf5 file
        indices : slice, optional = ()
            slice to in dex the desired data, use "()" for all data
        field: str, optional
            can be used to specify fields for a compound dataset

        Raises
        ------
        HDF5FileInterfaceError
            if the hdf5 file object is not a dataset
        KeyError
            if there exists no object at the path
        """
        dset = self._f[path]

        if not isinstance(dset, h5py.Dataset):
            raise HDF5FileInterfaceError(
                f'hdf5 object at path "{path}" is not a Dataset'
            )

        if field:
            return dset[field][indices]

        return dset[indices]

    def get(
        self,
        path: str,
    ):
        """Return an objecte from the hdf5 file, specified with path. Use this to
        access its children or attributes. If you want to get data from a datset,
        use :meth:`get_data`
        """
        return self._f[path]
