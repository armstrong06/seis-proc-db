# Have to import tables or Base doesn't register them
from seis_proc_db import database, services
from seis_proc_db.tables import WaveformBLOB, Waveform
from sqlalchemy import select, text, insert
import numpy as np

"""Create all tables defined in app.tables
"""

if __name__ == "__main__":
    metadata = database.Base.metadata
    metadata.create_all(database.engine, tables=[WaveformBLOB.__table__])

    Session = database.Session

    with Session.begin() as session:
        stmt = text("select * from waveform")
        wfs = session.scalars(select(Waveform).from_statement(stmt)).all()
        for wf in wfs:
            blob_data = np.array(wf.data, dtype=np.float32).tobytes()
            blob_wf = WaveformBLOB(
                data_id=wf.data_id,
                chan_id=wf.chan_id,
                pick_id=wf.pick_id,
                start=wf.start,
                end=wf.end,
                data=blob_data,
                filt_low=wf.filt_low,
                filt_high=wf.filt_high,
                proc_notes=wf.proc_notes,
            )
            session.add(blob_wf)
