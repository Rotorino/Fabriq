"""Event DTOs and event type enum for the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EventType(str, Enum):
    """Supported discrete simulation event types."""

    BATCH_ARRIVAL = "BATCH_ARRIVAL"
    QUEUE_ENTER = "QUEUE_ENTER"
    PROCESSING_START = "PROCESSING_START"
    PROCESSING_FINISH = "PROCESSING_FINISH"
    MOVE_TO_NEXT_STAGE = "MOVE_TO_NEXT_STAGE"
    MACHINE_BREAKDOWN = "MACHINE_BREAKDOWN"
    REPAIR_FINISH = "REPAIR_FINISH"
    BATCH_REJECTED = "BATCH_REJECTED"
    SIMULATION_END = "SIMULATION_END"


@dataclass(slots=True)
class Event:
    """A single event scheduled in the simulation."""

    timestamp: float
    event_type: EventType
    batch_id: str | None = None
    stage_id: str | None = None
    machine_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))

