import calendar
import math
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import (
    Any,
    ChainMap,
    Counter,
    DefaultDict,
    Hashable,
    Mapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from more_itertools.recipes import flatten

from pyopera.common import (
    DB_TYPE,
    Performance,
    get_all_names_from_performance,
    is_exact_date,
)
from pyopera.expanded_stats import run_expanded_stats
from pyopera.show_stats_utils import (
    add_split_earliest_date_to_db,
    create_frequency_chart,
    format_column_name,
    key_sort_opus_by_name_and_composer,
    normalize_role,
    truncate_composer_name,
)
from pyopera.streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    load_db,
    load_db_venues,
    remove_singular_prefix_from_role,
)


def run_frequencies():
    month_to_month_name = {i: calendar.month_abbr[i] for i in range(1, 13)}

    db = load_db()

    presets = {
        ("name", "composer"): "Opera",
        ("composer",): "Composer",
        ("stage",): "Stage",
    }

    col1, col2 = st.columns(2)
    with col1:
        preset = st.selectbox("Presets", presets, format_func=presets.get)
    with col2:
        options = st.multiselect(
            "Categories to combine",
            filter(
                lambda el: isinstance(getattr(db[0], el), (str, int)) and el not in ("comments", "key"),
                db[0].model_dump().keys(),
            ),
            default=preset,
            format_func=format_column_name,
        )

    if any(option in ("day", "month", "year") for option in options):
        db = add_split_earliest_date_to_db(db)
    else:
        db = [entry.model_dump() for entry in db]

    col1, col2 = st.columns([1, 3])
    with col1:
        number_to_show = st.number_input("Number of bars to show", 1, value=20, step=5)
    show_all = st.checkbox("Show full bar chart")

    if show_all:
        number_to_show = None

    if len(options) > 0:
        create_frequency_chart(
            db,
            options,
            number_to_show,
            column_mapper={
                "month": month_to_month_name.get,
                "composer": truncate_composer_name,
                "date": lambda el: ".".join(el.split("T")[0].split("-")[::-1]),
            },
        )
    else:
        st.warning("Add category names to above widget")


def run_single_opus():
    venues_db = load_db_venues()

    with st.sidebar:
        all_opus = sorted(
            {(performance.name, performance.composer) for performance in load_db()},
            key=key_sort_opus_by_name_and_composer,
        )

        name, composer = st.selectbox(
            "Opera",
            all_opus,
            format_func=lambda name_composer: f"{name_composer[0]} - {truncate_composer_name(name_composer[1])}",
        )

    st.title(name)
    st.markdown(f"#### {composer}")
    all_entries_of_opus = [
        performance for performance in load_db() if performance.name == name and performance.composer == composer
    ]

    for entry in all_entries_of_opus:
        date_string = "" if entry.date is None else f"- {format_iso_date_to_day_month_year_with_dots(entry.date)} "
        st.markdown(f"{date_string} - {venues_db.get(entry.stage, entry.stage)}")


def run_single_person():
    venues_db = load_db_venues()

    with st.sidebar:
        all_persons = sorted(set(flatten(get_all_names_from_performance(performance) for performance in load_db())))

        person = st.selectbox("Person", all_persons)

    st.title(person)
    all_entries_with_person = [
        performance for performance in load_db() if person in get_all_names_from_performance(performance)
    ]
    for entry in all_entries_with_person:
        all_roles = ChainMap(entry.leading_team, entry.cast)
        roles = [role for role, persons in all_roles.items() if person in persons]

        to_join = [] if entry.date is None else [format_iso_date_to_day_month_year_with_dots(entry.date)]

        to_join.extend(
            [
                venues_db.get(entry.stage, entry.stage),
                entry.name,
            ]
        )
        if person == entry.composer and len(roles) == 0:
            pass
        else:
            to_join.extend([entry.composer, ", ".join(roles)])
        st.markdown("- " + " - ".join(to_join))


def run_single_role():
    venues_db = load_db_venues()

    with st.sidebar:
        all_opus = sorted(
            {(performance.name, performance.composer) for performance in load_db()},
            key=key_sort_opus_by_name_and_composer,
        )

        name, composer = st.selectbox(
            "Opus",
            all_opus,
            format_func=lambda name_composer: f"{name_composer[0]} - {truncate_composer_name(name_composer[1])}",
        )

        roles = sorted(
            {role for entry in load_db() for role in entry.cast if entry.name == name and entry.composer == composer}
        )

        roles_matched: DefaultDict[str, MutableSequence[str]] = defaultdict(list)
        for role in roles:
            role_normalized = normalize_role(role)
            roles_matched[role_normalized].append(role)

        # prefer role names that contain non-ascii characters that are short
        def format_func(role_normalized):
            return remove_singular_prefix_from_role(
                min(roles_matched[role_normalized], key=lambda role: (role.isascii(), len(role)))
            )

        role = st.selectbox(
            "Role",
            roles_matched,
            format_func=format_func,
        )

    st.markdown(f"#### {name} - {composer}")

    if role is not None:
        st.subheader(format_func(role))
        all_entries_of_opus = [
            performance
            for performance in load_db()
            if performance.name == name and performance.composer == composer
            # and set(roles_matched[role]).intersection(performance.cast) != set()
        ]

        for entry in all_entries_of_opus:
            date = format_iso_date_to_day_month_year_with_dots(entry.date)
            stage = venues_db.get(entry.stage, entry.stage)
            for unique_role_instance in roles_matched[role]:
                persons_list = entry.cast.get(unique_role_instance)
                if persons_list is not None:
                    persons = ", ".join(map(lambda person: f"**{person}**", persons_list))
                    break
            else:
                persons = "No information available"

            date_string = "" if entry.date is None else f"- {date} "
            st.markdown(f"{date_string}- {stage} - {persons}")
    else:
        st.warning("No roles available for this entry")


def run():
    modes = {
        ":material/monitoring: Numbers": run_frequencies,
        ":material/music_note: Opera": run_single_opus,
        ":material/person_search: Artist": run_single_person,
        ":material/person_pin: Role": run_single_role,
    }

    with st.sidebar:
        function = modes.get(st.radio("Items", modes))

    function()
