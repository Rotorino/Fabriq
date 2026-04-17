"""Tests for report exporting and scenario comparison reports."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analytics import calculate_analytics
from engine import SimulationEngine
from reporting import build_comparison_report
from scenario import build_scenario, load_config


class ReportingTestCase(unittest.TestCase):
    """Covers reporting outputs required by the project contract."""

    def test_comparison_report_exports_json_csv_and_text(self) -> None:
        analytics_runs = []
        for path in [
            "configs/base_scenario.json",
            "configs/high_load.json",
            "configs/frequent_breakdowns.json",
        ]:
            scenario = build_scenario(load_config(path))
            result = SimulationEngine(
                production_line=scenario.production_line,
                batches=scenario.batches,
                simulation_duration=scenario.scenario_config.simulation_duration,
                scenario_name=scenario.scenario_config.name,
            ).run()
            analytics_runs.append(calculate_analytics(result))

        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_comparison_report(
                analytics_runs,
                Path(temp_dir) / "comparison",
            )

            self.assertEqual(len(report["comparison"]), 3)
            self.assertTrue(Path(report["files"]["json"]).exists())
            self.assertTrue(Path(report["files"]["csv"]).exists())
            self.assertTrue(Path(report["files"]["txt"]).exists())
            self.assertIsNotNone(report["best_output_scenario"])
