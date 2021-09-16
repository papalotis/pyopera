import time
from collections import defaultdict
from datetime import datetime
from hashlib import sha1
from itertools import chain
from typing import Optional

import streamlit as st


from common import create_key_for_visited_performance_v2
from streamlit_common import DB, format_title, load_db, write_cast_and_leading_team

def run():
    def send_new_performance(new_performance: dict):

        assert "key" in new_performance

        return DB.put(new_performance)

    def delete_performance_by_key(key: str) -> None:
        return DB.delete(key)

    def clear_cast_leading_team_from_session_state():
        try:
            del st.session_state["cast"]
        except KeyError:
            pass

        try:
            del st.session_state["leading_team"]
        except KeyError:
            pass

    password = st.text_input("Enter password", type="password")
    if (
        sha1(password.encode()).hexdigest()
        != "ac2e1249ad3cbbe5908d15e5b1da6f0a603aaaf4"
    ):
        if password != "":
            st.error("Wrong password")
        st.stop()

    st.session_state["db"] = load_db()

    with st.sidebar:
        entry_to_update: Optional[dict] = st.selectbox(
            "Select entry",
            [None] + st.session_state["db"],
            format_func=format_title,
            on_change=clear_cast_leading_team_from_session_state,
        )
    update_existing = entry_to_update is not None

    if "cast" not in st.session_state:
        st.session_state["cast"] = defaultdict(set)
        st.session_state["leading_team"] = defaultdict(set)

        if update_existing:
            st.session_state["cast"].update(entry_to_update["cast"])
            st.session_state["leading_team"].update(entry_to_update["leading_team"])

    st.title(
        ("Update an existing" if update_existing else "Add a new visited")
        + " performance"
    )

    default_name = entry_to_update["name"] if update_existing else ""
    default_production = entry_to_update["production"] if update_existing else ""
    default_stage = entry_to_update["stage"] if update_existing else ""
    default_composer = entry_to_update["composer"] if update_existing else ""
    default_comments = entry_to_update["comments"] if update_existing else ""
    default_concertant = entry_to_update["is_concertante"] if update_existing else False

    col1, col2 = st.columns([1, 1])

    with col1:
        name = st.text_input(
            label="Name", help="The name of the opera", value=default_name
        )

    with col2:

        default_datetime_object = (
            datetime.fromisoformat(entry_to_update["date"])
            if update_existing
            else datetime.now()
        )
        default_date = datetime.date(default_datetime_object)

        date_obj = st.date_input(
            label="Date", help="The day of the visit", value=default_date
        )
        datetime_obj = datetime(date_obj.year, date_obj.month, date_obj.day)

    col1, col2, col3, col4 = st.columns([1, 1, 3, 1])

    with col1:
        production = st.text_input(
            label="Production", help="The production company", value=default_production
        )
    with col2:
        stage = st.text_input(label="Stage", value=default_stage)

    with col3:
        composer = st.text_input(label="Composer", value=default_composer)

    with col4:
        concertante = st.checkbox(label="Concertante", value=default_concertant)

    comments = st.text_area(
        label="Comments",
        help="Personal comments regarding the performance",
        value=default_comments,
    )

    mode = st.radio("Cast or Leading team mode", ["Cast", "Leading team"])

    add_to_cast = mode == "Cast"

    with st.form("cast_or_leading_team_member"):
        col1, col2 = st.columns([1, 1])

        with col1:
            label = "Role" if add_to_cast else "Part"
            role_or_part = st.text_input(label)
        with col2:
            label = "Name" + " " * add_to_cast
            cast_leading_team_name = st.text_input(label)

        append_button = st.form_submit_button("Append")

    if append_button:
        if cast_leading_team_name != "" or role_or_part != "":
            key = "cast" if add_to_cast else "leading_team"
            st.session_state[key][role_or_part].add(cast_leading_team_name)
        else:
            st.error("At least one field is empty")

    def all_persons_with_role(dol: dict) -> list:
        return [
            (role, person)
            for role in dol
            for person in dol[role]
            if role != "" and person != ""
        ]

    cast_flat = all_persons_with_role(st.session_state["cast"])
    leading_team_flat = all_persons_with_role(st.session_state["leading_team"])

    remove = st.selectbox(
        "Remove",
        chain(cast_flat, leading_team_flat),
        format_func=lambda role_name,: " - ".join(role_name),
    )

    do_remove = st.button("Remove")

    if do_remove and (len(cast_flat) > 0 or len(leading_team_flat) > 0):
        role, person = remove
        st.session_state["cast"][role] = st.session_state["cast"][role] - {person}

        st.session_state["leading_team"][role] = st.session_state["leading_team"][
            role
        ] - {person}
        # index = st.session_state["leading_team"][role].index(person)
        #     del st.session_state["leading_team"][role][index]

        st.experimental_rerun()

    write_cast_and_leading_team(
        st.session_state["cast"], st.session_state["leading_team"]
    )

    st.markdown("#\n\n---")

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
                time.sleep(1.5)
                cast = {k: list(v) for k, v in st.session_state["cast"].items()}
                leading_team = {
                    k: list(v) for k, v in st.session_state["leading_team"].items()
                }

                try:
                    final_data = dict(
                        date=datetime_obj.isoformat(),
                        production=production,
                        composer=composer,
                        name=name,
                        stage=stage,
                        comments=comments,
                        is_concertante=concertante,
                        cast=cast,
                        leading_team=leading_team,
                    )
                    final_data["key"] = create_key_for_visited_performance_v2(
                        final_data
                    )

                    if (
                        entry_to_update is not None
                        and entry_to_update["key"] != final_data["key"]
                    ):
                        delete_performance_by_key(entry_to_update["key"])
                    try:
                        send_new_performance(final_data)
                    except Exception:
                        send_new_performance(entry_to_update)
                        raise

                    st.success("Added to DB")
                    st.balloons()
                    
                    st.caching.clear_cache()
                    st.experimental_rerun()

                except Exception as e:
                    st.write(e)
                    st.error("Could not add new entry to database")


