# Fabriq

Fabriq is a modular Python application for discrete-event simulation of a
production line. It loads a JSON or YAML scenario, builds a validated
production model, runs the simulation engine, calculates metrics, exports
reports, and writes SVG charts.

## Architecture

Project modules:

- `domain/`: shared entities, enums, and DTOs
- `scenario/`: config loading, validation, and scenario building
- `engine/`: discrete-event simulation core
- `analytics/`: metrics and comparison logic
- `reporting/`: JSON/CSV/TXT report export
- `visualization/`: SVG chart generation
- `app/`: CLI entrypoint

Detailed docs are in `docs/docs/`:

- `architecture.md`: engine structure and runtime rules
- `event-flow.md`: event lifecycle and stop conditions
- `scenario-module.md`: config format, validation, and scenario builder
- `integration-contract.md`: public DTO and module contracts

## Run

```bash
python -m app.main --config configs/base_scenario.json
```

Scenario comparison is also supported from the CLI:

```bash
python -m app.main --config \
  configs/base_scenario.json \
  configs/high_load.json \
  configs/frequent_breakdowns.json
```

Outputs are written to `results/<scenario_name>/`:

- `report.json`
- `metrics.csv`
- `summary.txt`
- `charts/queue_length.svg`
- `charts/machine_utilization.svg`
- `charts/batch_cycle_time.svg`

When multiple configs are passed, a comparison report is written to
`results/comparison/`:

- `comparison_report.json`
- `comparison.csv`
- `comparison_summary.txt`

Logs are written to `logs/`.

## Scenarios

The repository includes three required scenarios:

- `configs/base_scenario.json`
- `configs/high_load.json`
- `configs/frequent_breakdowns.json`

Configuration rules to keep in mind:

- JSON is required; YAML works when `PyYAML` is installed.
- `batches.route` is mandatory when the line has multiple entry stages.
- `queue_limit` and `buffer_capacity` must be non-negative integers or `null`.
- probabilities such as `breakdown_probability` and `reject_probability` must be in `[0.0, 1.0]`.

## Tests

```bash
python -m unittest discover -s tests
python -m pytest -q
python -m compileall app domain scenario engine analytics reporting visualization tests
```

## CI

GitHub Actions runs Python CI on pushes and pull requests for the main project
branches. The workflow compiles Python packages, runs `unittest` discovery,
runs `pytest`, executes every `configs/*.json` scenario through the CLI, checks
fixed-seed engine repeatability, and uploads `logs/` and `results/` artifacts.
