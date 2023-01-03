
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
