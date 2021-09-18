import difflib
import json
from datetime import datetime
from pathlib import Path

from deta import Deta
from icecream import ic

from common import load_deta_project_key

deta = Deta(load_deta_project_key())

base = deta.Base("performances")


def load_all() -> list:
    return base.fetch().items


def do_backup() -> None:
    print("Downloading...")
    db = load_all()
    print("Finished downloading")

    directory = Path(__file__).parent.parent / "backups"

    directory.mkdir(parents=True, exist_ok=True)

    latest_backup = max(directory.iterdir(), key=lambda el: el.stat().st_ctime)

    print(f"Backup file {latest_backup.name}")
    existing_db = json.loads(latest_backup.read_text())

    if db != existing_db:
        print("Creating backup...")
        backup_file = directory / f"{datetime.now()}_backup.json"
        backup_file.write_text(json.dumps(db))
    else:
        print("Will NOT create backup")

    print("Done")


if __name__ == "__main__":
    do_backup()
