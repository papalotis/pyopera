import calendar
from collections import Counter, defaultdict
from datetime import datetime
from typing import Sequence

import pandas as pd
import plotly.express as px
import reverse_geocoder as rg
import streamlit as st
from unidecode import unidecode

from pyopera.common import Performance
from pyopera.show_maps import run_maps
from pyopera.show_stats_utils import convert_alpha2_to_alpha3, truncate_composer_name
from pyopera.streamlit_common import load_db, load_db_venues


def run_expanded_stats():
    performances = load_db()
    venues_db = load_db_venues()

    st.title("Opera Statistics Dashboard")

    st.subheader("Statistics Overview")

    # Top-level metrics
    col1, col2, col3 = st.columns(3)

    # Calculate productions
    opera_productions = defaultdict(set)
    for p in performances:
        if p.production_key:
            opera_productions[(p.name, p.composer)].add(p.production_key)
    total_unique_productions = sum(len(productions) for productions in opera_productions.values())

    # Calculate unique operas
    unique_operas = len({(p.name, p.composer) for p in performances})

    # Calculate concertante performances
    concertante_count = sum(1 for p in performances if p.is_concertante)

    # Calculate years of opera-going
    dated_performances = [p for p in performances if p.date is not None]
    years_span = None
    if dated_performances:
        years_span = (
            max(p.date.latest_date.year for p in dated_performances)
            - min(p.date.earliest_date.year for p in dated_performances)
            + 1
        )

    with col1:
        st.metric("Operas", unique_operas)
    with col2:
        st.metric("Performances", len(performances))
    with col3:
        st.metric("Concertante Performances", f"{concertante_count} ({concertante_count/len(performances):.1%})")

    with col1:
        st.metric("Productions", total_unique_productions)
    with col2:
        st.metric("Composers", len(set(p.composer for p in performances)))
    with col3:
        st.metric("Venues", len(set(p.stage for p in performances)))

    with col1:
        if years_span:
            st.metric("Years of Opera-going", years_span)
    # col2 and col3 are empty

    if False:
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

    # Add new bar graphs with top 20 view + option to see all
    st.subheader("Graphs")

    # Use selectbox instead of tabs for better space management
    graph_options = [
        "Operas by Composer",
        "Performances by Opera",
        "Productions by Opera",
        "Performances by Composer",
        "Performances by Venue",
        "Performances by Year",
    ]

    selected_graph = st.selectbox("Select graph to display:", graph_options)

    show_all = st.checkbox("Show all", key="show_all")

    # Operas by Composer
    if selected_graph == "Operas by Composer":
        composer_operas = {}
        for p in performances:
            composer = p.composer
            opera = (p.name, p.composer)
            if composer not in composer_operas:
                composer_operas[composer] = set()
            composer_operas[composer].add(opera)

        composer_opera_counts = [(composer, len(operas)) for composer, operas in composer_operas.items()]
        composer_opera_counts.sort(key=lambda x: x[1], reverse=True)

        data_to_show = composer_opera_counts if show_all else composer_opera_counts[:20]

        composer_opera_df = pd.DataFrame(
            {"Composer": [comp for comp, _ in data_to_show], "Operas": [count for _, count in data_to_show]}
        )

        fig = px.bar(composer_opera_df, x="Composer", y="Operas", text="Operas")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig, use_container_width=True)

    # Performances by Opera
    elif selected_graph == "Performances by Opera":
        opera_performance_counts = Counter((p.name, p.composer) for p in performances)
        opera_perf_data = [
            (f"{name} ({truncate_composer_name(composer)})", count)
            for (name, composer), count in opera_performance_counts.most_common()
        ]

        opera_perf_to_show = opera_perf_data if show_all else opera_perf_data[:20]

        opera_perf_df = pd.DataFrame(
            {
                "Opera": [name for name, _ in opera_perf_to_show],
                "Performances": [count for _, count in opera_perf_to_show],
            }
        )

        fig = px.bar(opera_perf_df, x="Opera", y="Performances", text="Performances")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig, use_container_width=True)

    # Productions by Opera
    elif selected_graph == "Productions by Opera":
        opera_prod_data = [
            (f"{name} ({truncate_composer_name(composer)})", len(productions))
            for (name, composer), productions in opera_productions.items()
            if productions
        ]
        opera_prod_data.sort(key=lambda x: x[1], reverse=True)

        opera_prod_to_show = opera_prod_data if show_all else opera_prod_data[:20]

        opera_prod_df = pd.DataFrame(
            {
                "Opera": [name for name, _ in opera_prod_to_show],
                "Productions": [count for _, count in opera_prod_to_show],
            }
        )

        fig = px.bar(opera_prod_df, x="Opera", y="Productions", text="Productions")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig, use_container_width=True)

    # Performances by Composer
    elif selected_graph == "Performances by Composer":
        composer_perf_counts = Counter(p.composer for p in performances)
        composer_perf_data = composer_perf_counts.most_common()

        composer_perf_to_show = composer_perf_data if show_all else composer_perf_data[:20]

        composer_perf_df = pd.DataFrame(
            {
                "Composer": [comp for comp, _ in composer_perf_to_show],
                "Performances": [count for _, count in composer_perf_to_show],
            }
        )

        fig = px.bar(composer_perf_df, x="Composer", y="Performances", text="Performances")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig, use_container_width=True)

    # Performances by Venue
    elif selected_graph == "Performances by Venue":
        venue_counts = Counter(p.stage for p in performances)
        venue_data = [(venues_db.get(venue, venue), count) for venue, count in venue_counts.most_common()]

        venue_to_show = venue_data if show_all else venue_data[:20]

        venue_df = pd.DataFrame(
            {"Venue": [venue for venue, _ in venue_to_show], "Performances": [count for _, count in venue_to_show]}
        )

        fig = px.bar(venue_df, x="Venue", y="Performances", text="Performances")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig, use_container_width=True)

    # Performances by Year
    elif selected_graph == "Performances by Year":
        if dated_performances:
            year_counts = Counter(p.date.earliest_date.year for p in dated_performances)
            years = sorted(year_counts.keys())
            counts = [year_counts[year] for year in years]

            year_df = pd.DataFrame({"Year": years, "Performances": counts})

            fig = px.bar(year_df, x="Year", y="Performances", text="Performances")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    # Add maps visualization at the end
    st.subheader("Map")
    run_maps()
