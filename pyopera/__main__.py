from pathlib import Path
from typing import Sequence

import typer
from deta import Deta

from pyopera.common import load_deta_project_key

drive = Deta(load_deta_project_key()).Drive("backups")


def file_sort_key(filename: str) -> str:
    """
    backup filename pattern backup_{ISO_FORMATED_DATE}
    backup filename example backup_2021-04-30T04:03:02
    """
    return filename.split("_", maxsplit=1)[1]


def main(local_backup_dir: Path) -> None:
    assert local_backup_dir.is_dir()

    all_filenames: Sequence[str] = drive.list(prefix="backup_")["names"]

    latest_filename = max(all_filenames, key=file_sort_key)

    backup_file = (local_backup_dir / latest_filename).with_suffix(".json")

    if backup_file not in local_backup_dir.iterdir():
        typer.echo(f"Creating backup at {backup_file}")
        data_to_write = drive.get(latest_filename).read().decode()
        backup_file.write_text(data_to_write)
    else:
        typer.echo("No new backup available")


if __name__ == "__main__":
    typer.run(main)
