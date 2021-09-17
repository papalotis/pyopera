import calendar
import textwrap
from copy import deepcopy
from datetime import datetime
from typing import (
    Any,
    Counter,
    Hashable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.graph_objects import Figure

from streamlit_common import load_db


def add_split_date_to_db(
    db: Sequence[Mapping[str, Any]]
) -> Sequence[Mapping[str, Any]]:

    db = deepcopy(db)
    for entry in db:
        date = datetime.fromisoformat(entry["date"])

        entry["day"] = date.day
        entry["month"] = date.month
        entry["year"] = date.year

    return db


def truncate_composer_name(composer: str) -> str:
    parts = composer.split()
    return " ".join([part[0] + "." for part in parts[:-1]] + [parts[-1]])


# @st.cache
def create_frequency_chart(
    db: Sequence[Mapping[str, Hashable]],
    columns: Union[str, Sequence[str]],
    range_to_show: Optional[Union[int, Tuple[int, int]]] = None,
    separator: str = ", ",
    column_mapper: Optional[Mapping[str, Mapping[str, str]]] = None,
    column_order: Optional[Sequence[str]] = None,
) -> Figure:

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
            #  [
            #     textwrap.shorten(
            #         el, 20 * len(columns), placeholder=" ...", break_long_words=True
            #     )
            #     for el in
            # ],
            "Frequency": frequencies,
        }
    )

    bar_chart = px.bar(
        composers_freq_df,
        x=column_names_combined,
        y="Frequency",
        category_orders={column_names_combined: column_order},
        # height=800,
        # template="presentation",
    )

    # bar_chart.update_layout()

    return bar_chart


def show_frequency_chart(
    db: Sequence[Mapping[str, Hashable]],
    columns: Union[str, Sequence[str]],
    range_to_show: Optional[Union[int, Tuple[int, int]]] = None,
    separator: str = ", ",
    column_mapper: Optional[Mapping[str, Mapping[str, str]]] = None,
    column_order: Optional[Sequence[str]] = None,
) -> None:
    st.plotly_chart(
        create_frequency_chart(
            db, columns, range_to_show, separator, column_mapper, column_order
        ),
        use_container_width=True,
    )


def format_column_name(column_name: str) -> str:
    return column_name.replace("is_", "").replace("_", " ").title()


def run():
    month_to_month_name = {i: calendar.month_abbr[i] for i in range(1, 13)}

    db = add_split_date_to_db(load_db())

    presets = {
        ("name",): "Name of opus",
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
        number_to_show = st.number_input("Number of bars to show", 1, value=20)
    show_all = st.checkbox("Show full bar chart")

    if show_all:
        number_to_show = None

    if len(options) > 0:
        show_frequency_chart(
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
