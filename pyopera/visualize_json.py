from itertools import chain
from typing import Counter, Sequence, Set

import streamlit as st

from common import SHORT_STAGE_NAME_TO_FULL
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

        performance_selectbox = st.empty()

        options = st.multiselect(
            "Person filter",
            [value for value, _ in all_names_counter.most_common()],
        )

        checkbox_only_full = st.checkbox("Only show full entries", value=True)

        db_filtered: Sequence[dict] = [
            performance
            for performance in db
            if set(options) <= get_all_names_from_performance(performance)
            and (
                not checkbox_only_full
                or (len(performance["cast"]) + len(performance["leading_team"])) > 0
            )
        ]

        if len(db_filtered) == 0:
            st.markdown("## No titles available")
            st.stop()

        # performance_selectbox.selectbox()

        performance = performance_selectbox.selectbox(
            "Select Performance", db_filtered, format_func=format_title
        )

    st.markdown(f'# {performance["name"]}')

    stage_name_to_show = SHORT_STAGE_NAME_TO_FULL.get(
        performance["stage"], performance["stage"]
    )
    st.markdown(
        f"#### **{performance['composer']}**\n{stage_name_to_show}"
        f"{' - ' + performance['production'] if performance['stage'] != performance['production'] else ''}"
    )

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

    if performance["comments"] != "":
        st.markdown("---")
        st.markdown(performance["comments"])
