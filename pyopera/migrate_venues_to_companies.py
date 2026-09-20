"""One-off migration: seed the ``companies`` table from the existing ``venues`` table.

Most opera companies share a short name with the venue they perform in (e.g. ``DOB``
means Deutsche Oper Berlin both as a venue and as a company), so the existing venue
entries are a good starting point for the companies table.

The script is idempotent: entries whose ``short_name`` already exists in the companies
table are skipped, so it is safe to re-run.

Usage::

    python -m pyopera.migrate_venues_to_companies            # dry run
    python -m pyopera.migrate_venues_to_companies --apply    # write changes
"""

import argparse

from pyopera.common import CompanyModel
from pyopera.streamlit_common import (
    COMPANIES_INTERFACE,
    load_db_companies,
    load_db_venues,
)


def migrate(*, apply: bool = False) -> tuple[int, int]:
    """Copy venue entries into the companies table.

    Returns a ``(created, skipped)`` tuple.
    """
    venues = load_db_venues(list_of_entries=True)
    existing_companies = load_db_companies(list_of_entries=True)
    existing_short_names = {company.short_name for company in existing_companies}

    to_create = []
    skipped = 0

    for venue in venues:
        if venue.short_name in existing_short_names:
            skipped += 1
            continue

        to_create.append(CompanyModel(name=venue.name, short_name=venue.short_name))
        existing_short_names.add(venue.short_name)

    if apply and len(to_create) > 0:
        COMPANIES_INTERFACE.put_db(to_create)

    return len(to_create), skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the new company entries. Without this flag it is a dry run.",
    )
    args = parser.parse_args()

    created, skipped = migrate(apply=args.apply)

    verb = "Created" if args.apply else "Would create"
    print(f"{verb} {created} company entries, skipped {skipped} already present.")

    if not args.apply:
        print("Dry run only. Re-run with --apply to write the changes.")


if __name__ == "__main__":
    main()
