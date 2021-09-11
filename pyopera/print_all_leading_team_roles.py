import json
from collections import Counter
from pathlib import Path

from more_itertools import flatten

wso_db = json.loads(
    (Path(__file__).parent.parent / "db" / "wso_performances.json").read_text()
)


print(
    Counter(
        flatten(performance["leading_team"].keys() for performance in wso_db["data"])
    )
)
