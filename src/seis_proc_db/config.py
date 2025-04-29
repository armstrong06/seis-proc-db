import os

# Get user and password environmental variables so they are not hardcoded
USER = os.getenv("USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_TYPE = "mysql"
DBAPI = "mysqldb"
DB_URL = f"{DB_TYPE}+{DBAPI}://{USER}:{DB_PASSWORD}@{DB_HOST}/SeisProcML"
# DB_URL = f"mariadb+mariadbconnector://{USER}:{DB_PASSWORD}@mysql.chpc.utah.edu/SeisProcML"

MYSQL_ENGINE = "InnoDB"

# The buffer around gaps to not add in a detection
DETECTION_GAP_BUFFER_SECONDS = 0.25

# Root path to store HDF5 files
HDF_BASE_PATH = os.getenv("SPDB_HDF_BASE_PATH")
# Directory name for HDF waveform files
HDF_WAVEFORM_DIR = "waveforms"
# Directory name for HDF detector posterior probs
HDF_UNET_SOFTMAX_DIR = "unet_softmax_values"
# Directory name for HDF swag repicker predictions
HDF_PICKCORR_DIR = "pick_corrections"
