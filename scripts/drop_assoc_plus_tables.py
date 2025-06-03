# Have to import tables or it doesn't work
from seis_proc_db import database, tables

"""Create tables for associated arrivals, event, origin, and mags
"""

if __name__ == "__main__":
    table_names = [
        "netmag",
        "arr_wf_feat",
        "arrmag",
        "assoc_arr",
        "origin",
        "event",
        "assoc_method",
        "loc_method",
        "vel_model",
        "mag_method",
    ]
    metadata = database.Base.metadata
    for table in table_names:
        print("Dropping", table)
        metadata.tables[table].drop(bind=database.engine, checkfirst=True)
