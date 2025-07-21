from sqlalchemy import select
from sqlalchemy.orm import joinedload
import os
import time
import pandas as pd
from seis_proc_db.database import Session
from seis_proc_db.tables import DailyContDataInfo, Pick

filedir = "/uufs/chpc.utah.edu/common/home/koper-group3/alysha/process_ys_data/slurm_detector_code/station_lists"
file1c = os.path.join(filedir, "station.list.db.1C.2023-01-01.2024-01-01.txt")
file3c = os.path.join(filedir, "station.list.db.3C.2023-01-01.2024-01-01.txt")

print("Loading station files...")
stats_1c_df = pd.read_csv(
    file1c, sep="\s+", names=["net", "sta", "loc", "chan"], skiprows=1, dtype=str
).fillna("")
stats_3c_df = pd.read_csv(
    file3c, sep="\s+", names=["net", "sta", "loc", "chan"], skiprows=1, dtype=str
).fillna("")

stats_1c_dict = {
    (row["net"], row["sta"], row["chan"]): row["loc"]
    for _, row in stats_1c_df.iterrows()
}
stats_3c_dict = {
    (row["net"], row["sta"], row["chan"]): row["loc"]
    for _, row in stats_3c_df.iterrows()
}

print(stats_1c_df.head())
print(stats_3c_df.head())

start_time = time.time()
with Session() as session:
    stmt = select(Pick).where(Pick.chan_loc.is_(None)).options(joinedload(Pick.station))
    cnt = 0
    print("Starting query...")
    t = time.time()
    for obj in session.scalars(stmt).yield_per(1000):
        sta = obj.station.sta
        net = obj.station.net
        chan = obj.chan_pref
        key = (net, sta, chan[:-1] if len(chan) > 2 else chan)
        loc = stats_1c_dict.get(key) if len(chan) > 2 else stats_3c_dict.get(key)

        obj.chan_loc = loc

        if cnt % 10000 == 0:
            session.commit()
            print(
                f"Commiting on row {cnt}. Time for 10_000 rows: {time.time() - t:.3f} s"
            )
            t = time.time()

        cnt += 1
    session.commit()
print(f"Total time {time.time() - start_time:.3f} s")
