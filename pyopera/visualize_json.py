from typing import Counter, Sequence

import streamlit as st

from common import (
    SHORT_STAGE_NAME_TO_FULL,
    Performance,
    filter_only_full_entries,
    get_all_names_from_performance,
)
from streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    format_title,
    load_db,
    write_cast_and_leading_team,
)

try:
    from icecream import ic
except ImportError:
    ic = lambda *a: a


def run():

    db = load_db()

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
        db_filtered_full = filter_only_full_entries(db)
        ratio_full = len(db_filtered_full) / len(db)

        if len(db_filtered_full) < len(db):
            checkbox_only_full = st.checkbox("Only show full entries", value=True)

            st.markdown(
                f"<sub>{len(db_filtered_full)}/{len(db)} ({ratio_full * 100:.0f}%) of entries are full</sub>",
                unsafe_allow_html=True,
            )
            st.progress(ratio_full)
        else:
            checkbox_only_full = False

        db_use_full = db_filtered_full if checkbox_only_full else list(db)
        db_filtered = list(
            filter(
                lambda performance: set(options)
                <= get_all_names_from_performance(performance),
                db_use_full,
            )
        )

        if len(db_filtered) == 0:
            st.markdown("## No titles available")
            st.stop()

        # performance_selectbox.selectbox()

        performance: Performance = performance_selectbox.selectbox(
            "Select Performance", db_filtered, format_func=format_title
        )

    stage_name_to_show = SHORT_STAGE_NAME_TO_FULL.get(
        performance.stage, performance.stage
    )
    st.markdown(
        f"##### **{performance.composer}**\n### {performance.name}\n{format_iso_date_to_day_month_year_with_dots(performance.date)}\n\n{stage_name_to_show}"
    )

    # st.markdown(f"# {performance.name}")
    # st.markdown(format_iso_date_to_day_month_year_with_dots(performance.date))

    # st.markdown(
    #     f"#### **{performance.composer}**\n{stage_name_to_show}"
    #     f"{' - ' + performance.production if performance.stage != performance.production else ''}"
    # )

    def hightlight_person_if_selected(person: str) -> str:

        if person in options:
            person = f"**{person}**"

        return person

    cast_highlighted = {
        role: [hightlight_person_if_selected(person) for person in persons]
        for role, persons in performance.cast.items()
    }

    leading_team_highlighted = {
        role: [hightlight_person_if_selected(person) for person in persons]
        for role, persons in performance.leading_team.items()
    }

    write_cast_and_leading_team(cast_highlighted, leading_team_highlighted)

    if performance.comments != "":
        st.markdown("---")
        st.markdown(performance.comments)
