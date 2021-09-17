import streamlit as st
from streamlit import caching

NAME = "Vangelis Opera Archiv"
st.set_page_config(page_title=NAME, page_icon=":violin:")

if True:
    from add_seen_performance import run as run_add_performance
    from show_stats import run as run_stats
    from visualize_json import run as run_vis_json


FUNCTION_TO_STRING = {
    run_vis_json: "Explore visits",
    run_stats: "Explore stats",
    run_add_performance: "Edit database",
}

with st.sidebar:
    st.title(NAME)

    mode_function = st.radio(
        "Mode", FUNCTION_TO_STRING, format_func=FUNCTION_TO_STRING.get
    )

mode_function()

with st.sidebar:
    st.markdown("#")
    if st.button("Clear cache"):
        caching.clear_cache()

    st.markdown(
        "#\n\n#\n\n---\n\n<sup>made by Panagiotis</sup>", unsafe_allow_html=True
    )
