import json
from copy import deepcopy
from datetime import datetime
from ssl import create_default_context
from typing import TYPE_CHECKING, Optional, Tuple

from deta import Deta

# from pyopera.common import Performance, create_key_for_visited_performance_v2

if TYPE_CHECKING:
    from pyopera.streamlit_common import DB_TYPE
else:
    DB_TYPE = object


try:
    from pyopera.common import load_deta_project_key
except ImportError:
    load_deta_project_key = lambda: None


deta = Deta(load_deta_project_key())
base = deta.Base("performances")
drive = deta.Drive("backups")


def load_all() -> DB_TYPE:
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


from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

try:
    from deta import App

    app: FastAPI = App(FastAPI())

    @app.lib.run(action="backup")
    @app.lib.cron()
    def cron_task(event):
        print(f"running backup")
        did_backup, filename = do_backup()

        return {"did_backup": did_backup, "filename": filename}


except ImportError:
    app = FastAPI()


app.mount("/", StaticFiles(directory="opera", html=True), name="opera")


# from icecream import ic


# def remove_empty_roles_and_parts_inplace(entry: Performance) -> bool:
#     calculate_number_of_roles = lambda entry: len(entry["cast"]) + len(
#         entry["leading_team"]
#     )

#     old_number_of_parts_or_roles = calculate_number_of_roles(entry)

#     column_keys = ("cast", "leading_team")
#     for column_key in column_keys:
#         role_or_part_dict = entry[column_key]
#         for role_or_part in list(role_or_part_dict):
#             if len(role_or_part_dict[role_or_part]) == 0:
#                 del role_or_part_dict[role_or_part]

#     return old_number_of_parts_or_roles != calculate_number_of_roles(entry)


# # @app.lib.run(action="fix")
# # @app.lib.cron()
# def fix_db(event):

#     print(f"running fix")
#     # db = ic([e for e in load_all() if e["name"] == "Theodora"])
#     db = load_all()
#     for entry in db:
#         new_entry = deepcopy(entry)
#         should_update = False
#         should_update |= remove_empty_roles_and_parts_inplace(new_entry)
#         if should_update:
#             new_entry["key"] = create_key_for_visited_performance_v2(new_entry)
#             base.put(new_entry)

#     # if should_update


# fix_db(None)
