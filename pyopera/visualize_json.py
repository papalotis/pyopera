from itertools import chain
from pathlib import Path
from typing import Counter, Sequence, Set

import streamlit as st
from icecream import ic

from combine_with_v import filter_by_excel_file

st.title("WSO Archive Visualization")


@st.cache
def load_data() -> list:

    parent_path = Path(__file__).parent
    excel_path = parent_path / "vangelos.xlsx"
    json_path = [
        parent_path.parent / "db" / works_db_filename
        for works_db_filename in [
            "wso_performances.json",
        ]
    ]
    json_work_path = parent_path.parent / "db" / "works_info_db.json"

    db = filter_by_excel_file(json_path, excel_path, json_work_path)

    return db


db = load_data()


def get_all_names_from_performance(performance: dict) -> Set[str]:
    return {
        name
        for names in chain(
            performance["leading_team"].values(),
            performance["cast"].values(),
        )
        for name in names
    }


all_names_counter: Counter[str] = Counter(
    name for performance in db for name in get_all_names_from_performance(performance)
)

options = st.multiselect(
    "Person filter",
    [value for value, _ in all_names_counter.most_common()],
)

db = [
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


performance = st.selectbox("Select Performance", db, format_func=format_title)


st.markdown(f'## {performance["name"]}')

st.markdown(f"### Composer\n\n**{performance['composer']}**")

leading_team = performance["leading_team"]
if len(leading_team) > 0:
    st.markdown("### Leading Team")
    for role, persons in leading_team.items():
        persons_str = ", ".join(persons)
        st.markdown(f"- **{role}** - " + persons_str)

cast_team = performance["cast"]
if len(cast_team) > 0:
    st.markdown("### Cast")
    for role, persons in cast_team.items():
        persons_str = ", ".join(persons)
        st.markdown(f"- **{role}** - " + persons_str)


st.markdown("#### Based on https://archiv.wiener-staatsoper.at")
