"""Create lightweight SVG charts without external dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Any


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
    ]
    return paths


def _queue_chart(raw_data: dict[str, Any], path: Path) -> Path:
    rows = raw_data.get("queue_lengths", [])
    points = [
        (float(row["timestamp"]), float(row["queue_length"]))
        for row in rows
    ]
    if not points:
        points = [(0.0, 0.0)]
    svg = _line_svg("Queue length over time", points)
    path.write_text(svg, encoding="utf-8")
    return path


def _machine_utilization_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    values = [
        (str(row["machine_id"]), float(row["utilization"]))
        for row in rows
    ]
    path.write_text(_bar_svg("Machine utilization", values), encoding="utf-8")
    return path


def _batch_cycle_time_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    values = [
        (str(row["batch_id"]), float(row["cycle_time"]))
        for row in rows
    ]
    path.write_text(_bar_svg("Batch cycle time", values), encoding="utf-8")
    return path


def _line_svg(title: str, points: list[tuple[float, float]]) -> str:
    width = 720
    height = 360
    max_x = max(point[0] for point in points) or 1.0
    max_y = max(point[1] for point in points) or 1.0
    scaled = [
        (
            50 + point[0] / max_x * 620,
            310 - point[1] / max_y * 250,
        )
        for point in points
    ]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in scaled)
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' "
        f"height='{height}' viewBox='0 0 {width} {height}'>"
        "<rect width='100%' height='100%' fill='white'/>"
        f"<text x='50' y='32' font-size='20'>{title}</text>"
        "<line x1='50' y1='310' x2='680' y2='310' stroke='black'/>"
        "<line x1='50' y1='60' x2='50' y2='310' stroke='black'/>"
        f"<polyline fill='none' stroke='#2f80ed' stroke-width='3' "
        f"points='{polyline}'/>"
        "</svg>"
    )


def _bar_svg(title: str, values: list[tuple[str, float]]) -> str:
    width = 720
    height = 360
    max_value = max([value for _, value in values] or [1.0]) or 1.0
    bar_width = 560 / max(len(values), 1)
    bars = []
    for index, (label, value) in enumerate(values):
        x = 70 + index * bar_width
        bar_height = value / max_value * 230
        y = 300 - bar_height
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width * 0.7:.1f}' "
            f"height='{bar_height:.1f}' fill='#27ae60'/>"
            f"<text x='{x:.1f}' y='324' font-size='10'>{label}</text>"
        )
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' "
        f"height='{height}' viewBox='0 0 {width} {height}'>"
        "<rect width='100%' height='100%' fill='white'/>"
        f"<text x='50' y='32' font-size='20'>{title}</text>"
        "<line x1='50' y1='300' x2='680' y2='300' stroke='black'/>"
        "<line x1='50' y1='60' x2='50' y2='300' stroke='black'/>"
        f"{''.join(bars)}"
        "</svg>"
    )
