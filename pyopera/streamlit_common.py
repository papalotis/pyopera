import http.client
import operator
from typing import Mapping, Optional, Sequence, Union

import requests
import streamlit as st
from deta import Deta

from common import DB_TYPE, Performance, load_deta_project_key

deta = Deta(load_deta_project_key())

DB = deta.Base("performances")


def reload_db_instance():
    global DB
    DB = deta.Base("performances")


def hide_hamburger_and_change_footer() -> None:
    hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
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


@st.cache(show_spinner=False)
def load_db() -> DB_TYPE:
    with st.spinner("Loading data..."):
        raw_data: DB_TYPE
        try:
            raw_data = DB.fetch().items
        except http.client.CannotSendRequest:
            warning = st.warning(
                "Using alternative download method. Updating database might not be possible."
            )
            project_key = load_deta_project_key()
            project_id = project_key.split("_")[0]
            base_name = "performances"
            base_url = f"https://database.deta.sh/v1/{project_id}/{base_name}"
            headers = {"X-API-Key": project_key, "Content-Type": "application/json"}

            final_url = base_url + "/query"

            response = requests.post(final_url, data="{}", headers=headers)
            raw_data = response.json()["items"]

            reload_db_instance()

            warning.empty()

        return sort_entries_by_date(raw_data)


def key_is_exception(key: str) -> bool:
    exceptions = {"orchester", "orchestra", "chor"}

    key_alpha = "".join(filter(str.isalpha, key.lower()))

    return key_alpha in exceptions or "ensemble" in key_alpha


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
