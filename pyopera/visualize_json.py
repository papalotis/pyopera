from typing import Counter

import streamlit as st

from pyopera.common import (
    filter_only_full_entries,
    get_all_names_from_performance,
)
from pyopera.streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    format_title,
    group_cast_and_leading_team_by_segment,
    load_db,
    load_db_venues,
    resolve_company_name,
    write_cast_and_leading_team,
)

try:
    from icecream import ic
except ImportError:

    def ic(*args, **kwargs):
        pass


def run():
    db = load_db()
    venues_db = load_db_venues()

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

        col1, col2 = st.columns(2)
        with col1:
            filter_works_without_date = st.checkbox("Only works with date", value=False)
        if len(db_filtered_full) < len(db):
            with col2:
                checkbox_only_full = st.checkbox("Only full entries", value=True)

            st.markdown(
                f"<sub>{len(db_filtered_full)}/{len(db)} ({ratio_full:.1%}) of entries are full</sub>",
                unsafe_allow_html=True,
            )
            st.progress(ratio_full)
        else:
            checkbox_only_full = False

        db_use_full = db_filtered_full if checkbox_only_full else list(db)

        if filter_works_without_date:
            db_use_full = list(
                filter(lambda performance: performance.date is not None, db_use_full)
            )

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

        performance = performance_selectbox.selectbox(
            "Select Performance", db_filtered, format_func=format_title
        )

    stage_name_to_show = venues_db.get(performance.stage, performance.stage)

    production_name_to_show = resolve_company_name(performance.production)

    if stage_name_to_show != production_name_to_show:
        stage_name_to_show += f" - {production_name_to_show}"

    date_str = (
        format_iso_date_to_day_month_year_with_dots(performance.date)
        if performance.date
        else ""
    )
    st.markdown(
        f"##### **{performance.composers_display}**\n### {performance.name}\n{date_str}\n\n{stage_name_to_show}"
    )

    def hightlight_person_if_selected(person: str) -> str:
        if person in options:
            person = f"**{person}**"

        return person

    def highlight_mapping(mapping: dict[str, list[str]]) -> dict[str, list[str]]:
        return {
            role: [hightlight_person_if_selected(person) for person in persons]
            for role, persons in mapping.items()
        }

    if performance.has_segments:
        blocks = group_cast_and_leading_team_by_segment(
            performance.cast,
            performance.leading_team,
            performance.segments,
            performance.segment_lookup,
        )

        titles_shown = False
        for segment, cast_block, leading_team_block in blocks:
            if len(cast_block) == 0 and len(leading_team_block) == 0:
                continue

            # The whole-performance block has no heading. The Cast / Leading team
            # headings belong to the whole-performance block if it has content,
            # otherwise to the first segment block that has content.
            show_titles = not titles_shown
            titles_shown = True

            if segment is not None:
                st.markdown(f"### {segment}")

            write_cast_and_leading_team(
                highlight_mapping(cast_block),
                highlight_mapping(leading_team_block),
                show_titles=show_titles,
            )
    else:
        write_cast_and_leading_team(
            highlight_mapping(performance.cast),
            highlight_mapping(performance.leading_team),
        )

    if performance.comments != "":
        st.markdown("---")
        st.markdown(performance.comments)
