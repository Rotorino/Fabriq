"""Dataclass entities shared by scenario, engine, and analytics modules."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.enums import BatchStatus, MachineStatus, RoutingStrategy, StageType


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

    def get_current_stage_id(self) -> str:
        """Return the current route stage identifier."""
        return self.route[self.current_stage_index]

    def move_to_next_stage(self) -> str | None:
        """Advance the batch to the next route stage and return it."""
        next_index = self.current_stage_index + 1
        if next_index >= len(self.route):
            self.current_stage_index = len(self.route) - 1
            return None
        self.current_stage_index = next_index
        self.status = BatchStatus.WAITING
        return self.route[next_index]

    def mark_processing(self) -> None:
        """Mark the batch as being processed."""
        self.status = BatchStatus.PROCESSING

    def mark_waiting(self) -> None:
        """Mark the batch as waiting for processing."""
        self.status = BatchStatus.WAITING

    def mark_buffered(self) -> None:
        """Mark the batch as waiting in a stage buffer."""
        self.status = BatchStatus.BUFFERED

    def mark_completed(self) -> None:
        """Mark the batch as completed."""
        self.status = BatchStatus.COMPLETED

    def mark_rejected(self) -> None:
        """Mark the batch as rejected."""
        self.is_rejected = True
        self.status = BatchStatus.REJECTED


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

    def start_processing(self, batch_id: str, finish_time: float) -> None:
        """Reserve the machine for processing a batch."""
        self.status = MachineStatus.BUSY
        self.current_batch_id = batch_id
        self.busy_until = finish_time

    def mark_broken(
        self,
        *,
        interrupted_batch_id: str | None,
        repair_finish_time: float,
    ) -> None:
        """Mark the machine as broken and store interrupted processing state."""
        self.status = MachineStatus.BROKEN
        self.interrupted_batch_id = interrupted_batch_id
        self.current_batch_id = None
        self.busy_until = repair_finish_time

    def mark_idle(self, at_time: float) -> None:
        """Release the machine after processing or repair."""
        self.status = MachineStatus.IDLE
        self.busy_until = at_time
        self.current_batch_id = None
        self.interrupted_batch_id = None


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

    def add_batch(self, batch_id: str) -> None:
        """Store a batch in the buffer."""
        if not self.can_accept():
            raise ValueError("buffer is full")
        self.batch_ids.append(batch_id)

    def pop_batch(self) -> str | None:
        """Return the oldest buffered batch if available."""
        if not self.batch_ids:
            return None
        return self.batch_ids.pop(0)


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
    stage_type: StageType = StageType.PROCESSING
    routing_strategy: RoutingStrategy = RoutingStrategy.SEQUENTIAL
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
        for machine in self.machines:
            if machine.stage_id != self.stage_id:
                raise ValueError(
                    f"machine {machine.machine_id} belongs to unexpected stage"
                )

    def has_queue_capacity(self) -> bool:
        """Return True when the stage queue can accept a batch."""
        return self.queue_limit is None or len(self.queue) < self.queue_limit

    def has_buffer_capacity(self) -> bool:
        """Return True when the stage buffer can accept a batch."""
        return self.buffer_capacity is None or len(self.buffer) < self.buffer_capacity

    def enqueue_batch(self, batch_id: str) -> None:
        """Place a batch into the stage queue."""
        if not self.has_queue_capacity():
            raise ValueError(f"queue is full for stage {self.stage_id}")
        self.queue.append(batch_id)

    def dequeue_batch(self) -> str | None:
        """Return the oldest waiting batch from the stage queue."""
        if not self.queue:
            return None
        return self.queue.pop(0)

    def buffer_batch(self, batch_id: str) -> None:
        """Place a batch into the stage buffer."""
        if not self.has_buffer_capacity():
            raise ValueError(f"buffer is full for stage {self.stage_id}")
        self.buffer.append(batch_id)

    def release_buffered_batch(self) -> str | None:
        """Return the oldest buffered batch."""
        if not self.buffer:
            return None
        return self.buffer.pop(0)

    def find_machine(self, machine_id: str) -> Machine:
        """Return a machine by identifier."""
        for machine in self.machines:
            if machine.machine_id == machine_id:
                return machine
        raise KeyError(f"Unknown machine_id: {machine_id}")

    def get_available_machine(self) -> Machine | None:
        """Return the first idle machine on this stage."""
        for machine in self.machines:
            if machine.status == MachineStatus.IDLE:
                return machine
        return None


@dataclass(slots=True)
class ProductionLine:
    """A full production line made of ordered stages."""

    stages: dict[str, Stage]
    entry_stage_id: str | None = None

    def __post_init__(self) -> None:
        """Validate production line fields."""
        if not self.stages:
            raise ValueError("production line must contain at least one stage")
        if self.entry_stage_id is None:
            self.entry_stage_id = next(iter(self.stages))
        if self.entry_stage_id not in self.stages:
            raise ValueError(f"Unknown entry_stage_id: {self.entry_stage_id}")

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

    def ordered_stage_ids(self) -> list[str]:
        """Return stage identifiers in their configured order."""
        return list(self.stages.keys())

    def route_from_entry(self) -> list[str]:
        """Return the logical route by following stage links from the entry stage."""
        if self.entry_stage_id is None:
            raise ValueError("production line entry_stage_id is not set")

        route: list[str] = []
        current_stage_id: str | None = self.entry_stage_id
        visited: set[str] = set()
        while current_stage_id is not None:
            if current_stage_id in visited:
                raise ValueError(
                    f"Cycle detected while resolving route at stage {current_stage_id}"
                )
            visited.add(current_stage_id)
            route.append(current_stage_id)
            current_stage_id = self.get_stage(current_stage_id).next_stage_id

        if len(visited) != len(self.stages):
            missing = sorted(set(self.stages) - visited)
            raise ValueError(
                "Production line route does not cover all stages: "
                + ", ".join(missing)
            )
        return route
