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

CALLBACK_THREAD_COUNT = 5
"""The amount of threads in the thread pool responsible for callbacks."""

GATEWAY_ADDRESS = "localhost"
"""Address"""

SETTINGS = {
    'gateway_address': GATEWAY_ADDRESS
}

def set_setting(key, value):
    SETTINGS[key] = value

def get_setting(key):
    return SETTINGS[key]
