"""
Simulation Core Tests

Tests for the main nuclear plant simulator including state management,
control actions, and simulation stepping.
"""

import numpy as np

from simulator.core.sim import ControlAction, NuclearPlantSimulator, ReactorState
from tests.base_test import BaseTest, TestAssertions


class SimulationCoreTests(BaseTest):
    """Test suite for simulation core"""
    
    def __init__(self):
        super().__init__("Simulation Core")
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
        """Define all simulation core tests"""
        self.add_test("Simulator Initialization", self.test_initialization)
        self.add_test("State Management", self.test_state_management)
        self.add_test("Control Actions", self.test_control_actions)
        self.add_test("Simulation Stepping", self.test_simulation_stepping)
        self.add_test("Observation Generation", self.test_observation_generation)
        self.add_test("Reward Calculation", self.test_reward_calculation)
        self.add_test("Safety Systems", self.test_safety_systems)
        self.add_test("Reset Functionality", self.test_reset_functionality)
    
    def test_initialization(self) -> bool:
        """Test simulator initialization"""
        TestAssertions.assert_equal(self.sim.dt, 1.0, "Time step should be set")
        TestAssertions.assert_equal(self.sim.time, 0.0, "Initial time should be zero")
        TestAssertions.assert_not_none(self.sim.state, "Should have reactor state")
        TestAssertions.assert_not_none(self.sim.heat_source, "Should have heat source")
        
        # Check initial state values
        TestAssertions.assert_greater(self.sim.state.neutron_flux, 0, "Initial neutron flux should be positive")
        TestAssertions.assert_greater(self.sim.state.fuel_temperature, 0, "Initial fuel temperature should be positive")
        TestAssertions.assert_false(self.sim.state.scram_status, "Should not be in scram initially")
        
        return True
    
    def test_state_management(self) -> bool:
        """Test reactor state management"""
        # Test state access
        state = self.sim.state
        TestAssertions.assert_not_none(state, "Should have accessible state")
        
        # Test state modification
        original_power = state.power_level
        state.power_level = 85.0
        TestAssertions.assert_equal(state.power_level, 85.0, "State should be modifiable")
        
        # Test state validation
        TestAssertions.assert_greater(state.neutron_flux, 0, "Neutron flux should be positive")
        TestAssertions.assert_in_range(state.control_rod_position, 0, 100, "Rod position should be in valid range")
        TestAssertions.assert_greater(state.boron_concentration, 0, "Boron concentration should be positive")
        
        return True
    
    def test_control_actions(self) -> bool:
        """Test control action application"""
        initial_rod_position = self.sim.state.control_rod_position
        
        # Test rod insertion
        self.sim.apply_action(ControlAction.CONTROL_ROD_INSERT, magnitude=1.0)
        TestAssertions.assert_less(self.sim.state.control_rod_position, initial_rod_position,
                                  "Rod insertion should decrease position")
        
        # Test rod withdrawal
        current_position = self.sim.state.control_rod_position
        self.sim.apply_action(ControlAction.CONTROL_ROD_WITHDRAW, magnitude=1.0)
        TestAssertions.assert_greater(self.sim.state.control_rod_position, current_position,
                                     "Rod withdrawal should increase position")
        
        # Test boron control
        initial_boron = self.sim.state.boron_concentration
        self.sim.apply_action(ControlAction.BORATE_COOLANT, magnitude=1.0)
        TestAssertions.assert_greater(self.sim.state.boron_concentration, initial_boron,
                                     "Boration should increase boron concentration")
        
        # Test flow control
        initial_flow = self.sim.state.coolant_flow_rate
        self.sim.apply_action(ControlAction.INCREASE_COOLANT_FLOW, magnitude=1.0)
        TestAssertions.assert_greater(self.sim.state.coolant_flow_rate, initial_flow,
                                     "Should increase coolant flow")
        
        return True
    
    def test_simulation_stepping(self) -> bool:
        """Test simulation step functionality"""
        initial_time = self.sim.time
        
        # Perform simulation step
        result = self.sim.step()
        
        # Check time advancement
        TestAssertions.assert_greater(self.sim.time, initial_time, "Time should advance")
        TestAssertions.assert_almost_equal(self.sim.time, initial_time + self.sim.dt, tolerance=1e-6,
                                         message="Time should advance by dt")
        
        # Check return structure
        TestAssertions.assert_true("observation" in result, "Should return observation")
        TestAssertions.assert_true("reward" in result, "Should return reward")
        TestAssertions.assert_true("done" in result, "Should return done flag")
        TestAssertions.assert_true("info" in result, "Should return info dict")
        
        # Check observation
        obs = result["observation"]
        TestAssertions.assert_true(isinstance(obs, np.ndarray), "Observation should be numpy array")
        TestAssertions.assert_greater(len(obs), 0, "Observation should have elements")
        
        return True
    
    def test_observation_generation(self) -> bool:
        """Test observation vector generation"""
        obs = self.sim.get_observation()
        
        # Check observation properties
        TestAssertions.assert_true(isinstance(obs, np.ndarray), "Observation should be numpy array")
        TestAssertions.assert_equal(len(obs), 12, "Should have 12 observation elements")
        
        # Check that all values are finite
        TestAssertions.assert_true(np.all(np.isfinite(obs)), "All observation values should be finite")
        
        # Check normalization (most values should be in reasonable range)
        for i, val in enumerate(obs):
            if i != 11:  # Skip scram status (boolean)
                TestAssertions.assert_in_range(val, -10, 10, f"Observation element {i} should be normalized")
        
        return True
    
    def test_reward_calculation(self) -> bool:
        """Test reward calculation"""
        # Test normal operation reward
        self.sim.state.power_level = 100.0
        self.sim.state.fuel_temperature = 600.0
        self.sim.state.coolant_pressure = 15.5
        self.sim.state.scram_status = False
        
        reward = self.sim.calculate_reward()
        TestAssertions.assert_greater(reward, -10, "Normal operation should give reasonable reward")
        
        # Test penalty for power deviation
        self.sim.state.power_level = 80.0  # 20% deviation
        reward_deviation = self.sim.calculate_reward()
        TestAssertions.assert_less(reward_deviation, reward, "Power deviation should reduce reward")
        
        # Test penalty for high temperature
        self.sim.state.power_level = 100.0  # Reset
        self.sim.state.fuel_temperature = 900.0  # High temperature
        reward_temp = self.sim.calculate_reward()
        TestAssertions.assert_less(reward_temp, reward, "High temperature should reduce reward")
        
        # Test scram penalty
        self.sim.state.fuel_temperature = 600.0  # Reset
        self.sim.state.scram_status = True
        reward_scram = self.sim.calculate_reward()
        TestAssertions.assert_less(reward_scram, -50, "Scram should give large penalty")
        
        return True
    
    def test_safety_systems(self) -> bool:
        """Test safety system activation"""
        # Test normal conditions
        self.sim.state.fuel_temperature = 600.0
        self.sim.state.coolant_pressure = 15.5
        self.sim.state.coolant_flow_rate = 20000.0
        self.sim.state.power_level = 100.0
        self.sim.state.scram_status = False
        
        scram_activated = self.sim.check_safety_systems()
        TestAssertions.assert_false(scram_activated, "Normal conditions should not trigger scram")
        
        # Test high fuel temperature
        self.sim.state.fuel_temperature = 1600.0  # Above limit
        scram_activated = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram_activated, "High fuel temperature should trigger scram")
        TestAssertions.assert_true(self.sim.state.scram_status, "Scram status should be set")
        TestAssertions.assert_equal(self.sim.state.control_rod_position, 0, "Rods should be inserted")
        
        # Reset for next test
        self.sim.state.scram_status = False
        self.sim.state.fuel_temperature = 600.0
        self.sim.state.control_rod_position = 95.0
        
        # Test high pressure
        self.sim.state.coolant_pressure = 18.0  # Above limit
        scram_activated = self.sim.check_safety_systems()
        TestAssertions.assert_true(scram_activated, "High pressure should trigger scram")
        
        return True
    
    def test_reset_functionality(self) -> bool:
        """Test simulation reset"""
        # Modify state
        self.sim.state.power_level = 80.0
        self.sim.state.scram_status = True
        self.sim.time = 100.0
        self.sim.history = [1, 2, 3]  # Add some history
        
        # Reset simulation
        obs = self.sim.reset()
        
        # Check reset state
        TestAssertions.assert_equal(self.sim.time, 0.0, "Time should be reset")
        TestAssertions.assert_equal(len(self.sim.history), 0, "History should be cleared")
        TestAssertions.assert_false(self.sim.state.scram_status, "Scram should be reset")
        
        # Check returned observation
        TestAssertions.assert_true(isinstance(obs, np.ndarray), "Should return observation array")
        TestAssertions.assert_equal(len(obs), 12, "Should have correct observation size")
        
        return True
