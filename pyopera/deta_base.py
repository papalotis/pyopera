from typing import Any, Mapping, Optional, Sequence, Tuple, Union

import requests
from pydantic import BaseModel

from common import Performance


class _DatabasePUTModel(BaseModel):
    items: Sequence[Performance]


class DetaBaseInterface:
    def __init__(self, project_key: str) -> None:
        self._project_key = project_key

    def _get_db_base_url(self) -> str:
        project_key_split = self._project_key.split("_")
        assert len(project_key_split) == 2
        project_id = project_key_split[0]
        base_name = "performances"
        base_url = f"https://database.deta.sh/v1/{project_id}/{base_name}"
        return base_url

    def _create_db_request_base_url_and_headers(self) -> Tuple[str, Mapping[str, str]]:
        base_url = self._get_db_base_url()

        headers = {"X-API-Key": self._project_key, "Content-Type": "application/json"}

        return base_url, headers

    def fetch_db(
        self, max_elements: Optional[int] = None
    ) -> Sequence[Mapping[str, Any]]:
        base_url, headers = self._create_db_request_base_url_and_headers()

        final_url = base_url + "/query"

        payload = {}
        if max_elements is not None:
            payload["limit"] = max_elements

        response = requests.post(final_url, json=payload, headers=headers)
        response.raise_for_status()
        raw_data = response.json()["items"]

        return raw_data

    def put_db(self, items_to_put: Union[Performance, Sequence[Performance]]) -> None:
        if isinstance(items_to_put, Performance):
            items_to_put = [items_to_put]

        base_url, headers = self._create_db_request_base_url_and_headers()

        final_url = base_url + "/items"

        final_data = _DatabasePUTModel(items=items_to_put).json()

        response = requests.put(final_url, data=final_data, headers=headers)
        response.raise_for_status()

        response_json = response.json()

        if "failed" in response_json:
            raise ValueError(
                f"The following items could not be PUT in the database:\n{response_json['failed']}"
            )

    def delete_item_db(self, to_delete: Union[Performance, str]) -> None:
        if isinstance(to_delete, Performance):
            assert to_delete.key is not None
            key_to_delete = to_delete.key
        else:
            key_to_delete = to_delete

        base_url, headers = self._create_db_request_base_url_and_headers()

        final_url = base_url + f"/items/{key_to_delete}"

        response = requests.delete(final_url, headers=headers)
        response.raise_for_status()
