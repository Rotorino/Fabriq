"""Low-level metric formulas used by analytics calculators."""

from __future__ import annotations


def calculate_utilization(total_busy_time: float, total_time: float) -> float:
    """Calculate utilization ratio in range [0.0, 1.0]."""
    if total_time <= 0:
        return 0.0
    return max(0.0, min(total_busy_time / total_time, 1.0))


def average(values: list[float]) -> float:
    """Return arithmetic mean or zero for an empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)
