import json
import os
import pathlib


def check_log_file(filepath: str) -> bool:
    return os.path.isfile(filepath)


def check_file_empty(filepath: str) -> bool:
    return os.path.getsize(filepath) == 0


def read_log_file(filepath: str) -> list:
    with open(filepath, 'r') as f:
        return json.load(f)


def create_log_file(filepath: str, data: list) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def update_log_file(filepath: str, new_entries: list) -> None:
    existing = []
    if check_log_file(filepath) and not check_file_empty(filepath):
        existing = read_log_file(filepath)
    existing.extend(new_entries)
    with open(filepath, 'w') as f:
        json.dump(existing, f, indent=2)


def check_processed_raw_files_v2(log_filepath: str, dir_entrada: str) -> list:
    """
    Scans dir_entrada for AVI files and returns those not yet in the log.
    Returns a list of tuples: (file_path, file_size).
    """
    processed = set()
    if check_log_file(log_filepath) and not check_file_empty(log_filepath):
        log_data = read_log_file(log_filepath)
        for entry in log_data:
            if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                processed.add(entry[0])

    new_files = []
    for root, _, files in os.walk(dir_entrada):
        for fname in files:
            if fname.upper().endswith('.AVI'):
                full_path = os.path.join(root, fname)
                normalized = str(pathlib.PureWindowsPath(full_path))
                if normalized not in processed:
                    new_files.append((full_path, os.path.getsize(full_path)))

    return new_files
