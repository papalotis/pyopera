import json
from collections import ChainMap
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Set, Tuple, Union

import requests
from more_itertools import flatten
from pydantic import BaseModel, validator
from pydantic.types import conlist, constr
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
    "SNF-ES": "(ΙΣΝ) Εναλλακτική Σκηνή",
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


NonEmptyStr = constr(min_length=1)
NonEmptyStrList = conlist(NonEmptyStr, min_items=1)
SHA1Str = constr(regex=r"[0-9a-f]{40}")


class Performance(BaseModel):
    name: NonEmptyStr
    date: datetime
    cast: Mapping[NonEmptyStr, NonEmptyStrList]
    leading_team: Mapping[NonEmptyStr, NonEmptyStrList]
    stage: NonEmptyStr
    production: NonEmptyStr
    composer: NonEmptyStr
    comments: str
    is_concertante: bool
    key: SHA1Str = None

    class Config:
        validate_assignment = True
        # allow_reuse = True

    @validator("key", pre=True, always=True, allow_reuse=True)
    def create_key(cls, key, values, **kwargs):

        computed_key = create_key_for_visited_performance_v2(values)

        if key is not None and computed_key != key:
            raise ValueError(
                f"Computed key ({computed_key}) and provided key ({key}) are not the same"
            )

        return computed_key


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


def create_key_for_visited_performance_v2(performance: dict) -> str:

    date = performance["date"]
    if isinstance(date, datetime):
        date = date.isoformat()

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
            + date,
        )
    )
    return sha1(string.encode()).hexdigest()


def get_all_names_from_performance(performance: Performance) -> Set[str]:

    return_set = set(
        flatten(
            ChainMap(
                performance.leading_team,
                performance.cast,
            ).values()
        )
    )

    if performance.composer != "":
        return_set.add(performance.composer)

    return return_set


def filter_only_full_entries(db: DB_TYPE) -> DB_TYPE:
    db_filtered = [
        performance
        for performance in db
        if (len(performance.cast) + len(performance.leading_team)) > 0
    ]

    return db_filtered
