from sqlalchemy import String, Integer, SmallInteger, DateTime
from sqlalchemy.types import TIMESTAMP, Double, Date, Boolean, JSON
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from typing import List, Optional
from sqlalchemy.schema import UniqueConstraint, CheckConstraint, ForeignKey
import datetime
import enum

from .database import Base

class FMEnum(enum.Enum):
    """Define ENUM for FirstMotion class"""
    UK = "uk"
    UP = "up"
    DN = "dn"

class ISAMethod(Base):
    """Abstract class from creating IS-A Method tables"""
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    desc: Mapped[Optional[str]] = mapped_column(String(255))
    path: Mapped[Optional[str]] = mapped_column(String(255))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)
    
class Station(Base):
    __tablename__ = "station"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    net: Mapped[str] = mapped_column(String(2), nullable=False)
    sta: Mapped[str] = mapped_column(String(4), nullable=False)
    ondate = mapped_column(DateTime, nullable=False)
    ## 
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    elev: Mapped[float] = mapped_column(Double)
    offdate = mapped_column(DateTime, nullable=True)
    # define 'last_modified' to use the SQL current_timestamp MySQL function on update
    # last_modified = mapped_column(DateTime, onupdate=func.utc_timestamp())
    # define 'last_updated' to be populated with datetime.now()
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)

    # One-to-Many relationship with Channel
    channels: Mapped[List["Channel"]] = relationship("channel.id", back_populates="station")
    # One-to-Many relationship with DLDetection
    dldetections: Mapped[List["DLDetection"]] = relationship("dldetection.id", back_populates="station")
    # One-to-Many relation with DailyContDataInfo
    contdatainfo: Mapped[List["DailyContDataInfo"]] = relationship("contdatainfo.id", back_populates="station")

    __table_args__ = (UniqueConstraint(net, sta, ondate, name="simplify_pk"), 
                      CheckConstraint("lat >= -90 AND lon <= 90", name="valid_lat"),
                      CheckConstraint("lon >= -180 AND lon <= 180", name="valid_lon"),
                      CheckConstraint("elev >= 0", name="positive_elev"),)
    
class Channel(Base):
    __tablename__ = "channel"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(ForeignKey("station.id"), nullable=False)
    seed_code: Mapped[str] = mapped_column(String(3), nullable=False)
    loc: Mapped[str] = mapped_column(String(2), nullable=False)
    ondate = mapped_column(DateTime, nullable=False)
    ##
    samp_rate: Mapped[float] = mapped_column(Double)
    clock_drift: Mapped[float] = mapped_column(Double)
    sensor_name: Mapped[Optional[str]] = mapped_column(String(50))
    sensitivity_units: Mapped[str] = mapped_column(String(10))
    sensitivity_val: Mapped[float] = mapped_column(Double)
    overall_gain_vel: Mapped[Optional[float]] = mapped_column(Double)
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    elev: Mapped[float] = mapped_column(Double)
    depth: Mapped[float] = mapped_column(Double)
    azimuth: Mapped[float] = mapped_column(Double)
    dip: Mapped[int] = mapped_column(SmallInteger)
    offdate = mapped_column(DateTime, nullable=True)
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)
    
    # Many-to-One relation with Station
    station: Mapped["Station"] = relationship("station.id", back_populates="channels")
    # One-to-Many relationship with Gaps
    gaps: Mapped[List["Gap"]] = relationship("gap.id", back_populates="channel")
    # One-to-Many relationship with Waveform
    wfs: Mapped[List["Waveform"]] = relationship("waveform.id", back_populates="channel")

    __table_args__ = (UniqueConstraint(sta_id, seed_code, loc, ondate, name="simplify_pk"), 
                      CheckConstraint("samp_rate > 0", name="positive_samp_rate"),
                      CheckConstraint("lat >= -90 AND lon <= 90", name="valid_lat"),
                      CheckConstraint("lon >= -180 AND lon <= 180", name="valid_lon"),
                      CheckConstraint("elev >= 0", name="nonneg_elev"),
                      CheckConstraint("azimuth >= 0 AND azimuth <= 360", name="valid_azimuth"),
                      CheckConstraint("dip >= -90 AND dip <= 90", name="valid_dip")
                      )
    
class DailyContDataInfo(Base):
    __tablename__ = "contdatainfo"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(ForeignKey("station.id"), nullable=False)
    chan_pref: Mapped[str] = mapped_column(String(2), nullable=False)
    ncomps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    date = mapped_column(Date, nullable=False)
    ##
    samprate: Mapped[float] = mapped_column(Double)
    dt: Mapped[float] = mapped_column(Double)    
    org_npts: Mapped[int] = mapped_column(Integer)
    org_start = mapped_column(DateTime, nullable=False)
    org_end = mapped_column(DateTime, nullable=False)
    proc_npts: Mapped[Optional[int]] = mapped_column(Integer)
    proc_start = mapped_column(DateTime, nullable=True)
    proc_end = mapped_column(DateTime, nullable=True)
    prev_appended: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="prev_app_bool"),
                                                nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(20))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)
    
    # Many-to-One relation with Station
    station: Mapped["Station"] = relationship("station.id", back_populates="contdatainfo")
    # One-to-Many relationship with DLDetection
    dldets: Mapped[List["DLDetection"]] = relationship("dldetection.id", back_populates="contdatainfo")
    # One-to-Many relationship with Gaps
    gaps: Mapped[List["Gap"]] = relationship("gap.id", back_populates="contdatainfo")
    # One-to-Many relationship with Waveform
    wfs: Mapped[List["Waveform"]] = relationship("waveform.id", back_populates="contdatainfo")

    __table_args__ = (UniqueConstraint(sta_id, chan_pref, ncomps, date, name="simplify_pk"),
                      CheckConstraint("samprate > 0", name="positive_samprate"),
                      CheckConstraint("dt <= 1", name="dt_lt_1"),
                      CheckConstraint("proc_npts >= 1", name="proc_npts_gt_1"),
                      CheckConstraint("org_npts >= 0", name="nonneg_org_npts"),
                      CheckConstraint("proc_end > proc_start", name="valid_proc_times"),
                      CheckConstraint("org_end > org_start", name="valid_org_times")
                      )
    
class RepickerMethod(ISAMethod):
    __tablename__ = "repicker_method"

    # One-to-Many relationship with PickCorrection
    corrs: Mapped[List["PickCorrection"]] = relationship("pick_corr.id", back_populates="method")

class CalibrationMethod(ISAMethod):
    __tablename__ = "calibration_method"

    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship("ci.id", back_populates="method")

class FMMethod(ISAMethod):
    __tablename__ = "fm_method"

    # One-to-Many relationship with FM
    fms: Mapped[List["FirstMotion"]] = relationship("fm.id", back_populates="method")

class DetectionMethod(ISAMethod):
    __tablename__ = "detection_method"
    phase: Mapped[str] = mapped_column(String(4))

    # One to Many relationship with DLDetection
    dldets: Mapped[List["DLDetection"]] = relationship("dldetection.id", back_populates="method")

class DLDetection(Base):
    __tablename__ = "dldetection"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(ForeignKey("contdatainfo.id"), nullable=False)
    method_id = mapped_column(ForeignKey("detection_method.id"), nullable=False)
    sample: Mapped[int] = mapped_column(Integer)
    ##
    width: Mapped[float] = mapped_column(Double)
    height: Mapped[int] = mapped_column(SmallInteger)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)
    
    # Many-to-one relationship with ContData
    contdatainfo: Mapped["DailyContDataInfo"] = relationship("contdatainfo.id", back_populates="dldets")
    # One-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship("pick.id", back_populates="dldet")
    # Many-to-one relationship with DetectionMethod
    method: Mapped["DetectionMethod"] = relationship("detection_method.id", back_populates="dldets")

    __table_args__ = (UniqueConstraint(data_id, method_id, sample, name="simplify_pk"),
                      CheckConstraint("sample >= 0", name="nonneg_sample"),
                      CheckConstraint("width > 0", name="positive_width"),
                      CheckConstraint("height > 0 AND height <= 100", name="valid_height"))

class Pick(Base):
    __tablename__ = "pick"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(ForeignKey("station.id"), nullable=False)
    chan_pref: Mapped[str] = mapped_column(String(2), nullable=False)
    phase: Mapped[str] = mapped_column(String(4), nullable=False)
    # TODO: Check this has fractional seconds
    pick_time = mapped_column(DateTime, nullable=False)
    auth: Mapped[str] = mapped_column(String(10), nullable=False)
    ##
    # From waveform info
    snr: Mapped[Optional[float]] = mapped_column(Double)
    amp: Mapped[Optional[float]] = mapped_column(Double)
    # FK from Detections
    detid = mapped_column(ForeignKey("dldetection.id"), nullable=True)

    # Many-to-one relationship with Station
    station: Mapped["Station"] = relationship("station.id", back_populates="pick")
    # One-to-one relationship with Detection
    dldet: Mapped["DLDetection"] = relationship("dldetection.id", back_populates="pick")
    # One-to-many relationship with PickCorrection
    corrs: Mapped[List["PickCorrection"]] = relationship("pick_corr.id", back_populates="pick")
    # One-to-many relationship with FM
    fms: Mapped[List["FirstMotion"]] = relationship("fm.id", back_populates="pick")
    # One-to-many relationship with Waveform
    wfs: Mapped[List["Waveform"]] = relationship("wf.id", back_populates="pick")

    __table_args__ = (UniqueConstraint(sta_id, chan_pref, phase, pick_time, auth, name="simplify_pk"),
                      UniqueConstraint(detid, name="detid"),
                      CheckConstraint("amp > 0", name="positive_amp"))
    
class PickCorrection(Base):
    __tablename__ = "pick_corr"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(ForeignKey("pick.id"), nullable=False)
    method_id = mapped_column(ForeignKey("repicker_method.id"), nullable=False)
    ##
    median: Mapped[float] = mapped_column(Double)
    mean: Mapped[float] = mapped_column(Double)
    std: Mapped[float] = mapped_column(Double)
    if_low: Mapped[float] = mapped_column(Double)
    if_high: Mapped[float] = mapped_column(Double)
    trim_median: Mapped[float] = mapped_column(Double)
    trim_mean: Mapped[float] = mapped_column(Double)
    # TODO: Figure out what I am going to store here
    preds_path: Mapped[str] = mapped_column(String(100))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)
    
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship("pick.id", back_populates="corrs")
    # Many-to-one relationship with RepickerMethod
    method: Mapped["RepickerMethod"] = relationship("repicker_method.id", back_populates="corrs")
    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship("ci.id", back_populates="corr")

    __table_args__ = (UniqueConstraint(pid, method_id, name="simplify_pk"),
                      CheckConstraint("if_low < if_high", name="if_order"),
                      CheckConstraint("std > 0", name="positive_std"),)

class FirstMotion(Base):
    __tablename__ = "fm"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(ForeignKey("pick.id"), nullable=False)
    method_id = mapped_column(ForeignKey("fm_method.id"), nullable=False)
    ##
    fm: Mapped[FMEnum]
    prob_up: Mapped[Optional[float]] = mapped_column(Double)
    prob_dn: Mapped[Optional[float]] = mapped_column(Double)
    # TODO: Figure out what I am going to store here
    preds_path: Mapped[Optional[str]] = mapped_column(String(100))

    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship("pick.id", back_populates="fms")
    # Many-to-one relationship with RepickerMethod
    method: Mapped["FMMethod"] = relationship("fm_method.id", back_populates="fms")

    __table_args__ = (UniqueConstraint(pid, method_id, name="simplify_pk"),
                      CheckConstraint("prob_up >= 0", name="nonneg_prob_up"),
                      CheckConstraint("prob_dn >= 0", name="nonneg_prob_dn"))
    
class CredibleInterval(Base):
    __tablename__ = "ci"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    corr_id = mapped_column(ForeignKey("pick_corr.id"), nullable=False)
    method_id = mapped_column(ForeignKey("calibration_method.id"), nullable=False)
    percent: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ##
    lb: Mapped[float] = mapped_column(Double)
    ub: Mapped[float] = mapped_column(Double)

    # Many-to-one relationship with PickCorrection
    corr: Mapped["PickCorrection"] = relationship("pick_corr.id", back_populates="cis")
    # Many-to-one relationship with CalibrationMethod
    method: Mapped["CalibrationMethod"] = relationship("calibration_method.id", back_populates="cis")

    __table_args__ = (UniqueConstraint(corr_id, method_id, percent, name="simplify_pk"),
                      CheckConstraint("lb < ub", name="bound_order"),
                      CheckConstraint("percent > 0 AND percent <= 100", name="valid_percent"))
    
class Gap(Base):
    __tablename__ = "gap"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(ForeignKey("contdatainfo.id"), nullable=False)
    chan_id = mapped_column(ForeignKey("channel.id"), nullable=False)
    start = mapped_column(DateTime, nullable=False)
    ##
    end = mapped_column(DateTime, nullable=False)
    startsamp: Mapped[int] = mapped_column(Integer)
    endsamp: Mapped[int] = mapped_column(Integer)
    avail_sig_sec: Mapped[float] = mapped_column(Double)

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship("contdatainfo.id", back_populates="gaps")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship("channel.id", back_populates="gaps")

    __table_args__ = (UniqueConstraint(data_id, chan_id, start, name="simplify_pk"),
                      CheckConstraint("start < end", name="times_order"),
                      CheckConstraint("startsamp >= 0", name="nonneg_startsamp"),
                      CheckConstraint("endsamp >= 1", name="pos_startsamp"),
                      CheckConstraint("startsamp < endsamp", name="samps_order"),
                      CheckConstraint("avail_sig_sec >= 0", name="nonneg_avail_sig"))
    
class Waveform(Base):
    __tablename__ = "waveform"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(ForeignKey("contdatainfo.id"), nullable=False)
    chan_id = mapped_column(ForeignKey("channel.id"), nullable=False)
    pick_id = mapped_column(ForeignKey("pick.id"), nullable=False)
    ##
    filt_low: Mapped[Optional[float]] = mapped_column(Double)
    filt_high: Mapped[Optional[float]] = mapped_column(Double)
    # TODO: Figure out the type I am going to use....
    data = mapped_column(JSON, nullable=False)
    start = mapped_column(DateTime, nullable=False)
    end = mapped_column(DateTime, nullable=False)
    proc_notes: Mapped[Optional[str]] = mapped_column(String(255))

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship("contdatainfo.id", back_populates="wfs")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship("channel.id", back_populates="wfs")
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship("pick.id", back_populates="wfs")

    __table_args__ = (UniqueConstraint(data_id, chan_id, pick_id, name="simplify_pk"),
                      CheckConstraint("filt_low > 0", name="pos_filt_low"), 
                      CheckConstraint("filt_high > 0", name="pos_filt_high"),
                      CheckConstraint("filt_low < filt_high", name="filt_order"),
                      CheckConstraint("start < end", name="times_order"),
                      )