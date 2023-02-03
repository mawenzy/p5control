# setup logging
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='bluefors_server.log',
    level=logging.DEBUG,
    filemode='w', # overwrites logs every time this script is started
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(thread)6d %(name)-30s %(funcName)-20s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

from p5control import InstrumentServer, drivers, inserv_cli

inserv = InstrumentServer()


inserv._add('inst1', drivers.ExampleInst)
inserv._add('inst2', drivers.ExampleInst)
inserv._add('bf', drivers.BlueForsAPI)
# inserv._add('magnet')
inserv._add('vna', drivers.ZNB40, '192.168.1.104')
# inserv._add('thermo', drivers.GIR2002, 'ASRL1::INSTR')
inserv._add('multi_source', drivers.Keysight34461A, 'TCPIP0::192.168.1.109::INSTR')
inserv._add('multi_sample', drivers.Keysight34461A, 'TCPIP0::192.168.1.110::INSTR')
inserv._add('multi_reference', drivers.Keysight34461A, 'TCPIP0::192.168.1.111::INSTR')
inserv._add("source_gate", drivers.KeysightB2962A, "TCPIP0::192.168.1.112::INSTR")
inserv._add("source_bias", drivers.KeysightB2962A, "TCPIP0::192.168.1.113::INSTR")
# inserv._add('femtos')
# inserv._add('motor')

print("Added instruments successfully.")

inserv.start()

inserv_cli(inserv)