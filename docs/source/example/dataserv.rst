Data Server
-----------

With the instrument server running, a second data server has been automatically started. Furthermore, the status of the device our driver represents is being logged in the background. To communicate with the data server, we again open a gateway:

.. code-block:: py

    >>> from p5control import DataGateway
    >>> dgw = DataGateway()
    >>> dgw.connect()

The data server is just a basic wrapper around an hdf5 file, shipped through :class:`.HDF5FileInterface`. The actual file lies in the directory ``.data/``. Take a look at the documentation to learn about the available methods. After the server has been stopped, you are free to open this file and use the data contained within in further calculations. Using

.. code-block:: py

    >>> dgw.get("/")
    <HDF5 group "/" (1 members)>

we can obtain the root group object of the hdf5 file. A group can be thougth of as a folder, which can contain other folders or datasets. The members of this folder can be listed with 

.. code-block:: py

    >>> dgw.get("/").keys()
    <KeysViewHDF5 ['status']>
    >>> dgw.get("status").keys()
    <KeysViewHDF5 ['inst1', 'inst2']>

This tells us that the root group contains a group with name `status`. This group itself contains two datasets with names `inst1` and `inst2`. These contain the values of the status of the devices for the time the instrument server has been running for. To get the result from the last 5 status requests, use

.. code-block:: py

    >>> dgw.get_data("status/inst1", slice(-5, None))
    array([[1.67283823e+09, 1.10000000e+00, 2.00000000e+00],
       [1.67283824e+09, 1.10000000e+00, 2.00000000e+00],
       [1.67283825e+09, 1.10000000e+00, 2.00000000e+00],
       [1.67283826e+09, 1.10000000e+00, 2.00000000e+00],
       [1.67283827e+09, 1.10000000e+00, 2.00000000e+00]])

Of course the exact values will be different.

.. note::
    Note that :class:`.DataGateway` wraps ``get_dataset_slice`` with the ``obtain`` function from ``rpyc.util.classic``. This makes sure that the numpy array is correctly copied from the remote to the client. If you run into problems when transferring data between server and client (both directions) make sure to use ``obtain``.

Callbacks
=========

The symmetric rpyc protocol behind the data server allows the server to make requests to the client. This can be used to notify the client if a dataset has received new data. For this, the client needs to be able to also handle incoming requests, which can be enabled using:

.. code-block:: py

    >>> from p5control import DataGateway
    >>> dgw = DataGateway(allow_callback=True)
    >>> dgw.connect()

Registering a callback to be notified with the newly added data is as easy as:

.. code-block:: py

    >>> id = dgw.register_callback("status/inst1", lambda arr: print(arr))

with an unique id for this callback, the path to the dataset in question and the function which should be called each time new data is added.

.. note::
    Make sure to use ``obtain`` if you plan to do any manipulations off the array containing the new data

Callbacks can be removed again using their id.

.. code-block:: py

    >>> dgw.remove_callback("someID")