#!/usr/bin/env python3
"""
Actual Timing Test using Real Pump Physics

This script uses the actual feedwater pump physics to simulate degradation
and measure when maintenance thresholds are actually triggered.
"""

import sys
import os
import time
from typing import Dict, List, Tuple

# Add the nuclear_simulator to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from nuclear_simulator.systems.secondary.feedwater.physics import EnhancedFeedwaterPhysics
from nuclear_simulator.systems.secondary.feedwater.config import create_standard_feedwater_config
from nuclear_simulator.data_gen.config_engine.initial_conditions.feedwater_conditions import FEEDWATER_CONDITIONS

class ActualTimingTester:
    """Tests actual timing using real pump physics"""
    
    def __init__(self):
        self.thresholds = {
            "pump_oil_contamination": 14.9,
            "pump_oil_levels": 60.0,  # less_than trigger
            "motor_temperature": 85.0,
            "motor_bearing_wear": 8.0,
            "pump_bearing_wear": 6.0,
            "thrust_bearing_wear": 4.0,
            "seal_face_wear": 15.0,
            "oil_water_content": 0.08,
            "oil_acid_number": 1.6,
            "lubrication_effectiveness": 0.85,  # less_than trigger
            "efficiency_factor": 0.85,  # less_than trigger
            "vibration_increase": 1.5,
            "system_health_factor": 0.80,  # less_than trigger
        }
    
    def create_feedwater_system_with_conditions(self, scenario_name: str):
        """Create feedwater system with specific initial conditions"""
        
        if scenario_name not in FEEDWATER_CONDITIONS:
            raise ValueError(f"Scenario {scenario_name} not found")
        
        # Create base config
        config = create_standard_feedwater_config()
        
        # Apply initial conditions from scenario
        scenario_conditions = FEEDWATER_CONDITIONS[scenario_name]
        
        # Update config initial conditions with scenario values
        for param, value in scenario_conditions.items():
            if hasattr(config.initial_conditions, param):
                setattr(config.initial_conditions, param, value)
            elif param in ['description', 'expected_action', 'threshold_triggered', 'competing_actions_prevented']:
                # Skip metadata fields
                continue
            else:
                # For parameters not in initial_conditions, try to set them directly
                print(f"   Warning: Parameter {param} not found in initial_conditions, skipping")
        
        # Fix NPSH issues by setting better values
        if hasattr(config.initial_conditions, 'npsh_available'):
            config.initial_conditions.npsh_available = [20.0, 20.0, 20.0, 20.0]
        
        # Create feedwater system
        feedwater_system = EnhancedFeedwaterPhysics(config=config)
        
        return feedwater_system
    
    def simulate_until_threshold(self, scenario_name: str, max_minutes: int = 300) -> Dict:
        """Simulate scenario until threshold is hit or max time reached"""
        
        print(f"\n🔬 Testing scenario: {scenario_name}")
        print(f"   Description: {FEEDWATER_CONDITIONS[scenario_name].get('description', 'N/A')}")
        
        try:
            # Create system with initial conditions
            feedwater_system = self.create_feedwater_system_with_conditions(scenario_name)
            
            # Simulation parameters
            dt_minutes = 10.0  # 10 minute time steps
            current_time = 0.0
            threshold_hit = False
            threshold_param = None
            threshold_value = None
            
            # Standard operating conditions
            sg_conditions = {
                'levels': [12.5, 12.5, 12.5],
                'pressures': [6.9, 6.9, 6.9],
                'steam_flows': [500.0, 500.0, 500.0],
                'steam_qualities': [0.99, 0.99, 0.99]
            }
            
            steam_demands = {'total_flow': 1500.0}
            
            system_conditions = {
                'feedwater_temperature': 227.0,
                'suction_pressure': 0.5,
                'discharge_pressure': 8.0
            }
            
            # Track initial values
            initial_state = feedwater_system.get_state_dict()
            print(f"   Initial state snapshot:")
            for key, value in initial_state.items():
                if any(param in key for param in self.thresholds.keys()):
                    print(f"     {key}: {value}")
            
            # Simulation loop
            while current_time < max_minutes and not threshold_hit:
                # Update system
                result = feedwater_system.update_state(
                    sg_conditions=sg_conditions,
                    steam_generator_demands=steam_demands,
                    system_conditions=system_conditions,
                    dt=dt_minutes
                )
                
                current_time += dt_minutes
                
                # Check thresholds
                current_state = feedwater_system.get_state_dict()
                
                # Check thresholds based on scenario type
                scenario_info = FEEDWATER_CONDITIONS[scenario_name]
                expected_action = scenario_info.get("expected_action", "")
                
                if hasattr(feedwater_system.pump_system, 'pumps'):
                    for pump_id, pump in feedwater_system.pump_system.pumps.items():
                        if hasattr(pump, 'lubrication_system'):
                            
                            # Only check the primary trigger for each scenario
                            if "oil_change" in scenario_name:
                                oil_contamination = pump.lubrication_system.oil_contamination_level
                                if oil_contamination >= self.thresholds["pump_oil_contamination"]:
                                    threshold_hit = True
                                    threshold_param = "pump_oil_contamination"
                                    threshold_value = oil_contamination
                                    break
                            
                            elif "oil_top_off" in scenario_name:
                                oil_level = pump.lubrication_system.oil_level
                                if oil_level <= self.thresholds["pump_oil_levels"]:
                                    threshold_hit = True
                                    threshold_param = "pump_oil_levels"
                                    threshold_value = oil_level
                                    break
                            
                            elif "motor_inspection" in scenario_name:
                                motor_temp = pump.state.motor_temperature
                                if motor_temp >= self.thresholds["motor_temperature"]:
                                    threshold_hit = True
                                    threshold_param = "motor_temperature"
                                    threshold_value = motor_temp
                                    break
                            
                            elif "motor_bearing_replacement" in scenario_name:
                                motor_bearing_wear = pump.lubrication_system.component_wear.get('motor_bearings', 0.0)
                                if motor_bearing_wear >= self.thresholds["motor_bearing_wear"]:
                                    threshold_hit = True
                                    threshold_param = "motor_bearing_wear"
                                    threshold_value = motor_bearing_wear
                                    break
                            
                            elif "pump_bearing_replacement" in scenario_name:
                                pump_bearing_wear = pump.lubrication_system.component_wear.get('pump_bearings', 0.0)
                                if pump_bearing_wear >= self.thresholds["pump_bearing_wear"]:
                                    threshold_hit = True
                                    threshold_param = "pump_bearing_wear"
                                    threshold_value = pump_bearing_wear
                                    break
                            
                            elif "thrust_bearing_replacement" in scenario_name:
                                thrust_bearing_wear = pump.lubrication_system.component_wear.get('thrust_bearing', 0.0)
                                if thrust_bearing_wear >= self.thresholds["thrust_bearing_wear"]:
                                    threshold_hit = True
                                    threshold_param = "thrust_bearing_wear"
                                    threshold_value = thrust_bearing_wear
                                    break
                
                # Print progress every hour
                if current_time % 60 == 0:
                    print(f"   Time: {current_time:3.0f} min - Still running...")
            
            # Results
            result = {
                "scenario": scenario_name,
                "threshold_hit": threshold_hit,
                "time_minutes": current_time,
                "threshold_param": threshold_param,
                "threshold_value": threshold_value,
                "within_target": threshold_hit and 100 <= current_time <= 200,
                "status": "TIMEOUT" if current_time >= max_minutes else "COMPLETED"
            }
            
            if threshold_hit:
                status = "✓ PASS" if result["within_target"] else "✗ FAIL"
                print(f"   {status} Threshold hit at {current_time:.0f} minutes")
                print(f"   Parameter: {threshold_param} = {threshold_value:.3f}")
            else:
                print(f"   ⏰ TIMEOUT No threshold hit after {max_minutes} minutes")
            
            return result
            
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            return {
                "scenario": scenario_name,
                "error": str(e),
                "threshold_hit": False,
                "time_minutes": 0,
                "within_target": False,
                "status": "ERROR"
            }
    
    def test_key_scenarios(self) -> Dict:
        """Test key scenarios with actual physics"""
        
        print("=" * 80)
        print("ACTUAL TIMING TEST USING REAL PUMP PHYSICS")
        print("=" * 80)
        print("Target: Thresholds should trigger between 100-200 minutes")
        print()
        
        # Test key scenarios
        key_scenarios = [
            "oil_change",
            "oil_top_off", 
            "motor_inspection",
            "motor_bearing_replacement",
            "pump_bearing_replacement",
            "thrust_bearing_replacement"
        ]
        
        results = {}
        summary = {
            "total_tested": 0,
            "within_target": 0,
            "outside_target": 0,
            "errors": 0
        }
        
        for scenario in key_scenarios:
            if scenario in FEEDWATER_CONDITIONS:
                result = self.simulate_until_threshold(scenario, max_minutes=300)
                results[scenario] = result
                summary["total_tested"] += 1
                
                if "error" in result:
                    summary["errors"] += 1
                elif result["within_target"]:
                    summary["within_target"] += 1
                else:
                    summary["outside_target"] += 1
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total scenarios tested: {summary['total_tested']}")
        print(f"Within target (100-200 min): {summary['within_target']}")
        print(f"Outside target: {summary['outside_target']}")
        print(f"Errors: {summary['errors']}")
        
        if summary["within_target"] > 0:
            success_rate = summary["within_target"] / summary["total_tested"] * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        # Detailed results
        print("\nDETAILED RESULTS:")
        for scenario, result in results.items():
            if "error" not in result:
                status = "✓" if result["within_target"] else "✗"
                print(f"{status} {scenario:<25} {result['time_minutes']:>6.0f} min  {result['threshold_param'] or 'N/A'}")
            else:
                print(f"❌ {scenario:<25} ERROR: {result['error']}")
        
        return {"summary": summary, "results": results}

def main():
    """Run the actual timing test"""
    tester = ActualTimingTester()
    results = tester.test_key_scenarios()
    
    # Return exit code based on success
    if results["summary"]["outside_target"] == 0 and results["summary"]["errors"] == 0:
        print("\n✅ TEST PASSED: All scenarios trigger within target range")
        return 0
    else:
        print(f"\n❌ TEST ISSUES: Check results above")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
