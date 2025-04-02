import obspy
import numpy as np
import os
import glob
from seis_proc_db.database import Session
from seis_proc_db import services

data_dir = (
    "/uufs/chpc.utah.edu/common/home/koper-group3/alysha/ys_data/downloaded_all_data/"
)

for year in np.arange(2024, 2001, -1):
    file_name = os.path.join(data_dir, str(year), f"stations/*")
    files = glob.glob(file_name)
    print(year)
    stats = []
    for file in files:
        inv = obspy.read_inventory(file)
        inv = inv.select(channel="[EHB]??")

        for network in inv:
            for station in network:
                stat_dict = {
                    "net": network.code,
                    "sta": station.code,
                    "ondate": station.start_date,
                    "lat": station.latitude,
                    "lon": station.longitude,
                    "elev": station.elevation,
                    "offdate": station.end_date,
                }

                channels = []
                for channel in station:
                    chan_dict = {
                        "seed_code": channel.code,
                        "loc": channel.location_code,
                        "ondate": channel.start_date,
                        "samp_rate": channel.sample_rate,
                        "clock_drift": channel.clock_drift_in_seconds_per_sample,
                        "lat": channel.latitude,
                        "lon": channel.longitude,
                        "elev": channel.elevation,
                        "depth": channel.depth,
                        "azimuth": channel.azimuth,
                        "dip": channel.dip,
                        "offdate": channel.end_date,
                        "sensor_desc": channel.sensor.description,
                        "sensit_units": channel.response.instrument_sensitivity.input_units,
                        "sensit_freq": channel.response.instrument_sensitivity.frequency,
                        "sensit_val": channel.response.instrument_sensitivity.value,
                        "overall_gain_vel": channel.response._get_overall_sensitivity_and_gain(
                            output="VEL"
                        )[
                            1
                        ],
                    }
                    channels.append(chan_dict)

                stat_dict["channels"] = channels
            stats.append(stat_dict)

    # import xml.etree.ElementTree as ET# tree = ET.parse('WY.YNR.xml')
    # root = tree.getroot()
    # net = root.findall(".//{http://www.fdsn.org/xml/station/1}Network")
    # stat = net[0].findall(".//{http://www.fdsn.org/xml/station/1}Station")
    # chans = stat[0].findall(".//{http://www.fdsn.org/xml/station/1}Channel")

    print("Starting insert")
    with Session() as session:
        for stat_dict in stats:
            stat = services.get_or_insert_station(session, stat_dict)

        session.commit()

        for stat_dict in stats:
            station = services.get_station(
                session, stat_dict["net"], stat_dict["sta"], stat_dict["ondate"]
            )
            services.insert_ignore_channels_common_stat(
                session, station.id, stat_dict["channels"]
            )

        session.commit()
