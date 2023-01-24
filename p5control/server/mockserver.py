from p5control import InstrumentServer, inserv_cli
from p5control import drivers

inserv = InstrumentServer()

#            name    class
inserv._add('inst1', drivers.MockInst)
inserv._add('inst2', drivers.MockInst)

inserv.start()

inserv_cli(inserv)