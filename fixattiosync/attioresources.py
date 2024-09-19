from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional, Self, Type, ClassVar, Any
from .logger import log


def get_latest_value(value: list[dict[str, Any]]) -> dict[str, Any]:
    if value and len(value) > 0:
        return value[0]
    return {}


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

    id: Optional[UUID]
    name: Optional[str]
    tier: Optional[str]
    status: Optional[str]
    fix_workspace_id: Optional[UUID]
    users: list[AttioUser] = field(default_factory=list)

    def __eq__(self: Self, other: Any) -> bool:
        if not hasattr(other, "id") or not hasattr(other, "tier"):
            return False
        return bool(self.id == other.id and self.tier == other.tier)

    @classmethod
    def make(cls: Type[Self], data: dict[str, Any]) -> Self:
        object_id = UUID(data["id"]["object_id"])
        record_id = UUID(data["id"]["record_id"])
        workspace_id = UUID(data["id"]["workspace_id"])
        created_at = datetime.fromisoformat(data["created_at"].rstrip("Z"))

        values = data.get("values", {})

        name_info = get_latest_value(values.get("name", [{}]))
        name = name_info.get("value")

        product_tier_info = get_latest_value(values.get("product_tier", [{}]))
        product_tier = product_tier_info.get("option", {}).get("title")

        status_info = get_latest_value(values.get("status", [{}]))
        status = status_info.get("status", {}).get("title")

        fix_workspace_id_info = get_latest_value(values.get("workspace_id", [{}]))
        fix_workspace_id = optional_uuid(str(fix_workspace_id_info.get("value")))
        if fix_workspace_id is None:
            log.error(f"Fix workspace ID not found for {record_id}: {data}")

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
        }

        return cls(**cls_data)


@dataclass
class AttioPerson(AttioResource):
    matching_attribute: ClassVar[str] = "email_addresses"

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

        name_info = get_latest_value(values.get("name", [{}]))
        full_name = name_info.get("full_name")
        first_name = name_info.get("first_name")
        last_name = name_info.get("last_name")

        email_info = get_latest_value(values.get("email_addresses", [{}]))
        email_address = email_info.get("email_address")

        job_title_info = get_latest_value(values.get("job_title", [{}]))
        job_title = job_title_info.get("value")

        linkedin_info = get_latest_value(values.get("linkedin", [{}]))
        linkedin = linkedin_info.get("value")

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

        return cls(**cls_data)  # type: ignore


@dataclass
class AttioUser(AttioResource):
    matching_attribute: ClassVar[str] = "user_id"

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

    def __eq__(self: Self, other: Any) -> bool:
        if not hasattr(other, "id") or not hasattr(other, "email"):
            return False
        return bool(self.id == other.id and str(self.email).lower() == str(other.email).lower())

    @classmethod
    def make(cls: Type[Self], data: dict[str, Any]) -> Self:
        object_id = UUID(data["id"]["object_id"])
        record_id = UUID(data["id"]["record_id"])
        workspace_id = UUID(data["id"]["workspace_id"])
        created_at = datetime.fromisoformat(data["created_at"].rstrip("Z"))

        values = data.get("values", {})

        email_info = get_latest_value(values.get("primary_email_address", [{}]))
        primary_email_address = email_info.get("email_address")

        status_info = get_latest_value(values.get("status", [{}]))
        status = status_info.get("status", {}).get("title")

        user_id_info = get_latest_value(values.get("user_id", [{}]))
        user_id = optional_uuid(user_id_info["value"])
        if user_id is None:
            log.error(f"Fix user ID not found for {record_id}: {data}")

        person_info = get_latest_value(values.get("person", [{}]))
        person_id = optional_uuid(str(person_info.get("target_record_id")))

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
            "registered_at": None,
            "status": status,
            "user_id": user_id,
            "person_id": person_id,
            "workspace_refs": workspace_refs,
        }

        return cls(**cls_data)

    def create_or_update(self) -> tuple[str, dict[str, Any]]:
        data = {
            "values": {
                "primary_email_address": [{"email_address": self.email}],
                "user_id": [{"value": str(self.id)}],
            }
        }
        return f"objects/users/records?matching_attribute={self.id}", data
