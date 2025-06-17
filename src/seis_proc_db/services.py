"""Store business logic"""

import numpy as np
import os
from sqlalchemy import select, text, insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from seis_proc_db.tables import *
from seis_proc_db.config import DETECTION_GAP_BUFFER_SECONDS
from seis_proc_db.pytables_backend import WaveformStorageReader


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


# TODO: Implement this
def get_operating_channels(session, min_date, max_date):

    textual_sql = text(
        (
            "channel.ondate <= :max_date AND "
            "(channel.offdate >= :min_date OR channel.offdate IS NULL)"
        )
    )
    stmt = (
        select(
            Station.net,
            Station.sta,
            Channel.loc,
            Channel.seed_code,
            Channel.ondate,
            Channel.offdate,
        )
        .join_from(Station, Channel, Station.id == Channel.sta_id)
        .where(textual_sql)
    )

    result = session.execute(stmt, {"max_date": max_date, "min_date": min_date}).all()

    return result


def get_operating_channels_by_station_name(
    session, sta, chan_pref, date, net=None, loc=None
):

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

    if net is not None:
        stmt = stmt.where(Station.net == net)
    if loc is not None:
        stmt = stmt.where(Channel.loc == loc)

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


def get_similar_channel_total_ndays(session, net, sta, loc, seed_code):
    stmt = (
        select(Channel.ndays)
        .join(Station, Station.id == Channel.sta_id)
        .where(Station.net == net)
        .where(Station.sta == sta)
        .where(Channel.loc == loc)
        .where(Channel.seed_code == seed_code)
    )

    result = session.execute(stmt).all()

    return np.sum(result)


def get_common_station_channels_by_name(
    session, sta, seed_code_pref, net=None, loc=None
):
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

    if net is not None:
        stmt = stmt.where(Station.net == net)
    if loc is not None:
        stmt = stmt.where(Channel.loc == loc)

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


def insert_detection_method(session, name, phase=None, details=None, path=None):
    new_det_method = DetectionMethod(name=name, phase=phase, details=details, path=path)
    session.add(new_det_method)

    return new_det_method


def get_detection_method(session, name):
    result = session.scalars(
        select(DetectionMethod).where(DetectionMethod.name == name)
    ).all()

    if len(result) == 0:
        return None

    return result[0]


def upsert_detection_method(session, name, phase=None, details=None, path=None):
    insert_stmt = mysql_insert(DetectionMethod).values(
        name=name, phase=phase, details=details, path=path
    )
    update_dict = {
        col.name: insert_stmt.inserted[col.name]
        for col in DetectionMethod.__table__.columns
        if col.name != "id"
    }
    upsert_stmt = insert_stmt.on_duplicate_key_update(**update_dict)

    session.execute(upsert_stmt)


def insert_dldetection(
    session, data_id, method_id, sample, phase, width, height, inference_id=None
):
    # TODO: Add gap check
    new_det = DLDetection(
        data_id=data_id,
        method_id=method_id,
        sample=sample,
        phase=phase,
        width=width,
        height=height,
        inference_id=inference_id,
    )
    session.add(new_det)
    return new_det


def insert_gap(
    session,
    data_id,
    chan_id,
    start,
    end,
    # startsamp=None,
    # endsamp=None,
    avail_sig_sec=None,
):
    new_gap = Gap(
        data_id=data_id,
        chan_id=chan_id,
        start=start,
        end=end,
        # startsamp=startsamp,
        # endsamp=endsamp,
        avail_sig_sec=avail_sig_sec,
    )
    session.add(new_gap)

    return new_gap


def insert_gaps(session, gap_dict_list):
    # Cant return the number of added gaps because they have not been committed yet
    session.execute(insert(Gap), gap_dict_list)


def get_gaps(session, chan_id, data_id):

    result = session.scalars(
        select(Gap).where(Gap.chan_id == chan_id, Gap.data_id == data_id)
    ).all()

    # if len(result) == 0:
    #     return None

    return result


def get_dldetections(session, data_id, method_id, min_height, phase=None):
    # select(DLDetection.id, DLDetection.time, DLDetection.phase)
    stmt = select(DLDetection).where(
        DLDetection.data_id == data_id,
        DLDetection.method_id == method_id,
        DLDetection.height >= min_height,
    )
    if phase is not None:
        stmt = stmt.where(DLDetection.phase == phase)

    result = session.scalars(stmt).all()

    # if len(result) == 0:
    #     return None
    # else:
    #
    return result


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


def get_picks(session, sta_id, chan_pref, phase=None, min_time=None, max_time=None):
    stmt = select(Pick).where(Pick.sta_id == sta_id, Pick.chan_pref == chan_pref)

    if phase is not None:
        stmt = stmt.where(Pick.phase == phase)
    if min_time is not None:
        stmt = stmt.where(Pick.ptime >= min_time)
    if max_time is not None:
        stmt = stmt.where(Pick.ptime <= max_time)

    result = session.scalars(stmt).all()

    return result


def insert_waveform(
    session,
    data_id,
    chan_id,
    pick_id,
    start,
    end,
    data,
    wf_source_id,
):
    new_wf = Waveform(
        data_id=data_id,
        chan_id=chan_id,
        pick_id=pick_id,
        start=start,
        end=end,
        data=data,
        wf_source_id=wf_source_id,
    )
    session.add(new_wf)

    return new_wf


def get_waveforms(session, pick_id, chan_id=None, data_id=None):

    stmt = select(Waveform).where(Waveform.pick_id == pick_id)

    if chan_id is not None:
        stmt = stmt.where(Waveform.chan_id == chan_id)

    if data_id is not None:
        stmt = stmt.where(Waveform.data_id == data_id)

    result = session.scalars(stmt).all()

    return result


def get_waveform_infos(
    session, pick_id, chan_id=None, hdf_file=None, data_id=None, wf_source_id=None
):

    stmt = select(WaveformInfo).where(WaveformInfo.pick_id == pick_id)

    if hdf_file is not None:
        stmt = stmt.join(
            WaveformStorageFile, WaveformStorageFile.id == WaveformInfo.hdf_file_id
        ).where(WaveformStorageFile.name == hdf_file)

    if chan_id is not None:
        stmt = stmt.where(WaveformInfo.chan_id == chan_id)

    if data_id is not None:
        stmt = stmt.where(WaveformInfo.data_id == data_id)

    if wf_source_id is not None:
        stmt = stmt.where(WaveformInfo.wf_source_id == wf_source_id)

    result = session.scalars(stmt).all()

    return result


def get_waveform_infos_and_data(session, storage, pick_id, chan_id=None, data_id=None):
    hdf_file = storage.relative_path
    wf_infos = get_waveform_infos(
        session, pick_id, chan_id=chan_id, hdf_file=hdf_file, data_id=data_id
    )
    results = []
    for wf_info in wf_infos:
        row = storage.select_row(wf_info.id)
        results.append((wf_info, row))

    return results


# def insert_pick_with_waveform(
#     session,
#     sta_id,
#     data_id,
#     chan_id,
#     chan_pref,
#     phase,
#     ptime,
#     auth,
#     wf_data,
#     wf_start,
#     wf_end,
#     snr=None,
#     amp=None,
#     detid=None,
#     wf_filt_low=None,
#     wf_filt_high=None,
#     wf_proc_notes=None,
# ):
#     new_pick = Pick(
#         sta_id=sta_id,
#         chan_pref=chan_pref,
#         phase=phase,
#         ptime=ptime,
#         auth=auth,
#         snr=snr,
#         amp=amp,
#         detid=detid,
#     )

#     new_wf = Waveform(
#         data_id=data_id,
#         chan_id=chan_id,
#         pick_id=None,
#         start=wf_start,
#         end=wf_end,
#         data=wf_data,
#         filt_low=wf_filt_low,
#         filt_high=wf_filt_high,
#         proc_notes=wf_proc_notes,
#     )

#     new_pick.wfs.add(new_wf)

#     session.add(new_pick)

#     return new_pick, new_wf


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


def bulk_insert_dldetections_with_gap_check(session, dldets_dict):
    session.execute(
        text("SET @buffer = :buffer"), {"buffer": DETECTION_GAP_BUFFER_SECONDS}
    )
    # BETWEEN is inclusive on both ends
    textual_sql = text(
        """INSERT INTO dldetection (data_id, method_id, sample, phase, width, height, inference_id)
        SELECT :data_id, :method_id, :sample, :phase, :width, :height, :inference_id
        FROM contdatainfo WHERE contdatainfo.id = :data_id
        AND NOT EXISTS (
        SELECT gap.id FROM gap WHERE gap.data_id = :data_id
        AND TIMESTAMPADD(MICROSECOND, (:sample*1.0) / contdatainfo.samp_rate * 1E6, contdatainfo.proc_start)
        BETWEEN TIMESTAMPADD(MICROSECOND, -@buffer * 1E6, gap.start) AND
        TIMESTAMPADD(MICROSECOND, @buffer * 1E6, gap.end)
        )"""
    )
    session.execute(textual_sql, dldets_dict)

    # CHATGPT on how to do this with ORM
    # from sqlalchemy import insert, select, literal_column, literal, func, table, column, text
    # from sqlalchemy.sql import and_, exists, not_, values
    # from your_model_module import dldetection, gap, contdatainfo

    # # Example detections
    # detections = [
    #     {"data_id": 80, "method_id": 43, "sample": 3960000, "phase": "P", "width": 20, "height": 80},
    #     {"data_id": 80, "method_id": 43, "sample": 3970000, "phase": "S", "width": 15, "height": 70},
    #     # Add more here
    # ]

    # buffer = 10.0  # seconds

    # # Build a VALUES table for detection candidates
    # vals = values(
    #     column("data_id"),
    #     column("method_id"),
    #     column("sample"),
    #     column("phase"),
    #     column("width"),
    #     column("height"),
    #     name="incoming_detections"
    # ).data(
    #     *[(d["data_id"], d["method_id"], d["sample"], d["phase"], d["width"], d["height"]) for d in detections]
    # )

    # # Aliases
    # v = vals.alias("v")
    # cdi = contdatainfo.alias("cdi")
    # g = gap.alias("g")

    # # Calculate detection time
    # detection_time = func.timestampadd(
    #     text("SECOND"),
    #     (v.c.sample * 1.0) / cdi.c.samp_rate,
    #     cdi.c.proc_start
    # )

    # # EXISTS subquery for overlapping gap
    # gap_exists = exists(
    #     select(1).select_from(g).where(
    #         and_(
    #             g.c.data_id == v.c.data_id,
    #             detection_time.between(
    #                 func.timestampadd(text("SECOND"), -buffer, g.c.start),
    #                 func.timestampadd(text("SECOND"),  buffer, g.c.end),
    #             )
    #         )
    #     )
    # )

    # # Select filtered detections
    # select_stmt = (
    #     select(
    #         v.c.data_id,
    #         v.c.method_id,
    #         v.c.sample,
    #         v.c.phase,
    #         v.c.width,
    #         v.c.height,
    #     )
    #     .select_from(v.join(cdi, v.c.data_id == cdi.c.id))
    #     .where(not_(gap_exists))
    # )

    # # Final insert
    # insert_stmt = insert(dldetection).from_select(
    #     ["data_id", "method_id", "sample", "phase", "width", "height"],
    #     select_stmt
    # )

    # # Execute it
    # with engine.begin() as conn:
    #     conn.execute(insert_stmt)


def insert_waveform_source(
    session,
    name,
    details=None,
    path=None,
    filt_low=None,
    filt_high=None,
    detrend=None,
    normalize=None,
    common_samp_rate=None,
):
    new_wf_source = WaveformSource(
        name=name,
        details=details,
        path=path,
        filt_low=filt_low,
        filt_high=filt_high,
        detrend=detrend,
        normalize=normalize,
        common_samp_rate=common_samp_rate,
    )
    session.add(new_wf_source)

    return new_wf_source


def upsert_waveform_source(
    session,
    name,
    details=None,
    path=None,
    filt_low=None,
    filt_high=None,
    detrend=None,
    normalize=None,
    common_samp_rate=None,
):
    insert_stmt = mysql_insert(WaveformSource).values(
        name=name,
        details=details,
        path=path,
        filt_low=filt_low,
        filt_high=filt_high,
        detrend=detrend,
        normalize=normalize,
        common_samp_rate=common_samp_rate,
    )
    update_dict = {
        col.name: insert_stmt.inserted[col.name]
        for col in WaveformSource.__table__.columns
        if col.name != "id"
    }
    upsert_stmt = insert_stmt.on_duplicate_key_update(**update_dict)

    session.execute(upsert_stmt)


def get_waveform_source(session, name):
    result = session.scalars(
        select(WaveformSource).where(WaveformSource.name == name)
    ).all()

    if len(result) == 0:
        return None

    return result[0]


def get_or_insert_waveform_storage_file(session, name):
    info = session.scalars(
        select(WaveformStorageFile).where(WaveformStorageFile.name == name)
    ).first()

    if info is None:
        info = WaveformStorageFile(name=name)
        session.add(info)

    return info


def insert_waveform_pytable(
    session,
    storage_session,
    chan_id,
    pick_id,
    wf_source_id,
    start,
    end,
    data,
    data_id=None,
    # filt_low=None,
    # filt_high=None,
    # proc_notes=None,
    signal_start_ind=None,
    signal_end_ind=None,
):
    file = get_or_insert_waveform_storage_file(session, storage_session.relative_path)
    session.flush()

    new_wf_info = WaveformInfo(
        data_id=data_id,
        chan_id=chan_id,
        pick_id=pick_id,
        wf_source_id=wf_source_id,
        start=start,
        end=end,
        hdf_file_id=file.id,
        # filt_low=filt_low,
        # filt_high=filt_high,
        # proc_notes=proc_notes,
        min_val=np.min(data),
        max_val=np.max(data),
    )
    session.add(new_wf_info)
    session.flush()

    db_id = new_wf_info.id
    storage_session.append(db_id, data, signal_start_ind, signal_end_ind)

    return new_wf_info


def insert_dldetector_output_pytable(
    session, storage_session, data_id, method_id, data
):
    new_detout = DLDetectorOutput(
        data_id=data_id, method_id=method_id, hdf_file=storage_session.file_name
    )

    session.add(new_detout)
    session.flush()

    db_id = new_detout.id
    storage_session.append(db_id, data)

    return new_detout


def insert_repicker_method(
    session,
    name,
    phase=None,
    details=None,
    path=None,
    n_comps=None,
    n_models=None,
    n_evals_per_model=None,
    wf_sample_dur=None,
    wf_proc_pad=None,
    wf_proc_fn_name=None,
    model_settings=None,
):
    new_repicker_method = RepickerMethod(
        name=name,
        phase=phase,
        details=details,
        path=path,
        n_comps=n_comps,
        n_models=n_models,
        n_evals_per_model=n_evals_per_model,
        wf_sample_dur=wf_sample_dur,
        wf_proc_pad=wf_proc_pad,
        wf_proc_fn_name=wf_proc_fn_name,
        model_settings=model_settings,
    )
    session.add(new_repicker_method)

    return new_repicker_method


def upsert_repicker_method(
    session,
    name,
    phase=None,
    details=None,
    path=None,
    n_comps=None,
    n_models=None,
    n_evals_per_model=None,
    wf_sample_dur=None,
    wf_proc_pad=None,
    wf_proc_fn_name=None,
    model_settings=None,
):
    insert_stmt = mysql_insert(RepickerMethod).values(
        name=name,
        phase=phase,
        details=details,
        path=path,
        n_comps=n_comps,
        n_models=n_models,
        n_evals_per_model=n_evals_per_model,
        wf_sample_dur=wf_sample_dur,
        wf_proc_pad=wf_proc_pad,
        wf_proc_fn_name=wf_proc_fn_name,
        model_settings=model_settings,
    )
    update_dict = {
        col.name: insert_stmt.inserted[col.name]
        for col in RepickerMethod.__table__.columns
        if col.name != "id"
    }
    upsert_stmt = insert_stmt.on_duplicate_key_update(**update_dict)

    session.execute(upsert_stmt)


def get_repicker_method(session, name):

    result = session.scalars(
        select(RepickerMethod).where(RepickerMethod.name == name)
    ).all()

    if len(result) == 0:
        return None

    return result[0]


def insert_calibration_method(
    session, name, phase=None, details=None, path=None, loc_type=None, scale_type=None
):
    new_calibration_method = CalibrationMethod(
        name=name,
        phase=phase,
        details=details,
        path=path,
        loc_type=loc_type,
        scale_type=scale_type,
    )
    session.add(new_calibration_method)

    return new_calibration_method


def upsert_calibration_method(
    session, name, phase=None, details=None, path=None, loc_type=None, scale_type=None
):
    insert_stmt = mysql_insert(CalibrationMethod).values(
        name=name,
        phase=phase,
        details=details,
        path=path,
        loc_type=loc_type,
        scale_type=scale_type,
    )
    update_dict = {
        col.name: insert_stmt.inserted[col.name]
        for col in CalibrationMethod.__table__.columns
        if col.name != "id"
    }
    upsert_stmt = insert_stmt.on_duplicate_key_update(**update_dict)

    session.execute(upsert_stmt)


def get_calibration_method(session, name):
    result = session.scalars(
        select(CalibrationMethod).where(CalibrationMethod.name == name)
    ).all()

    if len(result) == 0:
        return None

    return result[0]


def get_or_insert_corr_storage_file(session, name):
    info = session.scalars(
        select(CorrStorageFile).where(CorrStorageFile.name == name)
    ).first()

    if info is None:
        info = CorrStorageFile(name=name)
        session.add(info)

    return info


def insert_pick_correction_pytable(
    session,
    storage,
    pick_id,
    method_id,
    wf_source_id,
    median,
    mean,
    std,
    if_low,
    if_high,
    trim_median,
    trim_mean,
    trim_std,
    predictions,
):
    file = get_or_insert_corr_storage_file(session, storage.file_name)
    session.flush()

    pick_corr = PickCorrection(
        pid=pick_id,
        method_id=method_id,
        wf_source_id=wf_source_id,
        median=median,
        mean=mean,
        std=std,
        if_low=if_low,
        if_high=if_high,
        trim_median=trim_median,
        trim_mean=trim_mean,
        trim_std=trim_std,
        preds_file_id=file.id,
    )
    session.add(pick_corr)
    session.flush()

    db_id = pick_corr.id
    storage.append(db_id, predictions)

    return pick_corr


def get_pick_corrs(session, pick_id):
    stmt = select(PickCorrection).where(PickCorrection.pid == pick_id)

    return session.scalars(stmt).all()


def insert_ci(session, corr_id, method_id, percent, lb, ub):
    new_ci = CredibleInterval(
        corr_id=corr_id, method_id=method_id, percent=percent, lb=lb, ub=ub
    )
    session.add(new_ci)
    return new_ci


def insert_cis(session, ci_dict_list):
    session.execute(insert(CredibleInterval), ci_dict_list)


def get_correction_cis(session, corr_id):

    stmt = select(CredibleInterval).where(CredibleInterval.corr_id == corr_id)

    return session.scalars(stmt).all()


def get_dldet_probs_and_cis(
    session,
    percent,
    phase=None,
    start=None,
    end=None,
    sta=None,
    repicker_method=None,
    calibration_method=None,
    dldetection_method=None,
):
    stmt = (
        select(
            Pick.ptime,
            CredibleInterval.percent,
            CredibleInterval.lb,
            CredibleInterval.ub,
            DLDetection.height,
            DLDetection.width,
        )
        .join(
            PickCorrection,
            PickCorrection.id == CredibleInterval.corr_id,
        )
        .join(Pick, Pick.id == PickCorrection.pid)
        .join(DLDetection, Pick.detid == DLDetection.id)
        .join(Station, Station.id == Pick.sta_id)
        .where(CredibleInterval.percent == percent)
    )

    if phase is not None:
        stmt = stmt.where(Pick.phase == phase)

    if start is not None:
        stmt = stmt.where(Pick.ptime >= start)

    if end is not None:
        stmt = stmt.where(Pick.ptime < end)

    if sta is not None:
        stmt = stmt.where(Station.sta == sta)

    if repicker_method is not None:
        stmt = stmt.join(
            RepickerMethod,
            RepickerMethod.id == PickCorrection.method_id,
            RepickerMethod.name == repicker_method,
        )

    if calibration_method is not None:
        stmt = stmt.join(
            CalibrationMethod,
            CalibrationMethod.id == CredibleInterval.method_id,
            CalibrationMethod.name == calibration_method,
        )

    if dldetection_method is not None:
        stmt = stmt.join(
            DetectionMethod,
            DetectionMethod.id == DLDetection.method_id,
            DetectionMethod.name == dldetection_method,
        )

    return session.execute(stmt).all()


def insert_manual_pick_quality(
    session, corr_id, author, quality, pick_cat=None, ci_cat=None, note=None
):
    qual = ManualPickQuality(
        corr_id=corr_id,
        auth=author,
        quality=quality,
        note=note,
        pick_cat=pick_cat,
        ci_cat=ci_cat,
    )
    session.add(qual)

    return qual


def get_stations_comps_with_picks(session, phase=None, sta=None, chan_pref=None):
    stmt = select(Station.net, Station.sta, Pick.chan_pref, Pick.phase).join_from(
        Station, Pick, Station.id == Pick.sta_id
    )

    if phase is not None:
        stmt = stmt.where(Pick.phase == phase)

    if sta is not None:
        stmt = stmt.where(Station.sta == sta)

    if chan_pref is not None:
        stmt = stmt.where(Pick.chan_pref == chan_pref)

    stmt = stmt.distinct()

    result = session.execute(stmt).all()

    return result


def get_waveform_storage_number(session, chan_id, phase, max_entries):
    count_label = func.count(WaveformInfo.id).label("count")

    channel_subq = (
        select(Channel.seed_code, Channel.sta_id, Channel.loc)
        .where(Channel.id == chan_id)  # you need to define chan_id earlier
        .limit(1)
        .subquery()
    )

    stmt = (
        select(WaveformStorageFile.name, count_label)
        .join_from(
            WaveformInfo,
            WaveformStorageFile,
            WaveformInfo.hdf_file_id == WaveformStorageFile.id,
        )
        .join(Channel, WaveformInfo.chan_id == Channel.id)
        .join(Pick, WaveformInfo.pick_id == Pick.id)
        .where(Channel.seed_code == channel_subq.c.seed_code)
        .where(Channel.sta_id == channel_subq.c.sta_id)
        .where(Channel.loc == channel_subq.c.loc)
        .where(Pick.phase == phase) 
        .group_by(WaveformInfo.hdf_file_id)
        .order_by(WaveformInfo.hdf_file_id)  # count_label.asc())
    )

    # stmt = (
    #     select(WaveformStorageFile.name, count_label)
    #     .join_from(
    #         WaveformInfo,
    #         WaveformStorageFile,
    #         WaveformInfo.hdf_file_id == WaveformStorageFile.id,
    #     )
    #     .join(Pick, WaveformInfo.pick_id == Pick.id)
    #     .where(WaveformInfo.chan_id == chan_id)
    #     .where(Pick.phase == phase)
    #     .group_by(WaveformInfo.hdf_file_id)
    #     .order_by(WaveformInfo.hdf_file_id)  # count_label.asc())
    # )

    result = session.execute(stmt).all()
    print(result)

    if len(result) == 0:
        return 0, None, 0
    elif result[0].count < max_entries:
        return len(result) - 1, result[0].name, result[0].count
    else:
        return len(result), None, 0


class Waveforms:

    @staticmethod
    def get_sorted_waveform_info(
        session,
        phase,
        start,
        end,
        sources: list[str],
        vertical_only=False,
        threeC_only=False,
        # TODO: Can likely remove these options because it is redundant now that
        # the processing information is tied to waveform_source
        wf_filt_low=None,
        wf_filt_high=None,
        sta=None,
        chan_pref=None,
        pick_id_list=None,
    ):
        if vertical_only and threeC_only:
            raise ValueError(
                "Cannot set vertical_only and threeC_only at the same time"
            )

        # Build CASE expression to assign source priority by name
        source_priority = case(
            {name: i for i, name in enumerate(sources)},
            value=WaveformSource.name,
            else_=len(sources),
        )

        stmt = (
            select(Pick, Channel, WaveformInfo)
            .join_from(Pick, WaveformInfo, Pick.id == WaveformInfo.pick_id)
            .join(Channel, Channel.id == WaveformInfo.chan_id)
            .join(Station, Pick.sta_id == Station.id)
            .join(WaveformSource, WaveformSource.id == WaveformInfo.wf_source_id)
            .where(Pick.phase == phase)
            .where(Pick.ptime >= start)
            .where(Pick.ptime < end)
            .where(WaveformSource.name.in_(sources))
            .order_by(
                Station.id, Pick.chan_pref, Pick.id, source_priority, Channel.seed_code
            )
        )

        if pick_id_list is not None:
            stmt = stmt.where(Pick.id.in_(pick_id_list))

        # Only need vertical component for P pick regressor
        if vertical_only:
            stmt = stmt.where(text('channel.seed_code LIKE "__Z"'))
        elif threeC_only:
            group_by_subq = (
                select(WaveformInfo.pick_id, WaveformInfo.wf_source_id)
                .group_by(WaveformInfo.pick_id, WaveformInfo.wf_source_id)
                .having(func.count(WaveformInfo.id) == 3)
                .subquery()
            )
            stmt = stmt.join(
                group_by_subq,
                (WaveformInfo.pick_id == group_by_subq.c.pick_id)
                & (WaveformInfo.wf_source_id == group_by_subq.c.wf_source_id),
            )

        if wf_filt_low is not None:
            stmt = stmt.where(WaveformSource.filt_low == wf_filt_low)

        if wf_filt_high is not None:
            stmt = stmt.where(WaveformSource.filt_high == wf_filt_high)

        if sta is not None:
            stmt = stmt.where(Station.sta == sta)

        if chan_pref is not None:
            stmt = stmt.where(Pick.chan_pref == chan_pref)

        # params = {}
        # if hdf_file_contains is not None:
        #     params["hdf_file_contains"] = hdf_file_contains
        #     stmt = stmt.where(text("waveform_info.hdf_file LIKE :hdf_file_contains"))
        # result = session.execute(stmt, params).all()

        result = session.execute(stmt).all()

        return result

    def gather_waveforms(
        self,
        session,
        n_samples,
        threeC_waveforms,
        channel_index_mapping_fn,
        wf_process_fn,
        start,
        end,
        phase,
        sources,
        include_multiple_wf_sources=False,
        sta=None,
        chan_pref=None,
        pick_id_list=None,
        pad_samples=0,
        on_event=None,
    ):
        threeC_only = True
        vertical_only = False
        ncomps = 3
        if not threeC_waveforms:
            threeC_only = False
            vertical_only = True
            ncomps = 1

        # Get the relevant waveform information from the database and sort so waveforms
        # belonging to the same pick are next to each other
        all_infos = self.get_sorted_waveform_info(
            session,
            phase,
            start,
            end,
            sources,
            threeC_only=threeC_only,
            vertical_only=vertical_only,
            sta=sta,
            chan_pref=chan_pref,
            pick_id_list=pick_id_list,
        )

        if on_event is not None:
            on_event(f"Gathered {len(all_infos)} waveform_info rows")

        # Assume there are 3 wfs for each pick - should be true because of threeC_only=True in query
        n_picks = len(all_infos) // ncomps
        # Waveform information to return
        X = np.zeros((n_picks, n_samples, ncomps))
        # Store pick ids and waveform source ids for inserting results back into the db
        pick_source_ids = []
        # Dictionary to store the open pytables
        wf_storages = {}
        # Keep track of the pervious pick_id and wf_source_id
        prev_pid = -1
        prev_wf_source_id = -1
        # The count of pick waveforms added into X
        n_gathered = 0
        try:
            ## Iterate over the picks ##
            for pick_cnt in np.arange(0, n_picks):
                ## Get the 3C information for the pick - The waveforms should be next to each other from the query ##
                ind1 = pick_cnt * ncomps
                ind2 = ind1 + ncomps
                pick_wf_infos = all_infos[ind1:ind2]

                ## Check the pytables that are loaded and load new ones if necessary ##
                # Do not load the new pytables if they are a duplicate pick id from a lower priorty source
                # This assumes the lower priorty source waveforms will follow the higher priority ones
                if (
                    not include_multiple_wf_sources
                    and pick_wf_infos[0][-1].pick_id == prev_pid
                    and pick_wf_infos[0][-1].wf_source_id != prev_wf_source_id
                ):
                    continue

                pick_wfs, ids, wf_storages = self.get_pick_waveforms(
                    pick_wf_infos, channel_index_mapping_fn, wf_storages=wf_storages
                )

                # DO THE WAVEFORM PROCESSING TOGETHER
                if pick_wfs.shape[1] >= n_samples:
                    i0 = pick_wfs.shape[1] // 2 - n_samples // 2
                    i1 = pick_wfs.shape[1] // 2 + n_samples // 2
                    act_pad = 0
                    if (
                        pad_samples > 0
                        and pick_wfs.shape[1] >= n_samples + pad_samples * 2
                    ):
                        act_pad = pad_samples
                    elif pad_samples > 0 and on_event is not None:
                        on_event(
                            f"Did not pad pick id={ids['pick_id']}, wf_source_id={ids['wf_source_id']}. Not enough signal."
                        )

                    pick_wfs = pick_wfs[0, i0 - act_pad : i1 + act_pad, :]
                    if wf_process_fn is not None:
                        pick_wfs = wf_process_fn(pick_wfs, act_pad)
                    pick_source_ids.append(ids)
                    X[n_gathered, :, :] = pick_wfs
                    n_gathered += 1
                elif on_event is not None:
                    on_event(
                        f"Skipping pick id={ids['pick_id']}, wf_source_id={ids['wf_source_id']}. Not enough signal."
                    )

                prev_wf_source_id = ids["wf_source_id"]
                prev_pid = ids["pick_id"]
        finally:
            for _, wf_storage in wf_storages.items():
                wf_storage.close()

        # Remove any empty rows due to insufficient data
        X = X[0 : len(pick_source_ids), :, :]

        return pick_source_ids, X

    def get_pick_waveforms(
        self,
        pick_wf_infos,
        channel_index_mapping_fn,
        wf_storages={},
    ):
        ncomps = len(pick_wf_infos)
        if ncomps != 1 and ncomps != 3:
            raise ValueError("expected 1 or 3 components")

        try:
            pytables_loaded = self._check_wf_files(wf_storages, pick_wf_infos)
            if not pytables_loaded:
                if ncomps == 3:
                    wf_storages = self._set_3c_wf_storage(
                        pick_wf_infos, pick_wf_infos[0][0].phase
                    )
                else:
                    wf_storages = self._set_1c_wf_storage(pick_wf_infos[0])

            n_samples = wf_storages[
                pick_wf_infos[0][1].seed_code
            ].table.attrs.expected_array_length

            ## Iterate over the different components for the pick ##
            # Keep track of the current pick id an source id
            ids = {}
            curr_pid = -1
            curr_wf_source_id = -1
            # Keep track of the sensory type (channel prefix)
            curr_chan_pref = None
            # Keep track of signal starts and ends
            curr_signal_start = -1
            curr_signal_end = -1
            wf_i0 = -1
            wf_i1 = -1
            for i, info in enumerate(pick_wf_infos):
                pid = info[-1].pick_id
                wf_source_id = info[-1].wf_source_id
                # Get the appropriate channel index given the seed code
                seed_code = info[1].seed_code
                comp_ind = channel_index_mapping_fn(ncomps, seed_code)

                # Get the waveform from the pytable
                wf_info_id = info[-1].id
                wf_row = wf_storages[seed_code].select_row(wf_info_id)
                if wf_row is None:
                    # TODO: Throw error or just say insufficient signal?
                    raise ValueError(
                        f"Waveform for waveform_info.id == {wf_info_id} not found"
                    )

                # Few checks to make sure waveforms belong together
                if curr_pid < 0:
                    curr_pid = pid
                    curr_wf_source_id = wf_source_id
                    curr_chan_pref = seed_code[0:2]
                    curr_signal_start = wf_row["start_ind"]
                    curr_signal_end = wf_row["end_ind"]
                    # Set the start and end inds of the waveforms given how much signal is available
                    if wf_row["start_ind"] > 0 or wf_row["end_ind"] < n_samples:
                        center = n_samples // 2
                        samples_before = center - wf_row["start_ind"]
                        samples_after = wf_row["end_ind"] - center
                        if samples_before > samples_after:
                            wf_i0 = center - samples_after
                            wf_i1 = wf_row["end_ind"]
                        else:
                            wf_i0 = wf_row["start_ind"]
                            wf_i1 = center + samples_before
                    else:
                        wf_i0 = 0
                        wf_i1 = n_samples
                    # To store the 3C waveform for the pick
                    pick_wfs = np.zeros((1, wf_i1 - wf_i0, ncomps))
                else:
                    assert pid == curr_pid, "Pick IDS do not match"
                    assert (
                        wf_source_id == curr_wf_source_id
                    ), "Waveform source ids do not match"
                    # I think this is uncessary because chan_pref is part of the pick
                    # PK but I am scared of combining waveforms that do not belong together...
                    assert (
                        seed_code[0:2] == curr_chan_pref
                    ), "Waveform channel prefixes do not match"
                    assert (
                        wf_row["start_ind"] == curr_signal_start
                    ), "signal start inds do not match"
                    assert (
                        wf_row["end_ind"] == curr_signal_end
                    ), "signal end inds do not match"

                # Store the waveforms for the pick
                pick_wfs[0, :, comp_ind] = wf_row["data"][wf_i0:wf_i1]
                ids["pick_id"] = pid
                ids["wf_source_id"] = wf_source_id

        except Exception as e:
            for _, wf_storage in wf_storages.items():
                wf_storage.close()

            raise e

        return pick_wfs, ids, wf_storages

    def _check_wf_files(self, wf_storages, chan_pick_info):
        """Check that the necessary pytables files storing waveforms are loaded

        Args:
            wf_files (dict): dictionary of pytables files
            pick_info (list): list of tuples containing relevant waveform information from
            the database for 1 pick.

        Returns:
            bool: Whether the pytables files are correct (True) or need to be loaded (False)
        """
        if len(wf_storages.keys()) == 0:
            return False

        for pick_info in chan_pick_info:
            seed_code = pick_info[1].seed_code
            wf_hdf_file = pick_info[-1].hdf_file.name
            if (
                seed_code not in wf_storages.keys()
                or wf_storages[seed_code].stored_hdf_info != wf_hdf_file
            ):
                # Close the pytables before the new set are opened
                for _, wf_storage in wf_storages.items():
                    wf_storage.close()
                return False

        return True

    def _set_3c_wf_storage(self, pick_infos, phase):
        """Load 3 pytables files for the different components

        Args:
            pick_info (list): list of tuples containing relevant waveform information from
            the database for 1 pick.

        Returns:
            dict: dictionary of pytables files
        """
        try:
            wf_storages = {}
            for info in pick_infos:
                wf_hdf_file = info[-1].hdf_file.name
                seed_code = info[1].seed_code
                # Reload the files after resetting them
                if seed_code not in wf_storages.keys():
                    storage = WaveformStorageReader(wf_hdf_file)
                    wf_storages[seed_code] = storage

            # Check that the pytables metadata agree with eachother
            keys = list(wf_storages.keys())
            for i in range(1, 3):
                self._compare_pytables_attrs(
                    wf_storages[keys[i - 1]], wf_storages[keys[i]], phase
                )
        except Exception as e:
            for _, wf_storage in wf_storages.items():
                wf_storage.close()

            raise e

        return wf_storages

    def _set_1c_wf_storage(self, pick_info):
        """Load 1 pytables files for the different components

        Args:
            pick_info (list): list of tuples containing relevant waveform information from
            the database for 1 pick.

        Returns:
            dict: dictionary of pytables files
        """
        try:
            wf_storages = {}
            wf_hdf_file = pick_info[-1].hdf_file.name
            seed_code = pick_info[1].seed_code
            # Reload the files after resetting them
            storage = WaveformStorageReader(wf_hdf_file)
            wf_storages[seed_code] = storage
        except Exception as e:
            for _, wf_storage in wf_storages.items():
                wf_storage.close()

            raise e

        return wf_storages

    def _compare_pytables_attrs(self, prev_storage, curr_storage, phase):
        assert os.path.dirname(prev_storage.file_dir) == os.path.dirname(
            curr_storage.file_dir
        ), "loaded files do not come from the same directory"

        prev_attrs = prev_storage.table.attrs
        curr_attrs = curr_storage.table.attrs
        assert prev_attrs.sta == curr_attrs.sta, "Station names do not match"
        # assert (
        #     prev_attrs.filt_low == curr_attrs.filt_low
        # ), "filt_low values do not match"
        # assert (
        #     prev_attrs.filt_high == curr_attrs.filt_high
        # ), "filt_high values do not match"
        # assert (
        #     curr_attrs.wf_source_id == prev_attrs.wf_source_id
        # ), "Waveform source ids do not match"
        assert curr_attrs.phase == phase, "phase is not as expected"
        assert (
            prev_attrs.expected_array_length == curr_attrs.expected_array_length
        ), "expected_array_lengths do not match"
