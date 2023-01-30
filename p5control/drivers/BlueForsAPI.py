# Import needed libraries
import json
from requests import get as requests_get
import numpy as np
from .basedriver import BaseDriver
from logging import getLogger

# Logger
logger = getLogger(__name__)

class BlueForsAPI(BaseDriver):
    def __init__(self, name, address='localhost:49099'):
        self._name = name
        self._address = address

        # Memory
        self._latest_T50K = 0
        self._latest_T4K = 0
        self._latest_Tmagnet = 0

    """
    Response
    """
    def get_response(self):
        req = requests_get(
                    f"http://{self._address}/values",
                    timeout=3,
                )
        logger.debug(f'{self._name}.get_response()')
        return req.json()


    """
    Status measurement
    """
    def get_status(self):
        data = self.get_response()
        status = {}

        # Thermometers
        # 1. 50K
        # 2. 4K
        # 3. Magnet
        # 4. --
        # 5. Still
        # 6. MXC
        # 7. FMR
        # 8. MCBJ

        # 50K Thermometer
        T50K = data['data']['driver.lakeshore.status.inputs.channel1.temperature']['content']['latest_value']
        date = T50K['date']/1000.0
        if date!=self._latest_T50K:
            self._latest_T50K = date
            status['T50K'] = {'time': [date], 'T': [float(T50K['value'])]}

        # 4K Thermometer
        T4K = data['data']['driver.lakeshore.status.inputs.channel2.temperature']['content']['latest_value']
        date = T4K['date']/1000.0
        if date!=self._latest_T4K:
            self._latest_T4K = date
            status['T4K'] = {'time': [date], 'T': [float(T4K['value'])]}
            
        # Magnet Thermometer
        Tmagnet = data['data']['driver.lakeshore.status.inputs.channel3.temperature']['content']['latest_value']
        date = Tmagnet['date']/1000.0
        if date!=self._latest_Tmagnet:
            self._latest_Tmagnet = date
            status['Tmagnet'] = {'time': [date], 'T': [float(Tmagnet['value'])]}
        
        logger.debug(f'{self._name}.get_status()')
        return status

    def _save_status(
        self,
        hdf5_path: str,
        status,
        dgw
    ):
        if 'T50K' in status:
            dgw.append(f"{hdf5_path}/temperatures/50K", status['T50K'])
        if 'T4K' in status:
            dgw.append(f"{hdf5_path}/temperatures/4K", status['T4K'])
        if 'Tmagnet' in status:
            dgw.append(f"{hdf5_path}/temperatures/magnet", status['Tmagnet'])
