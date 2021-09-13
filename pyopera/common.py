import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence, TypeVar

from unidecode import unidecode

from pyopera.excel_to_json import ExcelRow


def austria_date_to_datetime(date_str: str) -> datetime:
    """
    Convert "Samstag, 28. August 2021" to datetime(2021, 08, 28)
    """

    GERMAN_MONTH_TO_INT = {
        "Januar": 1,
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
    day_name, day, month_name, year = date_str.split(" ")
    day_int = int(day[:-1])
    month_int = GERMAN_MONTH_TO_INT[month_name]
    year_int = int(year)
    return datetime(year_int, month_int, day_int)


@dataclass
class Performance:
    name: str
    date: datetime
    cast: Mapping[str, Sequence[str]]
    leading_team: Mapping[str, Sequence[str]]
    stage: str
    composer: str = ""

T = TypeVar('T', Performance, ExcelRow)



def export_as_json(performances: Sequence[T]) -> str:
    def default(obj: Any) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, Performance):
            return asdict(obj)
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
