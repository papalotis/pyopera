import asyncio as aio
from datetime import datetime
from pathlib import Path
from typing import Sequence

import requests
from aioitertools.asyncio import gather as limit_gather
from bs4 import BeautifulSoup
from icecream import ic
from joblib import Memory

from pyopera.common import GERMAN_MONTH_TO_INT, Performance

memory = Memory(Path(__file__).parent.parent / "cachedir")

base_url = "https://www.volksoper.at"


@memory.cache
def vow_get_main_page() -> requests.Response:
    return requests.get(
        f"{base_url}/event/show-archive?timeunit=season&from=1898-09-01"
    )


@memory.cache
def get_performance_page(link: str) -> requests.Response:
    return requests.get(link)


def get_opera_links_from_season_page(response: requests.Response) -> Sequence[str]:
    soup = BeautifulSoup(response.text, "lxml")

    links = [
        el["href"]
        for el in soup.find_all(
            "a",
            class_=[
                "repertoireEvent category-opera",
                "repertoireEvent category-operetta",
            ],
        )
    ]
    return links


async def extract_info_from_link(link: str) -> Performance:
    loop = aio.get_event_loop()
    response = await loop.run_in_executor(None, get_performance_page, link)
    soup = BeautifulSoup(response.text, "lxml")

    date_str = soup.find("span", class_="event-switcher-date").text

    day_str, _, month_name, year_str = date_str.split(",")[-1].split()
    month = GERMAN_MONTH_TO_INT[month_name]

    date = datetime(int(year_str), month, int(day_str))

    return date
    # print()


async def amain() -> None:
    links = ic(get_opera_links_from_season_page(vow_get_main_page(2015)))

    ic(links)

    results = await limit_gather(
        *(extract_info_from_link(link) for link in links), limit=20
    )

    ic(sorted(results))


if __name__ == "__main__":
    aio.run(amain())
