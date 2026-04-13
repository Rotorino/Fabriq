"""Batch generation helpers for configured simulation scenarios."""

from __future__ import annotations

import random
from typing import Any

from domain.entities import Batch


def generate_batches(config: dict[str, Any], default_route: list[str]) -> list[Batch]:
    """Generate batches from a fixed list or generation template."""
    mode = config.get("mode", "equal_intervals")
    route = list(config.get("route") or default_route)
    if mode == "fixed":
        return _fixed_batches(config, route)
    if mode == "random_intervals":
        return _random_interval_batches(config, route)
    return _equal_interval_batches(config, route)


def _fixed_batches(config: dict[str, Any], default_route: list[str]) -> list[Batch]:
    batches = []
    for raw_batch in config.get("items", []):
        batches.append(
            Batch(
                batch_id=str(raw_batch["batch_id"]),
                arrival_time=float(raw_batch["arrival_time"]),
                size=int(raw_batch.get("size", config.get("size", 1))),
                route=list(raw_batch.get("route") or default_route),
            )
        )
    return batches


def _equal_interval_batches(config: dict[str, Any], route: list[str]) -> list[Batch]:
    count = int(config.get("count", 1))
    size = int(config.get("size", 1))
    interval = float(config.get("arrival_interval", 1.0))
    start_time = float(config.get("start_time", 0.0))
    return [
        Batch(
            batch_id=f"batch-{index + 1}",
            arrival_time=start_time + index * interval,
            size=size,
            route=list(route),
        )
        for index in range(count)
    ]


def _random_interval_batches(config: dict[str, Any], route: list[str]) -> list[Batch]:
    count = int(config.get("count", 1))
    size = int(config.get("size", 1))
    mean_interval = float(config.get("mean_interval", 1.0))
    rng = random.Random(config.get("seed"))
    current_time = float(config.get("start_time", 0.0))
    batches: list[Batch] = []
    for index in range(count):
        if index > 0:
            current_time += rng.expovariate(1.0 / mean_interval)
        batches.append(
            Batch(
                batch_id=f"batch-{index + 1}",
                arrival_time=round(current_time, 4),
                size=size,
                route=list(route),
            )
        )
    return batches
