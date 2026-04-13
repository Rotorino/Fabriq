"""Validation functions for scenario configuration dictionaries."""

from __future__ import annotations

from typing import Any

from scenario.config_loader import ConfigurationError


def validate_config(config: dict[str, Any]) -> None:
    """Validate the raw scenario configuration before object construction."""
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

        _validate_non_negative_or_none(stage, "queue_limit")
        _validate_non_negative_or_none(stage, "buffer_capacity")
        _validate_probability(stage, "reject_probability")

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

    _validate_batches(config, stage_ids)


def _validate_batches(config: dict[str, Any], stage_ids: set[str]) -> None:
    batches = config.get("batches")
    if not isinstance(batches, dict):
        raise ConfigurationError("Config must contain batches object")
    mode = batches.get("mode", "equal_intervals")
    if mode not in {"fixed", "equal_intervals", "random_intervals"}:
        raise ConfigurationError(f"Unsupported batch generation mode: {mode}")

    route = batches.get("route")
    if route is not None:
        if not isinstance(route, list) or not route:
            raise ConfigurationError("batches.route must be a non-empty list")
        unknown = [stage_id for stage_id in route if stage_id not in stage_ids]
        if unknown:
            raise ConfigurationError(f"Unknown route stage_id: {unknown[0]}")


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
    if value is not None and int(value) < 0:
        raise ConfigurationError(f"{key} must be non-negative or null")
