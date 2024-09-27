import unicodedata
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

import streamlit as st
from common import (
    DB_TYPE,
    Performance,
    WorkYearEntryModel,
    convert_short_stage_name_to_long_if_available,
)
from streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    load_db,
    load_db_works_year,
)


def group_works_by_composer_and_name(
    db: DB_TYPE,
) -> Dict[Tuple[str, str], List[Performance]]:
    groups = defaultdict(list)

    for performance in db:
        composer = performance.composer
        name = performance.name
        groups[(composer, name)].append(performance)

    return groups


EP = False


def map_composer_to_names(db: DB_TYPE) -> Dict[str, Set[str]]:
    composer_to_titles = defaultdict(set)

    for performance in db:
        composer = performance.composer
        name = performance.name
        composer_to_titles[composer].add(name)

        if EP and "richard strauss" in composer.lower():
            st.write(f"{composer} {name} {performance.date}")

    return composer_to_titles


def remove_greek_diacritics(text: str) -> str:
    d = {ord("\N{COMBINING ACUTE ACCENT}"): None}
    return unicodedata.normalize("NFD", text).translate(d)


def get_year(
    title: str,
    composer: str,
    title_and_composer_to_dates: Dict[Tuple[str, str], WorkYearEntryModel],
) -> int:
    try:
        return title_and_composer_to_dates[(title, composer)].year
    except KeyError:
        if "ring-trilogie" in title.lower():
            new_title = title.replace(" (Ring-Trilogie)", "")
            return get_year(new_title, composer, title_and_composer_to_dates)

        return -1


def run_operas() -> None:
    db = load_db()
    title_and_composer_to_dates = load_db_works_year()
    markdown_string = create_markdown_string(db, title_and_composer_to_dates)

    st.markdown(markdown_string, unsafe_allow_html=True)


def create_markdown_string(db, title_and_composer_to_dates):
    groups = group_works_by_composer_and_name(db)
    composer_to_titles = map_composer_to_names(db)

    markdown_text = []

    markdown_text.append("# Operas")

    for composer in sorted(
        composer_to_titles.keys(), key=lambda composer: composer.split(" ")[-1]
    ):
        markdown_text.append(f"#### {remove_greek_diacritics(composer).upper()}")

        for title in sorted(
            composer_to_titles[composer],
            key=lambda title: get_year(title, composer, title_and_composer_to_dates),
        ):
            year = get_year(title, composer, title_and_composer_to_dates)
            visits = groups[composer, title]

            stages = Counter(performance.stage for performance in visits)

            stages_strings = []
            for stage, count in stages.most_common():
                stages_strings.append(f"{stage} ({count})")

            stages_string = ", ".join(stages_strings)

            markdown_text.append(
                f"##### {title} ({year})<br><sub>{stages_string}</sub>",
            )

        markdown_text.append("---")

    final_markdown = "\n".join(markdown_text)
    return final_markdown


def run_performances() -> None:
    db = load_db()

    markdown_string = create_performances_markdown_string(db)

    st.markdown(markdown_string, unsafe_allow_html=True)


def create_performances_markdown_string(db):
    markdown_text = []

    markdown_text.append("# Performances")

    for entry in db:
        stage = convert_short_stage_name_to_long_if_available(entry.stage)
        date = format_iso_date_to_day_month_year_with_dots(entry.date)
        markdown_text.append(f"{date} - {stage} - {entry.composer} - {entry.name}\n")

    return "\n".join(markdown_text)


def run() -> None:
    modes = {
        "Operas": run_operas,
        "Performances": run_performances,
    }

    with st.sidebar:
        mode = st.radio("Overview mode", modes)
        mode_function = modes[mode]

    mode_function()
