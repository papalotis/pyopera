from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence


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
    leading_team: Mapping[str, str]
    stage: str
    composer: str = ""
