from datetime import datetime

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

    inserted_stat = services.insert_station(db_session, d)
    db_session.commit()
    assert db_session.get(tables.Station, inserted_stat.id).sta == "YNR"


def test_get_station(db_session):
    ondate = datetime.strptime("1993-10-26T00:00:00.00", dateformat)

    d = {
        "ondate": ondate,
        "net": "WY",
        "sta": "YNR",
        "lat": 44.7155,
        "lon": -110.67917,
        "elev": 2336,
    }

    _ = services.insert_station(db_session, d)
    db_session.commit()
    # Just in case it would grab the stored object from the Session
    db_session.expunge_all()

    selected_stat = services.get_station(db_session, "WY", "YNR", ondate)
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
