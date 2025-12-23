import calendar
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Sequence

import pandas as pd
import plotly.express as px
import reverse_geocoder as rg
import streamlit as st
from unidecode import unidecode

from pyopera.common import Performance, group_performances_by_visit, pluralize
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

    # Calculate visits
    unique_visits = {p.visit_index for p in performances if p.visit_index}
    performances_without_visit = sum(1 for p in performances if not p.visit_index)
    total_visits = len(unique_visits) + performances_without_visit

    # Calculate longest streak
    dates = sorted({p.date.earliest_date for p in performances if p.date})
    longest_streak = 0
    streak_range_str = ""

    if dates:
        longest_streak = 1
        current_streak = 1
        streak_end_date = dates[0]

        for i in range(1, len(dates)):
            if dates[i] == dates[i - 1] + timedelta(days=1):
                current_streak += 1
            else:
                if current_streak > longest_streak:
                    longest_streak = current_streak
                    streak_end_date = dates[i - 1]
                current_streak = 1

        if current_streak > longest_streak:
            longest_streak = current_streak
            streak_end_date = dates[-1]

        streak_start_date = streak_end_date - timedelta(days=longest_streak - 1)
        streak_range_str = f"{streak_start_date.strftime('%d.%m.%y')} - {streak_end_date.strftime('%d.%m.%y')}"

    with col1:
        st.metric("Operas", unique_operas)
        st.metric("Visits", total_visits)
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
        "Visits by Venue",
        "Visits by Year",
    ]

    selected_graph = st.selectbox("Select graph to display:", graph_options)

    show_as_table = st.checkbox("Show as table", key="show_as_table")

    if show_as_table:
        show_all = True
    else:
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

        if show_as_table:
            st.dataframe(composer_opera_df, use_container_width=True, hide_index=True)

        else:
            fig = px.bar(composer_opera_df, x="Composer", y="Operas", text="Operas")
            fig.update_traces(
                textposition="outside",
                cliponaxis=False,
            )
            fig.update_layout(
                xaxis={
                    "categoryorder": "total descending",
                }
            )
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

        if show_as_table:
            st.dataframe(opera_perf_df, use_container_width=True, hide_index=True)
        else:
            fig = px.bar(opera_perf_df, x="Opera", y="Performances", text="Performances")
            fig.update_traces(
                textposition="outside",
                cliponaxis=False,
            )
            fig.update_layout(
                xaxis={
                    "categoryorder": "total descending",
                }
            )
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

        if show_as_table:
            st.dataframe(opera_prod_df, use_container_width=True, hide_index=True)

        else:
            fig = px.bar(opera_prod_df, x="Opera", y="Productions", text="Productions")
            fig.update_traces(
                textposition="outside",
                cliponaxis=False,
            )
            fig.update_layout(
                xaxis={
                    "categoryorder": "total descending",
                }
            )
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

        if show_as_table:
            st.dataframe(composer_perf_df, use_container_width=True, hide_index=True)

        else:
            fig = px.bar(composer_perf_df, x="Composer", y="Performances", text="Performances")
            fig.update_traces(
                textposition="outside",
                cliponaxis=False,
            )
            fig.update_layout(
                xaxis={
                    "categoryorder": "total descending",
                }
            )
            st.plotly_chart(fig, use_container_width=True)

    # Performances by Venue
    elif selected_graph == "Performances by Venue":
        venue_counts = Counter(p.stage for p in performances)
        venue_data = [(venues_db.get(venue, venue), count) for venue, count in venue_counts.most_common()]

        venue_to_show = venue_data if show_all else venue_data[:20]

        venue_df = pd.DataFrame(
            {"Venue": [venue for venue, _ in venue_to_show], "Performances": [count for _, count in venue_to_show]}
        )

        if show_as_table:
            st.dataframe(venue_df, use_container_width=True, hide_index=True)
        else:
            fig = px.bar(venue_df, x="Venue", y="Performances", text="Performances")
            fig.update_traces(
                textposition="outside",
                cliponaxis=False,
            )
            fig.update_layout(
                xaxis={
                    "categoryorder": "total descending",
                }
            )
            st.plotly_chart(fig, use_container_width=True)

    # Performances by Year
    elif selected_graph == "Performances by Year":
        # Calculate years of opera-going
        dated_performances = [p for p in performances if p.date is not None]

        if dated_performances:
            year_counts = Counter(p.date.earliest_date.year for p in dated_performances)
            years = sorted(year_counts.keys())
            counts = [year_counts[year] for year in years]

            year_df = pd.DataFrame({"Year": years, "Performances": counts})

            if show_as_table:
                st.dataframe(year_df, use_container_width=True, hide_index=True)
            else:
                fig = px.bar(year_df, x="Year", y="Performances", text="Performances")
                fig.update_traces(
                    textposition="outside",
                    cliponaxis=False,
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No performances with valid dates found.")

    # Visits by Venue
    elif selected_graph == "Visits by Venue":
        visit_stages = []
        visits = defaultdict(list)

        for p in performances:
            if p.visit_index:
                visits[p.visit_index].append(p)
            else:
                visit_stages.append(p.stage)

        for visit_id, perfs in visits.items():
            stages = {p.stage for p in perfs}
            if len(stages) > 1:
                raise ValueError(f"found visit {visit_id} with multiple stages: {stages}")
            visit_stages.append(stages.pop())

        venue_counts = Counter(visit_stages)
        venue_data = [(venues_db.get(venue, venue), count) for venue, count in venue_counts.most_common()]
        venue_to_show = venue_data if show_all else venue_data[:20]

        venue_df = pd.DataFrame(
            {
                "Venue": [venue for venue, _ in venue_to_show],
                "Visits": [count for _, count in venue_to_show],
            }
        )

        if show_as_table:
            st.dataframe(venue_df, use_container_width=True, hide_index=True)
        else:
            fig = px.bar(venue_df, x="Venue", y="Visits", text="Visits")
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(xaxis={"categoryorder": "total descending"})
            st.plotly_chart(fig, use_container_width=True)

    # Visits by Year
    elif selected_graph == "Visits by Year":
        visit_years = []
        visits = defaultdict(list)

        for p in performances:
            if p.visit_index:
                visits[p.visit_index].append(p)
            elif p.date:
                visit_years.append(p.date.earliest_date.year)

        for visit_id, perfs in visits.items():
            dated_perfs = [p for p in perfs if p.date]
            if dated_perfs:
                earliest_year = min(p.date.earliest_date.year for p in dated_perfs)
                visit_years.append(earliest_year)

        if visit_years:
            year_counts = Counter(visit_years)
            years = sorted(year_counts.keys())
            counts = [year_counts[year] for year in years]

            year_df = pd.DataFrame({"Year": years, "Visits": counts})

            if show_as_table:
                st.dataframe(year_df, use_container_width=True, hide_index=True)
            else:
                fig = px.bar(year_df, x="Year", y="Visits", text="Visits")
                fig.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No visits with valid dates found.")

    # Add maps visualization at the end
    st.subheader("Visits Map")
    run_maps()

    st.subheader("Interesting Facts")

    facts = []

    # Longest Streak
    if longest_streak > 1:
        facts.append(f"**Longest Streak**: {longest_streak} days ({streak_range_str})")

    if performances:
        # Most Performed Opera
        opera_counts = Counter((p.name, p.composer) for p in performances)
        (name, composer), count = opera_counts.most_common(1)[0]
        facts.append(f"**Most Performed Opera**: {name} ({truncate_composer_name(composer)}) — {count} performances")

        # Most Performed Composer
        composer_counts = Counter(p.composer for p in performances)
        composer, count = composer_counts.most_common(1)[0]
        facts.append(f"**Most Performed Composer**: {composer} — {count} performances")

        # Most Visited Venue
        # group by visit (so that we do not double count multiple performances at same venue in one visit)

        visits = group_performances_by_visit(performances)

        venue_counts = Counter(visit[0].stage for visit in visits.values())
        venue, count = venue_counts.most_common(1)[0]
        venue_name = venues_db.get(venue, venue)
        facts.append(f"**Most Visited Venue**: {venue_name} — {count} visits")

        # Busiest Year
        dated_visits = [visit for visit in visits.values() if visit[0].date]
        if dated_visits:
            year_counts = Counter(visit[0].date.earliest_date.year for visit in dated_visits)
            year, count = year_counts.most_common(1)[0]
            facts.append(f"**Busiest Year**: {year} — {count} visits")

            # Busiest Month
            month_counts = Counter(visit[0].date.earliest_date.strftime("%B") for visit in dated_visits)
            month, count = month_counts.most_common(1)[0]
            facts.append(f"**Busiest Month**: {month} — {count} visits")

        # Most Seen Production
        production_counts = Counter(p.production_key for p in performances if p.production_key)
        if production_counts:
            (identifying_person, production_name, opera_name, composer), count = production_counts.most_common(1)[0]
            if count > 1:
                facts.append(
                    f"**Most Seen Production**: {opera_name} ({truncate_composer_name(composer)}) by {production_name} ({identifying_person}) — {count} {pluralize(count, 'performance')}"
                )

    # Opera with Most Productions
    if opera_productions:
        (name, composer), productions = max(opera_productions.items(), key=lambda x: len(x[1]))
        count = len(productions)
        facts.append(
            f"**Opera with Most Productions**: {name} ({truncate_composer_name(composer)}) — {count} productions"
        )

    for fact in facts:
        st.markdown(f"- {fact}")
