# Materials Module

## Overview

This module provides thermodynamic material representations for nuclear reactor simulations. Materials (coolant, fuel, steam) are modeled as **algebraic objects** that can be added, subtracted, and multiplied - making flow calculations and mixing operations intuitive and natural.

**Key Design Principles**:
- **Algebraic representation**: Materials combine according to conservation laws using simple operators
- **Extrinsic tracking**: We track the three fundamental extrinsic properties (mass, energy, volume)
- **Intrinsic computation**: Properties like temperature, density, and pressure are computed on-the-fly from the extrinsic state
- **Natural syntax**: Code reads like physics equations (`outlet = inlet + heat_added`)

**Primary Use Case**: Thermal-hydraulic simulations of nuclear power plants, where materials flow between components, exchange heat, and undergo phase changes.

---

## Core Philosophy: Materials as Algebraic Objects

In physical systems, materials combine according to conservation laws. This module represents those operations directly in code:

```python
# Physical intuition: combine two water masses
water_hot = PWRPrimaryWater(m=10.0, U=5e6, V=0.014)   # 10 kg hot water
water_cold = PWRPrimaryWater(m=5.0, U=1e6, V=0.007)   # 5 kg cold water
water_mixed = water_hot + water_cold                   # 15 kg mixed water

# Result automatically conserves mass, energy, volume
assert water_mixed.m == 15.0
assert water_mixed.U == 6e6
assert water_mixed.T  # Temperature computed from energy
```

**Supported Operations**:
- **Addition**: Combine materials -> `combined = mat_a + mat_b`
- **Subtraction**: Remove material -> `remaining = tank - withdrawn`
- **Multiplication**: Scale for time steps -> `flow_over_dt = flow_rate * dt`
- **Division**: Split amounts -> `half = material / 2.0`

The multiplication operator is particularly useful for time integration: `material_new = material_old + flow_rate * dt` naturally computes the updated state after a timestep.

**Conservation Rules**:
- Operators automatically conserve m, U, V (extrinsic properties)
- Can only add materials of the same type
- Intrinsic properties (T, ρ, P) are recomputed from the new state

---

## The Material Hierarchy

All materials inherit from the [`Material`](base.py:16) base class. Specialized subclasses add phase-specific behavior:

```
Material (base class)
├── Gas      (ideal gas behavior)
├── Liquid   (incompressible, fixed density)
├── Solid    (incompressible, fixed density)
└── Energy   (special: only carries energy)
```

### Base Material Class

The [`Material`](base.py:16) class provides the foundation. Every material has:

**Extrinsic Properties** (state variables you set):
- `m` - Mass [kg]
- `U` - Internal energy [J] (referenced to 0 K)
- `V` - Volume [m³]

**Intrinsic Properties** (class constants):
- `HEAT_CAPACITY` - Specific heat capacity cv [J/(kg·K)]
- `DENSITY` - Reference density [kg/m³] (for solids/liquids)
- `MOLECULAR_WEIGHT` - Molecular weight [kg/mol] (for gases)
- `P0, T0, u0, LATENT_HEAT` - Saturation parameters (optional)

**Computed Properties** (calculated from state):
- `T` - Temperature [K] from U, m, cv
- `rho` - Density [kg/m³] from m, V
- `cv` - Specific heat capacity [J/(kg·K)]

### Solid

The [`Solid`](solids.py:7) class represents materials with fixed `DENSITY`. Volume is auto-calculated from mass:

```python
class UraniumFuel(Solid):
    HEAT_CAPACITY = 300.0
    DENSITY = 10_970.0  # kg/m³

fuel = UraniumFuel(m=100.0, U=3e7)  # V computed automatically
```

Solids are assumed incompressible (density constant).

### Liquid

The [`Liquid`](liquids.py:8) class is identical to [`Solid`](solids.py:7) - fixed `DENSITY`, auto-calculated volume:

```python
class Water(Liquid):
    HEAT_CAPACITY = 4200.0
    DENSITY = 1000.0  # kg/m³

water = Water(m=10.0, U=420_000.0)  # V = m/DENSITY
```

Liquids are assumed incompressible. The distinction from [`Solid`](solids.py:7) is semantic (for code clarity).

### Gas

The [`Gas`](gases.py:12) class adds ideal gas law behavior (PV = nRT). Gases can be constructed from temperature and pressure:

```python
class Steam(Gas):
    HEAT_CAPACITY = 2100.0
    MOLECULAR_WEIGHT = 0.018  # kg/mol (H₂O)

steam = Steam.from_temperature_pressure(m=5.0, T=400.0, P=101325.0)
# V computed from ideal gas law
```

**Gas-specific properties**:
- `P_ideal` - Pressure [Pa] from ideal gas law
- `cp` - Heat capacity at constant pressure [J/(kg·K)]

Gases are assumed ideal. For real gas behavior, subclass and override [`P_ideal`](gases.py:61).

### Energy

The [`Energy`](base.py:317) class carries **only internal energy** (no mass or volume):

```python
heat_added = Energy(U=1e6)  # 1 MJ, with m=0, V=0
```

**Why Energy Exists**:

Heat transfer happens without mass transfer. [`Energy`](base.py:317) makes this explicit:

```python
# Heat from fission
coolant_heated = coolant_cold + heat_source

# Heat to secondary side  
coolant_cooled = coolant_hot - heat_removed
```

[`Energy`](base.py:317) can be added to any [`Material`](base.py:16) type, affecting only the `U` component while leaving `m` and `V` unchanged.

---

## Key Concepts

### Construction Methods

**1. Direct** - Specify m, U, V:
```python
material = Material(m=10.0, U=1e6, V=0.01)
```

**2. From Temperature** - Specify m, T; U computed:
```python
material = Material.from_temperature(m=10.0, T=300.0, V=0.01)
```

**3. From Temperature and Pressure** - Gases only; V computed:
```python
gas = Gas.from_temperature_pressure(m=5.0, T=400.0, P=101325.0)
```

---


## Quick Start Examples

```python
from nuclear_simulator.sandbox.materials.nuclear import (
    PWRPrimaryWater, 
    PWRSecondarySteam,
    UraniumDioxide
)
from nuclear_simulator.sandbox.materials.base import Energy

# Create materials from scratch
fuel = UraniumDioxide(m=100.0, U=3e7)

# Create from temperature (U computed)
coolant = PWRPrimaryWater.from_temperature(m=1000.0, T=580.0)

# Create gas from temperature and pressure (V computed)
steam = PWRSecondarySteam.from_temperature_pressure(m=50.0, T=570.0, P=7e6)

# Access computed properties
print(f"Fuel temperature: {fuel.T:.1f} K")
print(f"Coolant density: {coolant.rho:.1f} kg/m³")
print(f"Steam pressure: {steam.P_ideal/1e6:.2f} MPa")

# Mix materials (conserves m, U, V)
hot_leg = PWRPrimaryWater.from_temperature(m=500.0, T=590.0)
cold_leg = PWRPrimaryWater.from_temperature(m=500.0, T=560.0)
mixed = hot_leg + cold_leg
print(f"Mixed temperature: {mixed.T:.1f} K")  # Average

# Add/remove energy
tank = PWRPrimaryWater.from_temperature(m=1000.0, T=570.0)
heat_added = Energy(U=10e6)  # 10 MJ
tank_heated = tank + heat_added
print(f"After heating: {tank_heated.T:.1f} K")

# Time integration with multiplication
flow_rate = PWRPrimaryWater.from_temperature(m=10.0, T=580.0)  # kg/s
dt = 0.1  # s
flow_amount = flow_rate * dt  # 1 kg flows in 0.1 s
tank_new = tank + flow_amount
```

---

## Advanced Features

### Validation

The [`validate()`](base.py:124) method checks physical constraints:

```python
material.validate()  # Raises ValueError if invalid
```

**Rules**: Mass, energy, and volume must be non-negative. We don't automatically validate because flow calculations may temporarily produce negative values (representing outflows). Call `validate()` on final physical quantities to ensure they're valid.

### Saturation Calculations

For two-phase flows, materials can compute saturation states using the Clausius-Clapeyron equation:

```python
# Requires P0, T0, LATENT_HEAT, MOLECULAR_WEIGHT to be set
water = PWRSecondaryWater.from_temperature(m=100.0, T=560.0)

T_sat = water.T_saturation(P=7e6)    # Saturation temperature at pressure
P_sat = water.P_saturation(T=559.0)  # Saturation pressure at temperature

# Check if boiling
if water.T > T_sat:
    print("Superheated (above boiling)")
elif water.T < T_sat:
    print("Subcooled (below boiling)")
```

---

## File Structure

```
nuclear_simulator/sandbox/materials/
├── __init__.py        # Package initialization
├── base.py            # Material and Energy base classes
├── gases.py           # Gas class (ideal gas behavior)
├── liquids.py         # Liquid class (incompressible)
├── solids.py          # Solid class (incompressible)
└── README.md          # This file
```

---

## Further Reading

- **Physics module**: [`nuclear_simulator/sandbox/physics/`](../physics) - Thermodynamic calculations
- **Graphs module**: [`nuclear_simulator/sandbox/graphs/`](../graphs) - Using materials in flow networks
- **Plants module**: [`nuclear_simulator/sandbox/plants/`](../plants) - Reactor component implementations
