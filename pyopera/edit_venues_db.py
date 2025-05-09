from decimal import Decimal

import streamlit as st

from pyopera.streamlit_common import (
    VENUES_INTERFACE,
    VenueModel,
    load_db_venues,
)


def upload_to_db(venue: str, venue_name: str, longitude: float | None, latitude: float | None, key: str):
    try:
        kwargs = dict(short_name=venue, name=venue_name, longitude=longitude, latitude=latitude)
        if key is not None:
            kwargs["key"] = key

        new_entry = VenueModel(**kwargs)

        VENUES_INTERFACE.put_db(new_entry)
    except Exception as e:
        import traceback

        traceback.print_exc()  # Prints the full traceback to stderr
        st.toast("An error occured during upload", icon=":material/error:")
        return

    st.toast("Updated database", icon=":material/cloud_sync:")


def delete_venue(key: str):
    try:
        VENUES_INTERFACE.delete_item_db(key)
    except Exception as e:
        print(e)
        st.toast("An error occured during deletion", icon=":material/error:")
        return

    st.toast("Deleted entry", icon=":material/delete:")


def convert_to_decimal(value: str | None) -> Decimal | None:
    if value is None or len(value) == 0:
        return None

    return Decimal(value)


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

    is_new_entry = venue not in {venue_model.short_name for venue_model in venues_db_list}

    title_verb = "Add" if is_new_entry else "Edit"
    title_element.markdown(f"# {title_verb} Venue")

    venue_entry = next(
        (venue_model for venue_model in venues_db_list if venue_model.short_name == venue),
        None,
    )

    venue_name = st.text_input("Venue Full Name", value=venue_entry.name if venue_entry is not None else None)
    st.write(venue_name)

    col1, col2 = st.columns(2)

    with col1:
        longitude = st.text_input("Longitude", value=venue_entry.longitude_float if venue_entry is not None else None)

    with col2:
        latitude = st.text_input("Latitude", value=venue_entry.latitude_float if venue_entry is not None else None)

    longitude = convert_to_decimal(longitude)
    latitude = convert_to_decimal(latitude)

    button_text = "Add Venue" if is_new_entry else "Update Venue"
    st.button(
        button_text,
        on_click=upload_to_db,
        kwargs=dict(
            venue=venue,
            venue_name=venue_name,
            longitude=longitude,
            latitude=latitude,
            key=venue_entry.key if venue_entry is not None else None,
        ),
    )

    if not is_new_entry:
        st.divider()

        entry = next(
            (venue_model for venue_model in venues_db_list if venue_model.short_name == venue),
            None,
        )

        assert entry is not None

        st.write(entry)

        st.button("Delete Venue", on_click=delete_venue, kwargs=dict(key=entry.key))
