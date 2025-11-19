# Physics Module

## Overview

This module provides fundamental thermodynamic and fluid mechanics equations used throughout the simulator. It includes physical constants, thermodynamic calculations, phase transition computations, and fluid flow models.

## Module Structure

### Constants (`constants.py`)
- **`UNIVERSAL_GAS_CONSTANT`**: 8.314462618 J/(mol·K) - Universal gas constant

### Thermodynamics (`thermodynamics.py`)
Functions for temperature-energy conversions:
- **`calc_temperature_from_energy(U, m, cv, T0, u0, eps)`**: Calculate temperature from internal energy
  - Converts internal energy to temperature using specific heat capacity
  - Accounts for reference temperature and energy offsets
- **`calc_energy_from_temperature(T, m, cv, T0, u0)`**: Calculate internal energy from temperature
  - Inverse operation of temperature calculation
  - Used by materials module for state initialization

### Phase Transitions (`phases.py`)
Saturation state calculations using Clausius-Clapeyron relations:
- **`calc_saturation_temperature(P, L, P0, T0, MW)`**: Calculate saturation temperature at given pressure
  - Used for determining boiling/condensation points
  - Essential for two-phase flow modeling
- **`calc_saturation_pressure(T, L, P0, T0, MW)`**: Calculate saturation pressure at given temperature
  - Determines vapor pressure for phase change calculations
  - Critical for steam generator and condenser modeling

### Gas Properties (`gases.py`)
Ideal gas law computations:
- **`calc_pressure_ideal_gas(n, T, V, eps)`**: Calculate pressure using ideal gas law
  - For isovolumetric (constant volume) processes
  - Returns pressure in Pascals
- **`calc_volume_ideal_gas(n, T, P, eps)`**: Calculate volume using ideal gas law
  - For isobaric (constant pressure) processes
  - Returns volume in cubic meters

### Fluid Flow (`fluids.py`)
Mass flow rate calculations for pipes and channels:
- **`calc_incompressible_mass_flow(P1, P2, rho, D, L, f, K_minor, eps)`**: Darcy-Weisbach equation for liquids
  - Models pressure-driven flow in pipes
  - Accounts for friction and minor losses
  - Automatically handles flow direction
- **`calc_compressible_mass_flow(P1, P2, T1, T2, MW, D, L, f, K_minor, eps)`**: Isothermal compressible flow equations
  - For gas flow through pipes
  - Uses isothermal approximation for long pipes
  - Handles bi-directional flow based on pressure gradient

## Key Features

1. **Conservation-based**: All equations respect mass and energy conservation laws
2. **Bi-directional flow**: Flow functions automatically handle direction based on pressure differences
3. **Numerical stability**: Small epsilon values prevent division by zero
4. **SI units**: All functions use standard SI units consistently
5. **Reference states**: Support for reference temperatures and energies in thermodynamic calculations

## Usage Examples

```python
from nuclear_simulator.sandbox.physics import (
    calc_temperature_from_energy,
    calc_saturation_temperature,
    calc_incompressible_mass_flow,
    UNIVERSAL_GAS_CONSTANT
)

# Convert energy to temperature
T = calc_temperature_from_energy(U=5e6, m=10.0, cv=4200.0)  # Water heating

# Find boiling point at pressure
T_boil = calc_saturation_temperature(
    P=7e6,           # 7 MPa
    L=1.96e6,        # Latent heat of water
    P0=101325,       # Reference: 1 atm
    T0=373.15,       # Reference: 100°C
    MW=0.018         # Water molecular weight
)

# Calculate pipe flow
m_dot = calc_incompressible_mass_flow(
    P1=7.5e6,        # Inlet pressure
    P2=7.0e6,        # Outlet pressure
    rho=700.0,       # Water density
    D=0.1,           # Pipe diameter
    L=10.0,          # Pipe length
    f=0.02           # Friction factor
)
```

## Integration with Other Modules

- **Materials module**: Uses thermodynamic functions for property calculations
- **Plants module**: Employs flow equations for pipe and pump modeling
- **Graphs module**: Leverages physics equations in edge flow calculations

## Available Functions

### Thermodynamics
- `calc_temperature_from_energy(U, m, cv, T0, u0, eps)`
- `calc_energy_from_temperature(T, m, cv, T0, u0)`

### Phase Transitions
- `calc_saturation_temperature(P, L, P0, T0, MW)`
- `calc_saturation_pressure(T, L, P0, T0, MW)`

### Gas Properties
- `calc_pressure_ideal_gas(n, T, V, eps)`
- `calc_volume_ideal_gas(n, T, P, eps)`

### Fluid Flow
- `calc_incompressible_mass_flow(P1, P2, rho, D, L, f, K_minor, eps)`
- `calc_compressible_mass_flow(P1, P2, T1, T2, MW, D, L, f, K_minor, eps)`

These functions form the physics foundation for the entire nuclear reactor simulation framework.