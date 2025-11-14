# Graph-Based Dynamics Simulation Module

## Overview

This module provides a framework for simulating dynamic systems by modeling them as directed graphs. It's designed for systems where **conserved quantities** (mass, energy, heat, money, etc.) flow between components following conservation laws.

**Key Principle**: The graph structure enforces perfect conservation - what flows out of one node must flow into another, with no losses or gains in the network itself.

## Core Architecture

The module is built around **4 major classes**:

1. **`Node`** - Holds state variables (e.g., temperature, mass, pressure)
2. **`Edge`** - Flows conserved quantities between nodes
3. **`Controller`** - Modifies dynamics via control signals (e.g., opens/closes valves)
4. **`Graph`** - Manages the network structure and orchestrates updates

All classes inherit from a `Component` base class and use **Pydantic**, making it trivial to create custom subclasses by simply declaring desired attributes.

---

## Pydantic Integration

The entire module leverages Pydantic's `BaseModel`, which means we can create Node by simply specifying their attributes, as a dea structure:

```python
# Creating a custom node is this simple:
class TankNode(Node):
    mass: float                # kg of fluid
    pressure: float            # Pa
    temperature: float = 300   # K
```

That's it! Pydantic handles:
- Automatic validation
- Type checking
- Field introspection

No need to write `__init__`, getters, setters, or validation logic.

**Important:** Although Pydantic typically handles serialization / deserialization, our `graphs` module overwrites many checks used in serialization, and also allows fields to have nonserializable values. For this reason, it should not be assumed that graphs written in our module can be serialized. 

---

## Component Roles

### Nodes: State Holders

**Nodes store state variables** that represent the system's current condition.

**Examples**:
- A fuel tank with mass, temperature, and chemical composition
- A reactor core with power level, coolant temperature, and neutron flux
- A bank account with balance and interest rate

**Responsibilities**:
- Hold state variables
- Automatically integrate flows from connected edges
- Optionally implement internal dynamics (e.g., radioactive decay, chemical reactions)

### Edges: Flow Connectors

**Edges transfer conserved quantities** between nodes following conservation laws.

**Key Property**: Flows are **conservative** - what leaves the source node equals what enters the target node.

**Examples**:
- A pipe flowing coolant (mass, energy) from reactor -> heat exchanger
- A heat conductor transferring thermal energy between components
- A financial transaction moving money between accounts

**Responsibilities**:
- Calculate flow rates based on node states
- Return flows as dictionaries: `{"mass": 10.5, "energy": 1000}`
- Flows are **rates** (per second), not absolute quantities

### Controllers: System Actuators

**Controllers modify system behavior** by reading states and sending control signals.

**Why separate from edges?** Controllers represent **external interventions** (operators, automated systems, safety logic) rather than physical connections.

**Examples**:
- A valve controller that opens/closes based on pressure readings
- A reactor protection system that initiates SCRAM on high temperature
- A PID controller maintaining setpoints

**Responsibilities**:
- Read states from nodes/edges via `Signal` connections
- Implement control logic in their `update()` method
- Write commands to nodes/edges to modify behavior

**The Monitor Attribute**:

Controllers automatically maintain a `monitor` dictionary that provides convenient access to all monitored values:

```python
class MyController(Controller):
    REQUIRED_CONNECTIONS_READ = ("sensor1", "sensor2")
    REQUIRED_CONNECTIONS_WRITE = ("actuator",)
    
    def update(self, dt: float) -> None:
        # The default update() populates self.monitor automatically
        super().update(dt)  # Call this if you override update()
        
        # Access monitored values directly
        temp = self.monitor["sensor1"]["temperature"]
        pressure = self.monitor["sensor2"]["pressure"]
        
        # Implement control logic...
        if temp > 500:
            self.connections_write["actuator"].write({"valve_open": False})
```

**Key points**:
- The base `update()` method automatically populates `self.monitor` with all read signal data
- Access monitored values via `self.monitor["signal_name"]["state_variable"]`
- Useful for logging, debugging, and cleaner control logic
- If you override `update()`, call `super().update(dt)` first to populate the monitor

#### Signals: Information Connectors

**`Signal` objects are the communication mechanism** between controllers and components.

**Key Properties**:
- Signals carry information (not mass/energy like Edges)
- Each Signal connects exactly one Controller to one Node/Edge
- Signals have a `payload` dictionary for data transfer

**Think of Signals as an extension of Controllers** - they exist solely to separate the control logic (in Controller) from the communication mechanism (Signal). This separation makes the code cleaner and more modular.

**Usage**:
```python
# Controller reads state via Signal
node_state = self.connections_read["sensor"].read()  # Returns dict of node state

# Controller writes commands via Signal
self.connections_write["actuator"].write({"valve_position": 0.5})
```

### Graphs: Network Orchestrators

**Graphs manage the network structure** and coordinate updates.

**Features**:
- Add/retrieve nodes, edges, controllers by ID or name
- Support hierarchical sub-graphs for modular design
- Thread-safe ID allocation
- Orchestrate update cycle across all components

---

## The Update Cycle ⚠️ CRITICAL

The update order is **Edges -> Nodes -> Controllers**. This sequence is essential for:
1. **Perfect conservation** - flows are calculated before being integrated
2. **Easy accounting** - all flows for a timestep are computed simultaneously
3. **Controller latency** - control actions take effect in the next timestep (realistic behavior)

```python
def update(self, dt: float):
    # 1. Calculate all flows (based on CURRENT node states)
    for edge in self.get_edges().values():
        edge.update(dt)
    
    # 2. Integrate flows into nodes (updates their states)
    for node in self.get_nodes().values():
        node.update(dt)
    
    # 3. Controllers react to NEW states (commands take effect next cycle)
    for controller in self.get_controllers().values():
        controller.update(dt)
```

**Why this matters**:
- Flows see consistent node states (no partial updates)
- Conservation is mathematically guaranteed
- Control actions show realistic one-timestep delay

---

## The Three Update Methods

Every component has **three update hooks** that are called in sequence:

### 1. `update_from_signals(dt)` 
- **Purpose**: Apply control signals from controllers
- **Default behavior**: Sets component attributes to match signal payloads
- **When to override**: Rarely - default usually works
- **Example**: A valve receiving an "open_fraction" command from a controller

### 2. `update_from_graph(dt)`
- **Purpose**: Update based on network connectivity
- **For Edges**: Calculate flows (MUST implement `calculate_flows`)
- **For Nodes**: Integrate flows from connected edges (automatic)
- **When to override**: 
  - Edges: Always (implement `calculate_flows`)
  - Nodes: Never (handled automatically)

### 3. `update_from_state(dt)`
- **Purpose**: Internal dynamics independent of network
- **Default behavior**: No-op
- **When to override**: When component has time-dependent behavior
- **Examples**:
  - A fuel node that heats up from fission
  - A pipe that corrodes over time
  - A battery that self-discharges

**Typical User Workflow**:
- **For Edges**: Implement `calculate_flows()` (required)
- **For Nodes/Edges with dynamics**: Optionally override `update_from_state()`
- **For Controllers**: Implement `update()` with all control logic
- Everything else is handled automatically!

---

## Implementing `calculate_flows()` - The Heart of the System

The `calculate_flows()` method is **where physics happens**. It must return a dictionary of flow **rates** (quantities per second).

### Basic Flow (Most Common Case)

```python
class PipeEdge(Edge):
    conductance: float  # Flow coefficient
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        # Recommended: Use helper methods (handles aliasing automatically)
        delta_pressure = self.get_field_source("pressure") - self.get_field_target("pressure")
        source_temp = self.get_field_source("temperature")
        
        return {
            "mass": self.conductance * delta_pressure,
            "energy": self.conductance * delta_pressure * source_temp
        }
```

**Key Points**:
- Returns `dict[str, float]` where keys match node state variables
- Values are **rates** (per second), not absolute changes
- **Recommended**: Use `self.get_field_source(key)` and `self.get_field_target(key)` helper methods
  - These automatically handle aliasing (see Advanced section below)
  - Alternative: Direct access via `self.node_source.attribute` works but doesn't support aliasing
- The node's `update_from_graph()` automatically integrates: `state += flow_rate * dt`

### Flow Sign Convention

**Positive flows leave source, enter target**:
```
Source Node --[+10 kg/s]--> Target Node
```
- Source loses: `-10 * dt` kg
- Target gains: `+10 * dt` kg

Conservation is automatic - no need to worry about signs!

---

## Advanced Flow Features

### Aliasing: Different Variable Names

When source and target have different names for the same quantity:

```python
class HeatExchangerEdge(Edge):
    def __init__(self, node_source, node_target, **data):
        super().__init__(
            node_source=node_source,
            node_target=node_target,
            alias_source={"thermal_energy": "Q_hot"},    # Source calls it Q_hot
            alias_target={"thermal_energy": "Q_cold"},   # Target calls it Q_cold
            **data
        )
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        # Use the canonical name in flows
        return {"thermal_energy": self.calculate_heat_transfer()}
```

The aliasing system automatically maps:
- `thermal_energy` -> `Q_hot` for source node
- `thermal_energy` -> `Q_cold` for target node

Access aliased fields with helper methods:
```python
source_temp = self.get_field_source("thermal_energy")  # Reads node_source.Q_hot
target_temp = self.get_field_target("thermal_energy")  # Reads node_target.Q_cold
```

### Node-Specific Flows: `_source` and `_target`

⚠️ **Advanced Use Only** - For non-conservative transformations (rare!)

When quantities transform between source and target (e.g., chemical reactions, phase changes):

```python
class ReactionEdge(Edge):
    def calculate_flows(self, dt: float) -> dict[str, float]:
        reaction_rate = self.calculate_reaction_rate()
        return {
            "_source": {
                "fuel": -reaction_rate,      # Fuel consumed at source
                "oxidizer": -reaction_rate
            },
            "_target": {
                "products": reaction_rate,    # Products created at target
                "heat": reaction_rate * self.heat_of_reaction
            }
        }
```

**When to use**:
- Chemical reactions (reactants -> products)
- Phase changes (liquid -> gas with different properties)
- Bifurcating flows (one stream splits into two with different compositions)

**Warning**: This bypasses conservation checks - use only when physically justified!

---

## File Structure

```
nuclear_simulator/sandbox/graphs/
├── __init__.py          # Public API exports
├── base.py              # Component base class
├── nodes.py             # Node class
├── edges.py             # Edge class
├── controllers.py       # Controller and Signal classes
├── graphs.py            # Graph class and ID management
├── utils.py             # Nested attribute helpers
└── README.md            # This file
```

---

## Quick Start Example

```python
from nuclear_simulator.sandbox.graphs import Graph, Node, Edge, Controller

# 1. Define custom components
class Tank(Node):
    volume: float     # m³
    mass: float       # kg
    elevation: float  # m (height above reference)

class Pipe(Edge):
    diameter: float  # m
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        # Simple gravity-driven flow
        height_diff = self.node_source.elevation - self.node_target.elevation
        flow_rate = self.diameter**2 * height_diff * 9.81
        return {"mass": flow_rate}

class ValveController(Controller):
    REQUIRED_CONNECTIONS_READ = ("tank_level",)
    REQUIRED_CONNECTIONS_WRITE = ("valve",)
    
    def update(self, dt: float) -> None:
        level = self.connections_read["tank_level"].read()["mass"]
        # Close valve if level too low
        if level < 10.0:
            self.connections_write["valve"].write({"diameter": 0.0})

# 2. Build graph
g = Graph()
tank1 = g.add_node(Tank, name="Tank1", volume=100, mass=50, elevation=10)
tank2 = g.add_node(Tank, name="Tank2", volume=100, mass=20, elevation=0)
pipe = g.add_edge(Pipe, node_source=tank1, node_target=tank2, diameter=0.1)

# 3. Simulate
for _ in range(100):
    g.update(dt=0.1)
    print(f"Tank1: {tank1.mass:.1f} kg, Tank2: {tank2.mass:.1f} kg")
```

---

## Key Takeaways

✅ **Use Nodes** for state storage  
✅ **Use Edges** for conservative flows between nodes  
✅ **Use Controllers** for external interventions and control logic  
✅ **Use Graphs** to manage the network and orchestrate updates  

✅ **Implement `calculate_flows()`** - this is where your physics lives  
✅ **Remember**: Flows are rates (per second), not quantities  
✅ **Trust the update order**: Edges -> Nodes -> Controllers guarantees conservation  

⚠️ **Rarely needed**: Using `_source`/`_target`  

---

## Further Reading

- See test functions in each file for working examples
- Check `nuclear_simulator/sandbox/plants/` for real-world implementations
- Pydantic documentation: https://docs.pydantic.dev/
