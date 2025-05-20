# Have to import tables or Base doesn't register them
from seis_proc_db import database, tables
import os
from seis_proc_db.config import (
    HDF_BASE_PATH,
    HDF_WAVEFORM_DIR,
    HDF_UNET_SOFTMAX_DIR,
    HDF_PICKCORR_DIR,
)

"""Drop all tables defined in app.tables
"""

if __name__ == "__main__":
    metadata = database.Base.metadata
    for name, table in metadata.tables.items():
        print(name)

    metadata.drop_all(database.engine)

    for data_dir in [HDF_WAVEFORM_DIR, HDF_UNET_SOFTMAX_DIR, HDF_PICKCORR_DIR]:
        path = os.path.join(HDF_BASE_PATH, data_dir)
        if os.path.exists(path):
            os.rmdir(path)
            print(f"Directory '{path}' and its contents removed successfully.")
