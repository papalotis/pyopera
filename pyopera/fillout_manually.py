from collections import defaultdict
from dataclasses import asdict
from itertools import count
from typing import MutableMapping, MutableSequence

import streamlit as st

from common import Performance

st.title("Performance importer")

performance_date = st.date_input("performance_date")
performance_title = st.text_input("performance title")
performance_stage = st.text_input("performance_stage")
performance_composer = st.text_input("performance_composer")


if "creative_team" not in st.session_state:
    st.session_state.creative_team = {}
if "roles" not in st.session_state:
    st.session_state.roles = defaultdict(list)


if "person" not in st.session_state:
    st.session_state.person = ""

if "role_or_function" not in st.session_state:
    st.session_state.role_or_function = ""

st.write((st.session_state.role_or_function != "" and st.session_state.person != ""))

st.button("add_person")

if st.session_state.role_or_function != "" and st.session_state.person != "" and 1:
    if st.checkbox("is_role"):
        st.session_state.roles[st.session_state.role_or_function].append(
            st.session_state.person
        )
    else:
        st.session_state.creative_team[
            st.session_state.role_or_function
        ] = st.session_state.person

    st.session_state.person = ""
    st.session_state.role_or_function = ""
else:
    st.session_state.person = st.text_input("peron_of_role_or_function")
    st.session_state.role_or_function = st.text_input("role_or_function")


performance = asdict(
    Performance(
        performance_title,
        performance_date,
        dict(st.session_state.roles),
        dict(st.session_state.creative_team),
        performance_stage,
        composer=performance_composer,
    )
)

st.write(performance)
