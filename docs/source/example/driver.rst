
Driver
------

We start by implementing a driver of an instrument which magically measures a sine wave. The module ``p5control.drivers`` contains the class :class:`.BaseDriver`, which implements some common functionality for all drivers. This is necessary to work within the internal logic of `p5control`. In this module, you can also find some other drivers as an inspiration. We start our driver by importing the following packages and defining our custom class:

.. code-block:: py

    # exampleinst.py
    import time
    import logging

    import numpy as np
    from pycontrol.drivers import BaseDriver

    logger = logging.getLogger(__name__)

    class ExampleInst(BaseDriver):
        """your custom driver"""
        def __init__(self, name):
            self._name = name
            self._offset = np.random.rand() * 50

            self._amplitude = 1.1
            self._freq = 1

Here, we have already implemented an initialization function. Note that the ``name`` argument is required for your driver to work with p5control. We added a random offset, such that two instances of this driver will not produce the same data. This covers the case that you use the same instrument multiple times and use the same driver to control these instruments individually. The last two lines set some reasonable default values for the sine wave. The service structure of rpyc ensures that any private member (starting with '_') cannot be accessed by a client. We utilize this here to limit the functionality exposed to the client. At this point, it is useful to look at the documentation of :class:`.BaseDriver` to realize which functions we have to implement. First, we need a function to open the connection to the device and then one to close it after we have finished the experiment. In these, you will for example reset a device to a standard state and make sure it is working properly. Since our instrument does not really exist, we only log the function calls:

.. code-block:: py

    # exampleinst.py
    def open(self):
        logger.debug(f'{self._name}.open()')

    def close(self):
        logger.debug(f'{self._name}.close()')

As soon as the :class:`.InstrumentServer` will be running, a separate thread will be started. This one calls the function ``get_status`` for each driver in evenly spaced intervals. This can be used to automatically log e.g. the environment temperature and humidity over the whole time the instrument server is running. This function should return an ``numpy.ndarray`` with shape *1xn*. A timestamp will be added to make the shape *1x(n+1)* and it will then be stored into a dataset with hdf5 path ``"status/{name}"``. For our driver, we implement a status function which lets us track the amplitude and frequency of the sine wave.

.. code-block:: py

    # exampleinst.py
    def get_status(self):
        return np.array([[self._amplitude, self._freq]])

When measuring, a separate measurement thread is created for each instrument. Setup of the measurement by your device should be done by implementing ``setup_measuring``. Here you should write every initialization your instrument needs immediately before you can trigger the actual measurement to start. Since this might take longer for some devices, all threads wait for each other at a barrier for this initialization to complete. They are then all released simultaneously. Again, our imagined instrument does not need a setup. Immediately after all threads are released at the barrier, the function ``start_measuring`` is called, which we implement:

.. code-block:: py

    # exampleinst.py
    def start_measuring(self):
        self.last_time = time.time()

By saving this timestamp, we can determine the time we have been measuring for when ``get_data`` is called. We use this to emulate the bahavior of measuring ten times a second by implementing to following:

.. code-block:: py

    # exampleinst.py
    def get_data(self):
        logger.debug(f'{self._name}.get_data()')

        now = time.time()

        times = np.arange(self.last_time, now, 0.1)
        values = [self._amplitude * np.sin(self._freq*(t + 0.1*np.random.rand()) \
        + self._offset) + 0.3*np.random.rand() for t in times]
        values = np.array(values)

        # set time for next cycle
        self.last_time = now

        # format data to shape (length, 2)
        return np.concatenate((
            np.reshape(times, (len(times), 1)),
            np.reshape(values, (len(values), 1))
        ), axis=1)

At this point we have a driver which lets us continually monitor its status and allows for easy measurements. You are free to implement any additional logic you might need. Here, we just implement two setters to change the shape of the sine wave:

.. code-block:: py

    # exampleinst.py
    def setAmplitude(self, value):
        self._amplitude = value

    def setFrequency(self, value):
        self._freq = value
