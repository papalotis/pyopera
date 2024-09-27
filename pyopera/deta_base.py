from typing import (
    Any,
    Generic,
    Sequence,
    Type,
    TypeVar,
    Union,
)

import boto3
import streamlit as st
from approx_dates.models import ApproxDate
from boto3.resources.factory import ServiceResource
from common import Performance
from pydantic import BaseModel, ConfigDict

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


class DetaBaseInterface(Generic[EntryType]):
    def __init__(
        self,
        db_name: str = "performances",
        entry_type: Type[EntryType] = Performance,
    ) -> None:
        self.dynamo_db_resource = create_dynamodb_resource()
        self.table = self.dynamo_db_resource.Table(db_name)
        self._entry_type = entry_type

    def fetch_db(self) -> Sequence[EntryType]:
        response = self.table.scan()

        items = response.get("Items", [])

        return [self._entry_type(**item) for item in items]

    def put_db(self, items_to_put: Union[EntryType, Sequence[EntryType]]) -> None:
        if isinstance(items_to_put, self._entry_type):
            items_to_put = [items_to_put]

        with self.table.batch_writer() as batch:
            for item in items_to_put:
                item_dict = item.dict()

                # Convert ApproxDate to string
                for key, value in item_dict.items():
                    if isinstance(value, ApproxDate):
                        item_dict[key] = str(value)

                batch.put_item(Item=item_dict)

    def delete_item_db(self, to_delete: Union[EntryType, str]) -> None:
        if isinstance(to_delete, self._entry_type):
            to_delete = to_delete.key

        self.table.delete_item(Key={"key": to_delete})


def convert_list_of_performances_to_json(
    performances: Sequence[EntryType], entry_class: Type[EntryType]
) -> str:
    class _DatabasePUTModel(BaseModel):
        items: Sequence[
            entry_class
        ]  # Reference the input `entry_class` correctly using the ellipsis
        # TODO[pydantic]: The following keys were removed: `json_encoders`.
        # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
        model_config = ConfigDict(json_encoders={ApproxDate: str})

    # Instantiate _DatabasePUTModel with provided data
    return _DatabasePUTModel(items=performances).json()
