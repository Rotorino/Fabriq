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
            self.assertTrue(Path(report["files"]["md"]).exists())
            self.assertIsNotNone(report["best_output_scenario"])
            self.assertIsNotNone(report["highest_throughput_scenario"])

    def test_single_report_includes_recommendations(self) -> None:
        from reporting import build_report
        from visualization import build_charts

        scenario = build_scenario(load_config("configs/base_scenario.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=scenario.batches,
            simulation_duration=scenario.scenario_config.simulation_duration,
            scenario_name=scenario.scenario_config.name,
        ).run()
        analytics = calculate_analytics(result)

        with tempfile.TemporaryDirectory() as temp_dir:
            chart_paths = build_charts(result, analytics, Path(temp_dir) / "charts")
            report = build_report(
                result=result,
                analytics=analytics,
                scenario_description="Test scenario",
                output_dir=Path(temp_dir) / "report",
                chart_paths=chart_paths,
            )

            self.assertIn("recommendations", report)
            self.assertIsInstance(report["recommendations"], list)
            self.assertGreater(len(report["recommendations"]), 0)
            self.assertIn("performance_insights", report)
            self.assertIn("efficiency_score", report["performance_insights"])
            self.assertIn("analytics", report)
            self.assertIn("average_queue_length", report["bottleneck"])
            self.assertTrue(Path(report["files"]["md"]).exists())

    def test_charts_generation_creates_all_required_files(self) -> None:
        from visualization import build_charts

        scenario = build_scenario(load_config("configs/base_scenario.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=scenario.batches,
            simulation_duration=scenario.scenario_config.simulation_duration,
            scenario_name=scenario.scenario_config.name,
        ).run()
        analytics = calculate_analytics(result)

        with tempfile.TemporaryDirectory() as temp_dir:
            chart_paths = build_charts(result, analytics, Path(temp_dir) / "charts")

            self.assertEqual(len(chart_paths), 7)
            for path in chart_paths:
                self.assertTrue(path.exists())
                self.assertTrue(path.suffix == ".svg")
