import os
from dotenv import load_dotenv

from pathlib import Path
import sqlite3
from typing import Dict, List

from utils import get_logger

logger = get_logger(__name__)


def moodle_extract_relevant_files(data_path: str | Path, extraction_config: List[Dict[str, str]]) -> List[dict[str, str | Path]]:
    """Extracts data from Moodle based on the provided extraction configuration.

    :param data_path: The path to the data directory.
    :param extraction_config: A list of dictionaries containing extraction configuration.
    :return: A list of dictionaries containing the extracted data with the source and the target.
    :raises FileNotFoundError: If the data path or moodle path does not exist.
    :raises ValueError: If the data path or moodle path is not a directory.
    """
    
    prepared_config = [rule for rule in extraction_config if rule.get("source").startswith("moodle/")]
    prepared_config.sort(key=lambda rule: len(rule["source"]), reverse=True)

    data_root = Path(data_path).resolve()
    
    if not data_root.exists():
        raise FileNotFoundError(f"The data path does not exist: '{data_root}'")
    if not data_root.is_dir():
        raise ValueError(f"The data path is not a directory: '{data_root}'")

    moodle_root = data_root / "moodle"
    if not moodle_root.exists():
        raise FileNotFoundError(f"The moodle path does not exist: '{moodle_root}'")
    if not moodle_root.is_dir():
        raise ValueError(f"The moodle path is not a directory: '{moodle_root}'")

    db_path = moodle_root / "moodle_state.db"
 
    db_connection = None
    if db_path.is_file():
        try:
            db_connection = sqlite3.connect(db_path)
        except sqlite3.Error:
            db_connection = None

    relevant_files: List[dict[str, str | Path]] = []

    for file_path in moodle_root.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(data_root).as_posix()
        path_in_moodle = file_path.relative_to(moodle_root).as_posix()

        matched_rule = next(
            (rule for rule in prepared_config if relative_path.startswith(rule["source"])),
            None,
        )

        if matched_rule is None:
            continue

        action = (matched_rule.get("action") or "").strip().lower()
        if action == "ignore":
            continue

        relevant_file = {
            "source": relative_path,
            "target": (matched_rule.get("target") or "").strip(),
            "file_path": file_path.resolve(),
            "url": None,
            "timestamp": file_path.stat().st_mtime,
        }


        if db_connection is not None:
            load_dotenv()
            moodle_url = os.getenv("MOODLE_URL", None)
            try:
                cursor = db_connection.cursor()
                result = cursor.execute(
                    "SELECT course_id, module_id, content_fileurl FROM files WHERE saved_to = ? LIMIT 1",
                    (str(Path(path_in_moodle)),), # The coma is necessary to make it a tuple
                ).fetchone()


                if result is not None:
                    if result[2] not in (None, ""):
                        relevant_file["url"] = result[2].replace("/webservice/", "/") # Replace the webservice path to ensure the URL is accessible directly
                    elif moodle_url is not None:
                        relevant_file["url"] = f"{moodle_url}/course/view.php?id={result[0]}#module-{result[1]}" 

            except sqlite3.Error as e:
                logger.exception("Error querying the database for file '%s': %s", relative_path, e)
                relevant_file["url"] = None
            finally:
                if 'cursor' in locals():
                    cursor.close()

        relevant_files.append(
            relevant_file
        )

    # close DB connection after processing all files
    if db_connection is not None:
        db_connection.close()

    return relevant_files
    