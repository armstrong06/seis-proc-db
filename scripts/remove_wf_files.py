import os
from seis_proc_db.config import HDF_BASE_PATH, HDF_WAVEFORM_DIR

base = os.path.join(HDF_BASE_PATH, HDF_WAVEFORM_DIR)

file_list_path = "tmp_files/waveform_files_to_remove_2024.txt"  # <-- change this if needed

with open(file_list_path, "r") as f:
    filenames = [line.strip() for line in f if line.strip()]

for filename in filenames:
    try:
        filename = os.path.join(base, filename)
        os.remove(filename)
        print(f"Removed: {filename}")
    except FileNotFoundError:
        print(f"Not found: {filename}")
    except PermissionError:
        print(f"Permission denied: {filename}")
    except Exception as e:
        print(f"Error removing {filename}: {e}")