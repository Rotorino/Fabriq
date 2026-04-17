"""Business metric calculators for simulation results."""

from __future__ import annotations

from typing import Any

from analytics.aggregators import machine_activity_by_machine, queue_lengths_by_stage
from analytics.metrics import average, calculate_utilization


def calculate_analytics(result: Any) -> dict[str, Any]:
    """Calculate general, stage, machine, and batch metrics."""
    batch_metrics = _batch_metrics(result)
    machine_metrics = _machine_metrics(result)
    stage_metrics = _stage_metrics(result, machine_metrics)
    completed = sum(1 for batch in result.batches if _status(batch) == "completed")
    rejected = sum(1 for batch in result.batches if _status(batch) == "rejected")
    output_units = sum(
        int(getattr(batch, "size", 0))
        for batch in result.batches
        if _status(batch) == "completed"
    )
    return {
        "scenario_name": result.scenario_name,
        "general": {
            "total_batches": len(result.batches),
            "completed_batches": completed,
            "rejected_batches": rejected,
            "simulation_time": result.simulation_time,
            "output_units": output_units,
        },
        "stages": stage_metrics,
        "machines": machine_metrics,
        "batches": batch_metrics,
    }


def _batch_metrics(result: Any) -> list[dict[str, Any]]:
    arrivals = {
        event.batch_id: event.timestamp
        for event in result.events
        if getattr(event.event_type, "value", event.event_type) == "BATCH_ARRIVAL"
        and event.batch_id
    }
    finishes: dict[str, float] = {}
    waited_batches: set[str] = set()
    for event in result.event_log:
        if event.result in {"batch_completed", "batch_rejected"} and event.batch_id:
            finishes[event.batch_id] = event.timestamp
        if event.result in {"queued", "buffered"} and event.batch_id:
            waited_batches.add(event.batch_id)

    metrics = []
    for batch in result.batches:
        batch_id = str(batch.batch_id)
        start = arrivals.get(batch_id, getattr(batch, "arrival_time", 0.0))
        finish = finishes.get(batch_id, result.simulation_time)
        metrics.append(
            {
                "batch_id": batch_id,
                "cycle_time": max(finish - start, 0.0),
                "stages_count": len(getattr(batch, "route", [])),
                "completed": _status(batch) == "completed",
                "waited_in_queue": batch_id in waited_batches,
            }
        )
    return metrics


def _stage_metrics(
    result: Any,
    machine_metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    queue_lengths = queue_lengths_by_stage(result.raw_data)
    waits = _stage_wait_times(result.event_log)
    processing_times = _stage_processing_times(result.event_log)
    stage_machine_map = {
        machine.machine_id: getattr(machine, "stage_id", "")
        for machine in result.machines
    }
    machine_utilization = {
        metric["machine_id"]: metric["utilization"]
        for metric in machine_metrics
    }
    metrics = []
    for stage in result.stages:
        stage_id = stage.stage_id
        stage_machines = [
            machine.machine_id
            for machine in getattr(stage, "machines", [])
            if stage_machine_map.get(machine.machine_id) == stage_id
        ]
        utilization_values = [
            machine_utilization[machine_id]
            for machine_id in stage_machines
            if machine_id in machine_utilization
        ]
        max_queue = max(
            [int(row["queue_length"]) for row in queue_lengths.get(stage_id, [])]
            or [0]
        )
        metrics.append(
            {
                "stage_id": stage_id,
                "processed_batches": len(processing_times.get(stage_id, [])),
                "average_wait_time": average(waits.get(stage_id, [])),
                "average_processing_time": average(
                    processing_times.get(stage_id, [])
                ),
                "max_queue_length": max_queue,
                "utilization": average(utilization_values),
                "rejected_batches": _count_events(
                    result.event_log,
                    stage_id,
                    "batch_rejected",
                ),
                "breakdowns": _count_events(
                    result.event_log,
                    stage_id,
                    "machine_broken",
                ),
            }
        )
    return metrics


def _machine_metrics(result: Any) -> list[dict[str, Any]]:
    activity = machine_activity_by_machine(result.raw_data)
    metrics = []
    for machine in result.machines:
        rows = sorted(
            activity.get(machine.machine_id, []),
            key=lambda row: float(row["timestamp"]),
        )
        busy_time = _sum_machine_busy_time(rows, result.simulation_time)
        breakdowns = sum(1 for row in rows if row["event"] == "machine_broken")
        repair_times = _machine_repair_times(rows)
        utilization = calculate_utilization(busy_time, result.simulation_time)
        metrics.append(
            {
                "machine_id": machine.machine_id,
                "busy_time": busy_time,
                "idle_time": max(result.simulation_time - busy_time, 0.0),
                "breakdowns": breakdowns,
                "average_repair_time": average(repair_times),
                "utilization": utilization,
            }
        )
    return metrics


def _sum_machine_busy_time(rows: list[dict[str, Any]], end_time: float) -> float:
    busy_started: float | None = None
    total = 0.0
    for row in rows:
        timestamp = float(row["timestamp"])
        if row["event"] == "processing_started" and busy_started is None:
            busy_started = timestamp
        if row["event"] in {"processing_finished", "machine_broken"}:
            if busy_started is not None:
                total += max(timestamp - busy_started, 0.0)
                busy_started = None
    if busy_started is not None:
        total += max(end_time - busy_started, 0.0)
    return total


def _machine_repair_times(rows: list[dict[str, Any]]) -> list[float]:
    repair_started: float | None = None
    repair_times: list[float] = []
    for row in rows:
        timestamp = float(row["timestamp"])
        if row["event"] == "machine_broken":
            repair_started = timestamp
        if row["event"] == "repair_finished" and repair_started is not None:
            repair_times.append(max(timestamp - repair_started, 0.0))
            repair_started = None
    return repair_times


def _stage_wait_times(events: list[Any]) -> dict[str, list[float]]:
    queued_at: dict[tuple[str, str], float] = {}
    waits: dict[str, list[float]] = {}
    for event in events:
        if event.batch_id is None or event.stage_id is None:
            continue
        key = (event.batch_id, event.stage_id)
        if event.result == "queued":
            queued_at[key] = event.timestamp
        if event.result == "processing_started" and key in queued_at:
            waits.setdefault(event.stage_id, []).append(
                max(event.timestamp - queued_at.pop(key), 0.0)
            )
    return waits


def _stage_processing_times(events: list[Any]) -> dict[str, list[float]]:
    started_at: dict[tuple[str, str], float] = {}
    durations: dict[str, list[float]] = {}
    for event in events:
        if event.batch_id is None or event.stage_id is None:
            continue
        key = (event.batch_id, event.stage_id)
        if event.result == "processing_started":
            started_at[key] = event.timestamp
        if event.result in {"processing_finished", "batch_marked_for_rejection"}:
            if key in started_at:
                durations.setdefault(event.stage_id, []).append(
                    max(event.timestamp - started_at.pop(key), 0.0)
                )
    return durations


def _count_events(events: list[Any], stage_id: str, result_name: str) -> int:
    return sum(
        1
        for event in events
        if event.stage_id == stage_id and event.result == result_name
    )


def _status(entity: Any) -> str:
    status = getattr(entity, "status", "")
    return getattr(status, "value", status)
