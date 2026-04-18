"""Build final report objects and save them to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analytics import compare_analytics_runs
from domain.models import (
    AnalyticsReport,
    BottleneckSummary,
    ComparisonReport,
    PerformanceInsights,
    ReportFiles,
    ScenarioComparisonRow,
    ScenarioReport,
    StageMetrics,
)
from reporting.exporter import (
    export_csv,
    export_json,
    export_markdown,
    export_rows_csv,
    export_text,
)


def build_report(
    result: Any,
    analytics: AnalyticsReport,
    scenario_description: str,
    output_dir: str | Path,
    chart_paths: list[Path] | None = None,
) -> ScenarioReport:
    """Build and export the final JSON, CSV, and TXT reports."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    bottleneck = _detect_bottleneck(analytics)
    problem_stages = _collect_problem_stages(analytics)
    recommendations = _generate_recommendations(analytics, bottleneck, problem_stages)
    performance_insights = _generate_performance_insights(analytics)
    summary = _build_summary(
        analytics,
        scenario_description,
        bottleneck,
        problem_stages,
        recommendations,
        performance_insights,
        [str(path) for path in chart_paths or []],
    )
    markdown_summary = _build_markdown_summary(
        analytics,
        scenario_description,
        bottleneck,
        problem_stages,
        recommendations,
        performance_insights,
        [str(path) for path in chart_paths or []],
    )
    report = ScenarioReport(
        scenario_name=result.scenario_name,
        scenario_description=scenario_description,
        run_parameters={
            "simulation_time": result.simulation_time,
            "total_batches": len(result.batches),
            "stages": len(result.stages),
            "machines": len(result.machines),
        },
        analytics=analytics,
        bottleneck=bottleneck,
        problem_stages=problem_stages,
        recommendations=recommendations,
        performance_insights=performance_insights,
        charts=[str(path) for path in chart_paths or []],
    )
    csv_path = export_csv(analytics, output_path / "metrics.csv")
    txt_path = export_text(summary, output_path / "summary.txt")
    md_path = export_markdown(markdown_summary, output_path / "summary.md")
    report.files = ReportFiles(
        json=str(output_path / "report.json"),
        csv=str(csv_path),
        txt=str(txt_path),
        md=str(md_path),
    )
    export_json(report, output_path / "report.json")
    return report


def build_comparison_report(
    analytics_runs: list[AnalyticsReport],
    output_dir: str | Path,
) -> ComparisonReport:
    """Build and export a multi-scenario comparison report."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    comparison_rows = compare_analytics_runs(analytics_runs)
    report = ComparisonReport(
        scenarios=[analytics["scenario_name"] for analytics in analytics_runs],
        comparison=comparison_rows,
        best_output_scenario=_best_scenario(
            comparison_rows,
            "output_units",
            reverse=True,
        ),
        lowest_cycle_time_scenario=_best_scenario(
            comparison_rows,
            "average_cycle_time",
            reverse=False,
        ),
        lowest_rejection_scenario=_best_scenario(
            comparison_rows,
            "rejection_rate",
            reverse=False,
        ),
        highest_throughput_scenario=_best_scenario(
            comparison_rows,
            "throughput",
            reverse=True,
        ),
    )
    summary = _build_comparison_summary(report)
    markdown_summary = _build_comparison_markdown(report)
    csv_path = export_rows_csv(
        [row.to_dict() for row in comparison_rows],
        output_path / "comparison.csv",
    )
    txt_path = export_text(summary, output_path / "comparison_summary.txt")
    md_path = export_markdown(markdown_summary, output_path / "comparison_summary.md")
    report.files = ReportFiles(
        json=str(output_path / "comparison_report.json"),
        csv=str(csv_path),
        txt=str(txt_path),
        md=str(md_path),
    )
    export_json(report, output_path / "comparison_report.json")
    return report


def _detect_bottleneck(analytics: AnalyticsReport) -> BottleneckSummary:
    """Return the stage that creates the strongest throughput pressure."""
    stages = analytics.get("stages", [])
    if not stages:
        return BottleneckSummary(stage_id=None, reason="no stages")
    stage = max(
        stages,
        key=lambda item: (
            float(item.get("average_wait_time", 0.0)),
            float(item.get("average_queue_length", 0.0)),
            int(item.get("max_queue_length", 0)),
            float(item.get("utilization", 0.0)),
        ),
    )
    return BottleneckSummary(
        stage_id=stage["stage_id"],
        average_wait_time=stage["average_wait_time"],
        average_queue_length=stage.get("average_queue_length", 0.0),
        max_queue_length=stage["max_queue_length"],
        utilization=stage["utilization"],
        downtime_time=stage.get("downtime_time", 0.0),
    )


def _build_summary(
    analytics: AnalyticsReport,
    scenario_description: str,
    bottleneck: BottleneckSummary,
    problem_stages: list[StageMetrics],
    recommendations: list[str],
    performance_insights: PerformanceInsights,
    chart_paths: list[str],
) -> str:
    """Return a plain-text summary suitable for final delivery."""
    general = analytics["general"]
    lines = [
        f"Scenario: {analytics['scenario_name']}",
        f"Description: {scenario_description}",
        "",
        "=== General Metrics ===",
        f"Total batches: {general['total_batches']}",
        f"Completed batches: {general['completed_batches']}",
        f"Rejected batches: {general['rejected_batches']}",
        f"Output units: {general['output_units']}",
        f"Rejected units: {general.get('rejected_units', 0)}",
        f"Completion rate: {general.get('completion_rate', 0.0):.2%}",
        f"Rejection rate: {general.get('rejection_rate', 0.0):.2%}",
        f"Average cycle time: {general.get('average_cycle_time', 0.0):.3f}",
        f"Average queue wait: {general.get('average_wait_time', 0.0):.3f}",
        f"Throughput: {general.get('throughput', 0.0):.3f} units/time",
        f"Simulation time: {general['simulation_time']}",
        f"Total breakdowns: {general.get('total_breakdowns', 0)}",
        f"Total repair time: {general.get('total_repair_time', 0.0):.2f}",
        "",
        "=== Bottleneck Analysis ===",
        f"Bottleneck stage: {bottleneck['stage_id']}",
        f"Average wait time: {bottleneck.get('average_wait_time', 0.0):.3f}",
        f"Average queue length: {bottleneck.get('average_queue_length', 0.0):.3f}",
        f"Max queue length: {bottleneck.get('max_queue_length', 0)}",
        f"Utilization: {bottleneck.get('utilization', 0.0):.3f}",
        "",
        "=== Problem Stages ===",
    ]
    if not problem_stages:
        lines.append("No overloaded stages detected")
    for stage in problem_stages:
        lines.append(
            f"{stage['stage_id']}: wait={stage['average_wait_time']:.3f}, "
            f"avg_queue={stage.get('average_queue_length', 0.0):.3f}, "
            f"max_queue={stage['max_queue_length']}, utilization={stage['utilization']:.3f}"
        )
    lines.extend(
        [
            "",
            "=== Recommendations ===",
        ]
    )
    for recommendation in recommendations:
        lines.append(f"- {recommendation}")
    lines.extend(
        [
            "",
            "=== Performance Insights ===",
            f"Average machine utilization: {performance_insights['average_machine_utilization']:.3f}",
            f"Most utilized machine: {performance_insights['most_utilized_machine']}",
            f"Least utilized machine: {performance_insights['least_utilized_machine']}",
            f"Most problematic stage: {performance_insights['most_problematic_stage']}",
            f"Efficiency score: {performance_insights['efficiency_score']:.2f}",
            "",
            f"Charts: {', '.join(chart_paths) if chart_paths else 'not generated'}",
        ]
    )
    return "\n".join(lines)


def _collect_problem_stages(analytics: AnalyticsReport) -> list[StageMetrics]:
    """Return stages sorted by queue pressure, waiting time, and downtime."""
    stages = list(analytics.get("stages", []))
    stages.sort(
        key=lambda item: (
            float(item.get("average_wait_time", 0.0)),
            float(item.get("average_queue_length", 0.0)),
            int(item.get("max_queue_length", 0)),
            float(item.get("downtime_time", 0.0)),
            float(item.get("utilization", 0.0)),
        ),
        reverse=True,
    )
    return stages[:3]


def _build_markdown_summary(
    analytics: AnalyticsReport,
    scenario_description: str,
    bottleneck: BottleneckSummary,
    problem_stages: list[StageMetrics],
    recommendations: list[str],
    performance_insights: PerformanceInsights,
    chart_paths: list[str],
) -> str:
    """Return a Markdown summary suitable for quick demo review."""
    general = analytics["general"]
    lines = [
        f"# Scenario Report: {analytics['scenario_name']}",
        "",
        scenario_description,
        "",
        "## General Metrics",
        f"- Total batches: {general['total_batches']}",
        f"- Completed batches: {general['completed_batches']}",
        f"- Rejected batches: {general['rejected_batches']}",
        f"- Output units: {general['output_units']}",
        f"- Rejected units: {general.get('rejected_units', 0)}",
        f"- Completion rate: {general.get('completion_rate', 0.0):.2%}",
        f"- Rejection rate: {general.get('rejection_rate', 0.0):.2%}",
        f"- Average cycle time: {general.get('average_cycle_time', 0.0):.3f}",
        f"- Average queue wait: {general.get('average_wait_time', 0.0):.3f}",
        f"- Throughput: {general.get('throughput', 0.0):.3f}",
        f"- Simulation time: {general['simulation_time']}",
        f"- Total breakdowns: {general.get('total_breakdowns', 0)}",
        f"- Total repair time: {general.get('total_repair_time', 0.0):.2f}",
        "",
        "## Bottleneck",
        f"- Stage: {bottleneck.get('stage_id')}",
        f"- Average wait time: {bottleneck.get('average_wait_time', 0.0):.3f}",
        f"- Average queue length: {bottleneck.get('average_queue_length', 0.0):.3f}",
        f"- Max queue length: {bottleneck.get('max_queue_length', 0)}",
        f"- Utilization: {bottleneck.get('utilization', 0.0):.3f}",
        "",
        "## Problem Stages",
    ]
    if not problem_stages:
        lines.append("- No overloaded stages detected")
    for stage in problem_stages:
        lines.append(
            "- "
            f"{stage['stage_id']}: wait={stage['average_wait_time']:.3f}, "
            f"avg_queue={stage.get('average_queue_length', 0.0):.3f}, "
            f"max_queue={stage['max_queue_length']}, "
            f"utilization={stage['utilization']:.3f}, "
            f"downtime={stage.get('downtime_time', 0.0):.3f}"
        )

    lines.extend(["", "## Recommendations"])
    for recommendation in recommendations:
        lines.append(f"- {recommendation}")

    lines.extend(
        [
            "",
            "## Performance Insights",
            f"- Average machine utilization: {performance_insights['average_machine_utilization']:.3f}",
            f"- Most utilized machine: {performance_insights['most_utilized_machine']}",
            f"- Least utilized machine: {performance_insights['least_utilized_machine']}",
            f"- Most problematic stage: {performance_insights['most_problematic_stage']}",
            f"- Efficiency score: {performance_insights['efficiency_score']:.2f}",
            "",
            "## Charts",
        ]
    )
    if not chart_paths:
        lines.append("- Not generated")
    for chart_path in chart_paths:
        lines.append(f"- {chart_path}")
    return "\n".join(lines)


def _best_scenario(
    comparison_rows: list[ScenarioComparisonRow],
    metric_name: str,
    *,
    reverse: bool,
) -> ScenarioComparisonRow | None:
    """Return the best scenario row for a selected metric."""
    if not comparison_rows:
        return None
    return sorted(
        comparison_rows,
        key=lambda row: float(row[metric_name]),
        reverse=reverse,
    )[0]


def _build_comparison_summary(report: ComparisonReport) -> str:
    """Return a plain-text summary for a comparison report."""
    best_output = report["best_output_scenario"]
    lowest_cycle = report["lowest_cycle_time_scenario"]
    lowest_rejection = report["lowest_rejection_scenario"]
    highest_throughput = report["highest_throughput_scenario"]
    lines = [
        "Scenario comparison summary",
        f"Compared scenarios: {', '.join(report['scenarios'])}",
        "",
        "Comparison table:",
    ]
    for row in report["comparison"]:
        lines.append(
            f"- {row['scenario_name']}: output={row['output_units']}, "
            f"cycle={row['average_cycle_time']:.3f}, "
            f"reject={row['rejection_rate']:.2%}, "
            f"avg_queue={row['average_queue_length']:.3f}, "
            f"utilization={row['average_machine_utilization']:.3f}, "
            f"throughput={row['throughput']:.3f}"
        )
    lines.append("")
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
            f"{lowest_rejection['scenario_name']} ({lowest_rejection['rejection_rate']:.2%})"
        )
    if highest_throughput is not None:
        lines.append(
            "Highest throughput: "
            f"{highest_throughput['scenario_name']} ({highest_throughput['throughput']:.3f})"
        )
    return "\n".join(lines)


def _build_comparison_markdown(report: ComparisonReport) -> str:
    """Return a Markdown comparison report for multiple scenarios."""
    lines = [
        "# Scenario Comparison",
        "",
        f"Compared scenarios: {', '.join(report['scenarios'])}",
        "",
        "## Comparison Table",
    ]
    for row in report["comparison"]:
        lines.append(
            "- "
            f"{row['scenario_name']}: output={row['output_units']}, "
            f"cycle_time={row['average_cycle_time']:.3f}, "
            f"rejection_rate={row['rejection_rate']:.2%}, "
            f"avg_queue={row['average_queue_length']:.3f}, "
            f"avg_wait={row['average_wait_time']:.3f}, "
            f"utilization={row['average_machine_utilization']:.3f}, "
            f"throughput={row['throughput']:.3f}"
        )

    lines.extend(["", "## Best Scenarios"])
    if report["best_output_scenario"] is not None:
        lines.append(
            "- Best output: "
            f"{report['best_output_scenario']['scenario_name']}"
        )
    if report["lowest_cycle_time_scenario"] is not None:
        lines.append(
            "- Lowest cycle time: "
            f"{report['lowest_cycle_time_scenario']['scenario_name']}"
        )
    if report["lowest_rejection_scenario"] is not None:
        lines.append(
            "- Lowest rejection rate: "
            f"{report['lowest_rejection_scenario']['scenario_name']}"
        )
    if report["highest_throughput_scenario"] is not None:
        lines.append(
            "- Highest throughput: "
            f"{report['highest_throughput_scenario']['scenario_name']}"
        )
    return "\n".join(lines)


def _generate_recommendations(
    analytics: AnalyticsReport,
    bottleneck: BottleneckSummary,
    problem_stages: list[StageMetrics],
) -> list[str]:
    """Generate actionable recommendations based on analytics."""
    recommendations = []
    general = analytics["general"]

    if bottleneck.get("utilization", 0.0) > 0.85:
        recommendations.append(
            f"Add capacity to stage '{bottleneck['stage_id']}' "
            f"(utilization {bottleneck['utilization']:.1%})."
        )

    if bottleneck.get("average_wait_time", 0.0) > 5.0:
        recommendations.append(
            f"Reduce waiting at stage '{bottleneck['stage_id']}' "
            f"(avg wait {bottleneck['average_wait_time']:.2f})."
        )

    if bottleneck.get("average_queue_length", 0.0) > 1.5:
        recommendations.append(
            f"Queue pressure is high at stage '{bottleneck['stage_id']}'. "
            "Consider a larger queue or a faster workstation."
        )

    if general.get("rejection_rate", 0.0) > 0.1:
        recommendations.append(
            f"High rejection rate detected ({general['rejection_rate']:.1%}). "
            "Review processing quality and reject thresholds."
        )

    if general.get("total_breakdowns", 0) > 5:
        recommendations.append(
            f"Frequent breakdowns detected ({general['total_breakdowns']} total). "
            "Introduce preventive maintenance."
        )

    for stage in problem_stages[:2]:
        if stage.get("downtime_time", 0.0) > 0:
            recommendations.append(
                f"Stage '{stage['stage_id']}' loses {stage['downtime_time']:.2f} time units "
                "to repairs. Check machine reliability."
            )

    if not recommendations:
        recommendations.append(
            "System is operating efficiently. No critical bottlenecks were detected."
        )

    return recommendations


def _generate_performance_insights(analytics: AnalyticsReport) -> PerformanceInsights:
    """Generate performance insights from analytics data."""
    general = analytics["general"]
    stages = analytics.get("stages", [])
    machines = analytics.get("machines", [])

    avg_utilization = sum(m["utilization"] for m in machines) / max(len(machines), 1)
    max_utilization_machine = (
        max(machines, key=lambda item: item["utilization"]) if machines else None
    )
    min_utilization_machine = (
        min(machines, key=lambda item: item["utilization"]) if machines else None
    )
    most_problematic_stage = (
        max(
            stages,
            key=lambda item: (
                item.get("average_wait_time", 0.0),
                item.get("average_queue_length", 0.0),
                item.get("downtime_time", 0.0),
            ),
        )
        if stages
        else None
    )

    return PerformanceInsights(
        average_machine_utilization=avg_utilization,
        most_utilized_machine=(
            max_utilization_machine["machine_id"] if max_utilization_machine else None
        ),
        least_utilized_machine=(
            min_utilization_machine["machine_id"] if min_utilization_machine else None
        ),
        most_problematic_stage=(
            most_problematic_stage["stage_id"] if most_problematic_stage else None
        ),
        efficiency_score=_calculate_efficiency_score(general, avg_utilization),
    )


def _calculate_efficiency_score(general: Any, avg_utilization: float) -> float:
    """Calculate an overall efficiency score in the range 0-100."""
    completion_rate = float(general.get("completion_rate", 0.0))
    rejection_rate = float(general.get("rejection_rate", 0.0))
    throughput = float(general.get("throughput", 0.0))
    normalized_throughput = min(throughput / max(float(general.get("output_units", 1)), 1.0), 1.0)
    score = (
        completion_rate * 0.45
        + avg_utilization * 0.25
        + (1.0 - rejection_rate) * 0.2
        + normalized_throughput * 0.1
    ) * 100
    return max(0.0, min(score, 100.0))
