"""Optional SVG timeline builder for simulation event logs."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def build_timeline(events: list[Any], output_path: str | Path) -> Path:
    """Build a simple textual SVG timeline for event log records."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, event in enumerate(events[:25]):
        y = 30 + index * 22
        text = escape(f"{event.timestamp:.2f}: {event.event_type} {event.result}")
        lines.append(f"<text x='20' y='{y}' font-size='12'>{text}</text>")
    height = max(80, 50 + len(lines) * 22)
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='900' "
        f"height='{height}'>"
        "<rect width='100%' height='100%' fill='white'/>"
        f"{''.join(lines)}</svg>"
    )
    path.write_text(svg, encoding="utf-8")
    return path
