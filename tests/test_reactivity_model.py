"""
Reactivity Model Tests

Tests for the comprehensive PWR reactivity model including all reactivity components,
fission product dynamics, and equilibrium calculations.
"""

import numpy as np

from simulator.core.sim import ReactorState
from systems.primary.reactor.reactivity_model import (
    ReactivityModel,
    ReactorConfig,
    create_equilibrium_state,
)
from tests.base_test import BaseTest, TestAssertions


class ReactivityModelTests(BaseTest):
    """Test suite for the reactivity model"""
    
    def __init__(self):
        super().__init__("Reactivity Model")
        self.model = None
        self.test_state = None
        self.define_tests()
    
    def setup(self) -> bool:
        """Setup test environment"""
        try:
            # Create reactivity model with default configuration
            self.model = ReactivityModel()
            
            # Create test reactor state
            self.test_state = ReactorState()
            
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def define_tests(self) -> None:
        """Define all reactivity model tests"""
        self.add_test("Control Rod Reactivity Curve", self.test_control_rod_reactivity)
        self.add_test("Boron Reactivity Linear", self.test_boron_reactivity)
        self.add_test("Doppler Temperature Feedback", self.test_doppler_reactivity)
        self.add_test("Moderator Temperature Feedback", self.test_moderator_temp_reactivity)
        self.add_test("Void Reactivity Feedback", self.test_void_reactivity)
        self.add_test("Pressure Reactivity Feedback", self.test_pressure_reactivity)
        self.add_test("Xenon Poisoning", self.test_xenon_reactivity)
        self.add_test("Samarium Poisoning", self.test_samarium_reactivity)
        self.add_test("Fuel Depletion", self.test_fuel_depletion_reactivity)
        self.add_test("Burnable Poisons", self.test_burnable_poison_reactivity)
        self.add_test("Total Reactivity Calculation", self.test_total_reactivity)
        self.add_test("Fission Product Updates", self.test_fission_product_updates)
        self.add_test("Equilibrium State Creation", self.test_equilibrium_state)
        self.add_test("Critical Boron Calculation", self.test_critical_boron)
        self.add_test("Reactivity Components Balance", self.test_reactivity_balance)
    
    def test_control_rod_reactivity(self) -> bool:
        """Test control rod reactivity curve"""
        # Test key positions
        rod_0_percent = self.model.calculate_control_rod_reactivity(0.0)  # Fully inserted
        rod_50_percent = self.model.calculate_control_rod_reactivity(50.0)  # Normal operation
        rod_100_percent = self.model.calculate_control_rod_reactivity(100.0)  # Fully withdrawn
        
        # Verify S-curve behavior
        TestAssertions.assert_less(rod_0_percent, 0, "Fully inserted rods should give negative reactivity")
        TestAssertions.assert_almost_equal(rod_50_percent, 0.0, tolerance=100.0, 
                                         message="50% position should be near zero reactivity")
        TestAssertions.assert_greater(rod_100_percent, 0, "Fully withdrawn rods should give positive reactivity")
        
        # Test monotonic behavior
        rod_25_percent = self.model.calculate_control_rod_reactivity(25.0)
        rod_75_percent = self.model.calculate_control_rod_reactivity(75.0)
        
        TestAssertions.assert_less(rod_25_percent, rod_50_percent, "Reactivity should increase with withdrawal")
        TestAssertions.assert_less(rod_50_percent, rod_75_percent, "Reactivity should increase with withdrawal")
        
        return True
    
    def test_boron_reactivity(self) -> bool:
        """Test boron reactivity (linear relationship)"""
        # Test zero boron
        boron_0 = self.model.calculate_boron_reactivity(0.0)
        TestAssertions.assert_equal(boron_0, 0.0, "Zero boron should give zero reactivity")
        
        # Test linear relationship
        boron_1000 = self.model.calculate_boron_reactivity(1000.0)
        boron_2000 = self.model.calculate_boron_reactivity(2000.0)
        
        TestAssertions.assert_less(boron_1000, 0, "Boron should give negative reactivity")
        TestAssertions.assert_almost_equal(boron_2000, 2 * boron_1000, tolerance=1.0,
                                         message="Boron reactivity should be linear")
        
        # Test typical PWR boron concentration
        boron_1200 = self.model.calculate_boron_reactivity(1200.0)
        TestAssertions.assert_in_range(boron_1200, -15000, -10000, 
                                      "Typical boron concentration should give reasonable reactivity")
        
        return True
    
    def test_doppler_reactivity(self) -> bool:
        """Test Doppler temperature feedback"""
        ref_temp = self.model.config.ref_fuel_temperature
        
        # Test reference temperature
        doppler_ref = self.model.calculate_doppler_reactivity(ref_temp)
        TestAssertions.assert_equal(doppler_ref, 0.0, "Reference temperature should give zero Doppler feedback")
        
        # Test temperature increase (should be negative feedback)
        doppler_high = self.model.calculate_doppler_reactivity(ref_temp + 100)
        TestAssertions.assert_less(doppler_high, 0, "Higher fuel temperature should give negative reactivity")
        
        # Test temperature decrease (should be positive feedback)
        doppler_low = self.model.calculate_doppler_reactivity(ref_temp - 100)
        TestAssertions.assert_greater(doppler_low, 0, "Lower fuel temperature should give positive reactivity")
        
        # Test linearity
        doppler_50 = self.model.calculate_doppler_reactivity(ref_temp + 50)
        TestAssertions.assert_almost_equal(doppler_high, 2 * doppler_50, tolerance=1.0,
                                         message="Doppler feedback should be linear with temperature")
        
        return True
    
    def test_moderator_temp_reactivity(self) -> bool:
        """Test moderator temperature feedback"""
        ref_temp = self.model.config.ref_coolant_temperature
        
        # Test reference temperature
        mod_temp_ref = self.model.calculate_moderator_temp_reactivity(ref_temp)
        TestAssertions.assert_equal(mod_temp_ref, 0.0, "Reference temperature should give zero feedback")
        
        # Test temperature increase (should be negative feedback for PWR)
        mod_temp_high = self.model.calculate_moderator_temp_reactivity(ref_temp + 50)
        TestAssertions.assert_less(mod_temp_high, 0, "Higher coolant temperature should give negative reactivity")
        
        # Test temperature decrease (should be positive feedback)
        mod_temp_low = self.model.calculate_moderator_temp_reactivity(ref_temp - 50)
        TestAssertions.assert_greater(mod_temp_low, 0, "Lower coolant temperature should give positive reactivity")
        
        return True
    
    def test_void_reactivity(self) -> bool:
        """Test void reactivity feedback"""
        # Test no void
        void_0 = self.model.calculate_void_reactivity(0.0)
        TestAssertions.assert_equal(void_0, 0.0, "No void should give zero reactivity")
        
        # Test full void (should be negative for PWR)
        void_100 = self.model.calculate_void_reactivity(1.0)
        TestAssertions.assert_less(void_100, 0, "Full void should give negative reactivity in PWR")
        
        # Test partial void
        void_50 = self.model.calculate_void_reactivity(0.5)
        TestAssertions.assert_almost_equal(void_50, 0.5 * void_100, tolerance=10.0,
                                         message="Void reactivity should be linear")
        
        return True
    
    def test_pressure_reactivity(self) -> bool:
        """Test pressure reactivity feedback"""
        ref_pressure = self.model.config.ref_pressure
        
        # Test reference pressure
        pressure_ref = self.model.calculate_pressure_reactivity(ref_pressure)
        TestAssertions.assert_equal(pressure_ref, 0.0, "Reference pressure should give zero reactivity")
        
        # Test pressure increase (should be positive for PWR)
        pressure_high = self.model.calculate_pressure_reactivity(ref_pressure + 1.0)
        TestAssertions.assert_greater(pressure_high, 0, "Higher pressure should give positive reactivity")
        
        # Test pressure decrease
        pressure_low = self.model.calculate_pressure_reactivity(ref_pressure - 1.0)
        TestAssertions.assert_less(pressure_low, 0, "Lower pressure should give negative reactivity")
        
        return True
    
    def test_xenon_reactivity(self) -> bool:
        """Test xenon poisoning reactivity"""
        # Test zero xenon
        xenon_0 = self.model.calculate_xenon_reactivity(0.0, 1e13)
        TestAssertions.assert_equal(xenon_0, 0.0, "Zero xenon should give zero reactivity")
        
        # Test equilibrium xenon concentration
        eq_xenon = 1.0e15  # atoms/cm³
        xenon_eq = self.model.calculate_xenon_reactivity(eq_xenon, 1e13)
        TestAssertions.assert_less(xenon_eq, 0, "Xenon should give negative reactivity")
        TestAssertions.assert_in_range(xenon_eq, -3000, -1000, 
                                      "Equilibrium xenon should give reasonable poisoning")
        
        # Test double concentration
        xenon_double = self.model.calculate_xenon_reactivity(2 * eq_xenon, 1e13)
        TestAssertions.assert_almost_equal(xenon_double, 2 * xenon_eq, tolerance=100.0,
                                         message="Xenon reactivity should be linear with concentration")
        
        return True
    
    def test_samarium_reactivity(self) -> bool:
        """Test samarium poisoning reactivity"""
        # Test zero samarium
        sm_0 = self.model.calculate_samarium_reactivity(0.0)
        TestAssertions.assert_equal(sm_0, 0.0, "Zero samarium should give zero reactivity")
        
        # Test equilibrium samarium concentration
        eq_sm = 5.0e14  # atoms/cm³
        sm_eq = self.model.calculate_samarium_reactivity(eq_sm)
        TestAssertions.assert_less(sm_eq, 0, "Samarium should give negative reactivity")
        TestAssertions.assert_in_range(sm_eq, -1000, -300, 
                                      "Equilibrium samarium should give reasonable poisoning")
        
        return True
    
    def test_fuel_depletion_reactivity(self) -> bool:
        """Test fuel depletion reactivity"""
        # Test fresh fuel (zero burnup)
        self.test_state.fuel_burnup = 0.0
        fresh_fuel = self.model.calculate_fuel_depletion_reactivity(self.test_state)
        TestAssertions.assert_greater(fresh_fuel, 0, "Fresh fuel should have excess reactivity")
        
        # Test depleted fuel (high burnup)
        self.test_state.fuel_burnup = 50000.0  # High burnup
        depleted_fuel = self.model.calculate_fuel_depletion_reactivity(self.test_state)
        TestAssertions.assert_less(depleted_fuel, fresh_fuel, 
                                  "Depleted fuel should have less reactivity than fresh")
        
        # Test mid-cycle fuel
        self.test_state.fuel_burnup = 15000.0  # Typical mid-cycle
        mid_cycle = self.model.calculate_fuel_depletion_reactivity(self.test_state)
        TestAssertions.assert_in_range(mid_cycle, depleted_fuel, fresh_fuel,
                                      "Mid-cycle fuel should be between fresh and depleted")
        
        return True
    
    def test_burnable_poison_reactivity(self) -> bool:
        """Test burnable poison reactivity"""
        # Test fresh fuel (zero burnup) - maximum burnable poison
        self.test_state.fuel_burnup = 0.0
        self.test_state.burnable_poison_worth = -800.0
        fresh_bp = self.model.calculate_burnable_poison_reactivity(self.test_state)
        TestAssertions.assert_less(fresh_bp, 0, "Burnable poisons should give negative reactivity")
        TestAssertions.assert_almost_equal(fresh_bp, -800.0, tolerance=50.0,
                                         message="Fresh fuel should have full burnable poison worth")
        
        # Test depleted fuel (high burnup) - minimal burnable poison
        self.test_state.fuel_burnup = 30000.0
        depleted_bp = self.model.calculate_burnable_poison_reactivity(self.test_state)
        TestAssertions.assert_greater(depleted_bp, fresh_bp, 
                                     "Depleted fuel should have less burnable poison worth")
        TestAssertions.assert_in_range(depleted_bp, -100, 0,
                                      "Highly burned fuel should have minimal burnable poison")
        
        return True
    
    def test_total_reactivity(self) -> bool:
        """Test total reactivity calculation"""
        # Use equilibrium state for testing
        eq_state = create_equilibrium_state(power_level=100.0, control_rod_position=95.0, auto_balance=True)
        
        total_reactivity, components = self.model.calculate_total_reactivity(eq_state)
        
        # Check that all expected components are present
        expected_components = [
            "control_rods", "boron", "doppler", "moderator_temp", "moderator_void",
            "pressure", "xenon", "samarium", "fuel_depletion", "burnable_poisons"
        ]
        
        for component in expected_components:
            TestAssertions.assert_true(component in components, 
                                     f"Component {component} should be in reactivity breakdown")
        
        # Check that total equals sum of components
        calculated_total = sum(components.values())
        TestAssertions.assert_almost_equal(total_reactivity, calculated_total, tolerance=1.0,
                                         message="Total reactivity should equal sum of components")
        
        # For equilibrium state, total reactivity should be near zero
        TestAssertions.assert_in_range(total_reactivity, -100, 100,
                                      "Equilibrium state should have near-zero reactivity")
        
        return True
    
    def test_fission_product_updates(self) -> bool:
        """Test fission product concentration updates"""
        # Set initial conditions
        initial_iodine = 1.0e16
        initial_xenon = 1.0e15
        initial_samarium = 5.0e14
        
        self.test_state.iodine_concentration = initial_iodine
        self.test_state.xenon_concentration = initial_xenon
        self.test_state.samarium_concentration = initial_samarium
        
        neutron_flux = 1e13  # 100% power
        dt = 3600.0  # 1 hour
        
        # Update fission products
        updates = self.model.update_fission_products(self.test_state, neutron_flux, dt)
        
        # Check that all fission products are updated
        TestAssertions.assert_true("iodine" in updates, "Iodine should be updated")
        TestAssertions.assert_true("xenon" in updates, "Xenon should be updated")
        TestAssertions.assert_true("samarium" in updates, "Samarium should be updated")
        
        # Check that concentrations are non-negative
        TestAssertions.assert_greater(updates["iodine"], 0, "Iodine concentration should be positive")
        TestAssertions.assert_greater(updates["xenon"], 0, "Xenon concentration should be positive")
        TestAssertions.assert_greater(updates["samarium"], 0, "Samarium concentration should be positive")
        
        # Check reasonable magnitudes
        TestAssertions.assert_in_range(updates["iodine"], 1e15, 1e17, 
                                      "Iodine concentration should be reasonable")
        TestAssertions.assert_in_range(updates["xenon"], 1e14, 1e16, 
                                      "Xenon concentration should be reasonable")
        TestAssertions.assert_in_range(updates["samarium"], 1e14, 1e16, 
                                      "Samarium concentration should be reasonable")
        
        return True
    
    def test_equilibrium_state(self) -> bool:
        """Test equilibrium state creation"""
        # Create equilibrium state
        eq_state = create_equilibrium_state(power_level=100.0, control_rod_position=95.0, auto_balance=True)
        
        # Check basic parameters
        TestAssertions.assert_almost_equal(eq_state.power_level, 100.0, tolerance=1.0,
                                         message="Power level should be 100%")
        TestAssertions.assert_almost_equal(eq_state.control_rod_position, 95.0, tolerance=1.0,
                                         message="Control rod position should be 95%")
        
        # Check neutron flux
        TestAssertions.assert_almost_equal(eq_state.neutron_flux, 1e13, tolerance=1e12,
                                         message="Neutron flux should be 100% power level")
        
        # Check fission product concentrations are reasonable
        TestAssertions.assert_greater(eq_state.xenon_concentration, 0, "Xenon concentration should be positive")
        TestAssertions.assert_greater(eq_state.iodine_concentration, 0, "Iodine concentration should be positive")
        TestAssertions.assert_greater(eq_state.samarium_concentration, 0, "Samarium concentration should be positive")
        
        # Check delayed neutron precursors
        TestAssertions.assert_not_none(eq_state.delayed_neutron_precursors, 
                                      "Delayed neutron precursors should be initialized")
        TestAssertions.assert_equal(len(eq_state.delayed_neutron_precursors), 6,
                                   "Should have 6 delayed neutron precursor groups")
        
        return True
    
    def test_critical_boron(self) -> bool:
        """Test critical boron concentration calculation"""
        # Create test state
        test_state = ReactorState()
        test_state.control_rod_position = 95.0  # Normal operating position
        test_state.boron_concentration = 1000.0  # Initial guess
        
        # Calculate critical boron for zero reactivity
        critical_boron = self.model.calculate_critical_boron_concentration(test_state, target_reactivity=0.0)
        
        # Check that result is reasonable
        TestAssertions.assert_greater(critical_boron, 0, "Critical boron should be positive")
        TestAssertions.assert_in_range(critical_boron, 500, 2500, 
                                      "Critical boron should be in reasonable range for PWR")
        
        # Verify that using this boron concentration gives near-zero reactivity
        test_state.boron_concentration = critical_boron
        total_reactivity, _ = self.model.calculate_total_reactivity(test_state)
        TestAssertions.assert_in_range(total_reactivity, -50, 50,
                                      "Using critical boron should give near-zero reactivity")
        
        return True
    
    def test_reactivity_balance(self) -> bool:
        """Test that reactivity components are properly balanced"""
        # Create equilibrium state
        eq_state = create_equilibrium_state(power_level=100.0, control_rod_position=95.0, auto_balance=True)
        
        # Calculate reactivity components
        total_reactivity, components = self.model.calculate_total_reactivity(eq_state)
        
        # Check that positive and negative components roughly balance
        positive_components = sum(v for v in components.values() if v > 0)
        negative_components = sum(v for v in components.values() if v < 0)
        
        TestAssertions.assert_greater(positive_components, 0, "Should have positive reactivity components")
        TestAssertions.assert_less(negative_components, 0, "Should have negative reactivity components")
        
        # Total should be near zero for equilibrium
        TestAssertions.assert_in_range(total_reactivity, -100, 100,
                                      "Total reactivity should be near zero for equilibrium")
        
        # Check that major components have reasonable magnitudes
        TestAssertions.assert_in_range(abs(components["boron"]), 5000, 20000,
                                      "Boron reactivity should be significant")
        TestAssertions.assert_in_range(abs(components["fuel_depletion"]), 1000, 5000,
                                      "Fuel depletion reactivity should be reasonable")
        TestAssertions.assert_in_range(abs(components["xenon"]), 1000, 3000,
                                      "Xenon poisoning should be reasonable")
        
        return True
