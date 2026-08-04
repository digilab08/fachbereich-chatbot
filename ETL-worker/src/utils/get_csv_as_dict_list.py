import csv
import os
from typing import Dict, List, Union


def get_csv_as_dict_list(
    file_path: Union[str, os.PathLike], encoding: str = "utf-8"
) -> List[Dict[str, str]]:
    """Reads a CSV file and returns its contents as a list of dictionaries.

    :param file_path: Path to the CSV file (str or PathLike object).
    :param encoding: Text encoding of the file (default: 'utf-8').
    :return: List of dictionaries mapping column headers to row values.
    :raises FileNotFoundError: If the file does not exist at the specified path.
    :raises ValueError: If the specified path is not a file.
    """
    # Resolve the path to an absolute path and validate using the os module
    abs_path = os.path.abspath(file_path)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(
            f"The file was not found at the specified path: '{abs_path}'"
        )

    if not os.path.isfile(abs_path):
        raise ValueError(
            f"The specified path is not a file: '{abs_path}'"
        )

    if not abs_path.lower().endswith(".csv"):
        raise ValueError(f"The specified file is not a CSV file: '{abs_path}'")

    try:
        with open(abs_path, mode="r", encoding=encoding, newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                raise ValueError(f"The CSV file has no header row: '{abs_path}'")
            return list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(f"Could not parse CSV file: '{abs_path}'") from exc
