from datetime import datetime
import pytest
from copy import deepcopy
from sqlalchemy import func

from seis_proc_db import services, tables

dateformat = "%Y-%m-%dT%H:%M:%S.%f"


def test_insert_station(db_session):
    d = {
        "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
        "net": "WY",
        "sta": "YNR",
        "lat": 44.7155,
        "lon": -110.67917,
        "elev": 2336,
    }

    inserted_stat = services.insert_station(db_session, **d)
    db_session.commit()
    assert db_session.get(tables.Station, inserted_stat.id).sta == "YNR"

@pytest.fixture
def db_session_with_station(db_session):
    d = {
        "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
        "net": "WY",
        "sta": "YNR",
        "lat": 44.7155,
        "lon": -110.67917,
        "elev": 2336,
    }

    inserted_stat = services.insert_station(db_session, **d)
    db_session.commit()

    return db_session, inserted_stat.id

def test_get_station(db_session_with_station):
    db_session, sid = db_session_with_station

    # Just in case it would grab the stored object from the Session
    db_session.expunge_all()

    selected_stat = services.get_station(db_session, "WY", "YNR", datetime.strptime("1993-10-26T00:00:00.00", dateformat))
    assert selected_stat is not None, "station was not found"
    assert (
        selected_stat.lat == 44.7155
        and selected_stat.lon == -110.67917
        and selected_stat.elev == 2336
    ), "selected station location is incorrect"


def test_station_no_results(db_session):
    ondate = datetime.strptime("1993-10-26T00:00:00.00", dateformat)

    selected_stat = services.get_station(db_session, "WY", "YNR", ondate)
    assert selected_stat is None, "get_station did not return None"

def test_insert_channels(db_session_with_station):
    db_session, sid = db_session_with_station

    common_chan_dict = {
        "sta_id": sid,
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
    }

    c1, c2, c3 = deepcopy(common_chan_dict), deepcopy(common_chan_dict), deepcopy(common_chan_dict)

    c1["seed_code"] = "HHE"
    c2["seed_code"] = "HHN"
    c3["seed_code"] = "HHZ"

    services.insert_channels(db_session, [c1, c2, c3])

    db_session.commit()

    cnt = db_session.execute(func.count(tables.Channel.id)).one()
    assert cnt[0] == 3

def test_insert_channel(db_session_with_station):
    db_session, sid = db_session_with_station

    chan_dict = {
        "sta_id": sid,
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
    }

    inserted_chan = services.insert_channel(db_session, chan_dict)
    db_session.commit()

    assert db_session.get(tables.Channel, inserted_chan.id).seed_code == "HHZ"