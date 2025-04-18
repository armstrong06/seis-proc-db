from tables import *
import numpy as np
import os
from abc import ABC, abstractmethod
from datetime import datetime
from seis_proc_db.config import HDF_BASE_PATH, HDF_WAVEFORM_DIR, HDF_UNET_SOFTMAX_DIR


class BasePyTable(ABC):
    TABLE_NAME = None
    TABLE_TITLE = None
    TABLE_DESCRIPTION = None
    TABLE_DTYPE = None

    @property
    def table(self):
        return self._table

    @property
    def file_path(self):
        return self._file_path

    def __init__(self, expected_array_length):

        self._is_open = False
        self.expected_array_length = expected_array_length
        self._file_path = self._make_filepath()
        self._flush_counter = 0
        self._flush_threshold = 50
        self._h5_file, self._table = None, None
        self._open_file(
            self.TABLE_NAME,
            self.TABLE_TITLE,
            self.TABLE_DESCRIPTION,
            self.TABLE_DTYPE,
        )

    @abstractmethod
    def _make_filepath(self):
        pass

    @abstractmethod
    def _make_h5_file_title(self):
        pass

    def _open_file(
        self, table_name, table_title, table_description, table_data_col_type
    ):
        dir_exists = os.path.exists(os.path.dirname(self._file_path))
        if not dir_exists:
            os.makedirs(os.path.dirname(self._file_path))

        file_exists = os.path.isfile(self._file_path)

        h5file = None
        try:
            h5file = open_file(
                self._file_path,
                mode="a",
                title=(self._make_h5_file_title()),
            )

            if not file_exists:
                table = h5file.create_table(
                    "/",
                    table_name,
                    self._generate_table_description(
                        table_data_col_type, table_description
                    ),
                    table_title,
                )

                table.cols.id.create_index()

                self._set_table_metadata(table)
            else:
                table = h5file.get_node(f"/{self.TABLE_NAME}")

            self._h5_file = h5file
            self._table = table
            self._is_open = True

        except Exception as e:
            if h5file is not None:
                h5file.close()

            raise

    def _generate_table_description(self, data_col_type, table_description):
        class_attrs = {
            "id": Int32Col(),
            "last_modified": Float64Col(),
            "data": data_col_type(shape=(self.expected_array_length,)),
        }
        return type(table_description, (IsDescription,), class_attrs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.close()

    def __del__(self):
        self.flush()
        self.close()

    def _maybe_flush(self):
        self._flush_counter += 1
        if self._flush_counter >= self._flush_threshold:
            self._table.flush()
            self._flush_counter = 0

    def _set_table_metadata(self, table):
        attrs = table

        # Get instance attributes that came from __init__ (excluding private/internal ones)
        init_params = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

        for key, value in init_params.items():
            if hasattr(attrs, key):
                existing = getattr(attrs, key)
                if existing != value:
                    raise ValueError(
                        f"Mismatch in HDF5 table metadata for '{key}': "
                        f"existing value = {existing}, new value = {value}"
                    )
            else:
                setattr(attrs, key, value)

    def close(self):
        if self._h5_file is not None and self._is_open:
            self._h5_file.close()
            self._is_open = False

    def flush(self):
        if self._table is not None and self._is_open and self._flush_counter > 0:
            self._table.flush()
            self._flush_counter = 0

    def append(self, db_id, data_array):
        row = self._table.row
        row["id"] = db_id
        row["data"] = data_array
        row["last_modified"] = datetime.now().timestamp()
        row.append()

        self._maybe_flush()

    def modify(self, db_id, data_array):
        result = [x for x in self._table.where(f"id == {db_id}")]
        assert len(result) == 1, "Expected exactly one row to match"
        row = result[0]
        row["data"] = data_array
        row["last_modified"] = datetime.now().timestamp()
        row.update()

        self._maybe_flush()


class WaveformStorage(BasePyTable):
    TABLE_NAME = "waveform"
    TABLE_TITLE = "Waveform data"
    TABLE_DESCRIPTION = "Waveform"
    TABLE_DTYPE = Float32Col

    def __init__(
        self,
        expected_array_length,
        sta,
        seed_code,
        ncomps,
        phase,
        filt_low,
        filt_high,
        proc_notes,
    ):
        self.sta = sta
        self.seed_code = seed_code
        self.ncomps = ncomps
        self.phase = phase

        self.filt_low = filt_low
        self.filt_high = filt_high
        self.proc_notes = proc_notes

        super().__init__(expected_array_length)

    def _make_filepath(self):
        file_name = f"{self.sta}_{self.seed_code}_{self.phase}_{self.ncomps}C_{self.filt_low!r}Hz_{self.filt_high!r}Hz_{self.expected_array_length}samps.h5"
        return os.path.join(HDF_BASE_PATH, HDF_WAVEFORM_DIR, file_name)

    def _make_h5_file_title(self):
        return (
            f"Waveform segments ({self.expected_array_length} samples) for {self.sta}.{self.seed_code} centered on "
            f"{self.phase} picks from {self.ncomps}C processing. Filtered from {self.filt_low} - {self.filt_high} Hz"
        )


class DLDetectorOutputStorage(BasePyTable):

    TABLE_NAME = "dldetector_output"
    TABLE_TITLE = "DL detector output"
    TABLE_DESCRIPTION = "DlDetectorOutput"
    TABLE_DTYPE = UInt8Col

    def __init__(
        self, expected_array_length, sta, seed_code, phase, ncomps, det_method_id
    ):

        self.sta = sta
        self.seed_code = seed_code
        self.ncomps = ncomps
        self.phase = phase
        self.det_method_id = det_method_id

        super().__init__(expected_array_length)

    def _make_filepath(self):
        file_name = f"{self.sta}_{self.seed_code}_{self.phase}_{self.ncomps}C_detmethod{self.det_method_id}.h5"
        return os.path.join(HDF_BASE_PATH, HDF_UNET_SOFTMAX_DIR, file_name)

    def _make_h5_file_title(self):
        return (
            f"Deep-learning detector outputs for {self.sta}.{self.seed_code} from {self.ncomps}C {self.phase}"
            f"model using DetectionMethod.id={self.det_method_id}."
        )
