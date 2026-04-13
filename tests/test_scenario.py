"""Tests for scenario configuration loading and validation."""

from __future__ import annotations

import unittest

from scenario.config_loader import ConfigurationError, load_config
from scenario.line_builder import build_scenario


class ScenarioTestCase(unittest.TestCase):
    """Covers scenario loader, validator, and builder behavior."""

    def test_load_valid_json_and_build_line(self) -> None:
        scenario = build_scenario(load_config("configs/base_scenario.json"))

        self.assertEqual(scenario.scenario_config.name, "base_scenario")
        self.assertEqual(len(scenario.production_line.stages), 3)
        self.assertEqual(len(scenario.batches), 12)

    def test_invalid_probability_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["stages"][0]["reject_probability"] = 2.0

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_unknown_route_stage_is_rejected(self) -> None:
        config = load_config("configs/base_scenario.json")
        config["batches"]["route"] = ["missing"]

        with self.assertRaises(ConfigurationError):
            build_scenario(config)

    def test_three_required_scenarios_are_valid(self) -> None:
        for path in [
            "configs/base_scenario.json",
            "configs/high_load.json",
            "configs/frequent_breakdowns.json",
        ]:
            with self.subTest(path=path):
                scenario = build_scenario(load_config(path))
                self.assertGreater(len(scenario.batches), 0)
