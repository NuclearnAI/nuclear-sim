"""
Scenarios Tests

Tests for simulation scenarios including steady state, transients,
and emergency conditions.
"""

from simulator.core.sim import ControlAction, NuclearPlantSimulator
from tests.base_test import BaseTest, TestAssertions


class ScenarioTests(BaseTest):
    """Test suite for simulation scenarios"""
    
    def __init__(self):
        super().__init__("Scenarios")
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
        """Define all scenario tests"""
        self.add_test("Steady State Operation", self.test_steady_state)
        self.add_test("Power Ramp Scenario", self.test_power_ramp)
        self.add_test("Load Following", self.test_load_following)
        self.add_test("Emergency Shutdown", self.test_emergency_shutdown)
        self.add_test("Reactivity Transient", self.test_reactivity_transient)
    
    def test_steady_state(self) -> bool:
        """Test steady state operation"""
        # Run for short period without control actions
        initial_power = self.sim.state.power_level
        
        for _ in range(60):  # 1 minute
            result = self.sim.step()
            if result["done"]:
                TestAssertions.assert_false(True, "Should not scram during steady state")
                return False
        
        final_power = self.sim.state.power_level
        power_drift = abs(final_power - initial_power)
        
        TestAssertions.assert_less(power_drift, 10.0, "Power should remain stable")
        TestAssertions.assert_false(self.sim.state.scram_status, "Should not scram")
        
        return True
    
    def test_power_ramp(self) -> bool:
        """Test power ramp scenario"""
        initial_power = self.sim.state.power_level
        
        # Ramp power down by withdrawing rods
        for _ in range(20):
            self.sim.step(ControlAction.CONTROL_ROD_INSERT)
        
        mid_power = self.sim.state.power_level
        TestAssertions.assert_less(mid_power, initial_power, "Power should decrease with rod insertion")
        
        # Ramp power back up
        for _ in range(30):
            self.sim.step(ControlAction.CONTROL_ROD_WITHDRAW)
        
        final_power = self.sim.state.power_level
        TestAssertions.assert_greater(final_power, mid_power, "Power should increase with rod withdrawal")
        
        return True
    
    def test_load_following(self) -> bool:
        """Test load following scenario"""
        # Simulate load changes by adjusting steam valve
        initial_steam_flow = self.sim.state.steam_flow_rate
        
        # Increase load (open steam valve)
        for _ in range(10):
            self.sim.step(ControlAction.OPEN_STEAM_VALVE)
        
        # Check response
        TestAssertions.assert_greater(self.sim.state.steam_valve_position, 50.0,
                                     "Steam valve should open")
        
        # Decrease load (close steam valve)
        for _ in range(15):
            self.sim.step(ControlAction.CLOSE_STEAM_VALVE)
        
        TestAssertions.assert_less(self.sim.state.steam_valve_position, 60.0,
                                  "Steam valve should close")
        
        return True
    
    def test_emergency_shutdown(self) -> bool:
        """Test emergency shutdown scenario"""
        # Force high temperature to trigger scram
        self.sim.state.fuel_temperature = 1600.0
        
        result = self.sim.step()
        
        TestAssertions.assert_true(result["done"], "Should trigger emergency shutdown")
        TestAssertions.assert_true(self.sim.state.scram_status, "Should be in scram")
        TestAssertions.assert_equal(self.sim.state.control_rod_position, 0,
                                   "Rods should be fully inserted")
        
        return True
    
    def test_reactivity_transient(self) -> bool:
        """Test reactivity transient scenario"""
        initial_boron = self.sim.state.boron_concentration
        
        # Add reactivity by diluting boron
        for _ in range(10):
            self.sim.step(ControlAction.DILUTE_BORON)
        
        TestAssertions.assert_less(self.sim.state.boron_concentration, initial_boron,
                                  "Boron should decrease")
        
        # Remove reactivity by adding boron
        for _ in range(15):
            self.sim.step(ControlAction.BORATE_COOLANT)
        
        TestAssertions.assert_greater(self.sim.state.boron_concentration, initial_boron,
                                     "Boron should increase above initial")
        
        return True
