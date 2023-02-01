"""
This file provides an interface around an hdf5 file provided by ``h5py.File``.
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
    logger.debug('generated id "%s"', newid)
    return newid

class HDF5FileInterfaceError(Exception):
    """Exceptions concerning the HDF5FileInterface"""

class HDF5FileInterface():
    """Wrapper around an ``h5py.File`` with some added functionality for convenience. The file will
    be open after this class is initialized.

    Parameters
    ----------
    filename : str
        filename to use for storing the data
    """

    def __init__(
        self,
        filename: str,
    ):
        logger.debug('filename "%s"', filename)
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
        """Open file in mode 'a'."""
        if self._f:
            raise Exception("Can't open h5py.File because it is already open")

        logger.info('opening file "%s" in mode "a"', self._filename)
        self._f = h5py.File(self._filename, "a", libver="latest")

    def close(self):
        """Closes file the file and removes all callbacks."""
        if not self._f:
            raise Exception("Can't close h5py.File because there is none open")

        # removing callbacks
        logger.debug('removing all dataset callbacks')
        with self._dset_callback_lock:
            for key in self._dset_callbacks.copy():
                self._dset_callbacks.pop(key)

        logger.debug('removing all group callbacks')
        with self._grp_callback_lock:
            for key in self._grp_callbacks.copy():
                self._grp_callbacks.pop()

        logger.info('closing file "%s"', self._filename)
        self._f.close()
        self._f = None

    def append(
        self,
        path: str,
        arr: Union[np.ndarray, dict[str, list[Any]]],
        **kwargs,
    ) -> None:
        """
        Append `arr` to the dataset specified with `path` along the first axis. Creates the dataset
        if no dataset at `path` exists. This one will have the dimensions of the array with the
        first axis being infinitely extendable. Does nothing if ``len(arr) == 0``.

        Any callback pointing to this path will be called and provided with the newly appended
        data, but converted to a numpy structured array.

        Parameters
        ----------
        path : str
            path in the hdf5 file
        arr : np.ndarray or dic
            the data to append to the dataset
        **kwargs :
            set as attributes of the dataset

        Raises
        ------
        ValueError : if the secondary dimensions are not the same

        Examples
        --------

        The data provided can be either a numpy array or a dictionary. If you want to add a row
        with three columns, you can for example use:

        .. code-block:: py

            >>> append('my_dataset', np.array([[1,2,3]]))

        Note that the type of the dataset in the hdf5 file is fixed after creating it. In this
        case, the type would be ``int64``. If you want to safe floating point numbers, make sure
        to use ``1.0``. For convenience, data can also be provided in the form of a dictionary.
        This is then automatically converted to a structured array with the keys of the dictionary
        determining the fields. For example:

        .. code-block:: py

            >>> append("dic_dset", {"time": 1.2, "freq": 2.3})
            >>> get_data("dic_set")
            array([(1.2, 2.3)], dtype=[('time', '<f8'), ('freq', '<f8')])

        In addition, you can also provide a list instead of just single values to add multiple
        columns at the same time. Internally, python's ``zip`` is used, so new rows are only
        appended until the first of the iterators does not have any additional elements.

        .. code-block:: py

            >>> append("dic_list", {"time": [1.0, 1.1, 1.2], "freq": [2.3, 0.6, 1.6]})
            >>> dgw.get_data("dic_list")
            array([(1. , 2.3), (1.1, 0.6), (1.2, 1.6)], dtype=[('time', '<f8'), ('freq', '<f8')])

        Instead of numbers, you can also add an numpy array as a value. This is restricted to
        numpy arrays because the underlying h5py library needs to know the size the element
        will need, and therefore only types with known size are accepted (e.g. you can't add a
        ``list`` with arbitrary length). Note that if the values of the dictionary are lists,
        the previous case applies.

        .. code-block:: py

            >>> append("dic_arr", {"a": 1, "b": np.array([[2,3], [1,0]])})
            >>> dgw.get_data("dic_arr")
            array([(1, [[2, 3], [1, 0]])], dtype=[('a', '<i8'), ('b', '<i8', (2, 2))])
        """
        # skip emtpy data
        if len(arr) == 0:
            return

        # need this lock so that if two threads want to access a dataset which has to be created
        # do not both create it, raising a error
        with self._lock:
            try:
                dset = self._f[path]
            except KeyError:
                # dataset does not exist, create it
                arr = self._convert_to_array(arr)
                dset = self._create_dataset(path, arr)
            else:
                # dataset exists, append to it
                arr = self._convert_to_array(arr, dset.dtype)

                logger.debug('appending data to "%s"', path)
                dset.resize(dset.shape[0] + arr.shape[0], axis=0)
                dset[-arr.shape[0]:] = arr

        # set attributes
        for (key, value) in kwargs.items():
            logger.info('attribute for "%s", "%s" : %s', path, key, value)
            dset.attrs[key] = value

        # callbacks
        with self._dset_callback_lock:
            for (callid, (callpath, func)) in self._dset_callbacks.copy().items():
                if callpath == path:
                    try:
                        logger.debug('calling callback "%s" for "%s"', callid, path)
                        func(arr)
                    except EOFError:
                        logger.info('Can\'t connect to callback "%s", removing it.', callid)
                        self._dset_callbacks.pop(callid)

    def _convert_to_array(
        self,
        arr: Union[np.ndarray, dict[str, list[Any]]],
        dtype = None
    ):
        """
        Converts a dictionary to a numpy structured array. If given an array, it does nothing
        and returns the array unchanged.

        Parameters
        ----------
        arr : Union[np.ndarray, dict[str, list[Any]]]
            the array or dictionary
        dtype : optional, None
            if provided, the dictionary is converted to this dtype, otherwise the dtype is
            automatically determined from the dictionary
        """
        if isinstance(arr, dict):
            for val in arr.values():
                val_type = type(val)
                break

            if dtype is None:
                # determine dtype
                def get_type(k, xorarray):
                    try:
                        return (k, xorarray.dtype, xorarray.shape)
                    except AttributeError:
                        return (k, type(xorarray))

                if val_type == list:
                    dtype = np.dtype([get_type(k, arr[k][0]) for k in arr.keys()])
                else:
                    dtype = np.dtype([get_type(k, arr[k]) for k in arr.keys()])

            # convert dict to compound type array, making sure to use the same tuple ordering
            try:
                if val_type == list:
                    arr = np.fromiter(
                        zip(*[arr[k] for k in dtype.names]),
                        dtype = dtype
                    )
                else:
                    arr = np.fromiter(
                        zip(*[[arr[k]] for k in dtype.names]),
                        dtype = dtype
                    )
            except KeyError as error:
                raise KeyError(f'Error when converting {arr} to dtype {dtype}, '
                    'likely due to mismatched keys in the dictionary and dtype') from error
            except ValueError as error:
                logger.critical(f'conversion failed from {arr} to dtype {dtype}')
                raise error

        return arr

    def _create_dataset(
        self,
        path: str,
        arr: np.ndarray,
        maxshape: Tuple = None,
        chunks=True,
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

        Returns
        -------
        the created dataset : h5py.Dataset
        """
        if maxshape is None:
            # make first axis appendable
            maxshape = (None,) + arr.shape[1:]

        logger.debug(
            'creating dataset "%s" with maxshape %s and dtype %s', path, maxshape, arr.dtype
        )
        dset = self._f.create_dataset(path, data=arr, maxshape=maxshape, chunks=chunks)

        # set attribute
        logger.debug('attribute for "%s", "created_on"', path)
        dset.attrs["created_on"] = time.ctime()

        # callbacks
        with self._grp_callback_lock:
            for (callid, (callpath, func)) in self._grp_callbacks.copy().items():
                if path.startswith(callpath):
                    try:
                        logger.debug('calling group callback "%s" for "%s"', callid, path)
                        func(path)
                    except EOFError:
                        logger.info('Can\'t connect to callback "%s", removing it.', callid)
                        self._grp_callbacks.pop(callid)

        return dset

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
            f'Can\'t remove callback with id "{callid}" because non exists.'
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

        logger.debug('dataset "%s", field: %s, indices %s', path, field, indices)

        if field:
            return dset[field][indices]

        return dset[indices]

    def get(
        self,
        path: str,
    ):
        """
        Return an object from the hdf5 file, specified with path. Use this to access its children
        or attributes. If you want to get data from a datset, use :meth:`get_data`
        """
        logger.debug('path "%s"', path)
        return self._f[path]
