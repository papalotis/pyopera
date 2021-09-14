import streamlit as st

from add_seen_performance import run as run_add_performance
from visualize_json import run as run_vis_json

with st.sidebar:
    mode = st.radio("Mode", ["Visualization", "Add new performance"])

if mode == "Visualization":
    run_vis_json()
else:
    run_add_performance()
