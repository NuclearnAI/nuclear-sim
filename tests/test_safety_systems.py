"""
Safety Systems Tests

Tests for safety system functionality including scram conditions,
safety limits, and emergency responses.
"""

from simulator.core.sim import NuclearPlantSimulator
from tests.base_test import BaseTest, TestAssertions


class SafetySystemTests(BaseTest):
    """Test suite for safety systems"""
    
    def __init__(self):
        super().__init__("Safety Systems")
        self.sim = None
        self.define_tests()
    
    def setup(self) -> bool:
        """Setup test environment"""
        try:
            self.sim = NuclearPlantSimulator(dt=1.0)
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def define_tests(self) -> None:
        """Define all safety system tests"""
        self.add_test("Safety Limits Definition", self.test_safety_limits)
        self.add_test("Temperature Protection", self.test_temperature_protection)
        self.add_test("Pressure Protection", self.test_pressure_protection)
        self.add_test("Flow Protection", self.test_flow_protection)
        self.add_test("Power Protection", self.test_power_protection)
        self.add_test("Scram Response", self.test_scram_response)
        self.add_test("Multiple Condition Scram", self.test_multiple_conditions)
    
    def test_safety_limits(self) -> bool:
        """Test safety limit definitions"""
        TestAssertions.assert_greater(self.sim.max_fuel_temp, 1000, "Fuel temperature limit should be reasonable")
        TestAssertions.assert_greater(self.sim.max_coolant_pressure, 15, "Pressure limit should be reasonable")
        TestAssertions.assert_greater(self.sim.min_coolant_flow, 500, "Minimum flow should be reasonable")
        return True
    
    def test_temperature_protection(self) -> bool:
        """Test fuel temperature protection"""
        # Set normal conditions
        self.sim.state.fuel_temperature = 600.0
        self.sim.state.scram_status = False
        
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_false(scram, "Normal temperature should not trigger scram")
        
        # Set high temperature
        self.sim.state.fuel_temperature = 1600.0  # Above limit
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram, "High temperature should trigger scram")
        TestAssertions.assert_true(self.sim.state.scram_status, "Scram status should be set")
        
        return True
    
    def test_pressure_protection(self) -> bool:
        """Test pressure protection"""
        # Reset scram status
        self.sim.state.scram_status = False
        self.sim.state.coolant_pressure = 15.5  # Normal
        
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_false(scram, "Normal pressure should not trigger scram")
        
        # Set high pressure
        self.sim.state.coolant_pressure = 18.0  # Above limit
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram, "High pressure should trigger scram")
        
        return True
    
    def test_flow_protection(self) -> bool:
        """Test coolant flow protection"""
        # Reset scram status
        self.sim.state.scram_status = False
        self.sim.state.coolant_flow_rate = 20000.0  # Normal
        
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_false(scram, "Normal flow should not trigger scram")
        
        # Set low flow
        self.sim.state.coolant_flow_rate = 500.0  # Below limit
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram, "Low flow should trigger scram")
        
        return True
    
    def test_power_protection(self) -> bool:
        """Test power level protection"""
        # Reset scram status
        self.sim.state.scram_status = False
        self.sim.state.power_level = 100.0  # Normal
        
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_false(scram, "Normal power should not trigger scram")
        
        # Set high power
        self.sim.state.power_level = 125.0  # Above limit
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram, "High power should trigger scram")
        
        return True
    
    def test_scram_response(self) -> bool:
        """Test scram response actions"""
        # Set conditions for scram
        self.sim.state.scram_status = False
        self.sim.state.control_rod_position = 95.0
        self.sim.state.fuel_temperature = 1600.0  # Trigger scram
        
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram, "Should trigger scram")
        TestAssertions.assert_true(self.sim.state.scram_status, "Scram status should be set")
        TestAssertions.assert_equal(self.sim.state.control_rod_position, 0, "Rods should be fully inserted")
        
        return True
    
    def test_multiple_conditions(self) -> bool:
        """Test multiple simultaneous scram conditions"""
        # Reset
        self.sim.state.scram_status = False
        self.sim.state.control_rod_position = 95.0
        
        # Set multiple violation conditions
        self.sim.state.fuel_temperature = 1600.0  # High temperature
        self.sim.state.coolant_pressure = 18.0    # High pressure
        self.sim.state.power_level = 125.0        # High power
        
        scram = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram, "Multiple violations should trigger scram")
        TestAssertions.assert_true(self.sim.state.scram_status, "Scram status should be set")
        
        return True
