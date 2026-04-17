"""Configuration loading helpers for simulation scenarios."""

from __future__ import annotations

import json
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when a scenario configuration cannot be loaded."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON or YAML scenario configuration from disk."""
    config_path = Path(path)
    suffix = config_path.suffix.lower()
    try:
        with config_path.open("r", encoding="utf-8") as file:
            if suffix == ".json":
                data = json.load(file)
            elif suffix in {".yaml", ".yml"}:
                data = _load_yaml(file.read(), config_path)
            else:
                raise ConfigurationError(
                    f"Unsupported config format: {config_path.suffix or '<none>'}"
                )
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Invalid JSON in config: {config_path}") from exc

    if not isinstance(data, dict):
        raise ConfigurationError("Scenario config root must be an object")
    return deepcopy(data)


def load_config_dict(config: dict[str, Any]) -> dict[str, Any]:
    """Return an isolated copy of an in-memory configuration object."""
    if not isinstance(config, dict):
        raise ConfigurationError("Scenario config root must be an object")
    return deepcopy(config)


def _load_yaml(content: str, config_path: Path) -> dict[str, Any]:
    """Load YAML content when PyYAML is available."""
    try:
        yaml = import_module("yaml")
    except ModuleNotFoundError as exc:
        raise ConfigurationError(
            "YAML support requires PyYAML to be installed"
        ) from exc

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in config: {config_path}") from exc

    if data is None:
        raise ConfigurationError(f"Empty config file: {config_path}")
    if not isinstance(data, dict):
        raise ConfigurationError("Scenario config root must be an object")
    return data
