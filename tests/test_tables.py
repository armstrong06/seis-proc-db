from datetime import datetime
from app import tables

dateformat = "%Y-%m-%dT%H:%M:%S.%f"

def test_station(db_session):
    ondate = datetime.strptime("1993-10-26T00:00:00.0000", dateformat)
    stat = tables.Station(net="WY", sta="YNR", ondate=ondate, lat=44.7155, lon=-110.67917, elev=2336)
    db_session.add(stat)
    db_session.commit()

if __name__ == "__main__":
    from conftest import db_session
    test_station(db_session)