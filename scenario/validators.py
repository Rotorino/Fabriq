"""Validation functions for scenario configuration dictionaries."""

from __future__ import annotations

from typing import Any

from domain.enums import RoutingStrategy, StageType
from scenario.config_loader import ConfigurationError


def validate_config(config: dict[str, Any]) -> None:
    """Validate the raw scenario configuration before object construction."""
    _validate_scenario_metadata(config)
    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ConfigurationError("Config must contain a non-empty stages list")

    stage_ids: set[str] = set()
    machine_ids: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise ConfigurationError("Each stage must be an object")
        stage_id = _required_string(stage, "stage_id")
        if stage_id in stage_ids:
            raise ConfigurationError(f"Duplicate stage_id: {stage_id}")
        stage_ids.add(stage_id)

        _required_string(stage, "name")
        _validate_non_negative_or_none(stage, "queue_limit")
        _validate_non_negative_or_none(stage, "buffer_capacity")
        _validate_probability(stage, "reject_probability")
        _validate_enum_value(
            stage,
            "stage_type",
            {item.value for item in StageType},
        )
        _validate_enum_value(
            stage,
            "routing_strategy",
            {item.value for item in RoutingStrategy},
        )

        machines = stage.get("machines")
        if not isinstance(machines, list) or not machines:
            raise ConfigurationError(f"Stage {stage_id} must contain machines")
        for machine in machines:
            machine_id = _required_string(machine, "machine_id")
            if machine_id in machine_ids:
                raise ConfigurationError(f"Duplicate machine_id: {machine_id}")
            machine_ids.add(machine_id)
            _validate_non_negative(machine, "processing_time")
            _validate_non_negative(machine, "repair_time")
            _validate_probability(machine, "breakdown_probability")

    for stage in stages:
        next_stage_id = stage.get("next_stage_id")
        if next_stage_id is not None and next_stage_id not in stage_ids:
            raise ConfigurationError(f"Unknown next_stage_id: {next_stage_id}")

    _validate_line_topology(stages, stage_ids)
    _validate_batches(config, stages, stage_ids)


def _validate_scenario_metadata(config: dict[str, Any]) -> None:
    scenario_name = config.get("scenario_name")
    if scenario_name is not None and (
        not isinstance(scenario_name, str) or not scenario_name
    ):
        raise ConfigurationError("scenario_name must be a non-empty string")
    if "simulation_duration" not in config:
        raise ConfigurationError("simulation_duration is required")
    _validate_non_negative(config, "simulation_duration")
    seed = config.get("seed")
    if seed is not None and not isinstance(seed, int):
        raise ConfigurationError("seed must be an integer or null")


def _validate_batches(
    config: dict[str, Any],
    stages: list[dict[str, Any]],
    stage_ids: set[str],
) -> None:
    batches = config.get("batches")
    if not isinstance(batches, dict):
        raise ConfigurationError("Config must contain batches object")
    mode = batches.get("mode", "equal_intervals")
    if mode not in {"fixed", "template", "equal_intervals", "random_intervals"}:
        raise ConfigurationError(f"Unsupported batch generation mode: {mode}")

    route = batches.get("route")
    if route is not None:
        if not isinstance(route, list) or not route:
            raise ConfigurationError("batches.route must be a non-empty list")
        unknown = [stage_id for stage_id in route if stage_id not in stage_ids]
        if unknown:
            raise ConfigurationError(f"Unknown route stage_id: {unknown[0]}")
        _validate_route_consistency(route, stages)

    if mode == "fixed":
        items = batches.get("items")
        if not isinstance(items, list) or not items:
            raise ConfigurationError(
                "batches.items must be a non-empty list for fixed mode"
            )
        batch_ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise ConfigurationError("Each fixed batch item must be an object")
            batch_id = _required_string(item, "batch_id")
            if batch_id in batch_ids:
                raise ConfigurationError(f"Duplicate batch_id: {batch_id}")
            batch_ids.add(batch_id)
            _validate_non_negative(item, "arrival_time")
            if "size" in item:
                _validate_positive_int(item, "size")
            elif not isinstance(batches.get("size"), int) or int(batches["size"]) <= 0:
                raise ConfigurationError(
                    "Each fixed batch must define a positive size or batches.size"
                )
            item_route = item.get("route", route)
            if not isinstance(item_route, list) or not item_route:
                raise ConfigurationError(
                    "Each fixed batch must define a non-empty route"
                )
            unknown = [stage_id for stage_id in item_route if stage_id not in stage_ids]
            if unknown:
                raise ConfigurationError(f"Unknown route stage_id: {unknown[0]}")
            _validate_route_consistency(item_route, stages)
        return

    _validate_positive_int(batches, "count")
    _validate_positive_int(batches, "size")
    _validate_non_negative(batches, "start_time")
    if mode in {"template", "equal_intervals"}:
        _validate_non_negative(batches, "arrival_interval")
    elif mode == "random_intervals":
        mean_interval = float(batches.get("mean_interval", 1.0))
        if mean_interval <= 0:
            raise ConfigurationError("mean_interval must be greater than zero")
        seed = batches.get("seed")
        if seed is not None and not isinstance(seed, int):
            raise ConfigurationError("batches.seed must be an integer or null")


def _validate_route_consistency(
    route: list[str],
    stages: list[dict[str, Any]],
) -> None:
    stage_map = {str(stage["stage_id"]): stage for stage in stages}
    for current_stage_id, next_stage_id in zip(route, route[1:]):
        configured_next = stage_map[current_stage_id].get("next_stage_id")
        if configured_next is not None and configured_next != next_stage_id:
            raise ConfigurationError(
                f"Route is inconsistent with stage links: {current_stage_id} -> {next_stage_id}"
            )


def _validate_line_topology(
    stages: list[dict[str, Any]],
    stage_ids: set[str],
) -> None:
    stage_map = {str(stage["stage_id"]): stage for stage in stages}
    referenced_stage_ids = {
        str(stage["next_stage_id"])
        for stage in stages
        if stage.get("next_stage_id") is not None
    }
    entry_stage_ids = sorted(stage_ids - referenced_stage_ids)
    if len(entry_stage_ids) != 1:
        raise ConfigurationError(
            "Production line must define exactly one entry stage"
        )

    visited: set[str] = set()
    current_stage_id: str | None = entry_stage_ids[0]
    while current_stage_id is not None:
        if current_stage_id in visited:
            raise ConfigurationError(
                f"Cycle detected in production line at stage {current_stage_id}"
            )
        visited.add(current_stage_id)
        current_stage = stage_map[current_stage_id]
        current_stage_id = current_stage.get("next_stage_id")

    if visited != stage_ids:
        missing = sorted(stage_ids - visited)
        raise ConfigurationError(
            "Production line contains unreachable or disconnected stages: "
            + ", ".join(missing)
        )


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{key} must be a non-empty string")
    return value


def _validate_probability(data: dict[str, Any], key: str) -> None:
    value = float(data.get(key, 0.0))
    if not 0.0 <= value <= 1.0:
        raise ConfigurationError(f"{key} must be in range [0.0, 1.0]")


def _validate_non_negative(data: dict[str, Any], key: str) -> None:
    value = float(data.get(key, 0.0))
    if value < 0:
        raise ConfigurationError(f"{key} must be non-negative")


def _validate_non_negative_or_none(data: dict[str, Any], key: str) -> None:
    value = data.get(key)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer or null")
    if value < 0:
        raise ConfigurationError(f"{key} must be non-negative or null")


def _validate_positive_int(data: dict[str, Any], key: str) -> None:
    value = data.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{key} must be a positive integer")


def _validate_enum_value(
    data: dict[str, Any],
    key: str,
    allowed_values: set[str],
) -> None:
    value = data.get(key)
    if value is None:
        return
    if not isinstance(value, str) or value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ConfigurationError(f"{key} must be one of: {allowed}")
