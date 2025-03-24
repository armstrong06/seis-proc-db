# Have to import tables or Base doesn't register them
from seis_proc_db import database, tables

"""Create all tables defined in app.tables
"""

if __name__ == "__main__":
    metadata = database.Base.metadata
    # for name, table in metadata.tables.items():
    #     print("Table:", name)
    metadata.create_all(database.engine)