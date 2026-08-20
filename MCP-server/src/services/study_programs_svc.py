import os
from dotenv import load_dotenv
from pathlib import Path

from utils import get_csv_as_dict_list

load_dotenv()

config_dir = Path(os.getenv("CONFIG_DIR", "config"))

list_cache: list[dict[str, str]] | None = None


def list_study_programs() -> list[dict[str, str]]:
    """
    Reads the study programs from a CSV file and returns them as a list of dictionaries.

    :return: A list of dictionaries, each representing a study program with its details.
    """
    global list_cache

    if list_cache is not None:
        return list_cache
    
    csv_file_path = config_dir / "study_programs.csv"

    if not config_dir.exists() or not config_dir.is_dir() or not csv_file_path.is_file():
        raise FileNotFoundError(f"The config file '{csv_file_path}' was not found.")

    list_cache = get_csv_as_dict_list(csv_file_path)
    return list_cache

dict_cache: dict[str, dict[str, str]] | None = None

def study_programs_dict() -> dict[str, dict[str, str]]:
    """
    Returns a dictionary of study programs keyed by their abbreviation.

    :return: A dictionary where each key is a study program abbreviation and the value is a dictionary of its details.
    """
    global dict_cache

    if dict_cache is not None:
        return dict_cache

    programs = list_study_programs()
    dict_cache = {program["abbreviation"]: program for program in programs}
    return dict_cache

def study_program_exists(abbreviation: str) -> bool:
    """
    Checks if a study program with the given abbreviation exists.

    :param abbreviation: The abbreviation of the study program to check.
    :return: True if the study program exists, False otherwise.
    """
    return abbreviation in study_programs_dict()

def get_categories(abbreviation: str) -> list[str]:
    """
    Retrieves the categories associated with a given study program abbreviation.

    :param abbreviation: The abbreviation of the study program.
    :return: A list of categories associated with the study program. Returns an empty list if the program does not exist or has no categories.
    """
    programs_dict = study_programs_dict()
    program = programs_dict.get(abbreviation)
    
    if not program:
        return []
    
    return [abbreviation, program.get("overarching degree program abbreviation", ""), program.get("department", ""), "all"]