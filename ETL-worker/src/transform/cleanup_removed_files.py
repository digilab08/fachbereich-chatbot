from pathlib import Path
from typing import List


def cleanup_removed_files(processed_data_path: str | Path, removed_file_paths: List[str]):
    processed_data_dir = Path(processed_data_path)
    for file_path in removed_file_paths:
        (processed_data_dir / file_path).unlink(missing_ok=True)