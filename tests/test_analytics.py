"""Tests for analytics aggregation and scenario comparison."""

from __future__ import annotations

import unittest

from analytics import calculate_analytics, compare_analytics_runs
from engine import SimulationEngine
from scenario import build_scenario, load_config


class AnalyticsTestCase(unittest.TestCase):
    """Covers analytics calculations and scenario comparison output."""

    def test_compare_analytics_runs_returns_required_columns(self) -> None:
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

        comparison_rows = compare_analytics_runs(analytics_runs)

        self.assertEqual(len(comparison_rows), 3)
        self.assertEqual(
            set(comparison_rows[0]),
            {
                "scenario_name",
                "output_units",
                "average_cycle_time",
                "rejection_rate",
                "average_queue_length",
                "average_machine_utilization",
            },
        )
