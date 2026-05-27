"""Tests for shared domain entities and integration contract."""

from __future__ import annotations

import unittest

from domain.entities import Batch, Buffer, Machine, ProductionLine, Stage
from domain.enums import BatchStatus, MachineStatus


class DomainEntityTestCase(unittest.TestCase):
    """Covers required domain-entity behavior for scenario and engine modules."""

    def test_stage_uses_buffer_entity(self) -> None:
        stage = Stage(
            stage_id="cutting",
            name="Cutting",
            machines=[
                Machine(
                    machine_id="cut-1",
                    name="Machine 1",
                    stage_id="cutting",
                    processing_time=2.0,
                )
            ],
            queue_limit=2,
            buffer_capacity=3,
        )

        self.assertIsInstance(stage.buffer, Buffer)
        self.assertEqual(stage.buffer.capacity, 3)

    def test_batch_state_methods_follow_contract(self) -> None:
        batch = Batch(
            batch_id="b1",
            arrival_time=0.0,
            size=5,
            route=["cutting", "assembly"],
        )

        self.assertEqual(batch.get_current_stage_id(), "cutting")
        self.assertEqual(batch.get_next_stage_id(), "assembly")
        batch.mark_waiting()
        batch.mark_processing()
        next_stage_id = batch.move_to_next_stage()

        self.assertEqual(next_stage_id, "assembly")
        self.assertEqual(batch.status, BatchStatus.WAITING)
        self.assertEqual(batch.get_current_stage_id(), "assembly")
        self.assertIsNone(batch.get_next_stage_id())

    def test_machine_runtime_methods_follow_contract(self) -> None:
        machine = Machine(
            machine_id="m1",
            name="Machine 1",
            stage_id="cutting",
            processing_time=3.0,
            repair_time=2.0,
        )

        machine.start_processing("b1", 5.0)
        self.assertEqual(machine.status, MachineStatus.BUSY)
        self.assertEqual(machine.current_batch_id, "b1")
        self.assertEqual(machine.busy_until, 5.0)

        machine.mark_broken(interrupted_batch_id="b1", repair_finish_time=7.0)
        self.assertEqual(machine.status, MachineStatus.BROKEN)
        self.assertEqual(machine.interrupted_batch_id, "b1")
        self.assertEqual(machine.busy_until, 7.0)

        machine.mark_idle(7.0)
        self.assertEqual(machine.status, MachineStatus.IDLE)
        self.assertIsNone(machine.current_batch_id)
        self.assertIsNone(machine.interrupted_batch_id)

    def test_production_line_exposes_ordered_public_contract(self) -> None:
        cutting = Stage(
            stage_id="cutting",
            name="Cutting",
            machines=[
                Machine(
                    machine_id="cut-1",
                    name="Machine 1",
                    stage_id="cutting",
                    processing_time=2.0,
                )
            ],
            queue_limit=2,
            next_stage_id="assembly",
        )
        assembly = Stage(
            stage_id="assembly",
            name="Assembly",
            machines=[
                Machine(
                    machine_id="asm-1",
                    name="Assembly Machine",
                    stage_id="assembly",
                    processing_time=3.0,
                )
            ],
            queue_limit=2,
        )
        line = ProductionLine(
            stages={"cutting": cutting, "assembly": assembly},
            entry_stage_id="cutting",
        )

        self.assertEqual(line.route_from_entry(), ["cutting", "assembly"])
        self.assertEqual(
            [stage.stage_id for stage in line.ordered_stages()],
            ["cutting", "assembly"],
        )
        self.assertEqual(
            [machine.machine_id for machine in line.all_machines()],
            ["cut-1", "asm-1"],
        )

    def test_production_line_orders_stages_by_route_not_by_dict_insertion(self) -> None:
        assembly = Stage(
            stage_id="assembly",
            name="Assembly",
            machines=[
                Machine(
                    machine_id="asm-1",
                    name="Assembly Machine",
                    stage_id="assembly",
                    processing_time=3.0,
                )
            ],
            queue_limit=2,
        )
        cutting = Stage(
            stage_id="cutting",
            name="Cutting",
            machines=[
                Machine(
                    machine_id="cut-1",
                    name="Machine 1",
                    stage_id="cutting",
                    processing_time=2.0,
                )
            ],
            queue_limit=2,
            next_stage_id="assembly",
        )
        line = ProductionLine(
            stages={"assembly": assembly, "cutting": cutting},
            entry_stage_id="cutting",
        )

        self.assertEqual(line.ordered_stage_ids(), ["cutting", "assembly"])
        self.assertEqual(
            [stage.stage_id for stage in line.ordered_stages()],
            ["cutting", "assembly"],
        )
        self.assertEqual(
            [machine.machine_id for machine in line.all_machines()],
            ["cut-1", "asm-1"],
        )
