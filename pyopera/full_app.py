import streamlit as st

from streamlit_common import clear_streamlit_cache

NAME = "Vangelis Opera Archiv"
st.set_page_config(
    page_title=NAME,
    page_icon=":violin:",
    menu_items={"About": "An interface for Vangelis' Opera Archive"},
)

# this is a trick so that isort does not put the imports above the set config line
if True:
    from add_seen_performance import run as run_add_performance
    from show_overview import run as run_overview
    from show_stats import run as run_stats
    from streamlit_common import hide_hamburger_and_change_footer
    from visualize_json import run as run_vis_json


hide_hamburger_and_change_footer()

STRING_TO_FUNCTION = {
    "Explore visits": run_vis_json,
    "Overview": run_overview,
    "Explore statistics": run_stats,
    "Edit database": run_add_performance,
}


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

mode_function()

with st.sidebar:
    st.markdown("#")
    st.button("Clear cache", on_click=clear_streamlit_cache)
