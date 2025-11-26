# Graphs Module

The Graphs module provides a flexible framework for building simulation graphs composed of nodes, edges, and controllers. This system enables modeling of complex interconnected systems where nodes represent state containers, edges handle mass/energy transfer between nodes, and controllers implement control logic.

## Core Concepts

### Components
The graph system is built on four main component types:

1. **Nodes** - State containers (e.g., tanks, vessels, reactors)
2. **Edges** - Transfer mechanisms between nodes (e.g., pipes, heat exchangers)
3. **Controllers** - Control logic components that read state and send commands
4. **Graphs** - Container components that organize nodes, edges, controllers, and sub-graphs

### Update Cycle

⚠️ **CRITICAL: Update Order is Essential** ⚠️

The update cycle MUST follow this exact order to avoid race conditions and ensure correct simulation behavior:

1. **Edges First** - Calculate flows based on current node states
2. **Nodes Second** - Update states based on calculated flows
3. **Controllers Last** - Read updated states and prepare control actions for next cycle

**WARNING**: Violating this order will cause:
- Race conditions where nodes try to use flows that haven't been calculated yet
- Control lag issues where controllers react to outdated states
- Incorrect simulation results and potential crashes

```python
# ✅ CORRECT UPDATE ORDER
def update(self, dt: float, steps: int = 1) -> None:
    for i in range(steps):
        # 1. Update edges FIRST - calculate flows
        for edge in self.get_edges().values():
            edge.update(dt)
        
        # 2. Update nodes SECOND - integrate flows
        for node in self.get_nodes().values():
            node.update(dt)
        
        # 3. Update controllers LAST - control logic
        for controller in self.get_controllers().values():
            controller.update(dt)
```

## Graph Serialization

The Graph class supports saving and loading complete graph states through serialization. This enables persisting simulations, creating checkpoints, and sharing complex graph configurations.

### Serialization Features

- **Complete State Preservation**: All node states, edge parameters, and controller settings are preserved
- **Connection Integrity**: Graph topology and all interconnections are maintained
- **Subgraph Support**: Nested graphs and complex hierarchies are fully supported
- **Type Safety**: Component types and parameters are preserved for accurate reconstruction

### Basic Usage

```python
# Save a graph to dictionary
graph_data = graph.to_dict()

# Restore from dictionary
restored_graph = Graph.from_dict(graph_data)

# Save to file (example using JSON)
import json
with open("simulation_state.json", "w") as f:
    json.dump(graph.to_dict(), f)

# Load from file
with open("simulation_state.json", "r") as f:
    graph_data = json.load(f)
    loaded_graph = Graph.from_dict(graph_data)
```

### Example: Checkpoint System

```python
# Create a simulation with checkpointing
def run_simulation_with_checkpoints(graph: Graph, total_time: float, checkpoint_interval: float):
    checkpoints = []
    time = 0.0
    dt = 0.1
    
    while time < total_time:
        # Run simulation step
        graph.update(dt)
        time += dt
        
        # Create checkpoint at intervals
        if time % checkpoint_interval < dt:
            checkpoint = {
                "time": time,
                "state": graph.to_dict()
            }
            checkpoints.append(checkpoint)
            print(f"Checkpoint saved at t={time:.1f}")
    
    return checkpoints

# Restore from checkpoint
def restore_checkpoint(checkpoint: dict) -> tuple[float, Graph]:
    time = checkpoint["time"]
    graph = Graph.from_dict(checkpoint["state"])
    return time, graph
```

The serialization system automatically handles all component types, preserving their exact state and configuration for seamless save/restore operations.

## Quick Start Example

Here's a minimal example demonstrating proper usage:

```python
from nuclear_simulator.sandbox.graphs import Graph, Node, Edge, Controller

# Define a simple node with one state variable
class TankNode(Node):
    level: float  # Water level in meters

# Define an edge that transfers water between tanks
class PipeEdge(Edge):
    flow_rate: float = 1.0  # m³/s
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        # Flow from source to target based on level difference
        level_diff = self.node_source.level - self.node_target.level
        return {"level": self.flow_rate * level_diff}

# Define a controller that adjusts flow rate
class FlowController(Controller):
    REQUIRED_CONNECTIONS_READ = ("tank1", "tank2")
    REQUIRED_CONNECTIONS_WRITE = ("pipe",)
    
    def update(self, dt: float) -> None:
        # Read tank levels
        level1 = self.connections_read["tank1"].read()["level"]
        level2 = self.connections_read["tank2"].read()["level"]
        
        # Adjust flow rate based on level difference
        if abs(level1 - level2) > 5.0:
            self.connections_write["pipe"].write({"flow_rate": 2.0})
        else:
            self.connections_write["pipe"].write({"flow_rate": 0.5})

# Build the graph
graph = Graph()
tank1 = graph.add_node(TankNode, name="Tank1", level=10.0)
tank2 = graph.add_node(TankNode, name="Tank2", level=2.0)
pipe = graph.add_edge(PipeEdge, node_source=tank1, node_target=tank2, name="Pipe")
controller = graph.add_controller(
    FlowController,
    connections={"tank1": tank1, "tank2": tank2, "pipe": pipe}
)

# ⚠️ CRITICAL: Follow correct update order!
dt = 0.1
graph.update(dt)  # Edges → Nodes → Controllers
```

## Node System

### Creating Nodes

Nodes are state containers that hold simulation variables:

```python
class ReactorNode(Node):
    temperature: float      # Kelvin
    pressure: float        # Pascals
    power: float          # Watts
    coolant_level: float  # meters
```

### Node Update Process

Nodes update their state by integrating flows from connected edges:

```python
# Node.update_from_graph() automatically:
# 1. Collects incoming flows (positive)
# 2. Collects outgoing flows (negative)
# 3. Integrates: state += net_flow * dt
```

## Edge System

### Creating Edges

Edges calculate and transport flows between nodes:

```python
class HeatExchangerEdge(Edge):
    heat_transfer_coeff: float  # W/K
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        temp_diff = self.get_field_source("temperature") - self.get_field_target("temperature")
        heat_flow = self.heat_transfer_coeff * temp_diff
        
        # Return flow rates (per second)
        return {
            "energy": heat_flow,  # Source loses energy
            "_target": {"energy": heat_flow}  # Target gains energy
        }
```

### Edge Aliasing

⚠️ **WARNING: Aliasing Edge Cases** ⚠️

When using aliasing to map edge flow keys to different node state variables, be aware of these limitations:

```python
# ⚠️ BROKEN: None parameters cause aliasing to fail
edge = graph.add_edge(
    MyEdge, 
    node_source=node1,
    node_target=node2,
    alias_source=None,  # This will cause aliasing to break!
    alias_target={"mass": "water_mass"}
)

# ✅ CORRECT: Omit None parameters or use empty dict
edge = graph.add_edge(
    MyEdge,
    node_source=node1,
    node_target=node2,
    alias_target={"mass": "water_mass"}  # Only specify what you need
)

# ✅ ALSO CORRECT: Use empty dict instead of None
edge = graph.add_edge(
    MyEdge,
    node_source=node1, 
    node_target=node2,
    alias_source={},  # Empty dict works fine
    alias_target={"mass": "water_mass"}
)
```

## Controller System

### Creating Controllers

Controllers implement control logic by reading state and sending commands:

```python
class PIDController(Controller):
    # Define required connections
    REQUIRED_CONNECTIONS_READ = ("sensor",)
    REQUIRED_CONNECTIONS_WRITE = ("actuator",)
    
    # PID parameters
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.01
    setpoint: float = 100.0
    
    def update(self, dt: float) -> None:
        # Read sensor value
        current_value = self.connections_read["sensor"].read()["temperature"]
        
        # Calculate error and PID output
        error = self.setpoint - current_value
        output = self.kp * error  # Simplified P-only control
        
        # Send command to actuator
        self.connections_write["actuator"].write({"valve_position": output})
```

### Signal Validation

⚠️ **Signal Validation Restrictions** ⚠️

Controllers have strict validation for signal connections:

1. **Required connections must be defined** - Both `REQUIRED_CONNECTIONS_READ` and `REQUIRED_CONNECTIONS_WRITE` must be defined as class variables
2. **Connection names must match** - Signal names must exactly match those in the required lists
3. **No dynamic connections** - You cannot add connections with names not in the required lists

```python
# ⚠️ This will raise an error:
class BadController(Controller):
    # Missing REQUIRED_CONNECTIONS_* definitions!
    
    def update(self, dt: float) -> None:
        pass

# ✅ Correct:
class GoodController(Controller):
    REQUIRED_CONNECTIONS_READ = ("sensor1", "sensor2")
    REQUIRED_CONNECTIONS_WRITE = ("valve",)
    
    def update(self, dt: float) -> None:
        pass
```

## Known Issues and Limitations

### 1. Controller and Graph Swapping Not Implemented

⚠️ **BUG**: The `swap_controller()` and `swap_graph()` methods return `NotImplementedError` instead of raising it:

```python
# Current behavior (INCORRECT):
def swap_controller(self, ...):
    return NotImplementedError("...")  # Should be 'raise'

# This means the error is silent and returns the error object!
result = graph.swap_controller(...)  # result is NotImplementedError object
```

**Workaround**: Do not use controller or graph swapping until this is fixed.

### 2. Race Condition in Node Updates

⚠️ **BUG**: `node.update_from_graph()` will crash if edges haven't calculated flows yet:

```python
# ⚠️ WRONG: This will crash with "flows have not been calculated"
for node in nodes:
    node.update(dt)  # Tries to read edge.flows before edges update!
    
# ✅ CORRECT: Always update edges first
for edge in edges:
    edge.update(dt)  # Calculate flows
for node in nodes:
    node.update(dt)  # Now safe to read flows
```

### 3. Aliasing Issues with None Parameters

As mentioned above, passing `None` for aliasing parameters breaks the aliasing system. Always omit the parameter or use an empty dict instead.

### 4. Signal Validation Limitations

- Controllers must define all connections at class level
- No dynamic addition of connections after initialization
- Connection names are strictly validated against required lists

## Best Practices

### 1. Always Follow Update Order

```python
# Create a simple wrapper to ensure correct order
def simulate_step(graph: Graph, dt: float):
    # 1. Edges calculate flows
    for edge in graph.get_edges().values():
        edge.update(dt)
    
    # 2. Nodes integrate flows  
    for node in graph.get_nodes().values():
        node.update(dt)
    
    # 3. Controllers read and command
    for controller in graph.get_controllers().values():
        controller.update(dt)
```

### 2. Use Type Hints

```python
class MyNode(Node):
    temperature: float  # Always specify types
    pressure: float
    
class MyEdge(Edge):
    conductance: float = 1.0  # Include defaults where appropriate
```

### 3. Document Flow Conventions

Always document what your flows represent and their units:

```python
def calculate_flows(self, dt: float) -> dict[str, float]:
    """
    Calculate mass and energy flows.
    
    Returns:
        dict with keys:
        - "mass": Mass flow rate [kg/s]
        - "energy": Energy flow rate [W]
    """
    return {
        "mass": mass_flow_rate,    # kg/s
        "energy": energy_flow_rate  # W (J/s)
    }
```

### 4. Handle Edge Cases in Controllers

```python
def update(self, dt: float) -> None:
    # Read safely with defaults
    sensor_data = self.connections_read["sensor"].read()
    temperature = sensor_data.get("temperature", 293.15)  # Default to room temp
    
    # Validate before writing
    if not 0 <= valve_position <= 1:
        valve_position = max(0, min(1, valve_position))  # Clamp to valid range
    
    self.connections_write["valve"].write({"position": valve_position})
```

## Complete Example: Temperature Control System

Here's a complete example showing proper usage of all components:

```python
from nuclear_simulator.sandbox.graphs import Graph, Node, Edge, Controller

# Define components
class ThermalMass(Node):
    """A node representing a thermal mass."""
    temperature: float  # Kelvin
    heat_capacity: float = 1000.0  # J/K

class HeatFlow(Edge):
    """Edge representing heat conduction."""
    conductance: float = 10.0  # W/K
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        # Q = k * (T_hot - T_cold)
        t_source = self.node_source.temperature
        t_target = self.node_target.temperature
        heat_flow = self.conductance * (t_source - t_target)
        
        # Energy flow from source to target
        return {"energy": heat_flow}  # W
    
    def update_from_signals(self, dt: float) -> None:
        # Allow controller to adjust conductance
        for signal in self.signals_incoming:
            if "conductance" in signal.payload:
                self.conductance = signal.payload["conductance"]

class TemperatureController(Controller):
    """PID controller for temperature regulation."""
    REQUIRED_CONNECTIONS_READ = ("sensor",)
    REQUIRED_CONNECTIONS_WRITE = ("heater",)
    
    setpoint: float = 350.0  # Target temperature (K)
    kp: float = 5.0
    
    def update(self, dt: float) -> None:
        # Read current temperature
        current_temp = self.connections_read["sensor"].read()["temperature"]
        
        # Calculate control action
        error = self.setpoint - current_temp
        control_output = self.kp * error
        
        # Limit conductance to reasonable range
        conductance = max(0.0, min(100.0, control_output))
        
        # Send to heater
        self.connections_write["heater"].write({"conductance": conductance})

# Build system
graph = Graph()

# Add nodes
heater = graph.add_node(ThermalMass, name="Heater", temperature=400.0)
room = graph.add_node(ThermalMass, name="Room", temperature=300.0)
outside = graph.add_node(ThermalMass, name="Outside", temperature=273.0)

# Add edges  
heat_to_room = graph.add_edge(HeatFlow, heater, room, name="HeaterToRoom")
heat_loss = graph.add_edge(HeatFlow, room, outside, name="RoomToOutside")

# Add controller
controller = graph.add_controller(
    TemperatureController,
    connections={"sensor": room, "heater": heat_to_room}
)

# Simulate with correct update order!
for step in range(100):
    graph.update(dt=0.1)  # Edges → Nodes → Controllers
    
    if step % 10 == 0:
        print(f"Step {step}: Room temp = {room.temperature:.1f}K")
```

## Testing

When writing tests, always verify the update order:

```python
def test_update_order():
    """Verify that update order prevents race conditions."""
    graph = create_test_graph()
    
    # This should work fine
    graph.update(dt=0.1)
    
    # But this should fail
    with pytest.raises(ValueError, match="flows have not been calculated"):
        # Try to update nodes before edges
        for node in graph.get_nodes().values():
            node.update(dt=0.1)
```

## Migration Guide

If you're updating from an older version:

1. **Check update order** - Ensure all update loops follow Edges→Nodes→Controllers
2. **Fix aliasing** - Replace `alias_source=None` with omission or empty dict
3. **Define controller connections** - Add `REQUIRED_CONNECTIONS_*` to all controllers
4. **Avoid swap methods** - Don't use `swap_controller()` or `swap_graph()` until fixed

## See Also

- `/nuclear_simulator/sandbox/plants/` - Example usage in plant simulations
- `/nuclear_simulator/sandbox/materials/` - Material property system that integrates with nodes