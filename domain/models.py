"""Shared DTOs for scenarios, analytics, and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


class MappingLikeMixin:
    """Provide a minimal mapping-like API for DTO compatibility."""

    def __getitem__(self, key: str) -> Any:
        """Return a field value by key."""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a field value or a default."""
        return getattr(self, key, default)

    def __contains__(self, key: object) -> bool:
        """Return True when the DTO exposes the requested field."""
        return isinstance(key, str) and any(field.name == key for field in fields(self))

    def keys(self) -> list[str]:
        """Return field names for mapping-style introspection."""
        return [field.name for field in fields(self)]

    def items(self) -> list[tuple[str, Any]]:
        """Return key-value pairs for mapping-style introspection."""
        return [(field.name, getattr(self, field.name)) for field in fields(self)]

    def values(self) -> list[Any]:
        """Return field values for mapping-style introspection."""
        return [getattr(self, field.name) for field in fields(self)]

    def to_dict(self) -> dict[str, Any]:
        """Return a recursively serializable representation."""
        return _serialize_value(self)


def _serialize_value(value: Any) -> Any:
    """Convert nested DTO values into JSON-serializable structures."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _serialize_value(item)
            for key, item in value.items()
        }
    if is_dataclass(value):
        return {
            key: _serialize_value(item)
            for key, item in asdict(value).items()
        }
    return value


@dataclass(slots=True)
class ScenarioConfig(MappingLikeMixin):
    """Validated scenario metadata and run settings."""

    name: str
    description: str
    simulation_duration: float
    seed: int | None = None
    batch_generation_mode: str = "equal_intervals"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate scenario metadata."""
        if not self.name:
            raise ValueError("scenario name must not be empty")
        if self.simulation_duration < 0:
            raise ValueError("simulation_duration must be non-negative")


@dataclass(slots=True)
class GeneralMetrics(MappingLikeMixin):
    """Top-level scenario metrics."""

    total_batches: int
    completed_batches: int
    rejected_batches: int
    simulation_time: float
    output_units: int
    rejected_units: int
    completion_rate: float
    rejection_rate: float
    average_cycle_time: float
    average_wait_time: float
    throughput: float
    total_breakdowns: int
    total_repair_time: float
    total_busy_time: float
    total_idle_time: float


@dataclass(slots=True)
class StageMetrics(MappingLikeMixin):
    """Metrics calculated for one production stage."""

    stage_id: str
    processed_batches: int
    output_units: int
    average_wait_time: float
    average_processing_time: float
    average_queue_length: float
    max_queue_length: float
    average_buffer_length: float
    max_buffer_length: float
    utilization: float
    rejected_batches: int
    breakdowns: int
    downtime_time: float
    completion_rate: float


@dataclass(slots=True)
class MachineMetrics(MappingLikeMixin):
    """Metrics calculated for one machine."""

    machine_id: str
    stage_id: str | None
    busy_time: float
    idle_time: float
    downtime_time: float
    breakdowns: int
    repair_count: int
    average_repair_time: float
    utilization: float


@dataclass(slots=True)
class BatchMetrics(MappingLikeMixin):
    """Metrics calculated for one production batch."""

    batch_id: str
    cycle_time: float
    queue_wait_time: float
    processing_time: float
    stages_count: int
    completed: bool
    rejected: bool
    waited_in_queue: bool
    status: str


@dataclass(slots=True)
class AnalyticsReport(MappingLikeMixin):
    """Typed analytics payload shared across post-processing modules."""

    scenario_name: str
    general: GeneralMetrics
    stages: list[StageMetrics]
    machines: list[MachineMetrics]
    batches: list[BatchMetrics]


@dataclass(slots=True)
class ScenarioComparisonRow(MappingLikeMixin):
    """One row in a multi-scenario comparison."""

    scenario_name: str
    output_units: int
    average_cycle_time: float
    rejection_rate: float
    average_queue_length: float
    average_wait_time: float
    average_machine_utilization: float
    throughput: float
    total_breakdowns: int
    total_repair_time: float
    completion_rate: float


@dataclass(slots=True)
class ReportFiles(MappingLikeMixin):
    """Paths to exported report artifacts."""

    json: str
    csv: str
    txt: str
    md: str


@dataclass(slots=True)
class BottleneckSummary(MappingLikeMixin):
    """High-level bottleneck description for a scenario."""

    stage_id: str | None
    average_wait_time: float = 0.0
    average_queue_length: float = 0.0
    max_queue_length: float = 0.0
    utilization: float = 0.0
    downtime_time: float = 0.0
    reason: str | None = None


@dataclass(slots=True)
class PerformanceInsights(MappingLikeMixin):
    """Derived performance insights for a scenario."""

    average_machine_utilization: float
    most_utilized_machine: str | None
    least_utilized_machine: str | None
    most_problematic_stage: str | None
    efficiency_score: float


@dataclass(slots=True)
class ScenarioReport(MappingLikeMixin):
    """Typed exported report for one scenario."""

    scenario_name: str
    scenario_description: str
    run_parameters: dict[str, Any]
    analytics: AnalyticsReport
    bottleneck: BottleneckSummary
    problem_stages: list[StageMetrics]
    recommendations: list[str]
    performance_insights: PerformanceInsights
    charts: list[str]
    files: ReportFiles | None = None


@dataclass(slots=True)
class ComparisonReport(MappingLikeMixin):
    """Typed exported report for multiple scenarios."""

    scenarios: list[str]
    comparison: list[ScenarioComparisonRow]
    best_output_scenario: ScenarioComparisonRow | None
    lowest_cycle_time_scenario: ScenarioComparisonRow | None
    lowest_rejection_scenario: ScenarioComparisonRow | None
    highest_throughput_scenario: ScenarioComparisonRow | None
    files: ReportFiles | None = None
