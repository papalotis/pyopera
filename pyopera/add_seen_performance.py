import json
import time
from datetime import datetime
from logging import exception
from pathlib import Path
from tokenize import Name

import requests
import streamlit as st

from excel_to_json import ExcelRow
from pyopera.common import create_key_for_visited_performance

base_url = "http://127.0.0.1:8000"


def send_new_performance(new_performance: dict) -> requests.Response:

    return requests.post(f"{base_url}/add_new_performance_seen", json=new_performance)


def delete_performance_by_key(key: str) -> None:
    return requests.delete(f"{base_url}/vangelis_db/{key}")


def load_existing_entries():
    db = requests.get(f"{base_url}/vangelis_db").json()
    return db


def update_existing_entries():
    st.session_state["db"] = load_existing_entries()


def format_title(performance: dict) -> str:
    date = ".".join(performance["date"].split("T")[0].split("-")[::-1])
    name = performance["name"]
    stage = performance["stage"]
    new_title = f"{date} - {name} - {stage}"
    return new_title


st.title("Add a new visited performance")


update_existing = st.checkbox("Update existing")
if update_existing:
    if "db" not in st.session_state:
        with st.spinner("Loading existing entries"):
            update_existing_entries()

    entry_to_update: dict = st.selectbox(
        "Select entry", st.session_state["db"], format_func=format_title
    )


default_name = entry_to_update["name"] if update_existing else ""
default_production = entry_to_update["production"] if update_existing else ""
default_stage = entry_to_update["stage"] if update_existing else ""
default_composer = entry_to_update["composer"] if update_existing else ""
default_comments = entry_to_update["comments"] if update_existing else ""
default_datetime_object = (
    datetime.fromisoformat(entry_to_update["date"])
    if update_existing
    else datetime.now()
)
default_date = datetime.date(default_datetime_object)


date_obj = st.date_input(label="Date", help="The day of the visit", value=default_date)
datetime_obj = datetime(date_obj.year, date_obj.month, date_obj.day)

name = st.text_input(label="Name", help="The name of the opera", value=default_name)
production = st.text_input(
    label="Production", help="The production company", value=default_production
)
stage = st.text_input(label="Stage", value=default_stage)
composer = st.text_input(label="Composer", value=default_composer)
comments = st.text_area(
    label="Comments",
    help="Personal comments regarding the performance",
    value=default_comments,
)

final_data = ExcelRow(
    date=datetime_obj.isoformat(),
    production=production,
    composer=composer,
    name=name,
    stage=stage,
    comments=comments,
)

submit_button = st.button(label="Submit" + (" update" if update_existing else ""))

if submit_button:
    number_of_form_errors = 0
    if datetime_obj > datetime.now():
        number_of_form_errors += 1
        st.error("Selected date is in the future")
    if name == "":
        number_of_form_errors += 1
        st.error("Name field is empty")
    if production == "":
        number_of_form_errors += 1
        st.error("Production field is empty")
    if stage == "":
        number_of_form_errors += 1
        st.error("Stage field is empty")
    if composer == "":
        number_of_form_errors += 1
        st.error("Composer field is empty")

    if number_of_form_errors == 0:
        with st.spinner(text="Contacting DB..."):

            if update_existing:
                delete_performance_by_key(
                    create_key_for_visited_performance(entry_to_update)
                )

            response = send_new_performance(final_data)
        if response.ok:
            update_existing_entries()
            st.success("Added to DB")

        else:
            try:
                st.error(
                    f"{response.json()['detail']} ({response.status_code}: {response.reason})"
                )
            except Exception as e:
                st.error(f"{response}")
                st.exception(e)
