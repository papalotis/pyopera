import streamlit as st

from common import convert_short_stage_name_to_long_if_available
from streamlit_common import format_iso_date_to_day_month_year_with_dots, load_db


def run() -> None:
    db = load_db()

    st.markdown("## Overview")
    for entry in db:

        stage = convert_short_stage_name_to_long_if_available(entry.stage)
        date = format_iso_date_to_day_month_year_with_dots(entry.date)
        st.markdown(f"{date} - {stage} - {entry.composer} - {entry.name}")
