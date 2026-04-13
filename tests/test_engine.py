"""Tests for the discrete-event simulation engine."""

from __future__ import annotations

import random
import unittest
from dataclasses import dataclass, field

from engine import Event, EventQueue, EventType, SimulationEngine


@dataclass
class FakeBatch:
    batch_id: str
    arrival_time: float
    route: list[str]
    size: int = 1
    current_stage_index: int = 0
    status: str = "new"
    is_rejected: bool = False


@dataclass
class FakeMachine:
    machine_id: str
    stage_id: str
    processing_time: float
    breakdown_probability: float = 0.0
    repair_time: float = 0.0
    status: str = "idle"
    busy_until: float = 0.0
    current_batch_id: str | None = None
    interrupted_batch_id: str | None = None


@dataclass
class FakeStage:
    stage_id: str
    machines: list[FakeMachine]
    queue_limit: int = 10
    reject_probability: float = 0.0
    buffer_capacity: int = 10
    next_stage_id: str | None = None
    queue: list[str] = field(default_factory=list)


@dataclass
class FakeLine:
    stages: dict[str, FakeStage]


class EngineTestCase(unittest.TestCase):
    """Covers required simulation engine behavior."""

    def test_event_queue_orders_by_time_and_keeps_fifo_for_equal_time(self) -> None:
        queue = EventQueue()
        first = Event(timestamp=2.0, event_type=EventType.BATCH_ARRIVAL, batch_id="b1")
        second = Event(timestamp=1.0, event_type=EventType.BATCH_ARRIVAL, batch_id="b2")
        third = Event(timestamp=1.0, event_type=EventType.BATCH_ARRIVAL, batch_id="b3")

        queue.push(first)
        queue.push(second)
        queue.push(third)

        self.assertIs(queue.pop(), second)
        self.assertIs(queue.pop(), third)
        self.assertIs(queue.pop(), first)
        self.assertTrue(queue.is_empty())

    def test_event_queue_raises_for_empty_pop(self) -> None:
        with self.assertRaises(IndexError):
            EventQueue().pop()

    def test_batch_passes_through_multiple_stages(self) -> None:
        line = make_line()
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1", "s2"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=20.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(batch.status, "completed")
        self.assertEqual(result.simulation_time, 20.0)
        self.assertEqual(
            [record.result for record in result.events].count("batch_completed"),
            1,
        )
        self.assertTrue(all(machine.status == "idle" for machine in result.machines))

    def test_processing_finish_at_simulation_duration_is_processed(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=10.0)],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(batch.status, "completed")
        self.assertEqual(result.events[-1].event_type, EventType.SIMULATION_END.value)
        self.assertIn("processing_finished", [record.result for record in result.events])

    def test_batch_waits_when_machine_is_busy(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=5.0)],
        )
        line = FakeLine(stages={"s1": stage})
        batches = [
            FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b2", arrival_time=0.0, route=["s1"]),
        ]

        result = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=20.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual([batch.status for batch in batches], ["completed", "completed"])
        processing_starts = [
            record for record in result.events if record.result == "processing_started"
        ]
        self.assertEqual(processing_starts[0].timestamp, 0.0)
        self.assertEqual(processing_starts[1].timestamp, 5.0)
        self.assertIn(
            {"timestamp": 0.0, "stage_id": "s1", "queue_length": 1},
            result.raw_data["queue_lengths"],
        )
        self.assertEqual(stage.queue, [])

    def test_queue_limit_ignores_batch_reserved_for_processing_start(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=5.0)],
            queue_limit=1,
        )
        line = FakeLine(stages={"s1": stage})
        batches = [
            FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b2", arrival_time=0.0, route=["s1"]),
        ]

        result = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=20.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual([batch.status for batch in batches], ["completed", "completed"])
        self.assertNotIn("queue_full", [record.result for record in result.events])

    def test_parallel_machines_start_different_batches(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(machine_id="m1", stage_id="s1", processing_time=5.0),
                FakeMachine(machine_id="m2", stage_id="s1", processing_time=5.0),
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batches = [
            FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b2", arrival_time=0.0, route=["s1"]),
        ]

        result = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        processing_starts = [
            record for record in result.events if record.result == "processing_started"
        ]
        self.assertEqual(len(processing_starts), 2)
        self.assertEqual({record.batch_id for record in processing_starts}, {"b1", "b2"})
        self.assertEqual({record.machine_id for record in processing_starts}, {"m1", "m2"})
        self.assertTrue(all(batch.status == "completed" for batch in batches))

    def test_machine_breakdown_requeues_batch_after_repair(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(
                    machine_id="m1",
                    stage_id="s1",
                    processing_time=4.0,
                    breakdown_probability=1.0,
                    repair_time=3.0,
                )
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=6.0,
            rng=random.Random(1),
        ).run()

        results = [record.result for record in result.events]
        self.assertIn("machine_broken", results)
        self.assertIn("repair_finished", results)
        self.assertEqual(batch.status, "waiting")
        self.assertEqual(stage.machines[0].status, "broken")
        self.assertEqual(stage.machines[0].interrupted_batch_id, "b1")

    def test_batch_rejection_stops_route(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(machine_id="m1", stage_id="s1", processing_time=1.0),
            ],
            reject_probability=1.0,
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(batch.status, "rejected")
        self.assertTrue(batch.is_rejected)
        self.assertIn("batch_rejected", [record.result for record in result.events])


def make_line() -> FakeLine:
    """Create a two-stage test production line."""
    first_stage = FakeStage(
        stage_id="s1",
        machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=2.0)],
        next_stage_id="s2",
    )
    second_stage = FakeStage(
        stage_id="s2",
        machines=[FakeMachine(machine_id="m2", stage_id="s2", processing_time=3.0)],
    )
    return FakeLine(stages={"s1": first_stage, "s2": second_stage})
