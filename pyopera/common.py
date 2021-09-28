import json
from collections import ChainMap
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping, Sequence, Set, Tuple, Union

import requests
from more_itertools import flatten
from typing_extensions import TypedDict
from unidecode import unidecode

GERMAN_MONTH_TO_INT = {
    "Januar": 1,
    "Jänner": 1,
    "Februar": 2,
    "März": 3,
    "April": 4,
    "Mai": 5,
    "Juni": 6,
    "Juli": 7,
    "August": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Dezember": 12,
}

SHORT_STAGE_NAME_TO_FULL = {
    "WSO": "Wiener Staatsoper",
    "TAW": "Theater an der Wien",
    "VOW": "Volksoper Wien",
    "DOB": "Deutsche Oper Berlin",
    "KOB": "Komische Oper Berlin",
    "SUL": "Staatsoper Unter den Linden",
    "GTLF": "Teatro La Fenice",
    "KOaF": "Kammeroper am Fleischmarkt",
    "MMAT": "Μέγαρο Μουσικής Αθηνών",
    "SNF": "Αίθουσα Σταύρος Νιάρχος",
    "SNF-ES": "(SNF) Εναλλακτική Σκηνή",
    "OLY": "Θέατρο Oλύμπια",
}


def austria_date_to_datetime(date_str: str) -> datetime:
    """
    Convert "Samstag, 28. August 2021" to datetime(2021, 08, 28)
    """

    day_name, day, month_name, year = date_str.split(" ")
    day_int = int(day.replace(".", ""))
    month_int = GERMAN_MONTH_TO_INT[month_name]
    year_int = int(year)
    return datetime(year_int, month_int, day_int)


def convert_short_stage_name_to_long_if_available(short_state_name: str) -> str:
    return SHORT_STAGE_NAME_TO_FULL.get(short_state_name, short_state_name)


class Performance(TypedDict):
    name: str
    date: str
    cast: Mapping[str, Sequence[str]]
    leading_team: Mapping[str, Sequence[str]]
    stage: str
    production: str
    composer: str
    comments: str
    is_concertante: bool
    key: str


DB_TYPE = Sequence[Performance]


def export_as_json(performances: Sequence[Performance]) -> str:
    def default(obj: Any) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()

        raise TypeError("Unknown type: ", type(obj))

    to_save = {
        "$schema": "https://raw.githubusercontent.com/papalotis/pyopera/main/schemas/performance_schema.json",
        "data": performances,
    }

    return json.dumps(to_save, default=default)


def normalize_title(title: str) -> str:
    return "".join(
        filter(
            str.isalpha,
            unidecode(title)
            .split("(")[0]
            .split("/")[0]
            .lower()
            .replace(" ", "")
            .strip(),
        )
    )


def load_deta_project_key() -> str:
    try:
        import os

        return os.environ["project_key"]
    except KeyError:
        try:
            deta_project_key: str = json.loads(
                (Path(__file__).parent.parent / "deta_project_data.json").read_text()
            )["Project Key"]
        except (FileNotFoundError, KeyError) as error:
            try:
                import streamlit as st
            except ImportError:
                raise error

            st.error(
                "Cannot find database key. Cannot continue! Please reload the page."
            )
            st.stop()

    return deta_project_key


def create_key_for_visited_performance_v2(performance: Performance) -> str:

    string = "".join(
        filter(
            str.isalnum,
            "".join(
                map(
                    normalize_title,
                    (
                        performance["name"],
                        performance["stage"],
                        performance["composer"],
                    ),
                )
            )
            + performance["date"],
        )
    )
    return sha1(string.encode()).hexdigest()


def get_all_names_from_performance(performance: Performance) -> Set[str]:

    return_set = set(
        flatten(
            ChainMap(
                performance["leading_team"],
                performance["cast"],
            ).values()
        )
    )

    if performance["composer"] != "":
        return_set.add(performance["composer"])

    return return_set


def filter_only_full_entries(db: DB_TYPE) -> DB_TYPE:
    db_filtered = [
        performance
        for performance in db
        if (len(performance["cast"]) + len(performance["leading_team"])) > 0
    ]

    return db_filtered


def get_db_base_url() -> str:
    project_key = load_deta_project_key()
    project_key_split = project_key.split("_")
    assert len(project_key_split) == 2
    project_id = project_key_split[0]
    base_name = "performances"
    base_url = f"https://database.deta.sh/v1/{project_id}/{base_name}"
    return base_url


def create_db_request_base_url_and_headers() -> Tuple[str, Mapping[str, str]]:
    base_url = get_db_base_url()
    project_key = load_deta_project_key()

    headers = {"X-API-Key": project_key, "Content-Type": "application/json"}

    return base_url, headers


def fetch_db() -> DB_TYPE:
    base_url, headers = create_db_request_base_url_and_headers()

    final_url = base_url + "/query"

    response = requests.post(final_url, data={}, headers=headers)
    response.raise_for_status()
    raw_data = response.json()["items"]

    return raw_data


def put_db(items_to_put: Union[Performance, Sequence[Performance]]) -> None:
    if isinstance(items_to_put, dict):
        items_to_put = [items_to_put]

    assert all("key" in item for item in items_to_put)

    base_url, headers = create_db_request_base_url_and_headers()

    final_url = base_url + "/items"
    final_data = {"items": items_to_put}

    response = requests.put(final_url, json=final_data, headers=headers)
    response.raise_for_status()

    response_json = response.json()

    if "failed" in response_json:
        raise ValueError(
            f"The following items could not be PUT in the database:\n{response_json['failed']}"
        )


def delete_item_db(key_to_delete: Union[Performance, str]) -> None:
    if isinstance(key_to_delete, dict):
        key_to_delete = key_to_delete["key"]

    base_url, headers = create_db_request_base_url_and_headers()

    final_url = base_url + f"/items/{key_to_delete}"

    response = requests.delete(final_url, headers=headers)
    response.raise_for_status()
