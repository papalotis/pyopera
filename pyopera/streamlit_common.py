import operator
from typing import Callable, Optional

import requests
import streamlit as st
from deta import Deta

from common import load_deta_project_key

deta = Deta(load_deta_project_key())
DB = deta.Base("performances")


@st.cache
def load_db() -> list:
    with st.spinner("Loading data..."):
        return sort_entries_by_date(DB.fetch().items)


def write_person_with_role(d: dict) -> None:
    for role, persons in d.items():
        if len(persons) > 0:
            persons_str = ", ".join(persons)
            st.markdown(f"- **{role}** - " + persons_str)


def write_role_with_persons(title: str, dict_of_roles: dict):

    if sum(map(len, dict_of_roles.values())) > 0:
        st.markdown(f"## {title}")
        write_person_with_role(dict_of_roles)


def write_cast_and_leading_team(cast: dict, leading_team: dict):

    col_left, col_right = st.columns([1, 1])

    with col_left:
        write_role_with_persons("Cast", cast)

    with col_right:
        write_role_with_persons("Leading team", leading_team)


def sort_entries_by_date(entires: list) -> list:
    return sorted(entires, key=operator.itemgetter("date"))


base_url = "https://wf5n5c.deta.dev"
# base_url = 'http://127.0.0.1:8000'


def create_load_final_db() -> Callable[[], list]:

    if "db_hash" not in st.session_state:
        st.session_state["db_hash"] = None
        st.session_state["existing_db"] = None

    @st.cache(ttl=60 * 60 * 2, show_spinner=False)
    def load_data() -> list:

        with st.spinner("Loading data ..."):
            hash = requests.get(f"{base_url}/final_db/hash").json()["hash"]
            if (
                hash == st.session_state["db_hash"]
                and st.session_state["existing_db"] is not None
            ):
                return st.session_state["existing_db"]

            response = requests.get(f"{base_url}/final_db")
            if response.ok:

                st.session_state["db_hash"] = hash

                st.session_state["existing_db"] = sorted(
                    response.json(), key=lambda el: el["date"]
                )

                return st.session_state["existing_db"]

        raise RuntimeError()

    return load_data


def create_load_manual_db() -> Callable[[], list]:
    @st.cache(ttl=60 * 60, show_spinner=False)
    def load_existing_entries() -> list:
        with st.spinner("Loading existing entries ..."):
            response = requests.get(f"{base_url}/vangelis_db")
            db = response.json()
            return sort_entries_by_date(db)

    return load_existing_entries


def format_title(performance: Optional[dict]) -> str:
    if performance is None:
        return "Add new visit"

    date = ".".join(performance["date"].split("T")[0].split("-")[::-1])
    name = performance["name"]
    stage = performance["stage"]
    new_title = f"{date} - {name} - {stage}"
    return new_title
