"""Tests for analytics aggregation and scenario comparison."""

from __future__ import annotations

import unittest

from analytics import (
    calculate_analytics,
    compare_analytics_runs,
    events_by_batch,
    events_by_machine,
    events_by_stage,
    events_by_time,
)
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
        self.assertIn("scenario_name", comparison_rows[0])
        self.assertIn("output_units", comparison_rows[0])
        self.assertIn("average_cycle_time", comparison_rows[0])
        self.assertIn("rejection_rate", comparison_rows[0])
        self.assertIn("average_queue_length", comparison_rows[0])
        self.assertIn("average_wait_time", comparison_rows[0])
        self.assertIn("average_machine_utilization", comparison_rows[0])
        self.assertIn("throughput", comparison_rows[0])
        self.assertIn("total_breakdowns", comparison_rows[0])
        self.assertIn("completion_rate", comparison_rows[0])

    def test_calculate_analytics_includes_extended_metrics(self) -> None:
        scenario = build_scenario(load_config("configs/base_scenario.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=scenario.batches,
            simulation_duration=scenario.scenario_config.simulation_duration,
            scenario_name=scenario.scenario_config.name,
        ).run()
        analytics = calculate_analytics(result)

        self.assertIn("throughput", analytics["general"])
        self.assertIn("rejected_units", analytics["general"])
        self.assertIn("total_breakdowns", analytics["general"])
        self.assertIn("total_repair_time", analytics["general"])
        self.assertIn("average_cycle_time", analytics["general"])
        self.assertIn("completion_rate", analytics["general"])
        self.assertGreaterEqual(analytics["general"]["throughput"], 0.0)
        self.assertIn("average_queue_length", analytics["stages"][0])
        self.assertIn("downtime_time", analytics["stages"][0])
        self.assertIn("downtime_time", analytics["machines"][0])
        self.assertIn("queue_wait_time", analytics["batches"][0])
        self.assertIn("status", analytics["batches"][0])

    def test_analytics_handles_zero_batches(self) -> None:
        scenario = build_scenario(load_config("configs/base_scenario.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=[],
            simulation_duration=10.0,
            scenario_name="empty_test",
        ).run()
        analytics = calculate_analytics(result)

        self.assertEqual(analytics["general"]["total_batches"], 0)
        self.assertEqual(analytics["general"]["output_units"], 0)
        self.assertEqual(analytics["general"]["throughput"], 0.0)
        self.assertEqual(analytics["general"]["completion_rate"], 0.0)

    def test_aggregators_group_events_by_operational_dimension(self) -> None:
        scenario = build_scenario(load_config("configs/base_scenario.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=scenario.batches,
            simulation_duration=scenario.scenario_config.simulation_duration,
            scenario_name=scenario.scenario_config.name,
        ).run()

        by_time = events_by_time(result.event_log)
        by_stage = events_by_stage(result.event_log)
        by_machine = events_by_machine(result.event_log)
        by_batch = events_by_batch(result.event_log)

        self.assertGreater(len(by_time), 0)
        self.assertLessEqual(by_time[0].timestamp, by_time[-1].timestamp)
        self.assertGreater(len(by_stage), 0)
        self.assertGreater(len(by_machine), 0)
        self.assertEqual(len(by_batch), len(result.batches))

    def test_average_queue_length_is_reported_for_loaded_scenario(self) -> None:
        scenario = build_scenario(load_config("configs/high_load.json"))
        result = SimulationEngine(
            production_line=scenario.production_line,
            batches=scenario.batches,
            simulation_duration=scenario.scenario_config.simulation_duration,
            scenario_name=scenario.scenario_config.name,
        ).run()

        analytics = calculate_analytics(result)
        stage_rows = {row["stage_id"]: row for row in analytics["stages"]}

        self.assertGreaterEqual(stage_rows["cutting"]["average_queue_length"], 0.0)
        self.assertGreaterEqual(stage_rows["assembly"]["average_queue_length"], 0.0)
        self.assertGreaterEqual(stage_rows["cutting"]["max_queue_length"], 0)
