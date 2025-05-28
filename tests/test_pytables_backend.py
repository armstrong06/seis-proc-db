import os
import pytest
import numpy as np
from datetime import datetime
from tables import Float32Col
from seis_proc_db import pytables_backend


class MockStorage(pytables_backend.BasePyTable):
    TABLE_NAME = "waveforms"
    TABLE_TITLE = "Test Waveforms"
    TABLE_DTYPE = Float32Col
    TABLE_START_END_INDS = True
    FLUSH_THRESHOLD = 1  # Need to flush or can't use iterrows

    def _make_filepath(self):
        return "./tests/pytables_outputs/test_transaction.h5"

    def _make_h5_file_title(self):
        return "Testing Transactions"


class TestBasePyTable:
    def test_transaction(self):
        if os.path.exists("./tests/pytables_outputs/test_transaction.h5"):
            os.remove("./tests/pytables_outputs/test_transaction.h5")

        stor = MockStorage(expected_array_length=10)

        # Append outside of transaction
        stor.append(db_id=1, data_array=np.ones(10))
        assert any(row["id"] == 1 for row in stor.table.iterrows())

        # Begin transaction
        stor.start_transaction()
        stor.append(db_id=2, data_array=np.full(10, 2))
        stor.modify(db_id=1, data_array=np.zeros(10), start_ind=0, end_ind=10)
        # Confirm changes exist for now
        assert any(row["id"] == 2 for row in stor.table.iterrows())
        assert np.allclose([row["data"] for row in stor.table.where("id == 1")][0], 0)

        # Rollback
        stor.rollback()
        ids = [row["id"] for row in stor.table.iterrows()]
        assert 2 not in ids  # Removed
        assert np.allclose(
            [row["data"] for row in stor.table.where("id == 1")][0], 1
        )  # Reverted

        # Begin and commit transaction
        stor.start_transaction()
        stor.append(db_id=3, data_array=np.full(10, 3))
        stor.commit()
        ids = [row["id"] for row in stor.table.iterrows()]
        assert 3 in ids  # Stays


class TestWaveformStorage:
    def test_init(self, mock_pytables_config):

        wf_storage = pytables_backend.WaveformStorage(
            expected_array_length=1200,
            net="JK",
            sta="TEST",
            loc="01",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            wf_source_id=1
        )

        try:
            file_name = wf_storage.file_name
            # Check that the filename is as would be expected
            assert file_name == "JK.TEST.01.HHZ.P.3C.1200samps.source01.h5", "file name is not as expected"
            # assert (
            #     os.path.basename(os.path.dirname(wf_storage.file_path))
            #     == "NoneHz_NoneHz_1200samps"
            # ), "incorrect directory name"
            assert wf_storage.relative_path == "JK.TEST.01.HHZ.P.3C.1200samps.source01.h5", "incorrect relative path"
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
            assert table.attrs.wf_source_id == 1, "incorrect wf_source_id"
            #assert table.attrs.filt_low is None, "the table filt_low attr is incorrect"
            # assert (
            #     table.attrs.filt_high is None
            # ), "the table filt_hight attr is incorrect"
            # assert (
            #     table.attrs.proc_notes == "raw waveforms"
            # ), "the table proc_notes attr is incorrect"
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
            net="JK",
            sta="TEST",
            loc="01",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            wf_source_id=1,
            # filt_low=None,
            # filt_high=None,
            # proc_notes="raw waveforms",
        )

        try:
            db_id = 1
            data = np.random.rand(1200).astype(np.float32)
            start_ind = 100
            end_ind = 1100
            data[0:start_ind] = 0
            data[end_ind:] = 0
            wf_storage.append(db_id, data, start_ind, end_ind)
            wf_storage.commit()

            assert wf_storage.table.nrows == 1, "incorrect number of rows in table"
            row = wf_storage.select_row(db_id)
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
            net="JK",
            sta="TEST",
            loc="01",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            wf_source_id=1,
            # filt_low=None,
            # filt_high=None,
            # proc_notes="raw waveforms",
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
            wf_storage.commit()

            # Modify the row
            new_data = np.random.rand(1200).astype(np.float32)
            start_ind = 0
            end_ind = 1200
            wf_storage.modify(db_id, new_data, start_ind, end_ind)
            wf_storage.commit()

            assert wf_storage.table.nrows == 1, "incorrect number of rows in table"
            row = wf_storage.select_row(db_id)
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
                net="JK",
                sta="TEST",
                loc="01",
                seed_code="HHZ",
                ncomps=3,
                phase="P",
                det_method_id=1,
            )

            file_name = detout_storage.file_name
            # Check that the filename is as would be expected
            assert (
                file_name == "JK.TEST.01.HHZ.P.3C.detmethod01.h5"
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
            net="JK",
            sta="TEST",
            loc="01",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            det_method_id=1,
        )

        try:
            db_id = 1
            data = np.random.rand(86400).astype(np.uint8)
            detout_storage.append(db_id, data)
            detout_storage.commit()

            assert detout_storage.table.nrows == 1, "incorrect number of rows in table"
            row = detout_storage.select_row(db_id)
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

class TestSwagPicksStorage:
    def test_init(self, mock_pytables_config):

        repicker_storage = pytables_backend.SwagPicksStorage(
            expected_array_length=450,
            start="2023-01-01",
            end="2023-01-31",
            phase="P",
            repicker_method_id=1
        )

        try:
            file_name = repicker_storage.file_name
            # Check that the filename is as would be expected
            assert file_name == "repicker01_P_2023-01-01_2023-01-31.h5", "file name is not as expected"
            # Check that the file was created
            assert os.path.exists(repicker_storage.file_path), "the file was not created"
            # Check that the file is set to open
            assert repicker_storage._is_open, "the file is not registered as open"
            table = repicker_storage.table
            # Check table info
            assert table.cols.id.is_indexed, "id column in table is not indexed"
            assert table.will_query_use_indexing(
                "id == 1"
            ), "table will not use an index search for query by id"
            assert table.name == "swag_picks", "the table name is incorrect"
            assert table.title == "SWAG Repicker Predictions", "the table title is incorrect"
            # Check table attributes
            assert table.attrs.phase == "P", "the table phase attr is incorrect"
            assert (
                table.attrs.expected_array_length == 450
            ), "the table expected_array_length attr is incorrect"
            assert table.attrs.start == "2023-01-01", "the table start attr is incorrect"
            assert table.attrs.end == "2023-01-31", "the table end attr is incorrect"
        finally:
            # Clean up
            repicker_storage.close()
            os.remove(repicker_storage.file_path)
            assert not os.path.exists(repicker_storage.file_path), "the file was not removed"

def test_waveform_storage_reader():
    wf_storage = pytables_backend.WaveformStorage(
            expected_array_length=1200,
            net="JK",
            sta="TEST",
            loc="01",
            seed_code="HHZ",
            ncomps=3,
            phase="P",
            wf_source_id=1
        )
    

    try:
        wf_file = wf_storage.file_path
        db_id = 1
        data = np.random.rand(1200).astype(np.float32)
        start_ind = 100
        end_ind = 1100
        data[0:start_ind] = 0
        data[end_ind:] = 0
        wf_storage.append(db_id, data, start_ind, end_ind)
        wf_storage.commit()
        wf_storage.close()

        wf_reader = pytables_backend.WaveformStorageReader(wf_file)
        assert wf_reader.table is not None, "table is not set"
        file_dir, file_name = os.path.split(wf_file)
        assert wf_reader.file_name == file_name, "incorrect file name"
        assert wf_reader.file_dir == file_dir, "incorrect dir"
        row = wf_reader.select_row(db_id)
        assert row is not None, "No row was returned"
        assert row["id"] == db_id, "incorrect id"
        assert np.array_equal(data, row["data"]), "incorrect data"
        assert start_ind == row["start_ind"], "incorrect start ind"
        assert end_ind == row["end_ind"], "incorrect end ind"
        rows = wf_reader.select_rows([db_id])
        assert len(rows) == 1, "expected 1 row to be returned"

        wf_reader.close()
        assert wf_reader._is_open == False, "should be closed"

    finally:
        # Clean up
        if wf_storage._is_open:
            wf_storage.close()
        if wf_reader._is_open:
            wf_reader.close()
        os.remove(wf_storage.file_path)
        assert not os.path.exists(wf_storage.file_path), "the file was not removed"