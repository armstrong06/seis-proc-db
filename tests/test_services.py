from datetime import datetime, timedelta
import pytest
from copy import deepcopy
from sqlalchemy import func
import numpy as np
import os

from seis_proc_db import services, tables, pytables_backend

dateformat = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture
def stat_ex():
    return deepcopy(
        {
            "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
            "net": "TS",
            "sta": "TEST",
            "lat": 44.7155,
            "lon": -110.67917,
            "elev": 2336,
        }
    )


@pytest.fixture()
def channel_ex():
    return deepcopy(
        {
            "seed_code": "HHZ",
            "loc": "01",
            "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
            "samp_rate": 100.0,
            "clock_drift": 1e-5,
            "sensor_desc": "Nanometrics something or other",
            "sensit_units": "M/S",
            "sensit_val": 9e9,
            "sensit_freq": 5,
            "lat": 44.7155,
            "lon": -110.67917,
            "elev": 2336,
            "depth": 100,
            "azimuth": 90,
            "dip": -90,
            "offdate": None,
            "overall_gain_vel": None,
        }
    )


@pytest.fixture
def contdatainfo_ex():
    return deepcopy(
        {
            "chan_pref": "HH",
            "ncomps": 3,
            "date": datetime(year=2024, month=10, day=1),
            "samp_rate": 100.0,
            "dt": 0.01,
            "orig_npts": 86399,
            "orig_start": datetime.strptime("2024-10-01T00:00:00.05", dateformat),
            "orig_end": datetime.strptime("2024-10-01T23:59:59.55", dateformat),
            "proc_npts": 86400,
            "proc_start": datetime.strptime("2024-10-01T00:00:00.00", dateformat),
        }
    )


@pytest.fixture
def detection_method_ex():
    return deepcopy(
        {
            "name": "TEST-UNET-v6",
            "phase": "P",
            "details": "For P picks, from Armstrong 2023 BSSA paper",
            "path": "the/model/files/are/stored/here",
        }
    )


@pytest.fixture
def repicker_method_ex():
    return deepcopy(
        {
            "name": "TEST-MSWAG-P-3M-120",
            "phase": "P",
            "details": "MSWAG P repicker using 3 models, each making 120 picks, from Armstrong 2023 BSSA paper",
            "path": "the/model/files/are/stored/here",
        }
    )


@pytest.fixture
def calibration_method_ex():
    return deepcopy(
        {
            "name": "TEST-Kuleshov-MSWAG-P-3M-120",
            "phase": "P",
            "details": "Uses Kuleshov et al 2018 approach to calibrate ensemble result from TEST-MSWAG-P-3M-120, from Armstrong 2023 BSSA paper",
            "path": "the/model/files/are/stored/here",
            "loc_type": "median",
            "scale_type": "std",
        }
    )


@pytest.fixture
def waveform_source_ex():
    return deepcopy(
        {
            "name": "TEST-ExtractContData",
            "details": "Extract waveform snippets from the contdata processed with DataLoader",
            "filt_low": 1.5,
            "filt_high": 17.0,
            "detrend": "linear",
            "normalize": "absolute max per channel",
            "common_samp_rate": 100.0,
        }
    )


@pytest.fixture
def pick_ex():
    return deepcopy(
        {
            "chan_pref": "HH",
            "phase": "P",
            "ptime": datetime.strptime("2024-01-02T10:11:12.13", dateformat),
            "auth": "SPDL",
            "snr": 40.5,
            "amp": 10.22,
        }
    )


@pytest.fixture
def gap_ex():
    return deepcopy(
        {
            "start": datetime.strptime("2024-10-01T12:00:00.15", dateformat),
            "end": datetime.strptime("2024-10-01T13:00:00.25", dateformat),
        }
    )


@pytest.fixture
def waveform_ex():
    return deepcopy(
        {
            # "filt_low": 1.5,
            # "filt_high": 17.5,
            "start": datetime.strptime("2024-01-02T10:11:02.13", dateformat),
            "end": datetime.strptime("2024-01-02T10:11:22.14", dateformat),
            # "proc_notes": "Processed for repicker",
            "data": np.zeros((2000)).tolist(),
        }
    )


@pytest.fixture
def db_session_with_station(db_session, stat_ex):
    inserted_stat = services.insert_station(db_session, **stat_ex)
    db_session.commit()

    return db_session, inserted_stat.id


def test_get_operating_channels(db_session):
    min_date = datetime.strptime("2023-01-01T00:00:00.00", dateformat)
    max_date = datetime.strptime("2024-01-01T00:00:00.00", dateformat)
    channel_infos = services.get_operating_channels(
        db_session,
        min_date,
        max_date,
    )

    summary_dict = {}
    for ci in channel_infos:
        key = f"{ci[0]}.{ci[1]}.{ci[2]}.{ci[3][0:2]}"
        if ci[3][1] != "H":
            continue
        if key in summary_dict.keys():
            summary_dict[key]["cnt"] += 1
            summary_dict[key]["chans"].append(ci)
        else:
            summary_dict[key] = {"cnt": 1, "chans": [ci]}

        assert ci[4] <= max_date, "channel.ondate is not less than max_date"
        assert (
            ci[5] is None or ci[5] >= min_date
        ), "channel.offdata is not greater than min_date"

    # One component stations
    onec = {k: v for k, v in summary_dict.items() if v.get("cnt") < 3}
    # Get 3C stations
    threec = {
        k: v
        for k, v in summary_dict.items()
        if v.get("cnt") >= 3 and v.get("cnt") % 3 == 0
    }

    print(onec, threec)
    assert len(onec) == 20, "Expected 20 1C stations in 2023"
    assert len(threec) == 32, "Expected 32 3C stations in 2023"
    assert len(onec) + len(threec) == len(summary_dict)


def test_get_similar_channel_total_ndays(db_session):

    total = services.get_similar_channel_total_ndays(
        db_session, "US", "LKWY", "00", "BHZ"
    )

    assert total == 5548, "incorrect number of days"


def test_insert_station(db_session_with_station):
    db_session, sid = db_session_with_station
    assert db_session.get(tables.Station, sid).sta == "TEST"


def test_get_station(db_session_with_station):
    db_session, sid = db_session_with_station

    # Just in case it would grab the stored object from the Session
    db_session.expunge_all()

    selected_stat = services.get_station(
        db_session,
        "TS",
        "TEST",
        datetime.strptime("1993-10-26T00:00:00.00", dateformat),
    )
    assert selected_stat is not None, "station was not found"
    assert (
        selected_stat.lat == 44.7155
        and selected_stat.lon == -110.67917
        and selected_stat.elev == 2336
    ), "selected station location is incorrect"


def test_get_operating_station_by_name(db_session_with_station):
    db_session, sid = db_session_with_station

    # Just in case it would grab the stored object from the Session
    db_session.expunge_all()

    selected_stat = services.get_operating_station_by_name(db_session, "TEST", 2003)
    assert selected_stat is not None, "station was not found"
    assert (
        selected_stat.lat == 44.7155
        and selected_stat.lon == -110.67917
        and selected_stat.elev == 2336
    ), "selected station location is incorrect"


def test_station_no_results(db_session):
    ondate = datetime.strptime("1993-10-26T00:00:00.00", dateformat)

    selected_stat = services.get_station(db_session, "TS", "TEST", ondate)
    assert selected_stat is None, "get_station did not return None"


@pytest.fixture
def db_session_with_multiple_channels(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

    common_chan_dict = channel_ex
    common_chan_dict["sta_id"] = sid

    cnt0 = db_session.execute(func.count(tables.Channel.id)).one()[0]

    c1, c2, c3, c4 = (
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
    )

    c1["seed_code"] = "HHE"
    c2["seed_code"] = "HHN"
    c3["seed_code"] = "HHZ"
    c4["seed_code"] = "EHZ"

    services.insert_channels(db_session, [c1, c2, c3, c4])

    db_session.commit()
    cnt1 = db_session.execute(func.count(tables.Channel.id)).one()[0]
    info = {"sta_id": sid, "cnt0": cnt0, "cnt1": cnt1}

    return db_session, info


def test_insert_channels(db_session_with_multiple_channels):
    db_session, info = db_session_with_multiple_channels
    assert info["cnt1"] - info["cnt0"] == 4, "incorrect number of channels inserted"


def test_insert_ignore_channels_common_stat(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

    common_chan_dict = channel_ex

    cnt0 = db_session.execute(func.count(tables.Channel.id)).one()[0]

    c1, c2, c3 = (
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
    )

    c1["seed_code"] = "HHE"
    c2["seed_code"] = "HHN"
    c3["seed_code"] = "HHZ"

    services.insert_ignore_channels_common_stat(db_session, sid, [c1, c2, c3])
    db_session.commit()
    cnt1 = db_session.execute(func.count(tables.Channel.id)).one()[0]
    assert cnt1 - cnt0 == 3


@pytest.fixture
def db_session_with_single_channel(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

    chan_dict = channel_ex
    chan_dict["sta_id"] = sid
    inserted_chan = services.insert_channel(db_session, chan_dict)
    db_session.commit()

    return db_session, sid, inserted_chan.id


def test_insert_channel(db_session_with_single_channel):
    db_session, sid, cid = db_session_with_single_channel
    assert db_session.get(tables.Channel, cid).seed_code == "HHZ"


def test_get_channel(db_session_with_single_channel):
    db_session, sid, cid = db_session_with_single_channel
    db_session.expunge_all()

    selected_chan = services.get_channel(
        db_session,
        sid,
        "HHZ",
        "01",
        datetime.strptime("1993-10-26T00:00:00.00", dateformat),
    )

    assert selected_chan is not None, "Channel not found"
    assert selected_chan.sta_id == sid, "Incorrect station id"
    assert (
        selected_chan.lat == 44.7155
        and selected_chan.lon == -110.67917
        and selected_chan.elev == 2336
    ), "Incorrect station location"


def test_get_all_station_channels(db_session_with_multiple_channels):
    db_session, info = db_session_with_multiple_channels
    db_session.expunge_all()

    chan_list = services.get_all_station_channels(db_session, info["sta_id"])

    assert len(chan_list) == 4, "Incorrect number of Channels"


def test_get_operating_channels_by_station_name(db_session_with_multiple_channels):
    db_session, info = db_session_with_multiple_channels
    db_session.expunge_all()

    station = db_session.get(tables.Station, info["sta_id"])

    station, channels = services.get_operating_channels_by_station_name(
        db_session,
        station.sta,
        "HH",
        datetime.strptime("2005-10-26T00:00:00.00", dateformat),
    )
    assert len(channels) == 3


def test_get_common_station_channels(db_session_with_multiple_channels):
    db_session, info = db_session_with_multiple_channels
    db_session.expunge_all()

    chan_list = services.get_common_station_channels(db_session, info["sta_id"], "HH")
    assert len(chan_list) == 3, "Incorrect number of Channels"


def test_get_common_station_channels_1c(db_session_with_multiple_channels):
    db_session, info = db_session_with_multiple_channels
    db_session.expunge_all()

    chan_list = services.get_common_station_channels(db_session, info["sta_id"], "EHZ")
    assert len(chan_list) == 1, "Incorrect number of Channels"


def test_get_common_station_channels_by_name(db_session_with_multiple_channels):
    db_session, info = db_session_with_multiple_channels
    sta_name = db_session.get(tables.Station, info["sta_id"]).sta
    db_session.expunge_all()
    chan_list = services.get_common_station_channels_by_name(db_session, sta_name, "HH")
    assert len(chan_list) == 3, "Incorrect number of Channels"


@pytest.fixture
def db_session_with_contdatainfo(db_session_with_station, contdatainfo_ex):
    db_session, sid = db_session_with_station

    d = contdatainfo_ex
    d["sta_id"] = sid

    inserted_contdatainfo = services.insert_contdatainfo(db_session, d)
    db_session.commit()

    return db_session, sid, inserted_contdatainfo.id


def test_insert_contdatainfo(db_session_with_contdatainfo):
    db_session, sid, dataid = db_session_with_contdatainfo
    contdatainfo = db_session.get(tables.DailyContDataInfo, dataid)
    assert contdatainfo.chan_pref == "HH", "invalid chan_pref"
    assert contdatainfo.id is not None, "id not set"


def test_get_contdatainfo(db_session_with_contdatainfo, contdatainfo_ex):
    d = contdatainfo_ex
    db_session, sid, dataid = db_session_with_contdatainfo
    db_session.expunge_all()

    selected_info = services.get_contdatainfo(
        db_session, sid, d["chan_pref"], d["ncomps"], d["date"]
    )

    assert selected_info is not None, "no contdatainfo selected"
    assert selected_info.id is not None, "contdatainfo has no id"
    assert selected_info.samp_rate == 100, "sampling rate is incorrect"


def test_insert_detection_method(db_session, detection_method_ex):
    d = detection_method_ex
    inserted_det_meth = services.insert_detection_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
    )
    db_session.commit()
    assert inserted_det_meth.name == "TEST-UNET-v6", "incorrect name"
    assert inserted_det_meth.phase == "P", "incorrect phase"


def test_get_detection_method(db_session, detection_method_ex):
    d = detection_method_ex
    inserted_det_meth = services.insert_detection_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
    )
    db_session.commit()
    db_session.expunge_all()

    selected_method = services.get_detection_method(db_session, d["name"])
    assert selected_method.name == "TEST-UNET-v6", "incorrect name"


def test_get_detection_method_none(db_session, detection_method_ex):
    d = detection_method_ex
    selected_method = services.get_detection_method(db_session, d["name"])
    assert selected_method is None, "method is not None"


def test_upsert_detection_method(db_session, detection_method_ex):
    d = detection_method_ex
    inserted_det_meth = services.insert_detection_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
    )
    db_session.commit()
    method_id = inserted_det_meth.id
    db_session.expunge_all()
    d["phase"] = "S"
    d["path"] = "new/path"
    services.upsert_detection_method(db_session, **d)
    db_session.commit()
    updated_meth = db_session.get(tables.DetectionMethod, method_id)

    assert updated_meth.phase == "S", f"phase not updated"
    assert updated_meth.path == "new/path", "path not updated"


@pytest.fixture
def db_session_with_gap(db_session_with_contdatainfo, channel_ex, gap_ex):
    db_session, sid, cid = db_session_with_contdatainfo
    chan_dict = channel_ex
    chan_dict["sta_id"] = sid
    chan = services.insert_channel(db_session, chan_dict)
    db_session.commit()

    inserted_gap = services.insert_gap(
        db_session, data_id=cid, chan_id=chan.id, **gap_ex
    )
    db_session.commit()

    ids = {"sta": sid, "data": cid, "chan": chan.id, "gap": inserted_gap.id}

    return db_session, ids


def test_insert_gap(db_session_with_gap):
    db_session, ids = db_session_with_gap
    inserted_gap = db_session.get(tables.Gap, ids["gap"])
    assert inserted_gap.id is not None
    assert inserted_gap.end > inserted_gap.start, "Invalid times"
    assert inserted_gap.startsamp == 4320015, "invalid startsamp"
    assert inserted_gap.endsamp == 4680025, "invalid endsamp"


def test_get_gaps(db_session_with_gap):
    db_session, ids = db_session_with_gap
    selected_gaps = services.get_gaps(db_session, ids["chan"], ids["data"])

    assert len(selected_gaps) == 1, "incorrect number of gaps"
    assert selected_gaps[0].id is not None, "gap id is not set"


def test_insert_gaps(db_session_with_gap, gap_ex):
    db_session, ids = db_session_with_gap

    common_gap_dict = gap_ex
    common_gap_dict["chan_id"] = ids["chan"]
    common_gap_dict["data_id"] = ids["data"]

    cnt0 = db_session.execute(func.count(tables.Gap.id)).one()[0]

    g1, g2, g3 = (
        deepcopy(common_gap_dict),
        deepcopy(common_gap_dict),
        deepcopy(common_gap_dict),
    )

    g1["start"] += timedelta(minutes=60)
    g1["end"] += timedelta(minutes=60)
    g2["start"] = g1["end"] + timedelta(minutes=60)
    g2["end"] = g2["start"] + timedelta(minutes=120)
    g3["start"] = g2["end"] + timedelta(minutes=60)
    g3["end"] = g3["start"] + timedelta(minutes=120)

    services.insert_gaps(db_session, [g1, g2, g3])

    db_session.commit()

    cnt1 = db_session.execute(func.count(tables.Gap.id)).one()[0]
    assert cnt1 - cnt0 == 3, "3 gaps were not added"


@pytest.fixture
def db_session_with_dldetection(db_session_with_gap, detection_method_ex):
    db_session, ids = db_session_with_gap
    inserted_method = services.insert_detection_method(
        db_session, **detection_method_ex
    )
    db_session.commit()

    d = {"sample": 1000, "phase": "P", "width": 40, "height": 90}
    inserted_dldet = services.insert_dldetection(
        db_session, ids["data"], inserted_method.id, **d
    )
    db_session.commit()

    ids["dldet"] = inserted_dldet.id
    ids["method"] = inserted_method.id

    return db_session, ids


def test_insert_dldetection(db_session_with_dldetection):
    db_session, ids = db_session_with_dldetection

    inserted_dldet = db_session.get(tables.DLDetection, ids["dldet"])

    assert inserted_dldet.id > 0, "No id"
    assert inserted_dldet.phase == "P"
    assert inserted_dldet.sample == 1000


@pytest.fixture
def db_session_with_dldet_pick(
    db_session_with_dldetection, pick_ex, waveform_source_ex
):
    db_session, ids = db_session_with_dldetection

    inserted_pick = services.insert_pick(
        db_session, sta_id=ids["sta"], detid=ids["dldet"], **pick_ex
    )
    db_session.commit()

    ids["pick"] = inserted_pick.id

    # Add waveform source because it will be needed when adding a waveform to the pick#
    isource = services.insert_waveform_source(db_session, **waveform_source_ex)
    db_session.commit()
    ids["wf_source"] = isource.id

    return db_session, ids


def test_insert_pick(db_session_with_dldet_pick):
    db_session, ids = db_session_with_dldet_pick
    inserted_pick = db_session.get(tables.Pick, ids["pick"])
    assert inserted_pick.id is not None
    assert inserted_pick.detid == ids["dldet"]
    assert inserted_pick.phase == "P"


def test_bulk_insert_dldetections_with_gap_check_outside_gap(
    db_session_with_dldetection,
):
    db_session, ids = db_session_with_dldetection
    cnt0 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    new_det1 = {
        "sample": 11 * 60 * 60 * 100,
        "phase": "P",
        "width": 20,
        "height": 70,
        "data_id": ids["data"],
        "method_id": ids["method"],
        "buffer": 0.0,
        "inference_id": None,
    }
    new_det2 = deepcopy(new_det1)
    new_det2["sample"] = 5000
    new_det2["height"] = 60
    new_det3 = deepcopy(new_det1)
    new_det3["sample"] = 6000
    new_det3["height"] = 50
    new_det4 = deepcopy(new_det1)
    new_det4["sample"] = 7000
    new_det4["height"] = 40
    services.bulk_insert_dldetections_with_gap_check(
        db_session, [new_det1, new_det2, new_det3, new_det4]
    )
    db_session.commit()
    cnt1 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    assert cnt1 - cnt0 == 4, "Detection not inserted"

    inserted_dets = services.get_dldetections(
        db_session, ids["data"], ids["method"], 70, "P"
    )
    assert (
        len(inserted_dets) == 2
    ), "incorrect number of dets returned with min_height=70"
    inserted_dets = services.get_dldetections(
        db_session, ids["data"], ids["method"], 71, "P"
    )
    assert (
        len(inserted_dets) == 1
    ), "incorrect number of dets returned with min_height=71"
    inserted_dets = services.get_dldetections(
        db_session, ids["data"], ids["method"], 50, "P"
    )
    assert (
        len(inserted_dets) == 4
    ), "incorrect number of dets returned with min_height=50"


def test_bulk_insert_dldetections_with_gap_check_inside_gap(
    db_session_with_dldetection,
):
    db_session, ids = db_session_with_dldetection
    cnt0 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    new_pick = {
        "sample": 12.5 * 60 * 60 * 100,
        "phase": "P",
        "width": 20,
        "height": 80,
        "data_id": ids["data"],
        "method_id": ids["method"],
        "buffer": 0.0,
        "inference_id": None,
    }
    services.bulk_insert_dldetections_with_gap_check(db_session, [new_pick])
    db_session.commit()
    cnt1 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    assert cnt1 - cnt0 == 0, "Detection inserted"


def test_bulk_insert_dldetections_with_gap_check_inside_buffer(
    db_session_with_dldetection,
):
    db_session, ids = db_session_with_dldetection
    cnt0 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    new_pick = {
        "sample": 4320000,
        "phase": "P",
        "width": 20,
        "height": 80,
        "data_id": ids["data"],
        "method_id": ids["method"],
        "inference_id": None,
    }
    # print(db_session.get(tables.Gap, ids["gap"]))
    services.bulk_insert_dldetections_with_gap_check(db_session, [new_pick])
    db_session.commit()

    cnt1 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]

    # from sqlalchemy import text, select

    # dets = db_session.scalars(
    #     select(tables.DLDetection).from_statement(text("select * from dldetection"))
    # ).all()
    # print(
    #     "data start",
    #     db_session.get(tables.DailyContDataInfo, ids["data"]).proc_start,
    # )
    # print("Det time", dets[-1].time)
    # print(db_session.get(tables.Gap, ids["gap"]))
    # print(
    #     "Gap buffered times",
    #     db_session.execute(
    #         text(
    #             """select TIMESTAMPADD(MICROSECOND, -@buffer*1E6, gap.start),
    #             TIMESTAMPADD(MICROSECOND, @buffer*1E6, gap.end)
    #             from gap where gap.id = :id"""
    #         ),
    #         {"id": ids["gap"]},
    #     ).all(),
    # )

    # TODO: Add more checks
    assert cnt1 - cnt0 == 0, "Detection inserted"


@pytest.fixture
def db_session_with_multiple_channel_gaps(
    db_session_with_contdatainfo, channel_ex, gap_ex, detection_method_ex
):
    db_session, sid, cid = db_session_with_contdatainfo

    common_chan_dict = channel_ex
    common_chan_dict["sta_id"] = sid

    c1, c2, c3 = (
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
        deepcopy(common_chan_dict),
    )

    c1["seed_code"] = "HHE"
    c2["seed_code"] = "HHN"
    c3["seed_code"] = "HHZ"

    services.insert_channels(db_session, [c1, c2, c3])
    db_session.commit()
    channels = services.get_common_station_channels(db_session, sid, "HH")

    gaps = []
    for i, chan in enumerate(channels):
        g = deepcopy(gap_ex)
        g["sta_id"] = sid
        g["data_id"] = cid
        g["chan_id"] = chan.id
        g["start"] += timedelta(minutes=((-1 + i) * 10))
        gaps.append(g)
    services.insert_gaps(db_session, gaps)

    inserted_method = services.insert_detection_method(
        db_session, **detection_method_ex
    )
    db_session.commit()
    ids = {"sta": sid, "data": cid, "chan": chan.id, "method": inserted_method.id}

    return db_session, ids


def test_bulk_insert_dldetections_with_multiple_channel_gaps(
    db_session_with_multiple_channel_gaps,
):
    db_session, ids = db_session_with_multiple_channel_gaps
    cnt0 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    new_pick = {
        "sample": 4319915,
        "phase": "P",
        "width": 20,
        "height": 80,
        "data_id": ids["data"],
        "method_id": ids["method"],
        "inference_id": None,
    }
    # print(db_session.get(tables.Gap, ids["gap"]))
    services.bulk_insert_dldetections_with_gap_check(db_session, [new_pick])
    db_session.commit()

    cnt1 = db_session.execute(func.count(tables.DLDetection.id)).one()[0]
    assert cnt1 - cnt0 == 0, "Detection inserted"


@pytest.fixture
def db_session_with_pick_waveform(db_session_with_dldet_pick, waveform_ex):
    db_session, ids = db_session_with_dldet_pick

    new_wf = services.insert_waveform(
        db_session,
        data_id=ids["data"],
        chan_id=ids["chan"],
        pick_id=ids["pick"],
        wf_source_id=ids["wf_source"],
        **waveform_ex,
    )

    db_session.commit()

    ids["wf"] = new_wf.id

    return db_session, ids


def test_insert_waveform(db_session_with_pick_waveform):
    db_session, ids = db_session_with_pick_waveform

    new_wf = db_session.get(tables.Waveform, ids["wf"])

    assert new_wf.id is not None, "ID is not set"
    assert len(new_wf.data) == 2000, "data length is invalid"
    # assert new_wf.filt_low == 1.5, "filt_low is invalid"


def test_get_waveforms(db_session_with_pick_waveform):
    db_session, ids = db_session_with_pick_waveform

    wfs = services.get_waveforms(db_session, ids["pick"])
    assert len(wfs) == 1, "incorrect number of waveforms"


def test_insert_pick_and_waveform_manual(
    db_session_with_dldetection, pick_ex, waveform_ex, waveform_source_ex
):
    db_session, ids = db_session_with_dldetection
    wf_source = services.insert_waveform_source(db_session, **waveform_source_ex)
    db_session.flush()

    inserted_pick = services.insert_pick(
        db_session, sta_id=ids["sta"], detid=ids["dldet"], **pick_ex
    )

    # db_session.commit()
    new_wf = tables.Waveform(
        data_id=ids["data"],
        chan_id=ids["chan"],
        pick_id=None,
        wf_source_id=wf_source.id,
        **waveform_ex,
    )
    inserted_pick.wfs.add(new_wf)
    # new_wf = services.insert_waveform(
    #     db_session,
    #     data_id=ids["data"],
    #     chan_id=ids["chan"],
    #     pick_id=inserted_pick.id,
    #     **waveform_ex,
    # )
    db_session.commit()
    assert inserted_pick.id is not None
    assert new_wf.pick_id is not None
    assert new_wf.id is not None


def test_get_picks(db_session_with_dldet_pick):
    db_session, ids = db_session_with_dldet_pick

    picks = services.get_picks(db_session, ids["sta"], "HH")
    assert len(picks) == 1, "incorrect number of picks"


# This fail, so you can't get column_properties from db unless using ORM (unsurprising)
# def test_get_startsamp(db_session_with_gap):
#     db_session, ids = db_session_with_gap
#     from sqlalchemy import text

#     startsamp = db_session.execute(
#         text("SELECT startsamp from gap where gap.id = :gap_id"), {"gap_id": ids["gap"]}
#     )


@pytest.fixture
def db_session_with_waveform_info(
    db_session_with_dldet_pick,
    waveform_ex,
    mock_pytables_config,
):
    db_session, ids = db_session_with_dldet_pick

    # Add pytable
    wf_storage = pytables_backend.WaveformStorage(
        expected_array_length=2000,
        net="JK",
        sta="TEST",
        loc="",
        seed_code="HHZ",
        ncomps=3,
        phase="P",
        wf_source_id=ids["wf_source"],
    )
    #

    new_wf_info = services.insert_waveform_pytable(
        db_session,
        wf_storage,
        data_id=ids["data"],
        chan_id=ids["chan"],
        pick_id=ids["pick"],
        wf_source_id=ids["wf_source"],
        **waveform_ex,
    )

    db_session.commit()
    wf_storage.commit()

    ids["wf_info"] = new_wf_info.id

    return db_session, wf_storage, ids


def test_insert_waveform_pytable(db_session_with_waveform_info, waveform_ex):
    try:
        db_session, wf_storage, ids = db_session_with_waveform_info

        db_id = ids["wf_info"]
        new_wf_info = db_session.get(tables.WaveformInfo, db_id)
        assert db_id is not None, "WaveformInfo.id is not set"
        assert wf_storage.table.nrows == 1, "incorrect number of rows in table"
        row = wf_storage.select_row(db_id)
        assert row["id"] == db_id, "incorrect id"
        assert row["start_ind"] == 0, "incorrect start_ind"
        assert row["end_ind"] == 2000, "incorrect end_ind"
        assert np.array_equal(row["data"], waveform_ex["data"]), "incorrect data"
        assert (
            datetime.fromtimestamp(row["last_modified"]).date() == datetime.now().date()
        ), "incorrect last_modified date"
        assert (
            datetime.fromtimestamp(row["last_modified"]) - new_wf_info.last_modified
        ).microseconds * 1e-6 < 2, (
            "WaveformInfo.last_modified and Pytables.Row.last_modified are not close"
        )
        assert (
            new_wf_info.hdf_file.name == wf_storage.relative_path
        ), "wf_info hdf_file incorrect"
        assert new_wf_info.chan_id == ids["chan"], "wf_info chan id incorrect"
        assert new_wf_info.pick_id == ids["pick"], "wf_info pick_id incorrect"
        assert new_wf_info.data_id == ids["data"], "wf_info data_id incorrect"
        # assert new_wf_info.filt_low == 1.5, "wf_info filt_low incorrect"
        # assert new_wf_info.filt_high == 17.5, "wf_info filt_high incorrect"
        assert new_wf_info.min_val == np.min(waveform_ex["data"]), "Incorrect min_val"
        assert new_wf_info.max_val == np.max(waveform_ex["data"]), "Incorrect min_val"
        assert new_wf_info.start == datetime.strptime(
            "2024-01-02T10:11:02.13", dateformat
        ), "wf_info start incorrect"
        assert new_wf_info.end == datetime.strptime(
            "2024-01-02T10:11:22.14", dateformat
        ), "wf_info end incorrect"
        # assert (
        #     new_wf_info.proc_notes == "Processed for repicker"
        # ), "wf_info proc_notes incorrect"
        assert new_wf_info.duration_samples == 2001, "incorrect duration"
        print(new_wf_info.pick_id, new_wf_info.start, new_wf_info.samp_rate)
        print(new_wf_info.pick_index, new_wf_info.duration_samples)
        assert new_wf_info.pick_index == 1000, "incorrect pick_index"

    finally:
        # Clean up
        wf_storage.close()
        os.remove(wf_storage.file_path)
        assert not os.path.exists(wf_storage.file_path), "the file was not removed"


def test_get_waveform_infos(db_session_with_waveform_info):
    db_session, wf_storage, ids = db_session_with_waveform_info
    try:
        wfs = services.get_waveform_infos(db_session, ids["pick"])
        assert len(wfs) == 1, "incorrect number of waveforms"
    finally:
        # Clean up
        wf_storage.close()
        os.remove(wf_storage.file_path)
        assert not os.path.exists(wf_storage.file_path), "the file was not removed"


def test_get_waveform_infos_and_data(db_session_with_waveform_info, waveform_ex):
    db_session, wf_storage, ids = db_session_with_waveform_info
    try:
        wfs = services.get_waveform_infos_and_data(db_session, wf_storage, ids["pick"])
        assert len(wfs) == 1, "incorrect number of waveforms"
        assert wfs[0][0].id == ids["wf_info"], "incorrect in db_wf_info"
        assert np.array_equal(wfs[0][1]["data"], waveform_ex["data"]), "incorrect data"
        assert wfs[0][1]["id"] == ids["wf_info"]
    finally:
        # Clean up
        wf_storage.close()
        os.remove(wf_storage.file_path)
        assert not os.path.exists(wf_storage.file_path), "the file was not removed"


def test_insert_dldetector_output_pytable(
    db_session_with_dldet_pick, mock_pytables_config
):
    try:
        db_session, ids = db_session_with_dldet_pick

        detout_storage = pytables_backend.DLDetectorOutputStorage(
            expected_array_length=8640000,
            net="JK",
            sta="TEST",
            loc="",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            det_method_id=ids["method"],
        )

        data = np.zeros(8640000).astype(np.uint8)
        new_detout_id = services.insert_dldetector_output_pytable(
            db_session,
            detout_storage,
            data_id=ids["data"],
            method_id=ids["method"],
            data=data,
        )

        db_session.commit()
        detout_storage.commit()

        db_id = new_detout_id.id
        assert db_id is not None, "DLDetectorOutput.id is not set"
        assert detout_storage.table.nrows == 1, "incorrect number of rows in table"
        row = [row for row in detout_storage.table.where(f"id == {db_id}")][0]
        assert row["id"] == db_id, "incorrect id"
        assert np.array_equal(row["data"], data), "incorrect data"
        assert (
            datetime.fromtimestamp(row["last_modified"]).date() == datetime.now().date()
        ), "incorrect last_modified date"
        assert (
            datetime.fromtimestamp(row["last_modified"]) - new_detout_id.last_modified
        ).microseconds * 1e-6 < 2, "DLDetectorOutput.last_modified and Pytables.Row.last_modified are not close"

    finally:
        # Clean up
        detout_storage.close()
        os.remove(detout_storage.file_path)
        assert not os.path.exists(detout_storage.file_path), "the file was not removed"


def test_insert_repicker_method(db_session, repicker_method_ex):
    d = repicker_method_ex
    inserted_repick_meth = services.insert_repicker_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
    )
    db_session.commit()
    assert inserted_repick_meth.name == "TEST-MSWAG-P-3M-120", "incorrect name"
    assert inserted_repick_meth.phase == "P", "incorrect phase"


def test_get_repicker_method(db_session, repicker_method_ex):
    d = repicker_method_ex
    _ = services.insert_repicker_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
    )
    db_session.commit()
    db_session.expunge_all()

    selected_method = services.get_repicker_method(db_session, d["name"])
    assert selected_method.name == "TEST-MSWAG-P-3M-120", "incorrect name"


def test_insert_ci_method(db_session, calibration_method_ex):
    d = calibration_method_ex
    inserted_repick_meth = services.insert_calibration_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
        loc_type=d["loc_type"],
        scale_type=d["scale_type"],
    )
    db_session.commit()
    assert inserted_repick_meth.name == "TEST-Kuleshov-MSWAG-P-3M-120", "incorrect name"
    assert inserted_repick_meth.phase == "P", "incorrect phase"


def test_get_ci_method(db_session, calibration_method_ex):
    d = calibration_method_ex
    _ = services.insert_calibration_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
        loc_type=d["loc_type"],
        scale_type=d["scale_type"],
    )
    db_session.commit()
    db_session.expunge_all()

    selected_method = services.get_calibration_method(db_session, d["name"])
    assert selected_method.name == "TEST-Kuleshov-MSWAG-P-3M-120", "incorrect name"


@pytest.fixture
def db_session_with_pick_corr(
    db_session_with_dldet_pick,
    mock_pytables_config,
    repicker_method_ex,
    calibration_method_ex,
    waveform_source_ex,
):
    db_session, ids = db_session_with_dldet_pick
    d = repicker_method_ex
    repicker_method = services.insert_repicker_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
    )
    d = calibration_method_ex
    cal_method = services.insert_calibration_method(
        db_session,
        name=d["name"],
        phase=d["phase"],
        details=d["details"],
        path=d["path"],
        loc_type=d["loc_type"],
        scale_type=d["scale_type"],
    )

    db_session.flush()

    preds = np.random.random((360,)).astype(np.float32)

    corr_storage = pytables_backend.SwagPicksStorage(
        360,
        phase="P",
        start="2023-01-01",
        end="2023-01-31",
        repicker_method_id=repicker_method.id,
    )

    pick_corr = services.insert_pick_correction_pytable(
        db_session,
        corr_storage,
        ids["pick"],
        repicker_method.id,
        ids["wf_source"],
        median=np.median(preds),
        mean=np.mean(preds),
        std=np.std(preds),
        if_low=0,
        if_high=1,
        trim_median=0,
        trim_mean=0.1,
        trim_std=0.05,
        predictions=preds,
    )
    db_session.commit()
    corr_storage.commit()

    ids["corr"] = pick_corr.id
    ids["repicker_method"] = repicker_method.id
    ids["cal_method"] = cal_method.id

    ci = services.insert_ci(db_session, ids["corr"], ids["cal_method"], 90, -1.22, 1.34)
    db_session.commit()
    ids["ci"] = ci.id

    return db_session, corr_storage, ids, preds


def test_insert_pick_correction_pytable(db_session_with_pick_corr):
    try:
        db_session, corr_storage, ids, preds = db_session_with_pick_corr

        pick_corr = db_session.get(tables.PickCorrection, ids["corr"])

        assert ids["corr"] is not None, "PickCorrection.id is not set"
        assert corr_storage.table.nrows == 1, "Expected 1 rows in pytable"
        row = [row for row in corr_storage.table.where(f'id == {ids["corr"]}')][0]
        assert row["id"] == ids["corr"], "incorrect id"
        assert np.array_equal(row["data"], preds), "incorrect data"
        assert (
            datetime.fromtimestamp(row["last_modified"]).date() == datetime.now().date()
        ), "incorrect last_modified date"
        assert (
            datetime.fromtimestamp(row["last_modified"]) - pick_corr.last_modified
        ).microseconds * 1e-6 < 2, (
            "PickCorrection.last_modified and Pytables.Row.last_modified are not close"
        )

    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"


def test_insert_ci(db_session_with_pick_corr):
    try:
        db_session, corr_storage, ids, _ = db_session_with_pick_corr
    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"

    ci = db_session.get(tables.CredibleInterval, ids["ci"])

    assert ci is not None
    assert ci.id is not None
    assert ci.method_id == ids["cal_method"]
    assert ci.percent == 90
    assert ci.lb == -1.22
    assert ci.ub == 1.34


def test_get_cis(db_session_with_pick_corr):
    try:
        db_session, corr_storage, ids, _ = db_session_with_pick_corr
    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"

    cis = services.get_correction_cis(db_session, ids["corr"])
    assert len(cis) == 1
    ci = cis[0]
    assert ci is not None
    assert ci.id is not None
    assert ci.method_id == ids["cal_method"]
    assert ci.percent == 90
    assert ci.lb == -1.22
    assert ci.ub == 1.34


def test_insert_cis(db_session_with_pick_corr):
    try:
        db_session, corr_storage, ids, _ = db_session_with_pick_corr
    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"

    cnt0 = db_session.execute(func.count(tables.CredibleInterval.id)).one()[0]
    cis_list = [
        {
            "corr_id": ids["corr"],
            "method_id": ids["cal_method"],
            "percent": 60,
            "lb": -1.11,
            "ub": 1.22,
        }
    ]
    services.insert_cis(db_session, cis_list)
    db_session.commit()

    cnt1 = db_session.execute(func.count(tables.CredibleInterval.id)).one()[0]
    assert cnt1 - cnt0 == 1, "Expected 1 CI to be inserted"

    cis = services.get_correction_cis(db_session, ids["corr"])
    assert len(cis) == 1
    ci = cis[0]
    assert ci is not None
    assert ci.id is not None
    assert ci.method_id == ids["cal_method"]
    assert ci.percent == 60
    assert ci.lb == -1.11
    assert ci.ub == 1.22


def test_make_pick_catalog(
    db_session_with_pick_corr,
    repicker_method_ex,
    calibration_method_ex,
):
    try:
        db_session, corr_storage, ids, _ = db_session_with_pick_corr
        repick_dict = repicker_method_ex
        cal_dict = calibration_method_ex
    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"

    df = services.make_pick_catalog_df(
        db_session, "P", repick_dict["name"], cal_dict["name"], 90
    )

    pick = db_session.get(tables.Pick, ids["pick"])
    sta = db_session.get(tables.Station, ids["sta"])
    corr = db_session.get(tables.PickCorrection, ids["corr"])
    ci = db_session.get(tables.CredibleInterval, ids["ci"])

    assert len(df) == 1, "expected one row to be returned"
    row = df.iloc[0]
    assert row["pick_identifier"] == pick.id
    assert row["network"] == sta.net
    assert row["station"] == sta.sta
    assert row["channel"] == pick.chan_pref
    assert row["location_code"] == ""
    assert row["phase_hint"] == "P"
    # assert result[0][6] == pick.ptime
    # assert result[0][7] == corr.median
    from datetime import timezone

    assert (
        row["arrival_time"]
        == (pick.ptime + timedelta(microseconds=corr.median * 1e6))
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    assert row["uncertainty"] == ci.ub - ci.lb


def test_make_pick_catalog_max_width(
    db_session_with_pick_corr,
    repicker_method_ex,
    calibration_method_ex,
):
    try:
        db_session, corr_storage, ids, _ = db_session_with_pick_corr
        repick_dict = repicker_method_ex
        cal_dict = calibration_method_ex
    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"

    result, _ = services.make_pick_catalog_df(
        db_session, "P", repick_dict["name"], cal_dict["name"], 90, max_width=2.0
    )

    assert len(result) == 0, "expected 0 rows to be returned"


def test_make_pick_catalog_min_width(
    db_session_with_pick_corr,
    repicker_method_ex,
    calibration_method_ex,
):
    try:
        db_session, corr_storage, ids, _ = db_session_with_pick_corr
        repick_dict = repicker_method_ex
        cal_dict = calibration_method_ex
    finally:
        # Clean up
        corr_storage.close()
        os.remove(corr_storage.file_path)
        assert not os.path.exists(corr_storage.file_path), "the file was not removed"

    df = services.make_pick_catalog_df(
        db_session, "P", repick_dict["name"], cal_dict["name"], 90, min_width=3.0
    )

    pick = db_session.get(tables.Pick, ids["pick"])
    sta = db_session.get(tables.Station, ids["sta"])
    corr = db_session.get(tables.PickCorrection, ids["corr"])
    ci = db_session.get(tables.CredibleInterval, ids["ci"])

    assert len(df) == 1, "expected one row to be returned"
    row = df.iloc[0]
    assert row["pick_identifier"] == pick.id
    assert row["network"] == sta.net
    assert row["station"] == sta.sta
    assert row["channel"] == pick.chan_pref
    assert row["location_code"] == ""
    assert row["phase_hint"] == "P"
    # assert result[0][6] == pick.ptime
    # assert result[0][7] == corr.median
    from datetime import timezone

    assert (
        row["arrival_time"]
        == (pick.ptime + timedelta(microseconds=corr.median * 1e6))
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    assert row["uncertainty"] == 3.0


def test_get_waveform_storage_number_existing(db_session_with_waveform_info):
    try:
        db_session, wf_storage, ids = db_session_with_waveform_info

        storage_number, hdf_file, count = services.get_waveform_storage_number(
            db_session, ids["chan"], ids["wf_source"], "P", 100
        )

        assert storage_number == 0, "expected the storage_number to be 0"
        assert count == 1, "expected 1 entry in the hdf_file"
        assert (
            hdf_file
            == f"JK.TEST..HHZ.P.3C.2000samps.source{ids['wf_source']:02d}.000.h5"
        ), "incorrect hdf_file name"
    finally:
        wf_storage.close()


def test_get_waveform_storage_number_next(db_session_with_waveform_info):
    try:
        db_session, wf_storage, ids = db_session_with_waveform_info

        storage_number, hdf_file, count = services.get_waveform_storage_number(
            db_session, ids["chan"], ids["wf_source"], "P", 1
        )

        assert storage_number == 1, "expected the storage_number to be 1"
        assert count == 0, "expected 0 entry in the hdf_file"
        assert hdf_file is None, "expected hdf_file to be None"
    finally:
        wf_storage.close()


def test_get_waveform_storage_number_new(db_session_with_waveform_info):
    try:
        db_session, wf_storage, ids = db_session_with_waveform_info

        storage_number, hdf_file, count = services.get_waveform_storage_number(
            db_session, 10, ids["wf_source"], "P", 1
        )

        assert storage_number == 0, "expected the storage_number to be 0"
        assert count == 0, "expected 0 entry in the hdf_file"
        assert hdf_file is None, "expected hdf_file to be None"
    finally:
        wf_storage.close()


class TestWaveforms:
    @pytest.fixture
    def db_session_with_many_waveform_info(self, db_session, mock_pytables_config):

        ids = {}
        # Insert the stations
        sta_dict = {
            "ondate": datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            "lat": 44.7155,
            "lon": -110.67917,
            "elev": 2336,
        }
        sta1 = services.insert_station(db_session, "JK", "TST1", **sta_dict)
        sta2 = services.insert_station(db_session, "JK", "TST2", **sta_dict)
        db_session.flush()

        # Insert the channels
        chan_info = {
            "loc": "01",
            "ondate": datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            "samp_rate": 100.0,
            "clock_drift": 1e-5,
            "sensor_desc": "Nanometrics something or other",
            "sensit_units": "M/S",
            "sensit_val": 9e9,
            "sensit_freq": 5,
            "lat": 44.7155,
            "lon": -110.67917,
            "elev": 2336,
            "depth": 100,
            "azimuth": 90,
            "dip": -90,
            "offdate": None,
            "overall_gain_vel": None,
        }
        all_channel_dict = {}
        for id in [sta1.id, sta2.id]:
            for code in ["HHZ", "HHE", "HHN"]:
                chan_info["seed_code"] = code
                chan_info["sta_id"] = id
                all_channel_dict[f"{id}.{code}"] = services.insert_channel(
                    db_session, chan_info
                )

        db_session.flush()

        # Insert P Picks
        pick_cnt0 = db_session.execute(func.count(tables.Pick.id)).one()[0]
        p_dict = {
            "chan_pref": "HH",
            "phase": "P",
            "ptime": datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            "auth": "TEST",
        }
        p1 = services.insert_pick(db_session, sta1.id, **p_dict)
        p_dict["ptime"] = datetime.strptime("2010-02-02T00:00:00.00", dateformat)
        p2 = services.insert_pick(db_session, sta2.id, **p_dict)
        p_dict["ptime"] = datetime.strptime("2010-02-03T00:00:00.00", dateformat)
        p3 = services.insert_pick(db_session, sta2.id, **p_dict)

        # Insert S Picks
        s_dict = {
            "chan_pref": "HH",
            "phase": "S",
            "ptime": datetime.strptime("2010-02-01T12:00:00.00", dateformat),
            "auth": "TEST",
        }
        s1 = services.insert_pick(db_session, sta1.id, **s_dict)
        s_dict["ptime"] = datetime.strptime("2010-02-02T12:00:00.00", dateformat)
        s2 = services.insert_pick(db_session, sta1.id, **s_dict)
        s_dict["ptime"] = datetime.strptime("2010-02-03T12:00:00.00", dateformat)
        s3 = services.insert_pick(db_session, sta2.id, **s_dict)

        # Insert waveform sources
        wf_source1 = services.insert_waveform_source(
            db_session, "TEST-ExtractContData", "Extract snippets"
        )
        wf_source2 = services.insert_waveform_source(
            db_session, "TEST-DownloadSegment", "Download waveform segment from IRIS"
        )
        wf_source3 = services.insert_waveform_source(
            db_session,
            "TEST-ProcessExtracted",
            "Filter extracted waveforms",
            filt_low=1,
            filt_high=17,
        )
        db_session.flush()
        # for src in [wf_source1, wf_source2, wf_source3]:
        #     print(src.id, src.name)

        ids["p_pick1"] = p1.id
        ids["p_pick2"] = p2.id
        ids["p_pick3"] = p3.id
        ids["s_pick1"] = s1.id
        ids["s_pick2"] = s2.id
        ids["s_pick3"] = s3.id
        ids["wf_source1"] = wf_source1.id
        ids["wf_source2"] = wf_source2.id
        ids["wf_source3"] = wf_source3.id

        pick_cnt1 = db_session.execute(func.count(tables.Pick.id)).one()[0]
        assert pick_cnt1 - pick_cnt0 == 6, "Expected to insert 6 picks."

        try:
            # Open waveform storages
            wf_storages = {}
            for id in [sta1.id, sta2.id]:
                for code in ["HHZ", "HHE", "HHN"]:
                    for phase in ["P", "S"]:
                        for wf_source_id in [
                            wf_source1.id,
                            wf_source2.id,
                            wf_source3.id,
                        ]:
                            wf_storage = pytables_backend.WaveformStorage(
                                expected_array_length=100,
                                net="JK",
                                sta=str(id),
                                loc="01",
                                seed_code=code,
                                ncomps=3,
                                phase=phase,
                                wf_source_id=wf_source_id,
                            )
                            wf_storages[f"{id}.{code}.{phase}.{wf_source_id}"] = (
                                wf_storage
                            )

            ### Insert waveform infos ###

            def insert_wf_info(
                phase, pick, chan_code, wf_source, value, start_ind=None, end_ind=None
            ):
                _ = services.insert_waveform_pytable(
                    db_session,
                    wf_storages[f"{pick.sta_id}.{chan_code}.{phase}.{wf_source.id}"],
                    all_channel_dict[f"{pick.sta_id}.{chan_code}"].id,
                    pick.id,
                    wf_source.id,
                    start=pick.ptime - timedelta(seconds=0.5),
                    end=pick.ptime + timedelta(seconds=0.5),
                    data=np.full(100, value),
                    signal_start_ind=start_ind,
                    signal_end_ind=end_ind,
                )

            wfinfo_cnt0 = db_session.execute(func.count(tables.WaveformInfo.id)).one()[
                0
            ]
            # Info for P Pick 1 - a 1C P pick that is on a different station, earlier than the others, and had a different filter band
            insert_wf_info("P", p1, "HHZ", wf_source3, 1)

            # Info for P Pick 2 - a 3C P pick
            for i, code in enumerate(["HHE", "HHN", "HHZ"]):
                insert_wf_info("P", p2, code, wf_source1, 2 + i)

            # Info for P Pick 2 from a different source
            insert_wf_info("P", p2, "HHZ", wf_source2, 5)

            # Info for P Pick 3 - Same info as Pick 2 (source 1) but at a later time
            insert_wf_info("P", p3, "HHZ", wf_source1, 6)

            # Info for S Pick 1
            for i, code in enumerate(["HHE", "HHN", "HHZ"]):
                insert_wf_info("S", s1, code, wf_source2, 10 + i)

            # Info for S Pick 1 - but from a different (higher priority) source
            for i, code in enumerate(["HHE", "HHN", "HHZ"]):
                insert_wf_info("S", s1, code, wf_source1, 13 + i)

            # Info for S pick 2 - From the same source as S Pick 1 but incomplete channels
            insert_wf_info("S", s2, "HHE", wf_source1, 16)

            # Info for S pick 3 - From a different station, later than others, and has a different filter band
            for i, code in enumerate(["HHE", "HHN", "HHZ"]):
                insert_wf_info(
                    "S", s3, code, wf_source3, 17 + i, start_ind=10, end_ind=85
                )

            db_session.commit()
            wfinfo_cnt1 = db_session.execute(func.count(tables.WaveformInfo.id)).one()[
                0
            ]
            assert (
                wfinfo_cnt1 - wfinfo_cnt0 == 16
            ), "Expected to insert 16 waveform infos"
        finally:
            for _, wf_storage in wf_storages.items():
                wf_storage.commit()
                nrows = wf_storage.table.nrows
                if wf_storage._is_open:
                    wf_storage.close()
                if nrows == 0:
                    os.remove(wf_storage.file_path)

        return db_session, ids

    def test_get_sorted_waveform_info_P_freq_limits(
        self, db_session_with_many_waveform_info
    ):
        """Should return 1 rows.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "P",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            wf_filt_low=1.0,
            wf_filt_high=17.0,
        )

        assert len(wf_infos) == 1, "incorrect number of rows returned. Expected 1."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["p_pick1"]
        ), "Incorrect PID for the first waveform"

    def test_get_sorted_waveform_info_S_freq_limits(
        self, db_session_with_many_waveform_info
    ):
        """Should return 3 rows.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            wf_filt_low=1.0,
            wf_filt_high=17.0,
        )

        assert len(wf_infos) == 3, "incorrect number of rows returned. Expected 3."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"
        # Ninth wf
        assert (
            wf_infos[1][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHN"
        ), "Incorrect seed_code for the second waveform"
        # Tenth wf
        assert (
            wf_infos[2][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"

    def test_get_sorted_waveform_info_P_vertical_and_threeC_only_error(
        self, db_session_with_many_waveform_info
    ):
        """Should raise a ValueError.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info

        with pytest.raises(ValueError):
            wf_infos = services.Waveforms.get_sorted_waveform_info(
                db_session,
                "P",
                datetime.strptime("2010-01-01T00:00:00.00", dateformat),
                datetime.strptime("2011-01-01T00:00:00.00", dateformat),
                [
                    "TEST-ProcessExtracted",
                    "TEST-ExtractContData",
                    "TEST-DownloadSegment",
                ],
                threeC_only=True,
                vertical_only=True,
            )

    def test_get_sorted_waveform_info_P_threeC_only(
        self, db_session_with_many_waveform_info
    ):
        """Should return 3 rows.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "P",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            threeC_only=True,
        )

        assert len(wf_infos) == 3, "incorrect number of rows returned. Expected 3."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHN"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"

    def test_get_sorted_waveform_info_S_threeC_only(
        self, db_session_with_many_waveform_info
    ):
        """Should return 9 rows. For pick 1, the source 2 should be after source 1.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            threeC_only=True,
        )

        assert len(wf_infos) == 9, "incorrect number of rows returned. Expected 9."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHN"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"
        # Fourth wf
        assert (
            wf_infos[3][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the fourth waveform"
        assert (
            wf_infos[3][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the fourth waveform"
        assert (
            wf_infos[3][1].seed_code == "HHE"
        ), "Incorrect seed_code for the fourth waveform"
        # Fifth wf
        assert (
            wf_infos[4][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the fifth waveform"
        assert (
            wf_infos[4][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the fifth waveform"
        assert (
            wf_infos[4][1].seed_code == "HHN"
        ), "Incorrect seed_code for the fifth waveform"
        # Sixth wf
        assert (
            wf_infos[5][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the sixth waveform"
        assert (
            wf_infos[5][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the sixth waveform"
        assert (
            wf_infos[5][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the sixth waveform"
        # Seventh wf
        assert (
            wf_infos[6][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the seventh waveform"
        assert (
            wf_infos[6][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the seventh waveform"
        assert (
            wf_infos[6][1].seed_code == "HHE"
        ), "Incorrect seed_code for the seventh waveform"
        # Eigth wf
        assert (
            wf_infos[7][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the eigth waveform"
        assert (
            wf_infos[7][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the eigth waveform"
        assert (
            wf_infos[7][1].seed_code == "HHN"
        ), "Incorrect seed_code for the eigth waveform"
        # Ninth wf
        assert (
            wf_infos[8][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the ninth waveform"
        assert (
            wf_infos[8][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the ninth waveform"
        assert (
            wf_infos[8][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the ninth waveform"

    def test_get_sorted_waveform_info_P_vertical_only(
        self, db_session_with_many_waveform_info
    ):
        """Should return 4 rows. For pick 2, the source 2 should be after source 1.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "P",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            vertical_only=True,
        )

        assert len(wf_infos) == 4, "incorrect number of rows returned. Expected 4."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["p_pick1"]
        ), "Incorrect PID for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"
        # Fourth wf
        assert (
            wf_infos[3][-1].pick_id == ids["p_pick3"]
        ), "Incorrect PID for the fourth waveform"

    def test_get_sorted_waveform_info_S_vertical_only(
        self, db_session_with_many_waveform_info
    ):
        """Should return 3 rows. For pick 1, the source 2 should be after source 1.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            vertical_only=True,
        )

        assert len(wf_infos) == 3, "incorrect number of rows returned. Expected 3."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"

    def test_get_sorted_waveform_info_P_limit_sources(
        self, db_session_with_many_waveform_info
    ):
        """Should return 1 rows.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "P",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-DownloadSegment"],
        )

        assert len(wf_infos) == 1, "incorrect number of rows returned. Expected 1."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the first waveform"

    def test_get_sorted_waveform_info_S_limit_sources(
        self, db_session_with_many_waveform_info
    ):
        """Should return 3 rows.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-DownloadSegment"],
        )

        assert len(wf_infos) == 3, "incorrect number of rows returned. Expected 3."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHN"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"

    def test_get_sorted_waveform_info_P_temporal(
        self, db_session_with_many_waveform_info
    ):
        """Should return 4 rows. For pick 2, the source 2 should be after source 1.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "P",
            datetime.strptime("2010-02-02T00:00:00.00", dateformat),
            datetime.strptime("2010-02-02T23:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
        )

        assert len(wf_infos) == 4, "incorrect number of rows returned. Expected 4."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHN"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"
        # Fourth wf
        assert (
            wf_infos[3][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the fourth waveform"
        assert (
            wf_infos[3][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the fourth waveform"
        assert (
            wf_infos[3][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the fourth waveform"

    def test_get_sorted_waveform_info_S_temporal(
        self, db_session_with_many_waveform_info
    ):
        """Should return 1 rows.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-02-02T00:00:00.00", dateformat),
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
        )

        assert len(wf_infos) == 1, "incorrect number of rows returned. Expected 1."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["s_pick2"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"

    def test_get_sorted_waveform_info_P_no_filters(
        self, db_session_with_many_waveform_info
    ):
        """Should return 6 rows. For pick 2, the source 2 should be after source 1.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "P",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
        )

        assert len(wf_infos) == 6, "incorrect number of rows returned. Expected 6."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["p_pick1"]
        ), "Incorrect PID for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHE"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHN"
        ), "Incorrect seed_code for the third waveform"
        # Fourth wf
        assert (
            wf_infos[3][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the fourth waveform"
        assert (
            wf_infos[3][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the fourth waveform"
        assert (
            wf_infos[3][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the fourth waveform"
        # Fifth wf
        assert (
            wf_infos[4][-1].pick_id == ids["p_pick2"]
        ), "Incorrect PID for the fifth waveform"
        assert (
            wf_infos[4][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the fifth waveform"
        assert (
            wf_infos[4][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the fifth waveform"
        # Sixth wf
        assert (
            wf_infos[5][-1].pick_id == ids["p_pick3"]
        ), "Incorrect PID for the sixth waveform"

    def test_get_sorted_waveform_info_S_no_filters(
        self, db_session_with_many_waveform_info
    ):
        """Should return 10 rows. For pick 1, the source 2 should be after source 1.

        Args:
            db_session_with_many_waveform_info (_type_): _description_
        """
        db_session, ids = db_session_with_many_waveform_info
        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-01-01T00:00:00.00", dateformat),
            datetime.strptime("2011-01-01T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
        )

        assert len(wf_infos) == 10, "incorrect number of rows returned. Expected 10."

        # First wf
        assert (
            wf_infos[0][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the first waveform"
        assert (
            wf_infos[0][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the first waveform"
        assert (
            wf_infos[0][1].seed_code == "HHE"
        ), "Incorrect seed_code for the first waveform"
        # Second wf
        assert (
            wf_infos[1][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the second waveform"
        assert (
            wf_infos[1][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the second waveform"
        assert (
            wf_infos[1][1].seed_code == "HHN"
        ), "Incorrect seed_code for the second waveform"
        # Third wf
        assert (
            wf_infos[2][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the third waveform"
        assert (
            wf_infos[2][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the third waveform"
        assert (
            wf_infos[2][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the third waveform"
        # Fourth wf
        assert (
            wf_infos[3][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the fourth waveform"
        assert (
            wf_infos[3][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the fourth waveform"
        assert (
            wf_infos[3][1].seed_code == "HHE"
        ), "Incorrect seed_code for the fourth waveform"
        # Fifth wf
        assert (
            wf_infos[4][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the fifth waveform"
        assert (
            wf_infos[4][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the fifth waveform"
        assert (
            wf_infos[4][1].seed_code == "HHN"
        ), "Incorrect seed_code for the fifth waveform"
        # Sixth wf
        assert (
            wf_infos[5][-1].pick_id == ids["s_pick1"]
        ), "Incorrect PID for the sixth waveform"
        assert (
            wf_infos[5][-1].wf_source_id == ids["wf_source2"]
        ), "Incorrect wf_source_id for the sixth waveform"
        assert (
            wf_infos[5][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the sixth waveform"
        # Seventh wf
        assert (
            wf_infos[6][-1].pick_id == ids["s_pick2"]
        ), "Incorrect PID for the seventh waveform"
        assert (
            wf_infos[6][-1].wf_source_id == ids["wf_source1"]
        ), "Incorrect wf_source_id for the seventh waveform"
        assert (
            wf_infos[6][1].seed_code == "HHE"
        ), "Incorrect seed_code for the seventh waveform"
        # Eighth wf
        assert (
            wf_infos[7][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the eigth waveform"
        assert (
            wf_infos[7][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the eigth waveform"
        assert (
            wf_infos[7][1].seed_code == "HHE"
        ), "Incorrect seed_code for the eigth waveform"
        # Ninth wf
        assert (
            wf_infos[8][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the ninth waveform"
        assert (
            wf_infos[8][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the ninth waveform"
        assert (
            wf_infos[8][1].seed_code == "HHN"
        ), "Incorrect seed_code for the ninth waveform"
        # Tenth wf
        assert (
            wf_infos[9][-1].pick_id == ids["s_pick3"]
        ), "Incorrect PID for the tenth waveform"
        assert (
            wf_infos[9][-1].wf_source_id == ids["wf_source3"]
        ), "Incorrect wf_source_id for the tenth waveform"
        assert (
            wf_infos[9][1].seed_code == "HHZ"
        ), "Incorrect seed_code for the tenth waveform"

    def test_get_sorted_waveform_info_simple(self, db_session_with_waveform_info):
        wf_storage = None
        try:
            db_session, wf_storage, ids = db_session_with_waveform_info
            picks_and_wf_infos = services.Waveforms.get_sorted_waveform_info(
                db_session,
                "P",
                datetime.strptime("2024-01-01T00:00:00.00", dateformat),
                datetime.strptime("2024-01-10T00:00:00.00", dateformat),
                ["TEST-ExtractContData"],
            )

            assert len(picks_and_wf_infos) == 1, "expected exactly 1 row"
            assert (
                len(picks_and_wf_infos[0]) == 3
            ), "Expected 3 objects to be returned for row"
            assert (
                type(picks_and_wf_infos[0][0]) == tables.Pick
            ), "expected the first item to be a Pick"
            assert (
                type(picks_and_wf_infos[0][1]) == tables.Channel
            ), "expected the second item to be a Channel"
            assert (
                type(picks_and_wf_infos[0][2]) == tables.WaveformInfo
            ), "expected the third item to be a WaveformInfo"

        finally:
            # Clean up
            if wf_storage is not None:
                wf_storage.close()
                os.remove(wf_storage.file_path)
                assert not os.path.exists(
                    wf_storage.file_path
                ), "the file was not removed"

    def test_gather_3c_waveforms_source1(self, db_session_with_many_waveform_info):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 2
            elif seed_code == "HHE":
                return 0

            return 1

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            True,
            index_fn,
            lambda x, y: x,
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            "S",
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            False,
        )
        assert X.shape[0] == 1
        assert X.shape[1] == 60
        assert X.shape[2] == 3
        assert len(pick_source_ids) == 1
        assert pick_source_ids[0]["pick_id"] == ids["s_pick1"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source1"]
        assert np.all(X[0, :, 0] == 13)
        assert np.all(X[0, :, 1] == 14)
        assert np.all(X[0, :, 2] == 15)

    def test_gather_3c_waveforms_source2(self, db_session_with_many_waveform_info):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 2
            elif seed_code == "HHE":
                return 0

            return 1

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            True,
            index_fn,
            lambda x, y: x,
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            "S",
            ["TEST-DownloadSegment", "TEST-ProcessExtracted", "TEST-ExtractContData"],
            False,
        )
        assert X.shape[0] == 1
        assert X.shape[1] == 60
        assert X.shape[2] == 3
        assert len(pick_source_ids) == 1
        assert pick_source_ids[0]["pick_id"] == ids["s_pick1"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source2"]
        assert np.all(X[0, :, 0] == 10)
        assert np.all(X[0, :, 1] == 11)
        assert np.all(X[0, :, 2] == 12)

    def test_gather_3c_waveforms_limited_signal(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 2
            elif seed_code == "HHE":
                return 0

            return 1

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            True,
            index_fn,
            lambda x, y: x,
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            datetime.strptime("2010-02-04T00:00:00.00", dateformat),
            "S",
            ["TEST-DownloadSegment", "TEST-ProcessExtracted", "TEST-ExtractContData"],
            False,
        )
        assert X.shape[0] == 1
        assert X.shape[1] == 60
        assert X.shape[2] == 3
        assert len(pick_source_ids) == 1
        assert pick_source_ids[0]["pick_id"] == ids["s_pick3"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source3"]
        assert np.all(X[0, :, 0] == 17)
        assert np.all(X[0, :, 1] == 18)
        assert np.all(X[0, :, 2] == 19)

    def test_gather_3c_waveforms_multiple(self, db_session_with_many_waveform_info):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 2
            elif seed_code == "HHE":
                return 0

            return 1

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            True,
            index_fn,
            lambda x, y: x / 2,
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-04T00:00:00.00", dateformat),
            "S",
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            False,
        )
        assert X.shape[0] == 2
        assert X.shape[1] == 60
        assert X.shape[2] == 3
        assert len(pick_source_ids) == 2
        assert pick_source_ids[0]["pick_id"] == ids["s_pick1"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source1"]
        assert np.all(X[0, :, 0] == 13 / 2)
        assert np.all(X[0, :, 1] == 14 / 2)
        assert np.all(X[0, :, 2] == 15 / 2)
        assert pick_source_ids[1]["pick_id"] == ids["s_pick3"]
        assert pick_source_ids[1]["wf_source_id"] == ids["wf_source3"]
        assert np.all(X[1, :, 0] == 17 / 2)
        assert np.all(X[1, :, 1] == 18 / 2)
        assert np.all(X[1, :, 2] == 19 / 2)

    def test_get_pick_waveforms_3c_limited_signal(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 2
            elif seed_code == "HHE":
                return 0

            return 1

        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            datetime.strptime("2010-02-04T00:00:00.00", dateformat),
            ["TEST-ExtractContData", "TEST-ProcessExtracted", "TEST-DownloadSegment"],
            threeC_only=True,
        )

        assert len(wf_infos) == 3, "expected 3 waveform infos returned"

        X, pick_source_ids, storages = services.Waveforms().get_pick_waveforms(
            wf_infos, index_fn
        )

        try:
            assert X.shape[0] == 1
            assert X.shape[1] == 70
            assert X.shape[2] == 3
            assert pick_source_ids["pick_id"] == ids["s_pick3"]
            assert pick_source_ids["wf_source_id"] == ids["wf_source3"]
            assert np.all(X[0, :, 0] == 17)
            assert np.all(X[0, :, 1] == 18)
            assert np.all(X[0, :, 2] == 19)
        finally:
            for _, storage in storages.items():
                storage.close()

    def test_get_pick_waveforms_3c_full_signal(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 2
            elif seed_code == "HHE":
                return 0

            return 1

        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-02T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            threeC_only=True,
        )

        assert len(wf_infos) == 6, "expected 6 waveform infos returned"

        try:
            X, pick_source_ids, storages = services.Waveforms().get_pick_waveforms(
                wf_infos[0:3], index_fn
            )
            assert X.shape[0] == 1
            assert X.shape[1] == 100
            assert X.shape[2] == 3
            assert pick_source_ids["pick_id"] == ids["s_pick1"]
            assert pick_source_ids["wf_source_id"] == ids["wf_source1"]
            assert np.all(X[0, :, 0] == 13)
            assert np.all(X[0, :, 1] == 14)
            assert np.all(X[0, :, 2] == 15)
            X, pick_source_ids, storages = services.Waveforms().get_pick_waveforms(
                wf_infos[3:], index_fn, wf_storages=storages
            )
            assert X.shape[0] == 1
            assert X.shape[1] == 100
            assert X.shape[2] == 3
            assert pick_source_ids["pick_id"] == ids["s_pick1"]
            assert pick_source_ids["wf_source_id"] == ids["wf_source2"]
            assert np.all(X[0, :, 0] == 10)
            assert np.all(X[0, :, 1] == 11)
            assert np.all(X[0, :, 2] == 12)
        finally:
            for _, storage in storages.items():
                storage.close()

    def test_get_pick_waveforms_1c_limited_signal(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 0

        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            datetime.strptime("2010-02-04T00:00:00.00", dateformat),
            ["TEST-ExtractContData", "TEST-ProcessExtracted", "TEST-DownloadSegment"],
            threeC_only=True,
        )

        assert len(wf_infos) == 3, "expected 3 waveform infos returned"

        X, pick_source_ids, storages = services.Waveforms().get_pick_waveforms(
            [wf_infos[-1]], index_fn
        )

        try:
            assert X.shape[0] == 1
            assert X.shape[1] == 70
            assert X.shape[2] == 1
            assert pick_source_ids["pick_id"] == ids["s_pick3"]
            assert pick_source_ids["wf_source_id"] == ids["wf_source3"]
            assert np.all(X[0, :, 0] == 19)
        finally:
            for _, storage in storages.items():
                storage.close()

    def test_get_pick_waveforms_1c_full_signal(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if seed_code == "HHZ":
                return 0

        wf_infos = services.Waveforms.get_sorted_waveform_info(
            db_session,
            "S",
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-02T00:00:00.00", dateformat),
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            threeC_only=True,
        )

        assert len(wf_infos) == 6, "expected 6 waveform infos returned"

        storages = {}
        try:
            X, pick_source_ids, storages = services.Waveforms().get_pick_waveforms(
                [wf_infos[2]], index_fn
            )
            assert X.shape[0] == 1
            assert X.shape[1] == 100
            assert X.shape[2] == 1
            assert pick_source_ids["pick_id"] == ids["s_pick1"]
            assert pick_source_ids["wf_source_id"] == ids["wf_source1"]
            assert np.all(X[0, :, 0] == 15)
            X, pick_source_ids, storages = services.Waveforms().get_pick_waveforms(
                [wf_infos[-1]], index_fn, wf_storages=storages
            )
            assert X.shape[0] == 1
            assert X.shape[1] == 100
            assert X.shape[2] == 1
            assert pick_source_ids["pick_id"] == ids["s_pick1"]
            assert pick_source_ids["wf_source_id"] == ids["wf_source2"]
            assert np.all(X[0, :, 0] == 12)
        finally:
            for _, storage in storages.items():
                storage.close()

    def test_gather_vertical_waveforms_source1(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if ncomps == 1 and seed_code == "HHZ":
                return 0

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            False,
            index_fn,
            lambda x, y: x,
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            "S",
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            False,
        )
        assert X.shape[0] == 1
        assert X.shape[1] == 60
        assert X.shape[2] == 1
        assert len(pick_source_ids) == 1
        assert pick_source_ids[0]["pick_id"] == ids["s_pick1"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source1"]
        assert np.all(X[0, :, 0] == 15)

    def test_gather_vertical_waveforms_source2(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if ncomps == 1 and seed_code == "HHZ":
                return 0

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            False,
            index_fn,
            lambda x, y: x,
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            "S",
            ["TEST-DownloadSegment", "TEST-ProcessExtracted", "TEST-ExtractContData"],
            False,
        )
        assert X.shape[0] == 1
        assert X.shape[1] == 60
        assert X.shape[2] == 1
        assert len(pick_source_ids) == 1
        assert pick_source_ids[0]["pick_id"] == ids["s_pick1"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source2"]
        assert np.all(X[0, :, 0] == 12)

    def test_gather_vertical_waveforms_limited_signal(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if ncomps == 1 and seed_code == "HHZ":
                return 0

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            False,
            index_fn,
            lambda x, y: x,
            datetime.strptime("2010-02-03T00:00:00.00", dateformat),
            datetime.strptime("2010-02-04T00:00:00.00", dateformat),
            "S",
            ["TEST-DownloadSegment", "TEST-ProcessExtracted", "TEST-ExtractContData"],
            False,
        )
        assert X.shape[0] == 1
        assert X.shape[1] == 60
        assert X.shape[2] == 1
        assert len(pick_source_ids) == 1
        assert pick_source_ids[0]["pick_id"] == ids["s_pick3"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source3"]
        assert np.all(X[0, :, 0] == 19)

    def test_gather_vertical_waveforms_multiple(
        self, db_session_with_many_waveform_info
    ):
        db_session, ids = db_session_with_many_waveform_info

        def index_fn(ncomps, seed_code):
            if ncomps == 1 and seed_code == "HHZ":
                return 0

        pick_source_ids, X = services.Waveforms().gather_waveforms(
            db_session,
            60,
            False,
            index_fn,
            lambda x, y: x / 2,
            datetime.strptime("2010-02-01T00:00:00.00", dateformat),
            datetime.strptime("2010-02-04T00:00:00.00", dateformat),
            "S",
            ["TEST-ProcessExtracted", "TEST-ExtractContData", "TEST-DownloadSegment"],
            False,
        )
        assert X.shape[0] == 2
        assert X.shape[1] == 60
        assert X.shape[2] == 1
        assert len(pick_source_ids) == 2
        assert pick_source_ids[0]["pick_id"] == ids["s_pick1"]
        assert pick_source_ids[0]["wf_source_id"] == ids["wf_source1"]
        assert np.all(X[0, :, 0] == 15 / 2)
        assert pick_source_ids[1]["pick_id"] == ids["s_pick3"]
        assert pick_source_ids[1]["wf_source_id"] == ids["wf_source3"]
        assert np.all(X[1, :, 0] == 19 / 2)
