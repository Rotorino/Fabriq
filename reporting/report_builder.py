"""Build final report objects and save them to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analytics import compare_analytics_runs
from reporting.exporter import export_csv, export_json, export_rows_csv, export_text


def build_report(
    result: Any,
    analytics: dict[str, Any],
    scenario_description: str,
    output_dir: str | Path,
    chart_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Build and export the final JSON, CSV, and TXT reports."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    bottleneck = _detect_bottleneck(analytics)
    problem_stages = _collect_problem_stages(analytics)
    summary = _build_summary(
        analytics,
        scenario_description,
        bottleneck,
        [str(path) for path in chart_paths or []],
    )
    report = {
        "scenario_name": result.scenario_name,
        "scenario_description": scenario_description,
        "run_parameters": {
            "simulation_time": result.simulation_time,
            "total_batches": len(result.batches),
            "stages": len(result.stages),
            "machines": len(result.machines),
        },
        "analytics": analytics,
        "bottleneck": bottleneck,
        "problem_stages": problem_stages,
        "charts": [str(path) for path in chart_paths or []],
    }
    csv_path = export_csv(analytics, output_path / "metrics.csv")
    txt_path = export_text(summary, output_path / "summary.txt")
    report["files"] = {
        "json": str(output_path / "report.json"),
        "csv": str(csv_path),
        "txt": str(txt_path),
    }
    export_json(report, output_path / "report.json")
    return report


def build_comparison_report(
    analytics_runs: list[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, Any]:
    """Build and export a multi-scenario comparison report."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    comparison_rows = compare_analytics_runs(analytics_runs)
    report = {
        "scenarios": [analytics["scenario_name"] for analytics in analytics_runs],
        "comparison": comparison_rows,
        "best_output_scenario": _best_scenario(
            comparison_rows,
            "output_units",
            reverse=True,
        ),
        "lowest_cycle_time_scenario": _best_scenario(
            comparison_rows,
            "average_cycle_time",
            reverse=False,
        ),
        "lowest_rejection_scenario": _best_scenario(
            comparison_rows,
            "rejection_rate",
            reverse=False,
        ),
    }
    summary = _build_comparison_summary(report)
    csv_path = export_rows_csv(comparison_rows, output_path / "comparison.csv")
    txt_path = export_text(summary, output_path / "comparison_summary.txt")
    report["files"] = {
        "json": str(output_path / "comparison_report.json"),
        "csv": str(csv_path),
        "txt": str(txt_path),
    }
    export_json(report, output_path / "comparison_report.json")
    return report


def _detect_bottleneck(analytics: dict[str, Any]) -> dict[str, Any]:
    stages = analytics.get("stages", [])
    if not stages:
        return {"stage_id": None, "reason": "no stages"}
    stage = max(
        stages,
        key=lambda item: (
            item.get("average_wait_time", 0.0),
            item.get("max_queue_length", 0),
            item.get("utilization", 0.0),
        ),
    )
    return {
        "stage_id": stage["stage_id"],
        "average_wait_time": stage["average_wait_time"],
        "max_queue_length": stage["max_queue_length"],
        "utilization": stage["utilization"],
    }


def _build_summary(
    analytics: dict[str, Any],
    scenario_description: str,
    bottleneck: dict[str, Any],
    chart_paths: list[str],
) -> str:
    general = analytics["general"]
    return "\n".join(
        [
            f"Scenario: {analytics['scenario_name']}",
            f"Description: {scenario_description}",
            f"Total batches: {general['total_batches']}",
            f"Completed batches: {general['completed_batches']}",
            f"Rejected batches: {general['rejected_batches']}",
            f"Output units: {general['output_units']}",
            f"Simulation time: {general['simulation_time']}",
            f"Bottleneck stage: {bottleneck['stage_id']}",
            f"Charts: {', '.join(chart_paths) if chart_paths else 'not generated'}",
        ]
    )


def _collect_problem_stages(analytics: dict[str, Any]) -> list[dict[str, Any]]:
    """Return stages sorted by queue pressure and waiting time."""
    stages = list(analytics.get("stages", []))
    stages.sort(
        key=lambda item: (
            float(item.get("average_wait_time", 0.0)),
            int(item.get("max_queue_length", 0)),
            float(item.get("utilization", 0.0)),
        ),
        reverse=True,
    )
    return stages[:3]


def _best_scenario(
    comparison_rows: list[dict[str, Any]],
    metric_name: str,
    *,
    reverse: bool,
) -> dict[str, Any] | None:
    """Return the best scenario row for a selected metric."""
    if not comparison_rows:
        return None
    return sorted(
        comparison_rows,
        key=lambda row: float(row[metric_name]),
        reverse=reverse,
    )[0]


def _build_comparison_summary(report: dict[str, Any]) -> str:
    """Return a plain-text summary for a comparison report."""
    best_output = report["best_output_scenario"]
    lowest_cycle = report["lowest_cycle_time_scenario"]
    lowest_rejection = report["lowest_rejection_scenario"]
    lines = [
        "Scenario comparison summary",
        f"Compared scenarios: {', '.join(report['scenarios'])}",
    ]
    if best_output is not None:
        lines.append(
            f"Best output: {best_output['scenario_name']} ({best_output['output_units']})"
        )
    if lowest_cycle is not None:
        lines.append(
            "Lowest average cycle time: "
            f"{lowest_cycle['scenario_name']} ({lowest_cycle['average_cycle_time']:.3f})"
        )
    if lowest_rejection is not None:
        lines.append(
            "Lowest rejection rate: "
            f"{lowest_rejection['scenario_name']} ({lowest_rejection['rejection_rate']:.3f})"
        )
    return "\n".join(lines)
