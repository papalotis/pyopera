import random
import string
from collections import ChainMap
from datetime import date, datetime
from typing import List, Mapping, Optional, Sequence

from approx_dates.models import ApproxDate
from more_itertools import flatten
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, validator
from typing_extensions import Annotated
from unidecode import unidecode

SHORT_STAGE_NAME_TO_FULL = {
    "WSO": "Wiener Staatsoper",
    "TAW": "Theater an der Wien",
    "DOB": "Deutsche Oper Berlin",
    "VOW": "Volksoper Wien",
    "KOaF": "Kammeroper am Fleischmarkt",
    "KOB": "Komische Oper Berlin",
    "SUL": "Staatsoper unter den Linden",
    "MMAT": "Μέγαρο Μουσικής, Αίθουσα Αλεξάνδρα Τριάντη",
    "OF": "Oper Frankfurt",
    "MTL": "Musiktheater Linz",
    "WKH": "Wiener Konzerthaus, Großer Saal",
    "OG": "Oper Graz",
    "OLY": "Θέατρο Ολύμπια",
    "HER": "Ωδείο Ηρώδου Αττικού",
    "MQE": "Museumsquartier Halle E",
    "NTM": "Nationaltheater München",
    "ND": "Národní Divadlo",
    "BSK": "Badisches Staatstheater Karlsruhe",
    "HfM": "Haus für Mozart",
    "OH": "Oper Halle",
    "SND-N": "Slovenské Národné Divadlo, Nová budova",
    "SNF": "Ίδρυμα Σταύρος Νιάρχος (Λυρική Σκηνή)",
    "WMV": "Wiener Musikverein",
    "OZ": "Oper Zürich",
    "MTL-BB": "Musiktheater Linz, Black Box",
    "PRT": "Prinzregententheater",
    "JAN": "Janáčkovo Divadlo",
    "KAS": "Kasino",
    "FEL": "Felsenreitschule",
    "HSW": "Hessisches Staatstheater Wiesbaden",
    "SND-I": "Slovenské Národné Divadlo, Historická budova",
    "LTS": "Landestheater Salzburg",
    "AKZ": "Theater Akzent",
    "BPh": "Berliner Philharmonie",
    "HEB": "Hebbel-Theater",
    "ALT": "Stift Altenburg",
    "StKNB": "Stift Klosterneuburg Kaiserhof",
    "MAN": "Nationaltheater Mannheim",
    "ERK": "Erkel Színház",
    "BREF": "Festspielhaus Bregenz",
    "SEM": "Semperdepot",
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

SHORT_STAGE_NAME_TO_FULL = {k: v.strip() for k, v in SHORT_STAGE_NAME_TO_FULL.items()}


def convert_short_stage_name_to_long_if_available(short_state_name: str) -> str:
    return SHORT_STAGE_NAME_TO_FULL.get(short_state_name, short_state_name)


NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
NonEmptyStrList = Annotated[List[NonEmptyStr], Field(min_items=1)]
SHA1Str = Annotated[str, StringConstraints(pattern=r"[0-9a-f]{40}")]


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
    # TODO[pydantic]: The following keys were removed: `json_encoders`.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
        json_encoders={ApproxDate: str},
    )

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
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

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("key", pre=True, always=True, allow_reuse=True)
    def create_key(cls, key, values, **kwargs):
        if key is not None:
            return key

        # create random key
        return create_key_for_visited_performance_v3()


def is_exact_date(date: ApproxDate) -> bool:
    return date.earliest_date == date.latest_date


DB_TYPE = Sequence[Performance]


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


def create_key_for_visited_performance_v3() -> str:
    available_characters = "abcdef" + string.digits

    # create a 40 character long random string (like a sha1 hash)
    return "".join(random.choices(available_characters, k=40))


def get_all_names_from_performance(performance: Performance) -> set[str]:
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


def create_deta_style_key() -> str:
    available_characters = string.ascii_lowercase + string.digits
    # create a 12 character long random
    return "".join(random.choices(available_characters, k=12))


class WorkYearEntryModel(BaseModel):
    composer: NonEmptyStr
    title: NonEmptyStr
    year: int
    key: Optional[str] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("key", pre=True, always=True, allow_reuse=True)
    def create_key(cls, key, values, **kwargs):
        if key is not None:
            return key

        return create_deta_style_key()
