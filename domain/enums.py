"""Shared enum values used by the simulation modules."""

from __future__ import annotations

from enum import Enum


class BatchStatus(str, Enum):
    """Lifecycle statuses for production batches."""

    NEW = "new"
    WAITING = "waiting"
    BUFFERED = "buffered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class MachineStatus(str, Enum):
    """Lifecycle statuses for production machines."""

    IDLE = "idle"
    BUSY = "busy"
    BROKEN = "broken"
