import json
from datetime import datetime
from http.client import ImproperConnectionState
from pathlib import Path

from typing_extensions import TypedDict

try:
    import pandas as pd
except ImportError:

    class A:
        pass

    pd = A()
    pd.Series = "pandas.Series"
# try :
#     from typing import TypedDict
# except ImportError:


class ExcelRow(TypedDict):
    date: str
    production: str
    composer: str
    name: str
    stage: str
    comments: str


last_row = None


def convert_row_to_typed_dict(row: pd.Series) -> ExcelRow:

    global last_row

    date: datetime

    _, date, production, composer, name, stage, *_ = row
    if isinstance(date, float):
        _, date, production, _, _, stage, *_ = last_row
    else:
        last_row = row

    dates_names.add((date, name))

    entry = ExcelRow(
        date=date.isoformat(),
        production=production,
        composer=composer,
        name=name,
        stage=stage,
        comments="",
    )

    return entry


if __name__ == "__main__":

    df = pd.read_excel(
        "/mnt/c/Users/papal/Documents/fun_stuff/pyopera/vangelos.xlsx",
        converters={"KOSTEN": str},
    )

    dates_names = set()

    data = [
        convert_row_to_typed_dict(row)
        for _, row in df.iterrows()
        if isinstance(row["DATUM"], (datetime, float)) and isinstance(row["OPER"], str)
    ]

    # (Path(__file__).parent.parent / "db" / "vangelis_excel_converted.json").write_text(
    #     json.dumps({"$schema": "", "data": data})
    # )
