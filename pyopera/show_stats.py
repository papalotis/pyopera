import calendar
import re
import textwrap
from collections import defaultdict
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

import pandas as pd
import plotly.express as px
import streamlit as st
from more_itertools.recipes import flatten
from unidecode import unidecode

from common import (
    DB_TYPE,
    convert_short_stage_name_to_long_if_available,
    get_all_names_from_performance,
)
from streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    load_db,
    remove_singular_prefix_from_role,
)


def add_split_date_to_db(db: DB_TYPE) -> Sequence[Mapping[str, Any]]:
    return [
        dict(
            day=entry.date.day,
            month=entry.date.month,
            year=entry.date.year,
            **entry.dict(),
        )
        for entry in db
    ]


def truncate_composer_name(composer: str) -> str:
    parts = composer.split()
    return " ".join([part[0] + "." for part in parts[:-1]] + [parts[-1]])


def create_frequency_chart(
    db: Sequence[Mapping[str, Hashable]],
    columns: Union[str, Sequence[str]],
    range_to_show: Optional[Union[int, Tuple[int, int]]] = None,
    separator: str = ", ",
    column_mapper: Optional[Mapping[str, Mapping[str, str]]] = None,
    column_order: Optional[Sequence[str]] = None,
) -> None:

    if isinstance(columns, str):
        columns = cast(Sequence[str], (columns,))
    else:
        columns = tuple(columns)

    if column_mapper is None:
        column_mapper = {}

    if not isinstance(range_to_show, tuple):
        range_to_show = (None, range_to_show)

    counter = Counter(
        [
            separator.join(
                textwrap.shorten(
                    str(column_mapper.get(column, lambda x: x)(entry[column])),
                    20,
                    placeholder="...",
                )
                for column in columns
            )
            for entry in db
        ]
    )

    columns_combined, frequencies = zip(*counter.most_common()[slice(*range_to_show)])

    column_names_combined = ", ".join(
        column_name.capitalize() for column_name in columns
    )

    composers_freq_df = pd.DataFrame(
        {
            column_names_combined: columns_combined,
            "Frequency": frequencies,
        }
    )

    bar_chart = px.bar(
        composers_freq_df,
        x=column_names_combined,
        y="Frequency",
        category_orders={column_names_combined: column_order},
    )

    bar_chart.update_layout()

    st.plotly_chart(bar_chart, use_container_width=True)


def format_column_name(column_name: str) -> str:
    return column_name.replace("is_", "").replace("_", " ").title()


def key_sort_opus_by_name_and_composer(
    name_composer_rest: Tuple[str, ...]
) -> Tuple[str, ...]:
    name, composer, *a = name_composer_rest
    return (name.replace("A ", "").replace("The ", "").replace("An ", ""), composer, *a)


def run_frequencies():

    month_to_month_name = {i: calendar.month_abbr[i] for i in range(1, 13)}

    db = add_split_date_to_db(load_db())

    presets = {
        ("name", "composer"): "Opus",
        ("composer",): "Composer",
        ("stage",): "Stage",
        ("month",): "Number of performances seen each month",
        ("day", "month"): "Day of year",
    }

    col1, col2 = st.columns(2)
    with col1:
        preset = st.selectbox("Presets", presets, format_func=presets.get)
    with col2:
        options = st.multiselect(
            "Categories to combine",
            filter(
                lambda el: isinstance(db[0][el], (str, int))
                and el not in ("comments", "key"),
                db[0].keys(),
            ),
            default=preset,
            format_func=format_column_name,
        )

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

    st.title(name)
    st.markdown(f"#### {composer}")
    all_entries_of_opus = [
        performance
        for performance in load_db()
        if performance.name == name and performance.composer == composer
    ]
    for entry in all_entries_of_opus:
        st.markdown(
            f"- {format_iso_date_to_day_month_year_with_dots(entry.date)} - {convert_short_stage_name_to_long_if_available(entry.stage)}"
        )


def run_single_person():

    with st.sidebar:
        all_persons = sorted(
            set(
                flatten(
                    get_all_names_from_performance(performance)
                    for performance in load_db()
                )
            )
        )

        person = st.selectbox("Person", all_persons)

    st.title(person)
    all_entries_with_person = [
        performance
        for performance in load_db()
        if person in get_all_names_from_performance(performance)
    ]
    for entry in all_entries_with_person:

        all_roles = ChainMap(entry.leading_team, entry.cast)
        roles = [role for role, persons in all_roles.items() if person in persons]

        to_join = [
            format_iso_date_to_day_month_year_with_dots(entry.date),
            convert_short_stage_name_to_long_if_available(entry.stage),
            entry.name,
        ]
        if person == entry.composer and len(roles) == 0:
            pass
        else:
            to_join.extend([entry.composer, ", ".join(roles)])
        st.markdown("- " + " - ".join(to_join))


def normalize_role(role: str) -> str:
    role_normalized = remove_singular_prefix_from_role(unidecode(role))
    return role_normalized


def run_single_role():

    with st.sidebar:
        all_opus = sorted(
            {(performance.name, performance.composer) for performance in load_db()},
            key=key_sort_opus_by_name_and_composer,
        )

        # st.write(all_opus)

        name, composer = st.selectbox(
            "Opus",
            all_opus,
            format_func=lambda name_composer: f"{name_composer[0]} - {truncate_composer_name(name_composer[1])}",
        )

        roles = sorted(
            {
                role
                for entry in load_db()
                for role in entry.cast
                if entry.name == name and entry.composer == composer
            }
        )

        roles_matched: DefaultDict[str, MutableSequence[str]] = defaultdict(list)
        for role in roles:
            role_normalized = normalize_role(role)
            roles_matched[role_normalized].append(role)

    if len(roles_matched) > 0:
        with st.sidebar:
            # prefer role names that contain non-ascii characters that are short
            format_func = lambda role_normalized: remove_singular_prefix_from_role(
                min(
                    roles_matched[role_normalized],
                    key=lambda role: (role.isascii(), len(role)),
                )
            )
            role = st.selectbox(
                "Role",
                roles_matched,
                format_func=format_func,
            )
    else:
        role = None

    st.markdown(f"#### {name} - {composer}")

    if role is not None:
        st.subheader(format_func(role))
        all_entries_of_opus = [
            performance
            for performance in load_db()
            if performance.name == name
            and performance.composer == composer
            and set(roles_matched[role]).intersection(performance.cast) != set()
        ]

        for entry in all_entries_of_opus:
            date = format_iso_date_to_day_month_year_with_dots(entry.date)
            stage = convert_short_stage_name_to_long_if_available(entry.stage)
            for unique_role_instance in roles_matched[role]:
                persons_list = entry.cast.get(unique_role_instance)
                if persons_list is not None:
                    persons = ", ".join(persons_list)
                    break
            st.markdown(f"- {date} - {stage} - {persons}")
    else:
        st.warning("No roles available for this entry")


def run():
    modes = {
        "Frequencies": run_frequencies,
        "Opus Info": run_single_opus,
        "Person Info": run_single_person,
        "Role Info": run_single_role,
    }

    with st.sidebar:
        function = modes.get(st.radio("Stats to show", modes))

    function()
