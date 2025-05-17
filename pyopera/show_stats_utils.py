import textwrap
from typing import (
    Any,
    Hashable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

import streamlit as st

from pyopera.common import DB_TYPE, is_exact_date


def truncate_composer_name(composer: str) -> str:
    parts = composer.split()
    return " ".join([part[0] + "." for part in parts[:-1]] + [parts[-1]])


def key_sort_opus_by_name_and_composer(
    name_composer_rest: Tuple[str, ...],
) -> Tuple[str, ...]:
    name, composer, *a = name_composer_rest
    name_no_prefix = (
        name.replace("A ", "")
        .replace("The ", "")
        .replace("An ", "")
        .replace("Der ", "")
        .replace("Die ", "")
        .replace("Das ", "")
        .replace("La ", "")
        .replace("Le ", "")
        .replace("L'", "")
        .replace("L'", "")
        .strip()
    )
    return (name_no_prefix, composer, *a)


def add_split_earliest_date_to_db(db: DB_TYPE) -> Sequence[Mapping[str, Any]]:
    return [
        dict(
            day=entry.date.earliest_date.day,
            month=entry.date.earliest_date.month,
            year=entry.date.earliest_date.year,
            **entry.model_dump(),
        )
        for entry in db
        if entry.date is not None
    ]


def format_column_name(column_name: str) -> str:
    return column_name.replace("is_", "").replace("_", " ").title()


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

    date_columns = {"day", "month", "year"}
    present_date_columns = date_columns.intersection(columns)
    if len(present_date_columns) > 0:
        st.warning("Only entries with exact date are considered")
        db = [entry for entry in db if is_exact_date(entry["date"])]

    if column_mapper is None:
        column_mapper = {}

    if not isinstance(range_to_show, tuple):
        range_to_show = (None, range_to_show)

    from collections import Counter

    import pandas as pd
    import plotly.express as px

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

    column_names_combined = ", ".join(column_name.capitalize() for column_name in columns)

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


def normalize_role(role: str) -> str:
    from unidecode import unidecode

    from pyopera.streamlit_common import remove_singular_prefix_from_role

    role_normalized = remove_singular_prefix_from_role(unidecode(role))
    return role_normalized


def convert_alpha2_to_alpha3(country: str) -> str:
    return {
        "AT": "AUT",
        "BE": "BEL",
        "BG": "BGR",
        "CH": "CHE",
        "CY": "CYP",
        "CZ": "CZE",
        "DE": "DEU",
        "DK": "DNK",
        "EE": "EST",
        "ES": "ESP",
        "FI": "FIN",
        "FR": "FRA",
        "GB": "GBR",
        "GR": "GRC",
        "HR": "HRV",
        "HU": "HUN",
        "IE": "IRL",
        "IS": "ISL",
        "IT": "ITA",
        "LI": "LIE",
        "LT": "LTU",
        "LU": "LUX",
        "LV": "LVA",
        "MC": "MCO",
        "MD": "MDA",
        "MT": "MLT",
        "NL": "NLD",
        "NO": "NOR",
        "PL": "POL",
        "PT": "PRT",
        "RO": "ROU",
        "RS": "SRB",
        "SE": "SWE",
        "SI": "SVN",
        "SK": "SVK",
        "UA": "UKR",
    }.get(country, country)
