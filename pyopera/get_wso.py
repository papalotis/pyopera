import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Tuple, Union

import requests
from bs4 import BeautifulSoup
from joblib import Memory
from more_itertools import chunked
from tqdm import tqdm, trange

from common import Performance, austria_date_to_datetime

base_link = "https://archiv.wiener-staatsoper.at"


parent_path = Path(__file__).parent

cachedir_path = parent_path.parent / "cachedir"
cachedir_path.mkdir(exist_ok=True)
memory = Memory(cachedir_path, verbose=False)


@memory.cache
def get_wso_page(page: int) -> requests.Response:
    response = requests.get(base_link + f"/performances/page/{page}")

    return response


@memory.cache
def get_wso_performance_from_link(performance_link: str) -> requests.Response:
    response = requests.get(performance_link)
    return response


def get_wso_performances_from_list_of_links(
    performance_links: Iterable[str],
) -> Iterable[requests.Response]:
    loop = asyncio.get_event_loop()

    responses = []

    for links in tqdm(
        list(chunked(performance_links, 20)),
        desc="downloading performance info",
        leave=False,
    ):
        futures = [
            loop.run_in_executor(None, get_wso_performance_from_link, link)
            for link in links
        ]
        responses_part = loop.run_until_complete(asyncio.gather(*futures))
        responses.extend(responses_part)

    return responses


def get_performance_list_from_page(
    response: requests.Response,
) -> Iterable[Performance]:
    soup = BeautifulSoup(response.text, "html.parser")

    all_performances_soups = soup.findAll("div", {"class": "simple-result-list-item"})

    performances = []

    links = tuple(
        base_link + performance.find("a")["href"]
        for performance in all_performances_soups
    )

    infos_responses = get_wso_performances_from_list_of_links(links)

    all_performances_with_infos = list(zip(all_performances_soups, infos_responses))

    for performance, info_response in tqdm(
        all_performances_with_infos, desc="processing performances", leave=False
    ):
        name = performance.find("h2").text.strip()
        if name == "GESCHLOSSEN / KEINE VORSTELLUNG":
            continue
        date = austria_date_to_datetime(performance.find("p").text.strip())

        performance_soup = BeautifulSoup(info_response.text, "html.parser")

        leading_team_table, cast_table = performance_soup.findAll(
            "table", {"class": "performance-credits-table"}
        )[0].findAll("tbody")

        cast = {}
        for x in cast_table:
            th_ = x.find("th")

            if th_ != -1:
                for role in th_.text.split("/"):
                    persons = x.find("td").text.split(", ")
                    cast[role] = persons

        leading_team = {}
        for x in leading_team_table:
            th_ = x.find("th")

            if th_ != -1:
                function_str: str = th_.text

                for function_maybe in function_str.split(" "):
                    if not (
                        function_maybe != ""
                        and function_maybe[0].isalpha()
                        and function_maybe[0].isupper()
                        and function_maybe.lower() not in ("nach",)
                    ):
                        continue

                    if function_maybe.endswith("in"):
                        function_maybe = function_maybe[:-2]

                    function = "".join(filter(str.isalpha, function_maybe))

                    persons = x.find("td").text.split(",")
                    leading_team[function] = persons

        performances.append(
            Performance(
                name=name,
                date=date,
                cast=cast,
                leading_team=leading_team,
                stage="WSO",
            )
        )

    return performances


def default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, Performance):
        return asdict(obj)
    raise TypeError("Unknown type: ", type(obj))


"""
Drei vorstellungen müssen gesondert hinzugefügt werden: 2.2.20 Rusalka, 30.11.17 Don Pasquale,
 18.9.17 Chowanschtschina (Datum muss korrigiert werden in 17.9.17)
"""


def fix_known_issues(performances: Sequence[Performance]) -> None:

    for performance in performances:
        if (
            performance.date == datetime(2017, 9, 18)
            and performance.name == "Chowanschtschina"
        ):
            performance.date = datetime(2017, 9, 17)


def get_all():
    all_performances = tuple(
        performance
        for i in trange(980, 1046, desc=f"processing pages")
        for performance in get_performance_list_from_page(get_wso_page(i))
    )

    fix_known_issues(all_performances)

    return all_performances


if __name__ == "__main__":
    all_performances = get_all()

    to_save = {
        "$schema": "https://raw.githubusercontent.com/papalotis/pyopera/main/schemas/performance_schema.json",
        "data": all_performances,
    }

    json_path = parent_path / "wso_performances_test.json"
    with open(json_path, "w") as json_file:
        json.dump(to_save, json_file, default=default)
