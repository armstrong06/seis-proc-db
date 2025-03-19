"""Simple tests to make sure there were no major issues when generating the schema"""

from datetime import datetime
from sqlalchemy import select
import pytest 

from app import tables

dateformat = "%Y-%m-%dT%H:%M:%S.%f"

def test_station(db_session):
    ondate = datetime.strptime("1993-10-26T00:00:00.00", dateformat)
    net = "WY"
    sta = "YNR"
    lat = 44.7155
    lon = -110.67917
    elev = 2336
    istat = tables.Station(net=net, sta=sta, ondate=ondate, lat=lat, lon=lon, elev=elev)
    db_session.add(istat)
    db_session.commit()
    #rstat = db_session.scalars(select(tables.Station)).first()#
    # Use this approach incase there are existing entries in the DB
    rstat = db_session.get(tables.Station, istat.id)
    assert rstat.ondate.year == ondate.year, "invalid ondate year"
    assert rstat.ondate.month == ondate.month, "invalid ondate month"
    assert rstat.ondate.day == ondate.day, "invalid ondate day"
    assert rstat.net == net, "invalid net"
    assert rstat.sta == sta, "invalid sta"
    assert abs(rstat.lat - lat) < 1e-5, "invalud lat"
    assert abs(rstat.lon - lon) < 1e-5, "invalid lon"
    assert abs(rstat.elev - elev) < 1e-1, "invalud elev"
    assert rstat.offdate is None, "invalid offdate"
    assert rstat.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert rstat.last_modified.month == datetime.now().month, "invalid last_modified year"
    assert rstat.last_modified.day == datetime.now().day, "invalid last_modified year"

def test_station_offdate(db_session):
    ondate = datetime.strptime("1993-10-26T00:00:00.0", dateformat)
    offdate = datetime.strptime("2023-08-25T00:00:00.0", dateformat)
    net = "WY"
    sta = "YNR"
    lat = 44.7155
    lon = -110.67917
    elev = 2336
    istat = tables.Station(net=net, sta=sta, ondate=ondate, lat=lat, lon=lon, elev=elev, offdate=offdate)
    db_session.add(istat)
    db_session.commit()
    #rstat = db_session.scalars(select(tables.Station)).first()#
    # Use this approach incase there are existing entries in the DB
    rstat = db_session.get(tables.Station, istat.id)
    assert rstat.offdate.year == offdate.year, "invalid offdate year"
    assert rstat.offdate.month == offdate.month, "invalid offdate month"
    assert rstat.offdate.day == offdate.day, "invalid offdate day"

@pytest.fixture
def db_session_with_stat(db_session):
    ondate = datetime.strptime("1993-10-26T12:10:10.1010", dateformat)
    net = "WY"
    sta = "YNR"
    lat = 44.7155
    lon = -110.67917
    elev = 2336
    istat = tables.Station(net=net, sta=sta, ondate=ondate, lat=lat, lon=lon, elev=elev)
    db_session.add(istat)
    db_session.commit()
    return db_session, istat

def test_channel(db_session_with_stat):
    # Make a station to associate with the channel
    db_session, istat = db_session_with_stat
    assert istat.id is not None
    assert len(istat.channels) == 0, "stat.channels before adding"

    seed_code = "HHE"
    loc = "01"
    ondate = istat.ondate
    samp_rate = 100.0
    clock_drift = 1E-5
    sensor_name = "Nanometrics something or other"
    sensitivity_units = "M/S"
    sensitivity_val = 9E9
    lat = istat.lat
    lon = istat.lon
    elev = istat.elev
    depth = 100
    azimuth = 90
    dip = -90

    ichan = tables.Channel(sta_id=istat.id, seed_code=seed_code,
                           loc=loc, ondate=ondate, samp_rate=samp_rate,
                           clock_drift=clock_drift, sensor_name=sensor_name,
                           sensitivity_units=sensitivity_units, 
                           sensitivity_val=sensitivity_val,
                           depth=depth, azimuth=azimuth, dip=dip,
                           lat=lat, lon=lon, elev=elev)
    
    db_session.add(ichan)
    db_session.commit()
    rchan = db_session.get(tables.Channel, ichan.id)
    assert len(istat.channels) == 1, "stat.channels after"
    assert rchan.sta_id == istat.id, "channe.sta_id error"
