"""Build validated domain objects from raw scenario configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.entities import Batch, Machine, ProductionLine, Stage
from domain.models import ScenarioConfig
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
    stages = _build_stages(config["stages"])
    line = ProductionLine(stages=stages)
    scenario = ScenarioConfig(
        name=str(config.get("scenario_name", "default")),
        description=str(config.get("description", "")),
        simulation_duration=float(config.get("simulation_duration", 100.0)),
        seed=config.get("seed"),
    )
    batches = generate_batches(config["batches"], list(stages.keys()))
    return ScenarioInput(line, batches, scenario)


def _build_stages(raw_stages: list[dict[str, Any]]) -> dict[str, Stage]:
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
            next_stage_id=raw_stage.get("next_stage_id"),
        )
    return stages
