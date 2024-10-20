import streamlit as st
from pydantic import ValidationError
from icecream import ic

from pyopera.common import WorkYearEntryModel
from pyopera.deta_base import DatabaseInterface
from pyopera.streamlit_common import (
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


def delete_from_db(to_delete: str) -> None:
    assert isinstance(st.session_state.interface, DatabaseInterface) 
    st.session_state.interface.delete_item_db(to_delete)
    st.toast("Deleted entry", icon=":material/delete:")


def upload_to_db(**kwargs) -> None:
    try:
        if kwargs["key"] is None:
            del kwargs["key"]

        new_entry = WorkYearEntryModel(**kwargs)
    except ValidationError as e:
        ic(kwargs)
        ic(e)
        st.toast(f"Error: {e}", icon=":material/error:")
        return

    INTERFACE.put_db(new_entry)
    st.toast("Updated database", icon=":material/cloud_sync:")


INTERFACE = DatabaseInterface(WorkYearEntryModel)


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

    new_entry_key = entry.key if entry is not None else None

    button_text_start = "Update" if entry is not None else "Add"
    button_text = f"{button_text_start} work year of first performance"

    st.button(
        button_text,
        on_click=upload_to_db,
        kwargs=dict(key=new_entry_key, composer=composer, title=title, year=year),
    )

    if new_entry_key is not None:
        st.button(
            "Delete work year",
            on_click=delete_from_db,
            kwargs=dict(to_delete=new_entry_key),
        )
