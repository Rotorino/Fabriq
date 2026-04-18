# Visualization Module Documentation

## Overview

The visualization module generates SVG charts from simulation results and analytics data. It creates lightweight, dependency-free visualizations that can be embedded in reports or viewed in browsers.

## Module Structure

```
visualization/
├── __init__.py
├── charts.py          # Main chart generation functions
└── timeline.py        # Optional event timeline visualization
```

## Chart Types

### 1. Queue Length Over Time

**Function:** `_queue_chart(raw_data, path)`

Shows how queue lengths change during simulation.

**Data source:** `raw_data["queue_lengths"]`

**Use case:** Identify periods of congestion and queue buildup

### 2. Machine Utilization

**Function:** `_machine_utilization_chart(machines, path)`

Bar chart showing utilization ratio for each machine.

**Data source:** `analytics["machines"]`

**Use case:** Identify underutilized or overloaded machines

### 3. Batch Cycle Time

**Function:** `_batch_cycle_time_chart(batches, path)`

Bar chart showing total cycle time for each batch.

**Data source:** `analytics["batches"]`

**Use case:** Identify batches with abnormally long processing times

### 4. Breakdown Distribution

**Function:** `_breakdown_distribution_chart(stages, path)`

Bar chart showing number of breakdowns per stage.

**Data source:** `analytics["stages"]`

**Use case:** Identify stages with reliability issues

### 5. Stage Comparison

**Function:** `_stage_comparison_chart(stages, path)`

Multi-metric comparison showing wait time vs processing time per stage.

**Data source:** `analytics["stages"]`

**Use case:** Compare stage performance and identify bottlenecks

### 6. Throughput Over Time

**Function:** `_throughput_over_time_chart(event_log, path)`

Line chart showing cumulative completed batches over time.

**Data source:** `result.event_log`

**Use case:** Visualize production rate and identify slowdowns

## Main Function

### `build_charts(result, analytics, output_dir) -> list[Path]`

Generates all required charts and returns their file paths.

**Parameters:**
- `result`: SimulationResult object from engine
- `analytics`: Analytics dictionary from analytics module
- `output_dir`: Directory where charts will be saved

**Returns:** List of Path objects pointing to generated SVG files

**Example:**
```python
from visualization import build_charts

chart_paths = build_charts(result, analytics, "results/charts")
# Returns: [
#   Path("results/charts/queue_length.svg"),
#   Path("results/charts/machine_utilization.svg"),
#   Path("results/charts/batch_cycle_time.svg"),
#   Path("results/charts/breakdown_distribution.svg"),
#   Path("results/charts/stage_comparison.svg"),
#   Path("results/charts/throughput_over_time.svg")
# ]
```

## SVG Generation

### Line Charts

Generated using `_line_svg(title, points)` helper function.

**Features:**
- Auto-scaling to fit data range
- Axes with labels
- 720x360px default size
- Blue stroke color (#2f80ed)

**Input format:** `[(x1, y1), (x2, y2), ...]`

### Bar Charts

Generated using `_bar_svg(title, values)` helper function.

**Features:**
- Auto-scaling to maximum value
- Labeled bars
- 720x360px default size
- Green fill color (#27ae60)

**Input format:** `[("label1", value1), ("label2", value2), ...]`

## Design Decisions

### Why SVG?

- **No dependencies**: Pure Python string generation
- **Scalable**: Vector format scales to any size
- **Embeddable**: Can be included in HTML reports
- **Lightweight**: Small file sizes
- **Browser-friendly**: Opens in any modern browser

### Why Not matplotlib/plotly?

- Adds heavy dependencies (numpy, matplotlib, etc.)
- Increases installation complexity
- Overkill for simple production charts
- SVG generation is fast and sufficient

## Customization

### Changing Colors

Edit color codes in chart generation functions:

```python
# In _bar_svg
fill='#27ae60'  # Green bars

# In _line_svg
stroke='#2f80ed'  # Blue line

# In _stage_comparison_chart
fill='#e74c3c'  # Red for wait time
fill='#3498db'  # Blue for processing time
```

### Changing Dimensions

Modify width/height variables:

```python
width = 720
height = 360
```

### Adding New Chart Types

1. Create a new function following the pattern:
```python
def _my_new_chart(data: list[dict], path: Path) -> Path:
    # Process data
    values = [(item["label"], item["value"]) for item in data]
    
    # Generate SVG
    svg = _bar_svg("My Chart Title", values)
    
    # Write to file
    path.write_text(svg, encoding="utf-8")
    return path
```

2. Add to `build_charts()`:
```python
paths = [
    # ... existing charts ...
    _my_new_chart(analytics["my_data"], chart_dir / "my_chart.svg"),
]
```

## Performance

- Chart generation is fast (<10ms per chart)
- Memory usage is minimal (string concatenation)
- No external process spawning
- Suitable for batch generation of hundreds of charts

## Integration

### With Reporting Module

Charts are automatically included in reports:

```python
from reporting import build_report
from visualization import build_charts

chart_paths = build_charts(result, analytics, output_dir / "charts")
report = build_report(
    result=result,
    analytics=analytics,
    scenario_description="...",
    output_dir=output_dir,
    chart_paths=chart_paths,
)
# Report JSON includes chart paths
```

### Standalone Usage

Charts can be generated independently:

```python
from visualization import build_charts

# Generate only charts
chart_paths = build_charts(result, analytics, "output/charts")

# Open in browser
import webbrowser
webbrowser.open(str(chart_paths[0]))
```

## Testing

See `tests/test_reporting.py`:
- `test_charts_generation_creates_all_required_files`: Validates all 6 charts are created

## Future Enhancements

Potential improvements:
- Interactive SVG with JavaScript
- Export to PNG/PDF formats
- Animated charts showing simulation progress
- Customizable color schemes
- Responsive sizing
- Dark mode support
