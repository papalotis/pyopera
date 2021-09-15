import json
import os
from itertools import chain
from pathlib import Path
from typing import Counter, Optional, Sequence, Set

import streamlit as st

from streamlit_common import format_title, load_db, write_cast_and_leading_team

try:
    from icecream import ic
except ImportError:
    ic = lambda *a: a


def run():

    db = load_db()

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
        name
        for performance in db
        for name in get_all_names_from_performance(performance)
    )

    with st.sidebar:

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

        st.session_state["performance"] = st.selectbox(
            "Select Performance", db, format_func=format_title
        )

    performance = st.session_state["performance"]
    st.markdown(f'# {performance["name"]}')

    st.markdown(f"## Composer\n\n**{performance['composer']}**")

    def hightlight_person_if_selected(person: str) -> str:

        if person in options:
            person = f"**{person}**"

        return person

    cast_highlighted = {
        role: [hightlight_person_if_selected(person) for person in persons]
        for role, persons in performance["cast"].items()
    }

    leading_team_highlighted = {
        role: [hightlight_person_if_selected(person) for person in persons]
        for role, persons in performance["leading_team"].items()
    }

    write_cast_and_leading_team(cast_highlighted, leading_team_highlighted)
