import os
import pytest
from unittest import mock
from seis_proc_db import pytables_backend


@pytest.fixture
def mock_config():
    with mock.patch(
        "seis_proc_db.pytables_backend.HDF_BASE_PATH",
        "./tests/pytables_outputs",
    ):
        yield


class TestWaveformPyTable:
    def test_init(self, mock_config):

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

        base_path, file_name = os.path.split(wf_storage.file_path)
        # Check that the filename is as would be expected
        assert (
            file_name == "TEST_HHZ_P_3C_NoneHz_NoneHz_1200samps.h5"
        ), "file name is not as expected"
        # Check that the file was created
        assert os.path.exists(wf_storage.file_path), "the file was not created"

        print(wf_storage._h5_file.title)
        # Check that the file is set to open
        assert wf_storage._is_open, "the file is not registered as open"
        table = wf_storage.table
        # Check table info
        assert table.name == "waveform", "the table name is incorrect"
        assert table.title == "Waveform data", "the table title is incorrect"
        assert table.description == "Waveform", "the table description is incorrect"
        # Check table attributes
        assert table.attrs.sta == "TEST", "the table sta attr is incorrect"
        assert table.attrs.seed_code == "HHZ", "the table seed_code attr is incorrect"
        assert table.attrs.ncomps == 3, "the table ncomps attr is incorrect"
        assert table.attrs.phase == "P", "the table phase attr is incorrect"
        assert table.attrs.filt_low is None, "the table filt_low attr is incorrect"
        assert table.attrs.filt_high is None, "the table filt_hight attr is incorrect"
        assert (
            table.attrs.proc_nots == "raw waveforms"
        ), "the table proc_desc attr is incorrect"
        assert (
            table.attrs.expected_array_length == 1200
        ), "the table expected_array_length attr is incorrect"

        # Clean up
        wf_storage.close()
        os.remove(wf_storage.file_path)
        assert not os.path.exists(wf_storage.file_path), "the file was not removed"
