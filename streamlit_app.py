import streamlit as st

from pyopera.accumulate_pages import main

st.set_page_config(
    page_title="Vangelis OperArchive",
    page_icon=":violin:",
    menu_items={"About": "An interface for Vangelis' Opera Archive"},
)


if __name__ == "__main__":
    main()
else:
    raise ValueError("This script should be run directly")
