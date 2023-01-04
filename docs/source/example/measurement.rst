
Measurement
-----------

Of course you want to perform measurements with your experimental setup. Since the data acquired can quickly result in large file sizes, *p5control* provides simple syntax in form of the :class:`.Measurement` class to control when measurements are performed.

.. note::
    If you want to track slow changing variables of your setup, use :class:`.BaseDriver` ``.get_status``, which by default is called every ten seconds.

Obtain a measurement from the gateway for the instrument server.

.. code-block:: py

    >>> m = gw.measure("name")

If no name is provided, the measurement will receive a unique name similar to `m000000`. The correspondig data is saved under the hdf5 group ``measurement/name``. Support for the python context manager is included and therefore you can perform an experiment and measure your instruments using the code structure

.. code-block:: py

    with gw.measure() as m:

        # do your experiment logic here

    # only executed after all devices have stopped measuring 

When entering the context manager, a threading barrier is used to ensure that all drivers have time to setup their corresponding devices. Only after this has been completed, the inner logic will be executed. Here you can perform sweeps and everything necessary for your experiment. If you need to get access to the data as it is obtained, use a :class:`.DataGateway`. After this logic has completed, the data acquisition stops and the drivers can reset the devices to a desired idle state. Again, a threading barrier waits for all drivers to complete this step. Then any remaining code in the script will be run.