"""Typed Nexus operator adapter for the Nova release lifecycle."""
from __future__ import annotations

from typing import Any

from nova.release_lifecycle import GovernedApprovalStore, NovaReleaseCapability, NovaReleaseController


def _invoke(capability: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    controller = NovaReleaseController(approval_store=GovernedApprovalStore())
    return NovaReleaseCapability(controller).invoke(capability, arguments)


def nova_release_status(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return _invoke("nova.release.status", arguments)


def nova_release_stage(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke("nova.release.stage", arguments)


def nova_release_validate(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke("nova.release.validate", arguments)


def nova_release_activate(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke("nova.release.activate", arguments)


def nova_release_verify(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke("nova.release.verify", arguments)


def nova_release_rollback(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke("nova.release.rollback", arguments)
