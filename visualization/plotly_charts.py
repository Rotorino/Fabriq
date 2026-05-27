"""Interactive Plotly charts for simulation analytics."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
from typing import Any

from domain.models import BatchMetrics, MachineMetrics, StageMetrics


def make_queue_length_chart(result: Any) -> go.Figure:
    """
    Creates an interactive queue length over time chart for each stage.
    """
    from analytics.aggregators import queue_lengths_by_stage
    
    queue_data = queue_lengths_by_stage(result.raw_data)
    fig = go.Figure()
    
    for stage_id, rows in queue_data.items():
        times = [row["timestamp"] for row in rows]
        lengths = [row["queue_length"] for row in rows]
        
        if times and times[-1] < result.simulation_time:
            times.append(result.simulation_time)
            lengths.append(lengths[-1])
            
        fig.add_trace(go.Scatter(
            x=times,
            y=lengths,
            mode='lines+markers',
            name=f"Stage: {stage_id}",
            line_shape='hv'
        ))
        
    fig.update_layout(
        title="Queue Length Over Time",
        xaxis_title="Time",
        yaxis_title="Queue Length",
        hovermode="x unified",
        template="plotly_white"
    )
    return fig


def make_machine_utilization_chart(machine_metrics: list[MachineMetrics]) -> go.Figure:
    """
    Creates a horizontal bar chart of machine utilization.
    """
    ids = [m.machine_id for m in machine_metrics]
    utils = [m.utilization * 100 for m in machine_metrics]
    
    colors = []
    for u in utils:
        if u < 70:
            colors.append("green")
        elif u < 90:
            colors.append("orange")
        else:
            colors.append("red")
            
    fig = go.Figure(go.Bar(
        x=utils,
        y=ids,
        orientation='h',
        marker_color=colors,
        text=[f"{u:.1f}%" for u in utils],
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Machine Utilization (%)",
        xaxis_title="Utilization (%)",
        yaxis_title="Machine",
        xaxis=dict(range=[0, 105]),
        template="plotly_white"
    )
    return fig


def make_batch_time_histogram(batch_metrics: list[BatchMetrics]) -> go.Figure:
    """
    Histogram of batch cycle time distribution.
    """
    completed_times = [m.cycle_time for m in batch_metrics if m.completed]
    
    if not completed_times:
        return go.Figure()
        
    fig = go.Figure(go.Histogram(
        x=completed_times,
        nbinsx=20,
        name="Batches",
        marker_color="skyblue"
    ))
    
    avg_time = sum(completed_times) / len(completed_times)
    fig.add_vline(
        x=avg_time, 
        line_dash="dash", 
        line_color="red"
    )
    
    fig.update_layout(
        title="Batch Cycle Time Distribution",
        xaxis_title="Cycle Time",
        yaxis_title="Batch Count",
        template="plotly_white"
    )
    return fig


def make_scenario_comparison_chart(scenario_results: dict[str, dict[str, Any]]) -> go.Figure:
    """
    Grouped bar chart for comparing scenarios by metrics.
    """
    scenarios = list(scenario_results.keys())
    if not scenarios:
        return go.Figure()
        
    metrics = list(scenario_results[scenarios[0]].keys())
    fig = go.Figure()
    
    for metric in metrics:
        values = [scenario_results[s][metric] for s in scenarios]
        fig.add_trace(go.Bar(
            name=metric,
            x=scenarios,
            y=values,
            text=values,
            textposition='auto',
        ))
        
    fig.update_layout(
        title="Scenario Comparison",
        barmode='group',
        xaxis_title="Scenario",
        yaxis_title="Value",
        legend_title="Metrics",
        template="plotly_white"
    )
    return fig


def make_radar_comparison_chart(scenario_results: dict[str, dict[str, Any]], t: dict[str, str]) -> go.Figure:
    """
    Radar Chart for performance comparison with localization.
    """
    scenarios = list(scenario_results.keys())
    if not scenarios:
        return go.Figure()

    fig = go.Figure()

    for s in scenarios:
        data = scenario_results[s]
        quality = 100 - data.get(t.get("metric_rejection_val", "Rejection %"), 0)
        
        r_values = [
            data.get(t.get("metric_output", "Output"), 0),
            data.get(t.get("metric_utilization", "Avg Utilization (%)"), 0),
            data.get(t.get("metric_throughput", "Throughput"), 0) * 100,
            quality
        ]
        theta = [
            t.get("radar_output", "Output"), 
            t.get("radar_utilization", "Utilization"), 
            t.get("radar_throughput", "Throughput (x100)"), 
            t.get("radar_quality", "Quality")
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=r_values,
            theta=theta,
            fill='toself',
            name=s
        ))

    max_val = 100
    for trace in fig.data:
        if hasattr(trace, 'r') and trace.r:
            max_val = max(max_val, max(trace.r))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max_val])),
        showlegend=True,
        title=t.get("radar_title", "Strategy Efficiency (KPI Radar)")
    )
    return fig


def make_performance_chart(history: list[dict[str, Any]], t: dict[str, str]) -> go.Figure:
    """
    Performance chart (Event Processing Rate) with localization.
    """
    if not history:
        return go.Figure()
        
    ids = [f"#{e['id']}" for e in history]
    workload = [len(e["result"].event_log) for e in history]
    
    fig = go.Figure(go.Scatter(
        x=ids,
        y=workload,
        mode='lines+markers',
        line=dict(color='#6c63ff', width=4),
        marker=dict(size=10, symbol='diamond')
    ))
    
    fig.update_layout(
        title=t.get("perf_title", "Engine Performance"),
        xaxis_title=t.get("perf_x", "Run ID"),
        yaxis_title=t.get("perf_y", "Event Count"),
        template="plotly_dark",
        height=400
    )
    return fig
