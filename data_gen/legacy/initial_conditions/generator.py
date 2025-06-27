"""
Initial conditions generator for maintenance scenarios.

This module generates intelligent initial conditions that position component
parameters near maintenance thresholds for natural triggering during simulation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .analyzer import ThresholdAnalyzer


class InitialConditionsGenerator:
    """
    Generates targeted initial conditions for maintenance scenario testing
    
    This class analyzes threshold configurations and generates initial conditions
    that position parameters strategically for natural maintenance triggering.
    """
    
    def __init__(self, analyzer: ThresholdAnalyzer):
        """
        Initialize generator with a threshold analyzer
        
        Args:
            analyzer: ThresholdAnalyzer instance for understanding thresholds
        """
        self.analyzer = analyzer
        self.simulator = analyzer.simulator
        self.state_manager = analyzer.state_manager
    
    def generate_conditions_for_action(self, target_action: str, 
                                     target_trigger_time_hours: float = 1.0,
                                     safety_margin: float = 0.05) -> Dict[str, float]:
        """
        Generate initial conditions to trigger a specific maintenance action
        
        Args:
            target_action: Maintenance action to target (e.g., "oil_top_off")
            target_trigger_time_hours: When we want maintenance to trigger (hours)
            safety_margin: Safety margin from threshold (0.05 = 5%)
            
        Returns:
            Dictionary mapping parameter names to initial values
        """
        print(f"GENERATOR: Generating initial conditions for {target_action}")
        
        # Get components and thresholds for this action
        components = self.analyzer.find_components_for_action(target_action)
        action_thresholds = self.analyzer.get_thresholds_for_action(target_action)
        
        if not components:
            raise ValueError(f"No components found that can trigger action: {target_action}")
        
        print(f"GENERATOR: Found {len(components)} components that can trigger {target_action}")
        
        initial_conditions = {}
        
        for component_id in components:
            component_thresholds = action_thresholds.get(component_id, {})
            
            for param_name, threshold_config in component_thresholds.items():
                # Generate initial value for this parameter
                initial_value = self._calculate_initial_value(
                    param_name, threshold_config, target_trigger_time_hours, safety_margin
                )
                
                if initial_value is not None:
                    # Create full parameter name for configuration
                    full_param_name = f"{component_id}.{param_name}"
                    initial_conditions[full_param_name] = initial_value
                    
                    print(f"GENERATOR: {full_param_name} = {initial_value:.3f} "
                          f"(threshold: {threshold_config['threshold']}, "
                          f"comparison: {threshold_config['comparison']})")
        
        return initial_conditions
    
    def _calculate_initial_value(self, param_name: str, threshold_config: Dict[str, Any],
                                target_trigger_time_hours: float, safety_margin: float) -> Optional[float]:
        """
        Calculate initial value for a parameter to trigger at target time
        
        Args:
            param_name: Parameter name
            threshold_config: Threshold configuration
            target_trigger_time_hours: Target trigger time
            safety_margin: Safety margin from threshold
            
        Returns:
            Initial parameter value or None if cannot calculate
        """
        threshold = threshold_config.get('threshold')
        comparison = threshold_config.get('comparison', 'greater_than')
        
        if threshold is None:
            return None
        
        # Estimate degradation rate based on parameter type
        degradation_rate = self._estimate_degradation_rate(param_name, threshold)
        
        if degradation_rate == 0:
            # No degradation expected, position near threshold
            return self._calculate_near_threshold_value(threshold, comparison, safety_margin)
        
        # Calculate where to start to hit threshold at target time
        if comparison == "greater_than":
            # Parameter increases over time, start below threshold
            initial_value = threshold - (degradation_rate * target_trigger_time_hours)
            # Apply safety margin (start a bit further from threshold)
            initial_value -= threshold * safety_margin
        elif comparison == "less_than":
            # Parameter decreases over time, start above threshold
            initial_value = threshold + (degradation_rate * target_trigger_time_hours)
            # Apply safety margin (start a bit further from threshold)
            initial_value += threshold * safety_margin
        else:
            # For other comparisons, just position near threshold
            initial_value = self._calculate_near_threshold_value(threshold, comparison, safety_margin)
        
        # Apply realistic bounds
        initial_value = self._apply_realistic_bounds(param_name, initial_value, threshold)
        
        return initial_value
    
    def _estimate_degradation_rate(self, param_name: str, threshold: float) -> float:
        """
        Estimate degradation rate for a parameter
        
        Args:
            param_name: Parameter name
            threshold: Threshold value
            
        Returns:
            Estimated degradation rate per hour
        """
        param_lower = param_name.lower()
        
        # Oil level degradation (decreases over time)
        if 'oil_level' in param_lower:
            # Oil level typically decreases 1-2% per hour under normal operation
            return threshold * 0.015  # 1.5% per hour
        
        # Oil contamination (increases over time)
        if 'oil_contamination' in param_lower or 'contamination' in param_lower:
            # Contamination typically increases 0.5-1 ppm per hour
            return 0.75  # 0.75 ppm per hour
        
        # Bearing temperature (increases with wear)
        if 'bearing_temperature' in param_lower or 'temperature' in param_lower:
            # Temperature typically increases 1-2°C per hour under stress
            return 1.5  # 1.5°C per hour
        
        # Vibration (increases with wear)
        if 'vibration' in param_lower:
            # Vibration typically increases 0.5-1 mm/s per hour under stress
            return 0.75  # 0.75 mm/s per hour
        
        # Fouling (increases over time)
        if 'fouling' in param_lower:
            # Fouling typically increases slowly
            return threshold * 0.01  # 1% per hour
        
        # Efficiency (decreases over time)
        if 'efficiency' in param_lower:
            # Efficiency typically decreases slowly
            return threshold * 0.005  # 0.5% per hour
        
        # Default: no degradation (position near threshold)
        return 0.0
    
    def _calculate_near_threshold_value(self, threshold: float, comparison: str, 
                                      safety_margin: float) -> float:
        """
        Calculate value near threshold for immediate or quick triggering
        
        Args:
            threshold: Threshold value
            comparison: Comparison operator
            safety_margin: Safety margin
            
        Returns:
            Value positioned near threshold
        """
        if comparison == "greater_than":
            # Start just below threshold
            return threshold * (1.0 - safety_margin)
        elif comparison == "less_than":
            # Start just above threshold
            return threshold * (1.0 + safety_margin)
        elif comparison == "greater_equal":
            # Start just below threshold
            return threshold * (1.0 - safety_margin)
        elif comparison == "less_equal":
            # Start just above threshold
            return threshold * (1.0 + safety_margin)
        else:
            # For equals/not_equals, start at threshold
            return threshold
    
    def _apply_realistic_bounds(self, param_name: str, value: float, threshold: float) -> float:
        """
        Apply realistic bounds to parameter values
        
        Args:
            param_name: Parameter name
            value: Calculated value
            threshold: Threshold value
            
        Returns:
            Bounded value
        """
        param_lower = param_name.lower()
        
        # Oil level bounds (0-100%)
        if 'oil_level' in param_lower:
            return max(0.0, min(100.0, value))
        
        # Oil contamination bounds (0-50 ppm typically)
        if 'oil_contamination' in param_lower or 'contamination' in param_lower:
            return max(0.0, min(50.0, value))
        
        # Temperature bounds (0-200°C for most components)
        if 'temperature' in param_lower:
            return max(0.0, min(200.0, value))
        
        # Vibration bounds (0-100 mm/s)
        if 'vibration' in param_lower:
            return max(0.0, min(100.0, value))
        
        # Fouling bounds (0-1 for fractions, 0-10mm for thickness)
        if 'fouling' in param_lower:
            if 'fraction' in param_lower:
                return max(0.0, min(1.0, value))
            else:
                return max(0.0, min(10.0, value))
        
        # Efficiency bounds (0-1 for fractions, 0-100 for percentages)
        if 'efficiency' in param_lower:
            if value <= 1.0:  # Fraction
                return max(0.0, min(1.0, value))
            else:  # Percentage
                return max(0.0, min(100.0, value))
        
        # Pressure bounds (0-20 MPa)
        if 'pressure' in param_lower:
            return max(0.0, min(20.0, value))
        
        # Flow bounds (0-10000 kg/s)
        if 'flow' in param_lower:
            return max(0.0, min(10000.0, value))
        
        # Default: ensure positive and reasonable relative to threshold
        if value < 0:
            return max(0.0, threshold * 0.1)  # 10% of threshold as minimum
        elif value > threshold * 10:
            return threshold * 2.0  # Cap at 2x threshold
        
        return value
    
    def generate_conditions_for_multiple_actions(self, actions: List[str],
                                               target_trigger_time_hours: float = 1.0) -> Dict[str, Dict[str, float]]:
        """
        Generate initial conditions for multiple actions
        
        Args:
            actions: List of maintenance actions
            target_trigger_time_hours: Target trigger time for all actions
            
        Returns:
            Dictionary mapping action names to initial conditions
        """
        all_conditions = {}
        
        for action in actions:
            try:
                conditions = self.generate_conditions_for_action(action, target_trigger_time_hours)
                all_conditions[action] = conditions
            except Exception as e:
                warnings.warn(f"Failed to generate conditions for {action}: {e}")
                all_conditions[action] = {}
        
        return all_conditions
    
    def validate_conditions(self, conditions: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate that generated conditions are reasonable
        
        Args:
            conditions: Generated initial conditions
            
        Returns:
            Validation report
        """
        validation_report = {
            'total_conditions': len(conditions),
            'valid_conditions': 0,
            'invalid_conditions': 0,
            'warnings': [],
            'errors': []
        }
        
        for param_name, value in conditions.items():
            try:
                # Check if value is numeric
                if not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
                    validation_report['errors'].append(f"{param_name}: Invalid numeric value {value}")
                    validation_report['invalid_conditions'] += 1
                    continue
                
                # Check if value is reasonable
                if value < 0:
                    validation_report['warnings'].append(f"{param_name}: Negative value {value}")
                
                # Check if value is extremely large
                if abs(value) > 1e6:
                    validation_report['warnings'].append(f"{param_name}: Very large value {value}")
                
                validation_report['valid_conditions'] += 1
                
            except Exception as e:
                validation_report['errors'].append(f"{param_name}: Validation error - {e}")
                validation_report['invalid_conditions'] += 1
        
        return validation_report
    
    def optimize_conditions_for_timing(self, target_action: str, 
                                     desired_trigger_time_hours: float,
                                     tolerance_hours: float = 0.1) -> Dict[str, float]:
        """
        Optimize initial conditions to achieve specific trigger timing
        
        Args:
            target_action: Maintenance action to target
            desired_trigger_time_hours: Desired trigger time
            tolerance_hours: Acceptable timing tolerance
            
        Returns:
            Optimized initial conditions
        """
        # Start with basic conditions
        conditions = self.generate_conditions_for_action(target_action, desired_trigger_time_hours)
        
        # For now, return basic conditions
        # Future enhancement: iterative optimization based on simulation results
        return conditions
    
    def get_conditions_summary(self, conditions: Dict[str, float]) -> str:
        """
        Get human-readable summary of initial conditions
        
        Args:
            conditions: Initial conditions dictionary
            
        Returns:
            Summary string
        """
        if not conditions:
            return "No initial conditions generated"
        
        summary_lines = [f"Generated {len(conditions)} initial conditions:"]
        
        for param_name, value in conditions.items():
            summary_lines.append(f"  {param_name}: {value:.3f}")
        
        return "\n".join(summary_lines)
