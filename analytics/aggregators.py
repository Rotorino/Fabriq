"""Aggregation helpers that reshape event logs for metric calculations."""

from __future__ import annotations

from typing import Any


def events_by_result(events: list[Any]) -> dict[str, list[Any]]:
    """Group event log records by processing result value."""
    grouped: dict[str, list[Any]] = {}
    for event in events:
        grouped.setdefault(event.result, []).append(event)
    return grouped


def queue_lengths_by_stage(raw_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group recorded queue length observations by stage."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in raw_data.get("queue_lengths", []):
        grouped.setdefault(str(row["stage_id"]), []).append(row)
    return grouped


def machine_activity_by_machine(
    raw_data: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Group machine activity observations by machine."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in raw_data.get("machine_activity", []):
        grouped.setdefault(str(row["machine_id"]), []).append(row)
    return grouped
