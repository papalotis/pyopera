from typing import Callable, Sequence

import streamlit as st
from common import Performance, WorkYearEntryModel
from pydantic import BaseModel, ConfigDict
from streamlit_common import (
    load_db,
    load_db_works_year,
    runs_on_streamlit_sharing,
)

NAME = "Vangelis OperArchive"
st.set_page_config(
    page_title=NAME,
    page_icon=":violin:",
    menu_items={"About": "An interface for Vangelis' Opera Archive"},
)

# this is a trick so that isort does not put the imports above the set config line
if True:
    from add_seen_performance import run as run_add_seen_performance
    from show_overview import run as run_overview
    from show_stats import run as run_stats
    from visualize_json import run as run_vis_json


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


def download_button() -> None:
    return
    from approx_dates.models import ApproxDate

    if runs_on_streamlit_sharing():
        # running on streamlit sharing, so no need to download
        return

    db = load_db()
    works_dates_db = list(load_db_works_year().values())

    class CombinedModel(BaseModel):
        performances: Sequence[Performance]
        works_dates: Sequence[WorkYearEntryModel]

        model_config = ConfigDict(json_encoders={ApproxDate: str})

    combined_model = CombinedModel(performances=db, works_dates=works_dates_db)
    combined_model_json = combined_model.json()

    st.download_button(
        "Download database as JSON",
        combined_model_json,
        file_name="database.json",
        mime="application/json",
        help="Download the database content as a JSON file",
    )


page = st.navigation(create_pages())
page.run()


with st.sidebar:
    st.markdown("#")
    download_button()
