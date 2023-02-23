import logging
import time
import os

import numpy as np
from ADwin import ADwin

from .basedriver import BaseDriver

logger = logging.getLogger(__name__)

class ADwinGold2(BaseDriver):
    """Represents an instrument which magically measures a sine wave. Both the frequency and the amplitude can be changed.

    Parameters
    ----------
    name : str
        name for this instance
    """

    def __init__(self, name: str):
        self._name = name

        self.open()
        self._time_offset = time.time()
        self.averaging = self.getAveraging()
        self.ranges = np.array([10, 10, 10, 10])

        self.patterns = np.arange(4)
        self.psbl_ranges = 10/2**self.patterns

    def open(self):
        """Just logs the call to debug."""
        self.inst = ADwin()
        self.inst.Boot(os.path.join(os.path.dirname(__file__), "adwin/ADwin11.btl"))
        self.inst.Load_Process(os.path.join(os.path.dirname(__file__), "adwin/adwin-gold2.TB0"))
        self.inst.Start_Process(ProcessNo=10)
        # self.inst.Set_Processdelay(ProcessNo=1, Processdelay=300000)
        status = self.inst.Process_Status(ProcessNo=10)
        logger.debug("%s.open() %s"%(self._name, status))

    def close(self):
        """Just logs the call to debug."""
        logger.debug(f'{self._name}.close()')

    """
    Status measurement
    """
    def get_status(self):
        """Returns the current averaging and ranges."""
        logger.debug(f'{self._name}, ampl: {0}, freq: {0}')
        return {
            "averaging": self.averaging,
            "range_ch1": self.ranges[0],
            "range_ch2": self.ranges[1],
            "range_ch3": self.ranges[2],
            "range_ch4": self.ranges[3],
        }

    """
    Measurement
    """

    def start_measuring(self):
        """Start the measurement. Clear FIFOs
        """
        self.inst.Set_Par(Index=10, Value=1)

    def get_data(self):
        """Collects data
        """        
        logger.debug(f'{self._name}.get_data()')

        l = [
            self.inst.Fifo_Full(FifoNo=9),
            self.inst.Fifo_Full(FifoNo=1),
            self.inst.Fifo_Full(FifoNo=2),
            self.inst.Fifo_Full(FifoNo=3),
            self.inst.Fifo_Full(FifoNo=4)
                ]

        l = list(map(int, l))
        count = min(l)
        if count <= 0:
            return None

        times = np.array(self.inst.GetFifo_Float(FifoNo=9, Count=count), dtype='float64') + self._time_offset
        ch1 = self.inst.GetFifo_Float(FifoNo=1, Count=count)
        ch2 = self.inst.GetFifo_Float(FifoNo=2, Count=count)
        ch3 = self.inst.GetFifo_Float(FifoNo=3, Count=count)
        ch4 = self.inst.GetFifo_Float(FifoNo=4, Count=count)

        return {
            "time": list(times),
            "V1": list(ch1),
            "V2": list(ch2),
            "V3": list(ch3),
            "V4": list(ch4),
        }

    """
    Properties
    - default length in gui
    - averaging
    - ranges
    """

    def _save_data(self, hdf5_path: str, array, dgw):
        return super()._save_data(hdf5_path, array, dgw, max_length=int(10000))

    def setAveraging(self, value:int):
        logger.debug('%s.setAveraging(%i)', self._name, value)
        self.inst.Set_Par(Index=20, Value=value)
        self.averaging = value

    def getAveraging(self):
        logger.debug('%s.getAveraging()', self._name)
        value = int(self.inst.Get_FPar(20))
        return value

    def setRange(self, range, ch:int):
        logger.debug('%s.setRange(%f, %i)', self._name, range, ch)        
        index = np.argmin(np.abs(self.psbl_ranges-range))
        self.inst.Set_FPar(Index=ch, Value = self.psbl_ranges[index])
        self.inst.Set_Par(Index=ch, Value = int(self.patterns[index]))
        self.ranges[ch-1] = self.psbl_ranges[index]

    def getRange(self, ch:int):
        logger.debug('%s.getRange(%i)', self._name, ch)
        value = self.inst.Get_Fpar(ch)
        return value




'''
Panik Alert:

Import Math.LIB
        print(min(l), l)
        count = l[0]

        self.inst.Set_Par(16, 0)

        par_11 = self.inst.Get_Par(11)
        if par_11 == 1:
            print("!!!")

        # count = int(self.inst.Fifo_Full(FifoNo=4))
        self.inst.Set_Par(16, 1)

    If (Par_16 = 0) Then
      len1 = FIFO_Full(9)
      index = 1
      Do
        len2 = FIFO_Full(index)
        if (len1 <> len2) Then
          Par_11 = 1
          Par_12 = len1
          Par_13 = len2
          Par_14 = index
          Par_15 = len1 - len2
        endif
        Inc(index)
      Until (index = 5)
    EndIf
    '''