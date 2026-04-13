# Fabriq

Fabriq is a modular Python application for discrete-event simulation of a
production line. It loads a JSON scenario, builds a validated production model,
runs the simulation engine, calculates metrics, exports reports, and writes SVG
charts.

## Run

```bash
python -m app.main --config configs/base_scenario.json
```

Outputs are written to `results/<scenario_name>/`:

- `report.json`
- `metrics.csv`
- `summary.txt`
- `charts/queue_length.svg`
- `charts/machine_utilization.svg`
- `charts/batch_cycle_time.svg`

Logs are written to `logs/`.

## Scenarios

The repository includes three required scenarios:

- `configs/base_scenario.json`
- `configs/high_load.json`
- `configs/frequent_breakdowns.json`

## Tests

```bash
python -m unittest discover -s tests
python -m compileall app domain scenario engine analytics reporting visualization tests
```
