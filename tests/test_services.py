from datetime import datetime
import pytest
from copy import deepcopy
from sqlalchemy import func
import numpy as np

from seis_proc_db import services, tables

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
            "org_npts": 86399,
            "org_start": datetime.strptime("2024-10-01T00:00:00.05", dateformat),
            "org_end": datetime.strptime("2024-10-01T23:59:59.55", dateformat),
        }
    )


@pytest.fixture
def detection_method_ex():
    return deepcopy(
        {
            "name": "TEST-UNET-v1",
            "phase": "P",
            "desc": "For P picks, from Armstrong 2023 BSSA paper",
            "path": "the/model/files/are/stored/here",
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
            "start": datetime.strptime("2023-01-02T12:13:14.15", dateformat),
            "end": datetime.strptime("2023-01-02T12:13:14.25", dateformat),
            "startsamp": 4399415,
            "endsamp": 4399425,
        }
    )


@pytest.fixture
def waveform_ex():
    return deepcopy(
        {
            "filt_low": 1.5,
            "filt_high": 17.5,
            "start": datetime.strptime("2024-01-02T10:11:02.13", dateformat),
            "end": datetime.strptime("2024-01-02T10:11:22.14", dateformat),
            "proc_notes": "Processed for repicker",
            "data": np.zeros((2000)).tolist(),
        }
    )


@pytest.fixture
def db_session_with_station(db_session, stat_ex):
    inserted_stat = services.insert_station(db_session, **stat_ex)
    db_session.commit()

    return db_session, inserted_stat.id


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


def test_insert_channels(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

    common_chan_dict = channel_ex
    common_chan_dict["sta_id"] = sid

    cnt0 = db_session.execute(func.count(tables.Channel.id)).one()[0]

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

    cnt1 = db_session.execute(func.count(tables.Channel.id)).one()[0]
    assert cnt1 - cnt0 == 3


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


def test_get_all_station_channels(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

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
    db_session.expunge_all()

    chan_list = services.get_all_station_channels(db_session, sid)

    assert len(chan_list) == 3, "Incorrect number of Channels"


def test_get_operating_channels_by_station_name(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

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
    db_session.expunge_all()

    station = db_session.get(tables.Station, sid)

    print("STA", station.sta)
    station, channels = services.get_operating_channels_by_station_name(
        db_session,
        station.sta,
        "HH",
        datetime.strptime("2005-10-26T00:00:00.00", dateformat),
    )
    print(station)
    print(channels)
    assert len(channels) == 3


def test_get_common_station_channels(db_session_with_station, channel_ex):
    db_session, sid = db_session_with_station

    common_chan_dict = channel_ex
    common_chan_dict["sta_id"] = sid
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
    db_session.expunge_all()

    chan_list = services.get_common_station_channels(db_session, sid, "HH")
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
    assert db_session.get(tables.DailyContDataInfo, dataid).chan_pref == "HH"


def test_insert_detection_method(db_session, detection_method_ex):
    d = detection_method_ex
    inserted_det_meth = services.insert_detection_method(
        db_session, name=d["name"], phase=d["phase"], desc=d["desc"], path=d["path"]
    )
    db_session.commit()
    assert inserted_det_meth.name == "TEST-UNET-v1", "incorrect name"
    assert inserted_det_meth.phase == "P", "incorrect phase"


def test_get_detection_method(db_session, detection_method_ex):
    d = detection_method_ex
    inserted_det_meth = services.insert_detection_method(
        db_session, name=d["name"], phase=d["phase"], desc=d["desc"], path=d["path"]
    )
    db_session.commit()
    db_session.expunge_all()

    selected_method = services.get_detection_method(db_session, d["name"])
    assert selected_method.name == "TEST-UNET-v1", "incorrect name"


def test_get_detection_method_none(db_session, detection_method_ex):
    d = detection_method_ex
    selected_method = services.get_detection_method(db_session, d["name"])
    assert selected_method is None, "method is not None"


def test_upsert_detection_method(db_session, detection_method_ex):
    d = detection_method_ex
    inserted_det_meth = services.insert_detection_method(
        db_session, name=d["name"], phase=d["phase"], desc=d["desc"], path=d["path"]
    )
    db_session.commit()
    method_id = inserted_det_meth.id
    db_session.expunge_all()
    d["phase"] = "S"
    d["path"] = "new/path"
    print("dict", d)
    services.upsert_detection_method(db_session, **d)
    db_session.commit()
    updated_meth = db_session.get(tables.DetectionMethod, method_id)

    assert updated_meth.phase == "S", f"phase not updated"
    assert updated_meth.path == "new/path", "path not updated"


@pytest.fixture
def db_session_with_dldetection(db_session_with_contdatainfo, detection_method_ex):
    db_session, sid, dataid = db_session_with_contdatainfo
    inserted_method = services.insert_detection_method(
        db_session, **detection_method_ex
    )
    db_session.commit()

    d = {"sample": 1000, "phase": "P", "width": 40, "height": 90}
    inserted_dldet = services.insert_dldetection(
        db_session, dataid, inserted_method.id, **d
    )
    db_session.commit()

    ids = {
        "sta": sid,
        "data": dataid,
        "method": inserted_method.id,
        "dldet": inserted_dldet.id,
    }

    return db_session, ids


def test_insert_dldetection(db_session_with_dldetection):
    db_session, ids = db_session_with_dldetection

    inserted_dldet = db_session.get(tables.DLDetection, ids["dldet"])

    assert inserted_dldet.id > 0, "No id"
    assert inserted_dldet.phase == "P"
    assert inserted_dldet.sample == 1000


@pytest.fixture
def db_session_with_dldet_pick(db_session_with_dldetection, pick_ex, channel_ex):
    db_session, ids = db_session_with_dldetection
    chan_dict = channel_ex
    chan_dict["sta_id"] = ids["sta"]
    chan = services.insert_channel(db_session, chan_dict)
    db_session.commit()
    ids["chan"] = chan.id

    inserted_pick = services.insert_pick(
        db_session, sta_id=ids["sta"], detid=ids["dldet"], **pick_ex
    )
    db_session.commit()

    ids["pick"] = inserted_pick.id

    return db_session, ids


def test_insert_pick(db_session_with_dldet_pick):
    db_session, ids = db_session_with_dldet_pick
    inserted_pick = db_session.get(tables.Pick, ids["pick"])
    assert inserted_pick.id is not None
    assert inserted_pick.detid == ids["dldet"]
    assert inserted_pick.phase == "P"


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


def test_insert_waveform(db_session_with_dldet_pick, waveform_ex):
    db_session, ids = db_session_with_dldet_pick

    new_wf = services.insert_waveform(
        db_session,
        data_id=ids["data"],
        chan_id=ids["chan"],
        pick_id=ids["pick"],
        **waveform_ex,
    )

    db_session.commit()

    assert new_wf.id is not None, "ID is not set"
    assert len(new_wf.data) == 2000, "data length is invalid"
    assert new_wf.filt_low == 1.5, "filt_low is invalid"
