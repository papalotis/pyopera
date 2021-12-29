from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

import streamlit as st

from common import DB_TYPE, Performance, convert_short_stage_name_to_long_if_available
from streamlit_common import format_iso_date_to_day_month_year_with_dots, load_db


def group_works_by_composer_and_name(
    db: DB_TYPE,
) -> Dict[Tuple[str, str], List[Performance]]:
    groups = defaultdict(list)

    for performance in db:
        composer = performance.composer
        name = performance.name
        groups[(composer, name)].append(performance)

    return groups


def map_composer_to_names(db: DB_TYPE) -> Dict[str, Set[str]]:
    composer_to_titles = defaultdict(set)

    for performance in db:
        composer = performance.composer
        name = performance.name
        composer_to_titles[composer].add(name)

    return composer_to_titles


def run() -> None:
    db = load_db()
    groups = group_works_by_composer_and_name(db)
    composer_to_titles = map_composer_to_names(db)
    st.title("Overview")

    for composer in sorted(composer_to_titles.keys()):
        st.header(composer)

        for title in sorted(composer_to_titles[composer]):
            st.markdown(f"#### {title}")
            visits = groups[composer, title]

            stages = Counter(performance.stage for performance in visits)

            stages_strings = []
            for stage, count in stages.most_common():
                stages_strings.append(f"{stage} ({count})")

            stages_string = ", ".join(stages_strings)
            st.markdown(f"<sub>{stages_string}</sub>", unsafe_allow_html=True)
