import os

# Get user and password environmental variables so they are not hardcoded
USER = os.getenv("USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_TYPE = "mysql"
DBAPI = "mysqldb"
DB_URL = f"{DB_TYPE}+{DBAPI}://{USER}:{DB_PASSWORD}@mysql.chpc.utah.edu/SeisProcML"
# DB_URL = f"mariadb+mariadbconnector://{USER}:{DB_PASSWORD}@mysql.chpc.utah.edu/SeisProcML"

MYSQL_ENGINE = "InnoDB"

# The buffer around gaps to not add in a detection
DETECTION_GAP_BUFFER_SECONDS = 1.0
