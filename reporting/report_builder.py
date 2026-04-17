"""Build final report objects and save them to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reporting.exporter import export_csv, export_json, export_text


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
