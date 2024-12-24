import unicodedata
from collections import Counter, defaultdict
from typing import Dict, List, Sequence, Set, Tuple

import streamlit as st

from pyopera.common import (
    DB_TYPE,
    Performance,
    WorkYearEntryModel,
)
from pyopera.streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    load_db,
    load_db_venues,
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


def create_markdown_element(
    db: DB_TYPE,
    title_and_composer_to_dates: dict[tuple[str, str], WorkYearEntryModel],
) -> None:
    markdown_string = create_markdown_string(db, title_and_composer_to_dates)
    st.markdown(markdown_string, unsafe_allow_html=True)


def run_operas() -> None:
    db = load_db()
    title_and_composer_to_dates = load_db_works_year()

    create_markdown_element(db, title_and_composer_to_dates)


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

            stages_and_production_ids = Counter(
                (
                    performance.stage,
                    performance.production_key,
                    performance.production_identifying_person,
                )
                for performance in visits
            )

            stages_strings = []
            for (stage, _, id_person), count in stages_and_production_ids.most_common():
                # check if stage is inlcuded multiple times
                # if that is the case add the Inszenierung/Dirigent to the string
                count = sum(
                    1
                    for stage_it, _, _ in stages_and_production_ids
                    if stage_it == stage
                )

                extra_id = f"{id_person}, " if count > 1 and id_person != "" else ""

                stages_strings.append(f"{stage} ({extra_id}{count})")

            stages_string = ", ".join(stages_strings)

            markdown_text.append(
                f"##### {title} ({year})<br><sub>{stages_string}</sub>",
            )

        markdown_text.append("---")

    final_markdown = "\n".join(markdown_text)

    return final_markdown


def run_performances() -> None:
    db = load_db()

    venues_db = load_db_venues()

    markdown_string = create_performances_markdown_string(db, venues_db)

    st.markdown(markdown_string, unsafe_allow_html=True)


def create_performances_markdown_string(
    db: Sequence[Performance], venues_db: dict[str, str]
):
    markdown_text = []

    markdown_text.append("# Performances")

    have_added_following_works_no_dates = False

    for entry in db:
        stage = venues_db.get(entry.stage, entry.stage)

        base_string = f"{stage} - {entry.composer} - {entry.name}\n"
        if entry.date is not None:
            date = format_iso_date_to_day_month_year_with_dots(entry.date)
            base_string = f"{date} - {base_string}"
        elif not have_added_following_works_no_dates:
            markdown_text.append("---")
            have_added_following_works_no_dates = True

        markdown_text.append(base_string)

    return "\n".join(markdown_text)


def create_productions_markdown_string(db: Sequence[Performance]) -> str:
    markdown_text = []

    markdown_text.append("# Productions")

    # group by production id
    production_id_to_performances: defaultdict[
        tuple[str, str, str, str], list[Performance]
    ] = defaultdict(list)
    for performance in db:
        production_id_to_performances[performance.production_key].append(performance)

    last_production_str = ""

    for _, performances in sorted(
        production_id_to_performances.items(),
        key=lambda production_id_performances: (
            production_id_performances[1][0].production,
            production_id_performances[1][0].composer,
        ),
    ):
        first_performance = performances[0]
        if first_performance.production != last_production_str:
            if last_production_str != "":
                # new line is needed the last date is rendered in bold and large
                markdown_text.append("\n---")
            markdown_text.append(f"### {first_performance.production}")
            last_production_str = first_performance.production

        markdown_text.append(
            f"###### {first_performance.composer} - {first_performance.name}\n"
        )

        markdown_text.append(
            ", ".join(
                [
                    format_iso_date_to_day_month_year_with_dots(performance.date)
                    for performance in performances
                ]
            )
        )

    return "\n".join(markdown_text)


def run_productions() -> None:
    db = load_db()

    markdown_string = create_productions_markdown_string(db)

    st.markdown(markdown_string, unsafe_allow_html=True)


def run() -> None:
    modes = {
        ":material/music_note: Operas": run_operas,
        ":material/local_activity: Performances": run_performances,
        # ":material/theaters: Productions": run_productions,
    }

    tabs = st.tabs(modes.keys())

    for tab, mode_function in zip(tabs, modes.values()):
        with tab:
            mode_function()
