import operator
import re
from datetime import datetime
from typing import Any, Mapping, Optional, Sequence, Union

import streamlit as st
from approx_dates.models import ApproxDate
from common import DB_TYPE, Performance, WorkYearEntryModel, load_deta_project_key
from deta_base import DetaBaseInterface


def hide_hamburger_and_change_footer() -> None:
    hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            footer:after {
                content:"Made by Panagiotis"; 
                visibility: visible;
                display: block;
                position: relative;
                #background-color: red;
                padding: 5px;
                top: 2px;
            }
            </style>
            """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def load_data_raw() -> Sequence[Mapping[str, Any]]:
    base_interface = DetaBaseInterface(load_deta_project_key())
    with st.spinner("Loading data..."):
        raw_data = base_interface.fetch_db()
        return raw_data


def load_works_year_raw() -> Mapping[tuple[str, str], WorkYearEntryModel]:
    base_interface = DetaBaseInterface(load_deta_project_key(), db_name="works_year")
    with st.spinner("Loading works year data..."):
        raw_data = base_interface.fetch_db()
        return {
            (data["title"], data["composer"]): WorkYearEntryModel(**data)
            for data in raw_data
        }


def sort_entries_by_date(entries: DB_TYPE) -> DB_TYPE:
    return sorted(entries, key=lambda x: x.date.earliest_date, reverse=True)


def verify_and_sort_db() -> DB_TYPE:
    raw_data = load_data_raw()
    verified_data = [Performance(**data) for data in raw_data]
    sorted_data = sort_entries_by_date(verified_data)

    return sorted_data


def reset_existing_db():
    st.session_state["DB"] = None
    st.session_state["DB_WORKS_YEAR"] = None


def clear_db_cache():
    st.session_state["DB"] = None


def clear_works_year_cache():
    st.session_state["DB_WORKS_YEAR"] = None


def load_db() -> DB_TYPE:
    if "DB" not in st.session_state or st.session_state["DB"] is None:
        st.session_state["DB"] = verify_and_sort_db()

    return st.session_state["DB"]


def load_db_works_year() -> Mapping[tuple[str, str], WorkYearEntryModel]:
    if (
        "DB_WORKS_YEAR" not in st.session_state
        or st.session_state["DB_WORKS_YEAR"] is None
    ):
        st.session_state["DB_WORKS_YEAR"] = load_works_year_raw()

    return st.session_state["DB_WORKS_YEAR"]


def key_is_exception(key: str) -> bool:
    exceptions = {"orchester", "orchestra", "chor"}
    key_alpha_lower = "".join(filter(str.isalpha, key.lower()))

    return key_alpha_lower in exceptions or "ensemble" in key_alpha_lower


def write_person_with_role(d: Mapping[str, Sequence[str]]) -> None:
    d_without_exceptions = {k: v for k, v in d.items() if not key_is_exception(k)}

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


def write_cast_and_leading_team(
    cast: Mapping[str, Sequence[str]], leading_team: Mapping[str, Sequence[str]]
):
    col_left, col_right = st.columns([1, 1])

    with col_left:
        write_role_with_persons("Cast", cast)

    with col_right:
        write_role_with_persons("Leading team", leading_team)


def format_iso_date_to_day_month_year_with_dots(
    date_iso: Union[datetime, str, ApproxDate],
) -> str:
    if isinstance(date_iso, str):
        date_iso = datetime.fromisoformat(date_iso)

    if isinstance(date_iso, ApproxDate):
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
                return f"{earliest.day:02}.{earliest.month:02}-{latest.day:02}.{latest.month:02}.{earliest.year % 100:02}"
        else:
            # all different
            return f"{earliest.day:02}.{earliest.month:02}.{earliest.year % 100:02}-{latest.day:02}.{latest.month:02}.{latest.year % 100:02}"

    elif isinstance(date_iso, datetime):
        return f"{date_iso.day:02}.{date_iso.month:02}.{date_iso.year % 100:02}"


def format_title(performance: Optional[Union[Performance, dict]]) -> str:
    if performance.__class__.__name__ == Performance.__name__:
        performance = performance.dict()

    if performance in (None, {}):
        return "Add new visit"

    date = format_iso_date_to_day_month_year_with_dots(performance["date"])
    name = performance["name"]
    stage = performance["stage"]
    new_title = f"{date} - {name} - {stage}"
    return new_title


def remove_singular_prefix_from_role(role: str) -> str:
    """
    If a role contains a 'ein' or 'eine' at the beginning of the
    role remove it
    """
    return re.sub(r"^[eE]ine?\s", "", role)


def format_role(role: str) -> str:
    return remove_singular_prefix_from_role(role)


def clear_streamlit_cache() -> None:
    import streamlit

    streamlit.cache_data.clear()
