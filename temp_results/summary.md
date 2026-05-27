# Scenario Report: bottleneck_exit

Slow final stage causing upstream congestion.

## General Metrics
- Total batches: 500
- Completed batches: 154
- Rejected batches: 346
- Output units: 616
- Rejected units: 1384
- Completion rate: 30.80%
- Rejection rate: 69.20%
- Average cycle time: 27.562
- Average queue wait: 1.962
- Throughput: 0.297
- Simulation time: 2074.0
- Total breakdowns: 1214
- Total repair time: 1214.00

## Bottleneck
- Stage: assembly
- Average wait time: 1.140
- Average queue length: 0.516
- Max queue length: 5.0
- Utilization: 0.481

## Problem Stages
- assembly: wait=1.140, avg_queue=0.516, max_queue=5.0, utilization=0.481, downtime=501.000
- cutting: wait=0.728, avg_queue=0.424, max_queue=4.0, utilization=0.482, downtime=516.000
- quality: wait=0.098, avg_queue=2.063, max_queue=3.0, utilization=0.903, downtime=197.000

## Recommendations
- High rejection rate detected (69.2%). Review processing quality and reject thresholds.
- Frequent breakdowns detected (1214 total). Introduce preventive maintenance.
- Stage 'assembly' loses 501.00 time units to repairs. Check machine reliability.
- Stage 'cutting' loses 516.00 time units to repairs. Check machine reliability.

## Performance Insights
- Average machine utilization: 0.622
- Most utilized machine: qc-1
- Least utilized machine: asm-1
- Most problematic stage: assembly
- Efficiency score: 35.57

## Charts
- Not generated