import streamlit as st

from pyopera.common import PasswordModel
from pyopera.deta_base import DatabaseInterface
from pyopera.edit_main_db import run as edit_main_db
from pyopera.edit_venues_db import run as edit_venues_db
from pyopera.edit_works_year_db import run as edit_works_year_db
from pyopera.streamlit_common import runs_on_streamlit_sharing

PASS_INTERFACE = DatabaseInterface(PasswordModel)


def authenticate() -> bool:
    if not runs_on_streamlit_sharing():
        # running locally, no need to authenticate
        return True

    passwords = PASS_INTERFACE.fetch_db()
    if len(passwords) == 0:
        raise ValueError("No password found in the database")

    if len(passwords) > 1:
        raise ValueError("More than one password found in the database")

    password_entry = passwords[0]

    if "authenticated" not in st.session_state:
        password_widget = st.empty()
        password = password_widget.text_input("Enter password", type="password")
        if not password_entry.verify_password(password):
            if password != "":
                st.error("Wrong password")
            return False
        else:
            password_widget.empty()
            st.session_state["authenticated"] = True

    return True


def run():
    if not authenticate():
        return

    func_to_title = {
        edit_main_db: ":material/storage: Main database",
        edit_works_year_db: ":material/edit_calendar: Year of first performance",
        edit_venues_db: ":material/home: Venues",
    }

    with st.sidebar:
        function = st.radio(
            "Select database :material/database:",
            func_to_title,
            format_func=func_to_title.get,
        )

        st.markdown("---")

    function()
