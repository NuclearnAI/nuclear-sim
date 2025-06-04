"""
Control Systems Tests

Tests for control system functionality including control actions,
setpoint tracking, and control logic.
"""

from simulator.core.sim import ControlAction, NuclearPlantSimulator
from tests.base_test import BaseTest, TestAssertions


class ControlSystemTests(BaseTest):
    """Test suite for control systems"""
    
    def __init__(self):
        super().__init__("Control Systems")
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
        """Define all control system tests"""
        self.add_test("Control Action Enumeration", self.test_control_actions)
        self.add_test("Rod Control System", self.test_rod_control)
        self.add_test("Boron Control System", self.test_boron_control)
        self.add_test("Flow Control System", self.test_flow_control)
        self.add_test("Steam Control System", self.test_steam_control)
        self.add_test("Control Limits", self.test_control_limits)
        self.add_test("Control Response", self.test_control_response)
    
    def test_control_actions(self) -> bool:
        """Test control action enumeration"""
        # Test that all control actions exist
        actions = [
            ControlAction.CONTROL_ROD_INSERT,
            ControlAction.CONTROL_ROD_WITHDRAW,
            ControlAction.INCREASE_COOLANT_FLOW,
            ControlAction.DECREASE_COOLANT_FLOW,
            ControlAction.OPEN_STEAM_VALVE,
            ControlAction.CLOSE_STEAM_VALVE,
            ControlAction.INCREASE_FEEDWATER,
            ControlAction.DECREASE_FEEDWATER,
            ControlAction.NO_ACTION,
            ControlAction.DILUTE_BORON,
            ControlAction.BORATE_COOLANT,
        ]
        
        TestAssertions.assert_equal(len(actions), 11, "Should have 11 control actions")
        
        # Test that actions have unique values
        values = [action.value for action in actions]
        TestAssertions.assert_equal(len(set(values)), len(values), "Actions should have unique values")
        
        return True
    
    def test_rod_control(self) -> bool:
        """Test control rod system"""
        initial_position = self.sim.state.control_rod_position
        
        # Test rod insertion
        for _ in range(5):
            self.sim.apply_action(ControlAction.CONTROL_ROD_INSERT, magnitude=1.0)
        
        TestAssertions.assert_less(self.sim.state.control_rod_position, initial_position,
                                  "Rod insertion should decrease position")
        
        # Test rod withdrawal
        current_position = self.sim.state.control_rod_position
        for _ in range(3):
            self.sim.apply_action(ControlAction.CONTROL_ROD_WITHDRAW, magnitude=1.0)
        
        TestAssertions.assert_greater(self.sim.state.control_rod_position, current_position,
                                     "Rod withdrawal should increase position")
        
        # Test position limits
        TestAssertions.assert_in_range(self.sim.state.control_rod_position, 0, 100,
                                      "Rod position should be within limits")
        
        return True
    
    def test_boron_control(self) -> bool:
        """Test boron control system"""
        initial_boron = self.sim.state.boron_concentration
        
        # Test boration (adding boron)
        for _ in range(5):
            self.sim.apply_action(ControlAction.BORATE_COOLANT, magnitude=1.0)
        
        TestAssertions.assert_greater(self.sim.state.boron_concentration, initial_boron,
                                     "Boration should increase boron concentration")
        
        # Test dilution (removing boron)
        current_boron = self.sim.state.boron_concentration
        for _ in range(3):
            self.sim.apply_action(ControlAction.DILUTE_BORON, magnitude=1.0)
        
        TestAssertions.assert_less(self.sim.state.boron_concentration, current_boron,
                                  "Dilution should decrease boron concentration")
        
        # Test concentration limits
        TestAssertions.assert_greater_equal(self.sim.state.boron_concentration, 0,
                                           "Boron concentration should not be negative")
        
        return True
    
    def test_flow_control(self) -> bool:
        """Test coolant flow control"""
        initial_flow = self.sim.state.coolant_flow_rate
        
        # Test flow increase
        for _ in range(3):
            self.sim.apply_action(ControlAction.INCREASE_COOLANT_FLOW, magnitude=1.0)
        
        TestAssertions.assert_greater(self.sim.state.coolant_flow_rate, initial_flow,
                                     "Should increase coolant flow")
        
        # Test flow decrease
        current_flow = self.sim.state.coolant_flow_rate
        for _ in range(2):
            self.sim.apply_action(ControlAction.DECREASE_COOLANT_FLOW, magnitude=1.0)
        
        TestAssertions.assert_less(self.sim.state.coolant_flow_rate, current_flow,
                                  "Should decrease coolant flow")
        
        # Test flow limits
        TestAssertions.assert_greater(self.sim.state.coolant_flow_rate, 0,
                                     "Flow rate should be positive")
        
        return True
    
    def test_steam_control(self) -> bool:
        """Test steam system control"""
        initial_valve = self.sim.state.steam_valve_position
        initial_feedwater = self.sim.state.feedwater_flow_rate
        
        # Test steam valve control
        self.sim.apply_action(ControlAction.OPEN_STEAM_VALVE, magnitude=1.0)
        TestAssertions.assert_greater(self.sim.state.steam_valve_position, initial_valve,
                                     "Should open steam valve")
        
        self.sim.apply_action(ControlAction.CLOSE_STEAM_VALVE, magnitude=1.0)
        TestAssertions.assert_less(self.sim.state.steam_valve_position, 
                                  self.sim.state.steam_valve_position,
                                  "Should close steam valve")
        
        # Test feedwater control
        self.sim.apply_action(ControlAction.INCREASE_FEEDWATER, magnitude=1.0)
        TestAssertions.assert_greater(self.sim.state.feedwater_flow_rate, initial_feedwater,
                                     "Should increase feedwater flow")
        
        self.sim.apply_action(ControlAction.DECREASE_FEEDWATER, magnitude=1.0)
        TestAssertions.assert_less(self.sim.state.feedwater_flow_rate,
                                  self.sim.state.feedwater_flow_rate,
                                  "Should decrease feedwater flow")
        
        return True
    
    def test_control_limits(self) -> bool:
        """Test control system limits"""
        # Test rod position limits
        for _ in range(50):  # Try to over-insert
            self.sim.apply_action(ControlAction.CONTROL_ROD_INSERT, magnitude=1.0)
        
        TestAssertions.assert_greater_equal(self.sim.state.control_rod_position, 0,
                                           "Rod position should not go below 0")
        
        for _ in range(100):  # Try to over-withdraw
            self.sim.apply_action(ControlAction.CONTROL_ROD_WITHDRAW, magnitude=1.0)
        
        TestAssertions.assert_less_equal(self.sim.state.control_rod_position, 100,
                                        "Rod position should not exceed 100")
        
        # Test boron limits
        for _ in range(100):  # Try to over-dilute
            self.sim.apply_action(ControlAction.DILUTE_BORON, magnitude=1.0)
        
        TestAssertions.assert_greater_equal(self.sim.state.boron_concentration, 0,
                                           "Boron concentration should not be negative")
        
        return True
    
    def test_control_response(self) -> bool:
        """Test control system response characteristics"""
        # Test magnitude scaling
        initial_position = self.sim.state.control_rod_position
        
        # Small magnitude
        self.sim.apply_action(ControlAction.CONTROL_ROD_INSERT, magnitude=0.1)
        small_change = initial_position - self.sim.state.control_rod_position
        
        # Reset
        self.sim.state.control_rod_position = initial_position
        
        # Large magnitude
        self.sim.apply_action(ControlAction.CONTROL_ROD_INSERT, magnitude=1.0)
        large_change = initial_position - self.sim.state.control_rod_position
        
        TestAssertions.assert_greater(large_change, small_change,
                                     "Larger magnitude should produce larger change")
        
        # Test no action
        initial_state = {
            'rod_position': self.sim.state.control_rod_position,
            'boron_concentration': self.sim.state.boron_concentration,
            'coolant_flow': self.sim.state.coolant_flow_rate
        }
        
        self.sim.apply_action(ControlAction.NO_ACTION, magnitude=1.0)
        
        TestAssertions.assert_equal(self.sim.state.control_rod_position, initial_state['rod_position'],
                                   "No action should not change rod position")
        TestAssertions.assert_equal(self.sim.state.boron_concentration, initial_state['boron_concentration'],
                                   "No action should not change boron concentration")
        TestAssertions.assert_equal(self.sim.state.coolant_flow_rate, initial_state['coolant_flow'],
                                   "No action should not change coolant flow")
        
        return True
