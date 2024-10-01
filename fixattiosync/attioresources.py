from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, Self, Type, ClassVar, Any
from enum import Enum
from .logger import log


def get_nested_field(values_dict: dict[str, Any], key: str, field_path: list[str], default: Any = None) -> Any:
    items = values_dict.get(key, [{}])
    if items and isinstance(items, list) and len(items) > 0:
        data = items[0]
        for f in field_path:
            if isinstance(data, dict):
                data = data.get(f, default)
            else:
                return default
        return data
    return default


def optional_uuid(value: str) -> Optional[UUID]:
    uuid = None
    try:
        uuid = UUID(value)
    except (ValueError, TypeError):
        pass
    return uuid


@dataclass
class AttioResource(ABC):
    matching_attribute: ClassVar[str] = "record_id"
    api_object: ClassVar[str] = ""

    object_id: UUID
    record_id: UUID
    workspace_id: UUID
    created_at: datetime

    @classmethod
    @abstractmethod
    def make(cls: Type[Self], data: dict[str, Any]) -> Self:
        pass


@dataclass
class AttioWorkspace(AttioResource):
    matching_attribute: ClassVar[str] = "workspace_id"
    api_object: ClassVar[str] = "workspaces"

    id: Optional[UUID]
    name: Optional[str]
    tier: Optional[str]
    status: Optional[str]
    fix_workspace_id: Optional[UUID]
    cloud_account_connected: Optional[bool]
    users: list[AttioUser] = field(default_factory=list)

    def __eq__(self: Self, other: Any) -> bool:
        if (
            not hasattr(other, "id")
            or not hasattr(other, "tier")
            or not hasattr(other, "cloud_account_connected")
            or not hasattr(other, "status")
            or not isinstance(other.status, Enum)
        ):
            return False
        return bool(
            self.id == other.id
            and self.tier == other.tier
            and self.status == other.status.value
            and self.cloud_account_connected == other.cloud_account_connected
        )

    @classmethod
    def make(cls: Type[Self], data: dict[str, Any]) -> Self:
        object_id = UUID(data["id"]["object_id"])
        record_id = UUID(data["id"]["record_id"])
        workspace_id = UUID(data["id"]["workspace_id"])
        created_at = datetime.fromisoformat(data["created_at"].rstrip("Z"))

        values = data.get("values", {})

        name = get_nested_field(values, "name", ["value"])
        product_tier = get_nested_field(values, "product_tier", ["option", "title"])
        status = get_nested_field(values, "status", ["status", "title"])
        fix_workspace_id = optional_uuid(str(get_nested_field(values, "workspace_id", ["value"])))
        if fix_workspace_id is None:
            log.error(f"Fix workspace ID not found for {record_id}: {data}")
        cloud_account_connected = get_nested_field(values, "cloud_account_connected", ["value"])

        cls_data = {
            "id": fix_workspace_id,
            "object_id": object_id,
            "record_id": record_id,
            "workspace_id": workspace_id,
            "created_at": created_at,
            "name": name,
            "tier": product_tier,
            "status": status,
            "fix_workspace_id": fix_workspace_id,
            "cloud_account_connected": cloud_account_connected,
        }

        return cls(**cls_data)


@dataclass
class AttioPerson(AttioResource):
    matching_attribute: ClassVar[str] = "email_addresses"
    api_object: ClassVar[str] = "people"

    full_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    linkedin: Optional[str]
    job_title: Optional[str]
    users: list[AttioUser] = field(default_factory=list)

    @classmethod
    def make(cls: Type[Self], data: dict[str, Any]) -> Self:
        object_id = UUID(data["id"]["object_id"])
        record_id = UUID(data["id"]["record_id"])
        workspace_id = UUID(data["id"]["workspace_id"])
        created_at = datetime.fromisoformat(data["created_at"].rstrip("Z"))

        values = data["values"]

        full_name = get_nested_field(values, "name", ["full_name"])
        first_name = get_nested_field(values, "name", ["first_name"])
        last_name = get_nested_field(values, "name", ["last_name"])
        email_address = get_nested_field(values, "email_addresses", ["email_address"])
        job_title = get_nested_field(values, "job_title", ["value"])
        linkedin = get_nested_field(values, "linkedin", ["value"])

        cls_data = {
            "object_id": object_id,
            "record_id": record_id,
            "workspace_id": workspace_id,
            "created_at": created_at,
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email_address,
            "job_title": job_title,
            "linkedin": linkedin,
        }

        return cls(**cls_data)


@dataclass
class AttioUser(AttioResource):
    matching_attribute: ClassVar[str] = "user_id"
    api_object: ClassVar[str] = "users"

    id: Optional[UUID]
    demo_workspace_viewed: Optional[bool]
    email: Optional[str]
    registered_at: Optional[datetime]
    status: Optional[str]
    user_id: Optional[UUID]
    person_id: Optional[UUID]
    workspace_refs: Optional[list[UUID]] = None
    person: Optional[AttioPerson] = None
    workspaces: list[AttioWorkspace] = field(default_factory=list)
    user_email_notifications_disabled: Optional[bool] = None
    at_least_one_cloud_account_connected: Optional[bool] = None
    is_main_user_in_at_least_one_workspace: Optional[bool] = None
    cloud_account_connected_workspace_name: Optional[str] = None
    workspace_has_subscription: Optional[bool] = None

    def __eq__(self: Self, other: Any) -> bool:
        if (
            not hasattr(other, "id")
            or not hasattr(other, "email")
            or not hasattr(other, "registered_at")
            or not isinstance(self.registered_at, datetime)
            or not isinstance(other.registered_at, datetime)
            or not hasattr(other, "workspaces")
            or not isinstance(other.workspaces, list)
            or not hasattr(other, "user_email_notifications_disabled")
            or not hasattr(other, "at_least_one_cloud_account_connected")
            or not hasattr(other, "is_main_user_in_at_least_one_workspace")
            or not hasattr(other, "cloud_account_connected_workspace_name")
            or not hasattr(other, "workspace_has_subscription")
        ):
            return False
        return bool(
            self.id == other.id
            and str(self.email).lower() == str(other.email).lower()
            and self.registered_at.astimezone(timezone.utc) == other.registered_at.astimezone(timezone.utc)
            and {w.id for w in self.workspaces} == {w.id for w in other.workspaces}
            and self.user_email_notifications_disabled == other.user_email_notifications_disabled
            and self.at_least_one_cloud_account_connected == other.at_least_one_cloud_account_connected
            and self.is_main_user_in_at_least_one_workspace == other.is_main_user_in_at_least_one_workspace
            and self.cloud_account_connected_workspace_name == other.cloud_account_connected_workspace_name
            and self.workspace_has_subscription == other.workspace_has_subscription
        )

    @classmethod
    def make(cls: Type[Self], data: dict[str, Any]) -> Self:
        object_id = UUID(data["id"]["object_id"])
        record_id = UUID(data["id"]["record_id"])
        workspace_id = UUID(data["id"]["workspace_id"])
        created_at = datetime.fromisoformat(data["created_at"])

        values = data.get("values", {})

        registered_at = get_nested_field(values, "registered_at", ["value"])
        if registered_at:
            registered_at = datetime.fromisoformat(registered_at).replace(microsecond=0)

        primary_email_address = get_nested_field(values, "primary_email_address", ["email_address"])
        status = get_nested_field(values, "status", ["status", "title"])
        user_id = optional_uuid(str(get_nested_field(values, "user_id", ["value"])))
        person_id = optional_uuid(str(get_nested_field(values, "person", ["target_record_id"])))
        user_email_notifications_disabled = get_nested_field(values, "user_email_notifications_disabled", ["value"])
        at_least_one_cloud_account_connected = get_nested_field(
            values, "at_least_one_cloud_account_connected", ["value"]
        )
        is_main_user_in_at_least_one_workspace = get_nested_field(
            values, "is_main_user_in_at_least_one_workspace", ["value"]
        )
        cloud_account_connected_workspace_name = get_nested_field(
            values, "cloud_account_connected_workspace_name", ["value"]
        )
        workspace_has_subscription = get_nested_field(values, "workspace_has_subscription", ["value"])

        if user_id is None:
            log.error(f"Fix user ID not found for {record_id}: {data}")

        workspace_refs = None
        workspace_info = values.get("workspace", [])
        for workspace in workspace_info:
            workspace_ref = optional_uuid(str(workspace.get("target_record_id")))
            if workspace_refs is None:
                workspace_refs = []
            workspace_refs.append(workspace_ref)

        cls_data = {
            "object_id": object_id,
            "record_id": record_id,
            "workspace_id": workspace_id,
            "id": user_id,
            "created_at": created_at,
            "demo_workspace_viewed": None,
            "email": primary_email_address,
            "registered_at": registered_at,
            "status": status,
            "user_id": user_id,
            "person_id": person_id,
            "workspace_refs": workspace_refs,
            "user_email_notifications_disabled": user_email_notifications_disabled,
            "at_least_one_cloud_account_connected": at_least_one_cloud_account_connected,
            "is_main_user_in_at_least_one_workspace": is_main_user_in_at_least_one_workspace,
            "cloud_account_connected_workspace_name": cloud_account_connected_workspace_name,
            "workspace_has_subscription": workspace_has_subscription,
        }

        return cls(**cls_data)
