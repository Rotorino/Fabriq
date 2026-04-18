"""Analytics API for simulation results."""

from analytics.aggregators import (
    buffer_lengths_by_stage,
    events_by_batch,
    events_by_machine,
    events_by_result,
    events_by_stage,
    events_by_time,
    machine_activity_by_machine,
    queue_lengths_by_stage,
)
from analytics.calculators import calculate_analytics, compare_analytics_runs
from domain.models import (
    AnalyticsReport,
    BatchMetrics,
    GeneralMetrics,
    MachineMetrics,
    ScenarioComparisonRow,
    StageMetrics,
)

__all__ = [
    "AnalyticsReport",
    "BatchMetrics",
    "calculate_analytics",
    "compare_analytics_runs",
    "buffer_lengths_by_stage",
    "events_by_batch",
    "events_by_machine",
    "events_by_result",
    "events_by_stage",
    "events_by_time",
    "GeneralMetrics",
    "MachineMetrics",
    "machine_activity_by_machine",
    "queue_lengths_by_stage",
    "ScenarioComparisonRow",
    "StageMetrics",
]
