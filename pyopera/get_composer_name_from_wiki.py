import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from joblib import Memory
from textdistance import levenshtein
from tqdm import tqdm

from combine_with_v import normalize_title


def wrap_normalize_title(v: Any) -> Any:
    if isinstance(v, str):
        return normalize_title(v)

    return v


parent_path = Path(__file__).parent

cachedir_path = parent_path.parent / "cachedir"
cachedir_path.mkdir(exist_ok=True)
memory = Memory(cachedir_path, verbose=False)


title_translation = {"Boris Godunow": "Boris Godunov"}

hardcoded_searches = {"Manon": "Manon (Massenet)"}

ignore_set = {
    "Glass Pieces",
    "Duo Concertant",
    "A suite of dances",
    "The Concert",
    "Der Barbier für Kinder",
    "Symphony / Symphony in three Movements",
    "Bilder einer Ausstellung / Pictures at an exhibition",
    "Sinfonie Nr. 15",
    "Emeralds",
    "Rubies",
    "Diamonds",
    "LIVE",
    "4",
    "Solistenkonzert",
    "Suite En Blanc",
    "Before Nightfall",
    "OPERNBALL / REDOUTE",
    "Kammermusik der Wiener Philharmoniker",
    "Die Feen (Fassung für Kinder)",
    "In The Night",
    "Stravinsky Violin Concerto",
    "Thema Und Variationen",
    "Das Ensemble stellt sich vor",
    "Anna Karenina (Ballett)",
    "LIED.BÜHNE",
    "Matinee anlässlich des 20. Todestages von KS Eberhard Waechter",
    "The Vertiginous Thrill Of Exactitude",
    "Variationen Über Ein Thema Von Haydn",
    "Bach Suite III",
    "Positionslichter",
    "Einführungsmatinee La clemenza di Tito",
    "Don Quixote",
    "Einführungsmatinee Don Carlo (ital.)",
    "Nurejew Gala 2012",
    "Romeo und Julia",
    "Das Traumfresserchen",
    "Der Nussknacker",
    "Cipollino",
    "Tanzdemonstrationen",
    "Vers un Pays Sage",
    "Windspiele",
    "A Million Kisses To My Skin",
    "Eventide",
    "La Sylphide",
}


@memory.cache
def get_list() -> pd.DataFrame:
    df = pd.read_html("https://de.wikipedia.org/wiki/Liste_von_Opern")[0]
    df["normalized_title_german"] = df["Deutscher Titel"].apply(wrap_normalize_title)
    df["normalized_title_original"] = df["Originaltitel"].apply(wrap_normalize_title)
    return df


df = get_list()


@memory.cache
def get_composer_from_title(title: str) -> Optional[str]:
    nt = normalize_title(title)

    def wrap_hm(value: Any) -> float:
        if isinstance(value, str):
            return levenshtein.normalized_distance(nt, value)

        return 1

    if title in ignore_set or "für Kinder" in title:
        return None
    distances_title_german = df["normalized_title_german"].apply(wrap_hm)
    distances_title_original = df["normalized_title_original"].apply(wrap_hm)

    min_distance = np.minimum(distances_title_german, distances_title_original)
    row = df[min_distance < 0.12]
    if len(row) == 0:
        return None
    elif len(row) > 1:
        if nt == "laboheme":
            index_to_keep = 1
        elif nt == "salome":
            index_to_keep = 1
        elif nt == "otello":
            index_to_keep = 1
        elif nt == "wozzeck":
            index_to_keep = 0
        else:
            print(row)
            print(title, nt)
            assert False
    else:
        index_to_keep = 0

    row = row.iloc[index_to_keep]

    return row["Komponist"]


# print(get_composer_from_title("La Bohème (Puccini)"))
# exit()

path = Path("/mnt/c/Users/papal/Documents/fun_stuff/pyopera/db/wso_performances.json")

obj = json.loads(path.read_text())
db = obj["data"]

for performance in tqdm(db):
    name = performance["name"]

    try:
        composer = get_composer_from_title(name)
    except AssertionError:
        print(performance["date"])
        raise

    if composer is not None:
        performance["composer"] = composer

    if composer is None and (name not in ignore_set and 0):
        print("check this out", performance["date"])
        break

path.with_stem(path.stem + "_with_composers").with_suffix(".json").write_text(
    json.dumps(obj)
)
