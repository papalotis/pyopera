import random
from collections import defaultdict
from datetime import date
from itertools import chain
from typing import Mapping, Optional, Sequence, Tuple, Union

import streamlit as st

from pyopera.common import (
    ApproxDate,
    Performance,
    is_exact_date,
    is_performance_instance,
)
from pyopera.deta_base import DatabaseInterface
from pyopera.streamlit_common import (
    format_title,
    load_db,
    write_cast_and_leading_team,
)

BASE_INTERFACE = DatabaseInterface(Performance)


def send_new_performance(new_performance: Union[Performance, dict]) -> None:
    if isinstance(new_performance, dict):
        new_performance = Performance(**new_performance)

    BASE_INTERFACE.put_db(new_performance)


def delete_performance_by_key(key: str) -> None:
    return BASE_INTERFACE.delete_item_db(key)


def clear_cast_leading_team_from_session_state():
    for key in ("cast", "leading_team"):
        try:
            del st.session_state[key]
        except KeyError:
            pass


def run() -> None:
    db = load_db(include_archived_entries=True)

    with st.sidebar:
        if st.checkbox("Only show non-full entries"):
            db_to_use = [
                performance for performance in db if (len(performance.cast) + len(performance.leading_team)) < 1
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
            entry_to_update = entry_to_update_raw.model_dump()
        else:
            entry_to_update = {}

        if entry_to_update != {}:
            update_existing = not st.checkbox("Use for new entry")
        else:
            update_existing = False

    if __file__ not in st.session_state:
        st.session_state[__file__] = {}
        st.session_state[__file__]["last_run_counter"] = int(st.session_state.run_counter)

    coming_from_different_page = st.session_state.run_counter - st.session_state[__file__]["last_run_counter"] > 1

    if "cast" not in st.session_state or coming_from_different_page:
        st.session_state["cast"] = defaultdict(set)
        st.session_state["leading_team"] = defaultdict(set)

        if update_existing:
            st.session_state["cast"].update({k: set(v) for k, v in entry_to_update["cast"].items()})
            st.session_state["leading_team"].update({k: set(v) for k, v in entry_to_update["leading_team"].items()})

    st.title(("Update an existing" if update_existing else "Add a new visited") + " performance")

    if entry_to_update.get("archived", False):
        st.warning("This is an archived entry. You can only see it here.")

    default_name = entry_to_update.get("name", "")
    default_production = entry_to_update.get("production", "")
    default_stage = entry_to_update.get("stage", "")
    default_composer = entry_to_update.get("composer", "")
    default_comments = entry_to_update.get("comments", "")
    default_concertant = entry_to_update.get("is_concertante", False)

    with st.container(border=True):
        name = st.text_input(label="Name", help="The name of the opera", value=default_name)
        col1, col2 = st.columns([1, 2])

        existing_dates: Optional[ApproxDate] = entry_to_update.get("date")
        already_approximate_date = existing_dates is not None and not is_exact_date(existing_dates)
        no_date = existing_dates is None and update_existing
        with col1:
            date_type = st.pills(
                "Date type",
                ["Exact", "Approximate", "None"],
                default=("Approximate" if already_approximate_date else "None" if no_date else "Exact"),
            )

        with col2:
            if date_type == "Approximate":
                if existing_dates is None:
                    default_date = tuple()
                else:
                    approx_date = ApproxDate(**existing_dates)
                    default_date = (
                        approx_date.earliest_date,
                        approx_date.latest_date,
                    )
            elif date_type == "Exact":
                if existing_dates is None:
                    default_date = date.today()
                else:
                    default_date = ApproxDate(**existing_dates).earliest_date
                    if not is_exact_date(existing_dates):
                        st.error("Trying to treat an approximate date as an exact date")
                        return

            else:
                default_date = None

            dates = st.date_input(
                label="Date",
                help="The day of the visit",
                value=default_date,
                min_value=date(1970, 1, 1),
                disabled=date_type == "None",
            )

            if default_date is not None:
                if isinstance(dates, date):
                    dates = (dates, dates)

                if len(dates) < 2:
                    date_range = None
                else:
                    date_range = ApproxDate(earliest_date=dates[0], latest_date=dates[1])
            else:
                date_range = None

        col1, col2, col3, col4 = st.columns([2, 1, 3, 1])

        with col1:
            production = st.text_input(label="Production", help="The production company", value=default_production)

            possible_exisitng_productions = sorted(
                set(entry.production_key for entry in db if entry.production == production and entry.name == name),
                key=lambda x: x if x is not None else -1,
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

    with st.container(border=10):
        mode = st.radio("Cast or Leading team mode", ["Cast", "Leading team"], horizontal=True)

        add_to_cast = mode == "Cast"

        col1, col2 = st.columns([1, 1])
        with col1:
            relevant_works = [entry for entry in db if entry.name == name and entry.composer == composer]
            relevant_roles = set(
                chain.from_iterable(entry.cast if add_to_cast else entry.leading_team for entry in relevant_works)
            )

            label = "Role" if add_to_cast else "Part"

            role_or_part = st.selectbox(
                label,
                list(relevant_roles),
                format_func=lambda x: x,
                accept_new_options=True,
            )

        with col2:
            label = "Name" + " " * add_to_cast

            all_persons = sorted(
                set(
                    person
                    for entry in db
                    for persons in (entry.cast if add_to_cast else entry.leading_team).values()
                    for person in persons
                )
            )

            cast_leading_team_name = st.selectbox(
                label,
                all_persons,
                format_func=lambda x: x,
                accept_new_options=True,
            )

        append_button = st.button(
            "Append to " + mode,
            disabled=role_or_part in ("", None) or cast_leading_team_name in ("", None),
        )

        if append_button:
            if cast_leading_team_name != "" or role_or_part != "":
                key = "cast" if add_to_cast else "leading_team"
                st.session_state[key][role_or_part].update({n.strip() for n in cast_leading_team_name.split(",")})

            else:
                st.error("At least one field is empty")

    def all_persons_with_role(
        dol: Mapping[str, Sequence[str]],
    ) -> Sequence[Tuple[str, str]]:
        return [(role, person) for role in dol for person in dol[role] if role != "" and person != ""]

    cast_flat = all_persons_with_role(st.session_state["cast"])
    leading_team_flat = all_persons_with_role(st.session_state["leading_team"])

    def format_func(role_name: Tuple[str, str]) -> str:
        role, name = role_name
        return f"{role} - {name}"

    with st.container(border=True, key="remove_person_container"):
        remove = st.selectbox(
            "Remove",
            [*cast_flat, *leading_team_flat],
            format_func=format_func,
        )

        st.button(
            "Remove",
            on_click=remove_person_from_performance,
            args=[remove],
            disabled=len(cast_flat) == 0 and len(leading_team_flat) == 0,
        )

    write_cast_and_leading_team(st.session_state["cast"], st.session_state["leading_team"])

    if update_existing:
        ### delete entry
        with st.expander("Delete entry"):
            st.warning(
                "This action will permanently delete the entry from the database. Make sure that you absolutely want to delete the entry before proceeding."
            )
            # ask user text confirmation
            confirmation_text = "delete"
            user_delete_text = st.text_input(f"Type '{confirmation_text}' to confirm deletion", value="")

            user_text_confirmation = user_delete_text == confirmation_text
            st.button(
                "Delete entry",
                disabled=not user_text_confirmation,
                on_click=do_deletion,
                args=[
                    entry_to_update,
                    user_text_confirmation,
                ],
            )

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.button(
            label="Submit" + (" update" if update_existing else ""),
            icon=":material/cloud_upload:",
            on_click=do_submission,
            args=[
                entry_to_update,
                update_existing,
                name,
                date_range,
                production,
                stage,
                composer,
                concertante,
                comments,
            ],
        )

    with col2:
        if update_existing:
            is_archived = entry_to_update.get("archived", False)

            st.button(
                label="Unarchive" if is_archived else "Archive",
                icon=":material/archive:" if is_archived else ":material/undo:",
                on_click=toggle_archive_entry,
                args=[entry_to_update],
            )

    st.session_state[__file__]["last_run_counter"] = int(st.session_state.run_counter)


def remove_person_from_performance(remove: tuple[str, str]):
    role, person = remove

    st.session_state["cast"][role] = st.session_state["cast"][role] - {person}
    if len(st.session_state["cast"][role]) == 0:
        del st.session_state["cast"][role]

    st.session_state["leading_team"][role] = st.session_state["leading_team"][role] - {person}

    if len(st.session_state["leading_team"][role]) == 0:
        del st.session_state["leading_team"][role]


def toggle_archive_entry(entry_to_update):
    if entry_to_update.get("archived", False):
        entry_to_update["archived"] = False
        st.toast("Unarchived entry", icon=":material/undo:")
    else:
        entry_to_update["archived"] = True
        st.toast("Archived entry", icon=":material/archive:")
    send_new_performance(entry_to_update)


def do_deletion(entry_to_update, user_text_confirmation):
    if user_text_confirmation:
        delete_performance_by_key(entry_to_update["key"])
        st.toast("Deleted entry", icon=":material/delete:")


def do_submission(
    entry_to_update,
    update_existing,
    name,
    date_range: Optional[ApproxDate],
    production,
    stage,
    composer,
    concertante,
    comments,
):
    number_of_form_errors = 0

    st.write(date_range)

    if date_range is not None:
        if date_range.latest_date > date.today():
            number_of_form_errors += 1
            st.error("Selected date is in the future")
        # if date_range == ApproxDate.PAST:
        #     number_of_form_errors += 1
        #     st.error("Date range is not full")
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

    if number_of_form_errors > 0:
        st.toast("Missing fields", icon=":material/error:")
        return

    with st.spinner(text="Contacting database..."):
        cast = {k: list(v) for k, v in st.session_state["cast"].items()}
        leading_team = {k: list(v) for k, v in st.session_state["leading_team"].items()}

        final_dict = dict(
            name=name,
            date=date_range,
            production=production,
            composer=composer,
            stage=stage,
            comments=comments,
            is_concertante=concertante,
            cast=cast,
            leading_team=leading_team,
        )

        try:
            final_data = Performance(**final_dict)

            final_data_dict = final_data.model_dump()

            if update_existing and entry_to_update["key"] != final_data_dict["key"]:
                delete_performance_by_key(entry_to_update["key"])
            try:
                send_new_performance(final_data_dict)
            except Exception:
                if entry_to_update != {}:
                    send_new_performance(entry_to_update)
                raise

            # clear the leading team and cast
            clear_cast_leading_team_from_session_state()

            st.toast("Updated database", icon=":material/cloud_sync:")

        except Exception as e:
            st.write(e)
            st.toast("An error occured when uploading the entry", icon=":material/error:")
