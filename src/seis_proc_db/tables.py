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
        ForeignKey("station.id", onupdate="restrict", ondelete="restrict"),
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
        ForeignKey("station.id", onupdate="restrict", ondelete="restrict"),
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
        loc_type: Optional. Indicates what value is used for the "center" of the distribution
            (i.e., mean) when computing the percent point function (ppf).
        scale_type: Optional. Indicates what value is used for the "spread" of the distribution
            (i.e., std. dev.) when computing the ppf.

    """

    __tablename__ = "calibration_method"

    phase: Mapped[Optional[str]] = mapped_column(String(4))
    loc_type: Mapped[Optional[str]] = mapped_column(String(50))
    scale_type: Mapped[Optional[str]] = mapped_column(String(50))

    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
        return (
            f"CalibrationMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, phase={self.phase!r}, loc_type={self.loc_type!r}, "
            f"scale_type={self.scale_type!r}, last_modified={self.last_modified!r})"
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
    """Stores some info about the type/version of the source/method for gathering waveform snippets
    and any processing that was used.

    Attributes:
        filt_low: Optional. Lower end of the filter applied.
        filt_high: Optional. Upper end of the filter applied.
        detrend: Optional. Type of detrend that was applied (e.g., demean, linear, simple)
        normalize: Optional. How the trace was normalized.
        common_samp_rate: Optional. Sampling rate that all traces are resampled to, if necessary.
    """

    __tablename__ = "waveform_source"

    filt_low: Mapped[Optional[float]] = mapped_column(Double)
    filt_high: Mapped[Optional[float]] = mapped_column(Double)
    detrend: Mapped[Optional[str]] = mapped_column(String(15))
    normalize: Mapped[Optional[str]] = mapped_column(String(50))
    common_samp_rate: Mapped[Optional[float]] = mapped_column(Double)

    # One-to-Many relationship with CredibleIntervals
    wf_info: WriteOnlyMapped[List["WaveformInfo"]] = relationship(
        back_populates="source"
    )
    # One-to-Many relationship with CredibleIntervals
    wfs: WriteOnlyMapped[List["Waveform"]] = relationship(back_populates="source")
    # One-to-Many relationship with CredibleIntervals
    corrs: WriteOnlyMapped[List["PickCorrection"]] = relationship(
        back_populates="source"
    )

    __table_args__ = (
        UniqueConstraint("name", name="simplify_pk"),
        CheckConstraint("filt_low > 0", name="pos_filt_low"),
        CheckConstraint("filt_high > 0", name="pos_filt_high"),
        CheckConstraint("filt_low < filt_high", name="filt_order"),
        CheckConstraint("common_samp_rate > 0", name="pos_common_samp_rate"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"WaveformSource(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"filt_low={self.filt_low!r}, filt_high={self.filt_high!r}, detrend={self.detrend!r}, "
            f"normalize={self.normalize!r}, common_samp_rate={self.common_samp_rate!r}, "
            f"path={self.path!r}, last_modified={self.last_modified!r})"
        )


class DLDetectorOutput(Base):

    __tablename__ = "dldetector_output"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    data_id = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    method_id = mapped_column(
        ForeignKey("detection_method.id", onupdate="restrict", ondelete="restrict"),
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
        ForeignKey("contdatainfo.id", onupdate="restrict", ondelete="cascade"),
        nullable=False,
    )
    method_id = mapped_column(
        ForeignKey("detection_method.id", onupdate="restrict", ondelete="restrict"),
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
        ForeignKey("station.id", onupdate="restrict", ondelete="restrict"),
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
        ForeignKey("dldetection.id", onupdate="restrict", ondelete="cascade")
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
    # One-to-many relationship with AssocArrival
    assoc_arrs: WriteOnlyMapped[List["AssocArrival"]] = relationship(
        back_populates="pick"
    )

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

class CorrStorageFile(Base):
    __tablename__ = "corr_stor_file"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    name: Mapped[str] = mapped_column(String(255))
    ##
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Man-to-one relationship with WaveformInfo
    corrs: WriteOnlyMapped[List["PickCorrection"]] = relationship(
        back_populates="preds_hdf_file"
    )

    __table_args__ = (
        UniqueConstraint(name, name="simplify_pk"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"CorrStorageFile(id={self.id!r}, "
            f"name={self.name!r}, last_modified={self.last_modified!r})"
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
        # preds_hdf_file: The name of the hdf file in config.HDF_BASE_PATH/config.HDF_PICKCORR_DIR
        #     where the predictions are stored
        preds_file_id: ID of the CorrStorageFile with the name of the hdf file in 
            config.HDF_BASE_PATH/config.HDF_PICKCORR_DIR where the predictions are stored
        # preds_hdf_index: The index in the hdf_file where the predictions are stored
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "pick_corr"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(
        ForeignKey("pick.id", onupdate="restrict", ondelete="cascade"), nullable=False
    )
    method_id = mapped_column(
        ForeignKey("repicker_method.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    ##
    # Store the waveform_source to be able to identify which data is being read into the
    # model because a pick can have multiple waveforms (e.g., one extracted from contdata
    # and one downloaded separatley because the pick is near the end/start of a day)
    # Don't store waveform_info_id because the S picker uses 3 waveforms
    wf_source_id = mapped_column(
        ForeignKey("waveform_source.id", onupdate="restrict", ondelete="restrict"),
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
    # preds_hdf_file: Mapped[str] = mapped_column(String(255))
    preds_file_id: Mapped[int] = mapped_column(
        ForeignKey("corr_stor_file.id", onupdate="restrict", ondelete="cascade"),
        nullable=False,
    )
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
    # Many-to-one relationship with WaveformSource
    source: Mapped["WaveformSource"] = relationship(back_populates="corrs")
    # Many-to-one relationship with CorrStorageFile
    preds_hdf_file: Mapped["CorrStorageFile"] = relationship(back_populates="corrs")
    # One-to-Many relationship with CredibleIntervals
    cis: Mapped[List["CredibleInterval"]] = relationship(back_populates="corr")
    # One-to-many relationship with ManualPickQuality
    quals: Mapped[List["ManualPickQuality"]] = relationship(
            back_populates="corr"
        )


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


class FMStorageFile(Base):
    __tablename__ = "fm_stor_file"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    name: Mapped[str] = mapped_column(String(255))
    ##
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # Man-to-one relationship with WaveformInfo
    fms: WriteOnlyMapped[List["FirstMotion"]] = relationship(
        back_populates="preds_hdf_file"
    )

    __table_args__ = (
        UniqueConstraint(name, name="simplify_pk"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"FMStorageFile(id={self.id!r}, "
            f"name={self.name!r}, last_modified={self.last_modified!r})")

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
        # preds_hdf_file: Optional. The name of the hdf file in config.HDF_BASE_PATH/config.HDF_FM_DIR
        #     where the predictions are stored
        preds_file_id: ID of the FMStorageFile with the name of the hdf file in 
            config.HDF_BASE_PATH/config.HDF_FM_DIR where the predictions are stored
        # preds_hdf_index: Optional. The index in the hdf_file where the predictions are stored
        last_modified: Automatic field that keeps track of when a row was added to
                or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "fm"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    pid = mapped_column(
        ForeignKey("pick.id", onupdate="restrict", ondelete="cascade"), nullable=False
    )
    method_id = mapped_column(
        ForeignKey("fm_method.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    # TODO: Get this constraint to work..
    clsf: Mapped[Enum] = mapped_column(
        Enum("uk", "up", "dn", create_constraint=True, name="fm_enum")
    )  # Mapped[FMEnum] = mapped_column(Enum(FMEnum))
    prob_up: Mapped[Optional[float]] = mapped_column(Double)
    prob_dn: Mapped[Optional[float]] = mapped_column(Double)
    # preds: Mapped[Optional[JSON]] = mapped_column(JSON)
    #preds_hdf_file: Mapped[Optional[str]] = mapped_column(String(255))
    preds_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fm_stor_file.id", onupdate="restrict", ondelete="cascade"),
        nullable=True,
    )
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
    # Many-to-one relationship with FMStorageFile
    preds_hdf_file: Mapped["FMStorageFile"] = relationship(back_populates="fms")

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
    """Credible Intervals associated with a pick correction. Since the CI are for the pick
    corrections, they should be added to the pick time to get the lower bound and upper
    bound of the arrival time.

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
        ForeignKey("pick_corr.id", onupdate="restrict", ondelete="cascade"),
        nullable=False,
    )
    method_id = mapped_column(
        ForeignKey("calibration_method.id", onupdate="restrict", ondelete="restrict"),
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
    # One-to-many relationship with AssocArrival
    assoc_arrs: WriteOnlyMapped[List["AssocArrival"]] = relationship(
        back_populates="ci"
    )

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
        ForeignKey("contdatainfo.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    chan_id = mapped_column(
        ForeignKey("channel.id", onupdate="restrict", ondelete="restrict"),
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

class WaveformStorageFile(Base):
    __tablename__ = "wf_stor_file"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    name: Mapped[str] = mapped_column(String(255))
    ##
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # One-to-many relationship with WaveformInfo
    wf_info: WriteOnlyMapped[List["WaveformInfo"]]= relationship(
        back_populates="hdf_file"
    )

    __table_args__ = (
        UniqueConstraint(name, name="simplify_pk"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"WaveformStorageFile(id={self.id!r}, "
            f"name={self.name!r}, last_modified={self.last_modified!r})"
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
        # hdf_file: The name of the hdf file in config.HDF_BASE_PATH/config.HDF_WAVEFORM_DIR
        #     where the waveform is stored
        hdf_file_id: ID of the WaveformStorageFile with the name of the hdf file in 
            config.HDF_BASE_PATH/config.HDF_WAVEFORM_DIR where the waveform is stored
        data_id: Optional. ID of DailyContDataInfo describing where the waveform was grabbed from.
        #filt_low: Optional. Lower end of the filter applied.
        #filt_high: Optional. Upper end of the filter applied.
        start: Start time of the waveform in UTC. Should include fractional seconds.
        end: End time of the waveform in UTC. Should include fractional seconds.
        min_val: Optional. The minimum value of the waveform snippet stored in the hdf_file.
            Stored for debugging purposes.
        max_val: Optional. The maximum value of the waveform snippet stored in the hdf_file.
            Stored for debugging purposes.
        samp_rate: OPTIONAL. Sampling rate of the data, in case data_id is Null
        #proc_notes: Optional. Brief notes about waveform processing.
        last_modified: Automatic field that keeps track of when a row was added to
            or modified in the database in local time. Does not include microseconds.
    """

    # TODO: Update this to include waveform_gather_method
    __tablename__ = "waveform_info"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    chan_id = mapped_column(
        ForeignKey("channel.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    pick_id = mapped_column(
        ForeignKey("pick.id", onupdate="restrict", ondelete="cascade"), nullable=False
    )
    wf_source_id = mapped_column(
        ForeignKey("waveform_source.id", onupdate="restrict", ondelete="cascade"),
        nullable=False,
    )
    ##
    # hdf_file: Mapped[str] = mapped_column(String(255))
    hdf_file_id: Mapped[int] = mapped_column(
        ForeignKey("wf_stor_file.id", onupdate="restrict", ondelete="cascade"), nullable=False
    )
    
    data_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="restrict", ondelete="restrict"),
        nullable=True,
    )
    # filt_low: Mapped[Optional[float]] = mapped_column(Double)
    # filt_high: Mapped[Optional[float]] = mapped_column(Double)
    start: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    end: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    # proc_notes: Mapped[Optional[str]] = mapped_column(String(255))
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
    # Many-to-one relationship with WaveformStorageFile
    hdf_file: Mapped["WaveformStorageFile"] = relationship(back_populates="wf_info")
    # One-to-many relationship with ArrWaveformFeat
    arr_wf_feats: WriteOnlyMapped[List["ArrWaveformFeat"]] = relationship(
        back_populates="wf_info"
    )

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
        # CheckConstraint("filt_low > 0", name="pos_filt_low"),
        # CheckConstraint("filt_high > 0", name="pos_filt_high"),
        # CheckConstraint("filt_low < filt_high", name="filt_order"),
        CheckConstraint("start < end", name="times_order"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"WaveformInfo(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
            f"pick_id={self.pick_id!r}, start={self.start!r}, end={self.end!r},"
            # f"filt_low={self.filt_low!r}, filt_high={self.filt_high!r}, proc_notes={self.proc_notes!r}, "
            f"samp_rate={self.samp_rate!r}, min_val={self.min_val!r}, max_val={self.max_val!r}, "
            f"hdf_file_id={self.hdf_file_id!r}, last_modified={self.last_modified!r})"
        )


class Waveform(Base):
    """Waveform snippet recorded on a Channel, around a Pick, extracted from continuous
    data described in DailyContDataInfo.

    Attributes:
        Base (_type_): _description_
        id: Not meaningful waveform identifier that is used as the PK.
        chan_id: ID of the Channel recording the waveform.
        pick_id: ID of the Pick the waveform is centered on.
        wf_source_id: ID of the WaveformSource describing where the snippet came from
            or how it was gathered.
        data: Waveform data in some format of path to data...
        start: Start time of the waveform in UTC. Should include fractional seconds.
        end: End time of the waveform in UTC. Should include fractional seconds.
        data_id: Optional. ID of DailyContDataInfo describing where the waveform was grabbed from.
        last_modified: Automatic field that keeps track of when a row was added to
            or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "waveform"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    chan_id = mapped_column(
        ForeignKey("channel.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    pick_id = mapped_column(
        ForeignKey("pick.id", onupdate="restrict", ondelete="cascade"), nullable=False
    )
    wf_source_id = mapped_column(
        ForeignKey("waveform_source.id", onupdate="restrict", ondelete="cascade"),
        nullable=False,
    )
    ##
    data_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contdatainfo.id", onupdate="restrict", ondelete="restrict"),
        nullable=True,
    )
    start: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
    end: Mapped[datetime] = mapped_column(
        DATETIME(fsp=MYSQL_DATETIME_FSP), nullable=False
    )
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
    # Many-to-one relationship with WaveformSource
    source: Mapped["WaveformSource"] = relationship(back_populates="wfs")

    __table_args__ = (
        UniqueConstraint(chan_id, pick_id, wf_source_id, name="simplify_pk"),
        CheckConstraint("start < end", name="times_order"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Waveform(id={self.id!r}, data_id={self.data_id!r}, chan_id={self.chan_id!r}, "
            f"wf_source_id={self.wf_source_id!r}, pick_id={self.pick_id!r}, start={self.start!r}, "
            f"end={self.end!r}, data={self.data[0:3]!r}, last_modified={self.last_modified!r})"
        )


class ManualPickQuality(Base):
    __tablename__ = "man_pick_qual"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## PK (not simplified)
    # pick_id = mapped_column(
    #     ForeignKey("pick.id", onupdate="restrict", ondelete="cascade"),
    #     nullable=False,
    # )
    corr_id = mapped_column(
        ForeignKey("pick_corr.id", onupdate="restrict", ondelete="cascade"),
        nullable=False,
    )    
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    ##
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    pick_cat: Mapped[Optional[str]] = mapped_column(String(50))
    # det_cat: Mapped[Optional[str]] = mapped_column(String(50))
    # corr_cat: Mapped[Optional[str]] = mapped_column(String(50))
    ci_cat: Mapped[Optional[str]] = mapped_column(String(50))
    note: Mapped[Optional[str]] = mapped_column(String(1000))

    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    # # Many-to-one relationship with Pick
    # pick: Mapped["Pick"] = relationship(
    #     back_populates="quality"
    # )
    # Many-to-one relationship with PickCorrection
    corr: Mapped["PickCorrection"] = relationship(back_populates="quals")


    __table_args__ = (
        UniqueConstraint(corr_id, auth, name="simplify_pk"),
        # CheckConstraint("hdf_index >= 0", name="nonneg_index"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"ManualPickQuality(id={self.id!r}, corr_id={self.corr_id!r}, auth={self.auth!r}, "
            f"quality={self.quality}, note={self.note!r}, pick_cat={self.pick_cat}, "
            f"ci_cat={self.ci_cat}, last_modified={self.last_modified!r})"
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

## TABLES BELOW THIS POINT ARE A WORK IN PROGRESS ##


class AssocMethod(ISAMethod):
    __tablename__ = "assoc_method"

    # One-to-Many relationship with PickCorrection
    origins: WriteOnlyMapped[List["Origin"]] = relationship(
        back_populates="assoc_method"
    )

    def __repr__(self) -> str:
        return (
            f"AssocMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, last_modified={self.last_modified!r})"
        )


class LocMethod(ISAMethod):
    __tablename__ = "loc_method"

    # One-to-Many relationship with PickCorrection
    origins: WriteOnlyMapped[List["Origin"]] = relationship(back_populates="loc_method")

    def __repr__(self) -> str:
        return (
            f"LocMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, last_modified={self.last_modified!r})"
        )


class VelModel(ISAMethod):
    __tablename__ = "vel_model"

    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One-to-Many relationship with PickCorrection
    origins: WriteOnlyMapped[List["Origin"]] = relationship(back_populates="vel_model")

    def __repr__(self) -> str:
        return (
            f"VelModel(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, phase={self.phase}, last_modified={self.last_modified!r})"
        )


class MagMethod(ISAMethod):
    __tablename__ = "mag_method"

    phase: Mapped[Optional[str]] = mapped_column(String(4))

    # One-to-Many relationship with ArrMag
    arr_mags: WriteOnlyMapped[List["ArrMag"]] = relationship(back_populates="method")

    def __repr__(self) -> str:
        return (
            f"MagMethod(id={self.id!r}, name={self.name!r}, details={self.details!r}, "
            f"path={self.path!r}, phase={self.phase}, last_modified={self.last_modified!r})"
        )


class Event(Base):
    """Defines an event... This table is still a work in progress.

    Attributes:
        id: Unique identifier.
        last_modified: Automatic field that keeps track of when a row was added to
             or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "event"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    # TODO: Figure out if this needs any more parameters and if I am going to store
    # preferred information
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ## Relationships
    # One-to-Many relationship with Origin
    origins: Mapped[List["Origin"]] = relationship(back_populates="event")

    __table_args__ = ({"mysql_engine": MYSQL_ENGINE},)

    def __repr__(self) -> str:
        return f"Event(id={self.id!r}, last_modified={self.last_modified!r})"


class Origin(Base):
    """An event origin. This table is still a work in progress.

    Args:
        Base (_type_): _description_
        id: Unique identifier
        evid: ID of the event the origin belongs to
        assocm_id: ID of the association method used
        locm_id: ID of the location method used
        velm_id: ID of the velocity model used
        lat: Latitude
        lon: Longitude
        depth: Depth in km (relative to ?)
        ot: Origin Time
        rms: Root mean square error
        errh: Horizontal location error
        errz: Vertical location error
        gap: The maximum gap between stations used in the location
        narrs: The number of arrivals used
        quality: The orign quality
        min_dist: Distance (km) from the epicenter to the closest station with a phase arrival
        last_modified: Automatic field that keeps track of when a row was added to
             or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "origin"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## Primary Key without simplification
    evid: Mapped[int] = mapped_column(
        ForeignKey("event.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    assocm_id: Mapped[int] = mapped_column(
        ForeignKey("assoc_method.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    locm_id: Mapped[int] = mapped_column(
        ForeignKey("loc_method.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    velm_id: Mapped[int] = mapped_column(
        ForeignKey("vel_model.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    ##
    # Define location
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    depth: Mapped[float] = mapped_column(Double)
    ot: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP))
    # Location quality info
    rms: Mapped[float] = mapped_column(Double)
    errh: Mapped[float] = mapped_column(Double)
    errz: Mapped[float] = mapped_column(Double)
    gap: Mapped[float] = mapped_column(Double)
    narrs: Mapped[int] = mapped_column(Integer)
    quality: Mapped[float] = mapped_column(Double)
    min_dist: Mapped[float] = mapped_column(Double)

    # TODO: Figure out what other information needs to be stored

    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ## Relationships
    # Many-to-one relationship with Event
    event: Mapped["Event"] = relationship(back_populates="origins")
    # Many-to-one relationship with AssocMethod
    assoc_method: Mapped["AssocMethod"] = relationship(back_populates="origins")
    # Many-to-one relationship with LocMethod
    loc_method: Mapped["LocMethod"] = relationship(back_populates="origins")
    # Many-to-one relationship with WaveformSource
    vel_model: Mapped["VelModel"] = relationship(back_populates="origins")
    # One-to-Many relationship with AssocArrival
    assoc_arrs: Mapped[List["AssocArrival"]] = relationship(back_populates="origin")
    # One-to-Many relationship with NetMag
    netmags: Mapped[List["NetMag"]] = relationship(back_populates="origin")

    __table_args__ = (
        UniqueConstraint(evid, assocm_id, locm_id, velm_id, name="simplify_pk"),
        CheckConstraint("depth >= -10.0 and depth <= 1000.0", name="valid_depth"),
        CheckConstraint("rms >= 0.0", name="nonneg_rms"),
        CheckConstraint("errh >= 0.0", name="nonneg_errh"),
        CheckConstraint("errz >= 0.0", name="nonneg_errz"),
        CheckConstraint("gap >= 0.0 and gap <= 360.0", name="valid_gap"),
        CheckConstraint("narrs >= 0", name="nonneg_narrs"),
        CheckConstraint("quality >= 0.0 and quality <= 1.0", name="valid_quality"),
        CheckConstraint("min_dist >= 0.0", name="nonneg_min_dist"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"Origin(id={self.id!r}, evid={self.evid}, assocm_id={self.assocm_id}, "
            f"locm_id={self.locm_id}, velm_id={self.velm_id}, lat={self.lat}, "
            f"lon={self.lon}, depth={self.depth}, ot={self.ot!r}, rms={self.rms}, "
            f"errh={self.errh}, errz={self.errz}, gap={self.gap}, narrs={self.narrs}, "
            f"min_dist={self.min_dist}, quality={self.quality}, last_modified={self.last_modified!r})"
        )


class AssocArrival(Base):
    """Stores picks that have been associated into an event. I'll call picks that have been
    associated an arrival. This table is still a work in progress.

    Attributes:
        id: Unique identifier
        orid: ID of the origin the arrival is associated with
        pick_id: ID of the pick that has been associated
        ci_id: Optional. ID of the credible interval used. Table currently assumes that
            if a pick_corr is used, it will always be used along with a ci
        arrtime: Arrival time used in the association
        at_uncert_lb: Uncertainty (in seconds) of the arrival time to be earlier
        at_uncert_ub: Uncertainty (in seconds) of the arrival time to be later
        aphase: Optional. Phase assigned to the arrival after association, if association
            can change the phase hint
        weight: Weight of the arrival in association
        importance: Importance of the arrival in association. Between 0 and 1.
        delta:  Residual (in seconds) of the actual and theoretical arrival time
        slowness: Slowness (in s/km) of the arrival between the origin epicenter and
            station recoring the arrival. Absolute value of the slowness vector.
        azimuth: Azimuth (in deg) between the epicenter and the station recording the
             arrival. Measured clock-wise between north and the direction towards the station
        sr_distance: Distance (in km) between the station recording the arrival and the
            epicenter
        last_modified: Automatic field that keeps track of when a row was added to
             or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "assoc_arr"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## Primary Key without simplification
    # The origin has the association method info
    orid: Mapped[int] = mapped_column(
        ForeignKey("origin.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    pick_id: Mapped[int] = mapped_column(
        ForeignKey("pick.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    ##

    # Since this is tied to the pick_corr and the cal_method specifies the loc_type,
    # I can get the pick correction info from this.
    # TODO: What if just the pick corr is used and no ci?
    ci_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ci.id", onupdate="restrict", ondelete="restrict"),
        nullable=True,
    )

    # TODO: Decide if a good idea to store these. Thinking YES in case the pick_corr
    # or CI are updated. This wouldn't be great so maybe I should manually enforce that...
    # Could be also be useful if setting a min/max uncert value, but that could also be
    # stored in the assoc method
    arrtime: Mapped[datetime] = mapped_column(DATETIME(fsp=MYSQL_DATETIME_FSP))
    at_uncert_lb: Mapped[float] = mapped_column(Double)
    at_uncert_ub: Mapped[float] = mapped_column(Double)

    # TODO: Adjust/add params after figure out what comes out of massociate
    aphase: Mapped[Optional[str]] = mapped_column(String(4))
    weight: Mapped[float] = mapped_column(Double)
    importance: Mapped[float] = mapped_column(Double)
    delta: Mapped[float] = mapped_column(Double)

    # TODO: Should these be in this table?
    slowness: Mapped[float] = mapped_column(Double)
    azimuth: Mapped[float] = mapped_column(Double)
    sr_dist: Mapped[float] = mapped_column(Double)

    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ## Relationships
    # Many-to-one relationship with Origin
    origin: Mapped["Origin"] = relationship(back_populates="assoc_arrs")
    # Many-to-one relationship with Pick
    pick: Mapped["Pick"] = relationship(back_populates="assoc_arrs")
    # Many-to-one relationship with Origin
    ci: Mapped["CredibleInterval"] = relationship(back_populates="assoc_arrs")
    # One-to-many relationship with AssocArrival
    arr_mags: Mapped[List["ArrMag"]] = relationship(back_populates="arr")
    # One-to-Many relationship with ArrWaveformFeat
    wf_feats: WriteOnlyMapped[List["ArrWaveformFeat"]] = relationship(
        back_populates="arr"
    )

    __table_args__ = (
        UniqueConstraint(orid, pick_id, name="simplify_pk"),
        CheckConstraint("at_uncert_lb < 0.0", name="neg_at_uncert_lb"),
        CheckConstraint("at_uncert_ub > 0.0", name="pos_at_uncert_ub"),
        CheckConstraint("weight >= 0.0", name="nonneg_weight"),
        CheckConstraint(
            "importance >= 0.0 and importance <= 1.0", name="valid_importance"
        ),
        CheckConstraint("delta >= 0.0", name="nonneg_delta"),
        CheckConstraint("slowness >= 0.0", name="nonneg_slowness"),
        CheckConstraint("azimuth >= 0.0 and azimuth <= 360.0", name="valid_azimuth"),
        CheckConstraint("sr_dist >= 0", name="nonneg_sr_dist"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"AssocArrival(id={self.id!r}, orid={self.orid}, pick_id={self.pick_id}, "
            f"ci_id={self.ci_id}, arrtime={self.arrtime!r}, at_uncert_lb={self.at_uncert_lb}, "
            f"at_uncert_ub={self.at_uncert_ub}, aphase={self.aphase}, weight={self.weight}, "
            f"importance={self.importance}, delta={self.delta}, slowness={self.slowness}, "
            f"azimuth={self.azimuth}, sr_dist={self.sr_dist}, last_modified={self.last_modified!r})"
        )


class ArrMag(Base):
    """Stores magnitude estimates based off an arrival time.
    This table is still a work in progress.

    Attributes:
        Base (_type_): _description_
        id: Unique identifier
        arid: ID of the arrival used
        method_id: ID of the magnitude method used
        mag: Magnitude value
        uncertainty: Optional. Magnitude uncertainty
        last_modified: Automatic field that keeps track of when a row was added to
             or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "arrmag"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## Primary Key without simplification
    arid: Mapped[int] = mapped_column(
        ForeignKey("assoc_arr.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    method_id: Mapped[int] = mapped_column(
        ForeignKey("mag_method.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    ##
    mag: Mapped[float] = mapped_column(Double, nullable=False)
    uncertainty: Mapped[Optional[float]] = mapped_column(Double)

    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ## Relationships
    # Many-to-one relationship with AssocArrival
    arr: Mapped["AssocArrival"] = relationship(back_populates="arr_mags")
    # Many-to-one relationship with MagMethod
    method: Mapped["MagMethod"] = relationship(back_populates="arr_mags")

    __table_args__ = (
        UniqueConstraint(arid, method_id, name="simplify_pk"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"ArrMag(id={self.id!r}, arid={self.arid}, method_id={self.method_id}, "
            f"mag={self.mag}, uncertainty={self.uncertainty}, last_modified={self.last_modified!r})"
        )


class ArrWaveformFeat(Base):
    """Stores features extracted from the waveform near an arrival. For now, assume the
    features are computed using pyuussFeatures (except SNR).
    This table is still a work in progress.

    Attributes:
        Base (_type_): _description_
        id: Unique identifier
        arid: ID of the arrival used
        name: Feature name
        comp: Waveform component the feature was extracted from. Must be Z (vertical),
            R (radial) or T (transverse)
        val: Feature values
        wf_info_id: Optional. ID of the waveform_info for the waveform the features
            were extracted from
        last_modified: Automatic field that keeps track of when a row was added to
             or modified in the database in local time. Does not include microseconds.
    """

    __tablename__ = "arr_wf_feat"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## Primary Key without simplification
    arid: Mapped[int] = mapped_column(
        ForeignKey("assoc_arr.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    # TODO: Could add a feature description table
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    comp: Mapped[Enum] = mapped_column(
        Enum("Z", "R", "T", create_constraint=True, name="comp_enum", nullable=False)
    )
    ##
    val: Mapped[float] = mapped_column(Double, nullable=False)
    # Store the waveform that was used to extract the features
    wf_info_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("waveform_info.id", onupdate="restrict", ondelete="restrict"),
        nullable=True,
    )
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ## Relationships
    # Many-to-one relationship with AssocArrival
    arr: Mapped["AssocArrival"] = relationship(back_populates="wf_feats")
    # Many-to-one relationship with WaveformInfo
    wf_info: Mapped["WaveformInfo"] = relationship(back_populates="arr_wf_feats")

    __table_args__ = (
        UniqueConstraint(arid, name, comp, name="simplify_pk"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"ArrWaveformFeat(id={self.id!r}, arid={self.arid}, name={self.name}"
            f"comp={self.comp}, val={self.val}, wf_info_id={self.wf_info_id}, "
            f"last_modified={self.last_modified!r})"
        )


class NetMag(Base):
    """Stores network magnitudes, which are generally comptutes by combining arrival
    magnitude estimates.

    Args:
        Base (_type_): _description_
        id: Unique identifier
        orid: ID of the origin the netowrk magnitude belongs to
        type: Type of magnitude
        auth: Author of the magnitude (e.g., SPDL, UUSS)
        mag: Magnitude value
        nsta: Number of stations used to compute the network mag
        nobs: Number of observations used to compute the network mag
        rms: Root-mean-square error of the magnitude
        uncertainty: Uncertainty in the magnitude
        quality: Quality assigned to the magnitude
        min_dist: Distance (km) from the epicenter to the closest station with a
            magnitude estimate
        gap: Maximum gap between stations used in the network magnitude
        last_modified: Automatic field that keeps track of when a row was added to
             or modified in the database in local time. Does not include microseconds.

    """

    __tablename__ = "netmag"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    ## Primary Key without simplification
    orid: Mapped[int] = mapped_column(
        ForeignKey("origin.id", onupdate="restrict", ondelete="restrict"),
        nullable=False,
    )
    # TODO: Change this to a method or make a type table?
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    # TODO: Make an author table or include this in the type/method?
    auth: Mapped[str] = mapped_column(String(10), nullable=False)
    ##
    mag: Mapped[float] = mapped_column(Double, nullable=False)
    # Quality info #TODO: Figure out which values I will actually have/need
    nsta: Mapped[int] = mapped_column(Integer)
    nobs: Mapped[int] = mapped_column(Integer)
    rms: Mapped[float] = mapped_column(Double)
    uncertainty: Mapped[float] = mapped_column(Double)
    quality: Mapped[float] = mapped_column(Double)
    min_dist: Mapped[float] = mapped_column(Double)
    gap: Mapped[float] = mapped_column(Double)
    # Keep track of when the row was inserted/updated
    last_modified = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    ## Relationships
    # Many-to-one relationship with Origin
    origin: Mapped["Origin"] = relationship(back_populates="netmags")

    ___table_args__ = (
        UniqueConstraint(orid, type, auth, name="simplify_pk"),
        CheckConstraint("mag >= -10.0 and mag <= 10.0", name="valid_mag"),
        CheckConstraint("nsta > 0", name="pos_nsta"),
        CheckConstraint("nobs > 0", name="post_nobs"),
        CheckConstraint("rms >= 0.0", name="nonneg_rms"),
        CheckConstraint("uncertainty >= 0.0", name="nonneg_uncertainty"),
        CheckConstraint("quality >= 0.0 and quality <= 1.0", name="valid_quality"),
        CheckConstraint("min_dist >= 0.0", name="nonneg_min_dist"),
        CheckConstraint("gap >= 0.0 and gap <= 360.0", name="valid_gap"),
        {"mysql_engine": MYSQL_ENGINE},
    )

    def __repr__(self) -> str:
        return (
            f"NetMag(id={self.id!r}, orid={self.orid}, type={self.type}, auth={self.auth}, "
            f"mag={self.mag}, nsta={self.nsta}, nobs={self.nobs}, rms={self.rms}, "
            f"uncertainty={self.uncertainty}, quality={self.quality}, min_dist={self.min_dist}, "
            f"gap={self.gap}, last_modified={self.last_modified!r})"
        )
