# Analytics Module Documentation

## Overview

The analytics module is responsible for calculating performance metrics from simulation results. It processes raw simulation data and generates comprehensive statistics for batches, stages, machines, and overall system performance.

## Module Structure

```
analytics/
├── __init__.py
├── aggregators.py      # Data aggregation helpers
├── calculators.py      # Main analytics calculation logic
└── metrics.py          # Low-level metric formulas
```

## Core Functions

### `calculate_analytics(result: SimulationResult) -> dict`

Main entry point for analytics calculation. Takes a simulation result and returns a comprehensive analytics dictionary.

**Returns:**
```python
{
    "scenario_name": str,
    "general": {
        "total_batches": int,
        "completed_batches": int,
        "rejected_batches": int,
        "simulation_time": float,
        "output_units": int,
        "rejected_units": int,
        "throughput": float,  # units per time
        "total_breakdowns": int,
        "total_repair_time": float
    },
    "stages": [StageMetrics, ...],
    "machines": [MachineMetrics, ...],
    "batches": [BatchMetrics, ...]
}
```

### `compare_analytics_runs(analytics_runs: list) -> list`

Compares multiple scenario analytics and generates a comparison table.

**Returns:**
```python
[
    {
        "scenario_name": str,
        "output_units": int,
        "average_cycle_time": float,
        "rejection_rate": float,
        "average_queue_length": float,
        "average_machine_utilization": float,
        "throughput": float,
        "total_breakdowns": int,
        "total_repair_time": float
    },
    ...
]
```

## Metrics Explained

### General Metrics

- **total_batches**: Total number of batches that entered the system
- **completed_batches**: Number of batches that successfully completed all stages
- **rejected_batches**: Number of batches rejected due to quality issues
- **output_units**: Total units produced (sum of completed batch sizes)
- **rejected_units**: Total units rejected (sum of rejected batch sizes)
- **throughput**: Production rate (output_units / simulation_time)
- **total_breakdowns**: Sum of all machine breakdowns across the system
- **total_repair_time**: Total time spent on repairs

### Stage Metrics

- **processed_batches**: Number of batches processed at this stage
- **average_wait_time**: Average time batches spent waiting in queue
- **average_processing_time**: Average time spent processing batches
- **max_queue_length**: Maximum queue length observed
- **utilization**: Average utilization of machines at this stage
- **rejected_batches**: Number of batches rejected at this stage
- **breakdowns**: Number of machine breakdowns at this stage

### Machine Metrics

- **busy_time**: Total time machine was processing
- **idle_time**: Total time machine was idle
- **breakdowns**: Number of breakdowns for this machine
- **average_repair_time**: Average time to repair this machine
- **utilization**: Ratio of busy_time to total simulation time

### Batch Metrics

- **cycle_time**: Total time from arrival to completion/rejection
- **stages_count**: Number of stages in the batch route
- **completed**: Boolean indicating successful completion
- **waited_in_queue**: Boolean indicating if batch experienced queuing

## Usage Examples

### Basic Analytics Calculation

```python
from analytics import calculate_analytics
from engine import SimulationEngine

result = SimulationEngine(
    production_line=line,
    batches=batches,
    simulation_duration=100.0,
    scenario_name="test"
).run()

analytics = calculate_analytics(result)
print(f"Throughput: {analytics['general']['throughput']:.2f} units/time")
print(f"Rejection rate: {analytics['general']['rejected_batches'] / analytics['general']['total_batches']:.1%}")
```

### Scenario Comparison

```python
from analytics import calculate_analytics, compare_analytics_runs

analytics_runs = []
for config_path in ["base.json", "high_load.json", "frequent_breakdowns.json"]:
    result = run_simulation(config_path)
    analytics_runs.append(calculate_analytics(result))

comparison = compare_analytics_runs(analytics_runs)
for row in comparison:
    print(f"{row['scenario_name']}: {row['output_units']} units, "
          f"{row['average_cycle_time']:.2f} avg cycle time")
```

## Performance Considerations

- Analytics calculation is performed after simulation completes
- Memory usage scales linearly with number of events and batches
- For large simulations (>10,000 events), consider streaming analytics
- Aggregation functions use dictionary lookups for O(1) access

## Integration Points

### Input from Engine Module

The analytics module expects `SimulationResult` objects with:
- `events`: List of processed events
- `event_log`: List of event log records
- `batches`: List of batch entities with final states
- `stages`: List of stage entities with final states
- `machines`: List of machine entities with final states
- `simulation_time`: Total simulation duration
- `raw_data`: Dictionary with queue_lengths and machine_activity observations

### Output to Reporting Module

Analytics output is consumed by:
- `reporting.build_report()`: For single scenario reports
- `reporting.build_comparison_report()`: For multi-scenario comparisons
- `visualization.build_charts()`: For chart generation

## Error Handling

The module handles edge cases gracefully:
- Empty batch lists return zero metrics
- Division by zero is prevented with `max(value, 1)` guards
- Missing fields default to 0 or empty lists
- Invalid data types are caught during aggregation

## Testing

See `tests/test_analytics.py` for comprehensive test coverage:
- `test_calculate_analytics_includes_extended_metrics`: Validates all metric fields
- `test_compare_analytics_runs_returns_required_columns`: Validates comparison output
- `test_analytics_handles_zero_batches`: Edge case handling

## Future Enhancements

Potential improvements for future versions:
- Real-time streaming analytics during simulation
- Statistical confidence intervals for metrics
- Trend analysis across multiple runs
- Machine learning-based bottleneck prediction
- Custom metric plugins
