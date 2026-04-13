"""CLI entrypoint for the production process simulation application."""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

from analytics import calculate_analytics
from engine import SimulationEngine
from reporting import build_report
from scenario import build_scenario, load_config
from visualization import build_charts

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the application from CLI arguments."""
    args = _parse_args()
    _setup_logging()
    logger.info("Loading config: %s", args.config)
    scenario_input = build_scenario(load_config(args.config))
    rng_seed = args.seed
    if rng_seed is None:
        rng_seed = scenario_input.scenario_config.seed

    result = SimulationEngine(
        production_line=scenario_input.production_line,
        batches=scenario_input.batches,
        simulation_duration=scenario_input.scenario_config.simulation_duration,
        scenario_name=scenario_input.scenario_config.name,
        rng=random.Random(rng_seed),
    ).run()
    analytics = calculate_analytics(result)
    scenario_output_dir = Path(args.results_dir) / result.scenario_name
    chart_paths = build_charts(result, analytics, scenario_output_dir / "charts")
    report = build_report(
        result=result,
        analytics=analytics,
        scenario_description=scenario_input.scenario_config.description,
        output_dir=scenario_output_dir,
        chart_paths=chart_paths,
    )
    logger.info("Simulation report saved: %s", report["files"]["json"])
    print(report["files"]["json"])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run production process simulation scenario."
    )
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--results-dir", default="results", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed override")
    return parser.parse_args()


def _setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "app.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    main()
