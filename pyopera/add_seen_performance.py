from hashlib import sha1
from typing import NoReturn, Optional

import streamlit as st
from edit_main_db import run as edit_main_db
from edit_works_year_db import run as edit_works_year_db
from streamlit_common import runs_on_streamlit_sharing


def authenticate() -> Optional[NoReturn]:
    if not runs_on_streamlit_sharing():
        # running locally, no need to authenticate
        return

    if "authenticated" not in st.session_state:
        password_widget = st.empty()
        password = password_widget.text_input("Enter password", type="password")
        if (
            sha1(password.encode()).hexdigest()
            != "ac2e1249ad3cbbe5908d15e5b1da6f0a603aaaf4"
        ):
            if password != "":
                st.error("Wrong password")
            st.stop()
        else:
            password_widget.empty()
            st.session_state["authenticated"] = True


def run():
    authenticate()

    func_to_title = {
        edit_main_db: ":material/storage: Main database",
        edit_works_year_db: ":material/edit_calendar: Year of first performance",
    }

    with st.sidebar:
        function = st.radio(
            "Select database :material/database:",
            func_to_title,
            format_func=func_to_title.get,
        )

        st.markdown("---")

    function()
