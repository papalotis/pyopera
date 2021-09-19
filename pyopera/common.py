import json
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any, Mapping, Sequence, Set

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
}


def austria_date_to_datetime(date_str: str) -> datetime:
    """
    Convert "Samstag, 28. August 2021" to datetime(2021, 08, 28)
    """

    day_name, day, month_name, year = date_str.split(" ")
    day_int = int(day[:-1])
    month_int = GERMAN_MONTH_TO_INT[month_name]
    year_int = int(year)
    return datetime(year_int, month_int, day_int)


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

            st.error("Cannot find database key. Cannot continue!")
            st.stop()

    return deta_project_key


def create_key_for_visited_performance(performance: dict) -> str:
    import hashlib

    string = "".join(
        filter(
            str.isalnum,
            "".join(
                map(
                    normalize_title,
                    (
                        performance["name"],
                        performance["stage"],
                    ),
                )
            )
            + performance["date"],
        )
    )
    return hashlib.sha1(string.encode()).hexdigest()[-12:]


def create_key_for_visited_performance_v2(performance: dict) -> str:
    import hashlib

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
    return hashlib.sha1(string.encode()).hexdigest()


def get_all_names_from_performance(performance: Performance) -> Set[str]:

    return_set = {
        name
        for names in chain(
            performance["leading_team"].values(),
            performance["cast"].values(),
        )
        for name in names
    }

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
