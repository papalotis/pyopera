import platform
import re
from datetime import date, datetime
from typing import Literal, Mapping, Sequence, overload

import streamlit as st

from pyopera.common import (
    DB_TYPE,
    ApproxDate,
    Performance,
    VenueModel,
    WorkYearEntryModel,
    soft_isinstance,
)
from pyopera.deta_base import DatabaseInterface

WORKS_DATES_INTERFACE = DatabaseInterface(WorkYearEntryModel)


def load_db_works_year() -> dict[tuple[str, str], WorkYearEntryModel]:
    raw_data = WORKS_DATES_INTERFACE.fetch_db()
    return {(data.title, data.composer): data for data in raw_data}


PERFORMANCES_INTERFACE = DatabaseInterface(Performance)


def load_db(include_archived_entries: bool = False) -> DB_TYPE:
    raw_data = PERFORMANCES_INTERFACE.fetch_db()
    if not include_archived_entries:
        raw_data = [entry for entry in raw_data if not entry.archived]

    return raw_data


VENUES_INTERFACE = DatabaseInterface(VenueModel)


@overload
def load_db_venues(list_of_entries: Literal[True]) -> list[VenueModel]: ...


@overload
def load_db_venues(list_of_entries: Literal[False] = False) -> dict[str, str]: ...


def load_db_venues(list_of_entries: bool = False) -> dict[str, str] | list[VenueModel]:
    raw_data = VENUES_INTERFACE.fetch_db()

    if list_of_entries:
        return raw_data

    return {data.short_name: data.name for data in raw_data}


def key_is_exception(key: str) -> bool:
    exceptions = {"orchester", "orchestra", "chor"}
    key_alpha_lower = "".join(filter(str.isalpha, key.lower()))

    return key_alpha_lower in exceptions or "ensemble" in key_alpha_lower


def write_person_with_role(d: Mapping[str, Sequence[str]]) -> None:
    d_sorted = dict(sorted(d.items()))

    d_without_exceptions = {k: v for k, v in d_sorted.items() if not key_is_exception(k)}

    for role, persons in d_without_exceptions.items():
        if len(persons) > 0:
            persons_str = ", ".join(persons)
            st.markdown(f"- **{role}** - " + persons_str)

    exception_keys = set(d) - set(d_without_exceptions)
    if len(exception_keys) > 0:
        st.markdown("---")
        for exception in exception_keys:
            to_print = d.get(exception)
            if to_print is not None:
                st.write(f"**{''.join(to_print)}**")


def write_role_with_persons(title: str, dict_of_roles: dict):
    if sum(map(len, dict_of_roles.values())) > 0:
        st.markdown(f"## {title}")
        write_person_with_role(dict_of_roles)


def write_cast_and_leading_team(cast: Mapping[str, Sequence[str]], leading_team: Mapping[str, Sequence[str]]):
    col_left, col_right = st.columns([1, 1])

    with col_left:
        write_role_with_persons("Cast", cast)

    with col_right:
        write_role_with_persons("Leading team", leading_team)


def format_iso_date_to_day_month_year_with_dots(
    date_iso: datetime | str | ApproxDate | None,
) -> str:
    if date_iso is None:
        return "Unknown date"

    if isinstance(date_iso, str):
        date_iso = datetime.fromisoformat(date_iso)
        return date_iso

    if isinstance(date_iso, dict):
        date_iso = ApproxDate(**date_iso)

    if soft_isinstance(date_iso, ApproxDate):
        earliest, latest = date_iso.earliest_date, date_iso.latest_date
        if earliest.year == latest.year:
            if earliest.month == latest.month:
                if earliest.day == latest.day:
                    # exact date
                    return f"{earliest.day:02}.{earliest.month:02}.{earliest.year % 100:02}"
                else:
                    # different day, same month
                    return f"{earliest.day:02}-{latest.day:02}.{earliest.month:02}.{earliest.year % 100:02}"
            else:
                # same year different month
                return (
                    f"{earliest.day:02}.{earliest.month:02}-{latest.day:02}.{latest.month:02}.{earliest.year % 100:02}"
                )
        else:
            # all different
            return f"{earliest.day:02}.{earliest.month:02}.{earliest.year % 100:02}-{latest.day:02}.{latest.month:02}.{latest.year % 100:02}"

    elif isinstance(date_iso, datetime):
        return f"{date_iso.day:02}.{date_iso.month:02}.{date_iso.year % 100:02}"


def format_title(performance: Performance | dict | None) -> str:
    if soft_isinstance(performance, Performance):
        performance = performance.model_dump()

    if performance in (None, {}):
        return "Add new visit"

    name = performance["name"]
    stage = performance["stage"]

    base_string = f"{name} - {stage}"

    if performance["archived"]:
        base_string += " (archived)"

    if performance["date"] is None:
        return base_string

    date = format_iso_date_to_day_month_year_with_dots(performance["date"])
    new_title = f"{date} - {base_string}"
    return new_title


def remove_singular_prefix_from_role(role: str) -> str:
    """
    If a role contains a 'ein', 'eine', 'un', 'une', 'a' at the beginning of the
    role (first character can be uppercase), remove it.
    """
    return re.sub(r"^(ein|eine|un|une|a) ", "", role, flags=re.IGNORECASE)


def format_role(role: str) -> str:
    return remove_singular_prefix_from_role(role)


def runs_on_streamlit_sharing() -> bool:
    return platform.processor() in ("", None)
