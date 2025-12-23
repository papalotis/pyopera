from __future__ import annotations

import json
from contextlib import nullcontext
from datetime import datetime, timezone
from enum import Enum
from typing import Generic, Optional, Sequence, TypeVar

import streamlit as st
from pydantic import BaseModel

from pyopera.common import (
    ApproxDate,
    PasswordModel,
    Performance,
    VenueModel,
    WorkYearEntryModel,
    soft_isinstance,
)
from pyopera.create_table import make_deta_style_table

EntryType = TypeVar("EntryType", bound=BaseModel)


DEFAULT_DATE = datetime.fromtimestamp(0.0, timezone.utc).date()


def get_earliest_date(date: Optional[ApproxDate]) -> datetime:
    if date is None:
        return DEFAULT_DATE

    return date.earliest_date or DEFAULT_DATE


def sort_entries_by_date(entries: Sequence[Performance]) -> list[Performance]:
    return sorted(
        entries,
        key=lambda x: (
            get_earliest_date(x.date),
            x.day_index if x.day_index is not None else 0,
        ),
        reverse=True,
    )


class DatabaseName(str, Enum):
    performances = "performances"
    works_dates = "works_dates"
    venues = "venues"
    passwords = "passwords"


ModelToEnum = {
    Performance: DatabaseName.performances,
    WorkYearEntryModel: DatabaseName.works_dates,
    VenueModel: DatabaseName.venues,
    PasswordModel: DatabaseName.passwords,
}

EnumToLoadText = {
    Performance: "Loading performances ...",
    WorkYearEntryModel: "Loading work year data...",
    VenueModel: "Loading venue data...",
}

EnumToPostProcess = {
    Performance: sort_entries_by_date,
}


class DatabaseInterface(Generic[EntryType]):
    """
    Interface to interact with a database.
    """

    def __init__(
        self,
        entry_type: type[EntryType],
    ) -> None:
        self._entry_type = entry_type
        self._db_name = ModelToEnum[entry_type]
        self._table = make_deta_style_table(self._db_name.value)

    def _fetch_db(self) -> Sequence[EntryType]:
        # The actual fetching of the database
        final_items = []
        kwargs = {}

        while True:
            response = self._table.scan(**kwargs)

            items = response.get("Items", [])
            final_items.extend(items)

            # If there are no more items to fetch, break the loop
            if response.get("LastEvaluatedKey") is None:
                break

            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        return [self._entry_type(**item) for item in final_items]

    def fetch_db(self) -> list[EntryType]:
        return fetch_all_cached(self).copy()

    def put_db(self, items_to_put: EntryType | Sequence[EntryType]) -> None:
        if soft_isinstance(items_to_put, self._entry_type):
            items_to_put = [items_to_put]

        assert isinstance(items_to_put, Sequence)
        with self._table.batch_writer() as batch:
            for item in items_to_put:
                # this converts the pydantic model to a json string (that pydantic knows how to convert back)
                item_json_str = item.model_dump_json()
                # this converts the json string to a dictionary which is what boto3 expects
                item_dict = json.loads(item_json_str)

                batch.put_item(Item=item_dict)

        fetch_all_cached.clear(self)

    def create_instance(self, **kwargs) -> EntryType:
        return self._entry_type(**kwargs)

    def delete_item_db(self, to_delete: EntryType | str) -> None:
        if soft_isinstance(to_delete, self._entry_type):
            to_delete = to_delete.key

        self._table.delete_item(Key={"key": to_delete})

        fetch_all_cached.clear(self)

    def clear_db(self) -> None:
        for item in self.fetch_db():
            self.delete_item_db(item)

        fetch_all_cached.clear(self)

    def __hash__(self) -> int:
        return hash(self._db_name.value)


@st.cache_resource(
    show_spinner=False,
    hash_funcs={DatabaseInterface: lambda interface: interface._db_name},
)
def fetch_all_cached(interface: DatabaseInterface[EntryType]) -> list[EntryType]:
    text_for_spinner = EnumToLoadText.get(interface._entry_type)

    context_manager = nullcontext() if text_for_spinner is None else st.spinner(text_for_spinner)

    with context_manager:
        raw_data = interface._fetch_db()

        post_process = EnumToPostProcess.get(interface._entry_type)
        if post_process is not None:
            raw_data = post_process(raw_data)

    return raw_data
