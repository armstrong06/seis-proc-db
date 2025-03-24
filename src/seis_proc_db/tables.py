from sqlalchemy import String, Integer, SmallInteger, DateTime, Enum
from sqlalchemy.types import TIMESTAMP, Double, Date, Boolean, JSON
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import DATETIME
from typing import List, Optional
from sqlalchemy.schema import UniqueConstraint, CheckConstraint, ForeignKey
from datetime import datetime
import enum

from seis_proc_db.database import Base

MYSQL_DATETIME_FSP = 6

class FMEnum(enum.Enum):
    # Not using this currently, but maybe would be useful if I wanted to make directly from 0/1
    """Define ENUM for FirstMotion class"""
    UK = "uk"
    UP = "up"
    DN = "dn"

class ISAMethod(Base):
    """Abstract table from creating IS-A Method tables
    
    id: Not meaningful identifier for the method, used as the PK
    name: Name of the method used
    desc: Optional. Description of method.
    path: Optional. Path where relevant files for the method are stored. 
    last_modified: Automatic field that keeps track of when a method was added to
        or modified in the database in local time. Does not include fractional seconds.
    """
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    desc: Mapped[Optional[str]] = mapped_column(String(255))
    path: Mapped[Optional[str]] = mapped_column(String(255))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)
    
class Station(Base):
    """Stores a station's information. Unique station is defined by the net, sta, and ondate.

        id: Not meaningful identifier for the station, used as the PK
        net: Network abbreviation 
        sta: Station code
        ondate: The datetime in UTC that the station was turned on. Does not include fractional seconds.
        lat: station latitude
        lon: station longitude
        elev: station elevation in m
        offdate: Optional. The datetime in UTC that the station was turned off. Does not include fractional seconds.
        last_modified: Automatic field that keeps track of when a station was added to
        or modified in the database in local time. Does not include fractional seconds.
    """
    __tablename__ = "station"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    net: Mapped[str] = mapped_column(String(2), nullable=False)
    sta: Mapped[str] = mapped_column(String(4), nullable=False)
    ondate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ## 
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    elev: Mapped[float] = mapped_column(Double)
    offdate: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # define 'last_modified' to use the SQL current_timestamp MySQL function on update
    # last_modified = mapped_column(DateTime, onupdate=func.utc_timestamp())
    # define 'last_updated' to be populated with datetime.now()
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)

    # One-to-Many relationship with Channel
    channels: Mapped[List["Channel"]] = relationship(back_populates="station")
    # One-to-Many relationship with Pick
    picks: Mapped[List["Pick"]] = relationship(back_populates="station")
    # One-to-Many relation with DailyContDataInfo
    contdatainfo: Mapped[List["DailyContDataInfo"]] = relationship(back_populates="station")

    __table_args__ = (UniqueConstraint(net, sta, ondate, name="simplify_pk"), 
                      CheckConstraint("lat >= -90 AND lon <= 90", name="valid_lat"),
                      CheckConstraint("lon >= -180 AND lon <= 180", name="valid_lon"),
                      CheckConstraint("elev >= 0", name="positive_elev"),)
    
    def __repr__(self) -> str:
         return (f"Station(id={self.id!r}, net={self.net!r}, sta={self.sta!r}, ondate={self.ondate!r}, " 
                 f"lat={self.lat!r}, lon={self.lon!r}, elev={self.elev!r}, offdate={self.offdate!r}, " 
                 f"last_modified={self.last_modified!r})")
    
class Channel(Base):
    """Stores a channel's information.

    Args:
        id: Not meaningful channel identifier that is used as the PK. 
        sta_id: id of a Station
        seed_code: SEED Channel name
        loc: Location code
        ondate: Datetime the channel was turned on in UTC. Does not include fractional seconds.
        samp_rate: Instrument sampling rate
        clock_drift: Instrument clock drift
        sensit_units: Instrument sensitivity input units
        sensit_freq: Frequency the instrument sensitivity is measured at
        sensit_val: Instrument sensitivity value
        lat: Instrument latitude
        lon: Instrument longitude
        elev: Instrument elevation in m
        depth: Instrument depth in m
        azimuth: Instrument orientation azimuth
        dip: Instrument orientation dip
        offdate: Optional. The datetime the channel was turned off in UTC. Does not include fractional seconds.
        overall_gain_vel: Optional. The overall gain of the instrument computed in M/S
        sensor_desc: Optional. The short description of the sensor, usually including the brand
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """
    __tablename__ = "channel"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(ForeignKey("station.id"), nullable=False)
    seed_code: Mapped[str] = mapped_column(String(3), nullable=False)
    loc: Mapped[str] = mapped_column(String(2), nullable=False)
    ondate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ##
    samp_rate: Mapped[float] = mapped_column(Double)
    clock_drift: Mapped[float] = mapped_column(Double)
    sensor_desc: Mapped[Optional[str]] = mapped_column(String(50))
    sensit_units: Mapped[str] = mapped_column(String(10))
    sensit_val: Mapped[float] = mapped_column(Double)
    sensit_freq: Mapped[float] = mapped_column(Double)
    overall_gain_vel: Mapped[Optional[float]] = mapped_column(Double)
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    elev: Mapped[float] = mapped_column(Double)
    depth: Mapped[float] = mapped_column(Double)
    azimuth: Mapped[float] = mapped_column(Double)
    dip: Mapped[int] = mapped_column(SmallInteger)
    offdate: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)
    
    # Many-to-One relation with Station
    station: Mapped["Station"] = relationship(back_populates="channels")
    # One-to-Many relationship with Gaps
    gaps: Mapped[List["Gap"]] = relationship(back_populates="channel")
    # One-to-Many relationship with Waveform
    wfs: Mapped[List["Waveform"]] = relationship(back_populates="channel")

    __table_args__ = (UniqueConstraint(sta_id, seed_code, loc, ondate, name="simplify_pk"), 
                      CheckConstraint("samp_rate > 0", name="positive_samp_rate"),
                      CheckConstraint("lat >= -90 AND lon <= 90", name="valid_lat"),
                      CheckConstraint("lon >= -180 AND lon <= 180", name="valid_lon"),
                      CheckConstraint("elev >= 0", name="nonneg_elev"),
                      CheckConstraint("azimuth >= 0 AND azimuth <= 360", name="valid_azimuth"),
                      CheckConstraint("dip >= -90 AND dip <= 90", name="valid_dip")
                      )
    def __repr__(self) -> str:
         return (f"Channel(id={self.id!r}, sta_id={self.sta_id!r}, seed_code={self.seed_code!r}, "
                 f"loc={self.loc!r}, ondate={self.ondate!r}, samp_rate={self.samp_rate!r}, " 
                 f"clock_drift={self.clock_drift!r}, sensor_desc={self.sensor_desc!r}, "
                 f"sensit_units={self.sensit_units!r}, sensit_freq={self.sensit_freq!r}, sensit_val={self.sensit_val!r}, "
                 f"overall_gain_vel={self.overall_gain_vel!r}, lat={self.lat!r}, lon={self.lon!r}, "
                 f"elev={self.elev!r}, depth={self.depth!r}, azimuth={self.azimuth!r}, dip={self.dip!r}, " 
                 f"offdate={self.offdate!r}, last_modified={self.last_modified!r})")
    
class DailyContDataInfo(Base):
    """Keep track of information relating to daily (24 hr) continuous data files used in algorithms.

    Args:
        id: Not meaningful identifier that is used as the PK
        sta_id: id of the related Station
        chan_pref: First two letters of the SEED code for the channels used
        date: Date the data was recorded
        samp_rate: Sampling rate of the data (may be different than the Channel samp_rate)
        dt: Sampling interval of the data (should be 1/samp_rate)
        org_npts: Number of data samples in the file before any processing is done in ApplyDetectors
        org_start: Starttime (UTC) of the file before any processing is done in ApplyDetectors.
            DOES include fractional seconds.
        org_end: Endtime (UTC) of the file before any processing is done in ApplyDetectors.
            DOES include fractional seconds.
        proc_npts: Optional. Number of data samples in the file after processing in ApplyDetectors.
            This will be the same for the saved posterior probabilities files.
        proc_start: Optional. Starttime (UTC) of the file after processing in ApplyDetectors.
            This will be the same for the saved posterior probabilities files.
            DOES include fractional seconds.
        proc_end: Optional. Endtime (UTC) of the file after processing in ApplyDetectors.
            This will be the same for the saved posterior probabilities files.
            DOES include fractional seconds.
        prev_appended: Optional. Boolean value that stores whether data from the end of the previous
            day was appended to the start of this file when processing in ApplyDetectors.
        error: Optional. Short error string or message indicating why this data was not used in ApplyDetectors.
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does NOT include fractional seconds.
    """
    __tablename__ = "contdatainfo"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(ForeignKey("station.id"), nullable=False)
    chan_pref: Mapped[str] = mapped_column(String(2), nullable=False)
    ncomps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    date = mapped_column(Date, nullable=False)
    ##
    samp_rate: Mapped[float] = mapped_column(Double)
    # TODO: Decide if need to store this... 
    dt: Mapped[float] = mapped_column(Double)  
    # TODO: Decided whether to remove npts 
    org_npts: Mapped[int] = mapped_column(Integer)
    org_start: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    org_end: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    # TODO: Decide if proc_* values should be stored in a different table
    proc_npts: Mapped[Optional[int]] = mapped_column(Integer)
    proc_start: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=True)
    proc_end: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=True)
    # TODO: Should this be nullable or have a default value (i.e., 0)
    prev_appended: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="prev_app_bool"),
                                                nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(20))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)
    
    # Many-to-One relation with Station
    station: Mapped["Station"] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with DLDetection
    dldets: Mapped[List["DLDetection"]] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with Gaps
    gaps: Mapped[List["Gap"]] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with Waveform
    wfs: Mapped[List["Waveform"]] = relationship(back_populates="contdatainfo")

    __table_args__ = (UniqueConstraint(sta_id, chan_pref, ncomps, date, name="simplify_pk"),
                      CheckConstraint("samp_rate > 0", name="positive_samp_rate"),
                      CheckConstraint("dt <= 1", name="dt_lt_1"),
                      CheckConstraint("proc_npts >= 1", name="proc_npts_gt_1"),
                      CheckConstraint("org_npts >= 0", name="nonneg_org_npts"),
                      CheckConstraint("proc_end > proc_start", name="valid_proc_times"),
                      CheckConstraint("org_end > org_start", name="valid_org_times")
                      )
    
    def __repr__(self) -> str:
         return (f"DailyContDataInfo(id={self.id!r}, sta_id={self.sta_id!r}, chan_pref={self.chan_pref!r}, "
                 f"ncomps={self.ncomps!r}, date={self.date!r}, samp_rate={self.samp_rate!r}, dt={self.dt!r}, "
                 f"org_npts={self.org_npts!r}, org_start={self.org_start!r}, org_end={self.org_end!r}, "
                 f"proc_npts={self.proc_npts!r}, proc_start={self.proc_start!r}, proc_end={self.proc_end!r}, "
                 f"prev_appended={self.prev_appended!r}, error={self.error!r}, last_modified={self.last_modified!r})")
    
class RepickerMethod(ISAMethod):
    """Stores some info about the type/version of phase repicking model or technique used. 

    Args:
        ISAMethod (_type_)

        phase: Optional. Phase type the model was designed for, if applicable. 

    """
    __tablename__ = "repicker_method"

    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One-to-Many relationship with PickCorrection
    corrs: Mapped[List["PickCorrection"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
         return (f"RepickerMethod(id={self.id!r}, name={self.name!r}, desc={self.desc!r}, path={self.path!r}, last_modified={self.last_modified!r})")

class CalibrationMethod(ISAMethod):
    """Stores some info about the type/version of calibration model or technique used. 

    Args:
        ISAMethod (_type_)

        phase: Optional. Phase type the model was designed for, if applicable. 

    """
    __tablename__ = "calibration_method"

    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
         return (f"CalibrationMethod(id={self.id!r}, name={self.name!r}, desc={self.desc!r}, path={self.path!r}, last_modified={self.last_modified!r})")

class FMMethod(ISAMethod):
    """Stores some info about the type/version of first motion classifier used. 

    Args:
        ISAMethod (_type_)
    """
    __tablename__ = "fm_method"

    # One-to-Many relationship with FM
    fms: Mapped[List["FirstMotion"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
         return (f"FMMethod(id={self.id!r}, name={self.name!r}, desc={self.desc!r}, path={self.path!r}, last_modified={self.last_modified!r})")

class DetectionMethod(ISAMethod):
    """Stores some info about the type/version of phase Detection algorithm used. 

    Args:
        ISAMethod (_type_)

        phase: Optional. Phase type the model was designed for, if applicable. 

    """
    __tablename__ = "detection_method"
    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One to Many relationship with DLDetection
    dldets: Mapped[List["DLDetection"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
        return (f"DetectioNMethod(id={self.id!r}, name={self.name!r}, desc={self.desc!r}, "
                f"path={self.path!r}, phase={self.phase!r} last_modified={self.last_modified!r})")

class DLDetection(Base):
    """Store Deep-Learning (DL) phase detections from a certain continuous data file and detection method.

    Args:
        Base (_type_): _description_
        id: Not meaningful detection identifier that is used as the PK.
        data_id: ID of DailyContDataInfo the detection comes from. 
        method_id: ID of the DetectionMethod used.
        sample: Sample in the continous data file defined by DailyContDateInfo the detection is assigned to. 
            A pick time can be derived for a given detection using the sample and DailyContDateInfo.proc_start
        phase: Presumed phase type of the detection.
        width: Width of the spike in the posterior probabilities the detection is associated with. 
        height: Posterior probability value at the detection sample. Value is expected between 1 and 100 (not 0 and 1).
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds. 
    """
    __tablename__ = "dldetection"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(ForeignKey("contdatainfo.id"), nullable=False)
    method_id = mapped_column(ForeignKey("detection_method.id"), nullable=False)
    sample: Mapped[int] = mapped_column(Integer, nullable=False)
    ##
    phase: Mapped[str] = mapped_column(String(4))
    width: Mapped[float] = mapped_column(Double)
    height: Mapped[int] = mapped_column(SmallInteger)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)
    
    # Many-to-one relationship with ContData
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="dldets")
    # One-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="dldet")
    # Many-to-one relationship with DetectionMethod
    method: Mapped["DetectionMethod"] = relationship(back_populates="dldets")

    __table_args__ = (UniqueConstraint(data_id, method_id, sample, name="simplify_pk"),
                      CheckConstraint("sample >= 0", name="nonneg_sample"),
                      CheckConstraint("width > 0", name="positive_width"),
                      CheckConstraint("height > 0 AND height <= 100", name="valid_height"))
    
    def __repr__(self) -> str:
        return (f"DLDetection(id={self.id!r}, data_id={self.data_id!r}, method_id={self.method_id!r}, sample={self.sample!r}, "
                f"phase={self.phase!r}, width={self.width!r}, height={self.height!r}, last_modified={self.last_modified!r})")

class Pick(Base):
    """Describe a pick, which may be derived from a DLDetection.

    Args:
        Base (_type_): _description_
        id: Not meaningful pick identifier that is used as the PK.
        sta_id: Identifier for the Station the pick was made at
        chan_pref: First two letters of the SEED code for the channels used
        phase: Presumed phase type of the pick
        ptime: DateTime of the pick in UTC. DOES include fractional seconds. If a pick has a PickCorrection,
            it is NOT included in the ptime value. 
        auth: Short identifier for the author/creator of the pick (i.e., SPDL, UUSS)
        snr: Single to noise ratio of pick. TODO: Define a clear method for measuring this
        amp: Amplitude value of pick. TODO: Define a clear method for measuring this
        detid: Optional. Identifier for the DLDetection the pick is derived from
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds. 
    """
    __tablename__ = "pick"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(ForeignKey("station.id"), nullable=False)
    chan_pref: Mapped[str] = mapped_column(String(2), nullable=False)
    # TODO: Should phase be removed from the PK, in the case it was unknown?
    phase: Mapped[str] = mapped_column(String(4), nullable=False)
    ptime: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    auth: Mapped[str] = mapped_column(String(10), nullable=False)
    ##
    # From waveform info
    snr: Mapped[Optional[float]] = mapped_column(Double)
    amp: Mapped[Optional[float]] = mapped_column(Double)
    # FK from Detections
    detid = mapped_column(ForeignKey("dldetection.id"), nullable=True)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)

    # Many-to-one relationship with Station
    station: Mapped["Station"] = relationship(back_populates="picks")
    # One-to-one relationship with Detection
    dldet: Mapped["DLDetection"] = relationship(back_populates="pick")
    # One-to-many relationship with PickCorrection
    corrs: Mapped[List["PickCorrection"]] = relationship(back_populates="pick")
    # One-to-many relationship with FM
    fms: Mapped[List["FirstMotion"]] = relationship(back_populates="pick")
    # One-to-many relationship with Waveform
    wfs: Mapped[List["Waveform"]] = relationship(back_populates="pick")

    __table_args__ = (UniqueConstraint(sta_id, chan_pref, phase, ptime, auth, name="simplify_pk"),
                      UniqueConstraint(detid, name="detid"),
                      CheckConstraint("amp > 0", name="positive_amp"))
    
    def __repr__(self) -> str:
        return (f"Pick(id={self.id!r}, sta_id={self.sta_id!r}, chan_pref={self.chan_pref!r}, phase={self.phase!r}, ptime={self.ptime!r}, "
                f"auth={self.auth!r}, snr={self.snr!r}, amp={self.amp!r}, det_id={self.detid}, last_modified={self.last_modified!r})")

class PickCorrection(Base):
    """Correction to a Pick to improve the arrival time estimate. Basically assumes some sampling method.

    Args:
        Base (_type_): 
        id: Not meaningful pick correction identifier that is used as the PK.
        pid: Identifer of the Pick the correction is associated with.
        method_id: Identifier of the RepickerMethod used.
        median: Median value of all samples
        mean: Mean value of all samples
        std: Standard deviation of all samples
        if_low: Lower inner fence value for all samples
        if_high: Upper inner fence value for all samples
        trim_median: Median value of samples within the inner fence
        trim_mean: Mean value of samples within the inner fence
        preds: JSON object storing the sampled pick correction values
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds. 
    """
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
    preds: Mapped[JSON] = mapped_column(JSON)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)
    
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="corrs")
    # Many-to-one relationship with RepickerMethod
    method: Mapped["RepickerMethod"] = relationship(back_populates="corrs")
    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship(back_populates="corr")

    __table_args__ = (UniqueConstraint(pid, method_id, name="simplify_pk"),
                      CheckConstraint("if_low < if_high", name="if_order"),
                      CheckConstraint("std > 0", name="positive_std"),)
    
    def __repr__(self) -> str:
        return (f"PickCorrection(id={self.id!r}, pid={self.pid!r}, method_id={self.method_id!r}, "
                f"median={self.median!r}, mean={self.mean!r}, std={self.std!r}, if_low={self.if_low!r}, "
                f"if_high={self.if_high!r}, trim_mean={self.trim_mean!r}, trim_median={self.trim_median!r}, "
                f"preds={self.preds[0:3]!r}..., last_modified={self.last_modified!r})")

class FirstMotion(Base):
    """First motion information associated with a P pick

    Args:
        Base (_type_): _description_

        id: Not meaningful first motion identifier that is used as the PK.
        pid: Identifer of the Pick the first motion is associated with.
        method_id: Identifier of the FMMethod used.
        clsf: First motion classification, must be "uk" (unknown), "up" or "dn" (down) 
        prob_up: Optional. Probability of the fm being up.
        prob_dn: Optional. Probability of the fm being down.
        preds: Optional. JSON object storing the sampled first motion values.
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """
    __tablename__ = "fm"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(ForeignKey("pick.id"), nullable=False)
    method_id = mapped_column(ForeignKey("fm_method.id"), nullable=False)
    #TODO: Get this constraint to work.. 
    clsf: Mapped[Enum] = mapped_column(Enum('uk', 'up', 'dn', create_constraint=True, name="fm_enum")) #Mapped[FMEnum] = mapped_column(Enum(FMEnum))
    prob_up: Mapped[Optional[float]] = mapped_column(Double)
    prob_dn: Mapped[Optional[float]] = mapped_column(Double)
    preds: Mapped[Optional[JSON]] = mapped_column(JSON)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                default=datetime.now,
                                onupdate=datetime.now)
    
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="fms")
    # Many-to-one relationship with RepickerMethod
    method: Mapped["FMMethod"] = relationship(back_populates="fms")
    

    __table_args__ = (UniqueConstraint(pid, method_id, name="simplify_pk"),
                      CheckConstraint("prob_up >= 0", name="nonneg_prob_up"),
                      CheckConstraint("prob_dn >= 0", name="nonneg_prob_dn"))
    
    def __repr__(self) -> str:
        return (f"FirstMotion(id={self.id!r}, pid={self.pid!r}, method_id={self.method_id!r}, "
                f"clsf={self.clsf!r}, prob_up={self.prob_up!r}, prob_dn={self.prob_dn!r}, "
                f"preds={self.preds[0:3]!r}..., last_modified={self.last_modified!r})")
    
class CredibleInterval(Base):
    """Credible Intervals associated with a pick correction.

    Args:
        Base (_type_): _description_
        
        id: Not meaningful first motion identifier that is used as the PK.
        corr_id: Identifer of the PickCorrection the CI is associated with.
        method_id: Identifier of the CalibratioNMethod used.
        percent: Percentage that the CI represents
        lb: CI lower bound on the pick correction
        ub: CI upper bound on the pick correction
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """
    __tablename__ = "ci"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    corr_id = mapped_column(ForeignKey("pick_corr.id"), nullable=False)
    method_id = mapped_column(ForeignKey("calibration_method.id"), nullable=False)
    percent: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ##
    lb: Mapped[float] = mapped_column(Double)
    ub: Mapped[float] = mapped_column(Double)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)
    
    # Many-to-one relationship with PickCorrection
    corr: Mapped["PickCorrection"] = relationship(back_populates="cis")
    # Many-to-one relationship with CalibrationMethod
    method: Mapped["CalibrationMethod"] = relationship(back_populates="cis")


    __table_args__ = (UniqueConstraint(corr_id, method_id, percent, name="simplify_pk"),
                      CheckConstraint("lb < ub", name="bound_order"),
                      CheckConstraint("percent > 0 AND percent <= 100", name="valid_percent"))
    def __repr__(self) -> str:
        return (f"CredibleInterval(id={self.id!r}, corr_id={self.corr_id!r}, method_id={self.method_id!r}, "
                f"percent={self.percent!r}, lb={self.lb!r}, ub={self.ub!r}, last_modified={self.last_modified!r})")
    
class Gap(Base):
    """Information on gaps in the DailyContinuousData for a Channel. Many small gaps may be represented as one 
    large gap and, if so, avail_sig_sec will be > 0. 

    Args:
        Base (_type_): _description_

        id: Not meaningful gap identifier that is used as the PK.
        data_id: ID of DailyContDataInfo the gap comes from.
        chan_id: ID of the Channel the gap is from. 
        start: Start time of the gap in UTC. Should include fractional seconds.
        end: End time of the gap in UTC. Should include fractional seconds.
        # TODO: Am I going to put entire missing days as a gap?
        startsamp: Optional. Start sample of the gap in the processed DailyContDataInfo (i.e., the Post Probs)
        endsamp: Optional. End sample of the gap in the processed DailyContDataInfo (i.e., the Post Probs)
        avail_sig_sec: If the gap is not continuous, stores the amount of signal (in seconds) that are available.
        last_modified: Automatic field that keeps track of when a row was added to
                        or modified in the database in local time. Does not include microseconds.
    """
    __tablename__ = "gap"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(ForeignKey("contdatainfo.id"), nullable=False)
    chan_id = mapped_column(ForeignKey("channel.id"), nullable=False)
    start: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    ##
    end: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    startsamp: Mapped[Optional[int]] = mapped_column(Integer)
    endsamp: Mapped[Optional[int]] = mapped_column(Integer)
    avail_sig_sec: Mapped[float] = mapped_column(Double, default=0.0)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="gaps")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship(back_populates="gaps")

    __table_args__ = (UniqueConstraint(data_id, chan_id, start, name="simplify_pk"),
                      CheckConstraint("start < end", name="times_order"),
                      CheckConstraint("startsamp >= 0", name="nonneg_startsamp"),
                      CheckConstraint("endsamp >= 1", name="pos_startsamp"),
                      CheckConstraint("startsamp < endsamp", name="samps_order"),
                      CheckConstraint("avail_sig_sec >= 0", name="nonneg_avail_sig"))
    
    def __repr__(self) -> str:
        return (f"Gap(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
                f"start={self.start!r}, end={self.end!r}, startsamp={self.startsamp!r}, "
                f"avail_sig_sec={self.avail_sig_sec!r}, endsamp={self.endsamp!r}, "
                f"last_modified={self.last_modified!r})")
    
class Waveform(Base):
    """Waveform snippet recorded on a Channel, around a Pick, extracted from continuous data described in 
    DailyContDataInfo.

    Args:
        Base (_type_): _description_
        id: Not meaningful waveform identifier that is used as the PK.
        data_id: ID of DailyContDataInfo describing where the waveform was grabbed from.
        chan_id: ID of the Channel recording the waveform. 
        pick_id: ID of the Pick the waveform is centered on. 
        filt_low: Optional. Lower end of the filter applied. 
        filt_high: Optional. Upper end of the filter applied.
        data: Waveform data in some format of path to data...
        start: Start time of the waveform in UTC. Should include fractional seconds.
        end: End time of the waveform in UTC. Should include fractional seconds.
        proc_notes: Optional. Brief notes about waveform processing.
        last_modified: Automatic field that keeps track of when a row was added to
                        or modified in the database in local time. Does not include microseconds.
    """
    __tablename__ = "waveform"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(ForeignKey("contdatainfo.id"), nullable=False)
    chan_id = mapped_column(ForeignKey("channel.id"), nullable=False)
    pick_id = mapped_column(ForeignKey("pick.id"), nullable=False)
    ##
    # TODO: Add more fields to PK if needed (storing processed and unprocessed wfs, diff durations)
    filt_low: Mapped[Optional[float]] = mapped_column(Double)
    filt_high: Mapped[Optional[float]] = mapped_column(Double)
    start: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    end: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False)
    proc_notes: Mapped[Optional[str]] = mapped_column(String(255))
    data = mapped_column(JSON, nullable=False)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(TIMESTAMP,
                                  default=datetime.now,
                                  onupdate=datetime.now)

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="wfs")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship(back_populates="wfs")
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="wfs")

    __table_args__ = (UniqueConstraint(data_id, chan_id, pick_id, name="simplify_pk"),
                      CheckConstraint("filt_low > 0", name="pos_filt_low"), 
                      CheckConstraint("filt_high > 0", name="pos_filt_high"),
                      CheckConstraint("filt_low < filt_high", name="filt_order"),
                      CheckConstraint("start < end", name="times_order"),
                      )
    def __repr__(self) -> str:
        return (f"Waveform(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
                f"pick_id={self.pick_id!r}, filt_low={self.filt_low!r}, filt_high={self.filt_high!r}, "
                f"start={self.start!r}, end={self.end!r}, proc_notes={self.proc_notes!r}, "
                f"data={self.data[0:3]!r}, last_modified={self.last_modified!r})")