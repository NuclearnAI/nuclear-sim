#!/usr/bin/env python3
"""Test script to verify all code examples in the materials README work correctly."""

import sys
sys.path.insert(0, '/Users/shep/Code/nuclear-sim')

# Import base classes
from nuclear_simulator.sandbox.materials.base import Material, Energy
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.phases import BoilingProperties

print("Testing Materials README examples...")
print("=" * 50)

# Test 1: Basic algebraic operations
print("\n1. Testing basic algebraic operations:")
try:
    # Need to define a material class first
    class PWRPrimaryWater(Liquid):
        HEAT_CAPACITY = 5400.0
        DENSITY = 700.0
    
    water_hot = PWRPrimaryWater(m=10.0, U=5e6)   # 10 kg hot water
    water_cold = PWRPrimaryWater(m=5.0, U=1e6)   # 5 kg cold water
    water_mixed = water_hot + water_cold          # 15 kg mixed water
    
    assert water_mixed.m == 15.0
    assert water_mixed.U == 6e6
    print(f"✓ Mixed water: m={water_mixed.m} kg, U={water_mixed.U} J, T={water_mixed.T:.1f} K")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Solid material
print("\n2. Testing Solid material:")
try:
    class UraniumFuel(Solid):
        HEAT_CAPACITY = 300.0
        DENSITY = 10_970.0  # kg/m³

    fuel = UraniumFuel(m=100.0, U=3e7)
    print(f"✓ Fuel: m={fuel.m} kg, V={fuel.V:.6f} m³, density={fuel.rho} kg/m³")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Liquid material
print("\n3. Testing Liquid material:")
try:
    class Water(Liquid):
        HEAT_CAPACITY = 4200.0
        DENSITY = 1000.0  # kg/m³

    water = Water(m=10.0, U=420_000.0)
    print(f"✓ Water: m={water.m} kg, V={water.V} m³, T={water.T:.1f} K")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Gas material
print("\n4. Testing Gas material:")
try:
    class Steam(Gas):
        HEAT_CAPACITY = 2100.0
        MOLECULAR_WEIGHT = 0.018  # kg/mol (H₂O)

    steam = Steam.from_temperature_pressure(m=5.0, T=400.0, P=101325.0)
    print(f"✓ Steam: m={steam.m} kg, V={steam.V:.3f} m³, P={steam.P_ideal:.0f} Pa")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 5: Energy material
print("\n5. Testing Energy material:")
try:
    heat_added = Energy(U=1e6)  # 1 MJ
    print(f"✓ Energy: U={heat_added.U} J, m={heat_added.m} kg, V={heat_added.V} m³")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 6: Phase change system
print("\n6. Testing Phase change system:")
try:
    class WaterBoilingProperties(BoilingProperties):
        T0 = 373.15  # K
        P0 = 101325.0  # Pa
        u0_BOUND = 419_000.0  # J/kg
        u0_UNBOUND = 2_676_000.0  # J/kg
        HEAT_CAPACITY_BOUND = 4200.0  # J/(kg·K)
        HEAT_CAPACITY_UNBOUND = 2100.0  # J/(kg·K)
        MOLECULAR_WEIGHT = 0.018  # kg/mol
    
    class PWRSecondaryWater(Liquid):
        HEAT_CAPACITY = 5000.0
        DENSITY = 740.0
        BOILING_PROPERTIES = WaterBoilingProperties()
        MOLECULAR_WEIGHT = 0.018
    
    water = PWRSecondaryWater.from_temperature(m=100.0, T=560.0)
    
    # Calculate saturation states
    T_sat = water.boiling.T_saturation(P=7e6)
    P_sat = water.boiling.P_saturation(T=559.0)
    
    print(f"✓ Saturation T at 7 MPa: {T_sat:.1f} K")
    print(f"✓ Saturation P at 559 K: {P_sat/1e6:.2f} MPa")
    
    # Check if boiling
    if water.T > T_sat:
        print("✓ State: Superheated (above boiling)")
    elif water.T < T_sat:
        print("✓ State: Subcooled (below boiling)")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 7: Full example from Quick Start
print("\n7. Testing Quick Start example:")
try:
    # Define custom materials
    class UraniumDioxide(Solid):
        HEAT_CAPACITY = 300.0
        DENSITY = 10_970.0

    class PWRPrimaryWater(Liquid):
        HEAT_CAPACITY = 5400.0
        DENSITY = 700.0
        BOILING_PROPERTIES = WaterBoilingProperties()
        MOLECULAR_WEIGHT = 0.018

    class PWRSecondarySteam(Gas):
        HEAT_CAPACITY = 2100.0
        MOLECULAR_WEIGHT = 0.018
        BOILING_PROPERTIES = WaterBoilingProperties()

    # Create materials from scratch
    fuel = UraniumDioxide(m=100.0, U=3e7)

    # Create from temperature (U computed)
    coolant = PWRPrimaryWater.from_temperature(m=1000.0, T=580.0)

    # Create gas from temperature and pressure (V computed)
    steam = PWRSecondarySteam.from_temperature_pressure(m=50.0, T=570.0, P=7e6)

    # Access computed properties
    print(f"✓ Fuel temperature: {fuel.T:.1f} K")
    print(f"✓ Coolant density: {coolant.rho:.1f} kg/m³")
    print(f"✓ Steam pressure: {steam.P_ideal/1e6:.2f} MPa")

    # Mix materials (conserves m, U, V)
    hot_leg = PWRPrimaryWater.from_temperature(m=500.0, T=590.0)
    cold_leg = PWRPrimaryWater.from_temperature(m=500.0, T=560.0)
    mixed = hot_leg + cold_leg
    print(f"✓ Mixed temperature: {mixed.T:.1f} K")

    # Add/remove energy
    tank = PWRPrimaryWater.from_temperature(m=1000.0, T=570.0)
    heat_added = Energy(U=10e6)  # 10 MJ
    tank_heated = tank + heat_added
    print(f"✓ After heating: {tank_heated.T:.1f} K")

    # Time integration with multiplication
    flow_rate = PWRPrimaryWater.from_temperature(m=10.0, T=580.0)  # kg/s
    dt = 0.1  # s
    flow_amount = flow_rate * dt  # 1 kg flows in 0.1 s
    tank_new = tank + flow_amount
    print(f"✓ After flow: m={tank_new.m} kg")

    # Phase change calculations
    if hasattr(coolant, 'boiling'):
        T_sat = coolant.boiling.T_saturation(P=15.5e6)
        print(f"✓ Saturation temperature at 15.5 MPa: {T_sat:.1f} K")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 8: Known issues examples
print("\n8. Testing Known Issues examples:")

# Issue 1: Density calculation
try:
    print("  Testing density calculation...")
    class SomeLiquid(Liquid):
        HEAT_CAPACITY = 4200.0
        DENSITY = 1000.0
    
    material = SomeLiquid(m=10.0, U=1e6)
    print(f"  ✓ Density returns DENSITY constant: {material.rho} kg/m³")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Issue 2: Gas division by zero (should fail)
try:
    print("  Testing gas division by zero...")
    class SomeGas(Gas):
        HEAT_CAPACITY = 2100.0
        MOLECULAR_WEIGHT = 0.018
    
    gas = SomeGas(m=1.0, U=1e5, V=0.0)
    try:
        pressure = gas.P_ideal
        print(f"  ✗ Should have raised error but got P={pressure}")
    except Exception as e:
        print(f"  ✓ Correctly raised error: {type(e).__name__}")
except Exception as e:
    print(f"  ✗ Unexpected error: {e}")

# Issue 4: Energy validation
try:
    print("  Testing Energy validation issue...")
    energy = Energy(U=1e6)
    try:
        energy.validate()
        print(f"  ✗ Validation should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {str(e)[:50]}...")
except Exception as e:
    print(f"  ✗ Unexpected error: {e}")

print("\n" + "=" * 50)
print("Testing complete!")