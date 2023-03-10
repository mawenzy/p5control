"""
This is the 'p5control' module
"""
__version__ = '0.0.2'

from .server import InstrumentServer, DataServer, await_close, inserv_cli

from .gateway import InstrumentGateway, DataGateway

from .measure import Measurement

from .settings import INSERV_DEFAULT_PORT, set_setting, get_setting

from .util import wait
