"""End-to-end tests for simulation, analytics, reports, and charts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analytics import calculate_analytics
from engine import SimulationEngine
from reporting import build_report
from scenario import build_scenario, load_config
from visualization import build_charts


class IntegrationTestCase(unittest.TestCase):
    """Covers a full scenario run without invoking a shell."""

    def test_full_pipeline_exports_reports_and_charts(self) -> None:
        scenario = build_scenario(load_config("configs/base_scenario.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=scenario.batches,
            simulation_duration=scenario.scenario_config.simulation_duration,
            scenario_name=scenario.scenario_config.name,
        ).run()
        analytics = calculate_analytics(result)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            chart_paths = build_charts(result, analytics, output_dir / "charts")
            report = build_report(
                result=result,
                analytics=analytics,
                scenario_description=scenario.scenario_config.description,
                output_dir=output_dir,
                chart_paths=chart_paths,
            )

            self.assertEqual(len(chart_paths), 3)
            self.assertTrue(Path(report["files"]["json"]).exists())
            self.assertTrue(Path(report["files"]["csv"]).exists())
            self.assertTrue(Path(report["files"]["txt"]).exists())
            self.assertGreater(analytics["general"]["total_batches"], 0)

    def test_all_required_scenarios_run_without_crashing(self) -> None:
        for path in [
            "configs/base_scenario.json",
            "configs/high_load.json",
            "configs/frequent_breakdowns.json",
        ]:
            with self.subTest(path=path):
                scenario = build_scenario(load_config(path))
                result = SimulationEngine(
                    production_line=scenario.production_line,
                    batches=scenario.batches,
                    simulation_duration=scenario.scenario_config.simulation_duration,
                    scenario_name=scenario.scenario_config.name,
                ).run()
                analytics = calculate_analytics(result)
                self.assertIn("general", analytics)
                self.assertEqual(result.scenario_name, scenario.scenario_config.name)
