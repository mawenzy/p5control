import logging
import time
from pyvisa import ResourceManager
from ..gateway import DataGateway

import numpy as np

from .basedriver import BaseDriver

logger = logging.getLogger(__name__)

class ZNB40(BaseDriver):
    def __init__(self, 
                 name, 
                 address='192.168.1.104', 
                 res: float = 0.1):
        self._name = name
        self._address = address
        self.refresh_delay = 1

        self._temp_avg = 1
        self.open()
        
    def open(self):
        # Open Connection
        rm = ResourceManager()
        self._inst = rm.open_resource(f'TCPIP0::{self._address}::inst0::INSTR')  
        self._inst.timeout=1e5 
        # reset the device
        self._inst.write('*RST')
        # delete all old traces
        self._inst.write('CALC:PAR:DEL:ALL')
        # turn continous measurement off
        self._inst.write('INITiate1:CONTinuous OFF')
        # turn Display to remote control
        self._inst.write('SYSTem:TSLock SCReen')
        # close soft tool menu
        self._inst.write('SYSTem:DISPlay:BAR:STOols OFF')
        # Displaying the data increases measurement time 
        self._inst.write('SYSTem:DISPlay:UPDate OFF')
        # Wait for all commands happening
        self._inst.query('*OPC?')
        self.message()
        logger.debug(f'{self._name}.open()')

    def exit(self):
        # turn Display to local control
        self._inst.write('SYSTem:TSLock OFF)')
        # reset the device
        self._inst.write('*RST')
        # Go to local control
        self._inst.write('SYSTem:DISPlay:UPDate ON')

        self.inst.write('SYSTem:DISPlay:BAR:STOols ON')
        # Close Connection
        self._inst.close()
        logger.debug(f'{self._name}.exit()')

    def setup_measuring_fsweep(self, s_param: str = 'S21'):
        # Set the S-Parameter, that should be measured
        # input: 'S11','S22','S12','S21'
        
        # sets a displaypanel with the measured datapoints
        # db mag is default
        self._inst.write("DISP:WIND:STAT ON")
        
        # S-Parameter Trace is defined and added to the displaypanel
        self._inst.write(f"CALC1:PAR:SDEF 'Tr1', '{s_param}'")
        self._inst.write("DISPlay:WINDow:TRAC1:FEED 'Tr1'")

        # Update display once
        self._inst.write('SYSTem:DISPlay:UPDate ONCE')

        logger.debug(f'{self._name}.setup_measuring_fsweep(s_param={s_param})')

    def setup_timeout(self):
        # sets timeout time between measurments to zero
        self._inst.write("SENSe1:SWEep:TIME:AUTO ON")
        
        # gets maximum timeout time, to prevent errors during long time meas.
        time=float(self._inst.query('SENSe1:SWEep:TIME?'))
        if self._temp_avg > 1:
            self._inst.timeout=int((time*self._temp_avg*2.5+10)*1000)
        else:
            self._inst.timeout=int((time*2.5+10)*1000)
        logger.debug(f'{self._name}.setup_timeout()')

    def setup_measuring(self):
        self.setup_measuring_fsweep()
        self.setup_timeout()
    
    def get_data(self):
        # initialize measurement
        timestamp = time.time()
        self._inst.write("INIT")
        self._inst.write('*WAI')
        
        # gets y-axis / s_param data
        data = self._inst.query("CALC1:DATA:TRACe? 'Tr1', SDAT")
        data = np.fromstring(data, dtype='float64',sep=',')
        real, imag = data[::2], data[1::2]
        S = np.array(real+1j*imag, dtype='complex128')
        S_db = 20*np.log10(np.abs(S))

        # shows measured data once. (is better for performance)
        self._inst.write('SYSTem:DISPlay:UPDate ONCE')
        self._inst.write('SYSTem:DISPlay:BAR:STOols OFF')
        self._inst.write("DISP:TRAC1:Y:AUTO ONCE")

        logger.debug(f'{self._name}.get_data()')

        
        data = {
                'S_db': S_db,
                'Re': real,
                'Im': imag,
                'timestamp': timestamp
                }

        return data
    
    def get_fdata(self):
        return np.linspace(self.get_start_frequency(),
                           self.get_stop_frequency(),
                           self.get_sweep_points())

    # for important messages, lol
    def message(self, message="DON'T TOUCH\nRemote test running..."):
        self._inst.write(f'SYST:USER:DISP:TITL "{message}"')
        logger.debug(f'{self._name}.message({message})')

    # properties
    def get_start_frequency(self):
        return float(self._inst.query("SENSe1:FREQuency:STARt?"))
    def set_start_frequency(self, value):
        self._inst.write(f"SENSe1:FREQuency:STARt {int(value)} Hz")

    def get_stop_frequency(self):
        return float(self._inst.query("SENSe1:FREQuency:STOP?"))
    def set_stop_frequency(self, value):
        self._inst.write(f"SENSe1:FREQuency:STOP {int(value)} Hz")

    def get_sweep_points(self):
        return int(self._inst.query("SENSe1:SWEep:POINts?"))
    def set_sweep_points(self, value):
        self._inst.write(f"SENSe1:SWEep:POINts {int(value)}")
        
    def get_bandwidth(self):
        return float(self._inst.query("SENSe1:BANDwidth?"))
    def set_bandwidth(self, value):
        """
        possible values:   1, 1.5,  2,  3,  5,  7, 10,
                         1e1,15e0,2e1,3e1,5e1,7e1,1e2,
                         1e2,15e1,2e2,3e2,5e2,7e2,1e3,
                         1e3,15e2,2e3,3e3,5e3,7e3,1e4,
                         1e4,15e3,2e4,3e4,5e4,7e4,1e5,
                         1e5,15e4,2e5,3e5,5e5,7e5,1e6
        """
        self._inst.write(f"SENSe1:BANDwidth {value}")

    def get_power(self):
        return float(self._inst.query("SOURce1:POWer?"))
    def set_power(self, value):
        self._inst.write(f"SOURce1:POWer {value} dBm")

    def get_average(self):
        if self._temp_avg <=1:
            return_value = 1
        else:
            return_value = int(self._inst.query(f"SENSe1:AVERage:COUNt?"))
        return return_value
    def set_average(self, value:int):
        if value > 1:
            self._inst.write(f"SENSe1:AVERage:COUNt {value}")
            self._inst.write(f"SENSe1:AVERage:STATe ON")
            self._inst.write(f"SENSe1:AVERage:CLEar")
            self._inst.write(f"SENSe1:SWEep:COUNt {value}")
        else:
            self._inst.write(f"SENSe1:AVERage:STATe OFF")
        self._temp_avg = value
             


    # Debugging
    def query(self, request):
        return self._inst.query(request)
    def write(self, writing):
        self._inst.write(writing)
    def read(self):
        return self._inst.read()


    # Save Data
    
    def _save_data(
        self,
        hdf5_path: str,
        data,
        dgw: DataGateway,
    ):
        """Save data to hdf5 through a gateway
        
        Parameters
        ----------
        hdf5_path : str
            base hdf5_path under which you should save the data
        array
            data to save
        dgw : DataGateway
            gateway to the dataserver
        """
        if data['S_db'] is None:
            return

        my_dict = {'S_db': data['S_db'],
                   'Im': data['Im'],
                   'Re': data['Re']}

        path = f"{hdf5_path}/{self._name}/{data['timestamp']}"
        dgw.append(path, 
                    my_dict, 
                    start_freq = self.get_start_frequency(),
                    stop_freq = self.get_stop_frequency(),
                    points = self.get_sweep_points(),
                    plotConfig = "dset_mult")