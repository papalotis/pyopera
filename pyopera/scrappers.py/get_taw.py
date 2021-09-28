import asyncio as aio
import re
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import DefaultDict, MutableSequence, Optional, Union

import requests
from aioitertools.asyncio import gather as limit_gather
from bs4 import BeautifulSoup
from icecream import ic
from joblib import Memory
from tqdm import tqdm

from common import (
    GERMAN_MONTH_TO_INT,
    Performance,
    create_key_for_visited_performance_v2,
    load_deta_project_key,
    normalize_title,
)

memory = Memory(Path(__file__).parent.parent / "cachedir")

base_url = "https://www.theater-wien.at"


@memory.cache
def get_main_archive_page() -> requests.Response:
    return requests.get(f"{base_url}/de/programm/archiv")


@memory.cache
def get_production_page(link: str) -> requests.Response:
    return requests.get(link)


main_soup = BeautifulSoup(get_main_archive_page().text, "lxml")


@memory.cache
def get_production_link_from_title_and_date(
    search_title: str, search_date: Union[datetime]
) -> Optional[str]:

    if isinstance(search_date, str):
        search_date = datetime.fromisoformat(search_date)

    normalized_search_title = normalize_title(search_title)

    soup = main_soup

    all_elements = soup.find_all("li", class_="eventkachellist-item cfix")
    # print(len(all_elements))
    for element in all_elements:
        try:
            name_tag, start_date_tag, end_date_tag = element.find_all("meta")
        except ValueError:
            continue

        subtitle_tag = element.find("p", class_="smallsubtitle")
        if subtitle_tag is None:
            subtitle = ""
        else:
            subtitle = subtitle_tag.text

        element_title = name_tag["content"].split(" | ")[0] + ", " + subtitle

        normalized_element_title = normalize_title(element_title)

        start_date = datetime.fromisoformat(start_date_tag["content"])
        end_date = datetime.fromisoformat(end_date_tag["content"])

        if search_title.lower() in element_title.lower() and (
            start_date == end_date == search_date
        ):
            pass
            # ic(search_title, element_title, search_date, start_date, end_date)
        else:

            if normalized_element_title != normalized_search_title:
                continue

            if not start_date <= search_date <= end_date:
                continue

        return base_url + element.find("a")["href"]


leading_team_roles = {
    "Inszenierung",
    "Co-Regie",
    "Ausstattung",
    "Musikalische Leitung",
    "Choreographie",
    "Licht",
    "Kostüme",
    "Bühne",
    "Dramaturgie",
    "Choreografie",
    "Video",
}


async def extract_info_from_production_page(
    production_link: Optional[str], date: Union[datetime, str]
) -> Optional[dict]:

    if production_link is None:
        return None

    if isinstance(date, str):
        date = datetime.fromisoformat(date)

    loop = aio.get_event_loop()
    response = await loop.run_in_executor(None, get_production_page, production_link)

    soup = BeautifulSoup(response.text, "lxml")

    leading_team: DefaultDict[str, MutableSequence[str]] = DefaultDict(list)
    cast: DefaultDict[str, MutableSequence[str]] = DefaultDict(list)

    def select_dict(role_or_part: str) -> DefaultDict[str, MutableSequence[str]]:
        if role_or_part in leading_team_roles:
            dict_to_append = leading_team
        else:
            dict_to_append = cast

        return dict_to_append

    for el in soup.find_all("tr"):
        person: str = el.find("h4", class_="castname").text

        roles_or_part_with_date: str = el.find(
            "td", class_="castrole-col castrole"
        ).text

        for role_or_part_with_date in [roles_or_part_with_date]:
            role_or_part_with_date = role_or_part_with_date.strip()
            match = re.match(r"(.*)((\d{2}\.){2})", role_or_part_with_date)
            if match is not None:

                role_or_part, single_date_str, _ = match.groups()
                single_date_day, single_date_month, _ = single_date_str.split(".")
                single_date = datetime(
                    date.year, int(single_date_month), int(single_date_day)
                )

                if single_date == date:
                    dict_to_append = select_dict(role_or_part)
                    # ic(dict_to_append)
                    dict_to_append[role_or_part].clear()
                    dict_to_append[role_or_part].append(person)

            else:

                split_on_parenthesis = re.split(
                    r"(\(\d+)", role_or_part_with_date, maxsplit=1
                )

                # if len(split_on_parenthesis) == 1:
                # ic(role_or_part_with_date)

                # ic(role_or_part_with_date.split("."))
                # exit()

                role_or_part = split_on_parenthesis[0]

                dict_to_append = select_dict(role_or_part)

                if len(split_on_parenthesis) == 3:
                    to_search = split_on_parenthesis[1][1:] + split_on_parenthesis[2]

                    to_search = to_search.replace("Gesangspartie", "")

                    *days, month = re.findall("(\w+|\d+)", to_search)

                    for day in days:

                        try:
                            month = int(month)
                        except ValueError:
                            month = GERMAN_MONTH_TO_INT[month]

                        try:
                            day = int(day)
                        except ValueError:
                            continue

                        date_specific = datetime(date.year, month, day)
                        if date_specific == date:
                            break
                    else:
                        # person was not in specific date
                        continue

                dict_to_append[role_or_part].append(person)

    return dict(cast=dict(cast), leading_team=dict(leading_team))


async def extract_info_from_production_page_safe(
    production_link: Optional[str], date: Union[datetime, str]
) -> Optional[Performance]:
    try:
        return await extract_info_from_production_page(production_link, date)
    except Exception:
        return None


# @memory.cache
def get_db():
    from deta import Deta

    deta = Deta(load_deta_project_key())
    base = deta.Base("performances")

    return base.fetch({"stage": "KOaF"}).items


async def amain() -> None:
    # performances = [
    #     ("Isis", datetime(2020, 2, 22)),
    #     ("Don Giovanni", datetime(2016, 12, 19)),
    #     ("Zazà", datetime(2020, 9, 18)),
    #     ("Saul", datetime(2018, 2, 23)),
    #     ("Irene", datetime(2020, 1, 29)),
    #     ("Xerse", datetime(2015, 10, 18)),
    # ]

    db = get_db()

    performances = [
        (entry["name"], entry["date"])
        for entry in db
        if entry["cast"] == {} and entry["leading_team"] == {}
    ]

    links = [
        get_production_link_from_title_and_date(title, date)
        for title, date in tqdm(performances)
    ]

    ic(links)

    # ic(list(p for p, l in zip(performances, links) if l is None))

    # ic = lambda x: x

    output = await limit_gather(
        *(
            extract_info_from_production_page_safe(link, date)
            for link, (_, date) in zip(links, performances)
        ),
        limit=20,
    )

    # return output

    # del ic
    from deta import Deta

    deta = Deta(load_deta_project_key())
    base = deta.Base("performances")

    for entry, new_info in tqdm(list(zip(db, output))):
        if new_info is None:
            continue

        if new_info["cast"] == {} and new_info["leading_team"] == {}:
            continue

        old_key = entry["key"]
        entry.update(new_info)
        entry["key"] = create_key_for_visited_performance_v2(entry)

        # base.delete(old_key)
        base.put(entry)

    # print(len(output), len(db))


if __name__ == "__main__":
    aio.run(amain())
