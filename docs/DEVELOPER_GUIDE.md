# Developer Guide: Fabriq Architecture & Core Logic

This guide provides a deep technical walkthrough of the Fabriq simulation engine.

## 1. Modular Architecture

Fabriq uses a decoupled, event-driven design:

- **`domain/`**: Pure data entities (`Batch`, `Machine`, `Stage`).
- **`engine/`**: The reactive core. Implements the Event Loop.
- **`scenario/`**: Factory layer that parses JSON into Domain objects.
- **`analytics/`**: Aggregates the `EventLog` into performance metrics.

---

## 2. Core Engine: The Event Loop

The simulation follows the **Discrete Event Simulation (DES)** pattern (`engine/simulator.py`).

### Execution Flow:
1. **Bootstrap**: Clones input entities to prevent mutation.
2. **Initial Scheduling**: Places `BATCH_ARRIVAL` events into the priority queue.
3. **Processing**:
   - Pops the event with the lowest timestamp.
   - Dispatches it to the corresponding handler in `engine/handlers.py`.
4. **Safety**: A cap on events per timestamp prevents infinite zero-time loops.

---

## 3. UI/UX Implementation Details

The Streamlit UI (`app/ui.py`) has been upgraded with:
- **Dynamic Visualization**: Uses `st.graphviz_chart` to render the `ProductionLine` structure. It maps stages and their machines into a directed graph.
- **Session History**: Uses `st.session_state["simulation_history"]` to store results as dictionaries, allowing for real-time comparison without re-running simulations.
- **Reactive Editor**: The JSON editor syncs with the visualization, allowing users to see structural changes immediately.

---

## 4. Analytical Metrics

- **`MachineMetrics`**: Tracks `utilization`, `breakdowns`, and `downtime_time`.
- **`StageMetrics`**: Provides time-weighted averages for queue lengths.
- **`BatchMetrics`**: Calculates total cycle time and total waiting time.

---

## 5. Renaming & Human-Readability

The system now prioritizes the `name` field of entities over their `id` for display purposes. Developers should ensure that while `machine_id` remains unique for logic, the `name` field is populated with a user-friendly Russian string for the UI.
