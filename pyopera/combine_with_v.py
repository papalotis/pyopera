import json
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence, Tuple, Union

import pandas as pd
from unidecode import unidecode


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


def is_nan(value: Any) -> bool:
    return value != value


def load_excel_with_normalized_name_stage_and_date_as_key(
    df: pd.DataFrame,
) -> Mapping[Tuple[str, str, datetime], dict]:
    last_row = None

    out_dict: MutableMapping[Tuple[str, str, datetime], dict] = {}

    for (_, row) in df.iterrows():
        date: Union[datetime, str, float] = row["DATUM"]
        name: Union[str, float] = row["OPER"]
        if isinstance(date, (datetime, float)) and isinstance(name, str):

            stage: str = row["BÜHNE"]
            if isinstance(date, float):  # nan when no date available
                date = last_row["DATUM"]
                stage = last_row["BÜHNE"]

            normalized_name = normalize_title(name)

            out_dict[normalized_name, stage, date] = row.to_dict()
        last_row = row

    return out_dict


def load_performance_db_with_normalized_name_stage_and_date_as_key(
    performance_db: list,
) -> Mapping[Tuple[str, str, datetime], dict]:
    out_dict = {}
    for performance in performance_db:
        normalized_name = normalize_title(performance["name"])
        stage = performance["stage"]
        date = datetime.fromisoformat(performance["date"])
        out_dict[normalized_name, stage, date] = performance

    return out_dict


def load_works_db_with_normalized_name_and_composer_as_key(works_db: list) -> dict:
    out_dict = {}
    for work in works_db:
        normalized_name = normalize_title(work["name"])
        out_dict[normalized_name] = work

    return out_dict


def list_diff(li1, li2):
    li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
    return li_dif


def filter_by_excel_file(
    paths_to_performance_dbs: Sequence[Path],
    path_to_excel: Path,
    path_to_works_json: Path,
) -> list:
    all_dbs_combined = chain.from_iterable(
        [
            json.loads(path_to_performance_db.read_text())["data"]
            for path_to_performance_db in paths_to_performance_dbs
        ]
    )
    performance_db_with_normalized_name_stage_and_date_as_key = (
        load_performance_db_with_normalized_name_stage_and_date_as_key(all_dbs_combined)
    )

    works_db = json.loads(path_to_works_json.read_text())["data"]
    works_db_with_normalized_name_and_composer_as_key = (
        load_works_db_with_normalized_name_and_composer_as_key(works_db)
    )

    df = pd.read_excel(path_to_excel)
    excel_as_indicator_dict = load_excel_with_normalized_name_stage_and_date_as_key(df)

    works_seen = []

    for (name, stage, date) in excel_as_indicator_dict:
        try:
            db_performance = performance_db_with_normalized_name_stage_and_date_as_key[
                name, stage, date
            ]
        except KeyError:
            pass
        else:
            works_seen.append(db_performance)

    return works_seen


if __name__ == "__main__":
    filter_by_excel_file(
        [
            Path(
                "/mnt/c/Users/papal/Documents/fun_stuff/pyopera/db/wso_performances.json"
            )
        ],
        Path("/mnt/c/Users/papal/Documents/fun_stuff/pyopera/pyopera/vangelos.xlsx"),
        Path(
            "/mnt/c/Users/papal/Documents/fun_stuff/pyopera/cachedir/app_cache/works_db.json"
        ),
    )
