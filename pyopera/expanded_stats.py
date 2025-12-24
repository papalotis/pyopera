import calendar
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Sequence

import pandas as pd
import plotly.express as px
import reverse_geocoder as rg
import streamlit as st
from unidecode import unidecode

from pyopera.common import Performance, get_top_streaks, group_performances_by_visit, pluralize
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

    # Top Streaks
    # Calculate top streaks
    n = 3
    top_streaks = get_top_streaks(performances, n=n)
    if top_streaks and top_streaks[0][0] > 1:
        streak_strs = []
        for i, (streak_len, streak_range) in enumerate(top_streaks, 1):
            if streak_len > 1:
                streak_strs.append(f"{i}. {streak_len} days ({streak_range})")

        if streak_strs:
            facts.append(
                (
                    "**Longest Streaks**:\n  " + "\n  ".join(streak_strs),
                    f"Top {n} longest streaks of consecutive days with performances.",
                )
            )

    if performances:
        # Most Performed Opera
        opera_counts = Counter((p.name, p.composer) for p in performances)
        (name, composer), count = opera_counts.most_common(1)[0]
        facts.append(
            (
                f"**Most Performed Opera**: {name} ({truncate_composer_name(composer)}) — {count} performances",
                "The opera you have seen the most times.",
            )
        )

        # Most Performed Composer
        composer_counts = Counter(p.composer for p in performances)
        composer, count = composer_counts.most_common(1)[0]
        facts.append(
            (
                f"**Most Performed Composer**: {composer} — {count} performances",
                "The composer whose works you have seen the most.",
            )
        )

        # Most Visited Venue
        # group by visit (so that we do not double count multiple performances at same venue in one visit)

        visits = group_performances_by_visit(performances)

        venue_counts = Counter(visit[0].stage for visit in visits.values())
        venue, count = venue_counts.most_common(1)[0]
        venue_name = venues_db.get(venue, venue)
        facts.append(
            (
                f"**Most Visited Venue**: {venue_name} — {count} visits",
                "The venue you have visited the most times (grouped by visit).",
            )
        )

        # Busiest Year
        dated_visits = [visit for visit in visits.values() if visit[0].date]
        if dated_visits:
            year_counts = Counter(visit[0].date.earliest_date.year for visit in dated_visits)
            year, count = year_counts.most_common(1)[0]
            facts.append((f"**Busiest Year**: {year} — {count} visits", "The calendar year with the most visits."))

            # Busiest Month
            month_counts = Counter(visit[0].date.earliest_date.strftime("%B") for visit in dated_visits)
            month, count = month_counts.most_common(1)[0]
            facts.append(
                (
                    f"**Busiest Month**: {month} — {count} visits",
                    "The month of the year with the most visits (aggregated across all years).",
                )
            )

        # Most Seen Production
        production_counts = Counter(p.production_key for p in performances if p.production_key)
        if production_counts:
            (identifying_person, production_name, opera_name, composer), count = production_counts.most_common(1)[0]
            if count > 1:
                facts.append(
                    (
                        f"**Most Seen Production**: {opera_name} ({truncate_composer_name(composer)}) by {production_name} ({identifying_person}) — {count} {pluralize(count, 'performance')}",
                        "The specific production (Director/Conductor combination) you have seen the most times.",
                    )
                )

    # Opera with Most Productions
    if opera_productions:
        (name, composer), productions = max(opera_productions.items(), key=lambda x: len(x[1]))
        count = len(productions)
        facts.append(
            (
                f"**Opera with Most Productions**: {name} ({truncate_composer_name(composer)}) — {count} productions",
                "The opera for which you have seen the most different productions.",
            )
        )

    # --- Wacky Stats ---

    # The Chameleon (Artist with most unique roles)
    artist_roles = defaultdict(set)
    for p in performances:
        for role, artists in p.cast.items():
            for artist in artists:
                artist_roles[artist].add(role)

    if artist_roles:
        chameleon, roles = max(artist_roles.items(), key=lambda x: len(x[1]))
        if len(roles) > 1:
            facts.append(
                (
                    f"**The Chameleon**: {chameleon} — {len(roles)} different roles",
                    "The artist who has performed the most unique roles.",
                )
            )

    # The Deja Vu (Opera seen in most unique venues)
    opera_venues = defaultdict(set)
    for p in performances:
        opera_venues[(p.name, p.composer)].add(p.stage)

    if opera_venues:
        (opera, composer), venues = max(opera_venues.items(), key=lambda x: len(x[1]))
        if len(venues) > 1:
            facts.append(
                (
                    f"**The Deja Vu**: {opera} ({truncate_composer_name(composer)}) — seen in {len(venues)} different venues",
                    "The opera seen in the most unique venues.",
                )
            )

    # The Variety Spice (Longest streak of different operas)
    sorted_perfs = sorted([p for p in performances if p.date], key=lambda x: x.date.earliest_date)
    max_variety = 0
    current_variety = []

    for p in sorted_perfs:
        opera_id = (p.name, p.composer)
        if opera_id in current_variety:
            # Streak broken, remove everything up to and including the first occurrence
            idx = current_variety.index(opera_id)
            current_variety = current_variety[idx + 1 :]
        current_variety.append(opera_id)
        max_variety = max(max_variety, len(current_variety))

    if max_variety > 1:
        facts.append(
            (
                f"**The Variety Spice**: {max_variety} consecutive performances without repeating an opera",
                "The longest streak of consecutive performances without repeating an opera.",
            )
        )

    # The Cast Hog (Performance with largest cast)
    # Count total number of artists in cast (sum of lengths of lists in values)
    if performances:
        cast_hog = max(performances, key=lambda p: sum(len(artists) for artists in p.cast.values()))
        cast_size = sum(len(artists) for artists in cast_hog.cast.values())
        facts.append(
            (
                f"**The Cast Hog**: {cast_hog.name} ({truncate_composer_name(cast_hog.composer)}) — {cast_size} cast members",
                "The single performance with the largest number of cast members listed.",
            )
        )

    # The Double Dipper (Days with >1 performance)
    dates = [p.date.earliest_date for p in performances if p.date]
    if dates:
        date_counts = Counter(dates)
        double_dip_days = sum(1 for count in date_counts.values() if count > 1)
        if double_dip_days > 0:
            facts.append(
                (
                    f"**The Double Dipper**: {double_dip_days} days with multiple performances",
                    "The number of days where you attended more than one performance.",
                )
            )

    # The Weekend Warrior (Performances on Sat/Sun)
    weekend_count = sum(1 for p in performances if p.date and p.date.earliest_date.weekday() >= 5)
    if performances and weekend_count > 0:
        percentage = (weekend_count / len(performances)) * 100
        facts.append(
            (
                f"**The Weekend Warrior**: {weekend_count} performances on weekends ({percentage:.1f}%)",
                "The number and percentage of performances attended on Saturdays or Sundays.",
            )
        )

    # The Conductor Collector
    conductors = set()
    conductor_keys = ["Musikalische Leitung", "Dirigent", "Conductor"]
    for p in performances:
        for key in conductor_keys:
            if key in p.leading_team:
                conductors.update(p.leading_team[key])

    if conductors:
        facts.append(
            (
                f"**The Conductor Collector**: {len(conductors)} unique conductors seen",
                "The total number of unique conductors you have seen.",
            )
        )

    # The One-Night Stand (Operas seen exactly once)
    if performances:
        single_view_operas = sum(1 for count in opera_counts.values() if count == 1)
        if single_view_operas > 0:
            facts.append(
                (
                    f"**The One-Night Stand**: {single_view_operas} operas seen exactly once",
                    "The number of operas you have seen exactly once.",
                )
            )

    for fact, tooltip in facts:
        st.markdown(f"- {fact}", help=tooltip)
