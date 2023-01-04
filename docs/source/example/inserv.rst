
Instrument server
-----------------

The instrument server will hold two instances of our custom driver. This is as easy as defining the :class:`.InstrumentServer` object and then adding two instruments by providing a name and the correspondig class.

.. code-block:: py

    # inserv.py
    from p5control import InstrumentServer, inserv_cli
    from p5control import drivers

    inserv = InstrumentServer()

    #            name    class
    inserv._add('inst1', drivers.ExampleInst)
    inserv._add('inst2', drivers.ExampleInst)

    inserv.start()

    inserv_cli(inserv)

The last line starts a command line interface which lets the user interact with the running instrument server. With the instrument server running, we can open a jupyter notebook and open a gateway:

.. code-block:: py

    >>> from p5control import InstrumentGateway
    >>> gw = InstrumentGateway()
    >>> gw.connect()

Accessing the two drivers is possible by using the ``name`` used when adding them to the instrument server

.. code-block:: py

    >>> gw.inst1
    <p5control.drivers.exampleinst.ExampleInst object at 0x7f91b2b3b5b0>

At this point we can easily access any function defined in our driver. As an example, we can set the frequency using

.. code-block:: py

    >>> gw.inst1.setFrequency(2.0)

to a different value and then ask the driver for its status

.. code-block:: py

    >>> gw.inst1.get_status()
    array([[1.1, 2. ]])

to control that the status has been changed.