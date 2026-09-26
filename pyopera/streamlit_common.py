import platform
import re
from datetime import date, datetime
from typing import Literal, Mapping, Sequence, overload

import streamlit as st

from pyopera.common import (
    CAST_SECTION,
    DB_TYPE,
    LEADING_TEAM_SECTION,
    ApproxDate,
    CompanyModel,
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


COMPANIES_INTERFACE = DatabaseInterface(CompanyModel)


@overload
def load_db_companies(list_of_entries: Literal[True]) -> list[CompanyModel]: ...


@overload
def load_db_companies(list_of_entries: Literal[False] = False) -> dict[str, str]: ...


def load_db_companies(list_of_entries: bool = False) -> dict[str, str] | list[CompanyModel]:
    raw_data = COMPANIES_INTERFACE.fetch_db()

    if list_of_entries:
        return raw_data

    return {data.short_name: data.name for data in raw_data}


def resolve_company_name(short_name: str) -> str:
    """Resolve a production company short name to its full name.

    Precedence is companies -> venues -> the raw short name, so that short codes
    which have not been migrated to the companies table yet still resolve.
    """
    companies_db = load_db_companies()
    if short_name in companies_db:
        return companies_db[short_name]

    venues_db = load_db_venues()
    return venues_db.get(short_name, short_name)


def key_is_exception(key: str) -> bool:
    exceptions = {"orchester", "orchestra", "chor"}
    key_alpha_lower = "".join(filter(str.isalpha, key.lower()))

    return key_alpha_lower in exceptions or "ensemble" in key_alpha_lower


def write_person_with_role(
    d: Mapping[str, Sequence[str]],
    *,
    section: str,
    segment_lookup: Mapping[tuple[str, str, str], Sequence[str]] | None = None,
) -> None:
    d_sorted = dict(sorted(d.items()))

    d_without_exceptions = {k: v for k, v in d_sorted.items() if not key_is_exception(k)}

    for role, persons in d_without_exceptions.items():
        if len(persons) > 0:
            persons_str = ", ".join(
                format_person_with_segments(person, section, role, segment_lookup) for person in persons
            )
            st.markdown(f"- **{role}** - " + persons_str)

    exception_keys = set(d) - set(d_without_exceptions)
    if len(exception_keys) > 0:
        st.markdown("---")
        for exception in exception_keys:
            to_print = d.get(exception)
            if to_print is not None:
                st.write(f"**{''.join(to_print)}**")


def format_person_with_segments(
    person: str,
    section: str,
    role: str,
    segment_lookup: Mapping[tuple[str, str, str], Sequence[str]] | None,
) -> str:
    """Annotate a person with the segments their credit applies to.

    Credits that apply to the whole performance (empty segment list) are left
    unannotated.
    """
    if segment_lookup is None:
        return person

    segments = segment_lookup.get((section, role, person), [])
    if len(segments) == 0:
        return person

    return f"{person} ({', '.join(segments)})"


def write_role_with_persons(
    title: str,
    dict_of_roles: dict,
    *,
    section: str,
    segment_lookup: Mapping[tuple[str, str, str], Sequence[str]] | None = None,
    show_title: bool = True,
):
    if sum(map(len, dict_of_roles.values())) > 0:
        if show_title:
            st.markdown(f"## {title}")
        write_person_with_role(dict_of_roles, section=section, segment_lookup=segment_lookup)


def write_cast_and_leading_team(
    cast: Mapping[str, Sequence[str]],
    leading_team: Mapping[str, Sequence[str]],
    *,
    segment_lookup: Mapping[tuple[str, str, str], Sequence[str]] | None = None,
    show_titles: bool = True,
):
    col_left, col_right = st.columns([1, 1])

    with col_left:
        write_role_with_persons(
            "Cast", cast, section=CAST_SECTION, segment_lookup=segment_lookup, show_title=show_titles
        )

    with col_right:
        write_role_with_persons(
            "Leading team",
            leading_team,
            section=LEADING_TEAM_SECTION,
            segment_lookup=segment_lookup,
            show_title=show_titles,
        )


def group_cast_and_leading_team_by_segment(
    cast: Mapping[str, Sequence[str]],
    leading_team: Mapping[str, Sequence[str]],
    segments: Sequence[str],
    segment_lookup: Mapping[tuple[str, str, str], Sequence[str]],
) -> list[tuple[str | None, dict[str, list[str]], dict[str, list[str]]]]:
    """Split cast and leading team into whole-performance and per-segment blocks.

    Returns a list of ``(segment_label, cast, leading_team)`` tuples. The first
    entry has ``segment_label is None`` and holds every credit that applies to the
    whole performance. The remaining entries follow the given ``segments`` order and
    hold only the credits specific to that segment.
    """
    whole_cast: dict[str, list[str]] = {}
    whole_leading_team: dict[str, list[str]] = {}
    segment_cast: dict[str, dict[str, list[str]]] = {segment: {} for segment in segments}
    segment_leading_team: dict[str, dict[str, list[str]]] = {segment: {} for segment in segments}

    for section, mapping, whole, per_segment in (
        (CAST_SECTION, cast, whole_cast, segment_cast),
        (LEADING_TEAM_SECTION, leading_team, whole_leading_team, segment_leading_team),
    ):
        for role, persons in mapping.items():
            for person in persons:
                person_segments = segment_lookup.get((section, role, person), [])
                if len(person_segments) == 0:
                    whole.setdefault(role, []).append(person)
                else:
                    for segment in person_segments:
                        per_segment.setdefault(segment, {}).setdefault(role, []).append(person)

    blocks: list[tuple[str | None, dict[str, list[str]], dict[str, list[str]]]] = [
        (None, whole_cast, whole_leading_team)
    ]
    blocks.extend(
        (segment, segment_cast[segment], segment_leading_team[segment]) for segment in segments
    )

    return blocks


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
