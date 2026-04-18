"""Event handlers for the discrete-event simulation engine."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any

from domain.entities import Batch, Buffer, Machine, ProductionLine, Stage
from domain.enums import BatchStatus, MachineStatus
from engine.context import SimulationContext
from engine.events import Event, EventType

logger = logging.getLogger(__name__)

IDLE_STATUS = MachineStatus.IDLE.value
BUSY_STATUS = MachineStatus.BUSY.value
BROKEN_STATUS = MachineStatus.BROKEN.value
WAITING_STATUS = BatchStatus.WAITING.value
PROCESSING_STATUS = BatchStatus.PROCESSING.value
COMPLETED_STATUS = BatchStatus.COMPLETED.value
REJECTED_STATUS = BatchStatus.REJECTED.value
BUFFERED_STATUS = BatchStatus.BUFFERED.value


def build_default_handlers(rng: random.Random | None = None) -> dict[EventType, Any]:
    """Create the default handler registry used by the simulation engine."""
    random_source = rng or random.Random()
    starter = ProcessingStarter()
    return {
        EventType.BATCH_ARRIVAL: BatchArrivalHandler(),
        EventType.QUEUE_ENTER: QueueEnterHandler(starter=starter),
        EventType.PROCESSING_START: ProcessingStartHandler(rng=random_source),
        EventType.PROCESSING_FINISH: ProcessingFinishHandler(
            rng=random_source,
            starter=starter,
        ),
        EventType.MOVE_TO_NEXT_STAGE: MoveToNextStageHandler(starter=starter),
        EventType.MACHINE_BREAKDOWN: MachineBreakdownHandler(starter=starter),
        EventType.REPAIR_FINISH: RepairFinishHandler(starter=starter),
        EventType.BATCH_REJECTED: BatchRejectedHandler(),
        EventType.SIMULATION_END: SimulationEndHandler(),
    }


@dataclass(slots=True)
class BatchArrivalHandler:
    """Handles arrival of a production batch."""

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Schedule entering the first route stage for the arrived batch."""
        batch = get_batch(context, event.batch_id)
        stage_id = resolve_current_stage_id(batch, context.production_line)
        set_status(batch, WAITING_STATUS)
        context.event_queue.push(
            Event(
                timestamp=event.timestamp,
                event_type=EventType.QUEUE_ENTER,
                batch_id=batch.batch_id,
                stage_id=stage_id,
            )
        )
        context.add_event_log(event, "arrival_registered", {"next_stage_id": stage_id})


@dataclass(slots=True)
class QueueEnterHandler:
    """Places a batch into the stage queue."""

    starter: "ProcessingStarter"

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Add batch to stage queue and try to start processing."""
        stage = get_stage(context.production_line, event.stage_id)
        batch = get_batch(context, event.batch_id)
        queue = ensure_stage_queue(context, stage)
        queue_limit = getattr(stage, "queue_limit", None)
        available_machine = find_available_machine(stage, context)

        if available_machine is not None and not queue:
            if batch.batch_id not in queue:
                if hasattr(stage, "enqueue_batch"):
                    stage.enqueue_batch(batch.batch_id, enforce_capacity=False)
                else:
                    queue.append(batch.batch_id)
            set_status(batch, WAITING_STATUS)
            queue_length = (
                stage.queue_length() if hasattr(stage, "queue_length") else len(queue)
            )
            record_queue_length(context, event.timestamp, stage.stage_id, queue_length)
            context.add_event_log(
                event,
                "queued",
                {"queue_length": queue_length},
            )
            self.starter.try_start_next(event.timestamp, stage, context)
            return

        if (
            queue_limit is not None
            and count_waiting_batches(context, stage, queue) >= queue_limit
        ):
            buffer = ensure_stage_buffer(context, stage)
            buffer_capacity = getattr(stage, "buffer_capacity", 0)
            if buffer_capacity is None or len(buffer) < int(buffer_capacity):
                if batch.batch_id not in buffer:
                    if hasattr(stage, "buffer_batch"):
                        stage.buffer_batch(batch.batch_id)
                    else:
                        buffer.append(batch.batch_id)
                set_status(batch, BUFFERED_STATUS)
                record_buffer_length(
                    context,
                    event.timestamp,
                    stage.stage_id,
                    len(buffer),
                )
                context.add_event_log(
                    event,
                    "buffered",
                    {
                        "queue_length": len(queue),
                        "buffer_length": len(buffer),
                    },
                )
                return

            context.event_queue.push(
                Event(
                    timestamp=event.timestamp,
                    event_type=EventType.BATCH_REJECTED,
                    batch_id=batch.batch_id,
                    stage_id=stage.stage_id,
                )
            )
            context.add_event_log(
                event,
                "buffer_full_marked_for_rejection",
                {"queue_length": len(queue), "buffer_length": len(buffer)},
            )
            logger.warning("Queue is full for stage %s", event.stage_id)
            return

        if batch.batch_id not in queue:
            if hasattr(stage, "enqueue_batch"):
                stage.enqueue_batch(batch.batch_id, enforce_capacity=False)
            else:
                queue.append(batch.batch_id)
        set_status(batch, WAITING_STATUS)
        queue_length = stage.queue_length() if hasattr(stage, "queue_length") else len(queue)
        record_queue_length(context, event.timestamp, stage.stage_id, queue_length)
        context.add_event_log(
            event,
            "queued",
            {"queue_length": queue_length},
        )
        self.starter.try_start_next(event.timestamp, stage, context)


@dataclass(slots=True)
class ProcessingStartHandler:
    """Starts batch processing on a free machine."""

    rng: random.Random

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Reserve a machine and schedule processing completion or breakdown."""
        stage = get_stage(context.production_line, event.stage_id)
        queue = ensure_stage_queue(context, stage)
        machine = get_machine(stage, event.machine_id) if event.machine_id else None
        machine = machine or find_available_machine(stage, context)

        if machine is None:
            context.add_event_log(event, "no_available_machine")
            return
        if not queue:
            set_start_scheduled(context, machine, False)
            if event.batch_id is not None:
                set_batch_start_scheduled(
                    context,
                    stage.stage_id,
                    event.batch_id,
                    False,
                )
            context.add_event_log(
                event,
                "queue_empty",
                {"machine_id": machine.machine_id},
            )
            return

        batch_id = take_queued_batch(context, stage, event.batch_id)
        if batch_id is None:
            set_start_scheduled(context, machine, False)
            context.add_event_log(
                event,
                "reserved_batch_missing",
                {"machine_id": machine.machine_id},
            )
            return
        drain_stage_buffer(context, stage, event.timestamp)
        batch = get_batch(context, batch_id)
        processing_time, is_resumed = take_processing_time(
            context,
            stage,
            machine,
            batch.batch_id,
        )
        finish_time = event.timestamp + processing_time
        set_status(batch, PROCESSING_STATUS)
        set_start_scheduled(context, machine, False)
        if hasattr(machine, "start_processing"):
            machine.start_processing(batch.batch_id, finish_time)
        else:
            set_status(machine, BUSY_STATUS)
            setattr(machine, "busy_until", finish_time)
        set_current_batch_id(context, machine, batch.batch_id)
        queue_length = stage.queue_length() if hasattr(stage, "queue_length") else len(queue)
        record_queue_length(context, event.timestamp, stage.stage_id, queue_length)
        record_machine_activity(
            context,
            machine.machine_id,
            "processing_started",
            event.timestamp,
            batch.batch_id,
        )

        if processing_time <= 0:
            context.event_queue.push(
                Event(
                    timestamp=finish_time,
                    event_type=EventType.PROCESSING_FINISH,
                    batch_id=batch.batch_id,
                    stage_id=stage.stage_id,
                    machine_id=machine.machine_id,
                )
            )
        elif self._should_break(machine):
            breakdown_time = self._breakdown_time(event.timestamp, processing_time)
            context.event_queue.push(
                Event(
                    timestamp=breakdown_time,
                    event_type=EventType.MACHINE_BREAKDOWN,
                    batch_id=batch.batch_id,
                    stage_id=stage.stage_id,
                    machine_id=machine.machine_id,
                    payload={
                        "planned_finish": finish_time,
                        "processing_time": processing_time,
                    },
                )
            )
        else:
            context.event_queue.push(
                Event(
                    timestamp=finish_time,
                    event_type=EventType.PROCESSING_FINISH,
                    batch_id=batch.batch_id,
                    stage_id=stage.stage_id,
                    machine_id=machine.machine_id,
                )
            )

        context.add_event_log(
            event,
            "processing_started",
            {
                "batch_id": batch.batch_id,
                "machine_id": machine.machine_id,
                "finish_time": finish_time,
                "is_resumed": is_resumed,
            },
        )

    def _should_break(self, machine: Any) -> bool:
        probability = float(getattr(machine, "breakdown_probability", 0.0))
        return probability > 0 and self.rng.random() < probability

    @staticmethod
    def _breakdown_time(start_time: float, processing_time: float) -> float:
        return start_time + max(processing_time / 2.0, 0.0)


@dataclass(slots=True)
class ProcessingFinishHandler:
    """Handles successful completion of machine processing."""

    rng: random.Random
    starter: "ProcessingStarter"

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Release the machine and move or reject the batch."""
        stage = get_stage(context.production_line, event.stage_id)
        machine = get_machine(stage, event.machine_id)
        batch = get_batch(context, event.batch_id)

        if (
            not is_status(machine, BUSY_STATUS)
            or get_current_batch_id(context, machine) != batch.batch_id
        ):
            context.add_event_log(event, "processing_finish_skipped")
            return

        if hasattr(machine, "mark_idle"):
            machine.mark_idle(event.timestamp)
        else:
            set_status(machine, IDLE_STATUS)
            setattr(machine, "busy_until", event.timestamp)
        set_current_batch_id(context, machine, None)
        record_machine_activity(
            context,
            machine.machine_id,
            "processing_finished",
            event.timestamp,
            batch.batch_id,
        )

        if self._should_reject(stage):
            context.event_queue.push(
                Event(
                    timestamp=event.timestamp,
                    event_type=EventType.BATCH_REJECTED,
                    batch_id=batch.batch_id,
                    stage_id=stage.stage_id,
                    machine_id=machine.machine_id,
                )
            )
            result = "batch_marked_for_rejection"
        else:
            context.event_queue.push(
                Event(
                    timestamp=event.timestamp,
                    event_type=EventType.MOVE_TO_NEXT_STAGE,
                    batch_id=batch.batch_id,
                    stage_id=stage.stage_id,
                    machine_id=machine.machine_id,
                )
            )
            result = "processing_finished"

        context.add_event_log(event, result)
        self.starter.try_start_next(event.timestamp, stage, context)

    def _should_reject(self, stage: Any) -> bool:
        probability = float(getattr(stage, "reject_probability", 0.0))
        return probability > 0 and self.rng.random() < probability


@dataclass(slots=True)
class MoveToNextStageHandler:
    """Moves a processed batch to the next route stage."""

    starter: "ProcessingStarter"

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Schedule the next queue entry or complete the batch."""
        batch = get_batch(context, event.batch_id)
        current_stage = get_stage(context.production_line, event.stage_id)
        next_stage_id = resolve_next_stage_id(
            batch,
            current_stage,
            context.production_line,
        )

        if next_stage_id is None:
            if hasattr(batch, "mark_completed"):
                batch.mark_completed()
            else:
                set_status(batch, COMPLETED_STATUS)
            context.add_event_log(event, "batch_completed")
            return

        if hasattr(batch, "move_to_next_stage"):
            batch.move_to_next_stage()
        else:
            next_stage_index = int(getattr(batch, "current_stage_index", 0)) + 1
            setattr(batch, "current_stage_index", next_stage_index)
            set_status(batch, WAITING_STATUS)
        context.event_queue.push(
            Event(
                timestamp=event.timestamp,
                event_type=EventType.QUEUE_ENTER,
                batch_id=batch.batch_id,
                stage_id=next_stage_id,
            )
        )
        context.add_event_log(
            event,
            "moved_to_next_stage",
            {"next_stage_id": next_stage_id},
        )


@dataclass(slots=True)
class MachineBreakdownHandler:
    """Handles machine breakdowns."""

    starter: "ProcessingStarter"

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Mark the machine as broken and schedule repair completion."""
        stage = get_stage(context.production_line, event.stage_id)
        machine = get_machine(stage, event.machine_id)

        if not is_status(machine, BUSY_STATUS):
            context.add_event_log(event, "breakdown_skipped")
            return

        batch_id = get_current_batch_id(context, machine) or event.batch_id
        planned_finish = float(event.payload.get("planned_finish", event.timestamp))
        remaining_time = max(planned_finish - event.timestamp, 0.0)
        repair_time = float(getattr(machine, "repair_time", 0.0))
        if hasattr(machine, "mark_broken"):
            machine.mark_broken(
                interrupted_batch_id=batch_id,
                repair_finish_time=event.timestamp + repair_time,
            )
        else:
            set_status(machine, BROKEN_STATUS)
            setattr(machine, "busy_until", event.timestamp + repair_time)
        set_interrupted_batch_id(context, machine, batch_id)
        if batch_id is not None:
            set_remaining_processing_time(
                context,
                stage.stage_id,
                batch_id,
                remaining_time,
            )
            batch = get_batch(context, batch_id)
            queue = ensure_stage_queue(context, stage)
            set_status(batch, WAITING_STATUS)
            if batch_id not in queue:
                queue.insert(0, batch_id)
                record_queue_length(context, event.timestamp, stage.stage_id, len(queue))
        set_current_batch_id(context, machine, None)
        repair_finish = event.timestamp + repair_time
        record_machine_activity(
            context,
            machine.machine_id,
            "machine_broken",
            event.timestamp,
            batch_id,
        )
        context.event_queue.push(
            Event(
                timestamp=repair_finish,
                event_type=EventType.REPAIR_FINISH,
                batch_id=batch_id,
                stage_id=stage.stage_id,
                machine_id=machine.machine_id,
            )
        )
        context.add_event_log(
            event,
            "machine_broken",
            {"repair_finish": repair_finish, "remaining_time": remaining_time},
        )
        self.starter.try_start_next(event.timestamp, stage, context)


@dataclass(slots=True)
class RepairFinishHandler:
    """Handles repair completion for a broken machine."""

    starter: "ProcessingStarter"

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Return the machine to service and resume waiting stage work."""
        stage = get_stage(context.production_line, event.stage_id)
        machine = get_machine(stage, event.machine_id)
        interrupted_batch_id = get_interrupted_batch_id(context, machine)
        if hasattr(machine, "mark_idle"):
            machine.mark_idle(event.timestamp)
        else:
            set_status(machine, IDLE_STATUS)
            setattr(machine, "busy_until", event.timestamp)
        set_interrupted_batch_id(context, machine, None)
        record_machine_activity(
            context,
            machine.machine_id,
            "repair_finished",
            event.timestamp,
            interrupted_batch_id,
        )

        context.add_event_log(
            event,
            "repair_finished",
            {"interrupted_batch_id": interrupted_batch_id},
        )
        self.starter.try_start_next(event.timestamp, stage, context)


@dataclass(slots=True)
class BatchRejectedHandler:
    """Handles batch rejection."""

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Mark a batch as rejected and stop its route."""
        batch = get_batch(context, event.batch_id)
        if hasattr(batch, "mark_rejected"):
            batch.mark_rejected()
        else:
            setattr(batch, "is_rejected", True)
            set_status(batch, REJECTED_STATUS)
        context.add_event_log(event, "batch_rejected")


@dataclass(slots=True)
class SimulationEndHandler:
    """Handles explicit simulation stop events."""

    def handle(self, event: Event, context: SimulationContext) -> None:
        """Mark the simulation context as stopped."""
        context.stopped = True
        context.add_event_log(event, "simulation_stopped")


@dataclass(slots=True)
class ProcessingStarter:
    """Schedules processing start when a stage has a free machine and queue."""

    def try_start_next(
        self,
        timestamp: float,
        stage: Any,
        context: SimulationContext,
    ) -> None:
        """Schedule one processing start event if the stage can process work."""
        drain_stage_buffer(context, stage, timestamp)
        queue = ensure_stage_queue(context, stage)
        machine = find_available_machine(stage, context)
        batch_id = find_unreserved_batch_id(context, stage, queue)
        if batch_id is not None and machine is not None:
            set_start_scheduled(context, machine, True)
            set_batch_start_scheduled(context, stage.stage_id, batch_id, True)
            context.event_queue.push(
                Event(
                    timestamp=timestamp,
                    event_type=EventType.PROCESSING_START,
                    batch_id=batch_id,
                    stage_id=stage.stage_id,
                    machine_id=machine.machine_id,
                )
            )


def get_batch(context: SimulationContext, batch_id: str | None) -> Batch:
    """Return a batch by identifier."""
    if batch_id is None:
        raise ValueError("Event does not contain batch_id")
    try:
        return context.batches[batch_id]
    except KeyError as exc:
        raise KeyError(f"Unknown batch_id: {batch_id}") from exc


def get_stage(production_line: ProductionLine | Any, stage_id: str | None) -> Stage | Any:
    """Return a stage by identifier from a line object, dict, or list."""
    if stage_id is None:
        raise ValueError("Event does not contain stage_id")
    if hasattr(production_line, "get_stage"):
        return production_line.get_stage(stage_id)
    stages = getattr(production_line, "stages", production_line)
    if isinstance(stages, dict):
        try:
            return stages[stage_id]
        except KeyError as exc:
            raise KeyError(f"Unknown stage_id: {stage_id}") from exc
    for stage in stages:
        if getattr(stage, "stage_id") == stage_id:
            return stage
    raise KeyError(f"Unknown stage_id: {stage_id}")


def get_machine(stage: Stage | Any, machine_id: str | None) -> Machine | Any:
    """Return a machine by identifier from a stage."""
    if machine_id is None:
        raise ValueError("Event does not contain machine_id")
    if hasattr(stage, "find_machine"):
        return stage.find_machine(machine_id)
    for machine in getattr(stage, "machines"):
        if getattr(machine, "machine_id") == machine_id:
            return machine
    raise KeyError(f"Unknown machine_id: {machine_id}")


def find_available_machine(
    stage: Any,
    context: SimulationContext | None = None,
) -> Any | None:
    """Return the first idle machine in a stage."""
    for machine in getattr(stage, "machines"):
        start_scheduled = (
            get_start_scheduled(context, machine)
            if context is not None
            else getattr(machine, "start_scheduled", False)
        )
        if is_status(machine, IDLE_STATUS) and not start_scheduled:
            return machine
    return None


def ensure_stage_queue(context: SimulationContext, stage: Any) -> list[str]:
    """Return the mutable runtime queue for a stage."""
    if hasattr(stage, "queue"):
        queue = getattr(stage, "queue")
        if queue is None:
            queue = []
            setattr(stage, "queue", queue)
        return queue
    queues = context.raw_data.setdefault("_stage_queues", {})
    return queues.setdefault(stage.stage_id, [])


def ensure_stage_buffer(context: SimulationContext, stage: Any) -> list[str]:
    """Return the mutable runtime buffer for a stage."""
    if hasattr(stage, "buffer"):
        buffer = getattr(stage, "buffer")
        if isinstance(buffer, Buffer):
            return buffer.batch_ids
        if buffer is None:
            buffer = []
            setattr(stage, "buffer", buffer)
        return buffer
    buffers = context.raw_data.setdefault("_stage_buffers", {})
    return buffers.setdefault(stage.stage_id, [])


def drain_stage_buffer(
    context: SimulationContext,
    stage: Any,
    timestamp: float,
) -> None:
    """Move buffered batches into the waiting queue while queue slots are free."""
    queue = ensure_stage_queue(context, stage)
    buffer = ensure_stage_buffer(context, stage)
    queue_limit = getattr(stage, "queue_limit", None)

    while buffer and (
        queue_limit is None
        or count_waiting_batches(context, stage, queue) < int(queue_limit)
    ):
        batch_id = stage.release_buffered_batch() if hasattr(stage, "release_buffered_batch") else buffer.pop(0)
        if batch_id is None:
            break
        if batch_id not in queue:
            if hasattr(stage, "enqueue_batch"):
                stage.enqueue_batch(batch_id, enforce_capacity=False)
            else:
                queue.append(batch_id)
        set_status(get_batch(context, batch_id), WAITING_STATUS)
        record_queue_length(context, timestamp, stage.stage_id, len(queue))
        record_buffer_length(context, timestamp, stage.stage_id, len(buffer))


def take_queued_batch(
    context: SimulationContext,
    stage: Any,
    batch_id: str | None,
) -> str | None:
    """Remove and return a reserved batch from a stage queue."""
    queue = ensure_stage_queue(context, stage)
    if batch_id is not None and batch_id in queue:
        if hasattr(stage, "remove_from_queue"):
            stage.remove_from_queue(batch_id)
        else:
            queue.remove(batch_id)
        set_batch_start_scheduled(context, stage.stage_id, batch_id, False)
        return batch_id
    if batch_id is not None:
        set_batch_start_scheduled(context, stage.stage_id, batch_id, False)
        return None
    if not queue:
        return None
    next_batch_id = queue.pop(0)
    set_batch_start_scheduled(context, stage.stage_id, next_batch_id, False)
    return next_batch_id


def find_unreserved_batch_id(
    context: SimulationContext,
    stage: Any,
    queue: list[str],
) -> str | None:
    """Return the first queued batch that has no scheduled start event."""
    for batch_id in queue:
        if not get_batch_start_scheduled(context, stage.stage_id, batch_id):
            return batch_id
    return None


def count_waiting_batches(
    context: SimulationContext,
    stage: Any,
    queue: list[str],
) -> int:
    """Return queued batches not already reserved for processing start."""
    return sum(
        1
        for batch_id in queue
        if not get_batch_start_scheduled(context, stage.stage_id, batch_id)
    )


def resolve_current_stage_id(batch: Any, production_line: Any) -> str:
    """Resolve the batch's current route stage."""
    if hasattr(batch, "get_current_stage_id"):
        return str(batch.get_current_stage_id())
    route = getattr(batch, "route", None)
    current_stage_index = int(getattr(batch, "current_stage_index", 0))
    if route:
        return str(route[current_stage_index])
    stages = getattr(production_line, "stages", production_line)
    if isinstance(stages, dict):
        return str(next(iter(stages)))
    return str(getattr(stages[0], "stage_id"))


def resolve_next_stage_id(
    batch: Any,
    current_stage: Any,
    production_line: Any,
) -> str | None:
    """Resolve the next route stage for a processed batch."""
    if hasattr(batch, "get_next_stage_id"):
        return batch.get_next_stage_id()
    route = getattr(batch, "route", None)
    current_stage_index = int(getattr(batch, "current_stage_index", 0))
    if route:
        next_index = current_stage_index + 1
        return str(route[next_index]) if next_index < len(route) else None
    return getattr(current_stage, "next_stage_id", None)


def get_machine_runtime(context: SimulationContext, machine: Any) -> dict[str, Any]:
    """Return internal runtime state for a machine."""
    machine_states = context.raw_data.setdefault("_machine_states", {})
    return machine_states.setdefault(machine.machine_id, {})


def get_current_batch_id(context: SimulationContext, machine: Any) -> str | None:
    """Return the batch currently assigned to a machine."""
    state = get_machine_runtime(context, machine)
    return state.get("current_batch_id")


def set_current_batch_id(
    context: SimulationContext,
    machine: Any,
    batch_id: str | None,
) -> None:
    """Store the batch currently assigned to a machine."""
    state = get_machine_runtime(context, machine)
    state["current_batch_id"] = batch_id
    if hasattr(machine, "current_batch_id"):
        setattr(machine, "current_batch_id", batch_id)


def get_interrupted_batch_id(context: SimulationContext, machine: Any) -> str | None:
    """Return the batch interrupted by a machine breakdown."""
    state = get_machine_runtime(context, machine)
    return state.get("interrupted_batch_id")


def set_interrupted_batch_id(
    context: SimulationContext,
    machine: Any,
    batch_id: str | None,
) -> None:
    """Store the batch interrupted by a machine breakdown."""
    state = get_machine_runtime(context, machine)
    state["interrupted_batch_id"] = batch_id
    if hasattr(machine, "interrupted_batch_id"):
        setattr(machine, "interrupted_batch_id", batch_id)


def get_start_scheduled(context: SimulationContext, machine: Any) -> bool:
    """Return True when a start event has already reserved an idle machine."""
    state = get_machine_runtime(context, machine)
    return bool(state.get("start_scheduled", False))


def set_start_scheduled(
    context: SimulationContext,
    machine: Any,
    is_scheduled: bool,
) -> None:
    """Store a reservation flag for a scheduled processing start."""
    state = get_machine_runtime(context, machine)
    state["start_scheduled"] = is_scheduled
    if hasattr(machine, "start_scheduled"):
        setattr(machine, "start_scheduled", is_scheduled)


def get_batch_start_scheduled(
    context: SimulationContext,
    stage_id: str,
    batch_id: str,
) -> bool:
    """Return True when a queued batch already has a start event."""
    scheduled = context.raw_data.setdefault("_scheduled_batch_starts", {})
    return batch_id in scheduled.setdefault(stage_id, set())


def set_batch_start_scheduled(
    context: SimulationContext,
    stage_id: str,
    batch_id: str,
    is_scheduled: bool,
) -> None:
    """Store a reservation flag for a queued batch."""
    scheduled = context.raw_data.setdefault("_scheduled_batch_starts", {})
    stage_scheduled = scheduled.setdefault(stage_id, set())
    if is_scheduled:
        stage_scheduled.add(batch_id)
    else:
        stage_scheduled.discard(batch_id)


def take_processing_time(
    context: SimulationContext,
    stage: Any,
    machine: Any,
    batch_id: str,
) -> tuple[float, bool]:
    """Return processing time and whether the batch resumes interrupted work."""
    remaining_times = context.raw_data.setdefault("_remaining_processing_times", {})
    remaining_key = (stage.stage_id, batch_id)
    remaining_time = remaining_times.pop(remaining_key, None)
    if remaining_time is not None:
        return float(remaining_time), True
    return float(getattr(machine, "processing_time")), False


def set_remaining_processing_time(
    context: SimulationContext,
    stage_id: str,
    batch_id: str,
    remaining_time: float,
) -> None:
    """Store remaining processing time for a batch interrupted by breakdown."""
    remaining_times = context.raw_data.setdefault("_remaining_processing_times", {})
    remaining_times[(stage_id, batch_id)] = remaining_time


def set_status(entity: Any, value: str) -> None:
    """Set a status value while preserving enum status types when possible."""
    current = getattr(entity, "status", None)
    if isinstance(current, Enum):
        status_type = type(current)
        try:
            setattr(entity, "status", status_type(value))
            return
        except ValueError:
            try:
                setattr(entity, "status", status_type[value.upper()])
                return
            except KeyError:
                logger.warning("Unknown enum status %s for %s", value, status_type)
    setattr(entity, "status", value)


def is_status(entity: Any, value: str) -> bool:
    """Return True when an entity status matches a value."""
    current = getattr(entity, "status", None)
    if isinstance(current, Enum):
        return current.value == value or current.name.lower() == value
    return current == value


def record_queue_length(
    context: SimulationContext,
    timestamp: float,
    stage_id: str,
    queue_length: int,
) -> None:
    """Store queue length observations for later analytics."""
    context.raw_data.setdefault("queue_lengths", []).append(
        {"timestamp": timestamp, "stage_id": stage_id, "queue_length": queue_length}
    )


def record_buffer_length(
    context: SimulationContext,
    timestamp: float,
    stage_id: str,
    buffer_length: int,
) -> None:
    """Store buffer length observations for later analytics."""
    context.raw_data.setdefault("buffer_lengths", []).append(
        {"timestamp": timestamp, "stage_id": stage_id, "buffer_length": buffer_length}
    )


def record_machine_activity(
    context: SimulationContext,
    machine_id: str,
    event_name: str,
    timestamp: float,
    batch_id: str | None,
) -> None:
    """Store machine state changes for later analytics."""
    context.raw_data.setdefault("machine_activity", []).append(
        {
            "timestamp": timestamp,
            "machine_id": machine_id,
            "event": event_name,
            "batch_id": batch_id,
        }
    )
