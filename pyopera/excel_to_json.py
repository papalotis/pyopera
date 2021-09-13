import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import pandas as pd


class ExcelRow(TypedDict):
    date: str
    production: str
    composer: str
    name: str
    stage: str
    comments: str


df = pd.read_excel(
    "/mnt/c/Users/papal/Documents/fun_stuff/pyopera/vangelos.xlsx",
    converters={"KOSTEN": str},
)

last_row = None


def convert_row_to_typed_dict(row: pd.Series) -> ExcelRow:

    global last_row

    date: datetime

    _, date, production, composer, name, stage, *_ = row
    if isinstance(date, float):
        _, date, production, _, _, stage, *_ = last_row
    else:
        last_row = row

    entry = ExcelRow(
        date=date.isoformat(),
        production=production,
        composer=composer,
        name=name,
        stage=stage,
        comments="",
    )

    return entry


data = [
    convert_row_to_typed_dict(row)
    for _, row in df.iterrows()
    if isinstance(row["DATUM"], (datetime, float)) and isinstance(row["OPER"], str)
]


(Path(__file__).parent.parent / "db" / "vangelis_excel_converted.json").write_text(
    json.dumps({"$schema": "", "data": data})
)
