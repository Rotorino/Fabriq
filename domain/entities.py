"""Dataclass entities shared by scenario, engine, and analytics modules."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.enums import BatchStatus, MachineStatus


def _validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in range [0.0, 1.0]")


@dataclass(slots=True)
class Batch:
    """A production batch that travels through a processing route."""

    batch_id: str
    arrival_time: float
    size: int
    route: list[str]
    current_stage_index: int = 0
    status: BatchStatus = BatchStatus.NEW
    is_rejected: bool = False

    def __post_init__(self) -> None:
        """Validate batch fields."""
        if not self.batch_id:
            raise ValueError("batch_id must not be empty")
        if self.arrival_time < 0:
            raise ValueError("arrival_time must be non-negative")
        if self.size <= 0:
            raise ValueError("size must be positive")
        if not self.route:
            raise ValueError("route must contain at least one stage_id")

    def set_status(self, status: BatchStatus) -> None:
        """Change batch status."""
        self.status = status


@dataclass(slots=True)
class Machine:
    """A machine assigned to one production stage."""

    machine_id: str
    stage_id: str
    processing_time: float
    breakdown_probability: float = 0.0
    repair_time: float = 0.0
    status: MachineStatus = MachineStatus.IDLE
    busy_until: float = 0.0
    current_batch_id: str | None = None
    interrupted_batch_id: str | None = None

    def __post_init__(self) -> None:
        """Validate machine fields."""
        if not self.machine_id:
            raise ValueError("machine_id must not be empty")
        if not self.stage_id:
            raise ValueError("stage_id must not be empty")
        if self.processing_time < 0:
            raise ValueError("processing_time must be non-negative")
        if self.repair_time < 0:
            raise ValueError("repair_time must be non-negative")
        _validate_probability("breakdown_probability", self.breakdown_probability)

    def set_status(self, status: MachineStatus) -> None:
        """Change machine status."""
        self.status = status


@dataclass(slots=True)
class Buffer:
    """A finite waiting buffer for overflow from a stage queue."""

    capacity: int | None
    batch_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate buffer fields."""
        if self.capacity is not None and self.capacity < 0:
            raise ValueError("buffer capacity must be non-negative or None")

    def can_accept(self) -> bool:
        """Return True when the buffer can accept another batch."""
        return self.capacity is None or len(self.batch_ids) < self.capacity


@dataclass(slots=True)
class Stage:
    """A production stage containing machines, queue, and buffer."""

    stage_id: str
    name: str
    machines: list[Machine]
    queue_limit: int | None
    reject_probability: float = 0.0
    buffer_capacity: int | None = 0
    next_stage_id: str | None = None
    queue: list[str] = field(default_factory=list)
    buffer: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate stage fields."""
        if not self.stage_id:
            raise ValueError("stage_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.machines:
            raise ValueError("stage must contain at least one machine")
        if self.queue_limit is not None and self.queue_limit < 0:
            raise ValueError("queue_limit must be non-negative or None")
        if self.buffer_capacity is not None and self.buffer_capacity < 0:
            raise ValueError("buffer_capacity must be non-negative or None")
        _validate_probability("reject_probability", self.reject_probability)


@dataclass(slots=True)
class ProductionLine:
    """A full production line made of ordered stages."""

    stages: dict[str, Stage]

    def __post_init__(self) -> None:
        """Validate production line fields."""
        if not self.stages:
            raise ValueError("production line must contain at least one stage")

    def get_stage(self, stage_id: str) -> Stage:
        """Return a stage by identifier."""
        try:
            return self.stages[stage_id]
        except KeyError as exc:
            raise KeyError(f"Unknown stage_id: {stage_id}") from exc

    def all_machines(self) -> list[Machine]:
        """Return all machines in stage order."""
        return [
            machine
            for stage in self.stages.values()
            for machine in stage.machines
        ]
