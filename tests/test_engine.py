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
    buffer: list[str] = field(default_factory=list)


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

        self.assertEqual(result.batches[0].status, "completed")
        self.assertEqual(result.simulation_time, 5.0)
        self.assertEqual(
            [record.result for record in result.event_log].count("batch_completed"),
            1,
        )
        self.assertTrue(all(machine.status == "idle" for machine in result.machines))
        self.assertEqual(batch.status, "new")
        self.assertEqual(batch.current_stage_index, 0)
        self.assertEqual(line.stages["s1"].queue, [])

    def test_engine_does_not_mutate_input_model_between_runs(self) -> None:
        line = make_line()
        batches = [
            FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1", "s2"]),
            FakeBatch(batch_id="b2", arrival_time=1.0, route=["s1", "s2"]),
        ]
        engine = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=20.0,
            rng=random.Random(1),
        )

        first = engine.run()
        second = engine.run()

        self.assertEqual(len(first.events), len(second.events))
        self.assertEqual(
            [record.result for record in first.event_log],
            [record.result for record in second.event_log],
        )
        self.assertEqual([batch.status for batch in batches], ["new", "new"])
        self.assertEqual(
            [batch.current_stage_index for batch in batches],
            [0, 0],
        )
        self.assertTrue(
            all(machine.status == "idle" for machine in line.stages["s1"].machines)
        )
        self.assertEqual(line.stages["s1"].queue, [])

    def test_engine_rejects_duplicate_batch_ids(self) -> None:
        line = make_line()
        batches = [
            FakeBatch(batch_id="dup", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="dup", arrival_time=1.0, route=["s1"]),
        ]

        with self.assertRaises(ValueError):
            SimulationEngine(
                production_line=line,
                batches=batches,
                simulation_duration=10.0,
                rng=random.Random(1),
            ).run()

    def test_initial_events_are_sorted_by_arrival_time_then_batch_id(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=1.0)],
        )
        line = FakeLine(stages={"s1": stage})
        batches = [
            FakeBatch(batch_id="b2", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="a1", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="c3", arrival_time=2.0, route=["s1"]),
        ]

        result = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        arrival_batch_ids = [
            record.batch_id
            for record in result.event_log
            if record.result == "arrival_registered"
        ]
        self.assertEqual(arrival_batch_ids, ["a1", "b2", "c3"])

    def test_processing_finish_at_simulation_duration_is_processed(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(machine_id="m1", stage_id="s1", processing_time=10.0),
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(result.batches[0].status, "completed")
        self.assertEqual(result.event_log[-1].event_type, EventType.SIMULATION_END.value)
        self.assertIn(
            "processing_finished",
            [record.result for record in result.event_log],
        )
        self.assertEqual(result.simulation_time, 10.0)

    def test_simulation_ends_at_last_processed_event_when_queue_is_empty(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(machine_id="m1", stage_id="s1", processing_time=1.0),
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(result.simulation_time, 1.0)
        self.assertEqual(result.event_log[-1].timestamp, 1.0)
        self.assertEqual(result.event_log[-1].event_type, EventType.SIMULATION_END.value)

    def test_simulation_stops_at_duration_when_next_event_is_in_future(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(machine_id="m1", stage_id="s1", processing_time=1.0),
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=15.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(result.simulation_time, 10.0)
        self.assertEqual(
            [record.result for record in result.event_log],
            ["simulation_stopped"],
        )
        self.assertEqual(result.batches[0].status, "new")

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

        self.assertEqual(
            [batch.status for batch in result.batches],
            ["completed", "completed"],
        )
        processing_starts = [
            record
            for record in result.event_log
            if record.result == "processing_started"
        ]
        self.assertEqual(processing_starts[0].timestamp, 0.0)
        self.assertEqual(processing_starts[1].timestamp, 5.0)
        self.assertIn(
            {"timestamp": 0.0, "stage_id": "s1", "queue_length": 1},
            result.raw_data["queue_lengths"],
        )
        self.assertEqual(result.stages[0].queue, [])
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

        self.assertEqual(
            [batch.status for batch in result.batches],
            ["completed", "completed"],
        )
        self.assertNotIn("queue_full", [record.result for record in result.event_log])

    def test_queue_limit_zero_starts_processing_when_machine_is_free(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=2.0)],
            queue_limit=0,
            buffer_capacity=0,
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(result.batches[0].status, "completed")
        self.assertIn(
            "processing_started",
            [record.result for record in result.event_log],
        )
        self.assertNotIn(
            "buffer_full_marked_for_rejection",
            [record.result for record in result.event_log],
        )

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
            record
            for record in result.event_log
            if record.result == "processing_started"
        ]
        self.assertEqual(len(processing_starts), 2)
        self.assertEqual(
            {record.batch_id for record in processing_starts},
            {"b1", "b2"},
        )
        self.assertEqual(
            {record.machine_id for record in processing_starts},
            {"m1", "m2"},
        )
        self.assertTrue(all(batch.status == "completed" for batch in result.batches))

    def test_machine_breakdown_requeues_and_completes_batch_after_repair(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(
                    machine_id="m1",
                    stage_id="s1",
                    processing_time=4.0,
                    breakdown_probability=0.5,
                    repair_time=3.0,
                )
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=8.0,
            rng=random.Random(1),
        ).run()

        results = [record.result for record in result.event_log]
        self.assertIn("machine_broken", results)
        self.assertIn("repair_finished", results)
        self.assertEqual(result.batches[0].status, "completed")
        self.assertEqual(result.machines[0].status, "idle")
        self.assertIsNone(result.machines[0].interrupted_batch_id)

    def test_interrupted_batch_can_resume_on_another_machine_before_repair_finishes(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(
                    machine_id="m1",
                    stage_id="s1",
                    processing_time=4.0,
                    breakdown_probability=1.0,
                    repair_time=5.0,
                ),
                FakeMachine(
                    machine_id="m2",
                    stage_id="s1",
                    processing_time=4.0,
                    breakdown_probability=0.0,
                    repair_time=0.0,
                ),
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        processing_starts = [
            record
            for record in result.event_log
            if record.result == "processing_started"
        ]
        self.assertEqual(result.batches[0].status, "completed")
        self.assertEqual(result.simulation_time, 7.0)
        self.assertEqual(
            [(record.timestamp, record.machine_id) for record in processing_starts],
            [(0.0, "m1"), (2.0, "m2")],
        )
        self.assertEqual(
            [record.result for record in result.event_log].count("batch_completed"),
            1,
        )
        self.assertLess(
            next(
                record.timestamp
                for record in result.event_log
                if record.result == "batch_completed"
            ),
            next(
                record.timestamp
                for record in result.event_log
                if record.result == "repair_finished"
            ),
        )

    def test_full_queue_sends_batch_to_buffer_then_processes_it(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=4.0)],
            queue_limit=1,
            buffer_capacity=2,
        )
        line = FakeLine(stages={"s1": stage})
        batches = [
            FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b2", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b3", arrival_time=0.0, route=["s1"]),
        ]

        result = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=20.0,
            rng=random.Random(1),
        ).run()

        results = [record.result for record in result.event_log]
        self.assertIn("buffered", results)
        self.assertEqual([batch.status for batch in result.batches], ["completed"] * 3)
        self.assertEqual(result.stages[0].queue, [])
        self.assertEqual(result.stages[0].buffer, [])
        self.assertEqual(stage.queue, [])
        self.assertEqual(stage.buffer, [])
        self.assertIn(
            {"timestamp": 0.0, "stage_id": "s1", "buffer_length": 1},
            result.raw_data["buffer_lengths"],
        )

    def test_full_queue_and_full_buffer_rejects_batch(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[FakeMachine(machine_id="m1", stage_id="s1", processing_time=4.0)],
            queue_limit=1,
            buffer_capacity=0,
        )
        line = FakeLine(stages={"s1": stage})
        batches = [
            FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b2", arrival_time=0.0, route=["s1"]),
            FakeBatch(batch_id="b3", arrival_time=0.0, route=["s1"]),
        ]

        result = SimulationEngine(
            production_line=line,
            batches=batches,
            simulation_duration=20.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(
            [batch.status for batch in result.batches],
            ["completed", "completed", "rejected"],
        )
        self.assertTrue(result.batches[2].is_rejected)
        self.assertIn(
            "buffer_full_marked_for_rejection",
            [record.result for record in result.event_log],
        )

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

        self.assertEqual(result.batches[0].status, "rejected")
        self.assertTrue(result.batches[0].is_rejected)
        self.assertIn("batch_rejected", [record.result for record in result.event_log])

    def test_result_keeps_raw_events_and_processed_event_log(self) -> None:
        line = make_line()
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=10.0,
            rng=random.Random(1),
        ).run()

        self.assertTrue(all(hasattr(event, "payload") for event in result.processed_events))
        self.assertTrue(all(hasattr(record, "result") for record in result.event_log))
        self.assertTrue(all(hasattr(event, "event_type") for event in result.events))
        self.assertFalse(any(hasattr(event, "result") for event in result.events))
        self.assertEqual(result.events[0].event_type, EventType.BATCH_ARRIVAL)

    def test_machine_can_break_multiple_times_while_resuming_same_batch(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(
                    machine_id="m1",
                    stage_id="s1",
                    processing_time=4.0,
                    breakdown_probability=1.0,
                    repair_time=1.0,
                )
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=20.0,
            rng=random.Random(1),
        ).run()

        self.assertGreaterEqual(
            [record.result for record in result.event_log].count("machine_broken"),
            2,
        )

    def test_zero_duration_processing_does_not_create_breakdown_loop(self) -> None:
        stage = FakeStage(
            stage_id="s1",
            machines=[
                FakeMachine(
                    machine_id="m1",
                    stage_id="s1",
                    processing_time=0.0,
                    breakdown_probability=1.0,
                    repair_time=0.0,
                )
            ],
        )
        line = FakeLine(stages={"s1": stage})
        batch = FakeBatch(batch_id="b1", arrival_time=0.0, route=["s1"])

        result = SimulationEngine(
            production_line=line,
            batches=[batch],
            simulation_duration=1.0,
            rng=random.Random(1),
        ).run()

        self.assertEqual(result.batches[0].status, "completed")
        self.assertEqual(
            [record.result for record in result.event_log].count("machine_broken"),
            0,
        )
        self.assertLess(len(result.event_log), 10)


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
