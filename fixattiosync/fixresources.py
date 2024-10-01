from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional, Self, Any
from enum import Enum, IntFlag
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
    workspace_roles: dict[str, FixRoles] = field(default_factory=dict)
    user_email_notifications_disabled: Optional[bool] = None
    at_least_one_cloud_account_connected: Optional[bool] = None
    is_main_user_in_at_least_one_workspace: Optional[bool] = None
    cloud_account_connected_workspace_name: Optional[str] = None
    workspace_has_subscription: Optional[bool] = None

    def __eq__(self: Self, other: Any) -> bool:
        if (
            not hasattr(other, "id")
            or not hasattr(other, "email")
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
            and {w.id for w in self.workspaces} == {w.id for w in other.workspaces}
            and self.user_email_notifications_disabled == other.user_email_notifications_disabled
            and self.at_least_one_cloud_account_connected == other.at_least_one_cloud_account_connected
            and self.is_main_user_in_at_least_one_workspace == other.is_main_user_in_at_least_one_workspace
            and self.cloud_account_connected_workspace_name == other.cloud_account_connected_workspace_name
            and self.workspace_has_subscription == other.workspace_has_subscription
        )

    def attio_data(
        self, person: Optional[AttioPerson] = None, workspaces: Optional[list[AttioWorkspace]] = None
    ) -> dict[str, Any]:
        object_id = "users"
        matching_attribute = "user_id"
        data: dict[str, Any] = {
            "data": {
                "values": {
                    "user_id": str(self.id),
                    "primary_email_address": [{"email_address": self.email}],
                    "status": "Signed up" if self.is_active else "Invited",
                    "demo_workspace_viewed": False,
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
        if self.user_email_notifications_disabled is not None:
            data["data"]["values"]["email_notifications_disabled"] = self.user_email_notifications_disabled
        if self.at_least_one_cloud_account_connected is not None:
            data["data"]["values"]["at_least_one_cloud_account_connected"] = self.at_least_one_cloud_account_connected
        if self.is_main_user_in_at_least_one_workspace is not None:
            data["data"]["values"][
                "is_main_user_in_at_least_one_workspace"
            ] = self.is_main_user_in_at_least_one_workspace
        if self.cloud_account_connected_workspace_name is not None:
            data["data"]["values"][
                "cloud_account_connected_workspace_name"
            ] = self.cloud_account_connected_workspace_name
        if self.workspace_has_subscription is not None:
            data["data"]["values"]["workspace_has_subscription"] = self.workspace_has_subscription

        return {
            "object_id": object_id,
            "matching_attribute": matching_attribute,
            "data": data,
        }

    def attio_person(self) -> dict[str, Any]:
        object_id = "people"
        matching_attribute = "email_addresses"
        data: dict[str, Any] = {"data": {"values": {"email_addresses": [{"email_address": self.email}]}}}
        return {
            "object_id": object_id,
            "matching_attribute": matching_attribute,
            "data": data,
        }

    def update_workspace_info(self) -> None:
        best_workspace = None
        for workspace in self.workspaces:
            if self.workspace_roles[workspace.id] & (
                FixRoles.workspace_owner | FixRoles.workspace_admin | FixRoles.workspace_billing_admin
            ):
                if best_workspace is None:
                    best_workspace = workspace
                    continue
                if workspace.cloud_account_connected and not best_workspace.cloud_account_connected:
                    best_workspace = workspace
                    continue
                best_workspace_is_configured = any(
                    cloud_account.is_configured for cloud_account in best_workspace.cloud_accounts
                )
                workspace_is_configured = any(cloud_account.is_configured for cloud_account in workspace.cloud_accounts)
                if workspace_is_configured and not best_workspace_is_configured:
                    best_workspace = workspace
                    continue
                best_workspace_sum_of_last_scan_resources_scanned = sum(
                    cloud_account.last_scan_resources_scanned for cloud_account in best_workspace.cloud_accounts
                )
                workspace_sum_of_last_scan_resources_scanned = sum(
                    cloud_account.last_scan_resources_scanned for cloud_account in workspace.cloud_accounts
                )
                if workspace_sum_of_last_scan_resources_scanned > best_workspace_sum_of_last_scan_resources_scanned:
                    best_workspace = workspace
                    continue

        if best_workspace is not None:
            self.is_main_user_in_at_least_one_workspace = True
            if best_workspace.cloud_account_connected:
                self.at_least_one_cloud_account_connected = True
                self.cloud_account_connected_workspace_name = best_workspace.name
            if best_workspace.subscription_id is not None:
                self.workspace_has_subscription = True
            else:
                self.workspace_has_subscription = False
        else:
            self.is_main_user_in_at_least_one_workspace = False
            self.at_least_one_cloud_account_connected = False
            self.cloud_account_connected_workspace_name = ""
            self.workspace_has_subscription = False


class FixWorkspaceStatus(Enum):
    Created = "Created"
    Configured = "Configured"
    Collected = "Collected"
    Subscribed = "Subscribed"
    Unsubscribed = "Unsubscribed"


class FixRoles(IntFlag):
    workspace_member = 1 << 0
    workspace_admin = 1 << 1
    workspace_owner = 1 << 2
    workspace_billing_admin = 1 << 3


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
    cloud_accounts: list[FixCloudAccount] = field(default_factory=list)
    status: FixWorkspaceStatus = FixWorkspaceStatus.Created
    cloud_account_connected: bool = False
    user_roles: dict[str, FixRoles] = field(default_factory=dict)

    def __eq__(self: Self, other: Any) -> bool:
        if (
            not hasattr(other, "id")
            or not hasattr(other, "name")
            or not hasattr(other, "tier")
            or not hasattr(other, "status")
            or not hasattr(other, "cloud_account_connected")
        ):
            return False
        return bool(
            self.id == other.id
            and self.name == other.name
            and self.tier == other.tier
            and self.status.value == other.status
            and self.cloud_account_connected == other.cloud_account_connected
        )

    def update_status(self) -> None:
        if len(self.cloud_accounts) > 0:
            self.cloud_account_connected = True
        if self.subscription_id is not None:
            self.status = FixWorkspaceStatus.Subscribed
            return
        if any(cloud_account.is_configured for cloud_account in self.cloud_accounts):
            self.status = FixWorkspaceStatus.Configured
        if any(cloud_account.last_scan_resources_scanned > 0 for cloud_account in self.cloud_accounts):
            self.status = FixWorkspaceStatus.Collected

    def attio_data(self) -> dict[str, Any]:
        object_id = "workspaces"
        matching_attribute = "workspace_id"
        data: dict[str, Any] = {
            "data": {
                "values": {
                    "workspace_id": str(self.id),
                    "name": self.name,
                    "product_tier": self.tier,
                    "status": self.status.value,
                    "cloud_account_connected": self.cloud_account_connected,
                }
            }
        }
        return {
            "object_id": object_id,
            "matching_attribute": matching_attribute,
            "data": data,
        }


@dataclass
class FixCloudAccount:
    id: UUID
    tenant_id: UUID
    cloud: str
    account_id: str
    aws_role_name: Optional[str]
    aws_external_id: Optional[UUID]
    is_configured: bool
    enabled: bool
    privileged: bool
    user_account_name: Optional[str]
    api_account_name: Optional[str]
    api_account_alias: Optional[str]
    state: Optional[str]
    error: Optional[str]
    last_scan_duration_seconds: int
    last_scan_started_at: Optional[datetime]
    last_scan_resources_scanned: int
    created_at: datetime
    updated_at: datetime
    state_updated_at: datetime
    version_id: int
    cf_stack_version: Optional[int]
    scan: bool
    failed_scan_count: int
    gcp_service_account_key_id: Optional[UUID]
    last_task_id: Optional[str]
    azure_credential_id: Optional[UUID]
    last_scan_resources_errors: int
    last_degraded_scan_started_at: Optional[datetime]
