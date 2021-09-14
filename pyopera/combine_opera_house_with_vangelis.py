import asyncio as aio
import json
import time
from collections import defaultdict
from email import header
from functools import partial
from http.client import ImproperConnectionState
from itertools import product
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence
from unittest import result

from deta import Deta
from more_itertools import chunked, flatten

from pyopera.common import (
    create_key_for_visited_performance,
    export_as_json,
    load_deta_project_key,
    normalize_title,
)
from pyopera.excel_to_json import ExcelRow

try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda a, *args, **kwargs: a


# tqdm = lambda a, *args, **kwargs: a


def load_title_to_composer_db_and_index_by_normalized_title(
    path: Path,
) -> Mapping[str, Sequence[str]]:
    db = json.loads(path.read_text())
    out_dict = {}

    for title, composers in db.items():
        out_dict[normalize_title(title)] = composers
        out_dict[title] = composers

    return out_dict


def index_by_date(db_list: Iterable[dict]) -> Mapping[str, Sequence[dict]]:
    return_value: MutableMapping[str, list] = defaultdict(list)

    for performance in db_list:
        return_value[performance["date"]].append(performance)

    return return_value


def load_db_by_date(paths: Sequence[Path]) -> Mapping[str, Sequence[dict]]:
    all_files_loaded = flatten(json.loads(path.read_text())["data"] for path in paths)

    return index_by_date(all_files_loaded)


def titles_match(title_1: str, title_2: str) -> bool:
    norm_title_1 = normalize_title(title_1)
    norm_title_2 = normalize_title(title_2)

    return (norm_title_1 in norm_title_2) or (norm_title_2 in norm_title_1)


db_path = Path(__file__).parent.parent / "db"


deta = Deta(load_deta_project_key())

manual_db = deta.Base("manual_entries")
program_db = deta.Base("p_entries")

composers_db = load_title_to_composer_db_and_index_by_normalized_title(
    db_path / "title_to_composers.json"
)


async def handle_visit(visit_dict: dict) -> Optional[dict]:
    import requests

    headers = {"X-API-Key": load_deta_project_key(), "Content-type": "application/json"}

    project_id = load_deta_project_key().split("_")[0]
    base_name = "p_entries"

    request_callable = partial(
        requests.get,
        f"https://database.deta.sh/v1/{project_id}/{base_name}/items/{visit_dict['key']}",
        headers=headers,
    )

    loop = aio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        request_callable,
    )

    wp = response.json()

    if len(wp.keys()) == 1:
        return None

    if wp["composer"] == "":
        v_composer = visit_dict["composer"]
        norm_title = normalize_title(visit_dict["name"])
        possible_composers = composers_db.get(norm_title, [])
        for possible_composer in possible_composers:
            if normalize_title(v_composer) in normalize_title(possible_composer):
                wp["composer"] = possible_composer
                break
        else:
            wp["composer"] = v_composer

    return wp


async def calculate_final_list():

    final_list: Sequence[ExcelRow] = []
    fr = manual_db.fetch(
        [
            {"stage": "WSO"},
        ],
    )
    all_visits = fr.items

    loop = aio.get_event_loop()

    coros = [handle_visit(performance) for performance in all_visits]
    results = [
        await aio.gather(*part_coros) for part_coros in tqdm(list(chunked(coros, 50)))
    ]

    final_list = list(
        filter(
            lambda el: el is not None,
            flatten(results),
        )
    )

    return final_list


if __name__ == "__main__":

    final_list = aio.run(calculate_final_list())
    ic(len(final_list))

    json_str = export_as_json(final_list)

    (db_path / "final_db.json").write_text(json_str)
