import json
from pathlib import Path
from typing import Any, MutableMapping, Optional, Sequence

import numpy as np
import pandas as pd
from icecream import ic
from joblib import Memory
from textdistance import levenshtein
from tqdm import tqdm

from combine_with_v import normalize_title


def wrap_normalize_title(v: Any) -> Any:
    if isinstance(v, str):
        return normalize_title(v)

    return v


parent_path = Path(__file__).parent

cachedir_path = parent_path.parent / "cachedir"
cachedir_path.mkdir(exist_ok=True)
memory = Memory(cachedir_path, verbose=False)


@memory.cache
def get_list() -> pd.DataFrame:
    df = pd.read_html("https://de.wikipedia.org/wiki/Liste_von_Opern")[0]
    df["normalized_title_german"] = df["Deutscher Titel"].apply(wrap_normalize_title)
    df["normalized_title_original"] = df["Originaltitel"].apply(wrap_normalize_title)
    return df


df = get_list()


@memory.cache
def get_composer_from_title(title: str) -> Optional[Sequence[str]]:

    nt = normalize_title(title)

    def wrap_hm(value: Any) -> float:
        if isinstance(value, str):
            return levenshtein.normalized_distance(nt, value)

        return 1

    distances_title_german = df["normalized_title_german"].apply(wrap_hm)
    distances_title_original = df["normalized_title_original"].apply(wrap_hm)

    min_distance = np.minimum(distances_title_german, distances_title_original)
    row = df[min_distance < 0.12]
    if len(row) == 0:
        return []
    else:
        return [r["Komponist"] for _, r in row.iterrows()]


path = Path("/mnt/c/Users/papal/Documents/fun_stuff/pyopera/db/wso_performances.json")

obj = json.loads(path.read_text())
db = obj["data"]

out: MutableMapping[str, Sequence[str]] = {}

for performance in tqdm(db):
    name: str = performance["name"]

    composers = get_composer_from_title(name)

    if composers is not None:
        out[name] = composers


# ic({k: v for k, v in out.items()})

path_to_title_db = parent_path.parent / 'db' / 'title_to_composers.json'

path_to_title_db.write_text(json.dumps(out))

# path.with_stem(path.stem + "_with_composers").with_suffix(".json").write_text(
#     json.dumps(obj)
# )
