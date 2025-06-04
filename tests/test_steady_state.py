#!/usr/bin/env python3
"""
Test script to verify steady state operation with the new reactivity model

This script tests the nuclear simulator to ensure that:
1. The reactor can maintain steady state operation without early shutdown
2. The reactivity balance is correct
3. All PWR physics components are working properly
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from simulator.core.sim import NuclearPlantSimulator, ReactorState
from systems.primary.reactor.reactivity_model import (
    ReactivityModel,
    create_equilibrium_state,
)


def test_reactivity_model():
    """Test the reactivity model components"""
    print("Testing Reactivity Model Components")
    print("=" * 50)
    
    # Create equilibrium state with proper PWR rod position
    state = create_equilibrium_state(power_level=100.0, control_rod_position=95.0, auto_balance=True)
    
    # Create reactivity model
    model = ReactivityModel()
    
    # Calculate total reactivity
    total_reactivity, components = model.calculate_total_reactivity(state)
    
    print(model.get_reactivity_summary(state))
    
    # Test critical boron calculation
    critical_boron = model.calculate_critical_boron_concentration(state)
    print(f"\nCritical boron concentration: {critical_boron:.1f} ppm")
    
    # Verify reactivity is near critical
    if abs(total_reactivity) < 100:  # Within 100 pcm of critical
        print("✅ Reactivity model is properly balanced for steady state")
    else:
        print(f"❌ Reactivity model is not balanced: {total_reactivity:.1f} pcm")
    
    return abs(total_reactivity) < 100


def test_steady_state_operation():
    """Test steady state operation for extended period"""
    print("\nTesting Steady State Operation")
    print("=" * 50)
    
    # Create simulator with equilibrium initial state
    sim = NuclearPlantSimulator(dt=1.0)
    
    # Set equilibrium initial state with proper PWR rod position
    equilibrium_state = create_equilibrium_state(power_level=100.0, control_rod_position=95.0, auto_balance=True)
    sim.state = equilibrium_state
    
    print(f"Initial conditions:")
    print(f"  Power level: {sim.state.power_level:.1f}%")
    print(f"  Control rod position: {sim.state.control_rod_position:.1f}%")
    print(f"  Boron concentration: {sim.state.boron_concentration:.1f} ppm")
    print(f"  Fuel temperature: {sim.state.fuel_temperature:.1f}°C")
    print(f"  Neutron flux: {sim.state.neutron_flux:.2e} n/cm²/s")
    
    # Run simulation for 30 minutes without any control actions
    duration = 1800  # 30 minutes
    power_history = []
    reactivity_history = []
    
    print(f"\nRunning simulation for {duration} seconds...")
    print(f"{'Time (s)':<8} {'Power (%)':<10} {'Reactivity (pcm)':<15} {'Status':<10}")
    print("-" * 50)
    
    for t in range(duration):
        # No control actions - just let it run
        result = sim.step()
        
        power_history.append(sim.state.power_level)
        reactivity_history.append(result['info']['reactivity'])
        
        # Print status every 5 minutes
        if t % 300 == 0:
            status = "SCRAM" if sim.state.scram_status else "Normal"
            print(f"{sim.time:<8.0f} {sim.state.power_level:<10.1f} {result['info']['reactivity']:<15.1f} {status:<10}")
        
        # Check for early termination
        if result['done']:
            print(f"\n❌ Simulation terminated early at {sim.time:.0f}s due to safety system activation")
            print(f"   Final power level: {sim.state.power_level:.1f}%")
            print(f"   SCRAM status: {sim.state.scram_status}")
            return False
    
    # Analyze results
    final_power = sim.state.power_level
    power_drift = abs(final_power - 100.0)
    max_power_deviation = max(abs(p - 100.0) for p in power_history)
    avg_reactivity = sum(reactivity_history) / len(reactivity_history)
    
    print(f"\n✅ Simulation completed successfully!")
    print(f"Final power level: {final_power:.1f}%")
    print(f"Power drift: {power_drift:.2f}%")
    print(f"Maximum power deviation: {max_power_deviation:.2f}%")
    print(f"Average reactivity: {avg_reactivity:.1f} pcm")
    
    # Success criteria
    success = (
        not sim.state.scram_status and  # No SCRAM
        power_drift < 5.0 and          # Less than 5% drift
        max_power_deviation < 10.0     # Less than 10% max deviation
    )
    
    if success:
        print("✅ Steady state operation test PASSED")
    else:
        print("❌ Steady state operation test FAILED")
    
    return success


def test_reactivity_components():
    """Test individual reactivity components"""
    print("\nTesting Individual Reactivity Components")
    print("=" * 50)
    
    model = ReactivityModel()
    
    # Test control rod reactivity curve
    print("Control Rod Reactivity Curve:")
    for position in [0, 25, 50, 75, 100]:
        reactivity = model.calculate_control_rod_reactivity(position)
        print(f"  {position:3d}% withdrawn: {reactivity:8.1f} pcm")
    
    # Test boron reactivity
    print("\nBoron Reactivity:")
    for concentration in [0, 500, 1000, 1500, 2000]:
        reactivity = model.calculate_boron_reactivity(concentration)
        print(f"  {concentration:4d} ppm: {reactivity:8.1f} pcm")
    
    # Test temperature feedback
    print("\nTemperature Feedback:")
    for temp in [500, 575, 650, 725, 800]:
        doppler = model.calculate_doppler_reactivity(temp)
        print(f"  {temp:3d}°C fuel: {doppler:8.1f} pcm")
    
    # Test fission product poisons
    state = create_equilibrium_state()
    xenon_reactivity = model.calculate_xenon_reactivity(state.xenon_concentration, state.neutron_flux)
    samarium_reactivity = model.calculate_samarium_reactivity(state.samarium_concentration)
    
    print(f"\nFission Product Poisons:")
    print(f"  Xenon-135: {xenon_reactivity:8.1f} pcm")
    print(f"  Samarium-149: {samarium_reactivity:8.1f} pcm")
    
    return True


def test_boron_control():
    """Test boron control actions"""
    print("\nTesting Boron Control Actions")
    print("=" * 50)
    
    # Create simulator
    sim = NuclearPlantSimulator(dt=1.0)
    
    # Set equilibrium initial state
    equilibrium_state = create_equilibrium_state(power_level=100.0, control_rod_position=50.0, auto_balance=False)
    equilibrium_state.boron_concentration = 1200.0  # Set specific boron concentration for test
    sim.state = equilibrium_state
    
    initial_boron = sim.state.boron_concentration
    initial_reactivity = sim.reactivity_model.calculate_total_reactivity(sim.state)[0]
    
    print(f"Initial boron concentration: {initial_boron:.1f} ppm")
    print(f"Initial reactivity: {initial_reactivity:.1f} pcm")
    
    # Test dilution (reduce boron, add reactivity)
    from simulator.core.sim import ControlAction
    
    print("\nTesting boron dilution...")
    for i in range(10):
        result = sim.step(ControlAction.DILUTE_BORON, magnitude=1.0)
    
    diluted_boron = sim.state.boron_concentration
    diluted_reactivity = result['info']['reactivity']
    
    print(f"After dilution: {diluted_boron:.1f} ppm")
    print(f"Reactivity change: {diluted_reactivity - initial_reactivity:.1f} pcm")
    
    # Test boration (increase boron, reduce reactivity)
    print("\nTesting boron addition...")
    for i in range(20):
        result = sim.step(ControlAction.BORATE_COOLANT, magnitude=1.0)
    
    borated_boron = sim.state.boron_concentration
    borated_reactivity = result['info']['reactivity']
    
    print(f"After boration: {borated_boron:.1f} ppm")
    print(f"Final reactivity: {borated_reactivity:.1f} pcm")
    
    # Verify boron control works as expected
    dilution_worked = diluted_boron < initial_boron and diluted_reactivity > initial_reactivity
    boration_worked = borated_boron > diluted_boron and borated_reactivity < diluted_reactivity
    
    if dilution_worked and boration_worked:
        print("✅ Boron control system working correctly")
        return True
    else:
        print("❌ Boron control system not working correctly")
        return False


def main():
    """Run all tests"""
    print("Nuclear Simulator Steady State Test Suite")
    print("=" * 60)
    
    tests = [
        ("Reactivity Model Components", test_reactivity_model),
        ("Reactivity Component Details", test_reactivity_components),
        ("Boron Control System", test_boron_control),
        ("Steady State Operation", test_steady_state_operation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<40}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The steady state operation issue has been resolved.")
    else:
        print("⚠️  Some tests failed. The steady state operation issue may not be fully resolved.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
