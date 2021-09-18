import json
from datetime import datetime
from typing import Optional, Tuple

from deta import Deta

try:
    from pyopera.common import load_deta_project_key
except ImportError:
    load_deta_project_key = lambda: None


deta = Deta(load_deta_project_key())
base = deta.Base("performances")
drive = deta.Drive("backups")


def load_all() -> list:
    return base.fetch().items


def file_sort_key(filename: str) -> str:
    return filename.split("_", maxsplit=1)[1]


def get_latest_backup_filename() -> Optional[str]:
    backup_files = drive.list(prefix="backup_")["names"]
    if len(backup_files) == 0:
        return None

    latest_backup = max(backup_files, key=file_sort_key)
    return latest_backup


def do_backup() -> Tuple[bool, str]:
    print("Downloading...")
    db = load_all()
    print("Finished downloading")

    backup_filename = get_latest_backup_filename()

    if backup_filename is not None:
        print(f"Backup file {backup_filename}")
        backup_content = b"".join(drive.get(backup_filename).iter_chunks())
        existing_db = json.loads(backup_content.decode())
    else:
        print("No backup file found")
        existing_db = {}

    will_perform_backup = db != existing_db
    if will_perform_backup:
        print("Creating backup...")
        backup_filename = f"backup_{datetime.utcnow().isoformat()}"
        drive.put(backup_filename, json.dumps(db))
    else:
        print("Will not create backup")

    return will_perform_backup, backup_filename


from deta import app


@app.lib.run(action="backup")
@app.lib.cron()
def cron_task(event):
    print(f"running backup")
    did_backup, filename = do_backup()

    return {"did_backup": did_backup, "filename": filename}
