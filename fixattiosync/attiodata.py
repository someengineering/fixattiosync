import sys
import os
import requests
from uuid import UUID
from typing import Union, Any, Optional
from argparse import ArgumentParser
from .logger import log
from .attioresources import AttioWorkspace, AttioPerson, AttioUser


class AttioData:
    def __init__(self, api_key: str, default_limit: int = 500):
        self.api_key = api_key
        self.base_url = "https://api.attio.com/v2/"
        self.default_limit = default_limit
        self.hydrated = False
        self.__workspaces: dict[UUID, AttioWorkspace] = {}
        self.__people: dict[UUID, AttioPerson] = {}
        self.__users: dict[UUID, AttioUser] = {}

    def _headers(self, json: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if json:
            headers["Content-Type"] = "application/json"

        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
        timeout: int = 10,
    ) -> dict[str, Any]:
        url = self.base_url + endpoint
        headers = self._headers(json=bool(json))

        action_strings = {
            "DELETE": "Deleting data from",
            "POST": "Posting data to",
            "PUT": "Putting data to",
            "GET": "Fetching data from",
        }
        action_str = action_strings.get(method.upper(), f"Requesting data via {method} from")

        log.debug(f"{action_str} {url}")
        response = requests.request(method, url, headers=headers, json=json, params=params, timeout=timeout)

        if response.status_code == 200:
            return response.json()  # type: ignore
        else:
            raise Exception(f"Error {action_str.lower()} {url}: {response.status_code} {response.text}")

    def _delete_data(
        self,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return self._request("DELETE", endpoint, json=json, params=params)

    def _post_data(
        self,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return self._request("POST", endpoint, json=json, params=params)

    def _put_data(
        self,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return self._request("PUT", endpoint, json=json, params=params)

    def delete_record(self, object_id: str, record_id: UUID) -> dict[str, Any]:
        endpoint = f"objects/{object_id}/records/{record_id}"
        match object_id:
            case "users":
                self_store = self.__users
            case "people":
                self_store = self.__people  # type: ignore
            case "workspaces":
                self_store = self.__workspaces  # type: ignore
            case _:
                raise ValueError(f"Unknown object_id: {object_id}")

        response = self._delete_data(endpoint)
        if record_id in self_store:
            log.debug(f"Deleted {object_id} {record_id} in Attio, updating locally")
            attio_obj = self_store[record_id]
            if object_id == "users":
                assert isinstance(attio_obj, AttioUser)
                if attio_obj.person is not None:
                    assert isinstance(attio_obj.person, AttioPerson)
                    attio_obj.person.users.remove(attio_obj)
                for workspace in attio_obj.workspaces:
                    workspace.users.remove(attio_obj)
            del self_store[record_id]
        else:
            log.error(f"Deleted {object_id} {record_id} in Attio, not found locally")
        return response

    def assert_record(
        self, object_id: str, matching_attribute: str, data: dict[str, Any]
    ) -> Union[AttioPerson, AttioUser, AttioWorkspace]:
        endpoint = f"objects/{object_id}/records"
        params = {"matching_attribute": matching_attribute}
        attio_cls: Union[type[AttioPerson], type[AttioUser], type[AttioWorkspace]]
        match object_id:
            case "users":
                attio_cls = AttioUser
                self_store = self.__users
            case "people":
                attio_cls = AttioPerson
                self_store = self.__people  # type: ignore
            case "workspaces":
                attio_cls = AttioWorkspace
                self_store = self.__workspaces  # type: ignore
            case _:
                raise ValueError(f"Unknown object_id: {object_id}")

        response = self._put_data(endpoint, params=params, json=data)

        if response.get("data", []):
            attio_obj = attio_cls.make(response["data"])
            log.debug(f"Asserted {object_id} {attio_obj} in Attio, updating locally")
            self_store[attio_obj.record_id] = attio_obj  # type: ignore
            return attio_obj
        else:
            raise RuntimeError(f"Error asserting {object_id} in Attio: {response}")

    def _records(self, object_id: str) -> list[dict[str, Any]]:
        log.debug(f"Fetching {object_id}")
        endpoint = f"objects/{object_id}/records/query"
        all_data = []
        offset = 0

        while True:
            params = {"limit": self.default_limit, "offset": offset}
            response_data = self._post_data(endpoint, params)
            data = response_data.get("data", [])
            all_data.extend(data)

            if len(data) < self.default_limit:
                break

            offset += self.default_limit
        log.debug(f"Found {len(all_data)} {object_id} in Attio")
        return all_data

    @property
    def workspaces(self) -> list[AttioWorkspace]:
        if not self.hydrated:
            self.hydrate()
        return list(self.__workspaces.values())

    @property
    def people(self) -> list[AttioPerson]:
        if not self.hydrated:
            self.hydrate()
        return list(self.__people.values())

    @property
    def users(self) -> list[AttioUser]:
        if not self.hydrated:
            self.hydrate()
        return list(self.__users.values())

    def hydrate(self) -> None:
        log.debug("Hydrating Attio data")
        self.__workspaces = self.__marshal(self._records("workspaces"), AttioWorkspace)  # type: ignore
        self.__people = self.__marshal(self._records("people"), AttioPerson)  # type: ignore
        self.__users = self.__marshal(self._records("users"), AttioUser)  # type: ignore
        self.__connect()
        if len(self.__workspaces) == 0 or len(self.__people) == 0 or len(self.__users) == 0:
            log.fatal("No data found in Attio")
            sys.exit(3)
        self.hydrated = True

    def __connect(self) -> None:
        for user in self.__users.values():
            if user.person_id in self.__people:
                person = self.__people[user.person_id]
                person.users.append(user)
                user.person = person
            if user.workspace_refs is not None and len(user.workspace_refs) > 0:
                for workspace_ref in user.workspace_refs:
                    if workspace_ref in self.__workspaces:
                        workspace = self.__workspaces[workspace_ref]
                        workspace.users.append(user)
                        user.workspaces.append(workspace)

    def __marshal(
        self, data: list[dict[str, Any]], cls: Union[type[AttioWorkspace], type[AttioPerson], type[AttioUser]]
    ) -> dict[UUID, Union[AttioWorkspace, AttioPerson, AttioUser]]:
        ret = {}
        for item in data:
            obj = cls.make(item)
            ret[obj.record_id] = obj
        return ret


def add_args(arg_parser: ArgumentParser) -> None:
    arg_parser.add_argument(
        "--api-key", dest="attio_api_key", help="Attio API Key", default=os.environ.get("ATTIO_API_KEY", None)
    )
