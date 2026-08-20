import os
from dotenv import load_dotenv
from pathlib import Path

from utils import get_csv_as_dict_list
from services.study_programs_svc import get_categories

load_dotenv()

config_dir = Path(os.getenv("CONFIG_DIR", "config"))

list_cache: list[dict[str, str]] | None = None

def list_contact_points() -> list[dict[str, str]]:
    """
    Reads the contact points from a CSV file and returns them as a list of dictionaries.

    :return: A list of dictionaries, each representing a contact point with its details.
    """
    global list_cache

    if list_cache is not None:
        return list_cache
    
    csv_file_path = config_dir / "contact_points.csv"

    if not config_dir.exists() or not config_dir.is_dir() or not csv_file_path.is_file():
        raise FileNotFoundError(f"The config file '{csv_file_path}' was not found.")

    list_cache = get_csv_as_dict_list(csv_file_path)
    return list_cache

def get_contact_points_by_degree_program(degree_program_abbreviation: str) -> list[dict[str, str]]:
    """
    Returns a list of contact points for the specified degree program code.

    :param degree_program_abbreviation: The code for the degree program to filter by.
    :return: A list of dictionaries representing the contact points for the specified degree program.
    """
    categories = get_categories(degree_program_abbreviation)

    all_contact_points = list_contact_points()
    filtered_contact_points = [
        cp for cp in all_contact_points if cp.get("target") in categories
    ]
    return filtered_contact_points