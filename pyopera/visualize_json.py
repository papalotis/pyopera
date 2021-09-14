import json
import os
from itertools import chain
from pathlib import Path
from typing import Counter, Sequence, Set

import requests
import streamlit as st
from icecream import ic

NAME = "Vangelis Opera Archiv"

st.set_page_config(page_title=NAME, page_icon=":violin:")

base_url = "https://wf5n5c.deta.dev"
# base_url = 'http://127.0.0.1:8000'


@st.cache(ttl=60 * 2)
def load_data() -> list:

    response = requests.get(f"{base_url}/final_db")

    db = sorted(response.json(), key=lambda el: el["date"])

    return db


db = load_data()


def get_all_names_from_performance(performance: dict) -> Set[str]:

    return_set = {
        name
        for names in chain(
            performance["leading_team"].values(),
            performance["cast"].values(),
        )
        for name in names
    }

    if performance["composer"] != "":
        return_set.add(performance["composer"])

    return return_set


all_names_counter: Counter[str] = Counter(
    name for performance in db for name in get_all_names_from_performance(performance)
)


with st.sidebar:

    st.title(NAME)

    options = st.multiselect(
        "Person filter",
        [value for value, _ in all_names_counter.most_common()],
    )

    db: Sequence[dict] = [
        performance
        for performance in db
        if set(options) <= get_all_names_from_performance(performance)
    ]

    if len(db) == 0:
        st.markdown("## No titles available")
        st.stop()

    def format_title(performance: dict) -> str:
        date = ".".join(performance["date"].split("T")[0].split("-")[::-1])
        name = performance["name"]
        stage = performance["stage"]
        new_title = f"{date} - {name} - {stage}"
        return new_title

    st.session_state["performance"] = st.selectbox(
        "Select Performance",
        db,
        format_func=format_title,
    )


performance = st.session_state["performance"]
st.markdown(f'# {performance["name"]}')

st.markdown(f"## Composer\n\n**{performance['composer']}**")


def hightlight_person_if_selected(person: str) -> str:
    if person in options:
        person = f"**{person}**"

    return person


def write_person_with_role(d: dict) -> None:
    for role, persons in d.items():
        persons_str = ", ".join(
            hightlight_person_if_selected(person) for person in persons
        )
        st.markdown(f"- **{role}** - " + persons_str)


col_left, col_right = st.columns(2)

with col_left:
    cast_team = performance["cast"]
    if len(cast_team) > 0:
        st.markdown("## Cast")
        write_person_with_role(cast_team)

with col_right:
    leading_team = performance["leading_team"]
    if len(leading_team) > 0:
        st.markdown("## Leading Team")
        write_person_with_role(leading_team)
