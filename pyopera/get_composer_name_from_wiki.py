import json
from pathlib import Path
from typing import Optional

import wikipedia as wi
from bs4 import BeautifulSoup
from icecream import ic
from joblib import Memory
from tqdm import tqdm
from wikipedia.wikipedia import WikipediaPage

parent_path = Path(__file__).parent

cachedir_path = parent_path.parent / "cachedir"
cachedir_path.mkdir(exist_ok=True)
memory = Memory(cachedir_path, verbose=False)

title_translation = {"Boris Godunow": "Boris Godunov"}

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
    "Die Fledermaus",
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
    "Alceste",  # TODO
    "Cipollino",
    "Tanzdemonstrationen",
    "Vers un Pays Sage",
    "Windspiele",
    "A Million Kisses To My Skin",
    "Eventide",
    "La Sylphide",
}


@memory.cache
def get_composer_from_title(title: str) -> Optional[str]:

    if title in ignore_set:
        return None

    try:
        first, second, *_ = wi.search(f"{title.split('(')[0]} (opera)")

        res = first
        if "Manon Lescaut" in first:
            if "Puccini" not in first:
                res = second

    except ValueError:
        # raise
        return None

    try:
        page: WikipediaPage = wi.page(res, auto_suggest=False)
    except wi.exceptions.DisambiguationError:
        return None

    content = page.html()
    soup = BeautifulSoup(content, "lxml")

    try:
        infobox = soup.find_all("td", class_=["infobox-subheader", "reference"])[0]
        return infobox.find_all("a")[-1].text.strip()
    except IndexError:
        # raise
        return None


# print(get_composer_from_title("Manon Lescaut"))
# exit()

path = Path("/mnt/c/Users/papal/Documents/fun_stuff/pyopera/db/wso_performances.json")

obj = json.loads(path.read_text())
db = obj["data"]

for performance in tqdm(db):
    name = performance["name"]
    name = title_translation.get(name, name)

    composer = get_composer_from_title(name)

    if composer is not None:
        performance["composer"] = composer

    if composer is None and (name not in ignore_set and 0):
        print("check this out", performance["date"])
        break

path.with_stem(path.stem + "_with_composers").with_suffix(".json").write_text(
    json.dumps(obj)
)
