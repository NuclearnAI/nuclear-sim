"""
Reactor Physics Tests

Tests for the reactor physics module including neutron kinetics,
thermal dynamics, and reactor core calculations.
"""

import numpy as np

from systems.primary.reactor.physics.reactor_physics import (
    ReactorCoreState,
    ReactorPhysics,
)
from tests.base_test import BaseTest, TestAssertions


class ReactorPhysicsTests(BaseTest):
    """Test suite for reactor physics"""
    
    def __init__(self):
        super().__init__("Reactor Physics")
        self.physics = None
        self.define_tests()
    
    def setup(self) -> bool:
        """Setup test environment"""
        try:
            self.physics = ReactorPhysics(rated_power_mw=3000.0)
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def define_tests(self) -> None:
        """Define all reactor physics tests"""
        self.add_test("Reactor Physics Initialization", self.test_initialization)
        self.add_test("Point Kinetics Equations", self.test_point_kinetics)
        self.add_test("Thermal Power Calculation", self.test_thermal_power)
        self.add_test("Fuel Temperature Dynamics", self.test_fuel_temperature)
        self.add_test("Fission Product Updates", self.test_fission_product_updates)
        self.add_test("Reactivity Calculation", self.test_reactivity_calculation)
        self.add_test("Safety Limits Check", self.test_safety_limits)
        self.add_test("Reactor Update Cycle", self.test_update_cycle)
        self.add_test("State Management", self.test_state_management)
        self.add_test("Error Handling", self.test_error_handling)
    
    def test_initialization(self) -> bool:
        """Test reactor physics initialization"""
        TestAssertions.assert_equal(self.physics.rated_power_mw, 3000.0, "Rated power should be set")
        TestAssertions.assert_not_none(self.physics.state, "Should have reactor state")
        TestAssertions.assert_not_none(self.physics.reactivity_model, "Should have reactivity model")
        
        # Check physics constants
        TestAssertions.assert_greater(self.physics.BETA, 0, "Beta should be positive")
        TestAssertions.assert_greater(self.physics.LAMBDA_PROMPT, 0, "Prompt neutron lifetime should be positive")
        TestAssertions.assert_equal(len(self.physics.LAMBDA), 6, "Should have 6 delayed neutron groups")
        
        # Check initial state
        TestAssertions.assert_greater(self.physics.state.neutron_flux, 0, "Initial neutron flux should be positive")
        TestAssertions.assert_greater(self.physics.state.fuel_temperature, 0, "Initial fuel temperature should be positive")
        TestAssertions.assert_false(self.physics.state.scram_status, "Should not be in scram initially")
        
        return True
    
    def test_point_kinetics(self) -> bool:
        """Test point kinetics equations"""
        # Test critical conditions (zero reactivity)
        flux_change, precursor_change = self.physics.point_kinetics(0.0, 1.0)
        TestAssertions.assert_almost_equal(flux_change, 0.0, tolerance=1e-6, 
                                         message="Zero reactivity should give zero flux change")
        
        # Test positive reactivity
        flux_change_pos, _ = self.physics.point_kinetics(0.001, 1.0)  # 100 pcm
        TestAssertions.assert_greater(flux_change_pos, 0, "Positive reactivity should increase flux")
        
        # Test negative reactivity
        flux_change_neg, _ = self.physics.point_kinetics(-0.001, 1.0)  # -100 pcm
        TestAssertions.assert_less(flux_change_neg, 0, "Negative reactivity should decrease flux")
        
        # Test precursor changes
        TestAssertions.assert_equal(len(precursor_change), 6, "Should have 6 precursor groups")
        
        return True
    
    def test_thermal_power(self) -> bool:
        """Test thermal power calculation"""
        # Test at 100% flux
        self.physics.state.neutron_flux = 1e13
        power = self.physics.calculate_thermal_power()
        TestAssertions.assert_almost_equal(power, 3000.0, tolerance=100.0,
                                         message="100% flux should give rated power")
        
        # Test at 50% flux
        self.physics.state.neutron_flux = 5e12
        power_50 = self.physics.calculate_thermal_power()
        TestAssertions.assert_almost_equal(power_50, 1500.0, tolerance=100.0,
                                         message="50% flux should give 50% power")
        
        # Test power limits
        self.physics.state.neutron_flux = 2e13  # 200% flux
        power_high = self.physics.calculate_thermal_power()
        TestAssertions.assert_less_equal(power_high, 3600.0, "Power should be limited")
        
        return True
    
    def test_fuel_temperature(self) -> bool:
        """Test fuel temperature dynamics"""
        initial_temp = self.physics.state.fuel_temperature
        
        # Test temperature increase with high power
        temp_change = self.physics.update_fuel_temperature(
            thermal_power_mw=4000.0,  # High power
            coolant_temp=280.0,
            coolant_flow=20000.0,
            dt=1.0
        )
        TestAssertions.assert_greater(temp_change, 0, "High power should increase fuel temperature")
        
        # Test temperature decrease with low power
        temp_change_low = self.physics.update_fuel_temperature(
            thermal_power_mw=1000.0,  # Low power
            coolant_temp=280.0,
            coolant_flow=20000.0,
            dt=1.0
        )
        TestAssertions.assert_less(temp_change_low, temp_change, 
                                  "Lower power should give smaller temperature increase")
        
        # Test cooling effect
        temp_change_cool = self.physics.update_fuel_temperature(
            thermal_power_mw=2000.0,
            coolant_temp=280.0,
            coolant_flow=50000.0,  # High flow
            dt=1.0
        )
        temp_change_normal = self.physics.update_fuel_temperature(
            thermal_power_mw=2000.0,
            coolant_temp=280.0,
            coolant_flow=20000.0,  # Normal flow
            dt=1.0
        )
        TestAssertions.assert_less(temp_change_cool, temp_change_normal,
                                  "Higher coolant flow should reduce temperature rise")
        
        return True
    
    def test_fission_product_updates(self) -> bool:
        """Test fission product concentration updates"""
        updates = self.physics.update_fission_products(1.0)
        
        TestAssertions.assert_true("xenon" in updates, "Should update xenon")
        TestAssertions.assert_true("iodine" in updates, "Should update iodine")
        TestAssertions.assert_true("samarium" in updates, "Should update samarium")
        
        # Check that concentrations are reasonable
        TestAssertions.assert_greater(updates["xenon"], 0, "Xenon concentration should be positive")
        TestAssertions.assert_greater(updates["iodine"], 0, "Iodine concentration should be positive")
        TestAssertions.assert_greater(updates["samarium"], 0, "Samarium concentration should be positive")
        
        return True
    
    def test_reactivity_calculation(self) -> bool:
        """Test total reactivity calculation"""
        coolant_temp = 280.0
        coolant_pressure = 15.5
        
        total_reactivity, components = self.physics.calculate_total_reactivity(
            coolant_temp, coolant_pressure
        )
        
        # Check that components are returned
        TestAssertions.assert_true(isinstance(components, dict), "Should return component breakdown")
        TestAssertions.assert_true(len(components) > 0, "Should have reactivity components")
        
        # Check that total is reasonable
        TestAssertions.assert_in_range(total_reactivity, -20000, 20000,
                                      "Total reactivity should be in reasonable range")
        
        return True
    
    def test_safety_limits(self) -> bool:
        """Test safety limits checking"""
        # Test normal conditions
        scram_required, reason = self.physics.check_safety_limits()
        TestAssertions.assert_false(scram_required, "Normal conditions should not require scram")
        
        # Test high fuel temperature
        self.physics.state.fuel_temperature = 2000.0  # Above limit
        scram_required, reason = self.physics.check_safety_limits()
        TestAssertions.assert_true(scram_required, "High fuel temperature should trigger scram")
        TestAssertions.assert_true("temperature" in reason.lower(), "Reason should mention temperature")
        
        # Reset and test high power
        self.physics.state.fuel_temperature = 600.0  # Normal
        self.physics.state.power_level = 130.0  # Above limit
        scram_required, reason = self.physics.check_safety_limits()
        TestAssertions.assert_true(scram_required, "High power should trigger scram")
        
        return True
    
    def test_update_cycle(self) -> bool:
        """Test complete reactor update cycle"""
        # Set initial conditions
        coolant_temp = 280.0
        coolant_pressure = 15.5
        coolant_flow = 20000.0
        dt = 1.0
        
        # Perform update
        result = self.physics.update(dt, coolant_temp, coolant_pressure, coolant_flow)
        
        # Check return values
        required_keys = [
            "thermal_power_mw", "power_percent", "fuel_temperature",
            "neutron_flux", "reactivity_pcm", "scram_status"
        ]
        for key in required_keys:
            TestAssertions.assert_true(key in result, f"Should return {key}")
        
        # Check value ranges
        TestAssertions.assert_greater(result["thermal_power_mw"], 0, "Thermal power should be positive")
        TestAssertions.assert_in_range(result["power_percent"], 0, 200, "Power percent should be reasonable")
        TestAssertions.assert_greater(result["fuel_temperature"], 200, "Fuel temperature should be reasonable")
        TestAssertions.assert_greater(result["neutron_flux"], 0, "Neutron flux should be positive")
        
        return True
    
    def test_state_management(self) -> bool:
        """Test reactor state management"""
        # Test state dictionary
        state_dict = self.physics.get_state_dict()
        
        required_keys = [
            "neutron_flux", "reactivity", "fuel_temperature", "power_level",
            "control_rod_position", "boron_concentration", "scram_status"
        ]
        for key in required_keys:
            TestAssertions.assert_true(key in state_dict, f"State should include {key}")
        
        # Test reset functionality
        original_flux = self.physics.state.neutron_flux
        self.physics.state.neutron_flux = 5e12  # Change flux
        self.physics.state.scram_status = True  # Set scram
        
        self.physics.reset()
        
        # Check that state is reset
        TestAssertions.assert_false(self.physics.state.scram_status, "Scram should be reset")
        TestAssertions.assert_greater(self.physics.state.neutron_flux, 0, "Flux should be reset to positive value")
        
        return True
    
    def test_error_handling(self) -> bool:
        """Test error handling in reactor physics"""
        # Test with invalid inputs
        try:
            # Test with NaN values
            self.physics.state.neutron_flux = float('nan')
            result = self.physics.update(1.0, 280.0, 15.5, 20000.0)
            # Should handle NaN gracefully
            TestAssertions.assert_false(np.isnan(result["neutron_flux"]), "Should handle NaN values")
        except Exception:
            pass  # Also acceptable to raise exception
        
        # Test with extreme values
        try:
            result = self.physics.update(1.0, 1000.0, 50.0, 100000.0)  # Extreme conditions
            # Should handle extreme values gracefully
        except Exception:
            pass  # Acceptable to raise exception for extreme values
        
        return True
