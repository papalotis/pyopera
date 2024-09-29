import streamlit as st

from pyopera.streamlit_common import (
    VENUES_INTERFACE,
    VenueModel,
    load_db_venues,
)


def upload_to_db(venue: str, venue_name: str):
    try:
        new_entry = VenueModel(short_name=venue, name=venue_name)
        VENUES_INTERFACE.put_db(new_entry)
    except Exception as e:
        st.toast("An error occured during upload", icon=":material/error:")
        return

    st.toast("Updated database", icon=":material/cloud_sync:")


def delete_venue(key: str):
    try:
        VENUES_INTERFACE.delete_item_db(key)
    except Exception as e:
        st.toast("An error occured during deletion", icon=":material/error:")
        return

    st.toast("Deleted entry", icon=":material/delete:")


def run():
    title_element = st.empty()

    venues_db_list = load_db_venues(list_of_entries=True)
    assert isinstance(venues_db_list, list)

    if len(venues_db_list) > 0 and st.toggle("Existing Venue"):
        venue = st.selectbox(
            "Venue Short Name",
            sorted(venues_db_list, key=lambda x: x.short_name),
            key="venueselectbox",
            format_func=lambda x: x.short_name,
        ).short_name
    else:
        venue = st.text_input("Venue Short Name", key="venuetextinput").strip()

    is_new_entry = venue not in {
        venue_model.short_name for venue_model in venues_db_list
    }

    title_verb = "Add" if is_new_entry else "Edit"
    title_element.markdown(f"# {title_verb} Venue")

    venue_name = st.text_input(
        "Venue Full Name",
        value=next(
            (
                venue_model.name
                for venue_model in venues_db_list
                if venue_model.short_name == venue
            ),
            "",
        ),
    )

    button_text = "Add Venue" if is_new_entry else "Update Venue"
    st.button(
        button_text,
        on_click=upload_to_db,
        kwargs=dict(venue=venue, venue_name=venue_name),
    )

    if not is_new_entry:
        st.divider()

        entry = next(
            (
                venue_model
                for venue_model in venues_db_list
                if venue_model.short_name == venue
            ),
            None,
        )

        assert entry is not None

        st.write(entry)

        st.button("Delete Venue", on_click=delete_venue, kwargs=dict(key=entry.key))
