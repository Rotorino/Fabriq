"""Main discrete-event simulation engine."""

from __future__ import annotations

import logging
import random
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from domain.entities import Batch, Machine, ProductionLine, Stage

from engine.context import EventLogRecord, SimulationContext
from engine.dispatcher import EventDispatcher
from engine.event_queue import EventQueue
from engine.events import Event, EventType
from engine.handlers import build_default_handlers

logger = logging.getLogger(__name__)
MAX_EVENTS_PER_TIMESTAMP = 100_000


@dataclass(slots=True)
class SimulationResult:
    """Raw simulation output intended for analytics and reporting modules."""

    events: list[Event]
    event_log: list[EventLogRecord]
    batches: list[Batch]
    stages: list[Stage]
    machines: list[Machine]
    simulation_time: float
    scenario_name: str
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def processed_events(self) -> list[Event]:
        """Backward-compatible alias for raw processed events."""
        return self.events


@dataclass(slots=True)
class SimulationEngine:
    """Runs a discrete-event production process simulation."""

    production_line: ProductionLine
    batches: Iterable[Batch]
    simulation_duration: float
    scenario_name: str = "default"
    dispatcher: EventDispatcher | None = None
    rng: random.Random | None = None

    def run(self) -> SimulationResult:
        """Execute the simulation and return raw simulation results."""
        setup_engine_logging()
        logger.info("Simulation started: %s", self.scenario_name)
        if self.simulation_duration < 0:
            raise ValueError("simulation_duration must be non-negative")
        production_line = deepcopy(self.production_line)
        batches = self._prepare_batches(self.batches)
        batch_map = {str(batch.batch_id): batch for batch in batches}
        event_queue = EventQueue()
        context = SimulationContext(
            event_queue=event_queue,
            production_line=production_line,
            batches=batch_map,
        )
        rng = deepcopy(self.rng) if self.rng is not None else random.Random()
        dispatcher = self.dispatcher or EventDispatcher(build_default_handlers(rng))

        self._schedule_initial_events(context)
        stopped_due_to_duration = self._run_loop(context, dispatcher)
        self._finalize(context, dispatcher, stopped_due_to_duration)
        result = self._build_result(context)
        logger.info("Simulation finished: %s", self.scenario_name)
        return result

    @staticmethod
    def _prepare_batches(batches: Iterable[Batch]) -> list[Batch]:
        """Clone, validate, and sort batches before scheduling initial events."""
        prepared_batches = deepcopy(list(batches))
        seen_batch_ids: set[str] = set()
        for batch in prepared_batches:
            batch_id = str(getattr(batch, "batch_id"))
            if batch_id in seen_batch_ids:
                raise ValueError(f"Duplicate batch_id in simulation input: {batch_id}")
            seen_batch_ids.add(batch_id)
        prepared_batches.sort(
            key=lambda batch: (float(getattr(batch, "arrival_time")), str(batch.batch_id))
        )
        return prepared_batches

    def _schedule_initial_events(self, context: SimulationContext) -> None:
        for batch in context.batches.values():
            context.event_queue.push(
                Event(
                    timestamp=float(getattr(batch, "arrival_time")),
                    event_type=EventType.BATCH_ARRIVAL,
                    batch_id=str(batch.batch_id),
                )
            )

    def _run_loop(
        self,
        context: SimulationContext,
        dispatcher: EventDispatcher,
    ) -> bool:
        stopped_due_to_duration = False
        last_timestamp: float | None = None
        same_timestamp_event_count = 0
        while not context.event_queue.is_empty() and not context.stopped:
            if context.event_queue.peek().timestamp > self.simulation_duration:
                stopped_due_to_duration = True
                break
            event = context.event_queue.pop()
            if last_timestamp == event.timestamp:
                same_timestamp_event_count += 1
            else:
                last_timestamp = event.timestamp
                same_timestamp_event_count = 1
            if same_timestamp_event_count > MAX_EVENTS_PER_TIMESTAMP:
                raise RuntimeError(
                    "Simulation exceeded safe event count without time progress; "
                    "check for a zero-duration event cycle"
                )
            context.current_time = event.timestamp
            dispatcher.dispatch(event, context)
        return stopped_due_to_duration

    def _finalize(
        self,
        context: SimulationContext,
        dispatcher: EventDispatcher,
        stopped_due_to_duration: bool,
    ) -> None:
        if context.stopped:
            return
        if stopped_due_to_duration:
            end_time = float(self.simulation_duration)
        else:
            end_time = float(context.current_time)
        context.current_time = end_time
        dispatcher.dispatch(
            Event(
                timestamp=end_time,
                event_type=EventType.SIMULATION_END,
            ),
            context,
        )

    def _build_result(self, context: SimulationContext) -> SimulationResult:
        stages = list_stages(context.production_line)
        if hasattr(context.production_line, "all_machines"):
            machines = context.production_line.all_machines()
        else:
            machines = [machine for stage in stages for machine in getattr(stage, "machines", [])]
        return SimulationResult(
            events=list(context.processed_events),
            event_log=list(context.event_log),
            batches=list(context.batches.values()),
            stages=stages,
            machines=machines,
            simulation_time=context.current_time,
            scenario_name=self.scenario_name,
            raw_data={
                key: value
                for key, value in context.raw_data.items()
                if not key.startswith("_")
            },
        )


def list_stages(production_line: ProductionLine | Any) -> list[Stage | Any]:
    """Return production line stages as a list."""
    if hasattr(production_line, "ordered_stages"):
        return production_line.ordered_stages()
    stages = getattr(production_line, "stages", production_line)
    if isinstance(stages, dict):
        return list(stages.values())
    return list(stages)


def setup_engine_logging(log_path: Path = Path("logs/simulation.log")) -> None:
    """Configure file logging for the simulation engine."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    if any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_path.resolve()
        for handler in root_logger.handlers
    ):
        return
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
