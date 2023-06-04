import streamlit as st

from deta_base import convert_list_of_performances_to_json
from streamlit_common import clear_streamlit_cache, load_db

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
    from show_overview import run as run_overview_performances
    from show_stats import run as run_stats
    from streamlit_common import hide_hamburger_and_change_footer
    from visualize_json import run as run_vis_json


hide_hamburger_and_change_footer()

STRING_TO_FUNCTION = {
    "Overview": run_overview,
    "Performances": run_vis_json,
    "Search": run_stats,
    "Edit database": run_add_seen_performance,
}


def download_button() -> None:
    db = load_db()
    json_string = convert_list_of_performances_to_json(db)
    st.download_button(
        "Download database as JSON",
        json_string,
        file_name="database.json",
        mime="application/json",
        help="Download the database content as a JSON file",
    )


def get_default_mode() -> int:
    try:
        params = st.experimental_get_query_params()
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

    st.markdown("#")
    download_button()
    st.button(
        "Clear cache",
        on_click=clear_streamlit_cache,
        help="Clear the application cache",
    )


mode_function()
