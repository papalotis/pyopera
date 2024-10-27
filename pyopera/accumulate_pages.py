from typing import Callable

import streamlit as st

from pyopera.add_seen_performance import run as run_add_seen_performance
from pyopera.generate_logo import generate_logo
from pyopera.show_overview import run as run_overview
from pyopera.show_stats import run as run_stats
from pyopera.visualize_json import run as run_vis_json

CALLABLE_TITLE_ICON: list[tuple[Callable[[], None], str, str]] = [
    (run_overview, "Overview", ":material/bar_chart:"),
    (run_vis_json, "Performances", ":material/theater_comedy:"),
    (run_stats, "Search", ":material/search:"),
    (run_add_seen_performance, "Edit database", ":material/build:"),
]


def create_pages():
    return [
        st.Page(
            kallable, title=title, icon=icon, url_path=title.lower().replace(" ", "_")
        )
        for kallable, title, icon in CALLABLE_TITLE_ICON
    ]


def main():
    if "run_counter" not in st.session_state:
        st.session_state.run_counter = 0

    st.session_state.run_counter += 1

    st.logo(generate_logo(), size="large")
    page = st.navigation(create_pages())
    page.run()
