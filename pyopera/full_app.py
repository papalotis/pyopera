import streamlit as st
from streamlit import caching

NAME = "Vangelis Opera Archiv"
st.set_page_config(page_title=NAME, page_icon=":violin:")

if True:
    from add_seen_performance import run as run_add_performance
    from show_stats import run as run_stats
    from visualize_json import run as run_vis_json


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
    if st.button("Clear cache"):
        caching.clear_cache()

    st.markdown("---\n<sup>made by Panagiotis</sup>", unsafe_allow_html=True)
