import time
from seis_proc_db.services import get_waveform_storage_number
from seis_proc_db.database import Session

chan_id = 29
wf_source_id = 1

with Session() as session:
    t = time.time()
    print(
        get_waveform_storage_number(
            session, chan_id, wf_source_id, "P", 150_000, year=2024
        )
    )
    print(f"Run time: {time.time() - t:.2f}")
