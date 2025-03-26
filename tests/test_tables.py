"""Simple tests to make sure there were no major issues when generating the schema"""

from datetime import datetime
from sqlalchemy import select
import pytest
import numpy as np

from seis_proc_db import tables

dateformat = "%Y-%m-%dT%H:%M:%S.%f"


def test_station(db_session):
    d = {
        "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
        "net": "WY",
        "sta": "YNR",
        "lat": 44.7155,
        "lon": -110.67917,
        "elev": 2336,
    }
    istat = tables.Station(**d)
    db_session.add(istat)
    db_session.commit()
    # rstat = db_session.scalars(select(tables.Station)).first()#
    # Use this approach incase there are existing entries in the DB
    rstat = db_session.get(tables.Station, istat.id)
    assert rstat.ondate.year == d["ondate"].year, "invalid ondate year"
    assert rstat.ondate.month == d["ondate"].month, "invalid ondate month"
    assert rstat.ondate.day == d["ondate"].day, "invalid ondate day"
    assert rstat.ondate.microsecond == 0, "ondate is storing microsecond"
    assert rstat.net == d["net"], "invalid net"
    assert rstat.sta == d["sta"], "invalid sta"
    assert abs(rstat.lat - d["lat"]) < 1e-5, "invalud lat"
    assert abs(rstat.lon - d["lon"]) < 1e-5, "invalid lon"
    assert abs(rstat.elev - d["elev"]) < 1e-1, "invalud elev"
    assert rstat.offdate is None, "invalid offdate"
    assert rstat.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        rstat.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert rstat.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        rstat.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_station_offdate(db_session):
    d = {
        "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
        "offdate": datetime.strptime("2023-08-25T00:00:00.0", dateformat),
        "net": "WY",
        "sta": "YNR",
        "lat": 44.7155,
        "lon": -110.67917,
        "elev": 2336,
    }
    istat = tables.Station(**d)
    db_session.add(istat)
    db_session.commit()
    # rstat = db_session.scalars(select(tables.Station)).first()#
    # Use this approach incase there are existing entries in the DB
    rstat = db_session.get(tables.Station, istat.id)
    assert rstat.offdate.year == d["offdate"].year, "invalid offdate year"
    assert rstat.offdate.month == d["offdate"].month, "invalid offdate month"
    assert rstat.offdate.day == d["offdate"].day, "invalid offdate day"
    assert rstat.offdate.microsecond == 0, "offdate does include microseconds"


@pytest.fixture
def db_session_with_stat(db_session):
    d = {
        "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
        "net": "WY",
        "sta": "YNR",
        "lat": 44.7155,
        "lon": -110.67917,
        "elev": 2336,
    }

    istat = tables.Station(**d)
    db_session.add(istat)
    db_session.commit()
    return db_session, istat


def test_channel(db_session_with_stat):
    # Make a station to associate with the channel
    db_session, istat = db_session_with_stat
    assert istat.id is not None
    assert len(istat.channels) == 0, "stat.channels before adding"

    d = {
        "seed_code": "HHE",
        "loc": "01",
        "ondate": istat.ondate,
        "samp_rate": 100.0,
        "clock_drift": 1e-5,
        "sensor_desc": "Nanometrics something or other",
        "sensit_units": "M/S",
        "sensit_val": 9e9,
        "sensit_freq": 5,
        "lat": istat.lat,
        "lon": istat.lon,
        "elev": istat.elev,
        "depth": 100,
        "azimuth": 90,
        "dip": -90,
    }

    ichan = tables.Channel(sta_id=istat.id, **d)

    db_session.add(ichan)
    db_session.commit()
    rchan = db_session.get(tables.Channel, ichan.id)
    assert len(istat.channels) == 1, "stat.channels after"
    assert rchan.sta_id == istat.id, "channe.sta_id error"
    assert rchan.sensit_val == d["sensit_val"]
    assert rchan.dip == d["dip"]
    assert rchan.clock_drift == d["clock_drift"]
    assert rchan.ondate.microsecond == 0, "ondate does include microseconds"


def test_dailycontdatainfo(db_session_with_stat):
    # Make a station to associate with the contdata
    db_session, istat = db_session_with_stat
    assert istat.id is not None
    assert len(istat.contdatainfo) == 0, "stat.contdatainfo before adding"

    d = {
        "chan_pref": "HH",
        "ncomps": 3,
        "date": datetime(year=2024, month=10, day=1),
        "samp_rate": 100.0,
        "dt": 0.01,
        "org_npts": 86399,
        "org_start": datetime.strptime("2024-10-01T00:00:00.05", dateformat),
        "org_end": datetime.strptime("2024-10-01T23:59:59.55", dateformat),
        "proc_start": datetime.strptime("2024-10-01T00:00:00.01", dateformat),
        "proc_end": datetime.strptime("2024-10-01T23:59:59.59", dateformat),
    }

    icd = tables.DailyContDataInfo(sta_id=istat.id, **d)
    db_session.add(icd)
    db_session.commit()

    rcd = db_session.get(tables.DailyContDataInfo, icd.id)
    # # rcd is being retrieved from the IdentidyMap, which only stores a unique instance
    # # of a Python object per database identity and within a session scope.
    assert rcd == icd, "rcd and icd are not actually the same"
    assert rcd.date.day == 1, "day incorrect for Date obj"
    assert rcd.org_start.microsecond == 50000, "org_start microseconds incorrect"
    assert rcd.org_end.microsecond == 550000, "org_end microseconds incorrect"
    assert rcd.proc_start.microsecond == 10000, "proc_start microseconds incorrect"
    assert rcd.proc_end.microsecond == 590000, "proc_end microseconds incorrect"
    assert rcd.dt == 0.01
    assert rcd.samp_rate == 100.0
    assert rcd.chan_pref == "HH"
    assert rcd.org_npts == 86399
    assert rcd.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert rcd.last_modified.month == datetime.now().month, "invalid last_modified year"
    assert rcd.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        rcd.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_repicker_method(db_session):
    d = {
        "name": "MSWAG-v1.0",
        "phase": "S",
        "desc": "MultiSWAG models trained on 01/01/01 using M1 epoch 1, M2 epoch 2, M3 epoch 3",
        "path": "the/model/files/are/stored/here",
    }

    irpm = tables.RepickerMethod(**d)
    db_session.add(irpm)
    db_session.commit()

    assert irpm.phase == "S", "invalid phase"
    assert len(irpm.corrs) == 0, "The length of related PickCorrections is not 0"
    assert irpm.id is not None, "ID is not defined"
    assert len(irpm.name) > 0, "name is not defined"
    assert irpm.desc is not None, "desc is not defined"
    assert irpm.path is not None, "path is not defined"
    assert irpm.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        irpm.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert irpm.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        irpm.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_calibration_method(db_session):
    d = {
        "name": "kolosov-m1",
        "phase": "P",
        "desc": "Calibration model using all data and Repicker Method 1",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.CalibrationMethod(**d)
    db_session.add(imeth)
    db_session.commit()

    assert imeth.phase == "P", "invalid phase"
    assert len(imeth.cis) == 0, "The length of related CredibleInterval is not 0"
    assert imeth.id is not None, "ID is not defined"
    assert len(imeth.name) > 0, "name is not defined"
    assert imeth.desc is not None, "desc is not defined"
    assert imeth.path is not None, "path is not defined"
    assert imeth.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        imeth.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert imeth.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        imeth.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_fm_method(db_session):
    d = {
        "name": "MSWAG-v1.0",
        "desc": "MWAG models trained with data from 2012 - 2024",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.FMMethod(**d)
    db_session.add(imeth)
    db_session.commit()

    assert len(imeth.fms) == 0, "The length of related FMs is not 0"
    assert imeth.id is not None, "ID is not defined"
    assert len(imeth.name) > 0, "name is not defined"
    assert imeth.desc is not None, "desc is not defined"
    assert imeth.path is not None, "path is not defined"
    assert imeth.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        imeth.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert imeth.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        imeth.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_detection_method(db_session):
    d = {
        "name": "P-UNET-v1",
        "phase": "P",
        "desc": "For P picks, from Armstrong 2023 BSSA paper",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.DetectionMethod(**d)
    db_session.add(imeth)
    db_session.commit()

    assert imeth.phase == "P", "invalid phase"
    assert len(imeth.dldets) == 0, "The length of related DLDetections is not 0"
    assert imeth.id is not None, "ID is not defined"
    assert len(imeth.name) > 0, "name is not defined"
    assert imeth.desc is not None, "desc is not defined"
    assert imeth.path is not None, "path is not defined"
    assert imeth.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        imeth.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert imeth.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        imeth.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


@pytest.fixture
def db_session_with_contdata(db_session_with_stat):
    # Make a station to associate with the channel
    db_session, istat = db_session_with_stat
    assert istat.id is not None

    d = {
        "chan_pref": "HH",
        "ncomps": 3,
        "date": datetime(year=2024, month=10, day=1),
        "samp_rate": 100.0,
        "dt": 0.01,
        "org_npts": 86399,
        "org_start": datetime.strptime("2024-10-01T00:00:00.05", dateformat),
        "org_end": datetime.strptime("2024-10-01T23:59:59.55", dateformat),
        "proc_start": datetime.strptime("2024-10-01T00:00:00.01", dateformat),
        "proc_end": datetime.strptime("2024-10-01T23:59:59.59", dateformat),
    }

    icd = tables.DailyContDataInfo(sta_id=istat.id, **d)
    db_session.add(icd)
    db_session.commit()

    assert len(istat.contdatainfo) == 1, "contdatainfo not associated with station"
    assert icd.station is not None, "station not associated with contdatainfo"

    return db_session, icd


def test_dldetection(db_session_with_contdata):
    db_session, icd = db_session_with_contdata
    assert len(icd.dldets) == 0, "contdateinfo.dldets before adding det"

    # Add detection method #
    d = {
        "name": "P-UNET-v1",
        "phase": "P",
        "desc": "For P picks, from Armstrong 2023 BSSA paper",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.DetectionMethod(**d)
    db_session.add(imeth)
    db_session.commit()
    assert len(imeth.dldets) == 0, "detection_method.dldets before adding det"
    #

    d = {"sample": 1000, "phase": "P", "width": 40, "height": 90}

    idet = tables.DLDetection(data_id=icd.id, method_id=imeth.id, **d)
    db_session.add(idet)
    db_session.commit()

    assert len(icd.dldets) == 1, "DLDetection not assocaited with ContDataInfo"
    assert len(imeth.dldets) == 1, "DLDetection not assocaited with DetectionMethod"
    assert idet.contdatainfo is not None, "ContDataInfo not associated with DLDetection"
    assert idet.method is not None, "DetectionMethod not associated with DLDetection"
    assert idet.sample == 1000
    assert idet.phase == "P"
    assert idet.width == 40
    assert idet.height == 90
    assert idet.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        idet.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert idet.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        idet.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_pick(db_session_with_stat):
    db_session, istat = db_session_with_stat
    assert istat.id is not None
    assert len(istat.picks) == 0, "stat.pick before adding"

    d = {
        "chan_pref": "HH",
        "phase": "P",
        "ptime": datetime.strptime("2024-01-02T10:11:12.13", dateformat),
        "auth": "SPDL",
        "snr": 40.5,
        "amp": 10.22,
    }

    ipick = tables.Pick(sta_id=istat.id, **d)
    db_session.add(ipick)
    db_session.commit()

    assert ipick.chan_pref == "HH", "invalid chan_pref"
    assert ipick.ptime.day == 2, "invalid day"
    assert ipick.ptime.month == 1, "invalid month"
    assert ipick.ptime.year == 2024, "invalid year"
    assert ipick.ptime.hour == 10, "invalid hour"
    assert ipick.ptime.minute == 11, "invalid min"
    assert ipick.ptime.second == 12, "invalid sec"
    assert ipick.ptime.microsecond == 130000, "invalid microsecond"
    assert ipick.auth == "SPDL", "invalid auth"
    assert ipick.snr == 40.5, "invalid snr"
    assert ipick.amp == 10.22, "invalid amp"

    assert len(istat.picks) == 1, "stat.pick after adding"
    assert ipick.dldet is None, "dldet should not be defined"
    assert len(ipick.corrs) == 0, "should be 0 corrs assigned to the pick"
    assert len(ipick.wfs) == 0, "should be 0 wfs assigned to the pick"
    assert len(ipick.fms) == 0, "should be 0 fms assigned to the pick"
    assert ipick.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        ipick.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert ipick.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        ipick.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


@pytest.fixture
def db_session_with_pick(db_session_with_stat):
    # Make a station to associate with the channel
    db_session, istat = db_session_with_stat
    assert istat.id is not None

    d = {
        "chan_pref": "HH",
        "phase": "P",
        "ptime": datetime.strptime("2024-01-02T10:11:12.13", dateformat),
        "auth": "SPDL",
        "snr": 40.5,
        "amp": 10.22,
    }

    ipick = tables.Pick(sta_id=istat.id, **d)
    db_session.add(ipick)
    db_session.commit()

    assert len(istat.picks) == 1, "picks not associated with station"
    assert ipick.station is not None, "station not associated with pick"

    return db_session, ipick


def test_pick_correction(db_session_with_pick):
    db_session, ipick = db_session_with_pick
    assert len(ipick.corrs) == 0, "Pick.corrs should have 0 values before making"

    # Add repicker method #
    d = {
        "name": "SWAG-v1",
        "phase": "P",
        "desc": "For P picks, from Armstrong 2023 BSSA paper",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.RepickerMethod(**d)
    db_session.add(imeth)
    db_session.commit()
    assert len(imeth.corrs) == 0, "repicker_method.corrs before adding corr"
    #

    d = {
        "median": 1.1,
        "mean": 1.2,
        "std": 1.1,
        "if_low": 0.1,
        "if_high": 2.2,
        "trim_mean": 1.01,
        "trim_median": 1.02,
        "preds": np.zeros((300)).tolist(),
    }

    icorr = tables.PickCorrection(pid=ipick.id, method_id=imeth.id, **d)
    db_session.add(icorr)
    db_session.commit()

    assert len(ipick.corrs) == 1, "Pick.corrs should have 1 value"
    assert len(imeth.corrs) == 1, "RepickerMethod.corrs should have 1 value"
    assert icorr.pick is not None, "PickCorrection.pick should not be None"
    assert icorr.method is not None, "PickCorrection.method should not be None"
    assert len(icorr.cis) == 0, "PickCorrection.cis should have no values"
    assert icorr.trim_mean == 1.01, "invalud trim_mean"
    assert np.array_equal(icorr.preds, np.zeros((300))), "Invalid preds"
    assert icorr.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        icorr.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert icorr.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        icorr.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


def test_firstmotion(db_session_with_pick):
    db_session, ipick = db_session_with_pick
    assert len(ipick.fms) == 0, "Pick.fms should have 0 values before adding"

    # Add fm method #
    d = {
        "name": "MSWAG-v1.0",
        "desc": "MWAG models trained with data from 2012 - 2024",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.FMMethod(**d)
    db_session.add(imeth)
    db_session.commit()
    assert len(imeth.fms) == 0, "fm_method.fms before adding det"
    #

    d = {
        "clsf": "dn",
        "prob_up": 9.5,
        "prob_dn": 90.5,
        "preds": np.zeros((300)).tolist(),
    }

    ifm = tables.FirstMotion(pid=ipick.id, method_id=imeth.id, **d)
    db_session.add(ifm)
    db_session.commit()

    assert len(ipick.fms) == 1, "Pick.fms should have 1 value"
    assert len(imeth.fms) == 1, "fm_method.fms should have 1 value"
    assert ifm.pick is not None, "fm.pick should exist"
    assert ifm.method is not None, "fm.method should exist"
    assert np.array_equal(ifm.preds, np.zeros((300))), "Invalid preds"
    assert ifm.clsf == "dn", f"fm.clsf wrong as {ifm.clsf}"
    assert ifm.prob_up == 9.5, "fm.prob_up is wrong"
    assert ifm.prob_dn == 90.5, "fm.prob_up is wrong"
    assert ifm.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert ifm.last_modified.month == datetime.now().month, "invalid last_modified year"
    assert ifm.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        ifm.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


@pytest.fixture
def db_session_with_corr(db_session_with_pick):
    # Make a station to associate with the channel
    db_session, ipick = db_session_with_pick
    assert ipick.id is not None

    # Add repicker method #
    d = {
        "name": "SWAG-v1",
        "phase": "P",
        "desc": "For P picks, from Armstrong 2023 BSSA paper",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.RepickerMethod(**d)
    db_session.add(imeth)
    db_session.commit()
    assert len(imeth.corrs) == 0, "repicker_method.corrs before adding corr"
    #

    d = {
        "median": 1.1,
        "mean": 1.2,
        "std": 1.1,
        "if_low": 0.1,
        "if_high": 2.2,
        "trim_mean": 1.01,
        "trim_median": 1.02,
        "preds": np.zeros((300)).tolist(),
    }

    icorr = tables.PickCorrection(pid=ipick.id, method_id=imeth.id, **d)
    db_session.add(icorr)
    db_session.commit()

    assert len(ipick.corrs) == 1, "corrs not associated with pick"
    assert icorr.pick is not None, "pick not associated with corr"
    assert len(imeth.corrs) == 1, "repicker_method.corrs after adding corr should be 1"
    assert icorr.method is not None, "method not associated with corr"

    return db_session, icorr


def test_ci(db_session_with_corr):
    db_session, icorr = db_session_with_corr
    assert len(icorr.cis) == 0, "No CI should be associated with PickCorrection yet"

    # Add repicker method #
    d = {
        "name": "Kuleshov",
        "phase": "P",
        "desc": "For P picks, from Armstrong 2023 BSSA paper",
        "path": "the/model/files/are/stored/here",
    }

    imeth = tables.CalibrationMethod(**d)
    db_session.add(imeth)
    db_session.commit()
    assert (
        len(imeth.cis) == 0
    ), "calibration_method.cis should have 0 values at this point"
    #

    d = {
        "percent": 90,
        "lb": -2.13,
        "ub": 2.55,
    }

    ici = tables.CredibleInterval(corr_id=icorr.id, method_id=imeth.id, **d)
    db_session.add(ici)
    db_session.commit()

    assert len(icorr.cis) == 1, "1 CI should be associated with PickCorrection yet"
    assert len(imeth.cis) == 1, "calibration_method.cis should have 1 value now"
    assert ici.corr is not None, "CI should have a PickCorrection associated with it"
    assert (
        ici.method is not None
    ), "CI should have a CalibrationMethod associcated with it"
    assert ici.percent == 90, "Invalid ci.percent"
    assert ici.lb == -2.13, "Invalid ci.lb"
    assert ici.ub == 2.55, "Invalid ci.ub"
    assert ici.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert ici.last_modified.month == datetime.now().month, "invalid last_modified year"
    assert ici.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        ici.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


@pytest.fixture
def db_session_with_contdata_and_channel(db_session_with_contdata):
    db_session, icd = db_session_with_contdata

    d = {
        "seed_code": "HHE",
        "loc": "01",
        "ondate": datetime.strptime("1993-10-26T00:00:00.00", dateformat),
        "samp_rate": 100.0,
        "clock_drift": 1e-5,
        "sensor_desc": "Nanometrics something or other",
        "sensit_units": "M/S",
        "sensit_val": 9e9,
        "sensit_freq": 5,
        "lat": 44.4,
        "lon": -110.555,
        "elev": 256,
        "depth": 100,
        "azimuth": 90,
        "dip": -90,
    }

    ichan = tables.Channel(sta_id=icd.station.id, **d)

    db_session.add(ichan)
    db_session.commit()

    return db_session, icd, ichan


def test_gap(db_session_with_contdata_and_channel):
    db_session, icd, ichan = db_session_with_contdata_and_channel
    assert len(icd.gaps) == 0, "ContData should have no gaps yet"
    assert len(ichan.gaps) == 0, "Channel should have no gaps yet"

    d = {
        "start": datetime.strptime("2023-01-02T12:13:14.15", dateformat),
        "end": datetime.strptime("2023-01-02T12:13:14.25", dateformat),
        "startsamp": 4399415,
        "endsamp": 4399425,
    }

    igap = tables.Gap(data_id=icd.id, chan_id=ichan.id, **d)
    db_session.add(igap)
    db_session.commit()

    assert len(icd.gaps) == 1, "ContData should have one gaps now"
    assert len(ichan.gaps) == 1, "Channel should have one gaps now"
    assert igap.contdatainfo is not None, "Gap should have contdatainfo"
    assert igap.channel is not None, "Gap should have channel"

    assert igap.start.microsecond == 150000, "Invalid start fractional second"
    assert igap.end.microsecond == 250000, "Invalid end microsecond"
    assert igap.startsamp == 4399415, "Invalid startsamp"
    assert igap.endsamp == 4399425, "Invalid endsamp"
    assert igap.avail_sig_sec == 0.0, "Invalid default avail_sig_sec"
    assert igap.last_modified.year == datetime.now().year, "invalid last_modified year"
    assert (
        igap.last_modified.month == datetime.now().month
    ), "invalid last_modified year"
    assert igap.last_modified.day == datetime.now().day, "invalid last_modified year"
    assert (
        igap.last_modified.microsecond == 0
    ), "last_modified does not include microseconds"


@pytest.fixture
def db_session_with_contdata_and_channel_and_pick(db_session_with_contdata_and_channel):
    db_session, icd, ichan = db_session_with_contdata_and_channel

    stat = icd.station

    d = {
        "chan_pref": "HH",
        "phase": "P",
        "ptime": datetime.strptime("2024-01-02T10:11:12.13", dateformat),
        "auth": "SPDL",
        "snr": 40.5,
        "amp": 10.22,
    }

    ipick = tables.Pick(sta_id=stat.id, **d)
    db_session.add(ipick)
    db_session.commit()

    assert len(stat.picks) == 1, "picks not associated with station"
    assert ipick.station is not None, "station not associated with pick"

    return db_session, icd, ichan, ipick


def test_waveform(db_session_with_contdata_and_channel_and_pick):
    db_session, icd, ichan, ipick = db_session_with_contdata_and_channel_and_pick
    assert len(icd.wfs) == 0, "ContData should have no waveforms yet"
    assert len(ichan.wfs) == 0, "Channel should have no waveforms yet"
    assert len(ipick.wfs) == 0, "Pick should have no waveforms yet"

    d = {
        "filt_low": 1.5,
        "filt_high": 17.5,
        "start": datetime.strptime("2024-01-02T10:11:02.13", dateformat),
        "end": datetime.strptime("2024-01-02T10:11:22.14", dateformat),
        "proc_notes": "Processed for repicker",
        "data": np.zeros((2000)).tolist(),
    }

    iwf = tables.Waveform(data_id=icd.id, chan_id=ichan.id, pick_id=ipick.id, **d)
    db_session.add(iwf)
    db_session.commit()

    assert len(icd.wfs) == 1, "ContData should have 1 waveform now"
    assert len(ichan.wfs) == 1, "Channel should have 1 waveform now"
    assert len(ipick.wfs) == 1, "Pick should have 1 waveform now"
    assert iwf.contdatainfo is not None, "Waveform should have contdatainfo"
    assert iwf.pick is not None, "Waveform should have a pick"
    assert iwf.channel is not None, "Waveform should have a channel"

    assert iwf.filt_low == 1.5, "Invalid filt_low"
    assert iwf.filt_high == 17.5, "Invalid filt_high"
    assert iwf.start.second == 2, "Invalid start second"
    assert iwf.start.microsecond == 130000, "Invalid start microsecond"
    assert iwf.end.second == 22, "Invalud end second"
    assert iwf.end.microsecond == 140000, "Invalid end microsecond"
    assert np.array_equal(iwf.data, np.zeros(2000)), "invalid data"
