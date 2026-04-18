"""Business metric calculators for simulation results."""

from __future__ import annotations

from typing import Any

from analytics.aggregators import (
    buffer_lengths_by_stage,
    events_by_batch,
    machine_activity_by_machine,
    queue_lengths_by_stage,
)
from analytics.metrics import average, calculate_utilization
from domain.models import (
    AnalyticsReport,
    BatchMetrics,
    GeneralMetrics,
    MachineMetrics,
    ScenarioComparisonRow,
    StageMetrics,
)


def calculate_analytics(result: Any) -> AnalyticsReport:
    """Calculate general, stage, machine, and batch metrics."""
    batch_metrics = _batch_metrics(result)
    machine_metrics = _machine_metrics(result)
    stage_metrics = _stage_metrics(result, batch_metrics, machine_metrics)
    completed_batches = [batch for batch in result.batches if _status(batch) == "completed"]
    rejected_batches = [batch for batch in result.batches if _status(batch) == "rejected"]
    output_units = sum(int(getattr(batch, "size", 0)) for batch in completed_batches)
    rejected_units = sum(int(getattr(batch, "size", 0)) for batch in rejected_batches)
    total_breakdowns = sum(metric["breakdowns"] for metric in machine_metrics)
    total_repair_time = sum(metric["downtime_time"] for metric in machine_metrics)
    total_busy_time = sum(metric["busy_time"] for metric in machine_metrics)
    total_idle_time = sum(metric["idle_time"] for metric in machine_metrics)
    total_batches = len(result.batches)
    average_cycle_time = average(
        [float(metric["cycle_time"]) for metric in batch_metrics]
    )
    average_wait_time = average(
        [float(metric["queue_wait_time"]) for metric in batch_metrics]
    )
    throughput = (
        output_units / result.simulation_time if result.simulation_time > 0 else 0.0
    )

    return AnalyticsReport(
        scenario_name=result.scenario_name,
        general=GeneralMetrics(
            total_batches=total_batches,
            completed_batches=len(completed_batches),
            rejected_batches=len(rejected_batches),
            simulation_time=result.simulation_time,
            output_units=output_units,
            rejected_units=rejected_units,
            completion_rate=len(completed_batches) / max(total_batches, 1),
            rejection_rate=len(rejected_batches) / max(total_batches, 1),
            average_cycle_time=average_cycle_time,
            average_wait_time=average_wait_time,
            throughput=throughput,
            total_breakdowns=total_breakdowns,
            total_repair_time=total_repair_time,
            total_busy_time=total_busy_time,
            total_idle_time=total_idle_time,
        ),
        stages=stage_metrics,
        machines=machine_metrics,
        batches=batch_metrics,
    )


def compare_analytics_runs(
    analytics_runs: list[AnalyticsReport],
) -> list[ScenarioComparisonRow]:
    """Build a compact scenario-comparison table from analytics results."""
    comparison_rows: list[ScenarioComparisonRow] = []
    for analytics in analytics_runs:
        general = analytics["general"]
        stage_rows = analytics.get("stages", [])
        machine_rows = analytics.get("machines", [])
        comparison_rows.append(
            ScenarioComparisonRow(
                scenario_name=analytics["scenario_name"],
                output_units=general.get("output_units", 0),
                average_cycle_time=general.get("average_cycle_time", 0.0),
                rejection_rate=general.get("rejection_rate", 0.0),
                average_queue_length=average(
                    [float(row["average_queue_length"]) for row in stage_rows]
                ),
                average_wait_time=average(
                    [float(row["average_wait_time"]) for row in stage_rows]
                ),
                average_machine_utilization=average(
                    [float(row["utilization"]) for row in machine_rows]
                ),
                throughput=general.get("throughput", 0.0),
                total_breakdowns=general.get("total_breakdowns", 0),
                total_repair_time=general.get("total_repair_time", 0.0),
                completion_rate=general.get("completion_rate", 0.0),
            )
        )
    return comparison_rows


def _batch_metrics(result: Any) -> list[BatchMetrics]:
    batch_events = events_by_batch(result.event_log)
    processing_segments = _processing_segments_by_batch(result.event_log)
    metrics: list[BatchMetrics] = []

    for batch in result.batches:
        batch_id = str(batch.batch_id)
        events = batch_events.get(batch_id, [])
        finish_timestamp = _find_finish_timestamp(events, result.simulation_time)
        queue_wait_time = _batch_queue_wait_time(events)
        processing_time = sum(
            float(segment["duration"])
            for segment in processing_segments.get(batch_id, [])
        )
        waited_in_queue = queue_wait_time > 0 or any(
            event.result == "buffered" for event in events
        )
        metrics.append(
            BatchMetrics(
                batch_id=batch_id,
                cycle_time=max(
                    finish_timestamp - float(getattr(batch, "arrival_time", 0.0)),
                    0.0,
                ),
                queue_wait_time=queue_wait_time,
                processing_time=processing_time,
                stages_count=len(getattr(batch, "route", [])),
                completed=_status(batch) == "completed",
                rejected=_status(batch) == "rejected",
                waited_in_queue=waited_in_queue,
                status=_status(batch),
            )
        )
    return metrics


def _stage_metrics(
    result: Any,
    batch_metrics: list[BatchMetrics],
    machine_metrics: list[MachineMetrics],
) -> list[StageMetrics]:
    queue_lengths = queue_lengths_by_stage(result.raw_data)
    buffer_lengths = buffer_lengths_by_stage(result.raw_data)
    queue_waits = _stage_wait_times(result.event_log)
    processing_times = _stage_processing_times(result.event_log)
    stage_batch_metrics = _batch_metrics_by_stage(result.event_log)
    machine_metrics_by_stage = _machine_metrics_by_stage(machine_metrics, result.machines)
    queue_stats = {
        stage_id: _queue_statistics(rows, result.simulation_time, "queue_length")
        for stage_id, rows in queue_lengths.items()
    }
    buffer_stats = {
        stage_id: _queue_statistics(rows, result.simulation_time, "buffer_length")
        for stage_id, rows in buffer_lengths.items()
    }
    batch_metric_map = {row["batch_id"]: row for row in batch_metrics}

    metrics: list[StageMetrics] = []
    for stage in result.stages:
        stage_id = stage.stage_id
        per_stage_batch_metrics = stage_batch_metrics.get(stage_id, {})
        processed_batch_ids = sorted(per_stage_batch_metrics)
        queue_stat = queue_stats.get(stage_id, _empty_queue_statistics())
        buffer_stat = buffer_stats.get(stage_id, _empty_queue_statistics())
        machine_rows = machine_metrics_by_stage.get(stage_id, [])
        utilization_values = [float(row["utilization"]) for row in machine_rows]
        stage_output_units = sum(
            int(getattr(result_batch, "size", 0))
            for result_batch in result.batches
            if str(result_batch.batch_id) in processed_batch_ids
        )
        rejected_batch_ids = {
            event.batch_id
            for event in result.event_log
            if event.stage_id == stage_id and event.result == "batch_rejected"
        }

        metrics.append(
            StageMetrics(
                stage_id=stage_id,
                processed_batches=len(processed_batch_ids),
                output_units=stage_output_units,
                average_wait_time=average(queue_waits.get(stage_id, [])),
                average_processing_time=average(processing_times.get(stage_id, [])),
                average_queue_length=queue_stat["average"],
                max_queue_length=queue_stat["maximum"],
                average_buffer_length=buffer_stat["average"],
                max_buffer_length=buffer_stat["maximum"],
                utilization=average(utilization_values),
                rejected_batches=len(rejected_batch_ids),
                breakdowns=sum(int(row["breakdowns"]) for row in machine_rows),
                downtime_time=sum(float(row["downtime_time"]) for row in machine_rows),
                completion_rate=average(
                    [
                        1.0 if batch_metric_map[batch_id]["completed"] else 0.0
                        for batch_id in processed_batch_ids
                        if batch_id in batch_metric_map
                    ]
                ),
            )
        )
    return metrics


def _machine_metrics(result: Any) -> list[MachineMetrics]:
    activity = machine_activity_by_machine(result.raw_data)
    metrics: list[MachineMetrics] = []
    for machine in result.machines:
        rows = activity.get(machine.machine_id, [])
        busy_time = _sum_machine_busy_time(rows, result.simulation_time)
        downtime_time = _sum_machine_downtime(rows, result.simulation_time)
        breakdowns = sum(1 for row in rows if row["event"] == "machine_broken")
        repair_times = _machine_repair_times(rows)
        utilization = calculate_utilization(busy_time, result.simulation_time)
        metrics.append(
            MachineMetrics(
                machine_id=machine.machine_id,
                stage_id=getattr(machine, "stage_id", None),
                busy_time=busy_time,
                idle_time=max(
                    result.simulation_time - busy_time - downtime_time,
                    0.0,
                ),
                downtime_time=downtime_time,
                breakdowns=breakdowns,
                repair_count=len(repair_times),
                average_repair_time=average(repair_times),
                utilization=utilization,
            )
        )
    return metrics


def _processing_segments_by_batch(events: list[Any]) -> dict[str, list[dict[str, Any]]]:
    started_at: dict[tuple[str, str, str | None], float] = {}
    segments_by_batch: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.batch_id is None or event.stage_id is None:
            continue
        key = (event.batch_id, event.stage_id, event.machine_id)
        if event.result == "processing_started":
            started_at[key] = float(event.timestamp)
            continue
        if event.result not in {"processing_finished", "batch_marked_for_rejection", "machine_broken"}:
            continue
        start_time = started_at.pop(key, None)
        if start_time is None:
            continue
        segments_by_batch.setdefault(event.batch_id, []).append(
            {
                "stage_id": event.stage_id,
                "machine_id": event.machine_id,
                "duration": max(float(event.timestamp) - start_time, 0.0),
            }
        )
    return segments_by_batch


def _batch_metrics_by_stage(events: list[Any]) -> dict[str, dict[str, dict[str, float]]]:
    started_at: dict[tuple[str, str, str | None], float] = {}
    metrics: dict[str, dict[str, dict[str, float]]] = {}
    for event in events:
        if event.batch_id is None or event.stage_id is None:
            continue
        key = (event.batch_id, event.stage_id, event.machine_id)
        stage_metrics = metrics.setdefault(event.stage_id, {})
        batch_metrics = stage_metrics.setdefault(
            event.batch_id,
            {"processing_time": 0.0, "wait_time": 0.0},
        )
        if event.result == "queued":
            batch_metrics["wait_started_at"] = float(event.timestamp)
            continue
        if event.result == "processing_started":
            started_at[key] = float(event.timestamp)
            wait_started_at = batch_metrics.pop("wait_started_at", None)
            if wait_started_at is not None:
                batch_metrics["wait_time"] += max(
                    float(event.timestamp) - wait_started_at,
                    0.0,
                )
            continue
        if event.result not in {"processing_finished", "batch_marked_for_rejection", "machine_broken"}:
            continue
        start_time = started_at.pop(key, None)
        if start_time is None:
            continue
        batch_metrics["processing_time"] += max(float(event.timestamp) - start_time, 0.0)
    for stage_metrics in metrics.values():
        for batch_metrics in stage_metrics.values():
            batch_metrics.pop("wait_started_at", None)
    return metrics


def _machine_metrics_by_stage(
    machine_metrics: list[MachineMetrics],
    machines: list[Any],
) -> dict[str, list[MachineMetrics]]:
    machine_stage_map = {
        str(machine.machine_id): str(getattr(machine, "stage_id", ""))
        for machine in machines
    }
    grouped: dict[str, list[MachineMetrics]] = {}
    for metric in machine_metrics:
        stage_id = str(metric.get("stage_id") or machine_stage_map.get(metric["machine_id"], ""))
        grouped.setdefault(stage_id, []).append(metric)
    return grouped


def _find_finish_timestamp(events: list[Any], fallback_time: float) -> float:
    for event in reversed(events):
        if event.result in {"batch_completed", "batch_rejected"}:
            return float(event.timestamp)
    return float(fallback_time)


def _batch_queue_wait_time(events: list[Any]) -> float:
    wait_started_at: dict[str, float] = {}
    total_wait = 0.0
    for event in events:
        if event.stage_id is None:
            continue
        if event.result == "queued":
            wait_started_at[event.stage_id] = float(event.timestamp)
            continue
        if event.result != "processing_started":
            continue
        started_at = wait_started_at.pop(event.stage_id, None)
        if started_at is None:
            continue
        total_wait += max(float(event.timestamp) - started_at, 0.0)
    return total_wait


def _sum_machine_busy_time(rows: list[dict[str, Any]], end_time: float) -> float:
    busy_started: float | None = None
    total = 0.0
    for row in rows:
        timestamp = float(row["timestamp"])
        if row["event"] == "processing_started" and busy_started is None:
            busy_started = timestamp
            continue
        if row["event"] in {"processing_finished", "machine_broken"} and busy_started is not None:
            total += max(timestamp - busy_started, 0.0)
            busy_started = None
    if busy_started is not None:
        total += max(end_time - busy_started, 0.0)
    return total


def _sum_machine_downtime(rows: list[dict[str, Any]], end_time: float) -> float:
    repair_started: float | None = None
    total = 0.0
    for row in rows:
        timestamp = float(row["timestamp"])
        if row["event"] == "machine_broken" and repair_started is None:
            repair_started = timestamp
            continue
        if row["event"] == "repair_finished" and repair_started is not None:
            total += max(timestamp - repair_started, 0.0)
            repair_started = None
    if repair_started is not None:
        total += max(end_time - repair_started, 0.0)
    return total


def _machine_repair_times(rows: list[dict[str, Any]]) -> list[float]:
    repair_started: float | None = None
    repair_times: list[float] = []
    for row in rows:
        timestamp = float(row["timestamp"])
        if row["event"] == "machine_broken":
            repair_started = timestamp
            continue
        if row["event"] == "repair_finished" and repair_started is not None:
            repair_times.append(max(timestamp - repair_started, 0.0))
            repair_started = None
    return repair_times


def _stage_wait_times(events: list[Any]) -> dict[str, list[float]]:
    stage_batch_metrics = _batch_metrics_by_stage(events)
    waits: dict[str, list[float]] = {}
    for stage_id, batch_rows in stage_batch_metrics.items():
        waits[stage_id] = [float(row["wait_time"]) for row in batch_rows.values()]
    return waits


def _stage_processing_times(events: list[Any]) -> dict[str, list[float]]:
    stage_batch_metrics = _batch_metrics_by_stage(events)
    durations: dict[str, list[float]] = {}
    for stage_id, batch_rows in stage_batch_metrics.items():
        durations[stage_id] = [float(row["processing_time"]) for row in batch_rows.values()]
    return durations


def _queue_statistics(
    rows: list[dict[str, Any]],
    simulation_time: float,
    value_key: str,
) -> dict[str, float]:
    """Calculate max and time-weighted average for queue or buffer observations."""
    if simulation_time <= 0:
        return _empty_queue_statistics()
    if not rows:
        return _empty_queue_statistics()

    deduplicated: list[tuple[float, float]] = []
    for row in rows:
        timestamp = float(row["timestamp"])
        value = float(row[value_key])
        if deduplicated and deduplicated[-1][0] == timestamp:
            deduplicated[-1] = (timestamp, value)
        else:
            deduplicated.append((timestamp, value))

    weighted_total = 0.0
    previous_time = 0.0
    previous_value = 0.0
    maximum = 0.0
    for timestamp, value in deduplicated:
        clamped_timestamp = min(max(timestamp, 0.0), simulation_time)
        weighted_total += max(clamped_timestamp - previous_time, 0.0) * previous_value
        previous_time = clamped_timestamp
        previous_value = value
        maximum = max(maximum, value)
    weighted_total += max(simulation_time - previous_time, 0.0) * previous_value

    return {
        "average": weighted_total / simulation_time,
        "maximum": maximum,
    }


def _empty_queue_statistics() -> dict[str, float]:
    """Return a zero-value queue statistics payload."""
    return {"average": 0.0, "maximum": 0.0}


def _status(entity: Any) -> str:
    status = getattr(entity, "status", "")
    return getattr(status, "value", status)
