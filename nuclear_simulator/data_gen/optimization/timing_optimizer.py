"""
Timing optimizer for target trigger time optimization.

This module provides binary search and iterative optimization algorithms
to find initial conditions that trigger maintenance at specific target times.
"""

import sys
import time
import copy
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simulator.core.sim import NuclearPlantSimulator


class TimingOptimizer:
    """
    Optimizes initial conditions to achieve target trigger timing
    
    Uses binary search and iterative refinement to find IC values that
    trigger maintenance at specific target times within tolerance.
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize timing optimizer
        
        Args:
            verbose: Enable verbose output during optimization
        """
        self.verbose = verbose
    
    def optimize_for_target_timing(self, base_config: Dict[str, Any], target_action: str,
                                 target_trigger_hours: float, tolerance_hours: float = 0.1,
                                 max_iterations: int = 10) -> Tuple[Dict[str, Any], Optional[float], int]:
        """
        Optimize initial conditions to achieve target trigger timing
        
        Args:
            base_config: Base configuration from ComprehensiveComposer
            target_action: Maintenance action to optimize
            target_trigger_hours: Target trigger time in hours
            tolerance_hours: Acceptable timing tolerance
            max_iterations: Maximum optimization iterations
            
        Returns:
            Tuple of (optimized_config, achieved_trigger_hours, iterations_used)
        """
        if self.verbose:
            print(f"🎯 Optimizing {target_action} for target timing: {target_trigger_hours:.2f}h ±{tolerance_hours:.2f}h")
        
        # Extract initial conditions from base config
        baseline_ics = self._extract_initial_conditions(base_config, target_action)
        
        if not baseline_ics:
            if self.verbose:
                print(f"   ⚠️ No initial conditions found for {target_action}")
            return base_config, None, 0
        
        # Test baseline performance
        baseline_trigger_time = self._test_trigger_timing(base_config, target_action, target_trigger_hours * 2)
        
        if self.verbose:
            print(f"   📊 Baseline trigger time: {baseline_trigger_time:.3f}h" if baseline_trigger_time else "   📊 Baseline: no trigger detected")
        
        # If baseline is already within tolerance, return it
        if baseline_trigger_time and abs(baseline_trigger_time - target_trigger_hours) <= tolerance_hours:
            if self.verbose:
                print(f"   ✅ Baseline already within tolerance!")
            return base_config, baseline_trigger_time, 0
        
        # Optimize each relevant parameter
        best_config = copy.deepcopy(base_config)
        best_trigger_time = baseline_trigger_time
        best_error = float('inf')
        iterations_used = 0
        
        for param_path, baseline_value in baseline_ics.items():
            if self.verbose:
                print(f"   🔧 Optimizing parameter: {param_path}")
            
            # Binary search for optimal value
            optimized_value, trigger_time, param_iterations = self._binary_search_parameter(
                base_config, target_action, param_path, baseline_value,
                target_trigger_hours, tolerance_hours, max_iterations
            )
            
            iterations_used += param_iterations
            
            if trigger_time:
                error = abs(trigger_time - target_trigger_hours)
                if error < best_error:
                    best_error = error
                    best_trigger_time = trigger_time
                    # Apply this optimization to best config
                    self._set_config_value(best_config, param_path, optimized_value)
                    
                    if self.verbose:
                        print(f"      ✅ Improved: {optimized_value:.3f} → {trigger_time:.3f}h (error: {error:.3f}h)")
                    
                    # Check if we've achieved target
                    if error <= tolerance_hours:
                        if self.verbose:
                            print(f"   🎯 Target achieved within tolerance!")
                        break
                else:
                    if self.verbose:
                        print(f"      ➡️ No improvement: {optimized_value:.3f} → {trigger_time:.3f}h")
            else:
                if self.verbose:
                    print(f"      ❌ No trigger detected for {param_path}")
        
        return best_config, best_trigger_time, iterations_used
    
    def _binary_search_parameter(self, base_config: Dict[str, Any], target_action: str,
                                param_path: str, baseline_value: float,
                                target_trigger_hours: float, tolerance_hours: float,
                                max_iterations: int) -> Tuple[float, Optional[float], int]:
        """
        Binary search for optimal parameter value
        
        Args:
            base_config: Base configuration
            target_action: Target maintenance action
            param_path: Parameter path to optimize
            baseline_value: Baseline parameter value
            target_trigger_hours: Target trigger time
            tolerance_hours: Timing tolerance
            max_iterations: Maximum search iterations
            
        Returns:
            Tuple of (optimized_value, achieved_trigger_time, iterations_used)
        """
        # Define search bounds based on parameter type
        min_value, max_value = self._get_parameter_bounds(param_path, baseline_value)
        
        best_value = baseline_value
        best_trigger_time = None
        best_error = float('inf')
        
        for iteration in range(max_iterations):
            # Test middle value
            test_value = (min_value + max_value) / 2
            
            # Create test config
            test_config = copy.deepcopy(base_config)
            self._set_config_value(test_config, param_path, test_value)
            
            # Test trigger timing
            trigger_time = self._test_trigger_timing(test_config, target_action, target_trigger_hours * 2)
            
            if trigger_time:
                error = abs(trigger_time - target_trigger_hours)
                
                # Track best result
                if error < best_error:
                    best_error = error
                    best_value = test_value
                    best_trigger_time = trigger_time
                
                # Check if within tolerance
                if error <= tolerance_hours:
                    return test_value, trigger_time, iteration + 1
                
                # Adjust search bounds
                if trigger_time < target_trigger_hours:
                    # Triggered too early - move away from threshold
                    if self._parameter_increases_degradation(param_path):
                        max_value = test_value  # Decrease degradation
                    else:
                        min_value = test_value  # Increase degradation
                else:
                    # Triggered too late - move closer to threshold
                    if self._parameter_increases_degradation(param_path):
                        min_value = test_value  # Increase degradation
                    else:
                        max_value = test_value  # Decrease degradation
            else:
                # No trigger - move closer to threshold
                if self._parameter_increases_degradation(param_path):
                    min_value = test_value  # Increase degradation
                else:
                    max_value = test_value  # Decrease degradation
            
            # Prevent infinite loops
            if abs(max_value - min_value) < baseline_value * 0.001:  # 0.1% precision
                break
        
        return best_value, best_trigger_time, max_iterations
    
    def _get_parameter_bounds(self, param_path: str, baseline_value: float) -> Tuple[float, float]:
        """
        Get reasonable search bounds for a parameter
        
        Args:
            param_path: Parameter path
            baseline_value: Baseline value
            
        Returns:
            Tuple of (min_value, max_value)
        """
        param_lower = param_path.lower()
        
        # Oil level bounds (percentage)
        if 'oil_level' in param_lower:
            return (10.0, min(100.0, baseline_value * 1.5))  # 10% to 150% of baseline (max 100%)
        
        # Temperature bounds
        elif 'temperature' in param_lower:
            return (max(0.0, baseline_value * 0.5), baseline_value * 2.0)  # 50% to 200% of baseline
        
        # Vibration bounds
        elif 'vibration' in param_lower:
            return (0.0, baseline_value * 3.0)  # 0 to 300% of baseline
        
        # Contamination bounds
        elif 'contamination' in param_lower:
            return (0.0, baseline_value * 5.0)  # 0 to 500% of baseline
        
        # Fouling bounds
        elif 'fouling' in param_lower:
            return (0.0, baseline_value * 4.0)  # 0 to 400% of baseline
        
        # Efficiency bounds
        elif 'efficiency' in param_lower:
            return (max(0.1, baseline_value * 0.5), min(1.0, baseline_value * 1.2))  # 50% to 120% (max 100%)
        
        # Default bounds
        else:
            return (max(0.0, baseline_value * 0.3), baseline_value * 3.0)  # 30% to 300% of baseline
    
    def _parameter_increases_degradation(self, param_path: str) -> bool:
        """
        Determine if increasing parameter value increases degradation
        
        Args:
            param_path: Parameter path
            
        Returns:
            True if increasing value increases degradation
        """
        param_lower = param_path.lower()
        
        # Parameters where higher values = more degradation
        degradation_increasing = [
            'contamination', 'fouling', 'vibration', 'temperature',
            'wear', 'corrosion', 'scale', 'deposits'
        ]
        
        # Parameters where higher values = less degradation
        degradation_decreasing = [
            'oil_level', 'efficiency', 'performance', 'quality',
            'pressure', 'flow'
        ]
        
        for keyword in degradation_increasing:
            if keyword in param_lower:
                return True
        
        for keyword in degradation_decreasing:
            if keyword in param_lower:
                return False
        
        # Default: assume higher values = more degradation
        return True
    
    def _test_trigger_timing(self, config: Dict[str, Any], target_action: str, 
                           max_simulation_hours: float) -> Optional[float]:
        """
        Test trigger timing for a configuration
        
        Args:
            config: Configuration to test
            target_action: Target maintenance action
            max_simulation_hours: Maximum simulation time
            
        Returns:
            Trigger time in hours, or None if no trigger
        """
        try:
            # Create simulator with test configuration
            simulator = NuclearPlantSimulator(
                enable_state_management=True,
                enable_secondary=True,
                secondary_config=config,
                dt=1.0  # 1 minute time step
            )
            
            # Reset to apply initial conditions
            # simulator.reset(start_at_steady_state=True)
            
            # Run simulation
            max_steps = int(max_simulation_hours * 60)  # Convert hours to minutes
            
            for step in range(max_steps):
                simulator.step()
                
                # Check for maintenance triggers
                if hasattr(simulator, 'state_manager') and simulator.state_manager:
                    maintenance_history = simulator.state_manager.get_maintenance_history()
                    
                    # Look for our target action
                    for record in maintenance_history:
                        if record.get('action') == target_action:
                            trigger_time_hours = record['timestamp'] / 3600.0
                            return trigger_time_hours
            
            # No trigger detected
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"      ⚠️ Simulation error: {e}")
            return None
    
    def _extract_initial_conditions(self, config: Dict[str, Any], target_action: str) -> Dict[str, float]:
        """
        Extract initial conditions from configuration
        
        Args:
            config: Configuration dictionary
            target_action: Target maintenance action
            
        Returns:
            Dictionary mapping parameter paths to values
        """
        initial_conditions = {}
        
        # Look for initial conditions in secondary system config
        if 'secondary_system' in config:
            secondary_config = config['secondary_system']
            
            # Check each subsystem for initial conditions
            for subsystem_name, subsystem_config in secondary_config.items():
                if isinstance(subsystem_config, dict) and 'initial_conditions' in subsystem_config:
                    ic_section = subsystem_config['initial_conditions']
                    
                    for param_name, value in ic_section.items():
                        param_path = f"secondary_system.{subsystem_name}.initial_conditions.{param_name}"
                        
                        # Handle list values (take first element)
                        if isinstance(value, list) and value:
                            initial_conditions[param_path] = float(value[0])
                        elif isinstance(value, (int, float)):
                            initial_conditions[param_path] = float(value)
        
        return initial_conditions
    
    def _set_config_value(self, config: Dict[str, Any], param_path: str, value: float):
        """
        Set a nested configuration value
        
        Args:
            config: Configuration dictionary to modify
            param_path: Dot-separated parameter path
            value: Value to set
        """
        path_parts = param_path.split('.')
        current = config
        
        # Navigate to parent
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set value
        final_key = path_parts[-1]
        
        # Handle list values
        if isinstance(current.get(final_key), list):
            # Set all list elements to the same value
            current[final_key] = [value] * len(current[final_key])
        else:
            current[final_key] = value
