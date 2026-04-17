"""Tests for scenario configuration loading and validation."""

from __future__ import annotations

import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

from scenario.config_loader import ConfigurationError, load_config
from scenario.line_builder import build_batches, build_production_line, build_scenario


class ScenarioTestCase(unittest.TestCase):
    """Covers scenario loader, validator, and builder behavior."""

    def test_load_valid_json_and_build_line(self) -> None:
        scenario = build_scenario(load_config("configs/base_scenario.json"))

        self.assertEqual(scenario.scenario_config.name, "base_scenario")
        self.assertEqual(len(scenario.production_line.stages), 3)
        self.assertEqual(len(scenario.batches), 12)
        self.assertEqual(scenario.production_line.entry_stage_id, "cutting")
        self.assertEqual(
            scenario.scenario_config.batch_generation_mode,
            "equal_intervals",
        )

    def test_invalid_probability_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"][0]["reject_probability"] = 2.0

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_non_numeric_probability_is_rejected_with_configuration_error(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"][0]["reject_probability"] = "oops"

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_boolean_numeric_fields_are_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["simulation_duration"] = True

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_boolean_seed_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["seed"] = True

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_missing_simulation_duration_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        del config["simulation_duration"]

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_unknown_route_stage_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["batches"]["route"] = ["missing"]

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_unknown_next_stage_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"][0]["next_stage_id"] = "missing-stage"

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_random_generation_is_repeatable_with_seed(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["seed"] = 123
        config["batches"] = {
            "mode": "random_intervals",
            "count": 5,
            "size": 3,
            "mean_interval": 2.0,
            "route": ["cutting", "assembly", "quality"],
        }
        line = build_production_line(config)

        first = build_batches(config, line)
        second = build_batches(config, line)

        self.assertEqual(
            [batch.arrival_time for batch in first],
            [batch.arrival_time for batch in second],
        )
        self.assertEqual(
            [batch.batch_id for batch in first],
            [batch.batch_id for batch in second],
        )

    def test_yaml_config_is_supported(self) -> None:
        if find_spec("yaml") is None:
            self.skipTest("PyYAML is not installed in the current environment")
        yaml_config = """
scenario_name: yaml_scenario
description: YAML scenario
simulation_duration: 10
seed: 42
stages:
  - stage_id: cutting
    name: Cutting
    queue_limit: 2
    buffer_capacity: 1
    reject_probability: 0.0
    next_stage_id: null
    machines:
      - machine_id: cut-1
        processing_time: 1.5
        breakdown_probability: 0.0
        repair_time: 0.0
batches:
  mode: template
  count: 3
  size: 2
  arrival_interval: 1.0
  route: [cutting]
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scenario.yaml"
            path.write_text(yaml_config, encoding="utf-8")
            scenario = build_scenario(load_config(path))

        self.assertEqual(scenario.scenario_config.name, "yaml_scenario")
        self.assertEqual(len(scenario.batches), 3)

    def test_production_line_builder_populates_stage_fields(self) -> None:
        config = load_config("configs/base_scenario.json")
        line = build_production_line(config)
        cutting = line.get_stage("cutting")

        self.assertEqual(cutting.name, "Cutting")
        self.assertEqual(cutting.next_stage_id, "assembly")
        self.assertEqual(len(cutting.machines), 1)
        self.assertEqual(cutting.machines[0].stage_id, "cutting")
        self.assertEqual(cutting.buffer.capacity, 2)
        self.assertEqual(line.route_from_entry(), ["cutting", "assembly", "quality"])

    def test_default_route_follows_stage_links_not_stage_definition_order(self) -> None:
        config = {
            "scenario_name": "out_of_order",
            "simulation_duration": 10,
            "stages": [
                {
                    "stage_id": "assembly",
                    "name": "Assembly",
                    "next_stage_id": None,
                    "machines": [
                        {
                            "machine_id": "asm-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
                {
                    "stage_id": "cutting",
                    "name": "Cutting",
                    "next_stage_id": "assembly",
                    "machines": [
                        {
                            "machine_id": "cut-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
            ],
            "batches": {"mode": "equal_intervals", "count": 1, "size": 1},
        }

        scenario = build_scenario(config)

        self.assertEqual(scenario.production_line.entry_stage_id, "cutting")
        self.assertEqual(scenario.batches[0].route, ["cutting", "assembly"])

    def test_non_integer_queue_limit_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"][0]["queue_limit"] = 0.5

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_invalid_stage_type_is_rejected_as_configuration_error(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"][0]["stage_type"] = "weird"

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_unreachable_cyclic_stage_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"].append(
            {
                "stage_id": "packaging",
                "name": "Packaging",
                "next_stage_id": "packaging",
                "machines": [
                    {
                        "machine_id": "pkg-1",
                        "processing_time": 1.0,
                        "repair_time": 0.0,
                        "breakdown_probability": 0.0,
                    }
                ],
            }
        )

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_multiple_entry_stages_require_explicit_route(self) -> None:
        config = {
            "scenario_name": "multi_entry",
            "simulation_duration": 10,
            "stages": [
                {
                    "stage_id": "cutting",
                    "name": "Cutting",
                    "next_stage_id": "assembly",
                    "machines": [
                        {
                            "machine_id": "cut-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
                {
                    "stage_id": "painting",
                    "name": "Painting",
                    "next_stage_id": "assembly",
                    "machines": [
                        {
                            "machine_id": "paint-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
                {
                    "stage_id": "assembly",
                    "name": "Assembly",
                    "machines": [
                        {
                            "machine_id": "asm-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
            ],
            "batches": {"mode": "equal_intervals", "count": 1, "size": 1},
        }

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_multiple_entry_stages_are_supported_with_explicit_route(self) -> None:
        config = {
            "scenario_name": "multi_entry",
            "simulation_duration": 10,
            "stages": [
                {
                    "stage_id": "cutting",
                    "name": "Cutting",
                    "next_stage_id": "assembly",
                    "machines": [
                        {
                            "machine_id": "cut-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
                {
                    "stage_id": "painting",
                    "name": "Painting",
                    "next_stage_id": "assembly",
                    "machines": [
                        {
                            "machine_id": "paint-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
                {
                    "stage_id": "assembly",
                    "name": "Assembly",
                    "machines": [
                        {
                            "machine_id": "asm-1",
                            "processing_time": 1.0,
                            "repair_time": 0.0,
                            "breakdown_probability": 0.0,
                        }
                    ],
                },
            ],
            "batches": {
                "mode": "equal_intervals",
                "count": 1,
                "size": 1,
                "route": ["painting", "assembly"],
            },
        }

        scenario = build_scenario(config)

        self.assertEqual(sorted(scenario.production_line.entry_stage_ids), ["cutting", "painting"])
        self.assertIsNone(scenario.production_line.entry_stage_id)
        self.assertEqual(scenario.batches[0].route, ["painting", "assembly"])

    def test_fixed_batches_require_unique_ids(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["batches"] = {
            "mode": "fixed",
            "items": [
                {
                    "batch_id": "dup",
                    "arrival_time": 0.0,
                    "size": 1,
                    "route": ["cutting", "assembly", "quality"],
                },
                {
                    "batch_id": "dup",
                    "arrival_time": 1.0,
                    "size": 1,
                    "route": ["cutting", "assembly", "quality"],
                },
            ],
        }

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_fixed_batches_can_inherit_size_from_parent_batches_config(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["batches"] = {
            "mode": "fixed",
            "size": 5,
            "items": [
                {
                    "batch_id": "batch-a",
                    "arrival_time": 0.0,
                    "route": ["cutting", "assembly", "quality"],
                }
            ],
        }

        scenario = build_scenario(config)

        self.assertEqual(scenario.batches[0].size, 5)

    def test_three_required_scenarios_are_valid(self) -> None:
        for path in [
            "configs/base_scenario.json",
            "configs/high_load.json",
            "configs/frequent_breakdowns.json",
        ]:
            with self.subTest(path=path):
                scenario = build_scenario(load_config(path))
                self.assertGreater(len(scenario.batches), 0)
