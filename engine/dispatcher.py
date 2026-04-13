"""Event dispatcher for simulation handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.context import SimulationContext
from engine.events import Event, EventType


class EventHandler(Protocol):
    """Protocol for event handler classes."""

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Process a simulation event."""


@dataclass(slots=True)
class EventDispatcher:
    """Dispatches events to registered handlers by event type."""

    handlers: dict[EventType, EventHandler]

    def dispatch(self, event: Event, context: SimulationContext) -> None:
        """Run the handler registered for the event type."""
        try:
            handler = self.handlers[event.event_type]
        except KeyError as exc:
            raise KeyError(f"No handler registered for {event.event_type.value}") from exc
        handler.handle(event, context)

