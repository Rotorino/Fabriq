"""Create lightweight SVG charts without external dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analytics import queue_lengths_by_stage
from visualization.timeline import build_timeline

SVG_HEIGHT = 400
SVG_WIDTH = 840
PLOT_BOTTOM = 320
PLOT_LEFT = 70
PLOT_RIGHT = 780
PLOT_TOP = 70
LINE_COLORS = [
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#17becf",
]
BAR_COLORS = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e"]


def build_charts(
    result: Any,
    analytics: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    """Build the required queue, utilization, and cycle-time charts."""
    chart_dir = Path(output_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        _queue_chart(result.raw_data, chart_dir / "queue_length.svg"),
        _machine_utilization_chart(
            analytics["machines"],
            chart_dir / "machine_utilization.svg",
        ),
        _batch_cycle_time_chart(
            analytics["batches"],
            chart_dir / "batch_cycle_time.svg",
        ),
        _breakdown_distribution_chart(
            analytics["stages"],
            chart_dir / "breakdown_distribution.svg",
        ),
        _stage_comparison_chart(
            analytics["stages"],
            chart_dir / "stage_comparison.svg",
        ),
        _throughput_over_time_chart(
            result,
            chart_dir / "throughput_over_time.svg",
        ),
        build_timeline(
            result.event_log,
            chart_dir / "event_timeline.svg",
        ),
    ]
    return paths


def _queue_chart(raw_data: dict[str, Any], path: Path) -> Path:
    grouped = queue_lengths_by_stage(raw_data)
    series: list[tuple[str, list[tuple[float, float]]]] = []
    for stage_id, rows in grouped.items():
        series.append(
            (
                stage_id,
                [
                    (float(row["timestamp"]), float(row["queue_length"]))
                    for row in rows
                ]
                or [(0.0, 0.0)],
            )
        )
    if not series:
        series = [("queue", [(0.0, 0.0)])]
    path.write_text(_multi_line_svg("Queue length over time", series), encoding="utf-8")
    return path


def _machine_utilization_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    values = [
        {
            "label": str(row["machine_id"]),
            "value": float(row["utilization"]) * 100.0,
            "color": BAR_COLORS[index % len(BAR_COLORS)],
        }
        for index, row in enumerate(rows)
    ]
    svg = _bar_svg(
        title="Machine utilization (%)",
        values=values,
        y_axis_max=100.0,
    )
    path.write_text(svg, encoding="utf-8")
    return path


def _batch_cycle_time_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    cycle_times = sorted(float(row["cycle_time"]) for row in rows)
    if not cycle_times:
        svg = _bar_svg("Batch cycle time distribution", [])
        path.write_text(svg, encoding="utf-8")
        return path

    bins = _histogram(cycle_times, bucket_count=min(6, max(len(cycle_times), 1)))
    values = [
        {
            "label": label,
            "value": float(count),
            "color": BAR_COLORS[index % len(BAR_COLORS)],
        }
        for index, (label, count) in enumerate(bins)
    ]
    path.write_text(
        _bar_svg("Batch cycle time distribution", values),
        encoding="utf-8",
    )
    return path


def _breakdown_distribution_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    """Build a chart showing breakdown count per stage."""
    values = [
        {
            "label": str(row["stage_id"]),
            "value": float(row["breakdowns"]),
            "color": BAR_COLORS[index % len(BAR_COLORS)],
        }
        for index, row in enumerate(rows)
    ]
    path.write_text(_bar_svg("Breakdowns per stage", values), encoding="utf-8")
    return path


def _stage_comparison_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    """Build a chart showing queue pressure and wait time per stage."""
    width = SVG_WIDTH
    height = SVG_HEIGHT
    if not rows:
        path.write_text(_bar_svg("Stage comparison", []), encoding="utf-8")
        return path

    max_wait = max(float(row["average_wait_time"]) for row in rows) or 1.0
    max_queue = max(float(row.get("average_queue_length", 0.0)) for row in rows) or 1.0
    step = (PLOT_RIGHT - PLOT_LEFT) / max(len(rows), 1)
    bars: list[str] = []

    for index, row in enumerate(rows):
        origin_x = PLOT_LEFT + index * step + 25
        wait_height = float(row["average_wait_time"]) / max_wait * 180
        queue_height = float(row.get("average_queue_length", 0.0)) / max_queue * 180
        bars.append(
            f"<rect x='{origin_x:.1f}' y='{PLOT_BOTTOM - wait_height:.1f}' "
            f"width='{step * 0.28:.1f}' height='{wait_height:.1f}' fill='#d62728'/>"
            f"<rect x='{origin_x + step * 0.34:.1f}' y='{PLOT_BOTTOM - queue_height:.1f}' "
            f"width='{step * 0.28:.1f}' height='{queue_height:.1f}' fill='#1f77b4'/>"
            f"<text x='{origin_x:.1f}' y='{PLOT_BOTTOM + 24}' font-size='11'>{row['stage_id']}</text>"
        )

    legend = (
        "<rect x='90' y='350' width='14' height='14' fill='#d62728'/>"
        "<text x='110' y='362' font-size='12'>Average wait time</text>"
        "<rect x='260' y='350' width='14' height='14' fill='#1f77b4'/>"
        "<text x='280' y='362' font-size='12'>Average queue length</text>"
    )
    svg = (
        _svg_header("Stage comparison")
        + _axes_svg()
        + "".join(bars)
        + legend
        + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")
    return path


def _throughput_over_time_chart(result: Any, path: Path) -> Path:
    """Build a chart showing cumulative completed output units over time."""
    batch_sizes = {
        str(batch.batch_id): int(getattr(batch, "size", 0))
        for batch in result.batches
    }
    completed_events = [
        (float(event.timestamp), batch_sizes.get(str(event.batch_id), 0))
        for event in result.event_log
        if event.result == "batch_completed" and event.batch_id is not None
    ]
    if not completed_events:
        path.write_text(
            _multi_line_svg("Throughput over time", [("output", [(0.0, 0.0)])]),
            encoding="utf-8",
        )
        return path

    cumulative: list[tuple[float, float]] = []
    total_units = 0
    for timestamp, units in sorted(completed_events):
        total_units += units
        cumulative.append((timestamp, float(total_units)))
    svg = _multi_line_svg("Cumulative output units", [("output", cumulative)])
    path.write_text(svg, encoding="utf-8")
    return path


def _multi_line_svg(
    title: str,
    series: list[tuple[str, list[tuple[float, float]]]],
) -> str:
    """Render one or more line series on a simple SVG chart."""
    max_x = max(point[0] for _, points in series for point in points) or 1.0
    max_y = max(point[1] for _, points in series for point in points) or 1.0
    polylines: list[str] = []
    legends: list[str] = []
    for index, (label, points) in enumerate(series):
        color = LINE_COLORS[index % len(LINE_COLORS)]
        scaled_points = [
            (
                PLOT_LEFT + point[0] / max_x * (PLOT_RIGHT - PLOT_LEFT),
                PLOT_BOTTOM - point[1] / max_y * (PLOT_BOTTOM - PLOT_TOP),
            )
            for point in points
        ]
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in scaled_points)
        polylines.append(
            f"<polyline fill='none' stroke='{color}' stroke-width='3' points='{polyline}'/>"
        )
        legend_y = 50 + index * 18
        legends.append(
            f"<line x1='560' y1='{legend_y}' x2='582' y2='{legend_y}' stroke='{color}' stroke-width='3'/>"
            f"<text x='590' y='{legend_y + 4}' font-size='12'>{label}</text>"
        )
    return _svg_header(title) + _axes_svg() + "".join(polylines) + "".join(legends) + "</svg>"


def _bar_svg(
    title: str,
    values: list[dict[str, Any]],
    *,
    y_axis_max: float | None = None,
) -> str:
    """Render a simple bar chart SVG."""
    max_value = y_axis_max or max([float(item["value"]) for item in values] or [1.0]) or 1.0
    step = (PLOT_RIGHT - PLOT_LEFT) / max(len(values), 1)
    bars: list[str] = []
    for index, item in enumerate(values):
        value = float(item["value"])
        height = value / max_value * (PLOT_BOTTOM - PLOT_TOP)
        x = PLOT_LEFT + index * step + step * 0.15
        y = PLOT_BOTTOM - height
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{step * 0.7:.1f}' "
            f"height='{height:.1f}' fill='{item.get('color', BAR_COLORS[index % len(BAR_COLORS)])}'/>"
            f"<text x='{x:.1f}' y='{PLOT_BOTTOM + 24}' font-size='11'>{item['label']}</text>"
            f"<text x='{x:.1f}' y='{max(y - 6, 18):.1f}' font-size='11'>{value:.1f}</text>"
        )
    return _svg_header(title) + _axes_svg() + "".join(bars) + "</svg>"


def _svg_header(title: str) -> str:
    """Return the SVG header and title block."""
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{SVG_WIDTH}' "
        f"height='{SVG_HEIGHT}' viewBox='0 0 {SVG_WIDTH} {SVG_HEIGHT}'>"
        "<rect width='100%' height='100%' fill='#ffffff'/>"
        f"<text x='{PLOT_LEFT}' y='34' font-size='22' font-weight='bold'>{title}</text>"
    )


def _axes_svg() -> str:
    """Return standard X/Y axes for SVG charts."""
    return (
        f"<line x1='{PLOT_LEFT}' y1='{PLOT_BOTTOM}' x2='{PLOT_RIGHT}' y2='{PLOT_BOTTOM}' stroke='#111'/>"
        f"<line x1='{PLOT_LEFT}' y1='{PLOT_TOP}' x2='{PLOT_LEFT}' y2='{PLOT_BOTTOM}' stroke='#111'/>"
    )


def _histogram(values: list[float], bucket_count: int) -> list[tuple[str, int]]:
    """Build coarse histogram buckets for cycle-time distribution."""
    if not values:
        return [("0.0-0.0", 0)]
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return [(f"{minimum:.1f}", len(values))]
    bucket_size = (maximum - minimum) / bucket_count
    counts = [0 for _ in range(bucket_count)]
    for value in values:
        if value == maximum:
            index = bucket_count - 1
        else:
            index = int((value - minimum) / bucket_size)
        counts[index] += 1
    labels = []
    for index, count in enumerate(counts):
        start = minimum + index * bucket_size
        end = start + bucket_size
        labels.append((f"{start:.1f}-{end:.1f}", count))
    return labels
