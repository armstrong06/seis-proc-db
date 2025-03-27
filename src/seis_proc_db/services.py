"""Store business logic"""

from sqlalchemy import select, text, insert

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

def get_channel(session, sta_id, seed_code):
    pass

def get_station_channels(session, sta_id):
    pass

def insert_contdatainfo(session, sid):
    pass

def get_contdatainfo(session):
    pass

def insert_dldetection(session):
    pass


def insert_pick(session):
    pass


def insert_detection_method(session):
    pass


def insert_gap(session):
    pass


def insert_waveform(session):
    pass
