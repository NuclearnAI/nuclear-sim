# Plants Module

## Overview

**ACCURATE AS OF 11/10/2025. KEEP IN MIND THAT THIS MODULE IS IN DEVELOPMENT AND THUS THE README MAY NOT REFLECT THE CURRENT STATE OF THE MODULE WITH PERFECT FIDELITY.**

This module implements concrete nuclear reactor components and systems using the graph-based simulation framework. It builds on three foundational modules:

- **[`graphs`](../graphs)** - Provides the graph structure (Nodes, Edges, Controllers, Graphs)
- **[`materials`](../materials)** - Provides thermodynamic materials (coolant, fuel, steam)  
- **[`physics`](../physics)** - Provides physical equations (flow calculations, thermodynamics)

The plants module combines these foundations to model complete nuclear power plants as interconnected networks of physical components.

***IMPORTANT:*** This code was designed to be understandable and scalable, not necesarily fast. The philosophy is that speed optimizations can happen after the core logic is in place. For this reason the code in its current form is slow compared to other simulators. 

---

## Graph-Based Architecture

### Plants as Networks

We model nuclear plants as **directed graphs** where:

- **Nodes** represent physical components (vessels, heat sources, boundaries)
- **Edges** represent physical connections (pipes, pumps, heat exchangers)
- **Materials** flow through the network following conservation laws

This approach naturally captures plant topology and enforces mass/energy conservation automatically.

```
[Reactor Core] --pipe--> [Steam Generator] --valve--> [Turbine]
      ↑                          ↓
      └----------pump------------┘
```

Each node maintains its own state (pressure, temperature, material inventory), while edges calculate flows based on physical laws.

### Vessel Nodes

Most nodes are **vessels** - containers that hold materials. Vessels come in several varieties:

- **Single-phase vessels** hold one material (liquid or gas) with pressure computed from volume
- **Multi-phase vessels** hold multiple materials simultaneously (e.g., water + steam in a drum)
- **Boundary vessels** represent infinite sources/sinks for open-loop testing

Example single-phase vessel with liquid coolant:
```python
class Coolant(LiquidVessel):
    P0: float = 15.5e6              # Baseline pressure
    liquid: PWRPrimaryWater         # Contained material
```

Vessels automatically integrate material flows from connected edges and update their contents each timestep.

### Flow Edges

Edges calculate and move materials between nodes based on physical laws:

- **Hydraulic flows** use pressure-driven equations (Darcy-Weisbach for incompressible, isentropic for compressible)
- **Controlled flows** implement pumps and valves with setpoints
- **Thermal couplings** transfer heat without mass transfer

Example pressure-driven pipe:
```python
pipe = LiquidPipe(
    node_source=tank1,
    node_target=tank2,
    D=0.90,      # Geometry
    L=15.0,
    f=0.015      # Friction
)
```

The physics module provides the underlying flow calculations, while edges handle the graph connectivity and material movement.

### Hierarchical Subgraphs

Complex plants are built hierarchically using **subgraphs**. Each major system (reactor, steam generator, turbine, etc.) is its own `Graph` that encapsulates its internal components and can be embedded in a larger plant graph.

This hierarchical approach:
- **Organizes** complex systems into manageable subsystems
- **Encapsulates** implementation details
- **Enables** modular development and testing
- **Allows** multiple instances of the same component type

```python
plant = Plant()

# Add subsystems as subgraphs
reactor = plant.add_graph(Reactor)
steam_gen = plant.add_graph(SteamGenerator)

# Connect them with edges
plant.add_edge(Pipe, reactor.outlet, steam_gen.inlet)
```

---

## Quick Example

```python
from nuclear_simulator.sandbox.plants import Plant

# Create plant with default configuration
plant = Plant()

# Simulate
dt = 0.001  # timestep in seconds
for i in range(1000):
    plant.update(dt)
    # Access state through plant.monitor or component attributes
```

This creates a complete PWR system, integrates thermal-hydraulic behavior over time, and maintains conservation of mass and energy throughout.

---

## Design Philosophy

**High-Level Modeling**: Components abstract away internal complexity. Implementation details are handled by physics functions and material properties.

**Conservation by Construction**: The graph structure automatically enforces conservation laws. What flows out of one node must flow into another.

**Physical Intuition**: Code structure mirrors plant topology. Reading the graph construction shows the flow paths and connections.

**Modular Development**: Systems can be built and tested independently, then connected. Subsystems don't need to know about each other's internals.

**Incremental Complexity**: Start simple, add detail progressively without restructuring.

---

## Further Reading

- **Vessels module**: `nuclear_simulator/sandbox/plants/vessels/` - Container implementations
- **Examples**: See test functions in each file for working examples
- **Component inventory**: See `_list_of_components.md` for components being implemented
