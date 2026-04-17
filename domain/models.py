"""Shared DTOs for scenarios and calculated metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ScenarioConfig:
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
class StageMetrics:
    """Metrics calculated for one production stage."""

    stage_id: str
    processed_batches: int
    average_wait_time: float
    average_processing_time: float
    max_queue_length: int
    utilization: float
    rejected_batches: int
    breakdowns: int


@dataclass(slots=True)
class MachineMetrics:
    """Metrics calculated for one machine."""

    machine_id: str
    busy_time: float
    idle_time: float
    breakdowns: int
    average_repair_time: float
    utilization: float
