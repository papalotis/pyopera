from typing import Sequence

import streamlit as st
from common import Performance, WorkYearEntryModel
from pydantic import BaseModel
from streamlit_common import (
    load_db,
    load_db_works_year,
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


# hide_hamburger_and_change_footer()

STRING_TO_FUNCTION = {
    "Overview": run_overview,
    "Performances": run_vis_json,
    "Search": run_stats,
    "Edit database": run_add_seen_performance,
}


def download_button() -> None:
    import platform

    from approx_dates.models import ApproxDate

    if platform.processor() in ("", None):
        # running on streamlit sharing, so no need to download
        return

    db = load_db()
    works_dates_db = list(load_db_works_year().values())

    class CombinedModel(BaseModel):
        performances: Sequence[Performance]
        works_dates: Sequence[WorkYearEntryModel]

        class Config:
            json_encoders = {ApproxDate: str}

    combined_model = CombinedModel(performances=db, works_dates=works_dates_db)
    combined_model_json = combined_model.json()

    st.download_button(
        "Download database as JSON",
        combined_model_json,
        file_name="database.json",
        mime="application/json",
        help="Download the database content as a JSON file",
    )


def get_default_mode() -> int:
    try:
        params = st.query_params
        mode_params = params["mode"][0]
        try:
            default_index = list(STRING_TO_FUNCTION).index(mode_params)
        except ValueError:
            st.warning(f"Mode {mode_params} could not be found.")
            default_index = 0
    except KeyError:
        default_index = 0

    return default_index


with st.sidebar:
    st.title(NAME)

    mode_function = STRING_TO_FUNCTION.get(
        st.radio("Mode", STRING_TO_FUNCTION, index=get_default_mode())
    )


mode_function()

with st.sidebar:
    st.markdown("#")
    download_button()
