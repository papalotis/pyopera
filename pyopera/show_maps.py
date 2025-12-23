from collections import defaultdict
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import reverse_geocoder as rg
import streamlit as st

from pyopera.show_stats_utils import convert_alpha2_to_alpha3
from pyopera.streamlit_common import load_db, load_db_venues


@st.cache_resource(show_spinner=False)
def load_countries_geojson(
    url: str = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
) -> dict:
    """
    Download and cache a GeoJSON of world countries (with ISO codes under properties.ISO3166-1-Alpha-3),
    then copy that into properties.iso_a3 so we can match it easily.
    """
    resp = requests.get(url)
    resp.raise_for_status()
    geojson = resp.json()

    # copy the ugly ISO3166-1-Alpha-3 field into a simpler one
    for feature in geojson["features"]:
        if feature["properties"]["name"] == "France":
            props = feature["properties"]
            # for some reason france has alpha 3 code -99

            props["ISO3166-1-Alpha-3"] = "FRA"

        iso3 = feature["properties"].get("ISO3166-1-Alpha-3")
        feature["properties"]["iso_a3"] = iso3

    return geojson


@st.cache_data
def longitude_latitude_to_country(longitude: Decimal | None, latitude: Decimal | None) -> Optional[str]:
    if longitude is None or latitude is None:
        return None

    coordinates = (float(latitude), float(longitude))
    location = rg.search(coordinates, mode=1)
    if len(location) == 0:
        return None

    if len(location) > 1:
        raise ValueError("Multiple locations found for the given coordinates.")

    location_result = location[0]
    country_code = convert_alpha2_to_alpha3(location_result["cc"])
    return country_code


@st.cache_data
def longitude_latitude_to_location(longitude: Decimal | None, latitude: Decimal | None) -> Optional[str]:
    if longitude is None or latitude is None:
        return None

    coordinates = (float(latitude), float(longitude))
    location = rg.search(coordinates, mode=1)
    if len(location) == 0:
        return None

    if len(location) > 1:
        raise ValueError("Multiple locations found for the given coordinates.")

    location_result = location[0]

    # for germany if admin1 is berlin use that instead of name (names gives the bezirk, which is too specific)
    # for germany if city name is bogenhausen use munich
    # for germany if city name is "Hofen an der Enz" use Bad Wildbad
    # for greece if admin1 is attica, name gives the dimos, convert attica to Athens
    # for czechia if admin1 is prague, name gives the district, convert to prague
    # for france if if name is "Levallois-Perret" convert to "Paris"

    key_for_city_name = {
        "AT": "name",
        "DE": "name",
        "GR": "admin1",
        "GB": "name",
        "IT": "name",
        "CH": "name",
        "SK": "name",
        "FR": "name",
        "CZ": "name",
        "BE": "name",
        "HU": "admin1",
    }.get(location_result["cc"], "name")

    city_name: str | None = None
    if location_result[key_for_city_name] is not None:
        city_name = location_result[key_for_city_name]
        if location_result["cc"] == "DE" and location_result["admin1"] == "Berlin":
            city_name = "Berlin"
        elif location_result["cc"] == "GR" and location_result["admin1"] == "Attica":
            city_name = "Athens"
        elif location_result["cc"] == "CZ" and (
            location_result["admin1"] == "Prague" or location_result["name"] == "Stare Mesto"
        ):
            city_name = "Prague"
        elif location_result["cc"] == "FR" and location_result["name"] == "Levallois-Perret":
            city_name = "Paris"
        elif location_result["cc"] == "DE" and city_name == "Bogenhausen":
            city_name = "Munich"
        elif location_result["cc"] == "DE" and city_name == "Hofen an der Enz":
            city_name = "Bad Wildbad"

    return city_name


def calculate_city_coordinates() -> None:
    performances = load_db()
    stages = load_db_venues(list_of_entries=True)
    if st.session_state.get("city_name_to_coords") is None:
        city_name_to_coords_list: defaultdict[str, list[tuple[Decimal, Decimal]]] = defaultdict(list)
        for performance in performances:
            for stage in stages:
                if stage.short_name == performance.stage and stage.longitude is not None and stage.latitude is not None:
                    city_name = longitude_latitude_to_location(stage.longitude, stage.latitude)
                    if city_name is not None:
                        city_name_to_coords_list[city_name].append((stage.longitude, stage.latitude))

        city_name_to_coords = {key: np.mean(value, axis=0) for key, value in city_name_to_coords_list.items()}
        st.session_state["city_name_to_coords"] = city_name_to_coords


def calculate_country_coordinates() -> None:
    performances = load_db()
    stages = load_db_venues(list_of_entries=True)
    if st.session_state.get("country_name_to_coords") is None:
        country_name_to_coords_list: defaultdict[str, list[tuple[Decimal, Decimal]]] = defaultdict(list)
        for performance in performances:
            for stage in stages:
                if stage.short_name == performance.stage and stage.longitude is not None and stage.latitude is not None:
                    country_code = longitude_latitude_to_country(stage.longitude, stage.latitude)
                    if country_code is not None:
                        country_name_to_coords_list[country_code].append((stage.longitude, stage.latitude))

        country_name_to_coords = {key: np.mean(value, axis=0) for key, value in country_name_to_coords_list.items()}
        st.session_state["country_name_to_coords"] = country_name_to_coords


def run_maps() -> None:
    performances = load_db()
    calculate_city_coordinates()
    calculate_country_coordinates()

    mode = st.selectbox(
        "Map Mode",
        ("Venues", "Cities", "Countries"),
        index=1,
    )

    stages = load_db_venues(list_of_entries=True)

    coords_counter: dict[tuple[Decimal, Decimal], int] = defaultdict(int)

    # Group performances by visit
    visits = defaultdict(list)
    for p in performances:
        if p.visit_index:
            visits[p.visit_index].append(p)
        else:
            # Treat standalone performances as unique visits
            visits[id(p)].append(p)

    for visit_perfs in visits.values():
        # Use the stage of the first performance in the visit
        # (Assuming all performances in a visit are at the same location, or taking the first one as representative)
        performance = visit_perfs[0]
        stage = next((stage for stage in stages if stage.short_name == performance.stage), None)

        if stage is None:
            continue

        if stage.longitude is not None and stage.latitude is not None:
            if mode == "Venues":
                key = (stage.longitude, stage.latitude, stage.name)
            elif mode == "Cities":
                city_name = longitude_latitude_to_location(stage.longitude, stage.latitude)
                key = (*st.session_state["city_name_to_coords"][city_name], city_name)
            elif mode == "Countries":
                country_code = longitude_latitude_to_country(stage.longitude, stage.latitude)
                if country_code is None:
                    continue
                key = (*st.session_state["country_name_to_coords"][country_code], country_code)

            coords_counter[key] += 1

    map_count_to_size = {
        1: 2,
        5: 5,
        10: 7,
        20: 10,
        50: 15,
        100: 20,
        500: 30,
    }

    # Create DataFrame for map visualization
    map_data = pd.DataFrame(
        [
            {
                "lon": float(lon),
                "lat": float(lat),
                "count": count,
                "size": next(
                    (size for min_count, size in map_count_to_size.items() if count <= min_count),
                    40,
                ),
                "name": stage_name_or_city,
                "color": np.log(count),
            }
            for (lon, lat, stage_name_or_city), count in coords_counter.items()
        ]
    )

    if not map_data.empty:
        threshold = map_data["count"].nlargest(20).min()
        map_data["label"] = map_data["name"].where(map_data["count"] >= threshold, "")

        # Convert data to country format if in Countries mode
        if mode == "Countries":
            create_countries_plot(coords_counter)
        else:
            circle_scale = st.slider("Circle Scale", min_value=0.2, max_value=2.0, value=1.0)
            # For Venues and Cities, use the original scatter map
            fig = px.scatter_map(
                map_data,
                lat="lat",
                lon="lon",
                size="size",
                size_max=15 * circle_scale,
                color="color",
                color_continuous_scale=["red", "black"],
                text="label",
                hover_name="name",
                hover_data=["count"],
                zoom=3,
                map_style="carto-positron",
            )

            fig.update_traces(mode="markers+text", textposition="middle center", marker_opacity=0.7, textfont_size=10)
            fig.update_layout(uniformtext_minsize=12, uniformtext_mode="hide")

            fig.update_layout(
                coloraxis_colorbar=dict(title="Visits", ticks="outside"),
                margin=dict(l=0, r=0, t=40, b=0),
            )

            # dont show the legend
            fig.update_layout(showlegend=False)
            # dont show color bar
            fig.update_coloraxes(showscale=False)

            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No location data available for map visualization.")


@st.cache_data
def create_countries_plot(coords_counter):
    country_data = pd.DataFrame(
        [
            {
                "id": country_code,
                "count": count,
                "color": np.log(count),
            }
            for (_, _, country_code), count in coords_counter.items()
            if isinstance(country_code, str)
        ]
    )

    geojson = load_countries_geojson()

    fig = px.choropleth_map(
        country_data,
        geojson=geojson,
        locations="id",  # your ISO-3 codes column
        featureidkey="properties.iso_a3",
        color="color",
        color_continuous_scale=["red", "black"],
        hover_name="id",
        hover_data=["count", "id"],
        zoom=3,
        center={"lat": 48, "lon": 12},
        map_style="carto-positron",
    )

    fig.update_layout(uniformtext_minsize=12, uniformtext_mode="hide")

    fig.update_layout(
        coloraxis_colorbar=dict(title="Visits", ticks="outside"),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    fig.update_layout(showlegend=False)
    fig.update_coloraxes(showscale=False)

    st.plotly_chart(fig, use_container_width=True)
