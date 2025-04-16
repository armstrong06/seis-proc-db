import obspy
from obspy.core import UTCDateTime
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
                        )[1],
                    }
                    if station.code == "YFT" and channel.code[:-1] == "HH" and channel.start_date == UTCDateTime("2016-06-19T00:00:00.0000"):
                        print("UPDATING YFT ENDDATE")
                        # Enddate from IRIS http://ds.iris.edu/mda/WY/YFT/?starttime=1993-10-26&endtime=2599-12-31
                        # Possibly incorrect because the colocated strong motion from that time period is still operational
                        chan_dict["offdate"] = UTCDateTime("2020-09-14T23:59:59")
                    if station.code == "YTP" and channel.code == "EHZ" and channel.start_date == UTCDateTime("2013-08-26T00:00:00"):
                        # It seems that the channel metadata was updated in late 2024/early 2025 to have the start date be 2013/04/01 
                        # instead of 2013/08/26. This agrees with what is on iris http://ds.iris.edu/mda/WY/YTP/?starttime=1994-08-05&endtime=2599-12-31
                        chan_dict["ondate"] = UTCDateTime("2013-04-01T00:00:00")

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
