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
- `BOILING_PROPERTIES` - Boiling phase change behavior (optional)
- `FREEZING_PROPERTIES` - Freezing phase change behavior (optional)
- `P0, T0, u0` - Reference state for energy calculations (optional)

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

## Phase Change System

The module provides a sophisticated phase change system through composition instead of inheritance. This design allows materials to share phase change behavior and enables more flexible modeling of multi-phase systems.

### PhaseChangeProperties Base Class

The [`PhaseChangeProperties`](phases.py:18) class defines the interface for phase change behavior:

```python
class PhaseChangeProperties:
    """Base class for defining phase change behavior of materials."""
    T0: float                     # [K] Reference temperature
    P0: float                     # [Pa] Reference pressure
    u0_BOUND: float              # [J/kg] Internal energy of bound phase at T0
    u0_UNBOUND: float            # [J/kg] Internal energy of unbound phase at T0
    HEAT_CAPACITY_BOUND: float   # [J/(kg·K)] Heat capacity of bound phase
    HEAT_CAPACITY_UNBOUND: float # [J/(kg·K)] Heat capacity of unbound phase
```

**Key Methods**:
- `latent_heat(T)` - Returns the latent heat of phase change [J/kg]
- `T_saturation(P)` - Calculate saturation temperature at given pressure [K]
- `P_saturation(T)` - Calculate saturation pressure at given temperature [Pa]
- `u_saturation_bound(T)` - Internal energy of bound phase at saturation [J/kg]
- `u_saturation_unbound(T)` - Internal energy of unbound phase at saturation [J/kg]

### BoilingProperties Subclass

The [`BoilingProperties`](phases.py:91) class extends `PhaseChangeProperties` specifically for liquid-gas transitions:

```python
class BoilingProperties(PhaseChangeProperties):
    """Defines boiling phase change behavior."""
    MOLECULAR_WEIGHT: float  # [kg/mol] For Clausius-Clapeyron calculations
    
    # Convenience properties
    @property
    def HEAT_CAPACITY_GAS(self):
        return self.HEAT_CAPACITY_UNBOUND
    
    @property
    def HEAT_CAPACITY_LIQUID(self):
        return self.HEAT_CAPACITY_BOUND
```

The `BoilingProperties` class implements the Clausius-Clapeyron relation for accurate saturation calculations.

### Accessing Phase Change Properties

Materials access phase change properties through the `boiling` and `freezing` properties:

```python
# Access boiling properties
water = PWRSecondaryWater.from_temperature(m=100.0, T=560.0)
T_sat = water.boiling.T_saturation(P=7e6)    # Saturation temp at pressure
P_sat = water.boiling.P_saturation(T=559.0)  # Saturation pressure at temp
latent = water.boiling.latent_heat(T=559.0)  # Latent heat

# Check phase state
if water.T > T_sat:
    print("Superheated (above boiling)")
elif water.T < T_sat:
    print("Subcooled (below boiling)")
```

### Defining Materials with Phase Change Properties

Here's how to define materials with phase change behavior:

```python
# Define shared boiling properties
class PWRSecondaryBoilingProperties(BoilingProperties):
    T0 = 500.0                    # Reference temperature [K]
    P0 = 7e6                      # Reference pressure [Pa]
    u0_BOUND = 1_380_000.0       # Liquid internal energy at T0 [J/kg]
    u0_UNBOUND = 2_700_000.0     # Steam internal energy at T0 [J/kg]
    HEAT_CAPACITY_BOUND = 5000.0  # Liquid heat capacity [J/(kg·K)]
    HEAT_CAPACITY_UNBOUND = 2100.0 # Steam heat capacity [J/(kg·K)]
    MOLECULAR_WEIGHT = 0.01801528  # Water molecular weight [kg/mol]

# Define water and steam sharing the same properties
class PWRSecondaryWater(Liquid):
    BOILING_PROPERTIES = PWRSecondaryBoilingProperties()
    DENSITY = 740.0
    MOLECULAR_WEIGHT = PWRSecondaryBoilingProperties.MOLECULAR_WEIGHT
    HEAT_CAPACITY = PWRSecondaryBoilingProperties.HEAT_CAPACITY_BOUND
    P0 = PWRSecondaryBoilingProperties.P0
    T0 = PWRSecondaryBoilingProperties.T0
    u0 = PWRSecondaryBoilingProperties.u0_BOUND

class PWRSecondarySteam(Gas):
    BOILING_PROPERTIES = PWRSecondaryBoilingProperties()
    MOLECULAR_WEIGHT = PWRSecondaryBoilingProperties.MOLECULAR_WEIGHT
    HEAT_CAPACITY = PWRSecondaryBoilingProperties.HEAT_CAPACITY_UNBOUND
    P0 = PWRSecondaryBoilingProperties.P0
    T0 = PWRSecondaryBoilingProperties.T0
    u0 = PWRSecondaryBoilingProperties.u0_UNBOUND
```

This design pattern ensures water and steam share the same thermodynamic properties, maintaining consistency across phase changes.

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
# Import base classes
from nuclear_simulator.sandbox.materials.base import Material, Energy
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.phases import BoilingProperties

# Define custom materials
class UraniumDioxide(Solid):
    HEAT_CAPACITY = 300.0
    DENSITY = 10_970.0

class PWRPrimaryWater(Liquid):
    HEAT_CAPACITY = 5400.0
    DENSITY = 700.0

# Define materials with phase change
class SteamBoilingProperties(BoilingProperties):
    T0 = 373.15
    P0 = 101325.0
    u0_BOUND = 419_000.0
    u0_UNBOUND = 2_676_000.0
    HEAT_CAPACITY_BOUND = 4200.0
    HEAT_CAPACITY_UNBOUND = 2100.0
    MOLECULAR_WEIGHT = 0.018

class Water(Liquid):
    BOILING_PROPERTIES = SteamBoilingProperties()
    HEAT_CAPACITY = SteamBoilingProperties.HEAT_CAPACITY_BOUND
    DENSITY = 1000.0

class Steam(Gas):
    BOILING_PROPERTIES = SteamBoilingProperties()
    HEAT_CAPACITY = SteamBoilingProperties.HEAT_CAPACITY_UNBOUND
    MOLECULAR_WEIGHT = SteamBoilingProperties.MOLECULAR_WEIGHT

# Create materials from scratch
fuel = UraniumDioxide(m=100.0, U=3e7)

# Create from temperature (U computed)
coolant = PWRPrimaryWater.from_temperature(m=1000.0, T=580.0)

# Create gas from temperature and pressure (V computed)
steam = Steam.from_temperature_pressure(m=50.0, T=400.0, P=101325.0)

# Access computed properties
print(f"Fuel temperature: {fuel.T:.1f} K")
print(f"Coolant density: {coolant.rho:.1f} kg/m³")
print(f"Steam pressure: {steam.P_ideal/1e6:.2f} MPa")

# Use phase change properties
water = Water.from_temperature(m=10.0, T=360.0)
T_sat = water.boiling.T_saturation(P=101325.0)
print(f"Water at {water.T:.1f} K, saturation temp: {T_sat:.1f} K")

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

The phase change system provides comprehensive saturation calculations through the composition-based design:

```python
# Using phase change properties for saturation calculations
water = PWRSecondaryWater.from_temperature(m=100.0, T=560.0)

# Calculate saturation properties
T_sat = water.boiling.T_saturation(P=7e6)    # Saturation temperature at pressure
P_sat = water.boiling.P_saturation(T=559.0)  # Saturation pressure at temperature

# Get energy bounds for phase change
u_liquid_sat = water.boiling.u_saturation_liquid(T=559.0)
u_steam_sat = water.boiling.u_saturation_gas(T=559.0)
latent_heat = water.boiling.latent_heat(T=559.0)

# Determine phase state
if water.T > T_sat:
    print("Superheated steam")
elif water.T < T_sat:
    print("Subcooled liquid")
else:
    # At saturation - check energy to determine quality
    u_specific = water.U / water.m
    quality = (u_specific - u_liquid_sat) / latent_heat
    print(f"Two-phase mixture, quality: {quality:.2%}")
```

The Clausius-Clapeyron equation is used internally for accurate pressure-temperature relationships:

```
ln(P/P0) = (L/R) * (1/T0 - 1/T)
```

Where:
- L = Latent heat [J/kg]
- R = Specific gas constant [J/(kg·K)]
- P0, T0 = Reference pressure and temperature

### Mass and Volume Exchange Classes

The [`base`](base.py) module provides specialized exchange classes for representing flows:

- **[`Mass`](base.py:334)** - Represents mass exchange without energy (used internally for flow calculations)
- **[`Volume`](base.py:351)** - Represents volume exchange without mass or energy

These classes follow the same algebraic operations as other materials but are typically used internally by the simulation engine for representing specific types of transfers.

The [`base`](base.py) module also provides specialized exchange classes for representing flows:

- **[`Mass`](base.py)** - Represents mass exchange without energy (used internally for flow calculations)
- **[`Volume`](base.py)** - Represents volume exchange without mass or energy

These classes follow the same algebraic operations as other materials but are typically used internally by the simulation engine for representing specific types of transfers.

---

## Real-World Example: PWR Secondary System

Here's how the phase change system is used in practice for a PWR secondary system:

```python
from nuclear_simulator.sandbox.plants.materials import (
    PWRSecondaryWater, 
    PWRSecondarySteam,
    PWRSecondaryBoilingProperties
)

# Both water and steam share the same boiling properties instance
# This ensures thermodynamic consistency
assert PWRSecondaryWater.BOILING_PROPERTIES is PWRSecondarySteam.BOILING_PROPERTIES

# Create water near saturation
water = PWRSecondaryWater.from_temperature(m=1000.0, T=559.0)
P_operating = 7e6  # 7 MPa operating pressure

# Check saturation state
T_sat = water.boiling.T_saturation(P_operating)
print(f"At {P_operating/1e6:.1f} MPa, T_sat = {T_sat:.1f} K")
print(f"Water subcooling: {T_sat - water.T:.1f} K")

# Simulate heating to saturation
heat_to_sat = water.m * water.cv * (T_sat - water.T)
water_at_sat = water + Energy(U=heat_to_sat)
print(f"Water at saturation: {water_at_sat.T:.1f} K")

# Phase change - add latent heat
latent_total = water.m * water.boiling.latent_heat(T_sat)
steam = water_at_sat + Energy(U=latent_total)
# Note: In practice, you'd use PWRSecondarySteam class after phase change

# The steam now has the energy of saturated steam
u_steam_expected = water.boiling.u_saturation_gas(T_sat)
u_steam_actual = steam.U / steam.m
print(f"Steam specific energy: {u_steam_actual/1e6:.2f} MJ/kg")
print(f"Expected: {u_steam_expected/1e6:.2f} MJ/kg")
```

This example demonstrates:
- Shared phase change properties between related materials
- Saturation calculations for design and operation
- Energy requirements for phase transitions
- Consistent thermodynamic properties across phases

---

## File Structure

```
nuclear_simulator/sandbox/materials/
├── __init__.py            # Package initialization
├── base.py                # Material, Energy, Mass, and Volume base classes
├── gases.py               # Gas class (ideal gas behavior)
├── liquids.py             # Liquid class (incompressible)
├── solids.py              # Solid class (incompressible)
├── phases.py              # Phase change properties classes
└── README_materials.md    # This file
```

---

## Further Reading

- **Physics module**: [`nuclear_simulator/sandbox/physics/`](../physics) - Thermodynamic calculations
- **Graphs module**: [`nuclear_simulator/sandbox/graphs/`](../graphs) - Using materials in flow networks
- **Plants module**: [`nuclear_simulator/sandbox/plants/`](../plants) - Reactor component implementations