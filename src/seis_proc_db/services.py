"""Store business logic"""

from sqlalchemy import select, text, insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from seis_proc_db.tables import *


def insert_station(session, net, sta, ondate, lat, lon, elev, offdate=None):
    """Insert a row into the station table.

    Args:
        session (Session): The database Session
        net (str): Network code
        sta (str): Station code
        ondate (datetime): Station on date in UTC
        lat (float): Station latitude
        lon (float): Station longitude
        elev (float): Station elevation in m
        offdate (datetime, optional): Station off date in UTC. Defaults to None.

    Returns:
        Station: Station object representing the inserted row
    """

    new_stat = Station(
        net=net, sta=sta, ondate=ondate, lat=lat, lon=lon, elev=elev, offdate=offdate
    )
    session.add(new_stat)

    return new_stat


def get_station(session, net, sta, ondate):
    """Get a Station object from the database. Returns None if there was not a matching
    Station.

    Args:
        session (Session): The database Session
        net (str): The network of the desired station
        sta (str): The station code of the desired station
        ondate (datetime): The ondate of the desired station. Looks for entries with
        ondates with 60 s of this time.

    Raises:
        ValueError: More than one Station was found.

    Returns:
        Station: Station object containing the desired station information or None
    """

    ### Can use this if I want to compare the ondate exactly, but couldn't figure out
    ### how to compare if they were close
    # stmt = select(Station).where(
    #     Station.net == net,
    #     Station.sta == sta,
    #     Station.ondate == ondate,
    # )
    # result = session.scalars(stmt).all()

    # Find matching station with ondates within one minute of each other...

    textual_sql = text(
        "SELECT * FROM station WHERE net = :x AND sta = :y AND ABS(TIMESTAMPDIFF(SECOND, ondate, :z)) < 60",
    )

    result = session.scalars(
        select(Station).from_statement(textual_sql), {"x": net, "y": sta, "z": ondate}
    ).all()

    if len(result) == 1:
        return result[0]
    if len(result) == 0:
        return None

    # This should only happen if (oddly) there were Stations with ondates within 1 min
    raise ValueError("More than one Station matching these criteria")


def get_operating_station_by_name(session, sta, year):
    """Get a Station object from the database by looking for a specific station name that is operating during
    a given year.

    Args:
        session (Session): The database Session
        sta (str): The station code of the desired station
        year (int): A year that the station should be operational.
    Raises:
        ValueError: More than one Station was found.

    Returns:
        Station: Station object containing the desired station information or None
    """

    textual_sql = text(
        "SELECT * FROM station WHERE sta = :sta AND YEAR(ondate) <= :year AND (YEAR(offdate) >= :year OR offdate IS NULL)",
    )

    result = session.scalars(
        select(Station).from_statement(textual_sql), {"sta": sta, "year": str(year)}
    ).all()

    if len(result) == 1:
        return result[0]
    if len(result) == 0:
        return None

    # This should only happen if (oddly) there were Stations with ondates within 1 min
    raise ValueError("More than one Station matching these criteria")


def get_operating_channels_by_station_name(session, sta, chan_pref, date):

    # net, sta, seed_code, channel.ondate, channel.offdate
    textual_sql = text(
        (
            # "SELECT * FROM station JOIN channel ON station.id = channel.sta_id"
            # "AND station.sta = :sta AND   "
            # "channel.seed_code LIKE :chan_pref AND "
            "channel.ondate <= :date AND "
            "(channel.offdate >= :date OR channel.offdate IS NULL)"
        )
    )

    # select(
    #     Station.id,
    #     Station.net,
    #     Station.sta,
    #     Channel.id,
    #     Channel.seed_code,
    #     Channel.ondate,
    #     Channel.offdate,
    # )
    stmt = (
        select(Station, Channel)
        .join(Channel, Station.id == Channel.sta_id)
        .where(Station.sta == sta)
        .where(Channel.seed_code.op("REGEXP")(chan_pref))
        .where(textual_sql)
    )

    # print("STMT", stmt)
    result = session.execute(stmt, {"date": date}).all()

    if len(result) == 0:
        return None, None

    station_obj = result[0][0]
    channel_list = []
    for row in result:
        channel_list.append(row[1])

    return station_obj, channel_list


def insert_channels(session, channel_dict_list):
    """Inserts one or more channels into the database using a bulk insert.

    Args:
        session (Session): database session
        channel_dict_list (list): A list of dictionary objects containing the relevant Channel information.
        Dictionary keys should be the same as those in the Channel class.
    """

    # MySQL doesn't support bulk RETURNING
    # stmt = insert(Channel).returning(Channel)
    # inserted_channels = session.scalars(stmt, channel_dict_list).all()

    session.execute(insert(Channel), channel_dict_list)


def insert_ignore_channels_common_stat(session, sta_id, channel_dict_list):
    """Inserts one or more channels for the same station into the database. Ignoring duplicate entries.

    Args:
        session (Session): database session
        sta_id (int): Station.id
        channel_dict_list (list): A list of dictionary objects containing the relevant Channel information.
        Dictionary keys should be the same as those in the Channel class.
    """

    textual_sql = text(
        "INSERT IGNORE INTO channel (sta_id, seed_code, loc, ondate, samp_rate, clock_drift, lat, lon, elev,"
        "depth, azimuth, dip, offdate, sensor_desc, sensit_units, sensit_freq, sensit_val, overall_gain_vel)"
        "VALUES (:sta_id, :seed_code, :loc, :ondate, :samp_rate, :clock_drift, :lat, :lon, :elev,"
        ":depth, :azimuth, :dip, :offdate, :sensor_desc, :sensit_units, :sensit_freq, :sensit_val, :overall_gain_vel)"
    )

    for chan in channel_dict_list:
        chan["sta_id"] = sta_id

    session.execute(textual_sql, channel_dict_list)


def insert_channel(session, channel_dict):
    """Insert a single channel into the database.

    Args:
        session (Session): The database session
        channel_dict (dict): Dictionary containing Channel information

    Returns:
        Channel: Channel object corresponding to the inserted row
    """

    new_chan = Channel(**channel_dict)
    session.add(new_chan)

    return new_chan


def get_channel(session, sta_id, seed_code, loc, ondate):
    """Get a single Channel from the database.

    Args:
        session (Session): database Session
        sta_id (int): Station id
        seed_code (str): Channel seed code
        loc (str): Channel location code
        ondate (datetime): Channel ondate. Will look for ondates within 1 minutes of this time.

    Returns:
        Channel: Channel object containing the desired channel information or None.
    """
    # stmt = select(Channel).where(
    #     Channel.sta_id == sta_id,
    #     Channel.seed_code == seed_code,
    #     Channel.loc == loc,
    #     Channel.ondate == ondate
    # )
    # result = session.scalars(stmt).all()

    textual_sql = text(
        "SELECT * FROM channel WHERE sta_id = :sid AND seed_code = :c AND loc = :l AND ABS(TIMESTAMPDIFF(SECOND, ondate, :t)) < 60",
    )
    result = session.scalars(
        select(Channel).from_statement(textual_sql),
        {"sid": sta_id, "c": seed_code, "l": loc, "t": ondate},
    ).all()

    if len(result) == 1:
        return result[0]
    if len(result) == 0:
        return None


def get_all_station_channels(session, sta_id):
    """Get a list of Channel objects belonging to one station.

    Args:
         session (Session): database Session
        sta_id (int): Station id

    Returns:
        List: list of Channel objects corresponding to the table rows
    """
    stmt = select(Channel).where(
        Channel.sta_id == sta_id,
    )
    result = session.scalars(stmt).all()

    return result


def get_common_station_channels(session, sta_id, seed_code_pref):
    """Get a list of Channel objects belonging to one station with a common sensor type.

    Args:
        session (Session): database Session
        sta_id (int): Station id
        seed_code_pref(str): First two letters of the SEED code for the channel type
        for 3C or all three letter for 1C.

    Returns:
        List: list of Channel objects corresponding to the table rows
    """
    assert type(sta_id) is int, ValueError("Station id should be an int")

    if len(seed_code_pref) == 2:
        seed_code_pref += "."

    stmt = select(Channel).where(
        Channel.sta_id == sta_id, Channel.seed_code.op("REGEXP")(seed_code_pref)
    )
    result = session.scalars(stmt).all()

    # textual_sql = text(
    #     "SELECT * FROM channel WHERE sta_id = :sid AND seed_code = :c",
    # )
    # result = session.scalars(
    #     select(Channel).from_statement(textual_sql), {"sid": sta_id, "c": seed_code_pref}
    # ).all()

    return result


def get_common_station_channels_by_name(session, sta, seed_code_pref):
    """Get a list of Channel objects belonging to a station name with a common sensor
    type. THERE COULD BE MORE THAN ONE STATION WITH THE SAME NAME.

    Args:
        session (Session): database Session
        sta (str): station name
        seed_code_pref(str): First two letters of the SEED code for the channel type
        for 3C or all three letter for 1C.

    Returns:
        List: list of Channel objects corresponding to the table rows
    """

    assert type(sta) is str, ValueError("Station name should be a string")

    if len(seed_code_pref) == 2:
        seed_code_pref += "."

    stmt = (
        select(Channel)
        .join(Station, Channel.sta_id == Station.id)
        .where(Station.sta == sta, Channel.seed_code.op("REGEXP")(seed_code_pref))
    )

    result = session.scalars(stmt).all()

    return result


def insert_contdatainfo(session, contdatainfo_dict):
    new_contdatainfo = DailyContDataInfo(**contdatainfo_dict)
    session.add(new_contdatainfo)

    return new_contdatainfo


def get_contdatainfo(session, sta_id, chan_pref, ncomps, date):
    stmt = (
        select(DailyContDataInfo)
        .where(DailyContDataInfo.sta_id == sta_id)
        .where(DailyContDataInfo.chan_pref == chan_pref)
        .where(DailyContDataInfo.ncomps == ncomps)
        .where(DailyContDataInfo.date == date)
    )

    result = session.scalars(stmt).all()

    if len(result) == 0:
        return None
    else:
        return result[0]


def insert_detection_method(session, name, phase=None, desc=None, path=None):
    new_det_method = DetectionMethod(name=name, phase=phase, desc=desc, path=path)
    session.add(new_det_method)

    return new_det_method


def get_detection_method(session, name):
    result = session.scalars(
        select(DetectionMethod).where(DetectionMethod.name == name)
    ).all()

    if len(result) == 0:
        return None

    return result[0]


def upsert_detection_method(session, name, phase=None, desc=None, path=None):
    insert_stmt = mysql_insert(DetectionMethod).values(
        name=name, phase=phase, desc=desc, path=path
    )
    update_dict = {
        col.name: insert_stmt.inserted[col.name]
        for col in DetectionMethod.__table__.columns
        if col.name != "id"
    }
    upsert_stmt = insert_stmt.on_duplicate_key_update(**update_dict)

    session.execute(upsert_stmt)


def insert_dldetection(session, data_id, method_id, sample, phase, width, height):
    # TODO: Add gap check
    new_det = DLDetection(
        data_id=data_id,
        method_id=method_id,
        sample=sample,
        phase=phase,
        width=width,
        height=height,
    )
    session.add(new_det)
    return new_det


def insert_pick(
    session, sta_id, chan_pref, phase, ptime, auth, snr=None, amp=None, detid=None
):
    new_pick = Pick(
        sta_id=sta_id,
        chan_pref=chan_pref,
        phase=phase,
        ptime=ptime,
        auth=auth,
        snr=snr,
        amp=amp,
        detid=detid,
    )
    session.add(new_pick)

    return new_pick


def insert_gap(
    session,
    data_id,
    chan_id,
    start,
    end,
    startsamp=None,
    endsamp=None,
    avail_sig_sec=None,
):
    new_gap = Gap(
        data_id=data_id,
        chan_id=chan_id,
        start=start,
        end=end,
        startsamp=startsamp,
        endsamp=endsamp,
        avail_sig_sec=avail_sig_sec,
    )
    session.add(new_gap)

    return new_gap


def insert_waveform(
    session,
    data_id,
    chan_id,
    pick_id,
    start,
    end,
    data,
    filt_low=None,
    filt_high=None,
    proc_notes=None,
):
    new_wf = Waveform(
        data_id=data_id,
        chan_id=chan_id,
        pick_id=pick_id,
        start=start,
        end=end,
        data=data,
        filt_low=filt_low,
        filt_high=filt_high,
        proc_notes=proc_notes,
    )
    session.add(new_wf)

    return new_wf


def get_or_insert_station(session, stat_dict):
    stat = get_station(session, stat_dict["net"], stat_dict["sta"], stat_dict["ondate"])
    if stat is None:
        stat = insert_station(
            session,
            stat_dict["net"],
            stat_dict["sta"],
            stat_dict["ondate"],
            stat_dict["lat"],
            stat_dict["lon"],
            stat_dict["elev"],
            stat_dict["offdate"],
        )

    return stat


# Potentially useful to implement
def check_gaps(session):
    pass


def add_dldetection_pick(session):
    pass


def bulk_insert_dldetections(session):
    pass


def bulk_insert_picks(session):
    pass
