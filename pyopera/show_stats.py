import calendar
import math
import textwrap
from collections import defaultdict
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
import reverse_geocoder as rg
import streamlit as st
from more_itertools.recipes import flatten
from unidecode import unidecode

from pyopera.common import (
    DB_TYPE,
    get_all_names_from_performance,
    is_exact_date,
)
from pyopera.streamlit_common import (
    format_iso_date_to_day_month_year_with_dots,
    load_db,
    load_db_venues,
    remove_singular_prefix_from_role,
)


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

    date_columns = {"day", "month", "year"}
    present_date_columns = date_columns.intersection(columns)
    if len(present_date_columns) > 0:
        st.warning("Only entries with exact date are considered")
        db = [entry for entry in db if is_exact_date(entry["date"])]

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


def format_column_name(column_name: str) -> str:
    return column_name.replace("is_", "").replace("_", " ").title()


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
        .replace("L’", "")
        .strip()
    )
    return (name_no_prefix, composer, *a)


def run_frequencies():
    month_to_month_name = {i: calendar.month_abbr[i] for i in range(1, 13)}

    db = load_db()

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
            "Opus",
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


def normalize_role(role: str) -> str:
    role_normalized = remove_singular_prefix_from_role(unidecode(role))
    return role_normalized


def run_single_role():
    venues_db = load_db_venues()

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


@st.cache_data
def longitude_latitude_to_location(longitude: Decimal | None, latitude: Decimal | None) -> Optional[str]:
    if longitude is None or latitude is None:
        return None

    coordinates = (float(latitude), float(longitude))
    location = rg.search(coordinates, mode=1)
    if len(location) == 0:
        return None

    if len(location) > 1:
        raise ValueError("Multiple locations found for the given coordinates.")

    location_result = location[0]

    # for germany if admin1 is berlin use that instead of name (names gives the bezirk, which is too specific)
    # for germany if city name is bogenhausen use munich
    # for germany if city name is "Hofen an der Enz" use Bad Wildbad
    # for greece if admin1 is attica, name gives the dimos, convert attica to Athens
    # for czechia if admin1 is prague, name gives the district, convert to prague
    # for france if if name is "Levallois-Perret" convert to "Paris"

    key_for_city_name = {
        "AT": "name",
        "DE": "name",
        "GR": "admin1",
        "GB": "name",
        "IT": "name",
        "CH": "name",
        "SK": "name",
        "FR": "name",
        "CZ": "name",
        "BE": "name",
        "HU": "admin1",
    }.get(location_result["cc"], "name")

    if location_result["cc"] == "FR" and 0:
        st.write(location_result)

    city_name: str | None = None
    if location_result[key_for_city_name] is not None:
        city_name = location_result[key_for_city_name]
        if location_result["cc"] == "DE" and location_result["admin1"] == "Berlin":
            city_name = "Berlin"
        elif location_result["cc"] == "GR" and location_result["admin1"] == "Attica":
            city_name = "Athens"
        elif location_result["cc"] == "CZ" and (
            location_result["admin1"] == "Prague" or location_result["name"] == "Stare Mesto"
        ):
            city_name = "Prague"
        elif location_result["cc"] == "FR" and location_result["name"] == "Levallois-Perret":
            city_name = "Paris"
        elif location_result["cc"] == "DE" and city_name == "Bogenhausen":
            city_name = "Munich"
        elif location_result["cc"] == "DE" and city_name == "Hofen an der Enz":
            city_name = "Bad Wildbad"

    return city_name


def calculate_city_coordinates() -> None:
    performances = load_db()
    stages = load_db_venues(list_of_entries=True)
    if st.session_state.get("city_name_to_coords") is None:
        city_name_to_coords_list: defaultdict[str, list[tuple[Decimal, Decimal]]] = defaultdict(list)
        for performance in performances:
            for stage in stages:
                if stage.short_name == performance.stage and stage.longitude is not None and stage.latitude is not None:
                    city_name = longitude_latitude_to_location(stage.longitude, stage.latitude)
                    if city_name is not None:
                        city_name_to_coords_list[city_name].append((stage.longitude, stage.latitude))

        city_name_to_coords = {key: np.mean(value, axis=0) for key, value in city_name_to_coords_list.items()}
        st.session_state["city_name_to_coords"] = city_name_to_coords


def run_maps() -> None:
    performances = load_db()
    calculate_city_coordinates()

    st.markdown("### Visits Map")

    mode = st.selectbox(
        "Map Mode",
        ("Venues", "Cities"),
        index=1,
    )

    stages = load_db_venues(list_of_entries=True)

    coords_counter: dict[tuple[Decimal, Decimal], int] = defaultdict(int)

    for performance in performances:
        stage = next((stage for stage in stages if stage.short_name == performance.stage), None)

        if stage is None:
            continue

        if stage.longitude is not None and stage.latitude is not None:
            if mode == "Venues":
                key = (stage.longitude, stage.latitude, stage.name)
            elif mode == "Cities":
                city_name = longitude_latitude_to_location(stage.longitude, stage.latitude)
                key = (*st.session_state["city_name_to_coords"][city_name], city_name)

            coords_counter[key] += 1

    map_count_to_size = {
        1: 2,
        5: 5,
        10: 7,
        20: 10,
        50: 15,
        100: 20,
        500: 30,
    }

    # Create DataFrame for map visualization
    map_data = pd.DataFrame(
        [
            {
                "lon": float(lon),
                "lat": float(lat),
                "count": count,
                "size": next(
                    (size for min_count, size in map_count_to_size.items() if count <= min_count),
                    40,
                ),
                "name": stage_name_or_city,
            }
            for (lon, lat, stage_name_or_city), count in coords_counter.items()
        ]
    )

    if not map_data.empty:
        threshold = map_data["count"].nlargest(20).min()
        map_data["label"] = map_data["name"].where(map_data["count"] >= threshold, "")

        circle_scale = st.slider("Circle Scale", min_value=0.2, max_value=2.0, value=1.0)

        fig = px.scatter_map(
            map_data,
            lat="lat",
            lon="lon",
            size="size",
            size_max=30 * circle_scale,
            color="count",
            color_continuous_scale=["red", "black"],
            text="label",
            hover_name="name",
            hover_data=["count"],
            zoom=3,
            map_style="carto-positron",
        )

        fig.update_traces(mode="markers+text", textposition="middle center", marker_opacity=0.7, textfont_size=10)
        fig.update_layout(uniformtext_minsize=12, uniformtext_mode="hide")

        fig.update_layout(
            coloraxis_colorbar=dict(title="Visits", ticks="outside"),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No location data available for map visualization.")


@st.cache_data
def build_graph() -> nx.Graph:
    performances = load_db()
    # Build network of artists who have worked together
    g = nx.Graph()

    progress = st.progress(0.0)
    for i, performance in enumerate(performances):
        progress.progress(i / len(performances))
        all_artists = set()

        # Add cast members
        for role, people in performance.cast.items():
            for person in people:
                g.add_node(person, type="cast")
                all_artists.add(person)

        # Add leading team
        for role, people in performance.leading_team.items():
            for person in people:
                g.add_node(person, type="leading")
                all_artists.add(person)

        # Connect all artists in this performance
        for person1 in all_artists:
            for person2 in all_artists:
                if person1 != person2:
                    if g.has_edge(person1, person2):
                        g[person1][person2]["weight"] += 1
                    else:
                        g.add_edge(person1, person2, weight=1)

    return g


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


def run_expanded_stats():
    performances = load_db()
    venues_db = load_db_venues()

    st.title("Opera Statistics Dashboard")

    # Top-level metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        # group performances by date
        performances_by_date = defaultdict(list)
        for performance in performances:
            key = performance.date.earliest_date if performance.date is not None else None
            performances_by_date[key].append(performance)

        performances_no_date = performances_by_date.pop(None, [])

        number_of_performances = len(performances_by_date) + len(performances_no_date)
        st.metric("Total Performances", number_of_performances)

        unique_composers = len(set(p.composer for p in performances))
        st.metric("Unique Composers", unique_composers)

    with col2:
        unique_operas = len({(p.name, p.composer) for p in performances})
        st.metric("Unique Operas", unique_operas)

        unique_venues = len(set(p.stage for p in performances))
        st.metric("Unique Venues", unique_venues)

    with col3:
        concertante_count = sum(1 for p in performances if p.is_concertante)
        st.metric("Concertante Performances", f"{concertante_count} ({concertante_count/number_of_performances:.1%})")

        dated_performances = [p for p in performances if p.date is not None]
        if dated_performances:
            years_span = (
                max(p.date.latest_date.year for p in dated_performances)
                - min(p.date.earliest_date.year for p in dated_performances)
                + 1
            )
            st.metric("Years of Opera-going", years_span)

    # Performance frequency by year
    st.subheader("Performance Frequency by Year")

    if dated_performances:
        year_counts = Counter(p.date.earliest_date.year for p in dated_performances)
        years = sorted(year_counts.keys())
        counts = [year_counts[year] for year in years]

        fig = px.bar(x=years, y=counts, labels={"x": "Year", "y": "Performances"}, text=counts)
        fig.update_traces(textposition="outside")
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")
        st.plotly_chart(fig, use_container_width=True)

    # Composer distribution
    st.subheader("Most Watched Composers")

    composer_counts = Counter(p.composer for p in performances)
    top_composers = composer_counts.most_common(10)

    composer_df = pd.DataFrame(
        {"Composer": [comp for comp, _ in top_composers], "Performances": [count for _, count in top_composers]}
    )

    fig = px.pie(composer_df, values="Performances", names="Composer", hole=0.4, title="Top 10 Composers")
    st.plotly_chart(fig, use_container_width=True)

    # Opera House Distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most Visited Venues")
        venue_counts = Counter(p.stage for p in performances)
        top_venues = venue_counts.most_common(5)

        venue_df = pd.DataFrame(
            {
                "Venue": [venues_db.get(venue, venue) for venue, _ in top_venues],
                "Visits": [count for _, count in top_venues],
            }
        )

        fig = px.bar(venue_df, x="Venue", y="Visits", text="Visits")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Most Watched Operas")
        opera_counts = Counter((p.name, p.composer) for p in performances)
        top_operas = opera_counts.most_common(5)

        opera_df = pd.DataFrame(
            {
                "Opera": [f"{name} ({truncate_composer_name(composer)})" for (name, composer), _ in top_operas],
                "Viewings": [count for _, count in top_operas],
            }
        )

        fig = px.bar(opera_df, x="Opera", y="Viewings", text="Viewings")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    # Monthly distribution of performances
    if dated_performances:
        st.subheader("Performance Distribution by Month")

        month_to_name = {i: calendar.month_name[i] for i in range(1, 13)}
        month_counts = Counter(p.date.earliest_date.month for p in dated_performances)

        month_df = pd.DataFrame(
            {
                "Month": [month_to_name[month] for month in range(1, 13)],
                "Performances": [month_counts.get(month, 0) for month in range(1, 13)],
            }
        )

        fig = px.line(
            month_df,
            x="Month",
            y="Performances",
            markers=True,
            category_orders={"Month": [month_to_name[i] for i in range(1, 13)]},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Production Analysis
    st.subheader("Production Analysis")

    # Group performances by opera (name, composer) and count unique productions
    opera_productions = defaultdict(set)
    for p in performances:
        if p.production_key:
            opera_productions[(p.name, p.composer)].add(p.production_key)

    # Calculate statistics
    operas_with_multiple_productions = [
        (name, composer, len(productions))
        for (name, composer), productions in opera_productions.items()
        if len(productions) > 1
    ]

    if operas_with_multiple_productions:
        # Sort by number of productions (descending)
        operas_with_multiple_productions.sort(key=lambda x: x[2], reverse=True)

        col1, col2 = st.columns(2)

        with col1:
            total_unique_productions = sum(len(productions) for productions in opera_productions.values())
            st.metric("Total Unique Productions", total_unique_productions)

            # Calculate average productions per opera
            operas_with_productions = sum(1 for prods in opera_productions.values() if prods)
            if operas_with_productions > 0:
                avg_productions = total_unique_productions / operas_with_productions
                st.metric("Average Productions per Opera", f"{avg_productions:.2f}")

        with col2:
            operas_multiple_productions = sum(1 for prods in opera_productions.values() if len(prods) > 1)
            st.metric("Operas seen in multiple productions", operas_multiple_productions)

            if operas_multiple_productions > 0:
                most_productions = max(len(prods) for prods in opera_productions.values())
                st.metric("Max productions of a single opera", most_productions)

        # Display operas with multiple productions
        st.subheader("Operas Seen in Multiple Productions")

        multi_prod_df = pd.DataFrame(
            {
                "Opera": [
                    f"{name} ({truncate_composer_name(composer)})"
                    for name, composer, _ in operas_with_multiple_productions
                ],
                "Productions": [count for _, _, count in operas_with_multiple_productions],
            }
        )

        fig = px.bar(
            multi_prod_df.head(10),
            x="Opera",
            y="Productions",
            text="Productions",
            title="Top 10 Operas by Number of Different Productions",
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    # Countries visited for opera
    st.subheader("Countries Visited for Opera")

    countries = set()
    country_counts = Counter()

    for performance in performances:
        stage = next(
            (stage for stage in load_db_venues(list_of_entries=True) if stage.short_name == performance.stage), None
        )
        if stage and stage.longitude is not None and stage.latitude is not None:
            coordinates = (float(stage.latitude), float(stage.longitude))
            location = rg.search(coordinates, mode=1)
            if location:
                country = location[0]["cc"]

                # convert from ISO 3166-1 alpha-2 to ISO 3166-1 alpha-3
                country = unidecode(country).upper()

                if len(country) == 2:
                    country = convert_alpha2_to_alpha3(country)

                countries.add(country)
                country_counts[country] += 1

    if countries:
        country_df = pd.DataFrame(
            {"Country": list(country_counts.keys()), "Performances": list(country_counts.values())}
        )

        fig = px.choropleth(
            country_df,
            locations="Country",
            color="Performances",
            hover_name="Country",
            color_continuous_scale=px.colors.sequential.Plasma,
        )
        fig.update_geos(fitbounds="locations")
        st.plotly_chart(fig, use_container_width=True)

    # Artists network analysis
    st.subheader("Artist Network Analysis")

    all_artists = set()
    for performance in performances:
        # Get cast
        for role, people in performance.cast.items():
            all_artists.update(people)
        # Get leading team
        for role, people in performance.leading_team.items():
            all_artists.update(people)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Unique Artists", len(all_artists))

        # Count artists by role
        leading_roles = set()
        for performance in performances:
            leading_roles.update(performance.leading_team.keys())

        st.metric("Different Creative Team Roles", len(leading_roles))

    with col2:
        cast_roles = set()
        for performance in performances:
            cast_roles.update(performance.cast.keys())

        st.metric("Different Cast Roles", len(cast_roles))

        # Calculate average cast size
        cast_sizes = [sum(len(people) for people in performance.cast.values()) for performance in performances]
        if cast_sizes:
            avg_cast_size = sum(cast_sizes) / len(cast_sizes)
            st.metric("Average Cast Size", f"{avg_cast_size:.1f}")


def run():
    modes = {
        ":material/query_stats: Overview": run_expanded_stats,
        ":material/monitoring: Numbers": run_frequencies,
        ":material/language: Map": run_maps,
        ":material/music_note: Opera": run_single_opus,
        ":material/person_search: Artist": run_single_person,
        ":material/person_pin: Role": run_single_role,
    }

    with st.sidebar:
        function = modes.get(st.radio("Items", modes))

    function()
