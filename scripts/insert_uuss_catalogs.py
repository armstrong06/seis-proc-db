import pandas as pd
import os
import numpy as np
from datetime import datetime, timezone
from seis_proc_db import tables
from seis_proc_db.services import get_operating_station_by_name
from seis_proc_db.database import Session

if __name__ == "__main__":
    pref = "/uufs/chpc.utah.edu/common/home/koper-group3/alysha/ben_catalogs/20240220"
    arr_file = os.path.join(pref, "yellowstone_arrivals_gains_20121001_20240101.csv")
    ev_file = os.path.join(pref, "yellowstone_events_20121001_20240101.csv")

    arr_df = pd.read_csv(arr_file)
    ev_df = pd.read_csv(ev_file).sort_values("origin_time")

    ev_df = ev_df.replace({np.nan: None})
    arr_df = arr_df.replace({np.nan: None})

    with Session() as session:
        with session.begin():
            evs_to_add = []
            for _, ev_row in ev_df.iterrows():

                ev_arr_df = arr_df[arr_df["evid"] == ev_row["evid"]]
                ot = datetime.fromtimestamp(ev_row["origin_time"], tz=timezone.utc)
                min_sr_dist = None
                if len(ev_arr_df) > 0:
                    min_sr_dist = ev_arr_df["source_receiver_distance"].min()
                    if np.isnan(min_sr_dist):
                        min_sr_dist = None

                new_ev = tables.UUSSEvent(
                    evid=ev_row["evid"],
                    lat=ev_row["event_lat"],
                    lon=ev_row["event_lon"],
                    depth=ev_row["event_depth"] * 1000,
                    ot=ot,
                    mag=ev_row["magnitude"],
                    mag_type=ev_row["magnitude_type"],
                    narrs=(len(ev_arr_df) if len(ev_arr_df) > 0 else None),
                    min_dist=min_sr_dist,
                )

                if len(ev_arr_df) > 0:
                    for _, arr_row in ev_arr_df.iterrows():
                        sta = get_operating_station_by_name(
                            session, arr_row["station"], ot.year
                        )
                        if sta is None:
                            # print(
                            #     f"Station {arr_row['station']} not in db for {ot.year}"
                            # )
                            sta_id = None
                        else:
                            sta_id = sta.id
                        new_arr = tables.UUSSArrival(
                            arid=arr_row["arrival_id"],
                            evid=arr_row["evid"],
                            net=arr_row["network"],
                            sta=arr_row["station"],
                            chanz=arr_row["channelz"],
                            phase=arr_row["phase"],
                            arrtime=datetime.fromtimestamp(
                                arr_row["arrival_time"], tz=timezone.utc
                            ),
                            quality=arr_row["pick_quality"],
                            fm=arr_row["first_motion"],
                            take_off_angle=arr_row["take_off_angle"],
                            sr_dist=arr_row["source_receiver_distance"],
                            sr_azimuth=arr_row["source_receiver_azimuth"],
                            tt_residual=arr_row["travel_time_residual"],
                            gain_z=arr_row["gain_z"],
                            gain_units=arr_row["gain_units"],
                            low_freq_corner_z=arr_row["low_freq_corners_z"],
                            high_freq_corner_z=arr_row["high_freq_corners_z"],
                            sta_id=sta_id,
                        )
                        new_ev.uuss_arrs.append(new_arr)
                evs_to_add.append(new_ev)

            session.add_all(evs_to_add)
