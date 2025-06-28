import calendar
from collections import defaultdict
from typing import (
    ChainMap,
    DefaultDict,
    MutableSequence,
)

import streamlit as st
from more_itertools.recipes import flatten

from pyopera.common import (
    get_all_names_from_performance,
)
from pyopera.show_overview import create_performances_markdown_string
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


def run_query_and_analytics():
    """Combined query and analytics page that allows filtering and visualization of the data."""
    st.title("Query & Analytics")

    month_to_month_name = {i: calendar.month_abbr[i] for i in range(1, 13)}
    db = load_db()

    # === FILTERING SECTION ===
    with st.expander("Filter Performances", expanded=False):
        all_singers = sorted({person for performance in db for person in flatten(performance.cast.values())})
        all_leading_team = sorted(
            {person for performance in db for person in flatten(performance.leading_team.values())}
        )
        all_venues = sorted({performance.stage for performance in db if performance.stage is not None})
        all_composers = sorted({performance.composer for performance in db if performance.composer is not None})

        st.markdown("#### Cast & Team")

        col1, col2 = st.columns([1, 3])
        with col1:
            match_singers = st.segmented_control(
                "Match Singers",
                ["ALL", "ANY"],
                key="match_type",
                default="ALL",
                help="Select how to match singers in the cast. 'ALL' means all selected singers must be present, 'ANY' means at least one singer must be present.",
            )
        with col2:
            singers = st.multiselect("Select Singers", all_singers)

        col1, col2 = st.columns([1, 3])

        with col1:
            match_leading_team = st.segmented_control(
                "Match Leading Team",
                ["ALL", "ANY"],
                key="match_leading_team_type",
                default="ALL",
                help="Select how to match leading team members. 'ALL' means all selected members must be present, 'ANY' means at least one member must be present.",
            )

        with col2:
            leading_team = st.multiselect("Select Leading Team", all_leading_team)

        st.markdown("### Works & Venues")

        composers = st.multiselect("Select Composer", all_composers)

        all_operas = sorted(
            {
                performance.name
                for performance in db
                if performance.name is not None and (len(composers) == 0 or performance.composer in composers)
            }
        )
        opera_names = st.multiselect("Select Opera", all_operas)
        venues = st.multiselect("Select Venue", all_venues)

        concertant_mode = st.segmented_control(
            "Concertant Mode",
            ["ALL", "CONCERTANT", "NON_CONCERTANT"],
            key="concertant_mode",
            default="ALL",
            help="Select the concertant mode of the performances. 'ALL' includes all performances, 'CONCERTANT' includes only concertant performances, and 'NON_CONCERTANT' includes only non-concertant performances.",
        )

        # Apply filters
        aggregate_singers = all if match_singers == "ALL" else any
        aggregate_leading_team = all if match_leading_team == "ALL" else any

        filtered_performances = [
            performance
            for performance in db
            if (
                len(singers) == 0
                or aggregate_singers(singer in flatten(performance.cast.values()) for singer in singers)
            )
            and (
                len(leading_team) == 0
                or aggregate_leading_team(
                    person in flatten(performance.leading_team.values()) for person in leading_team
                )
            )
            and (len(venues) == 0 or performance.stage in venues)
            and (len(composers) == 0 or performance.composer in composers)
            and (len(opera_names) == 0 or performance.name in opera_names)
            and (
                concertant_mode == "ALL"
                or (concertant_mode == "CONCERTANT" and performance.is_concertante)
                or (concertant_mode == "NON_CONCERTANT" and not performance.is_concertante)
            )
        ]

    if len(filtered_performances) == 0:
        st.warning("No performances found for the selected criteria.")
        return

    # === ANALYTICS SECTION ===

    st.markdown(
        f"### Analytics ({len(filtered_performances)} {'performances' if len(filtered_performances) > 1 else 'performance'})"
    )

    # Analytics configuration
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        options = st.multiselect(
            "Group by",
            filter(
                lambda el: isinstance(getattr(db[0], el), (str, int)) and el not in ("comments", "key"),
                db[0].model_dump().keys(),
            ),
            default=["name", "composer"],
            format_func=format_column_name,
            help="Select the columns to group by for frequency analysis. You can select multiple columns.",
        )

    with col2:
        number_to_show = st.number_input("Bars to show", 1, value=15, step=5)

    with col3:
        show_all = st.checkbox("Show all")

    if show_all:
        number_to_show = None

    # Generate frequency chart for filtered data
    if len(options) > 0:
        # Prepare data for frequency analysis
        if any(option in ("day", "month", "year") for option in options):
            analysis_db = add_split_earliest_date_to_db(filtered_performances)
        else:
            analysis_db = [entry.model_dump() for entry in filtered_performances]

        create_frequency_chart(
            analysis_db,
            options,
            number_to_show,
            column_mapper={
                "month": month_to_month_name.get,
                "composer": truncate_composer_name,
                "date": lambda el: ".".join(el.split("T")[0].split("-")[::-1]),
            },
        )
    else:
        st.info("Select categories above to see frequency analysis")

    # === DETAILED RESULTS SECTION ===
    st.markdown("### Detailed Results")

    performances_md_string = create_performances_markdown_string(
        filtered_performances,
        load_db_venues(),
        include_header=False,
    )
    st.markdown(performances_md_string, unsafe_allow_html=True)


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
        ":material/analytics: Query & Analytics": run_query_and_analytics,
        ":material/music_note: Opera": run_single_opus,
        ":material/person_search: Artist": run_single_person,
        ":material/person_pin: Role": run_single_role,
    }

    with st.sidebar:
        function = modes.get(st.radio("Items", modes))

    function()
