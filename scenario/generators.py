"""Batch generation helpers for configured simulation scenarios."""

from __future__ import annotations

import random
from typing import Any

from domain.entities import Batch


def generate_batches(
    config: dict[str, Any],
    default_route: list[str],
    *,
    seed: int | None = None,
) -> list[Batch]:
    """Generate batches from a fixed list or generation template."""
    mode = config.get("mode", "equal_intervals")
    route = list(config.get("route") or default_route)
    if mode == "fixed":
        batches = _fixed_batches(config, route)
    elif mode == "template":
        batches = _template_batches(config, route)
    elif mode == "random_intervals":
        batches = _random_interval_batches(config, route, seed=seed)
    else:
        batches = _equal_interval_batches(config, route)
    return sorted(batches, key=lambda batch: (batch.arrival_time, batch.batch_id))


def _fixed_batches(config: dict[str, Any], default_route: list[str]) -> list[Batch]:
    """Build batches from an explicit list in configuration."""
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
    """Build batches that arrive with fixed intervals."""
    count = int(config.get("count", 1))
    size = int(config.get("size", 1))
    interval = float(config.get("arrival_interval", 1.0))
    start_time = float(config.get("start_time", 0.0))
    prefix = str(config.get("batch_id_prefix", "batch"))
    return [
        Batch(
            batch_id=f"{prefix}-{index + 1}",
            arrival_time=start_time + index * interval,
            size=size,
            route=list(route),
        )
        for index in range(count)
    ]


def _template_batches(config: dict[str, Any], route: list[str]) -> list[Batch]:
    """Build batches from a reusable generation template."""
    return _equal_interval_batches(config, route)


def _random_interval_batches(
    config: dict[str, Any],
    route: list[str],
    *,
    seed: int | None = None,
) -> list[Batch]:
    """Build batches with stochastic inter-arrival times."""
    count = int(config.get("count", 1))
    size = int(config.get("size", 1))
    mean_interval = float(config.get("mean_interval", 1.0))
    prefix = str(config.get("batch_id_prefix", "batch"))
    effective_seed = config.get("seed", seed)
    rng = random.Random(effective_seed)
    current_time = float(config.get("start_time", 0.0))
    batches: list[Batch] = []
    for index in range(count):
        if index > 0:
            current_time += rng.expovariate(1.0 / mean_interval)
        batches.append(
            Batch(
                batch_id=f"{prefix}-{index + 1}",
                arrival_time=round(current_time, 4),
                size=size,
                route=list(route),
            )
        )
    return batches
