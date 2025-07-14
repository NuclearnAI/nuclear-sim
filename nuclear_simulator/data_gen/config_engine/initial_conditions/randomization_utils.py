"""
Randomization utilities for initial conditions

This module provides the core randomization functionality with safety-aware
parameter scaling that distinguishes between safety trips and maintenance thresholds.
"""

import random
import numpy as np
from typing import Dict, Any, Optional, List
import copy

def add_randomness_to_conditions(
    conditions_dict: Dict[str, Any],
    parameter_rules: Optional[Dict[str, Dict]] = None,
    scaling_factor: float = 0.1,
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add controlled randomness to condition parameters
    
    Args:
        conditions_dict: Original conditions dictionary
        parameter_rules: Parameter-specific scaling rules
        scaling_factor: Default scaling factor
        seed: Random seed for reproducibility
    
    Returns:
        Randomized conditions dictionary
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    
    if parameter_rules is None:
        parameter_rules = get_default_parameter_rules()
    
    # Deep copy to avoid modifying original
    randomized = copy.deepcopy(conditions_dict)
    
    # Apply randomization recursively
    _randomize_recursive(randomized, parameter_rules, scaling_factor)
    
    return randomized

def _randomize_recursive(obj: Any, rules: Dict[str, Dict], default_scale: float):
    """Recursively apply randomization to nested dictionaries"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in rules:
                # Apply specific rule for this parameter
                obj[key] = _apply_parameter_rule(value, rules[key])
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                # Apply default scaling to numeric values
                obj[key] = _apply_default_scaling(value, default_scale)
            elif isinstance(value, list):
                # Handle arrays
                obj[key] = _randomize_array(value, rules.get(key, {}), default_scale)
            else:
                # Recurse into nested dictionaries
                _randomize_recursive(value, rules, default_scale)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _randomize_recursive(item, rules, default_scale)

def _apply_parameter_rule(value: Any, rule: Dict[str, Any]) -> Any:
    """Apply specific parameter rule"""
    if isinstance(value, list):
        return [_apply_single_rule(v, rule) for v in value]
    else:
        return _apply_single_rule(value, rule)

def _apply_single_rule(value: float, rule: Dict[str, Any]) -> float:
    """Apply rule to single numeric value"""
    scale_factor = rule.get('scale_factor', 0.1)
    min_value = rule.get('min_value', None)
    max_value = rule.get('max_value', None)
    
    # Apply random scaling
    variation = np.random.uniform(-scale_factor, scale_factor)
    new_value = value * (1.0 + variation)
    
    # Apply bounds
    if min_value is not None:
        new_value = max(new_value, min_value)
    if max_value is not None:
        new_value = min(new_value, max_value)
    
    return new_value

def _apply_default_scaling(value: float, scale_factor: float) -> float:
    """Apply default scaling to numeric value"""
    variation = np.random.uniform(-scale_factor, scale_factor)
    return value * (1.0 + variation)

def _randomize_array(arr: List[Any], rule: Dict[str, Any], default_scale: float) -> List[Any]:
    """Randomize array values"""
    if not arr or not isinstance(arr[0], (int, float)):
        return arr
    
    array_handling = rule.get('array_handling', 'individual')
    
    if array_handling == 'individual':
        # Each element varies independently
        return [_apply_single_rule(v, rule) if rule else _apply_default_scaling(v, default_scale) for v in arr]
    elif array_handling == 'correlated':
        # All elements get same scaling factor
        variation = np.random.uniform(-rule.get('scale_factor', default_scale), 
                                    rule.get('scale_factor', default_scale))
        return [v * (1.0 + variation) for v in arr]
    elif array_handling == 'preserve_pattern':
        # Maintain relative relationships
        if len(arr) > 1:
            # Find the dominant element
            max_idx = arr.index(max(arr))
            # Scale all elements but preserve pattern
            scale = np.random.uniform(0.8, 1.2)
            return [v * scale for v in arr]
        else:
            return [_apply_single_rule(arr[0], rule) if rule else _apply_default_scaling(arr[0], default_scale)]
    
    return arr

def get_default_parameter_rules() -> Dict[str, Dict]:
    """Get default parameter rules with safety vs maintenance distinction"""
    return {
        # === MAINTENANCE PARAMETERS (we want to trigger these) ===
        "pump_oil_contamination": {
            "scale_factor": 0.05,
            "min_value": 12.0,
            "max_value": 18.0,
            "target_threshold": 15.2,
            "threshold_type": "maintenance"
        },
        "oil_contamination_level": {
            "scale_factor": 0.05,
            "min_value": 12.0,
            "max_value": 18.0,
            "target_threshold": 15.0,
            "threshold_type": "maintenance"
        },
        "oil_level": {
            "scale_factor": 0.08,
            "min_value": 55.0,
            "max_value": 75.0,
            "target_threshold": 60.0,
            "threshold_type": "maintenance"
        },
        "oil_reservoir_level": {
            "scale_factor": 0.08,
            "min_value": 65.0,
            "max_value": 85.0,
            "target_threshold": 70.0,
            "threshold_type": "maintenance"
        },
        
        # === SAFETY PARAMETERS (never exceed these) ===
        "thrust_bearing_displacement": {
            "scale_factor": 0.02,
            "min_value": 10.0,
            "max_value": 45.0,  # 5mm safety margin below 50mm TRIP
            "safety_limit": 50.0,
            "threshold_type": "safety"
        },
        "rotor_speed": {
            "scale_factor": 0.01,
            "min_value": 3400.0,
            "max_value": 3700.0,  # 80 RPM safety margin below 3780 TRIP
            "safety_limit": 3780.0,
            "threshold_type": "safety"
        },
        "npsh_available": {
            "scale_factor": 0.03,
            "min_value": 13.0,  # 1m above 12m CRITICAL TRIP
            "max_value": 25.0,
            "safety_limit": 12.0,
            "threshold_type": "safety",
            "safety_direction": "less_than"  # NPSH below 12m is dangerous
        },
        "motor_temperature": {
            "scale_factor": 0.08,
            "min_value": 60.0,
            "max_value": 115.0,  # 15°C safety margin below 130°C TRIP
            "safety_limit": 130.0,
            "threshold_type": "safety",
            "array_handling": "individual"
        },
        "bearing_temperatures": {
            "scale_factor": 0.10,
            "min_value": 60.0,
            "max_value": 110.0,  # 10°C safety margin below 120°C TRIP
            "safety_limit": 120.0,
            "threshold_type": "safety",
            "array_handling": "individual"
        },
        "pump_vibrations": {
            "scale_factor": 0.10,
            "min_value": 0.0,
            "max_value": 22.0,  # 3 mm/s safety margin below 25 TRIP
            "safety_limit": 25.0,
            "threshold_type": "safety",
            "array_handling": "preserve_pattern"
        },
        "bearing_vibrations": {
            "scale_factor": 0.08,
            "min_value": 0.0,
            "max_value": 22.0,  # 3 mils safety margin below 25 TRIP
            "safety_limit": 25.0,
            "threshold_type": "safety",
            "array_handling": "individual"
        }
    }

def validate_safety_limits(conditions: Dict[str, Any], 
                          rules: Optional[Dict[str, Dict]] = None) -> Dict[str, List[str]]:
    """
    Validate that conditions don't violate safety limits
    
    Returns:
        Dictionary with violations: {"errors": [...], "warnings": [...]}
    """
    if rules is None:
        rules = get_default_parameter_rules()
    
    violations = {"errors": [], "warnings": []}
    
    def check_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if key in rules and rules[key].get("threshold_type") == "safety":
                    safety_limit = rules[key].get("safety_limit")
                    safety_direction = rules[key].get("safety_direction", "greater_than")
                    if safety_limit is not None:
                        if isinstance(value, list):
                            for i, v in enumerate(value):
                                if isinstance(v, (int, float)):
                                    if safety_direction == "less_than" and v < safety_limit:
                                        violations["errors"].append(
                                            f"{current_path}[{i}] = {v} below safety limit {safety_limit}"
                                        )
                                    elif safety_direction == "greater_than" and v > safety_limit:
                                        violations["errors"].append(
                                            f"{current_path}[{i}] = {v} exceeds safety limit {safety_limit}"
                                        )
                        elif isinstance(value, (int, float)):
                            if safety_direction == "less_than" and value < safety_limit:
                                violations["errors"].append(
                                    f"{current_path} = {value} below safety limit {safety_limit}"
                                )
                            elif safety_direction == "greater_than" and value > safety_limit:
                                violations["errors"].append(
                                    f"{current_path} = {value} exceeds safety limit {safety_limit}"
                                )
                else:
                    check_recursive(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_recursive(item, f"{path}[{i}]")
    
    check_recursive(conditions)
    return violations
