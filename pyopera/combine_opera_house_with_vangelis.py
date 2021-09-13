import json
from collections import defaultdict
from itertools import product
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

from icecream import ic
from more_itertools import flatten

from common import Performance, export_as_json, normalize_title
from pyopera.excel_to_json import ExcelRow


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


opera_dbs = load_db_by_date(
    [db_path / filename for filename in ("wso_performances.json",)]
)
vangelis_db = load_db_by_date([db_path / "vangelis_excel_converted.json"])
composers_db = load_title_to_composer_db_and_index_by_normalized_title(
    db_path / "title_to_composers.json"
)


final_list: Sequence[ExcelRow] = []

for date in vangelis_db:
    vangelis_performances = vangelis_db[date]
    wso_performances = opera_dbs[date]

    print(date)

    for vp, wp in product(vangelis_performances, wso_performances):
        if vp["stage"] != wp["stage"]:
            continue

        if not titles_match(vp["name"], wp["name"]):
            continue

        v_composer = vp["composer"]
        norm_title = normalize_title(vp["name"])

        possible_composers = composers_db.get(norm_title, [])

        if wp["composer"] != "":
            continue

        for possible_composer in possible_composers:
            if normalize_title(v_composer) in normalize_title(possible_composer):
                wp["composer"] = possible_composer
                break
        else:
            wp["composer"] = v_composer

        final_list.append(wp)


json_str = export_as_json(final_list)

(db_path / "final_db.json").write_text(json_str)
