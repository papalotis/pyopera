import json
from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Sequence, Tuple

from deta import Deta
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

if TYPE_CHECKING:
    from pyopera.common import DB_TYPE
else:
    DB_TYPE = object


try:
    from pyopera.common import load_deta_project_key
except ImportError:
    load_deta_project_key = lambda: None

try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)


deta = Deta(load_deta_project_key())
base = deta.Base("performances")
drive = deta.Drive("backups")


def load_all() -> DB_TYPE:
    return base.fetch().items


def file_sort_key(filename: str) -> str:
    """
    backup filename pattern backup_{ISO_FORMATED_DATE}
    backup filename example backup_2021-04-30T04:03:02
    """
    return filename.split("_", maxsplit=1)[1]


def get_all_backup_filename_list() -> Sequence[str]:
    return drive.list(prefix="backup_")["names"]


def get_latest_backup_filename() -> Optional[str]:
    backup_files = get_all_backup_filename_list()
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


def do_delete_old_files() -> Sequence[str]:
    """
    Delete old files and return a list of all names of all the deleted files
    """
    number_of_files_to_keep = 200
    all_backup_filenames = sorted(get_all_backup_filename_list(), key=file_sort_key)

    latest_n_files = all_backup_filenames[-number_of_files_to_keep:]

    filenames_to_delete = set(all_backup_filenames) - set(latest_n_files)

    for filename_to_delete in filenames_to_delete:
        drive.delete(filename_to_delete)

    return list(filenames_to_delete), get_all_backup_filename_list()


try:
    from deta import App

    app: FastAPI = App(FastAPI())

    @app.lib.run(action="backup")
    # @app.lib.cron()
    def backup(event):
        print(f"running backup")

        did_backup, current_backup_file = do_backup()

        return {"did_backup": did_backup, "current_backup_file": current_backup_file}

    @app.lib.run(action="delete_old_files")
    def delete_old_files(event):
        print(f"running delete old files")

        deleted_files, backup_filenames = do_delete_old_files()

        return {"deleted_files": deleted_files, "backup_filenames": backup_filenames}

    @app.lib.run(action="test")
    @app.lib.cron()
    def cron(event) -> None:
        return {**backup(event), **delete_old_files(event)}

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
