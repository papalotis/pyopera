import operator
from typing import Mapping, Optional, Sequence, Union

import streamlit as st

from common import DB_TYPE, Performance, fetch_db


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


@st.cache(show_spinner=False, suppress_st_warning=True)
def load_db() -> DB_TYPE:
    with st.spinner("Loading data..."):
        raw_data = fetch_db()
        return sort_entries_by_date(raw_data)


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


def sort_entries_by_date(entries: DB_TYPE) -> DB_TYPE:

    return sorted(entries, key=operator.itemgetter("date"))


def format_iso_date_to_day_month_year_with_dots(date_iso: str) -> str:
    return ".".join(date_iso.split("T")[0].split("-")[::-1])


def format_title(performance: Optional[Union[Performance, dict]]) -> str:
    if performance in (None, {}):
        return "Add new visit"

    date = format_iso_date_to_day_month_year_with_dots(performance["date"])
    name = performance["name"]
    stage = performance["stage"]
    new_title = f"{date} - {name} - {stage}"
    return new_title


def clear_streamlit_cache() -> None:
    import streamlit.legacy_caching

    streamlit.legacy_caching.clear_cache()
