import streamlit as st
from streamlit import caching

from add_seen_performance import run as run_add_performance
from visualize_json import run as run_vis_json

NAME = "Vangelis Opera Archiv"
st.set_page_config(page_title=NAME, page_icon=":violin:")

with st.sidebar:
    st.title(NAME)
    mode = st.radio("Mode", ["Visualization", "Add new performance"])

if mode == "Visualization":
    run_vis_json()
else:
    run_add_performance()

with st.sidebar:
    st.markdown("#")
    if st.button("Clear cache"):
        caching.clear_cache()
