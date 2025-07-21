# Have to import tables or it doesn't work
from seis_proc_db import database, tables

"""Create tables for associated arrivals, event, origin, and mags
"""

if __name__ == "__main__":
    table_names = [
        "uuss_arr",
        "uuss_event",
    ]
    metadata = database.Base.metadata
    for table in table_names:
        print("Dropping", table)
        metadata.tables[table].drop(bind=database.engine, checkfirst=True)
