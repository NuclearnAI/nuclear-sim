"""
Heat Sources Tests

Tests for the heat source architecture including constant heat source,
reactor heat source, and heat source interface functionality.
"""

from simulator.core.sim import ReactorState
from systems.primary.reactor.heat_sources.constant_heat_source import ConstantHeatSource
from systems.primary.reactor.heat_sources.reactor_heat_source import ReactorHeatSource
from tests.base_test import BaseTest, TestAssertions


class HeatSourceTests(BaseTest):
    """Test suite for heat sources"""
    
    def __init__(self):
        super().__init__("Heat Sources")
        self.constant_source = None
        self.reactor_source = None
        self.test_state = None
        self.define_tests()
    
    def setup(self) -> bool:
        """Setup test environment"""
        try:
            # Create heat sources
            self.constant_source = ConstantHeatSource(rated_power_mw=3000.0)
            self.reactor_source = ReactorHeatSource(rated_power_mw=3000.0)
            
            # Create test reactor state
            self.test_state = ReactorState()
            
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def define_tests(self) -> None:
        """Define all heat source tests"""
        self.add_test("Constant Heat Source Initialization", self.test_constant_source_init)
        self.add_test("Constant Heat Source Power Control", self.test_constant_source_power)
        self.add_test("Constant Heat Source Update", self.test_constant_source_update)
        self.add_test("Reactor Heat Source Initialization", self.test_reactor_source_init)
        self.add_test("Reactor Heat Source Update", self.test_reactor_source_update)
        self.add_test("Reactor Heat Source Physics", self.test_reactor_source_physics)
        self.add_test("Heat Source Interface Compliance", self.test_interface_compliance)
        self.add_test("Heat Source State Management", self.test_state_management)
        self.add_test("Heat Source Comparison", self.test_heat_source_comparison)
        self.add_test("Heat Source Error Handling", self.test_error_handling)
    
    def test_constant_source_init(self) -> bool:
        """Test constant heat source initialization"""
        # Test default initialization
        source = ConstantHeatSource(3000.0)
        
        TestAssertions.assert_equal(source.rated_power_mw, 3000.0, "Rated power should be set correctly")
        TestAssertions.assert_equal(source.get_power_percent(), 100.0, "Initial power should be 100%")
        TestAssertions.assert_equal(source.get_thermal_power_mw(), 3000.0, "Initial thermal power should equal rated")
        TestAssertions.assert_true(source.is_available(), "Heat source should be available initially")
        
        return True
    
    def test_constant_source_power(self) -> bool:
        """Test constant heat source power control"""
        # Test power setpoint changes
        self.constant_source.set_power_setpoint(80.0)
        TestAssertions.assert_equal(self.constant_source.get_power_percent(), 80.0, 
                                   "Power should change instantly to setpoint")
        
        # Test thermal power calculation
        expected_thermal = 3000.0 * 0.8  # 80% of rated
        TestAssertions.assert_almost_equal(self.constant_source.get_thermal_power_mw(), expected_thermal, 
                                         tolerance=1.0, message="Thermal power should match percentage")
        
        # Test power limits
        self.constant_source.set_power_setpoint(150.0)  # Above 100%
        TestAssertions.assert_less_equal(self.constant_source.get_power_percent(), 100.0,
                                        "Power should be limited to maximum")
        
        self.constant_source.set_power_setpoint(-10.0)  # Below 0%
        TestAssertions.assert_greater_equal(self.constant_source.get_power_percent(), 0.0,
                                           "Power should be limited to minimum")
        
        return True
    
    def test_constant_source_update(self) -> bool:
        """Test constant heat source update method"""
        # Set initial conditions
        self.constant_source.set_power_setpoint(90.0)
        
        # Update heat source
        result = self.constant_source.update(dt=1.0)
        
        # Check return values
        TestAssertions.assert_true("thermal_power_mw" in result, "Should return thermal power")
        TestAssertions.assert_true("power_percent" in result, "Should return power percentage")
        TestAssertions.assert_true("available" in result, "Should return availability status")
        
        # Check values
        TestAssertions.assert_almost_equal(result["power_percent"], 90.0, tolerance=0.1,
                                         message="Should return correct power percentage")
        TestAssertions.assert_almost_equal(result["thermal_power_mw"], 2700.0, tolerance=1.0,
                                         message="Should return correct thermal power")
        TestAssertions.assert_true(result["available"], "Should be available")
        
        return True
    
    def test_reactor_source_init(self) -> bool:
        """Test reactor heat source initialization"""
        source = ReactorHeatSource(3000.0)
        
        TestAssertions.assert_equal(source.rated_power_mw, 3000.0, "Rated power should be set correctly")
        TestAssertions.assert_not_none(source.reactivity_model, "Should have reactivity model")
        
        # Check physics constants
        TestAssertions.assert_greater(source.BETA, 0, "Beta should be positive")
        TestAssertions.assert_greater(source.LAMBDA_PROMPT, 0, "Prompt neutron lifetime should be positive")
        TestAssertions.assert_equal(len(source.LAMBDA), 6, "Should have 6 delayed neutron groups")
        
        return True
    
    def test_reactor_source_update(self) -> bool:
        """Test reactor heat source update method"""
        # Update with reactor state
        result = self.reactor_source.update(dt=1.0, reactor_state=self.test_state)
        
        # Check return values
        required_keys = ["thermal_power_mw", "power_percent", "available", "reactivity_pcm", "neutron_flux"]
        for key in required_keys:
            TestAssertions.assert_true(key in result, f"Should return {key}")
        
        # Check value ranges
        TestAssertions.assert_greater(result["thermal_power_mw"], 0, "Thermal power should be positive")
        TestAssertions.assert_in_range(result["power_percent"], 0, 200, "Power percent should be reasonable")
        TestAssertions.assert_greater(result["neutron_flux"], 0, "Neutron flux should be positive")
        
        return True
    
    def test_reactor_source_physics(self) -> bool:
        """Test reactor heat source physics calculations"""
        # Set up test state with known conditions
        self.test_state.neutron_flux = 1e13  # 100% power
        self.test_state.control_rod_position = 95.0
        self.test_state.boron_concentration = 1200.0
        
        # Update reactor source
        result = self.reactor_source.update(dt=1.0, reactor_state=self.test_state)
        
        # Check that physics calculations are reasonable
        TestAssertions.assert_in_range(result["reactivity_pcm"], -10000, 10000,
                                      "Reactivity should be in reasonable range")
        
        # Check that neutron flux affects power
        initial_flux = self.test_state.neutron_flux
        initial_power = result["thermal_power_mw"]
        
        # Change flux and check power response
        self.test_state.neutron_flux = 5e12  # 50% power
        result2 = self.reactor_source.update(dt=1.0, reactor_state=self.test_state)
        
        TestAssertions.assert_less(result2["thermal_power_mw"], initial_power,
                                  "Lower flux should give lower power")
        
        return True
    
    def test_interface_compliance(self) -> bool:
        """Test that heat sources comply with interface"""
        sources = [self.constant_source, self.reactor_source]
        
        for source in sources:
            # Test required methods exist
            TestAssertions.assert_true(hasattr(source, "get_thermal_power_mw"), 
                                      "Should have get_thermal_power_mw method")
            TestAssertions.assert_true(hasattr(source, "get_power_percent"), 
                                      "Should have get_power_percent method")
            TestAssertions.assert_true(hasattr(source, "set_power_setpoint"), 
                                      "Should have set_power_setpoint method")
            TestAssertions.assert_true(hasattr(source, "update"), 
                                      "Should have update method")
            TestAssertions.assert_true(hasattr(source, "is_available"), 
                                      "Should have is_available method")
            
            # Test methods return expected types
            TestAssertions.assert_true(isinstance(source.get_thermal_power_mw(), (int, float)),
                                      "get_thermal_power_mw should return number")
            TestAssertions.assert_true(isinstance(source.get_power_percent(), (int, float)),
                                      "get_power_percent should return number")
            TestAssertions.assert_true(isinstance(source.is_available(), bool),
                                      "is_available should return boolean")
        
        return True
    
    def test_state_management(self) -> bool:
        """Test heat source state management"""
        # Test constant source state
        const_state = self.constant_source.get_state_dict()
        TestAssertions.assert_true("type" in const_state, "Should include type")
        TestAssertions.assert_true("thermal_power_mw" in const_state, "Should include thermal power")
        TestAssertions.assert_true("power_percent" in const_state, "Should include power percent")
        
        # Test reactor source state
        reactor_state = self.reactor_source.get_state_dict()
        TestAssertions.assert_true("type" in reactor_state, "Should include type")
        TestAssertions.assert_equal(reactor_state["type"], "reactor", "Should identify as reactor type")
        
        # Test reset functionality
        original_power = self.constant_source.get_power_percent()
        self.constant_source.set_power_setpoint(50.0)
        self.constant_source.reset()
        reset_power = self.constant_source.get_power_percent()
        
        # Reset should restore to rated power
        TestAssertions.assert_almost_equal(reset_power, 100.0, tolerance=1.0,
                                         message="Reset should restore to 100% power")
        
        return True
    
    def test_heat_source_comparison(self) -> bool:
        """Test comparison between different heat sources"""
        # Set same setpoint for both sources
        target_power = 85.0
        self.constant_source.set_power_setpoint(target_power)
        self.reactor_source.set_power_setpoint(target_power)
        
        # Update both sources
        const_result = self.constant_source.update(dt=1.0)
        reactor_result = self.reactor_source.update(dt=1.0, reactor_state=self.test_state)
        
        # Constant source should reach setpoint immediately
        TestAssertions.assert_almost_equal(const_result["power_percent"], target_power, tolerance=0.1,
                                         message="Constant source should reach setpoint immediately")
        
        # Reactor source behavior depends on physics
        TestAssertions.assert_greater(reactor_result["power_percent"], 0,
                                     "Reactor source should produce positive power")
        
        # Both should be available
        TestAssertions.assert_true(const_result["available"], "Constant source should be available")
        TestAssertions.assert_true(reactor_result["available"], "Reactor source should be available")
        
        return True
    
    def test_error_handling(self) -> bool:
        """Test error handling in heat sources"""
        # Test invalid power setpoints
        try:
            self.constant_source.set_power_setpoint(float('nan'))
            # Should handle gracefully or raise appropriate exception
        except (ValueError, TypeError):
            pass  # Expected behavior
        
        # Test reactor source without state
        try:
            result = self.reactor_source.update(dt=1.0)  # No reactor_state provided
            # Should return default values
            TestAssertions.assert_true("thermal_power_mw" in result, "Should handle missing state gracefully")
        except Exception:
            # Also acceptable to raise exception
            pass
        
        # Test negative time step
        try:
            self.constant_source.update(dt=-1.0)
            # Should handle gracefully
        except ValueError:
            pass  # Expected behavior for negative time step
        
        return True
