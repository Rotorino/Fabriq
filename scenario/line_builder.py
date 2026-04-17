"""Build validated domain objects from raw scenario configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.entities import Batch, Buffer, Machine, ProductionLine, Stage
from domain.enums import RoutingStrategy, StageType
from domain.models import ScenarioConfig
from scenario.config_loader import ConfigurationError
from scenario.generators import generate_batches
from scenario.validators import validate_config


@dataclass(slots=True)
class ScenarioInput:
    """Prepared input for the simulation engine."""

    production_line: ProductionLine
    batches: list[Batch]
    scenario_config: ScenarioConfig


def build_scenario(config: dict[str, Any]) -> ScenarioInput:
    """Build a validated production line, batches, and scenario metadata."""
    validate_config(config)
    try:
        line = build_production_line(config)
        scenario = build_scenario_config(config)
        batches = build_batches(config, line)
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"Failed to build scenario objects: {exc}") from exc
    return ScenarioInput(line, batches, scenario)


def build_scenario_config(config: dict[str, Any]) -> ScenarioConfig:
    """Build validated scenario metadata."""
    batches = config.get("batches", {})
    return ScenarioConfig(
        name=str(config.get("scenario_name", "default")),
        description=str(config.get("description", "")),
        simulation_duration=float(config["simulation_duration"]),
        seed=config.get("seed"),
        batch_generation_mode=str(batches.get("mode", "equal_intervals")),
    )


def build_production_line(config: dict[str, Any]) -> ProductionLine:
    """Build a validated production line from raw config."""
    stages = _build_stages(config["stages"])
    entry_stage_ids = _resolve_entry_stage_ids(config["stages"])
    return ProductionLine(
        stages=stages,
        entry_stage_id=entry_stage_ids[0] if len(entry_stage_ids) == 1 else None,
        entry_stage_ids=entry_stage_ids,
    )


def build_batches(config: dict[str, Any], line: ProductionLine) -> list[Batch]:
    """Build validated batches for the production line."""
    configured_route = config["batches"].get("route")
    if configured_route is None and len(line.entry_stage_ids) != 1:
        raise ConfigurationError(
            "batches.route is required when the production line has multiple entry stages"
        )
    default_route = list(configured_route or line.route_from_entry())
    return generate_batches(
        config["batches"],
        default_route,
        seed=config.get("seed"),
    )


def _build_stages(raw_stages: list[dict[str, Any]]) -> dict[str, Stage]:
    """Build stage entities with nested machines."""
    stages: dict[str, Stage] = {}
    for raw_stage in raw_stages:
        stage_id = str(raw_stage["stage_id"])
        machines = [
            Machine(
                machine_id=str(raw_machine["machine_id"]),
                stage_id=stage_id,
                processing_time=float(raw_machine["processing_time"]),
                breakdown_probability=float(
                    raw_machine.get("breakdown_probability", 0.0)
                ),
                repair_time=float(raw_machine.get("repair_time", 0.0)),
            )
            for raw_machine in raw_stage["machines"]
        ]
        stages[stage_id] = Stage(
            stage_id=stage_id,
            name=str(raw_stage.get("name", stage_id)),
            machines=machines,
            queue_limit=raw_stage.get("queue_limit"),
            reject_probability=float(raw_stage.get("reject_probability", 0.0)),
            buffer_capacity=raw_stage.get("buffer_capacity", 0),
            buffer=Buffer(capacity=raw_stage.get("buffer_capacity", 0)),
            next_stage_id=raw_stage.get("next_stage_id"),
            stage_type=StageType(
                str(raw_stage.get("stage_type", StageType.PROCESSING.value))
            ),
            routing_strategy=RoutingStrategy(
                str(
                    raw_stage.get(
                        "routing_strategy",
                        RoutingStrategy.SEQUENTIAL.value,
                    )
                )
            ),
        )
    return stages


def _resolve_entry_stage_ids(raw_stages: list[dict[str, Any]]) -> list[str]:
    """Resolve the entry stages of the configured production line."""
    stage_ids = [str(stage["stage_id"]) for stage in raw_stages]
    referenced_stage_ids = {
        str(stage["next_stage_id"])
        for stage in raw_stages
        if stage.get("next_stage_id") is not None
    }
    entry_stage_ids = [stage_id for stage_id in stage_ids if stage_id not in referenced_stage_ids]
    return entry_stage_ids or [stage_ids[0]]
