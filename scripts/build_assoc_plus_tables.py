# Have to import tables or it doesn't work
from seis_proc_db import database, tables

"""Create tables for associated arrivals, event, origin, and mags
"""

if __name__ == "__main__":
    table_names = [
        "assoc_method",
        "loc_method",
        "vel_model",
        "mag_method",
        "event",
        "origin",
        "assoc_arr",
        "arrmag",
        "arr_wf_feat",
        "netmag",
    ]
    metadata = database.Base.metadata
    for table in table_names:
        print("Building", table)

        metadata.tables[table].create(bind=database.engine, checkfirst=True)
