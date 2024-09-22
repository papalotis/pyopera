import time

import streamlit as st
from common import WorkYearEntryModel, load_deta_project_key
from deta_base import DetaBaseInterface
from streamlit_common import (
    clear_works_year_cache,
    load_db,
    load_db_works_year,
)


def extract_all_existing_composers_and_titles() -> dict:
    db = load_db()

    composer_to_titles = {}

    for performance in db:
        composer = performance.composer
        title = performance.name

        if composer not in composer_to_titles:
            composer_to_titles[composer] = set()

        composer_to_titles[composer].add(title)

    return composer_to_titles


def run() -> None:
    title_and_composer_to_dates = load_db_works_year()

    composer_to_titles = extract_all_existing_composers_and_titles()

    title_markdown = st.empty()

    existing_composer = st.toggle("Existing composer")

    if existing_composer:
        composer = st.selectbox("Composer", sorted(composer_to_titles.keys()))
        possible_titles = composer_to_titles[composer]
    else:
        composer = st.text_input("Composer")
        possible_titles = []

    toggle_default_existing_title = len(possible_titles) > 0
    existing_title = st.toggle("Existing title", value=toggle_default_existing_title)

    if existing_title:
        title = st.selectbox(
            "Title",
            sorted(possible_titles),
            disabled=len(possible_titles) == 0,
            key="title-existing",
        )
    else:
        title = st.text_input("Title", key="title-new")

    dict_key = (title, composer)

    entry = title_and_composer_to_dates.get(dict_key)

    text_title = "Add work date" if entry is None else "Edit work date"
    title_markdown.markdown(f"## {text_title}")

    default_year = None if entry is None else entry.year

    year = st.number_input("Year", value=default_year, min_value=0)

    interface = DetaBaseInterface(db_name="works_dates", entry_type=WorkYearEntryModel)

    new_entry_key = entry.key if entry is not None else None

    if st.button("Save"):
        new_entry = WorkYearEntryModel(
            title=title, composer=composer, year=year, key=new_entry_key
        )
        interface.put_db(new_entry)
        clear_works_year_cache()
        st.toast("Updated database")
        time.sleep(2.0)
        st.rerun()
