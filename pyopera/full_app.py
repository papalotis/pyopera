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
    from show_stats import run as run_stats
    from streamlit_common import hide_hamburger_and_change_footer
    from visualize_json import run as run_vis_json


hide_hamburger_and_change_footer()

STRING_TO_FUNCTION = {
    "Explore visits": run_vis_json,
    "Explore statistics": run_stats,
    "Edit database": run_add_performance,
}

with st.sidebar:
    st.title(NAME)

    mode_function = STRING_TO_FUNCTION.get(st.radio("Mode", STRING_TO_FUNCTION))

mode_function()

with st.sidebar:
    st.markdown("#")
    st.button("Clear cache", on_click=clear_streamlit_cache)
