import os
import pytest
import numpy as np
from datetime import datetime
from seis_proc_db import pytables_backend


class TestWaveformStorage:
    def test_init(self, mock_pytables_config):

        wf_storage = pytables_backend.WaveformStorage(
            expected_array_length=1200,
            sta="TEST",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            filt_low=None,
            filt_high=None,
            proc_notes="raw waveforms",
        )

        try:
            file_name = wf_storage.file_name
            # Check that the filename is as would be expected
            assert (
                file_name == "TEST_HHZ_P_3C_NoneHz_NoneHz_1200samps.h5"
            ), "file name is not as expected"
            # Check that the file was created
            assert os.path.exists(wf_storage.file_path), "the file was not created"
            # Check that the file is set to open
            assert wf_storage._is_open, "the file is not registered as open"
            table = wf_storage.table
            # Check table info
            assert table.cols.id.is_indexed, "id column in table is not indexed"
            assert table.will_query_use_indexing(
                "id == 1"
            ), "table will not use an index search for query by id"
            assert table.name == "waveform", "the table name is incorrect"
            assert table.title == "Waveform data", "the table title is incorrect"
            # Check table attributes
            assert table.attrs.sta == "TEST", "the table sta attr is incorrect"
            assert (
                table.attrs.seed_code == "HHZ"
            ), "the table seed_code attr is incorrect"
            assert table.attrs.ncomps == 3, "the table ncomps attr is incorrect"
            assert table.attrs.phase == "P", "the table phase attr is incorrect"
            assert table.attrs.filt_low is None, "the table filt_low attr is incorrect"
            assert (
                table.attrs.filt_high is None
            ), "the table filt_hight attr is incorrect"
            assert (
                table.attrs.proc_notes == "raw waveforms"
            ), "the table proc_notes attr is incorrect"
            assert (
                table.attrs.expected_array_length == 1200
            ), "the table expected_array_length attr is incorrect"
        finally:
            # Clean up
            wf_storage.close()
            os.remove(wf_storage.file_path)
            assert not os.path.exists(wf_storage.file_path), "the file was not removed"

    def test_append(self, mock_pytables_config):
        wf_storage = pytables_backend.WaveformStorage(
            expected_array_length=1200,
            sta="TEST",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            filt_low=None,
            filt_high=None,
            proc_notes="raw waveforms",
        )

        try:
            db_id = 1
            data = np.random.rand(1200).astype(np.float32)
            start_ind = 100
            end_ind = 1100
            data[0:start_ind] = 0
            data[end_ind:] = 0
            wf_storage.append(db_id, data, start_ind, end_ind)
            wf_storage.flush()

            assert wf_storage.table.nrows == 1, "incorrect number of rows in table"
            row = [row for row in wf_storage.table.where(f"id == {db_id}")][0]
            assert row["id"] == db_id, "incorrect id"
            assert row["start_ind"] == 100, "incorrect start_ind"
            assert row["end_ind"] == 1100, "incorrect end_ind"
            assert np.array_equal(row["data"], data), "incorrect data"
            assert np.all(
                row["data"][row["start_ind"] : row["end_ind"]] != 0
            ), "start and end did not work correctly"
            assert (
                datetime.fromtimestamp(row["last_modified"]).date()
                == datetime.now().date()
            ), "incorrect last_modified date"

            # Try to insert a duplicate key
            with pytest.raises(ValueError):
                wf_storage.append(db_id, data)

        finally:
            # Clean up
            wf_storage.close()
            os.remove(wf_storage.file_path)
            assert not os.path.exists(wf_storage.file_path), "the file was not removed"

    def test_modify(self, mock_pytables_config):
        wf_storage = pytables_backend.WaveformStorage(
            expected_array_length=1200,
            sta="TEST",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            filt_low=None,
            filt_high=None,
            proc_notes="raw waveforms",
        )

        try:
            # Insert original values
            db_id = 1
            data = np.random.rand(1200).astype(np.float32)
            start_ind = 100
            end_ind = 1100
            data[0:start_ind] = 0
            data[end_ind:] = 0
            wf_storage.append(db_id, data, start_ind, end_ind)
            wf_storage.flush()

            # Modify the row
            new_data = np.random.rand(1200).astype(np.float32)
            start_ind = 0
            end_ind = 1200
            wf_storage.modify(db_id, new_data, start_ind, end_ind)

            assert wf_storage.table.nrows == 1, "incorrect number of rows in table"
            row = [row for row in wf_storage.table.where(f"id == {db_id}")][0]
            assert np.array_equal(row["data"], new_data), "incorrect data"
            assert row["start_ind"] == 0, "incorrect start_ind"
            assert row["end_ind"] == 1200, "incorrect end_ind"

        finally:
            # Clean up
            wf_storage.close()
            os.remove(wf_storage.file_path)
            assert not os.path.exists(wf_storage.file_path), "the file was not removed"


class TestDLDetectorOutputStorage:
    def test_init(self, mock_pytables_config):
        detout_storage = None
        try:
            detout_storage = pytables_backend.DLDetectorOutputStorage(
                expected_array_length=86400,
                sta="TEST",
                seed_code="HHZ",
                ncomps=3,
                phase="P",
                det_method_id=1,
            )

            file_name = detout_storage.file_name
            # Check that the filename is as would be expected
            assert (
                file_name == "TEST_HHZ_P_3C_detmethod01.h5"
            ), "file name is not as expected"
            # Check that the file was created
            assert os.path.exists(detout_storage.file_path), "the file was not created"
            # Check that the file is set to open
            assert detout_storage._is_open, "the file is not registered as open"
            table = detout_storage.table
            # Check table info
            assert table.name == "dldetector_output", "the table name is incorrect"
            assert table.title == "DL detector output", "the table title is incorrect"
            # Check table attributes
            assert table.attrs.sta == "TEST", "the table sta attr is incorrect"
            assert (
                table.attrs.seed_code == "HHZ"
            ), "the table seed_code attr is incorrect"
            assert table.attrs.ncomps == 3, "the table ncomps attr is incorrect"
            assert table.attrs.phase == "P", "the table phase attr is incorrect"
            assert (
                table.attrs.det_method_id == 1
            ), "the table det_method_id attr is incorrect"
            assert (
                table.attrs.expected_array_length == 86400
            ), "the table expected_array_length attr is incorrect"
        finally:
            # Clean up
            if detout_storage is not None:
                detout_storage.close()
                os.remove(detout_storage.file_path)
                assert not os.path.exists(
                    detout_storage.file_path
                ), "the file was not removed"

    def test_append(self, mock_pytables_config):
        detout_storage = pytables_backend.DLDetectorOutputStorage(
            expected_array_length=86400,
            sta="TEST",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            det_method_id=1,
        )

        try:
            db_id = 1
            data = np.random.rand(86400).astype(np.uint8)
            detout_storage.append(db_id, data)
            detout_storage.flush()

            assert detout_storage.table.nrows == 1, "incorrect number of rows in table"
            row = [row for row in detout_storage.table.where(f"id == {db_id}")][0]
            assert row["id"] == db_id, "incorrect id"
            assert np.array_equal(row["data"], data), "incorrect data"
            assert (
                datetime.fromtimestamp(row["last_modified"]).date()
                == datetime.now().date()
            ), "incorrect last_modified date"

            # Try to insert a duplicate key
            with pytest.raises(ValueError):
                detout_storage.append(db_id, data)

        finally:
            # Clean up
            detout_storage.close()
            os.remove(detout_storage.file_path)
            assert not os.path.exists(
                detout_storage.file_path
            ), "the file was not removed"
