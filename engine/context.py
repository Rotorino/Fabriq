"""Simulation context and event log structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.entities import Batch, ProductionLine
from engine.event_queue import EventQueue
from engine.events import Event


@dataclass(slots=True)
class EventLogRecord:
    """Stores the result of one processed simulation event."""

    timestamp: float
    event_type: str
    batch_id: str | None
    stage_id: str | None
    machine_id: str | None
    result: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationContext:
    """Mutable runtime state shared by event handlers."""

    event_queue: EventQueue
    production_line: ProductionLine
    batches: dict[str, Batch]
    current_time: float = 0.0
    processed_events: list[Event] = field(default_factory=list)
    event_log: list[EventLogRecord] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    stopped: bool = False

    def add_event_log(
        self,
        event: Event,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an event processing result to the simulation journal."""
        self.processed_events.append(event)
        self.event_log.append(
            EventLogRecord(
                timestamp=event.timestamp,
                event_type=event.event_type.value,
                batch_id=event.batch_id,
                stage_id=event.stage_id,
                machine_id=event.machine_id,
                result=result,
                details=details or {},
            )
        )
