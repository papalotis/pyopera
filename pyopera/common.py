import json
from collections import ChainMap
from datetime import date, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Set, Tuple, Union

from approx_dates.models import ApproxDate
from more_itertools import flatten
from pydantic import BaseModel, validator
from pydantic.types import conlist, constr
from unidecode import unidecode

GERMAN_MONTH_TO_INT = {
    "Januar": 1,
    "Jänner": 1,
    "Februar": 2,
    "März": 3,
    "April": 4,
    "Mai": 5,
    "Juni": 6,
    "Juli": 7,
    "August": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Dezember": 12,
}


SHORT_STAGE_NAME_TO_FULL = {
    "WSO": "Wiener Staatsoper",
    "TAW": "Theater an der Wien",
    "DOB": "Deutsche Oper Berlin",
    "VOW": "Volksoper Wien",
    "KOaF": "Kammeroper am Fleischmarkt",
    "KOB": "Komische Oper Berlin",
    "SUL": "Staatsoper unter den Linden",
    "MMAT": "Μέγαρο Μουσικής, Αίθουσα Αλεξάνδρα Τριάντη ",
    "OF": "Oper Frankfurt ",
    "MTL": "Musiktheater Linz",
    "WKH": "Wiener Konzerthaus, Großer Saal ",
    "OG": "Oper Graz",
    "OLY": "Θέατρο Ολύμπια ",
    "HER": "Ωδείο Ηρώδου Αττικού",
    "MQE": "Museumsquartier Halle E",
    "NTM": "Nationaltheater München",
    "ND": "Národní Divadlo",
    "BSK": "Badisches Staatstheater Karlsruhe ",
    "HfM": "Haus für Mozart",
    "OH": "Oper Halle",
    "SND-N": "Slovenské Národné Divadlo, Nová budova ",
    "SNF": "Ίδρυμα Σταύρος Νιάρχος (Λυρική Σκηνή)",
    "WMV": "Wiener Musikverein",
    "OZ": "Oper Zürich",
    "MTL-BB": "Musiktheater Linz, Black Box",
    "PRT": "Prinzregententheater",
    "JAN": "Janáčkovo Divadlo",
    "KAS": "Kasino ",
    "FEL": "Felsenreitschule",
    "HSW": "Hessisches Staatstheater Wiesbaden",
    "SND-I": "Slovenské Národné Divadlo, Historická budova",
    "LTS": "Landestheater Salzburg",
    "AKZ": "Theater Akzent ",
    "BPh": "Berliner Philharmonie",
    "HEB": "Hebbel-Theater",
    "ALT": "Stift Altenburg",
    "StKNB": "Stift Klosterneuburg Kaiserhof",
    "MAN": "Nationaltheater Mannheim",
    "ERK": "Erkel Színház ",
    "BREF": "Festspielhaus Bregenz ",
    "SEM": "Semperdepot ",
    "BERN": "Konzert Theater Bern",
    "CAS": "Casino Baden – Festsaal",
    "TRI": "Trinkhalle Bad Wildbad",
    "BAYF": "Festspielhaus Bayreuth",
    "BOD": "Bockenheimer Depot",
    "PLZ": "Divadlo Josefa Kajetána Tyla Plzni, Velké Divadlo",
    "GFH": "Großes Festspielhaus",
    "WKH-M2": "Konzerthaus, Mozartsaal",
    "HdK": "Universität der Künste, Konzertsaal Hardenbergstraße",
    "ICC": "International Congress Center",
    "NO": "Neuköllner Oper",
    "KHB": "Konzerthaus Berlin",
    "BPh-KM": "Berliner Philharmonie, Kammermusiksaal",
    "SUL-AS": "Staatsoper unter den Linden, Apollo-Saal",
    "OE": "Oper Erfurt",
    "MT": "Metropol-Theater",
    "ROCG": "Royal Opera House Convent Garden",
    "UJ": "Universität Jena",
    "MMNS": "Μέγαρο Μουσικής, Αίθουσα Νίκος Σκαλκώτας",
    "SGT": "Στέγη Γραμμάτων και Τεχνών",
    "GTLF": "Gran Teatro La Fenice",
    "SchT-W": "Schillertheater Werkstatt",
    "EMS": "EMS-Lounge",
    "ThT": "Θέατρο Τέχνης, Πλάκα",
    "SchT": "Schillertheater",
    "RTSZ": "Rokoko-Theater Schwetzingen",
    "MTL-FB": "Musiktheater Linz, FoyerBühne",
    "ULR": "Ulrichskirche",
    "KNB-BH": "Babenberger Halle",
    "MSH(kl)": "Meistersingerhalle, Kleiner Saal",
    "FSHE": "Festspielhaus Erl",
    "HSW-F": "Hessisches Staatstheater, Foyer",
    "SCH": "Theater Schloss Schönbrunn",
    "BRES": "Seebühne Bregenz",
    "BAD": "Theater Baden",
    "STD": "Stahovské Divadlo, Ständetheater",
    "TER": "Stadthalle Ternitz",
    "FRST": "Franckesche Stifungen, Frylinghausen-Saal",
    "GOE": "Goethe-Theater Bad Lauchstädt",
    "REA": "Reaktor",
    "SNF-ES": "Ίδρυμα Σταύρος Νιάρχος (Λυρική Σκηνή) Εναλλακτική Σκηνή",
    "RED": "Divadlo Reduta Brno",
    "MAH": "Mahenovo Divadlo",
    "MOZ": "Mozarteum, Großer Saal",
    "HLH": "Helmut-List-Halle Graz",
    "KUR": "Königliches Kurtheater Bad Wildbad",
    "TLT": "Tiroler Landestheater",
    "VER": "Opera Royal du Chateau de Versailles",
    "ELY": "Théâtre des Champs Elysées",
    "COM": "Opéra Comique",
    "GEN": "Koninklijke Opera van Gent",
    "HDM": "Haus der Musik, Innsbruck",
}


def austria_date_to_datetime(date_str: str) -> datetime:
    """
    Convert "Samstag, 28. August 2021" to datetime(2021, 08, 28)
    """

    day_name, day, month_name, year = date_str.split(" ")
    day_int = int(day.replace(".", ""))
    month_int = GERMAN_MONTH_TO_INT[month_name]
    year_int = int(year)
    return datetime(year_int, month_int, day_int)


def convert_short_stage_name_to_long_if_available(short_state_name: str) -> str:
    return SHORT_STAGE_NAME_TO_FULL.get(short_state_name, short_state_name)


NonEmptyStr = constr(min_length=1)
NonEmptyStrList = conlist(NonEmptyStr, min_items=1)
SHA1Str = constr(regex=r"[0-9a-f]{40}")


class Performance(BaseModel):
    name: NonEmptyStr
    date: ApproxDate
    cast: Mapping[NonEmptyStr, NonEmptyStrList]
    leading_team: Mapping[NonEmptyStr, NonEmptyStrList]
    stage: NonEmptyStr
    production: NonEmptyStr
    composer: NonEmptyStr
    comments: str
    is_concertante: bool
    key: SHA1Str = None

    class Config:
        validate_assignment = True
        anystr_strip_whitespace = True
        arbitrary_types_allowed = True
        json_encoders = {ApproxDate: str}

    @validator("date", pre=True, always=True, allow_reuse=True)
    def parse_date(cls, v, **kwargs):
        # there are three possible formats:
        # full iso format: "2020-01-01T00:00:00" (handled by datetime module)
        # partial iso format: "2020-01" (January 2020) (handled by ApproxDate)
        # short iso to short iso: "2020-01-01 to 2020-01-04" (January 1st to 4th 2020) (handled by manual parsing and ApproxDate)

        # pass on already parsed dates
        if isinstance(v, ApproxDate):
            return v

        try:
            exact_date = datetime.fromisoformat(v).date()
            approx_date = ApproxDate(exact_date, exact_date, source_string=v)
            return approx_date
        except ValueError:
            try:
                approx_date = ApproxDate.from_iso8601(v)
                return approx_date
            except ValueError:
                # two partial dates split by " to "
                # short iso to short iso
                date_strings = v.split(" to ")
                if len(date_strings) != 2:
                    raise ValueError(
                        f'Could not find two iso dates split by "to" in {v}'
                    )
                early_date, late_date = map(date.fromisoformat, date_strings)
                approx_date = ApproxDate(early_date, late_date, source_string=v)
                return approx_date

    @validator("key", pre=True, always=True, allow_reuse=True)
    def create_key(cls, key, values, **kwargs):
        computed_key = create_key_for_visited_performance_v2(values)

        if key is not None and computed_key != key:
            raise ValueError(
                f"Computed key ({computed_key}) and provided key ({key}) are not the same"
            )

        return computed_key


def is_exact_date(date: ApproxDate) -> bool:
    return date.earliest_date == date.latest_date


DB_TYPE = Sequence[Performance]


def export_as_json(performances: Sequence[Performance]) -> str:
    def default(obj: Any) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, ApproxDate):
            return str(obj)

        raise TypeError("Unknown type: ", type(obj))

    to_save = {
        "$schema": "https://raw.githubusercontent.com/papalotis/pyopera/main/schemas/performance_schema.json",
        "data": performances,
    }

    return json.dumps(to_save, default=default)


def normalize_title(title: str) -> str:
    return "".join(
        filter(
            str.isalpha,
            unidecode(title)
            .split("(")[0]
            .split("/")[0]
            .lower()
            .replace(" ", "")
            .strip(),
        )
    )


def load_deta_project_key() -> str:
    try:
        import os

        return os.environ["project_key"]
    except KeyError:
        try:
            deta_project_key: str = json.loads(
                (Path(__file__).parent.parent / "deta_project_data.json").read_text()
            )["Project Key"]
        except (FileNotFoundError, KeyError) as error:
            try:
                import streamlit as st
            except ImportError:
                raise error

            st.error(
                "Cannot find database key. Cannot continue! Please reload the page."
            )
            st.stop()

    return deta_project_key


def create_key_for_visited_performance_v2(performance: dict) -> str:
    if isinstance(performance, Performance):
        performance = performance.dict()

    date = performance["date"]

    if isinstance(date, datetime):
        date = date.isoformat()

    date = str(date)

    string = "".join(
        filter(
            str.isalnum,
            "".join(
                map(
                    normalize_title,
                    (
                        performance["name"],
                        performance["stage"],
                        performance["composer"],
                    ),
                )
            )
            + date,
        )
    )
    return sha1(string.encode()).hexdigest()


def get_all_names_from_performance(performance: Performance) -> Set[str]:
    return_set = set(
        flatten(
            ChainMap(
                performance.leading_team,
                performance.cast,
            ).values()
        )
    )

    if performance.composer != "":
        return_set.add(performance.composer)

    return return_set


def filter_only_full_entries(db: DB_TYPE) -> DB_TYPE:
    db_filtered = [
        performance
        for performance in db
        if (len(performance.cast) + len(performance.leading_team)) > 0
    ]

    return db_filtered


def is_performance_instance(performance: Performance):
    # hacky way to check if the type is Performance since
    # st rerun mechanism does not work with isinstance
    return performance.__class__.__name__ == Performance.__name__


class WorkYearEntryModel(BaseModel):
    composer: NonEmptyStr
    title: NonEmptyStr
    year: int
    key: str = None
