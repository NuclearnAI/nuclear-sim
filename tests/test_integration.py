"""
Integration Tests

Tests for integration between different simulator components and
end-to-end functionality.
"""

from simulator.core.sim import ControlAction, NuclearPlantSimulator
from tests.base_test import BaseTest, TestAssertions


class IntegrationTests(BaseTest):
    """Test suite for integration testing"""
    
    def __init__(self):
        super().__init__("Integration")
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
        """Define all integration tests"""
        self.add_test("End-to-End Simulation", self.test_end_to_end)
        self.add_test("Component Integration", self.test_component_integration)
        self.add_test("Control Loop Integration", self.test_control_loop)
        self.add_test("Safety Integration", self.test_safety_integration)
        self.add_test("Data Flow Integration", self.test_data_flow)
    
    def test_end_to_end(self) -> bool:
        """Test complete end-to-end simulation"""
        # Run simulation for extended period with various actions
        actions = [
            ControlAction.NO_ACTION,
            ControlAction.CONTROL_ROD_WITHDRAW,
            ControlAction.INCREASE_COOLANT_FLOW,
            ControlAction.OPEN_STEAM_VALVE,
            ControlAction.CONTROL_ROD_INSERT,
            ControlAction.BORATE_COOLANT,
        ]
        
        for i in range(100):  # Run for 100 steps
            action = actions[i % len(actions)]
            result = self.sim.step(action)
            
            # Check that simulation continues normally
            TestAssertions.assert_true("observation" in result, "Should return observation")
            TestAssertions.assert_true("reward" in result, "Should return reward")
            TestAssertions.assert_true("info" in result, "Should return info")
            
            # If scram occurs, that's acceptable but should be handled properly
            if result["done"]:
                TestAssertions.assert_true(self.sim.state.scram_status, "Done should mean scram")
                break
        
        TestAssertions.assert_greater(self.sim.time, 0, "Time should advance")
        TestAssertions.assert_greater(len(self.sim.history), 0, "History should be recorded")
        
        return True
    
    def test_component_integration(self) -> bool:
        """Test integration between major components"""
        # Test heat source integration
        TestAssertions.assert_not_none(self.sim.heat_source, "Should have heat source")
        
        # Test that heat source affects reactor state
        initial_power = self.sim.state.power_level
        
        # Run a few steps
        for _ in range(5):
            self.sim.step()
        
        # Power should be influenced by heat source
        TestAssertions.assert_greater(self.sim.state.power_level, 0, "Power should be positive")
        
        # Test reactivity model integration
        result = self.sim.step()
        TestAssertions.assert_true("reactivity" in result["info"], "Should include reactivity info")
        
        return True
    
    def test_control_loop(self) -> bool:
        """Test control system integration"""
        initial_rod_position = self.sim.state.control_rod_position
        
        # Apply control action and verify it affects the system
        self.sim.step(ControlAction.CONTROL_ROD_INSERT)
        TestAssertions.assert_not_equal(self.sim.state.control_rod_position, initial_rod_position,
                                       "Control action should affect system")
        
        # Verify control affects physics
        rod_position_after = self.sim.state.control_rod_position
        
        # Run simulation to see physics response
        for _ in range(10):
            result = self.sim.step()
        
        # System should respond to control input
        TestAssertions.assert_true("reactivity" in result["info"], "Should calculate reactivity")
        
        return True
    
    def test_safety_integration(self) -> bool:
        """Test safety system integration with other components"""
        # Set up conditions that will trigger safety systems
        self.sim.state.fuel_temperature = 1400.0  # High but not immediately dangerous
        
        # Run simulation and gradually increase temperature
        for i in range(20):
            result = self.sim.step()
            
            # Artificially increase temperature to test safety response
            self.sim.state.fuel_temperature += 10.0
            
            if result["done"]:
                # Safety system should have activated
                TestAssertions.assert_true(self.sim.state.scram_status, "Safety system should activate")
                TestAssertions.assert_equal(self.sim.state.control_rod_position, 0,
                                           "Rods should be inserted on scram")
                break
        
        return True
    
    def test_data_flow(self) -> bool:
        """Test data flow between components"""
        # Test observation generation
        obs = self.sim.get_observation()
        TestAssertions.assert_equal(len(obs), 12, "Observation should have correct size")
        
        # Test that observation reflects current state
        power_obs = obs[10]  # Power level is at index 10
        actual_power = self.sim.state.power_level / 100.0  # Normalized
        TestAssertions.assert_almost_equal(power_obs, actual_power, tolerance=0.1,
                                         message="Observation should reflect actual state")
        
        # Test info dictionary
        result = self.sim.step()
        info = result["info"]
        
        TestAssertions.assert_true("time" in info, "Info should include time")
        TestAssertions.assert_true("thermal_power" in info, "Info should include thermal power")
        
        # Test history recording
        history_length = len(self.sim.history)
        self.sim.step()
        TestAssertions.assert_equal(len(self.sim.history), history_length + 1,
                                   "History should be updated each step")
        
        return True
