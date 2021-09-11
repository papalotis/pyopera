import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence, TypeVar

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


T = TypeVar("T")


def find_subsequence_in_sequence(
    sequence: Sequence[T], subsequence: Sequence[T]
) -> Iterable[int]:
    """
    adapted `find_pivot` from https://stackoverflow.com/a/60819519
    """
    n = len(sequence)
    m = len(subsequence)
    stop = n - m + 1
    if n > 0:
        item = subsequence[0]
        i = 0
        try:
            while i < stop:
                i = sequence.index(item, i)
                if sequence[i : i + m] == subsequence:
                    yield i
                i += 1
        except ValueError:
            return


def recombine_function(
    full_search_function: str, split_functions_to_recombine: Sequence[str]
) -> Sequence[str]:
    """
    >>> recombine_function("Musikalische Leitung", ["Bühne", "Licht", "Musikalische", "Leitung", "Kostüme"])

    `['Bühne', 'Licht', 'Musikalische Leitung', 'Kostüme']`
    """
    split_functions_to_recombine = list(split_functions_to_recombine)

    split_search_function = full_search_function.split(" ")
    results = list(
        find_subsequence_in_sequence(
            split_functions_to_recombine, split_search_function
        )
    )

    if len(results) == 0:
        return split_functions_to_recombine
    if len(results) > 1:
        raise ValueError(f"Function found more than once {len(results)}")

    index_to_overwrite = results[0]
    split_functions_to_recombine[index_to_overwrite] = full_search_function

    number_of_remaining = len(split_search_function) - 1
    del split_functions_to_recombine[
        index_to_overwrite + 1 : index_to_overwrite + number_of_remaining + 1
    ]

    return split_functions_to_recombine


def fix_false_function_splits(split_functions: Sequence[str]) -> Sequence[str]:
    for full_search_function in (
        "Musikalische Leitung",
        "Szenische Einstudierung",
    ):
        split_functions = recombine_function(full_search_function, split_functions)

    return split_functions


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
                function_str_split_by_space = function_str.split(" ")

                function_str_split_fixed = fix_false_function_splits(
                    function_str_split_by_space
                )

                for function_maybe in function_str_split_fixed:
                    if not (
                        function_maybe != ""
                        and function_maybe[0].isalpha()
                        and function_maybe[0].isupper()
                        and function_maybe.lower() not in ("nach",)
                    ):
                        continue

                    function = "".join(
                        filter(lambda s: s.isalpha() or s.isspace(), function_maybe)
                    )

                    persons_split: Sequence[str] = x.find("td").text.split(",")
                    persons = [p.strip() for p in persons_split]
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
        for i in trange(980, 1049, desc=f"Processing pages 📑")
        for performance in get_performance_list_from_page(get_wso_page(i))
    )

    fix_known_issues(all_performances)

    return all_performances


from common import export_as_json

if __name__ == "__main__":
    all_performances = get_all()

    filename = "wso_performances"

    if all_performances[0].date > datetime(2013, 1, 1) and all_performances[
        -1
    ].date > datetime(2020, 1, 1):
        filename = filename + "_test"

    json_path = (parent_path.parent / "db" / filename).with_suffix(".json")

    json_path.write_text(export_as_json(all_performances))


"macbeth 14.06.21"
