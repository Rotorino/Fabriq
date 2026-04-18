"""Aggregation helpers that reshape runtime data for analytics."""

from __future__ import annotations

from typing import Any


def events_by_time(events: list[Any]) -> list[Any]:
    """Return events sorted by timestamp while preserving input order."""
    indexed_events = list(enumerate(events))
    indexed_events.sort(key=lambda item: (float(item[1].timestamp), item[0]))
    return [event for _, event in indexed_events]


def events_by_stage(events: list[Any]) -> dict[str, list[Any]]:
    """Group event log records by stage identifier."""
    grouped: dict[str, list[Any]] = {}
    for event in events_by_time(events):
        stage_id = getattr(event, "stage_id", None)
        if stage_id is None:
            continue
        grouped.setdefault(str(stage_id), []).append(event)
    return grouped


def events_by_machine(events: list[Any]) -> dict[str, list[Any]]:
    """Group event log records by machine identifier."""
    grouped: dict[str, list[Any]] = {}
    for event in events_by_time(events):
        machine_id = getattr(event, "machine_id", None)
        if machine_id is None:
            continue
        grouped.setdefault(str(machine_id), []).append(event)
    return grouped


def events_by_batch(events: list[Any]) -> dict[str, list[Any]]:
    """Group event log records by batch identifier."""
    grouped: dict[str, list[Any]] = {}
    for event in events_by_time(events):
        batch_id = getattr(event, "batch_id", None)
        if batch_id is None:
            continue
        grouped.setdefault(str(batch_id), []).append(event)
    return grouped


def events_by_result(events: list[Any]) -> dict[str, list[Any]]:
    """Group event log records by processing result value."""
    grouped: dict[str, list[Any]] = {}
    for event in events_by_time(events):
        grouped.setdefault(str(event.result), []).append(event)
    return grouped


def queue_lengths_by_stage(raw_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group queue-length observations by stage and sort them by time."""
    return _group_timed_rows(raw_data.get("queue_lengths", []), "stage_id")


def buffer_lengths_by_stage(
    raw_data: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Group buffer-length observations by stage and sort them by time."""
    return _group_timed_rows(raw_data.get("buffer_lengths", []), "stage_id")


def machine_activity_by_machine(
    raw_data: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Group machine-activity observations by machine and sort them by time."""
    return _group_timed_rows(raw_data.get("machine_activity", []), "machine_id")


def _group_timed_rows(
    rows: list[dict[str, Any]],
    key_name: str,
) -> dict[str, list[dict[str, Any]]]:
    """Group time-series rows by one identifier while keeping stable order."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    indexed_rows = list(enumerate(rows))
    indexed_rows.sort(key=lambda item: (float(item[1]["timestamp"]), item[0]))
    for _, row in indexed_rows:
        grouped.setdefault(str(row[key_name]), []).append(row)
    return grouped
