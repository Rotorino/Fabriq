"""Main discrete-event simulation engine."""

from __future__ import annotations

import logging
import random
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from engine.context import EventLogRecord, SimulationContext
from engine.dispatcher import EventDispatcher
from engine.event_queue import EventQueue
from engine.events import Event, EventType
from engine.handlers import build_default_handlers

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SimulationResult:
    """Raw simulation output intended for analytics and reporting modules."""

    events: list[EventLogRecord]
    batches: list[Any]
    stages: list[Any]
    machines: list[Any]
    simulation_time: float
    scenario_name: str
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationEngine:
    """Runs a discrete-event production process simulation."""

    production_line: Any
    batches: Iterable[Any]
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
        batches = deepcopy(list(self.batches))
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
        self._run_loop(context, dispatcher)
        self._stop_at_duration(context, dispatcher)
        result = self._build_result(context)
        logger.info("Simulation finished: %s", self.scenario_name)
        return result

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
    ) -> None:
        while not context.event_queue.is_empty() and not context.stopped:
            event = context.event_queue.pop()
            if event.timestamp > self.simulation_duration:
                break
            context.current_time = event.timestamp
            dispatcher.dispatch(event, context)

    def _stop_at_duration(
        self,
        context: SimulationContext,
        dispatcher: EventDispatcher,
    ) -> None:
        if context.stopped:
            return
        context.current_time = float(self.simulation_duration)
        dispatcher.dispatch(
            Event(
                timestamp=float(self.simulation_duration),
                event_type=EventType.SIMULATION_END,
            ),
            context,
        )

    def _build_result(self, context: SimulationContext) -> SimulationResult:
        stages = list_stages(context.production_line)
        machines = [
            machine for stage in stages for machine in getattr(stage, "machines", [])
        ]
        return SimulationResult(
            events=list(context.event_log),
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


def list_stages(production_line: Any) -> list[Any]:
    """Return production line stages as a list."""
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
