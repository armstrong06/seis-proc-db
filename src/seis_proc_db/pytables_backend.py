from tables import *
import numpy as np
import os
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from seis_proc_db.config import HDF_BASE_PATH, HDF_WAVEFORM_DIR, HDF_UNET_SOFTMAX_DIR


class BasePyTable(ABC):
    TABLE_NAME = None
    TABLE_TITLE = None
    TABLE_TYPE = "NewTable"
    TABLE_DTYPE = None
    TABLE_START_END_INDS = False
    FLUSH_THRESHOLD = 50

    @property
    def table(self):
        return self._table

    @property
    def file_path(self):
        return self._file_path

    @property
    def file_name(self):
        _, file_name = os.path.split(self._file_path)
        return file_name

    def __init__(self, expected_array_length, on_event=None):

        self._is_open = False
        self._on_event = on_event
        self.expected_array_length = expected_array_length
        self._file_path = self._make_filepath()
        self._flush_counter = 0
        self._default_start_ind = 0
        self._default_end_ind = int(expected_array_length)
        self._h5_file, self._table = None, None
        self._open_file(
            self.TABLE_NAME,
            self.TABLE_TITLE,
            self.TABLE_TYPE,
            self.TABLE_DTYPE,
        )

        self._in_transaction = False
        self._transaction_start_ind = None
        self._transaction_modified_backup = {}

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

            raise e

    def _generate_table_description(self, data_col_type, table_description):
        class_attrs = {
            "id": Int32Col(),
            "last_modified": Float64Col(),
            "data": data_col_type(shape=(self.expected_array_length,)),
        }
        if self.TABLE_START_END_INDS:
            class_attrs["start_ind"] = Int32Col()
            class_attrs["end_ind"] = Int32Col()  # (dflt=self._default_end_ind),
        return type(table_description, (IsDescription,), class_attrs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._in_transaction:
            if exc_type is not None:
                # An exception occurred; rollback
                self.rollback()
            else:
                # No exception; commit
                self.commit()
        self._flush()
        self.close()

    def __del__(self):
        if self._in_transaction:
            warnings.warn(
                "HDF5 table deleted with uncommitted transaction; changes may be lost.",
                ResourceWarning,
            )
        self._flush()
        self.close()

    def _maybe_flush(self):
        self._flush_counter += 1
        if self._flush_counter >= self.FLUSH_THRESHOLD:
            print("flushing")
            self._flush()

    def _set_table_metadata(self, table):
        attrs = table.attrs

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
            self.commit()
            self._h5_file.close()
            self._is_open = False

    def _flush(self):
        if self._table is not None and self._is_open and self._flush_counter > 0:
            self._table.flush()
            self._flush_counter = 0

    def append(self, db_id, data_array, start_ind=None, end_ind=None):
        if any(True for _ in self._table.where(f"id == {db_id}")):
            self.rollback()
            raise ValueError(f"Duplicate entry '{db_id}' for key 'id'")

        try:
            row = self._table.row
            row["id"] = db_id
            row["data"] = data_array
            # If no value is provided for start_ind and end_ind, then the default value
            # will be used
            if self.TABLE_START_END_INDS:
                row["start_ind"] = (
                    start_ind if start_ind is not None else self._default_start_ind
                )
                row["end_ind"] = (
                    end_ind if end_ind is not None else self._default_end_ind
                )
            row["last_modified"] = datetime.now().timestamp()
            row.append()
            self._maybe_flush()
        except Exception as e:
            self.rollback()
            self.close()
            raise e

    def modify(self, db_id, data_array, start_ind=None, end_ind=None):
        if self.TABLE_START_END_INDS:
            if start_ind is None or end_ind is None:
                self.rollback()
                raise ValueError(
                    "start_ind and end_ind must be provided when TABLE_START_END_INDS is True"
                )
        else:
            if start_ind is not None or end_ind is not None:
                self.rollback()
                raise ValueError(
                    "start_ind and end_ind should not be passed when TABLE_START_END_INDS is False"
                )
        n_matches = len(list(self._table.where(f"id == {db_id}")))
        if n_matches != 1:
            self.rollback()
            raise ValueError(
                f"Expected exactly one entry to match id = {db_id} but found {n_matches}"
            )

        try:
            for row in self._table.where(f"id == {db_id}"):
                if (
                    self._in_transaction
                    and row.nrow not in self._transaction_modified_backup
                ):
                    self._transaction_modified_backup[row.nrow] = row[:]

                row["data"] = data_array
                if self.TABLE_START_END_INDS:
                    row["start_ind"] = start_ind
                    row["end_ind"] = end_ind
                row["last_modified"] = datetime.now().timestamp()
                row.update()
            self._maybe_flush()
        except Exception as e:
            self.rollback()
            self.close()
            raise e

    def start_transaction(self):
        if not self._in_transaction:
            self._in_transaction = True
            self._transaction_start_ind = self._table.nrows

    def _remove_transaction_changes(self):
        try:
            for nrow, backup in self._transaction_modified_backup.items():
                nmod = self._table.modify_rows(
                    start=nrow, stop=nrow + 1, step=1, rows=[backup]
                )
                assert nmod == 1, "Expected exactly 1 row to be modified"

            self._table.remove_rows(self._transaction_start_ind)
            self._flush()
        except Exception as e:
            self.close()
            raise e

    def _reset_transaction(self):
        n_mod = len(self._transaction_modified_backup)
        n_added = self._table.nrows - self._transaction_start_ind
        self._in_transaction = False
        self._transaction_start_ind = None
        self._transaction_modified_backup = {}

        return n_added, n_mod

    def _notify(self, message: str):
        if self._on_event:
            self._on_event(message)

    def rollback(self):
        if self._in_transaction:
            self._remove_transaction_changes()
            n_added, n_mod = self._reset_transaction()
            self._notify(
                f"Rolled back {n_mod} modified rows and {n_added} added rows in the last transaction for {self.TABLE_NAME} PyTable."
            )

    def commit(self):
        self._flush()
        if self._in_transaction:
            n_added, n_mod = self._reset_transaction()
            self._notify(
                f"Committed {n_mod} modified rows and {n_added} added rows in the last transaction for {self.TABLE_NAME} PyTable."
            )


class WaveformStorage(BasePyTable):
    TABLE_NAME = "waveform"
    TABLE_TITLE = "Waveform data"
    # TABLE_DESCRIPTION = "Waveform"
    TABLE_DTYPE = Float32Col
    TABLE_START_END_INDS = True

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
        on_event=None,
    ):
        self.sta = sta
        self.seed_code = seed_code
        self.ncomps = ncomps
        self.phase = phase

        self.filt_low = filt_low
        self.filt_high = filt_high
        self.proc_notes = proc_notes

        super().__init__(expected_array_length, on_event=on_event)

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
    # TABLE_DESCRIPTION = "DlDetectorOutput"
    TABLE_DTYPE = UInt8Col

    def __init__(
        self,
        expected_array_length,
        sta,
        seed_code,
        phase,
        ncomps,
        det_method_id,
        on_event=None,
    ):

        self.sta = sta
        self.seed_code = seed_code
        self.ncomps = ncomps
        self.phase = phase
        self.det_method_id = det_method_id

        super().__init__(expected_array_length, on_event=on_event)

    def _make_filepath(self):
        file_name = f"{self.sta}_{self.seed_code}_{self.phase}_{self.ncomps}C_detmethod{self.det_method_id:02d}.h5"
        return os.path.join(HDF_BASE_PATH, HDF_UNET_SOFTMAX_DIR, file_name)

    def _make_h5_file_title(self):
        return (
            f"Deep-learning detector outputs for {self.sta}.{self.seed_code} from {self.ncomps}C {self.phase}"
            f"model using DetectionMethod.id={self.det_method_id}."
        )
