"""
Test driver to illustrate the inner workings of *p5control*.
"""
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

    def open(self):
        """Just logs the call to debug."""
        self.inst = ADwin()
        self.inst.Boot(os.path.join(os.path.dirname(__file__), "adwin/ADwin11.btl"))
        self.inst.Load_Process(os.path.join(os.path.dirname(__file__), "adwin/adwin-gold2.TB0"))
        self.inst.Start_Process(ProcessNo=10)
        self.inst.Set_Processdelay(ProcessNo=1, Processdelay=300000)
        status = self.inst.Process_Status(ProcessNo=10)
        logger.debug("%s.open() %s"%(self._name, status))

    def close(self):
        """Just logs the call to debug."""
        logger.debug(f'{self._name}.close()')

    """
    Status measurement
    """
    def get_status(self):
        """Returns the current amplitude and frequency."""
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
        self.inst.Fifo_Clear(FifoNo=9)
        self.inst.Fifo_Clear(FifoNo=1)
        self.inst.Fifo_Clear(FifoNo=2)
        self.inst.Fifo_Clear(FifoNo=3)
        self.inst.Fifo_Clear(FifoNo=4)

    def get_data(self):
        """Collects data
        """        
        logger.debug(f'{self._name}.get_data()')
        count = int(np.min([
            self.inst.Fifo_Full(FifoNo=9),
            self.inst.Fifo_Full(FifoNo=1),
            self.inst.Fifo_Full(FifoNo=2),
            self.inst.Fifo_Full(FifoNo=3),
            self.inst.Fifo_Full(FifoNo=4)
                ]))
        # count = int(self.inst.Fifo_Full(FifoNo=4))
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

    def setAveraging(self, value):
        value = int(value)
        logger.debug('%s.setAveraging(value = %i)'%(self._name, value))
        self.inst.Set_Par(Index=20, Value=value)
        self.averaging = value

    def getAveraging(self):
        value = self.inst.Get_FPar(20)
        logger.debug('%s.getAveraging() = %i'%(self._name, value))
        return value

    # def setRange(self, range):
    #     ch=1
    #     patterns = np.arange(4)
    #     ranges = 10/2**patterns
    #     index = np.argmin(np.abs(ranges-range))

    #     self.inst.Set_FPar(Index=ch, Value = ranges[index])
    #     self.inst.Set_Par(Index=ch, Value = int(patterns[index]))
    #     self.ranges[ch-1] = ranges[index]
    #     print(range, ranges[index], patterns[index])

