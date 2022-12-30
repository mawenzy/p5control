from pathlib import Path

# default instrument server port
INSERV_DEFAULT_PORT = 42068

# default data server port
DATASERV_DEFAULT_PORT = 30000

# directory to store hdf5 files
DEFAULT_DATA_DIR = Path(".data")

# paths in the hdf5 under which the measurements and status is stored
MEASUREMENT_BASE_PATH = "measurement"
STATUS_MEASUREMENT_BASE_PATH = "status"