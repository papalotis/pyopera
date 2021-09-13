import json
import time
from datetime import datetime
from pathlib import Path
from tokenize import Name

import requests
import streamlit as st

from excel_to_json import ExcelRow


def send_updated_performances(new_performance) -> requests.Response:

    return requests.post(
        "https://vangelis_db.deta.dev/add_new_performance_seen", json=new_performance
    )


st.title("Add a new visited performance")


date_obj = st.date_input(label="Date", help="The day of the visit")
date = datetime(date_obj.year, date_obj.month, date_obj.day)

name = st.text_input(label="Name", help="The name of the opera")
production = st.text_input(label="Production", help="The production company")
stage = st.text_input(label="Stage")
composer = st.text_input(label="Composer")
comments = st.text_area(
    label="Comments", help="Personal comments regarding the performance"
)

final_data = ExcelRow(
    date=date.isoformat(),
    production=production,
    composer=composer,
    name=name,
    stage=stage,
    comments=comments,
)

submit_button = st.button(label="Submit")

if submit_button:
    number_of_form_errors = 0
    if date > datetime.now():
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

            response = send_updated_performances(final_data)

        if response.ok:
            st.success("Added to DB")
            st.balloons()
        else:

            st.error(
                f"{response.json()['detail']} ({response.status_code}: {response.reason})"
            )
