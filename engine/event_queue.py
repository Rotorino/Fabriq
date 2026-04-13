"""Priority queue for discrete simulation events."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from engine.events import Event


@dataclass(slots=True)
class EventQueue:
    """Stable priority queue ordered by event timestamp."""

    _heap: list[tuple[float, int, Event]] = field(default_factory=list)
    _sequence: int = 0

    def push(self, event: Event) -> None:
        """Add an event to the queue."""
        heapq.heappush(self._heap, (event.timestamp, self._sequence, event))
        self._sequence += 1

    def pop(self) -> Event:
        """Remove and return the earliest event from the queue."""
        if not self._heap:
            raise IndexError("Cannot pop from an empty event queue")
        return heapq.heappop(self._heap)[2]

    def is_empty(self) -> bool:
        """Return True when the queue has no events."""
        return not self._heap

    def __len__(self) -> int:
        """Return the number of scheduled events."""
        return len(self._heap)

