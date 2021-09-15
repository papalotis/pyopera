import streamlit as st
from streamlit import caching

NAME = "Vangelis Opera Archiv"
st.set_page_config(page_title=NAME, page_icon=":violin:")

if True:
    from add_seen_performance import run as run_add_performance
    from visualize_json import run as run_vis_json


with st.sidebar:
    st.title(NAME)
    modes = ["Explore visits", "Add new performance"]
    mode = st.radio("Mode", modes)

if modes.index(mode) == 0:
    run_vis_json()
else:
    run_add_performance()

with st.sidebar:
    st.markdown("#")
    if st.button("Clear cache"):
        caching.clear_cache()
        st.experimental_rerun()
