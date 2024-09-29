from __future__ import annotations

from enum import Enum
from typing import Generic, Sequence, TypeVar

import boto3
import streamlit as st
from approx_dates.models import ApproxDate
from boto3.resources.factory import ServiceResource
from pydantic import BaseModel

from pyopera.common import Performance, VenueModel, WorkYearEntryModel, soft_isinstance

EntryType = TypeVar("EntryType", bound=BaseModel)


def create_dynamodb_resource() -> ServiceResource:
    """Create a DynamoDB resource using credentials stored in Streamlit secrets."""
    aws_access_key_id = st.secrets["aws"]["aws_access_key_id"]
    aws_secret_access_key = st.secrets["aws"]["aws_secret_access_key"]
    aws_region = st.secrets["aws"]["aws_region"]

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )

    dynamodb = session.resource("dynamodb")
    return dynamodb


def sort_entries_by_date(entries: Sequence[Performance]) -> list[Performance]:
    return sorted(entries, key=lambda x: x.date.earliest_date, reverse=True)


class DatabaseName(str, Enum):
    performances = "performances"
    works_dates = "works_dates"
    venues = "venues"


ModelToEnum = {
    Performance: DatabaseName.performances,
    WorkYearEntryModel: DatabaseName.works_dates,
    VenueModel: DatabaseName.venues,
}

EnumToLoadText = {
    DatabaseName.performances: "Loading data ...",
    DatabaseName.works_dates: "Loading work year data...",
    DatabaseName.venues: "Loading venue data...",
}

EnumToPostProcess = {
    DatabaseName.performances: sort_entries_by_date,
}


DYNAMO_DB_RESOURCE = create_dynamodb_resource()


class DatabaseInterface(Generic[EntryType]):
    """
    Interface to interact with a database.

    This class is a singleton, meaning that only one instance of this class can be created per database name.
    """

    def __init__(
        self,
        entry_type: type[EntryType],
    ) -> None:
        self._entry_type = entry_type
        self._db_name = ModelToEnum[entry_type]
        self._table = DYNAMO_DB_RESOURCE.Table(self._db_name)

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

        with self._table.batch_writer() as batch:
            for item in items_to_put:
                item_dict = item.model_dump()

                # Convert ApproxDate to string
                for key, value in item_dict.items():
                    if isinstance(value, ApproxDate):
                        item_dict[key] = str(value)

                batch.put_item(Item=item_dict)

        fetch_all_cached.clear(self)

    def delete_item_db(self, to_delete: EntryType | str) -> None:
        if soft_isinstance(to_delete, self._entry_type):
            to_delete = to_delete.key

        self._table.delete_item(Key={"key": to_delete})

        fetch_all_cached.clear(self)

    def __hash__(self) -> int:
        return hash(self._db_name.value)


@st.cache_resource(
    show_spinner=False,
    hash_funcs={DatabaseInterface: lambda interface: interface._db_name},
)
def fetch_all_cached(interface: DatabaseInterface[EntryType]) -> list[EntryType]:
    table_name_to_print = interface._db_name.value.replace("_", " ").title()
    text_for_spinner = EnumToLoadText.get(
        interface._db_name, f"Loading table {table_name_to_print} ..."
    )

    with st.spinner(text_for_spinner):
        raw_data = interface._fetch_db()

        post_process = EnumToPostProcess.get(interface._db_name)
        if post_process is not None:
            raw_data = post_process(raw_data)

    return raw_data
