import os

# Get user and password environemental variables so they are not hardcoded
USER = os.getenv("USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_URL = f"mysql+mysqldb://{USER}:{DB_PASSWORD}@mysql.chpc.utah.edu/SeisProcML"