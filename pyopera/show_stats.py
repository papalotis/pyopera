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
                str(column_mapper.get(column, {}).get(*([entry[column]] * 2)))
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
            column_names_combined: [
                textwrap.shorten(el, 30, placeholder=" ...") for el in columns_combined
            ],
            "Frequency": frequencies,
        }
    )

    composers_bar = px.bar(
        composers_freq_df,
        x=column_names_combined,
        y="Frequency",
        category_orders={column_names_combined: column_order},
        title=f"Frequency of {column_names_combined}",
    )

    st.plotly_chart(composers_bar, use_container_width=True)


def run():
    month_to_month_name = {i: calendar.month_abbr[i] for i in range(1, 13)}

    db = add_split_date_to_db(load_db())

    with st.expander("Opus"):
        number_to_show = st.slider("Number to show", 1, 30, 10, key="slider Opus")
        create_frequency_chart(db, "name", number_to_show)

    with st.expander("Composer"):
        number_to_show = st.slider("Number to show", 1, 30, 10, key="slider composer")
        create_frequency_chart(db, "composer", number_to_show)
    with st.expander("Stage"):
        number_to_show = st.slider("Number to show", 1, 30, 10, key="slider stage")
        create_frequency_chart(db, "stage", number_to_show)

    with st.expander("Opus, stage combination"):
        create_frequency_chart(db, ["name", "stage"], 20)

    with st.expander("Performances seen by Month"):
        create_frequency_chart(
            db,
            "month",
            column_mapper={"month": month_to_month_name},
            column_order=list(month_to_month_name.values()),
        )
    with st.expander("Performances seen by day of year"):

        create_frequency_chart(
            db,
            ["day", "month"],
            20,
            ". ",
            column_mapper={"month": month_to_month_name},
        )

        create_frequency_chart(
            db,
            ["day", "month"],
            366,
            ". ",
            column_mapper={"month": month_to_month_name},
            column_order=[
                f"{day}. {month_to_month_name[month]}"
                for month in month_to_month_name
                for day in range(1, calendar.monthrange(2012, month)[1] + 1)
            ],
        )
