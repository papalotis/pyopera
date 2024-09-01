from typing import Any, Generic, Mapping, Optional, Sequence, Tuple, Type, Union, TypeVar

import requests
from approx_dates.models import ApproxDate
from common import Performance
from pydantic import BaseModel


EntryType = TypeVar("EntryType", bound=BaseModel)



class DetaBaseInterface(Generic[EntryType]):
    def __init__(self, project_key: str, db_name: str = "performances", entry_type: Type[EntryType]=Performance) -> None:
        self._project_key = project_key
        self._db_name = db_name
        self._entry_type = entry_type

    def _get_db_base_url(self) -> str:
        project_key_split = self._project_key.split("_")
        assert len(project_key_split) == 2
        project_id = project_key_split[0]
        base_name = self._db_name
        base_url = f"https://database.deta.sh/v1/{project_id}/{base_name}"
        return base_url

    def _create_db_request_base_url_and_headers(self) -> Tuple[str, Mapping[str, str]]:
        base_url = self._get_db_base_url()

        headers = {"X-API-Key": self._project_key, "Content-Type": "application/json"}

        return base_url, headers

    def fetch_db(
        self, max_elements: Optional[int] = None
    ) -> Sequence[EntryType]:
        base_url, headers = self._create_db_request_base_url_and_headers()

        final_url = base_url + "/query"

        payload = {}
        if max_elements is not None:
            payload["limit"] = max_elements

        response = requests.post(final_url, json=payload, headers=headers)
        response.raise_for_status()
        raw_data = response.json()["items"]

        return raw_data

    def put_db(self, items_to_put: Union[EntryType, Sequence[EntryType]]) -> None:
        if isinstance(items_to_put, self._entry_type):
            items_to_put = [items_to_put]

        base_url, headers = self._create_db_request_base_url_and_headers()

        final_url = base_url + "/items"

        final_data = convert_list_of_performances_to_json(items_to_put, self._entry_type)

        response = requests.put(final_url, data=final_data, headers=headers)
        response.raise_for_status()

        response_json = response.json()

        if "failed" in response_json:
            raise ValueError(
                f"The following items could not be PUT in the database:\n{response_json['failed']}"
            )

    def delete_item_db(self, to_delete: Union[EntryType, str]) -> None:
        if isinstance(to_delete, self._entry_type):
            assert to_delete.key is not None
            key_to_delete = to_delete.key
        else:
            key_to_delete = to_delete

        base_url, headers = self._create_db_request_base_url_and_headers()

        final_url = base_url + f"/items/{key_to_delete}"

        response = requests.delete(final_url, headers=headers)
        response.raise_for_status()




def convert_list_of_performances_to_json(performances: Sequence[EntryType], entry_class: Type[EntryType]) -> str:

    class _DatabasePUTModel(BaseModel):
        items: Sequence[entry_class]

        class Config:
            json_encoders = {ApproxDate: str}



    return _DatabasePUTModel(items=performances).json()
