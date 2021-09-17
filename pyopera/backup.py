import json
from datetime import datetime
from pathlib import Path

from deta import Deta

from common import load_deta_project_key

deta = Deta(load_deta_project_key())
base = deta.Base("performances")


def load_all():
    return base.fetch().items


if __name__ == "__main__":
    db = load_all()

    directory = Path(__file__).parent.parent / "backups"

    directory.mkdir(parents=True, exist_ok=True)

    backup_file = directory / f"{datetime.now()}_backup.json"

    backup_file.write_text(json.dumps(db))
