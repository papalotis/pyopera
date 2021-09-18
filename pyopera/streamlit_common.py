import operator
from typing import Callable, Mapping, Optional, Sequence

import requests
import streamlit as st
from deta import Deta

from common import load_deta_project_key

deta = Deta(load_deta_project_key())
DB = deta.Base("performances")


@st.cache(show_spinner=False)
def load_db() -> list:
    with st.spinner("Loading data..."):
        return sort_entries_by_date(DB.fetch().items)


def write_person_with_role(d: Mapping[str, Sequence[str]]) -> None:
    exceptions = {"Orchester", "Orchestra", "Chor"}

    d_without_exceptions = {k: v for k, v in d.items() if k not in exceptions}

    for role, persons in d_without_exceptions.items():
        if len(persons) > 0:
            persons_str = ", ".join(persons)
            st.markdown(f"- **{role}** - " + persons_str)

    if len(exceptions - set(d)) < len(exceptions):
        st.markdown("---")
        for exception in exceptions:
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


def sort_entries_by_date(entries: list) -> list:
    return sorted(entries, key=operator.itemgetter("date"))


def format_title(performance: Optional[dict]) -> str:
    if performance is None:
        return "Add new visit"

    date = ".".join(performance["date"].split("T")[0].split("-")[::-1])
    name = performance["name"]
    stage = performance["stage"]
    new_title = f"{date} - {name} - {stage}"
    return new_title
