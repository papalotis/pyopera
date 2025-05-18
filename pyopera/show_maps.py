from collections import defaultdict
from decimal import Decimal
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import reverse_geocoder as rg
import streamlit as st
from unidecode import unidecode

from pyopera.show_stats_utils import convert_alpha2_to_alpha3
from pyopera.streamlit_common import load_db, load_db_venues


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


from collections import defaultdict
from decimal import Decimal
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import reverse_geocoder as rg
import streamlit as st
from unidecode import unidecode

from pyopera.show_stats_utils import convert_alpha2_to_alpha3
from pyopera.streamlit_common import load_db, load_db_venues


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


def get_mode_coords_and_key(stage, mode):
    """Given a stage and the selected mode, return (lon, lat, key) or None."""
    if mode == "Venues":
        return float(stage.longitude), float(stage.latitude), stage.name

    elif mode == "Cities":
        city = longitude_latitude_to_location(stage.longitude, stage.latitude)
        if not city:
            return None
        lon, lat = st.session_state["city_name_to_coords"][city]
        return float(lon), float(lat), city

    else:  # Countries
        country = longitude_latitude_to_country(stage.longitude, stage.latitude)
        if not country:
            return None
        lon, lat = st.session_state["country_name_to_coords"][country]
        return float(lon), float(lat), country


def build_raw_records(performances, stages, mode):
    """Turn each performance into a (year, lon, lat, key) record."""
    records = []
    for perf in performances:
        if not perf.date:
            continue
        year = perf.date.earliest_date.year
        stage = next((s for s in stages if s.short_name == perf.stage), None)
        if not stage or stage.longitude is None or stage.latitude is None:
            continue

        coords_key = get_mode_coords_and_key(stage, mode)
        if not coords_key:
            continue

        lon, lat, key = coords_key
        records.append((year, lon, lat, key))
    return records


def aggregate_yearly(records):
    """
    From raw (year, lon, lat, key) tuples build a mapping:
      key -> {'coords': (lon,lat), 'year_counts': {year: count}}
    """
    agg = {}
    for year, lon, lat, key in records:
        if key not in agg:
            agg[key] = {"coords": (lon, lat), "year_counts": {}}
        agg[key]["year_counts"][year] = agg[key]["year_counts"].get(year, 0) + 1
    return agg


def build_full_cumulative(agg, years_sorted):
    """
    For each key, walk through years_sorted in order, carrying forward
    the cumulative sum even when year_counts.get(year, 0) == 0.
    Returns a list of dicts ready to turn into a DataFrame.
    """
    rows = []
    for key, data in agg.items():
        lon, lat = data["coords"]
        cum = 0
        for year in years_sorted:
            yearly = data["year_counts"].get(year, 0)
            cum += yearly
            rows.append(
                {
                    "year": year,
                    "lon": lon,
                    "lat": lat,
                    "key": key,
                    "yearly_count": yearly,
                    "cum_count": cum,
                }
            )
    return rows


def pick_size(count):
    """Map cumulative count to a marker size."""
    for thresh, size in [(0, 0), (1, 2), (5, 5), (10, 7), (20, 10), (50, 15), (100, 20), (500, 30)]:
        if count <= thresh:
            return size
    return 40


def run_maps():
    performances = load_db()
    stages = load_db_venues(list_of_entries=True)

    # ensure our cached coord‐dicts exist
    calculate_city_coordinates()
    calculate_country_coordinates()

    mode = st.selectbox("Map Mode", ["Venues", "Cities", "Countries"], index=1)

    # 1) build raw per‐performance records
    raw = build_raw_records(performances, stages, mode)
    if not raw:
        st.warning("No location data available for map visualization.")
        return

    # 2) aggregate yearly counts
    agg = aggregate_yearly(raw)

    # 3) determine full year range
    all_years = sorted({year for year, _, _, _ in raw})

    # 4) build a full cumulative table
    full = build_full_cumulative(agg, all_years)
    df = pd.DataFrame(full)

    # compute the maximum cum_count to scale against
    max_cum = df["cum_count"].max()

    # define your desired diameter range in pixels
    desired_max_px = 20
    desired_min_px = 3

    # Plotly’s recommended sizeref for area‐to‐pixel mapping:
    #   sizeref = 2 * max_value / (max_pixel_diameter ** 2)
    sizeref = 2.0 * max_cum / (desired_max_px**2)

    # build the animated mapbox
    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        size="cum_count",  # raw data column
        color="cum_count",
        animation_frame="year",
        category_orders={"year": all_years},
        hover_name="key",
        hover_data={"yearly_count": True, "cum_count": True},
        zoom=3,
        map_style="carto-positron",
        color_continuous_scale=["red", "black"],
        size_max=desired_max_px,  # still set the upper cap
    )

    # override the marker sizing to use our fixed sizeref & a small sizemin
    fig.update_traces(
        marker=dict(
            sizemode="area",  # area ∝ cum_count
            sizeref=sizeref,  # absolute scale factor
            sizemin=desired_min_px,  # minimum pixel diameter
        ),
        selector=dict(mode="markers"),
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title="Cumulative Visits", ticks="outside"),
    )

    if fig.frames:
        last = fig.frames[-1]

        # 1) show the last frame’s data initially
        for orig_trace, new_trace in zip(fig.data, last.data):
            orig_trace.update(**new_trace.to_plotly_json())
        fig.layout.sliders[0].active = len(fig.frames) - 1

        # 2) compute bounding box + 10% padding
        import numpy as np

        all_lats = np.concatenate([np.array(trace.lat) for trace in last.data])
        all_lons = np.concatenate([np.array(trace.lon) for trace in last.data])
        min_lat, max_lat = float(all_lats.min()), float(all_lats.max())
        min_lon, max_lon = float(all_lons.min()), float(all_lons.max())

        lat_pad = (max_lat - min_lat) * 0.10
        lon_pad = (max_lon - min_lon) * 0.10

        # 3) update mapbox bounds to that padded box
        fig.update_mapboxes(
            bounds=dict(
                west=min_lon - lon_pad,
                south=min_lat - lat_pad,
                east=max_lon + lon_pad,
                north=max_lat + lat_pad,
            )
        )

    st.plotly_chart(fig, use_container_width=True)
