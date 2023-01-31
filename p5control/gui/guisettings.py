"""
This module defines settings which are common througout the gui elements.
"""

DATA_BUFFER_MAX_LENGTH = 1000
"""max length for data buffer"""

DOWN_SAMPLE = 1
"""
Can be used to only request every DOWN_SAMPLEth item from the dataset.

Use both settings in conjunction to control the performance of the gui
in order to not process to much data at any point.
"""
