"""CLI entrypoint for the production process simulation application."""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path
from typing import Any

from analytics import calculate_analytics
from engine import SimulationEngine
from reporting import build_comparison_report, build_report
from scenario import build_scenario, load_config
from visualization import build_charts

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the application from CLI arguments."""
    args = _parse_args()
    _setup_logging()
    run_outputs = [_run_single_config(config_path, args.results_dir, args.seed) for config_path in args.config]
    if len(run_outputs) == 1:
        report = run_outputs[0]["report"]
        logger.info("Simulation report saved: %s", report["files"]["json"])
        print(report["files"]["json"])
        return

    comparison_report = build_comparison_report(
        [output["analytics"] for output in run_outputs],
        Path(args.results_dir) / "comparison",
    )
    logger.info("Comparison report saved: %s", comparison_report["files"]["json"])
    print(comparison_report["files"]["json"])


def _run_single_config(
    config_path: str,
    results_dir: str,
    seed_override: int | None,
) -> dict[str, Any]:
    """Run one scenario configuration and export its outputs."""
    logger.info("Loading config: %s", config_path)
    scenario_input = build_scenario(load_config(config_path))
    rng_seed = seed_override
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
    scenario_output_dir = Path(results_dir) / result.scenario_name
    chart_paths = build_charts(result, analytics, scenario_output_dir / "charts")
    report = build_report(
        result=result,
        analytics=analytics,
        scenario_description=scenario_input.scenario_config.description,
        output_dir=scenario_output_dir,
        chart_paths=chart_paths,
    )
    return {"result": result, "analytics": analytics, "report": report}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run production process simulation scenario."
    )
    parser.add_argument(
        "--config",
        nargs="+",
        required=True,
        help="One or more paths to JSON or YAML configs",
    )
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
