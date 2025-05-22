from sqlalchemy import String, Integer, SmallInteger, DateTime, Enum
from sqlalchemy import func, select, text, literal_column, case, null, cast
from sqlalchemy.types import TIMESTAMP, Double, Date, Boolean, JSON, LargeBinary
from sqlalchemy.orm import (
    Mapped,
    WriteOnlyMapped,
    mapped_column,
    relationship,
    column_property,
)
from sqlalchemy.dialects.mysql import DATETIME
from typing import List, Optional
from sqlalchemy.schema import UniqueConstraint, CheckConstraint, ForeignKey
from datetime import datetime
import enum

from seis_proc_db.database import Base
from seis_proc_db.config import MYSQL_ENGINE

MYSQL_DATETIME_FSP = 6


class FMEnum(enum.Enum):
    # Not using this currently, might be useful if I wanted to make directly from 0/1
    """Define ENUM for FirstMotion class"""
    UK = "uk"
    UP = "up"
    DN = "dn"


class ISAMethod(Base):
    """Abstract table from creating IS-A Method tables
    Attributes:
        id: Not meaningful identifier for the method, used as the PK
        name: Name of the method used
        details: Optional. Description of method.
        path: Optional. Path where relevant files for the method are stored.
        last_modified: Automatic field that keeps track of when a method was added to
            or modified in the database in local time. Does not include fractional seconds.
    """

    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    details: Mapped[Optional[str]] = mapped_column(String(1000))
    path: Mapped[Optional[str]] = mapped_column(String(4096))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        UniqueConstraint("name", name="simplify_pk"),
        {"mysql_engine": MYSQL_ENGINE},
    )


class Station(Base):
    """Stores a station's information. Unique station is defined by the net, sta, and
    ondate.

    Attributes:
        id: Not meaningful identifier for the station, used as the PK
        net: Network abbreviation
        sta: Station code
        ondate: The datetime in UTC that the station was turned on. Does not include
            fractional seconds.
        lat: station latitude
        lon: station longitude
        elev: station elevation in m
        offdate: Optional. The datetime in UTC that the station was turned off. Does not
            include fractional seconds.
        last_modified: Automatic field that keeps track of when a station was added to
            or modified in the database in local time. Does not include fractional seconds.
    """

    __tablename__ = "station"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    net: Mapped[str] = mapped_column(String(4), nullable=False)
    sta: Mapped[str] = mapped_column(String(10), nullable=False)
    ondate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ##
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    elev: Mapped[float] = mapped_column(Double)
    offdate: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # define 'last_modified' to use the SQL current_timestamp MySQL function on update
    # last_modified = mapped_column(DateTime, onupdate=func.utc_timestamp())
    # define 'last_updated' to be populated with datetime.now()
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # One-to-Many relationship with Channel
    channels: Mapped[List["Channel"]] = relationship(back_populates="station")
    # One-to-Many relationship with Pick
    picks: WriteOnlyMapped[List["Pick"]] = relationship(back_populates="station")
    # One-to-Many relation with DailyContDataInfo
    contdatainfo: Mapped[List["DailyContDataInfo"]] = relationship(
        back_populates="station"
    )

    __table_args__ = (
        UniqueConstraint(net, sta, ondate, name="simplify_pk"),
        CheckConstraint("lat >= -90 AND lon <= 90", name="valid_lat"),
        CheckConstraint("lon >= -180 AND lon <= 180", name="valid_lon"),
        CheckConstraint("elev >= 0", name="positive_elev"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Station(id={self.id!r}, net={self.net!r}, sta={self.sta!r}, "
            f"ondate={self.ondate!r}, lat={self.lat!r}, lon={self.lon!r}, "
            f"elev={self.elev!r}, offdate={self.offdate!r}, "
            f"last_modified={self.last_modified!r})"
        )


class Channel(Base):
    """Stores a channel's information.

    Attributes:
        id: Not meaningful channel identifier that is used as the PK.
        sta_id: id of a Station
        seed_code: SEED Channel name
        loc: Location code
        ondate: Datetime the channel was turned on in UTC. Does not include frac secs.
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
        offdate: Optional. The datetime the channel was turned off in UTC. Does not
            include fractional seconds.
        overall_gain_vel: Optional. The overall gain of the instrument computed in M/S
        sensor_desc: Optional. The short description of the sensor, usually including the brand.
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "channel"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id: Mapped[int] = mapped_column(
        ForeignKey("station.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    seed_code: Mapped[str] = mapped_column(String(3), nullable=False)
    loc: Mapped[str] = mapped_column(String(2), nullable=False)
    ondate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ##
    samp_rate: Mapped[float] = mapped_column(Double)
    clock_drift: Mapped[float] = mapped_column(Double)
    sensor_desc: Mapped[Optional[str]] = mapped_column(String(100))
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
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ndays = column_property(
        select(
            text(
                "TIMESTAMPDIFF(DAY, channel.ondate, coalesce(channel.offdate, NOW()))"
            ),
        ).scalar_subquery()
    )

    # Many-to-One relation with Station
    station: Mapped["Station"] = relationship(back_populates="channels")
    # One-to-Many relationship with Gaps
    gaps: Mapped[List["Gap"]] = relationship(back_populates="channel")
    # One-to-Many relationship with Waveform
    wfs: WriteOnlyMapped[List["Waveform"]] = relationship(back_populates="channel")
    # One-to-Many relationship with WaveformInfo
    wf_info: WriteOnlyMapped[List["WaveformInfo"]] = relationship(
        back_populates="channel"
    )

    __table_args__ = (
        UniqueConstraint(sta_id, seed_code, loc, ondate, name="simplify_pk"),
        CheckConstraint("samp_rate > 0", name="positive_samp_rate"),
        CheckConstraint("lat >= -90 AND lon <= 90", name="valid_lat"),
        CheckConstraint("lon >= -180 AND lon <= 180", name="valid_lon"),
        CheckConstraint("elev >= 0", name="nonneg_elev"),
        CheckConstraint("azimuth >= 0 AND azimuth <= 360", name="valid_azimuth"),
        CheckConstraint("dip >= -90 AND dip <= 90", name="valid_dip"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Channel(id={self.id!r}, sta_id={self.sta_id!r}, seed_code={self.seed_code!r}, "
            f"loc={self.loc!r}, ondate={self.ondate!r}, samp_rate={self.samp_rate!r}, "
            f"clock_drift={self.clock_drift!r}, sensor_desc={self.sensor_desc!r}, "
            f"sensit_units={self.sensit_units!r}, sensit_freq={self.sensit_freq!r}, "
            f"sensit_val={self.sensit_val!r}, overall_gain_vel={self.overall_gain_vel!r}, "
            f"lat={self.lat!r}, lon={self.lon!r}, elev={self.elev!r}, "
            f"depth={self.depth!r}, azimuth={self.azimuth!r}, dip={self.dip!r}, "
            f"offdate={self.offdate!r}, last_modified={self.last_modified!r})"
        )


class DailyContDataInfo(Base):
    """Keep track of information relating to daily (24 hr) continuous data files used in
    algorithms. This assumes the data has been processed using
    seis_proc_dl.apply_detectors.DataLoader

    Attributes:
        id: Not meaningful identifier that is used as the PK
        sta_id: id of the related Station
        chan_pref: First two letters of the SEED code for the channels used for 3C or all
        three letters for 1C
        ncomps: The number of components used
        date: Date the data was recorded
        samp_rate: Sampling rate of the data (may be different than the Channel samp_rate)
        dt: Sampling interval of the data (should be 1/samp_rate)
        orig_npts: Number of data samples in the file before any processing is done in ApplyDetectors
        orig_start: Starttime (UTC) of the file before any processing is done in ApplyDetectors.
            DOES include fractional seconds.
        orig_end: Endtime (UTC) of the file before any processing is done in ApplyDetectors.
            DOES include fractional seconds.
        proc_npts: Optional. Number of data samples in the file after processing in ApplyDetectors.
            This will be the same for the saved posterior probabilities files.
        proc_start: Optional. Starttime (UTC) of the file after processing in ApplyDetectors.
            This will be the same for the saved posterior probabilities files.
            DOES include fractional seconds.
        proc_end: Optional. Endtime (UTC) of the file after processing in ApplyDetectors.
            This will be the same for the saved posterior probabilities files.
            DOES include fractional seconds.
        prev_appended: Optional. Boolean value that stores whether data from the end of
            the previous day was appended to the start of this file when processing in ApplyDetectors.
        error: Optional. Short error message indicating why this data was not used in ApplyDetectors.
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does NOT include fractional seconds.
    """

    __tablename__ = "contdatainfo"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(
        ForeignKey("station.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    chan_pref: Mapped[str] = mapped_column(String(3), nullable=False)
    ncomps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    date = mapped_column(Date, nullable=False)
    ##
    samp_rate: Mapped[Optional[float]] = mapped_column(Double)
    # TODO: Decide if need to store this...
    dt: Mapped[Optional[float]] = mapped_column(Double)
    # TODO: Decided whether to remove npts
    orig_npts: Mapped[Optional[int]] = mapped_column(Integer)
    orig_start: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP)
    )
    orig_end: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP)
    )
    # TODO: Decide if proc_* values should be stored in a different table
    proc_npts: Mapped[Optional[int]] = mapped_column(Integer)
    proc_start: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP)
    )
    proc_end: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP)
    )
    # TODO: Should this be nullable or have a default value (i.e., 0)
    prev_appended: Mapped[Optional[bool]] = mapped_column(
        Boolean(create_constraint=True, name="prev_app_bool")
    )
    error: Mapped[Optional[str]] = mapped_column(String(50))
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-One relation with Station
    station: Mapped["Station"] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with DLDetection
    dldets: Mapped[List["DLDetection"]] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with Gaps
    gaps: Mapped[List["Gap"]] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with Waveform
    wfs: WriteOnlyMapped[List["Waveform"]] = relationship(back_populates="contdatainfo")
    # One-to-Many relationship with WaveformInfo
    wf_info: WriteOnlyMapped[List["WaveformInfo"]] = relationship(
        back_populates="contdatainfo"
    )
    # One-to-Many relationship with DLDetectorOutput
    dldetector_output: WriteOnlyMapped[List["DLDetectorOutput"]] = relationship(
        back_populates="contdatainfo"
    )

    __table_args__ = (
        UniqueConstraint(sta_id, chan_pref, ncomps, date, name="simplify_pk"),
        CheckConstraint("samp_rate > 0", name="positive_samp_rate"),
        CheckConstraint("dt <= 1", name="dt_lt_1"),
        CheckConstraint("proc_npts >= 1", name="proc_npts_gt_1"),
        CheckConstraint("orig_npts >= 0", name="nonneg_orig_npts"),
        CheckConstraint("proc_end > proc_start", name="valid_proc_times"),
        CheckConstraint("orig_end > orig_start", name="valid_orig_times"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"DailyContDataInfo(id={self.id!r}, sta_id={self.sta_id!r}, "
            f"chan_pref={self.chan_pref!r}, ncomps={self.ncomps!r}, date={self.date!r}, "
            f"samp_rate={self.samp_rate!r}, dt={self.dt!r}, orig_npts={self.orig_npts!r}, "
            f"orig_start={self.orig_start!r}, orig_end={self.orig_end!r}, "
            f"proc_npts={self.proc_npts!r}, proc_start={self.proc_start!r}, "
            f"proc_end={self.proc_end!r}, prev_appended={self.prev_appended!r}, "
            f"error={self.error!r}, last_modified={self.last_modified!r})"
        )


class RepickerMethod(ISAMethod):
    """Stores some info about the type/version of phase repicking model or technique used.
    Inherits from ISAMethod()

    Attributes:
        phase: Optional. Phase type the model was designed for, if applicable.

    """

    __tablename__ = "repicker_method"

    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One-to-Many relationship with PickCorrection
    corrs: Mapped[List["PickCorrection"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
        return (
            f"RepickerMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, last_modified={self.last_modified!r})"
        )


class CalibrationMethod(ISAMethod):
    """Stores some info about the type/version of calibration model or technique used.
    Inherits from ISAMethod

    Attributes:
        phase: Optional. Phase type the model was designed for, if applicable.

    """

    __tablename__ = "calibration_method"

    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
        return (
            f"CalibrationMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, phase={self.phase!r}, last_modified={self.last_modified!r})"
        )


class FMMethod(ISAMethod):
    """Stores some info about the type/version of first motion classifier used.
    Inherits from ISAMethod
    """

    __tablename__ = "fm_method"

    # One-to-Many relationship with FM
    fms: Mapped[List["FirstMotion"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
        return (
            f"FMMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, last_modified={self.last_modified!r})"
        )


class DetectionMethod(ISAMethod):
    """Stores some info about the type/version of phase Detection algorithm used.
    Inherits from ISAMethod

    Attributes:
        phase: Optional. Phase type the model was designed for, if applicable.

    """

    __tablename__ = "detection_method"
    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One to Many relationship with DLDetection
    dldets: WriteOnlyMapped[List["DLDetection"]] = relationship(back_populates="method")
    # One-to-Many relationship with DLDetectorOutput
    dldetector_output: WriteOnlyMapped[List["DLDetectorOutput"]] = relationship(
        back_populates="method"
    )

    def __repr__(self) -> str:
        return (
            f"DetectioNMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, phase={self.phase!r} last_modified={self.last_modified!r})"
        )


class WaveformSource(ISAMethod):
    """Stores some info about the type/version of the source/method for extracting waveform snippets."""

    __tablename__ = "waveform_source"

    # One-to-Many relationship with CredibleIntervals
    wf_info: WriteOnlyMapped[List["WaveformInfo"]] = relationship(
        back_populates="source"
    )

    def __repr__(self) -> str:
        return (
            f"WaveformSource(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, last_modified={self.last_modified!r})"
        )


class DLDetectorOutput(Base):

    __tablename__ = "dldetector_output"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    method_id = mapped_column(
        ForeignKey("detection_method.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    ##
    hdf_file: Mapped[str] = mapped_column(String(255))

    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with ContData
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(
        back_populates="dldetector_output"
    )
    # Many-to-one relationship with DetectionMethod
    method: Mapped["DetectionMethod"] = relationship(back_populates="dldetector_output")
    # one-to-Many relationship with DLDetection
    # TODO: Remove this
    dldets: WriteOnlyMapped[List["DLDetection"]] = relationship(
        back_populates="dldetector_output"
    )

    __table_args__ = (
        UniqueConstraint(data_id, method_id, name="simplify_pk"),
        # CheckConstraint("hdf_index >= 0", name="nonneg_index"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"DLDetectorOutput(id={self.id!r}, hdf_file={self.hdf_file!r}, "
            f"data_id={self.data_id!r}, method_id={self.method_id!r}, "
            f"last_modified={self.last_modified!r})"
        )


class DLDetection(Base):
    """Store Deep-Learning (DL) phase detections from a certain continuous data file
    and detection method.

    Attributes:
        id: Not meaningful detection identifier that is used as the PK.
        data_id: ID of DailyContDataInfo the detection comes from.
        method_id: ID of the DetectionMethod used.
        sample: Sample in the continous data file defined by DailyContDateInfo the
            detection is assigned to. A pick time can be derived for a given detection
            using the sample and DailyContDateInfo.proc_start
        phase: Presumed phase type of the detection.
        width: Width of the spike in the posterior probabilities the detection is associated with.
        height: Posterior probability value at the detection sample. Value is expected to
            be between 1 and 100 (not 0 and 1).
        inference_id: OPTIONAL. The id of the DLDetectorOutput that the detection came from.
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "dldetection"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    method_id = mapped_column(
        ForeignKey("detection_method.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    sample: Mapped[int] = mapped_column(Integer, nullable=False)
    ##
    phase: Mapped[str] = mapped_column(String(4))
    width: Mapped[float] = mapped_column(Double)
    height: Mapped[int] = mapped_column(SmallInteger)
    # TODO: REMOVE this
    inference_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dldetector_output.id"), nullable=True
    )
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with ContData
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="dldets")
    # One-to-one relationship with Pick
    pick: Mapped[Optional["Pick"]] = relationship(back_populates="dldet")
    # Many-to-one relationship with DetectionMethod
    method: Mapped["DetectionMethod"] = relationship(back_populates="dldets")
    # Many-to-one relationship with DLDetectorOutput
    # TODO: Remove this
    dldetector_output: Mapped["DLDetectorOutput"] = relationship(
        back_populates="dldets"
    )

    # column property
    time = column_property(
        select(
            func.date_add(
                DailyContDataInfo.proc_start,
                text("INTERVAL (sample / samp_rate * 1E6) MICROSECOND"),
            )
        )
        .where(DailyContDataInfo.id == data_id)
        .correlate_except(DailyContDataInfo)
        .scalar_subquery()
    )

    __table_args__ = (
        UniqueConstraint(data_id, method_id, sample, name="simplify_pk"),
        CheckConstraint("sample >= 0", name="nonneg_sample"),
        CheckConstraint("width > 0", name="positive_width"),
        CheckConstraint("height > 0 AND height <= 100", name="valid_height"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"DLDetection(id={self.id!r}, data_id={self.data_id!r}, method_id={self.method_id!r}, "
            f"sample={self.sample!r}, phase={self.phase!r}, width={self.width!r}, "
            f"height={self.height!r}, time={self.time!r}, "
            f"inference_id={self.inference_id!r}, last_modified={self.last_modified!r})"
        )


class Pick(Base):
    """Describe a pick, which may be derived from a DLDetection.

    Attributes:
        id: Not meaningful pick identifier that is used as the PK.
        sta_id: Identifier for the Station the pick was made at
        chan_pref: First two letters of the SEED code for the channels used for 3C or all
        three letters for 1C
        phase: Presumed phase type of the pick
        ptime: DateTime of the pick in UTC. DOES include fractional seconds. If a pick
            has a PickCorrection, it is NOT included in the ptime value.
        auth: Short identifier for the author/creator of the pick (i.e., SPDL, UUSS)
        snr: Optional. Single to noise ratio of pick. TODO: Define a clear method for measuring this
        amp: Optional. Amplitude value of pick. TODO: Define a clear method for measuring this
        detid: Optional. Identifier for the DLDetection the pick is derived from
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "pick"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    sta_id = mapped_column(
        ForeignKey("station.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    chan_pref: Mapped[str] = mapped_column(String(3), nullable=False)
    # TODO: Should phase be removed from the PK, in the case it was unknown?
    phase: Mapped[str] = mapped_column(String(4), nullable=False)
    ptime: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    auth: Mapped[str] = mapped_column(String(10), nullable=False)
    ##
    # From waveform info
    snr: Mapped[Optional[float]] = mapped_column(Double)
    amp: Mapped[Optional[float]] = mapped_column(Double)
    # FK from Detections
    detid: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dldetection.id", onupdate="cascade", ondelete="cascade")
    )
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with Station
    station: Mapped["Station"] = relationship(back_populates="picks")
    # One-to-one relationship with Detection
    dldet: Mapped[Optional["DLDetection"]] = relationship(back_populates="pick")
    # One-to-many relationship with PickCorrection
    corrs: Mapped[List["PickCorrection"]] = relationship(back_populates="pick")
    # One-to-many relationship with FM
    fms: Mapped[List["FirstMotion"]] = relationship(back_populates="pick")
    # One-to-many relationship with Waveform
    wfs: WriteOnlyMapped[List["Waveform"]] = relationship(back_populates="pick")
    # One-to-many relationship with WaveformInfo
    wf_info: WriteOnlyMapped[List["WaveformInfo"]] = relationship(back_populates="pick")

    __table_args__ = (
        UniqueConstraint(sta_id, chan_pref, phase, ptime, auth, name="simplify_pk"),
        UniqueConstraint(detid, name="detid"),
        CheckConstraint("amp > 0", name="positive_amp"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Pick(id={self.id!r}, sta_id={self.sta_id!r}, chan_pref={self.chan_pref!r},  "
            f"phase={self.phase!r}, ptime={self.ptime!r},auth={self.auth!r}, snr={self.snr!r}, "
            f"amp={self.amp!r}, det_id={self.detid}, last_modified={self.last_modified!r})"
        )


class PickCorrection(Base):
    """Correction to a Pick to improve the arrival time estimate. Basically assumes some
    sampling method.

    Attributes:
        id: Not meaningful pick correction identifier that is used as the PK.
        pid: Identifer of the Pick the correction is associated with.
        method_id: Identifier of the RepickerMethod used.
        wf_source_id: ID of the WaveformSource describing which data was used in the inference.
        median: Median value of all samples
        mean: Mean value of all samples
        std: Standard deviation of all samples
        if_low: Lower inner fence value for all samples
        if_high: Upper inner fence value for all samples
        trim_median: Median value of samples within the inner fence
        trim_mean: Mean value of samples within the inner fence
        trim_std: Standard deviation within the inner fence
        # preds: JSON object storing the sampled pick correction values
        preds_hdf_file: The name of the hdf file in config.HDF_BASE_PATH/config.HDF_PICKCORR_DIR
            where the predictions are stored
        # preds_hdf_index: The index in the hdf_file where the predictions are stored
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "pick_corr"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(
        ForeignKey("pick.id", onupdate="cascade", ondelete="cascade"), nullable=False
    )
    method_id = mapped_column(
        ForeignKey("repicker_method.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    ##
    wf_source_id = mapped_column(
        ForeignKey("waveform_source.id", onupdate="cascade", ondelete="cascade"),
        nullable=False,
    )
    median: Mapped[float] = mapped_column(Double)
    mean: Mapped[float] = mapped_column(Double)
    std: Mapped[float] = mapped_column(Double)
    if_low: Mapped[float] = mapped_column(Double)
    if_high: Mapped[float] = mapped_column(Double)
    trim_median: Mapped[float] = mapped_column(Double)
    trim_mean: Mapped[float] = mapped_column(Double)
    trim_std: Mapped[float] = mapped_column(Double)
    # preds: Mapped[JSON] = mapped_column(JSON)
    preds_hdf_file: Mapped[str] = mapped_column(String(255))
    # preds_hdf_index: Mapped[int] = mapped_column(Integer)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="corrs")
    # Many-to-one relationship with RepickerMethod
    method: Mapped["RepickerMethod"] = relationship(back_populates="corrs")
    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship(back_populates="corr")

    __table_args__ = (
        UniqueConstraint(pid, method_id, name="simplify_pk"),
        CheckConstraint("if_low < if_high", name="if_order"),
        CheckConstraint("std > 0", name="positive_std"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"PickCorrection(id={self.id!r}, pid={self.pid!r}, method_id={self.method_id!r}, "
            f"median={self.median!r}, mean={self.mean!r}, std={self.std!r}, "
            f"if_low={self.if_low!r}, if_high={self.if_high!r}, trim_mean={self.trim_mean!r}, "
            f"trim_median={self.trim_median!r}, trim_std={self.trim_std!r}, "
            f"preds_hdf_file={self.preds_hdf_file!r}, last_modified={self.last_modified!r})"
        )


class FirstMotion(Base):
    """First motion information associated with a P pick

    Attributes:
        id: Not meaningful first motion identifier that is used as the PK.
        pid: Identifer of the Pick the first motion is associated with.
        method_id: Identifier of the FMMethod used.
        clsf: First motion classification, must be "uk" (unknown), "up" or "dn" (down)
        prob_up: Optional. Probability of the fm being up.
        prob_dn: Optional. Probability of the fm being down.
        # preds: Optional. JSON object storing the sampled first motion values.
        preds_hdf_file: Optional. The name of the hdf file in config.HDF_BASE_PATH/config.HDF_PICKCORR_DIR
            where the predictions are stored
        # preds_hdf_index: Optional. The index in the hdf_file where the predictions are stored
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "fm"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(
        ForeignKey("pick.id", onupdate="cascade", ondelete="cascade"), nullable=False
    )
    method_id = mapped_column(
        ForeignKey("fm_method.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    # TODO: Get this constraint to work..
    clsf: Mapped[Enum] = mapped_column(
        Enum("uk", "up", "dn", create_constraint=True, name="fm_enum")
    )  # Mapped[FMEnum] = mapped_column(Enum(FMEnum))
    prob_up: Mapped[Optional[float]] = mapped_column(Double)
    prob_dn: Mapped[Optional[float]] = mapped_column(Double)
    # preds: Mapped[Optional[JSON]] = mapped_column(JSON)
    preds_hdf_file: Mapped[Optional[str]] = mapped_column(String(255))
    # preds_hdf_index: Mapped[Optional[int]] = mapped_column(Integer)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="fms")
    # Many-to-one relationship with RepickerMethod
    method: Mapped["FMMethod"] = relationship(back_populates="fms")

    __table_args__ = (
        UniqueConstraint(pid, method_id, name="simplify_pk"),
        CheckConstraint("prob_up >= 0", name="nonneg_prob_up"),
        CheckConstraint("prob_dn >= 0", name="nonneg_prob_dn"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"FirstMotion(id={self.id!r}, pid={self.pid!r}, method_id={self.method_id!r}, "
            f"clsf={self.clsf!r}, prob_up={self.prob_up!r}, prob_dn={self.prob_dn!r}, "
            f"preds_hdf_file={self.preds_hdf_file!r},  last_modified={self.last_modified!r})"
        )


class CredibleInterval(Base):
    """Credible Intervals associated with a pick correction.

    Attributes:
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
    corr_id = mapped_column(
        ForeignKey("pick_corr.id", onupdate="cascade", ondelete="cascade"),
        nullable=False,
    )
    method_id = mapped_column(
        ForeignKey("calibration_method.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    percent: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ##
    lb: Mapped[float] = mapped_column(Double)
    ub: Mapped[float] = mapped_column(Double)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with PickCorrection
    corr: Mapped["PickCorrection"] = relationship(back_populates="cis")
    # Many-to-one relationship with CalibrationMethod
    method: Mapped["CalibrationMethod"] = relationship(back_populates="cis")

    __table_args__ = (
        UniqueConstraint(corr_id, method_id, percent, name="simplify_pk"),
        CheckConstraint("lb < ub", name="bound_order"),
        CheckConstraint("percent > 0 AND percent <= 100", name="valid_percent"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"CredibleInterval(id={self.id!r}, corr_id={self.corr_id!r}, "
            f"method_id={self.method_id!r}, percent={self.percent!r}, lb={self.lb!r},"
            f" ub={self.ub!r}, last_modified={self.last_modified!r})"
        )


class Gap(Base):
    """Information on gaps in the DailyContinuousData for a Channel. Many small gaps may
      be represented as one large gap and, if so, avail_sig_sec will be > 0.

    Attributes:
        id: Not meaningful gap identifier that is used as the PK.
        data_id: ID of DailyContDataInfo the gap comes from.
        chan_id: ID of the Channel the gap is from.
        start: Start time of the gap in UTC. Should include fractional seconds.
        end: End time of the gap in UTC. Should include fractional seconds.
        # TODO: Am I going to put entire missing days as a gap?
        #startsamp: Optional. Start sample of the gap in the processed DailyContDataInfo (i.e., Post Probs)
        #endsamp: Optional. End sample of the gap in the processed DailyContDataInfo (i.e., Post Probs)
        avail_sig_sec: If the gap is not continuous, stores the amount of available signal (in seconds)
        last_modified: Automatic field that keeps track of when a row was added to
            or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "gap"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    chan_id = mapped_column(
        ForeignKey("channel.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    start: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    ##
    end: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    # startsamp: Mapped[Optional[int]] = mapped_column(Integer)
    # endsamp: Mapped[Optional[int]] = mapped_column(Integer)
    avail_sig_sec: Mapped[float] = mapped_column(Double, default=0.0)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="gaps")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship(back_populates="gaps")

    # Column property
    # (gap[4] - self.metadata["starttime"]) * self.metadata["sampling_rate"]
    # startsamp = column_property(select(DailyContDataInfo.id))
    startsamp = column_property(
        select(
            (
                func.timestampdiff(
                    literal_column("MICROSECOND"),
                    DailyContDataInfo.proc_start,
                    start,
                )
                / 1e6
            )
            * DailyContDataInfo.samp_rate,
        )
        .where(
            (DailyContDataInfo.id == data_id) & (DailyContDataInfo.proc_start != None)
        )
        .correlate_except(DailyContDataInfo)
        .scalar_subquery()
    )
    endsamp = column_property(
        select(
            (
                func.timestampdiff(
                    literal_column("MICROSECOND"), DailyContDataInfo.proc_start, end
                )
                / 1e6
            )
            * DailyContDataInfo.samp_rate,
        )
        .where(
            (DailyContDataInfo.id == data_id) & (DailyContDataInfo.proc_start != None)
        )
        .correlate_except(DailyContDataInfo)
        .scalar_subquery()
    )

    __table_args__ = (
        UniqueConstraint(data_id, chan_id, start, name="simplify_pk"),
        CheckConstraint("start < end", name="times_order"),
        # CheckConstraint("startsamp >= 0", name="nonneg_startsamp"),
        # CheckConstraint("endsamp >= 1", name="pos_startsamp"),
        # CheckConstraint("startsamp < endsamp", name="samps_order"),
        CheckConstraint("avail_sig_sec >= 0", name="nonneg_avail_sig"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Gap(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
            f"start={self.start!r}, end={self.end!r}, startsamp={self.startsamp!r}, "
            f"avail_sig_sec={self.avail_sig_sec!r}, endsamp={self.endsamp!r}, "
            f"last_modified={self.last_modified!r})"
        )


class WaveformInfo(Base):
    """Waveform snippet recorded on a Channel, around a Pick, and stored in an hdf5 file.
    May be extracted from continuous data described in DailyContDataInfo.

    Attributes:
        Base (_type_): _description_
        id: Not meaningful waveform identifier that is used as the PK.
        chan_id: ID of the Channel recording the waveform.
        pick_id: ID of the Pick the waveform is centered on.
        wf_source_id: ID of the WaveformSource describing where the snippet came from
            or how it was gathered.
        hdf_file: The name of the hdf file in config.HDF_BASE_PATH/config.HDF_WAVEFORM_DIR
            where the waveform is stored
        data_id: Optional. ID of DailyContDataInfo describing where the waveform was grabbed from.
        filt_low: Optional. Lower end of the filter applied.
        filt_high: Optional. Upper end of the filter applied.
        start: Start time of the waveform in UTC. Should include fractional seconds.
        end: End time of the waveform in UTC. Should include fractional seconds.
        min_val: Optional. The minimum value of the waveform snippet stored in the hdf_file.
            Stored for debugging purposes.
        max_val: Optional. The maximum value of the waveform snippet stored in the hdf_file.
            Stored for debugging purposes.
        samp_rate: OPTIONAL. Sampling rate of the data, in case data_id is Null
        proc_notes: Optional. Brief notes about waveform processing.
        last_modified: Automatic field that keeps track of when a row was added to
            or modified in the database in local time. Does not include microseconds.
    """

    # TODO: Update this to include waveform_gather_method
    __tablename__ = "waveform_info"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    chan_id = mapped_column(
        ForeignKey("channel.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    pick_id = mapped_column(
        ForeignKey("pick.id", onupdate="cascade", ondelete="cascade"), nullable=False
    )
    wf_source_id = mapped_column(
        ForeignKey("waveform_source.id", onupdate="cascade", ondelete="cascade"),
        nullable=False,
    )
    ##
    hdf_file: Mapped[str] = mapped_column(String(255))
    data_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="cascade", ondelete="restrict"),
        nullable=True,
    )
    # TODO: Decide if adding filters to PK
    filt_low: Mapped[Optional[float]] = mapped_column(Double)
    filt_high: Mapped[Optional[float]] = mapped_column(Double)
    start: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    end: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    proc_notes: Mapped[Optional[str]] = mapped_column(String(255))
    samp_rate: Mapped[Optional[float]] = mapped_column(Double)
    max_val: Mapped[Optional[float]] = mapped_column(Double)
    min_val: Mapped[Optional[float]] = mapped_column(Double)

    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="wf_info")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship(back_populates="wf_info")
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="wf_info")
    # Many-to-one relationship with WaveformSource
    source: Mapped["WaveformSource"] = relationship(back_populates="wf_info")

    # column propertys
    # pick_index = column_property(
    #     select(
    #         func.round(
    #             (
    #                 func.timestampdiff(literal_column("MICROSECOND"), start, Pick.ptime)
    #                 / 1e6
    #             )
    #             * samp_rate,
    #         )
    #     )
    #     .where(Pick.id == pick_id)
    #     .correlate_except(Pick)
    #     .scalar_subquery()
    # )
    # This is overly complicated because samp_rate is allowed to be null. It would probably
    # be better to just store the samp_rate, regardless of if it attached to the dailycontdatainfo
    # or not...
    pick_index = column_property(
        case(
            # Case 1: data_id is not null → use joined table's samp_rate
            (
                data_id.isnot(None),
                select(
                    cast(
                        func.round(
                            (
                                func.timestampdiff(
                                    literal_column("MICROSECOND"),
                                    start,
                                    Pick.ptime,
                                )
                                / 1e6
                            )
                            * DailyContDataInfo.samp_rate,
                            0,
                        ),
                        Integer,
                    )
                )
                .where((Pick.id == pick_id) & (DailyContDataInfo.id == data_id))
                .correlate_except(Pick, DailyContDataInfo)
                .scalar_subquery(),
            ),
            # Case 2: data_id is null but local samp_rate is not null
            (
                samp_rate.isnot(None),
                select(
                    cast(
                        func.round(
                            (
                                func.timestampdiff(
                                    literal_column("MICROSECOND"), start, Pick.ptime
                                )
                                / 1e6
                            )
                            * samp_rate,
                            0,
                        ),
                        Integer,
                    )
                )
                .where(Pick.id == pick_id)
                .correlate_except(Pick)
                .scalar_subquery(),
            ),
            # Case 3: both are null → return NULL
            else_=null(),
        )
    )
    duration_samples = column_property(
        case(
            # Case 1: data_id is not null → use joined table's samp_rate
            (
                data_id.isnot(None),
                cast(
                    select(
                        (
                            func.timestampdiff(
                                literal_column("MICROSECOND"),
                                start,
                                end,
                            )
                            / 1e6
                        )
                        * DailyContDataInfo.samp_rate
                    )
                    .where(DailyContDataInfo.id == data_id)
                    .correlate_except(DailyContDataInfo)
                    .scalar_subquery(),
                    Integer,
                ),
            ),
            # Case 2: data_id is null but local samp_rate is not null
            (
                samp_rate.isnot(None),
                cast(
                    (
                        func.timestampdiff(
                            literal_column("MICROSECOND"),
                            start,
                            end,
                        )
                        / 1e6
                    )
                    * samp_rate,
                    Integer,
                ),
            ),
            # Case 3: both are null → return NULL
            else_=null(),
        )
    )

    __table_args__ = (
        UniqueConstraint(chan_id, pick_id, wf_source_id, name="simplify_pk"),
        CheckConstraint("filt_low > 0", name="pos_filt_low"),
        CheckConstraint("filt_high > 0", name="pos_filt_high"),
        CheckConstraint("filt_low < filt_high", name="filt_order"),
        CheckConstraint("start < end", name="times_order"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Waveform(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
            f"pick_id={self.pick_id!r}, filt_low={self.filt_low!r}, filt_high={self.filt_high!r}, "
            f"start={self.start!r}, end={self.end!r}, proc_notes={self.proc_notes!r}, "
            f"samp_rate={self.samp_rate!r}, min_val={self.min_val!r}, max_val={self.max_val!r}, "
            f"hdf_file={self.hdf_file!r}, last_modified={self.last_modified!r})"
        )


class Waveform(Base):
    """Waveform snippet recorded on a Channel, around a Pick, extracted from continuous
    data described in DailyContDataInfo.

    Attributes:
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
    data_id = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    chan_id = mapped_column(
        ForeignKey("channel.id", onupdate="cascade", ondelete="restrict"),
        nullable=False,
    )
    pick_id = mapped_column(
        ForeignKey("pick.id", onupdate="cascade", ondelete="cascade"), nullable=False
    )
    ##
    # TODO: Add more fields to PK if needed (storing processed and unprocessed wfs, diff durations)
    filt_low: Mapped[Optional[float]] = mapped_column(Double)
    filt_high: Mapped[Optional[float]] = mapped_column(Double)
    start: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    end: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    proc_notes: Mapped[Optional[str]] = mapped_column(String(255))
    data = mapped_column(JSON, nullable=False)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Many-to-one relationship with DailyContDataInfo
    contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="wfs")
    # Many-to-one relationship with Channel
    channel: Mapped["Channel"] = relationship(back_populates="wfs")
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="wfs")

    __table_args__ = (
        UniqueConstraint(data_id, chan_id, pick_id, name="simplify_pk"),
        CheckConstraint("filt_low > 0", name="pos_filt_low"),
        CheckConstraint("filt_high > 0", name="pos_filt_high"),
        CheckConstraint("filt_low < filt_high", name="filt_order"),
        CheckConstraint("start < end", name="times_order"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Waveform(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
            f"pick_id={self.pick_id!r}, filt_low={self.filt_low!r}, filt_high={self.filt_high!r}, "
            f"start={self.start!r}, end={self.end!r}, proc_notes={self.proc_notes!r}, "
            f"data={self.data[0:3]!r}, last_modified={self.last_modified!r})"
        )


# class WaveformBLOB(Base):
#     """Waveform snippet recorded on a Channel, around a Pick, extracted from continuous
#     data described in DailyContDataInfo.

#     Attributes:
#         Base (_type_): _description_
#         id: Not meaningful waveform identifier that is used as the PK.
#         data_id: ID of DailyContDataInfo describing where the waveform was grabbed from.
#         chan_id: ID of the Channel recording the waveform.
#         pick_id: ID of the Pick the waveform is centered on.
#         filt_low: Optional. Lower end of the filter applied.
#         filt_high: Optional. Upper end of the filter applied.
#         data: Waveform data in some format of path to data...
#         start: Start time of the waveform in UTC. Should include fractional seconds.
#         end: End time of the waveform in UTC. Should include fractional seconds.
#         proc_notes: Optional. Brief notes about waveform processing.
#         last_modified: Automatic field that keeps track of when a row was added to
#             or modified in the database in local time. Does not include microseconds.
#     """

#     __tablename__ = "waveform_blob"
#     id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
#     ## PK (not simplified)
#     data_id = mapped_column(
#         ForeignKey("contdatainfo.id", onupdate="cascade", ondelete="restrict"),
#         nullable=False,
#     )
#     chan_id = mapped_column(
#         ForeignKey("channel.id", onupdate="cascade", ondelete="restrict"),
#         nullable=False,
#     )
#     pick_id = mapped_column(
#         ForeignKey("pick.id", onupdate="cascade", ondelete="cascade"), nullable=False
#     )
#     ##
#     # TODO: Add more fields to PK if needed (storing processed and unprocessed wfs, diff durations)
#     filt_low: Mapped[Optional[float]] = mapped_column(Double)
#     filt_high: Mapped[Optional[float]] = mapped_column(Double)
#     start: Mapped[datetime] = mapped_column(
#         DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
#     )
#     end: Mapped[datetime] = mapped_column(
#         DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
#     )
#     proc_notes: Mapped[Optional[str]] = mapped_column(String(255))
#     data: Mapped[LargeBinary] = mapped_column(LargeBinary, nullable=False)
#     # Keep track of when the row was inserted/updated
#     last_modified: Mapped[TIMESTAMP] = mapped_column(
#         TIMESTAMP,
#         default=datetime.now,
#         onupdate=datetime.now,
#         server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
#     )

#     # # Many-to-one relationship with DailyContDataInfo
#     # contdatainfo: Mapped["DailyContDataInfo"] = relationship(back_populates="wfs")
#     # # Many-to-one relationship with Channel
#     # channel: Mapped["Channel"] = relationship(back_populates="wfs")
#     # # Many-to-one relationship with Pick
#     # pick: Mapped["Pick"] = relationship(back_populates="wfs")

#     __table_args__ = (
#         UniqueConstraint(data_id, chan_id, pick_id, name="simplify_pk"),
#         CheckConstraint("filt_low > 0", name="pos_filt_low"),
#         CheckConstraint("filt_high > 0", name="pos_filt_high"),
#         CheckConstraint("filt_low < filt_high", name="filt_order"),
#         CheckConstraint("start < end", name="times_order"),
#         {"mysql_engine": MYSQL_ENGINE},
#     )

#     def __repr__(self) -> str:
#         return (
#             f"Waveform(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
#             f"pick_id={self.pick_id!r}, filt_low={self.filt_low!r}, filt_high={self.filt_high!r}, "
#             f"start={self.start!r}, end={self.end!r}, proc_notes={self.proc_notes!r}, "
#             f"data={self.data[0:3]!r}, last_modified={self.last_modified!r})"
#         )
