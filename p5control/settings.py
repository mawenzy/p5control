from pathlib import Path

INSERV_DEFAULT_PORT = 42068
"""default instrument server port"""

DATASERV_DEFAULT_PORT = 30000
"""default data server port"""

DEFAULT_DATA_DIR = Path(".data")
"""directory to store hdf5 files"""

MEASUREMENT_BASE_PATH = "/measurement"
"""path in the hdf5 file under which the measurements are stored"""

STATUS_MEASUREMENT_BASE_PATH = "/status"
"""path in the hdf5 file under which the statuses are stored"""

T_STRING = '/LakeShore370AC'
P_STRING = '/PfeifferMaxiGauge'
VC_STRING = ''
"""path in the hdf5 file in /status/BlueFors"""