from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional
from .attioresources import AttioPerson, AttioWorkspace


@dataclass
class FixUser:
    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    otp_secret: Optional[str]
    is_mfa_active: Optional[bool]
    created_at: datetime
    updated_at: datetime
    workspaces: list[FixWorkspace] = field(default_factory=list)

    def __eq__(self, other):
        return self.id == other.id and self.email.lower() == other.email.lower()

    def attio_data(
        self, person: Optional[AttioPerson] = None, workspaces: Optional[list[AttioWorkspace]] = None
    ) -> dict:
        object_id = "users"
        matching_attribute = "user_id"
        data = {
            "data": {
                "values": {
                    "user_id": str(self.id),
                    "primary_email_address": [{"email_address": self.email}],
                    "status": "Signed up" if self.is_active else "Invited",
                }
            }
        }
        if person:
            data["data"]["values"]["person"] = {
                "target_object": "people",
                "target_record_id": str(person.record_id),
            }
        if workspaces:
            data["data"]["values"]["workspace"] = []
            for workspace in workspaces:
                data["data"]["values"]["workspace"].append(
                    {
                        "target_object": "workspaces",
                        "target_record_id": str(workspace.record_id),
                    }
                )

        return {
            "object_id": object_id,
            "matching_attribute": matching_attribute,
            "data": data,
        }

    def attio_person(self) -> dict:
        object_id = "people"
        matching_attribute = "email_addresses"
        data = {"data": {"values": {"email_addresses": [{"email_address": self.email}]}}}
        return {
            "object_id": object_id,
            "matching_attribute": matching_attribute,
            "data": data,
        }


@dataclass
class FixWorkspace:
    id: UUID
    slug: str
    name: str
    external_id: UUID
    tier: str
    subscription_id: Optional[UUID]
    payment_on_hold_since: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    owner_id: UUID
    highest_current_cycle_tier: Optional[str]
    current_cycle_ends_at: Optional[datetime]
    tier_updated_at: Optional[datetime]
    owner: Optional[FixUser] = None
    users: list[FixUser] = field(default_factory=list)

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name and self.tier == other.tier

    def attio_data(self) -> dict:
        object_id = "workspaces"
        matching_attribute = "workspace_id"
        data = {
            "data": {
                "values": {
                    "workspace_id": str(self.id),
                    "name": self.name,
                    "product_tier": self.tier,
                }
            }
        }
        return {
            "object_id": object_id,
            "matching_attribute": matching_attribute,
            "data": data,
        }
