import time
from collections import defaultdict
from datetime import date, datetime
from hashlib import sha1
from itertools import chain
from typing import Mapping, NoReturn, Optional, Sequence, Tuple, Union

import streamlit as st
from approx_dates.models import ApproxDate

from common import (
    Performance,
    filter_only_full_entries,
    is_exact_date,
    is_performance_instance,
    load_deta_project_key,
)
from deta_base import DetaBaseInterface
from streamlit_common import (
    clear_streamlit_cache,
    format_title,
    load_db,
    write_cast_and_leading_team,
)


def authenticate() -> Optional[NoReturn]:
    if "authenticated" not in st.session_state:
        password_widget = st.empty()
        password = password_widget.text_input("Enter password", type="password")
        if (
            sha1(password.encode()).hexdigest()
            != "ac2e1249ad3cbbe5908d15e5b1da6f0a603aaaf4"
        ):
            if password != "":
                st.error("Wrong password")
            clear_cast_leading_team_from_session_state()
            st.stop()
        else:
            password_widget.empty()
            st.session_state["authenticated"] = True


BASE_INTERFACE = DetaBaseInterface(load_deta_project_key())


def send_new_performance(new_performance: Union[Performance, dict]) -> None:
    print("converting back to performance", new_performance)

    if isinstance(new_performance, dict):
        new_performance = Performance(**new_performance)

    print("converted to performance", new_performance)

    BASE_INTERFACE.put_db(new_performance)


def delete_performance_by_key(key: str) -> None:
    return BASE_INTERFACE.delete_item_db(key)


def clear_cast_leading_team_from_session_state():
    for key in ("cast", "leading_team"):
        try:
            del st.session_state[key]
        except KeyError:
            pass


def run():

    authenticate()
    db = load_db()

    with st.sidebar:

        if st.checkbox("Only show non-full entries"):

            db_to_use = [
                performance
                for performance in db
                if (len(performance.cast) + len(performance.leading_team)) < 1
            ]

        else:
            db_to_use = [None] + db

        if len(db_to_use) < 1:
            st.error("No entries were found")
            st.stop()

        entry_to_update_raw: Optional[Performance] = st.selectbox(
            "Select entry",
            db_to_use,
            format_func=format_title,
            on_change=clear_cast_leading_team_from_session_state,
        )

        # if isinstance(entry_to_update_raw, Performance):
        if is_performance_instance(entry_to_update_raw):
            entry_to_update = entry_to_update_raw.dict()
        else:
            entry_to_update = {}

        if entry_to_update != {}:
            update_existing = not st.checkbox("Use for new entry")
        else:
            update_existing = False

    if "cast" not in st.session_state:
        st.session_state["cast"] = defaultdict(set)
        st.session_state["leading_team"] = defaultdict(set)

        if update_existing:
            st.session_state["cast"].update(
                {k: set(v) for k, v in entry_to_update["cast"].items()}
            )
            st.session_state["leading_team"].update(
                {k: set(v) for k, v in entry_to_update["leading_team"].items()}
            )

    st.title(
        ("Update an existing" if update_existing else "Add a new visited")
        + " performance"
    )

    default_name = entry_to_update.get("name", "")
    default_production = entry_to_update.get("production", "")
    default_stage = entry_to_update.get("stage", "")
    default_composer = entry_to_update.get("composer", "")
    default_comments = entry_to_update.get("comments", "")
    default_concertant = entry_to_update.get("is_concertante", False)

    name = st.text_input(label="Name", help="The name of the opera", value=default_name)
    col1, col2 = st.columns([1, 3])

    existing_dates: Optional[ApproxDate] = entry_to_update.get("date")
    already_approximate_date = existing_dates is not None and not is_exact_date(
        existing_dates
    )
    with col1:
        approximate_date = st.checkbox(
            "Approximate date", value=already_approximate_date
        )

    with col2:

        if approximate_date:
            if existing_dates is None:
                default_date = tuple()
            else:
                default_date = (
                    existing_dates.earliest_date,
                    existing_dates.latest_date,
                )
        else:
            if existing_dates is None:
                default_date = date.today()
            else:
                default_date = existing_dates.earliest_date
                assert is_exact_date(existing_dates)

        dates = st.date_input(
            label="Date", help="The day of the visit", value=default_date
        )

        if isinstance(dates, date):
            dates = (dates, dates)

        if len(dates) < 2:
            date_range = ApproxDate.PAST
        else:
            date_range = ApproxDate(*dates)

    col1, col2, col3, col4 = st.columns([2, 1, 3, 1])

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
        label="Notes",
        help="Notes regarding the performance",
        value=default_comments,
    )

    mode = st.radio("Cast or Leading team mode", ["Cast", "Leading team"])

    add_to_cast = mode == "Cast"

    col1, col2 = st.columns([1, 1])
    with col1:
        label = "Role" if add_to_cast else "Part"
        use_existing_checkbox = st.checkbox(f"Use existing {label.lower()}")
        if use_existing_checkbox:
            relevant_works = [
                entry
                for entry in db
                if entry.name == name and entry.composer == composer
            ]
            relevant_roles = set(
                chain.from_iterable(
                    entry.cast if add_to_cast else entry.leading_team
                    for entry in relevant_works
                )
            )
            role_or_part = st.selectbox(label, relevant_roles)
        else:
            role_or_part = st.text_input(label)
    with col2:
        label = "Name" + " " * add_to_cast
        use_existing_checkbox = st.checkbox("Use existing person")
        if use_existing_checkbox:
            # list_of_persons =
            all_persons = sorted(
                set(
                    person
                    for entry in db
                    for persons in (
                        entry.cast if add_to_cast else entry.leading_team
                    ).values()
                    for person in persons
                )
            )
            cast_leading_team_name = st.selectbox(label, all_persons)
        else:
            cast_leading_team_name = st.text_input(label)

    append_button = st.button("Append to " + mode)

    if append_button:
        if cast_leading_team_name != "" or role_or_part != "":
            key = "cast" if add_to_cast else "leading_team"
            st.session_state[key][role_or_part].update(
                {n.strip() for n in cast_leading_team_name.split(",")}
            )

        else:
            st.error("At least one field is empty")

    def all_persons_with_role(
        dol: Mapping[str, Sequence[str]]
    ) -> Sequence[Tuple[str, str]]:
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
        if len(st.session_state["cast"][role]) == 0:
            del st.session_state["cast"][role]

        st.session_state["leading_team"][role] = st.session_state["leading_team"][
            role
        ] - {person}

        if len(st.session_state["leading_team"][role]) == 0:
            del st.session_state["leading_team"][role]

        # st.experimental_rerun()
        st.experimental_rerun()

    write_cast_and_leading_team(
        st.session_state["cast"], st.session_state["leading_team"]
    )

    st.markdown("---")

    submit_button = st.button(label="Submit" + (" update" if update_existing else ""))

    if submit_button:
        number_of_form_errors = 0
        if date_range.latest_date > date.today():
            number_of_form_errors += 1
            st.error("Selected date is in the future")
        if date_range == ApproxDate.PAST:
            number_of_form_errors += 1
            st.error("Date range is not full")
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
            with st.spinner(text="Contacting database..."):
                time.sleep(0.3)
                cast = {k: list(v) for k, v in st.session_state["cast"].items()}
                leading_team = {
                    k: list(v) for k, v in st.session_state["leading_team"].items()
                }

                print("test to string", str(date_range))

                final_dict = dict(
                    name=name,
                    date=str(date_range),
                    production=production,
                    composer=composer,
                    stage=stage,
                    comments=comments,
                    is_concertante=concertante,
                    cast=cast,
                    leading_team=leading_team,
                )

                try:
                    print("creating final instance")
                    final_data = Performance(**final_dict)

                    print("final data", final_data)

                    if final_data in db:
                        st.error("Uploading same entry")

                    else:
                        print("creating dict")
                        final_data_dict = final_data.dict()

                        if (
                            update_existing
                            and entry_to_update["key"] != final_data_dict["key"]
                        ):
                            delete_performance_by_key(entry_to_update["key"])
                        try:
                            print("ready to send", final_data_dict)
                            send_new_performance(final_data_dict)
                        except Exception:
                            if entry_to_update != {}:
                                send_new_performance(entry_to_update)
                            raise

                        st.success("Database updated successfully")
                        clear_streamlit_cache()

                except Exception as e:
                    st.write(e)
                    st.error("Could not add new entry to database")
