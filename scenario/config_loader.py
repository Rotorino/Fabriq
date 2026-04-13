"""Configuration loading helpers for simulation scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when a scenario configuration cannot be loaded."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON scenario configuration from disk."""
    config_path = Path(path)
    try:
        with config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Invalid JSON in config: {config_path}") from exc

    if not isinstance(data, dict):
        raise ConfigurationError("Scenario config root must be a JSON object")
    return data
