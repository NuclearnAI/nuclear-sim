"""
Randomization utilities for initial conditions

This module provides the core randomization functionality with safety-aware
parameter scaling that distinguishes between safety trips and maintenance thresholds.
"""

import random
import numpy as np
from typing import Dict, Any, Optional, List, Union
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


# === SCENARIO-BASED RANDOMIZATION SYSTEM ===

# Scenario definitions for physics-aware randomization - OPTIMIZED FOR 12-HOUR TIMEFRAME
ACTION_SCENARIOS = {
    "motor_bearing_replacement": [
        {
            "name": "critical_wear",
            "probability": 0.5,
            "description": "Very high wear with high stress - almost certain 12hr trigger (targets 8.5 threshold)",
            "parameters": {
                "motor_bearing_wear": {"range": [8.45, 8.49], "distribution": "uniform"},
                "motor_temperature": {"range": [100, 115], "distribution": "normal"},
                "pump_oil_contamination": {"range": [15.0, 15.15], "distribution": "uniform"},
                "oil_temperature": {"range": [58, 65], "distribution": "normal"}
            }
        },
        {
            "name": "high_stress",
            "probability": 0.35,
            "description": "High wear with very high stress conditions (targets 8.5 threshold)",
            "parameters": {
                "motor_bearing_wear": {"range": [8.3, 8.4], "distribution": "uniform"},
                "motor_temperature": {"range": [105, 120], "distribution": "normal"},
                "pump_oil_contamination": {"range": [15.1, 15.18], "distribution": "uniform"},
                "oil_temperature": {"range": [60, 68], "distribution": "normal"}
            }
        },
        {
            "name": "stable_operation",
            "probability": 0.15,
            "description": "Moderate wear with elevated conditions - possible trigger (targets 8.5 threshold)",
            "parameters": {
                "motor_bearing_wear": {"range": [8.0, 8.2], "distribution": "uniform"},
                "motor_temperature": {"range": [90, 100], "distribution": "normal"},
                "pump_oil_contamination": {"range": [14.8, 15.0], "distribution": "uniform"},
                "oil_temperature": {"range": [55, 60], "distribution": "normal"}
            }
        }
    ],
    
    "pump_bearing_replacement": [
        {
            "name": "high_cavitation_physics",
            "probability": 0.5,
            "description": "Physics-driven high cavitation with compound acceleration - 11hr trigger via physics",
            "parameters": {
                "pump_bearing_wear": {"range": [6.2, 6.3], "distribution": "uniform"},  # Start 0.2-0.3% below threshold
                "cavitation_intensity": {"range": [0.25, 0.35], "distribution": "uniform"},  # 2.5-2.7x acceleration
                "impeller_wear": {"range": [3.0, 5.0], "distribution": "uniform"},  # 1.12-1.2x coupling acceleration
                "npsh_available": {"range": [16.0, 17.5], "distribution": "uniform"},  # SAFE: above 15.0m trip
                "oil_temperature": {"range": [60, 70], "distribution": "normal"},  # 1.3-1.7x temperature acceleration
                "motor_temperature": {"range": [80, 90], "distribution": "normal"},  # Supporting elevated conditions
                "pump_vibrations": {"range": [12.0, 18.0], "distribution": "normal"}  # Higher hydraulic loads
            }
        },
        {
            "name": "moderate_cavitation_physics",
            "probability": 0.35,
            "description": "Physics-driven moderate cavitation with coupling effects - 8hr trigger via physics",
            "parameters": {
                "pump_bearing_wear": {"range": [6.25, 6.35], "distribution": "uniform"},  # Start 0.15-0.25% below threshold
                "cavitation_intensity": {"range": [0.18, 0.28], "distribution": "uniform"},  # 2.18-2.28x acceleration
                "impeller_wear": {"range": [2.0, 4.0], "distribution": "uniform"},  # 1.08-1.16x coupling acceleration
                "npsh_available": {"range": [16.5, 18.0], "distribution": "uniform"},  # SAFE: above 15.0m trip
                "oil_temperature": {"range": [55, 65], "distribution": "normal"},  # 1.17-1.5x temperature acceleration
                "motor_temperature": {"range": [75, 85], "distribution": "normal"},  # Supporting elevated conditions
                "pump_vibrations": {"range": [10.0, 15.0], "distribution": "normal"}  # Moderate hydraulic loads
            }
        },
        {
            "name": "low_cavitation_physics",
            "probability": 0.15,
            "description": "Physics-driven low cavitation with temperature effects - 6hr trigger via physics",
            "parameters": {
                "pump_bearing_wear": {"range": [6.3, 6.4], "distribution": "uniform"},  # Start 0.1-0.2% below threshold
                "cavitation_intensity": {"range": [0.12, 0.18], "distribution": "uniform"},  # 2.12-2.18x acceleration
                "impeller_wear": {"range": [1.0, 3.0], "distribution": "uniform"},  # 1.04-1.12x coupling acceleration
                "npsh_available": {"range": [17.0, 18.5], "distribution": "uniform"},  # SAFE: above 15.0m trip
                "oil_temperature": {"range": [50, 60], "distribution": "normal"},  # 1.0-1.33x temperature acceleration
                "motor_temperature": {"range": [70, 80], "distribution": "normal"},  # Supporting elevated conditions
                "pump_vibrations": {"range": [8.0, 12.0], "distribution": "normal"}  # Lower hydraulic loads
            }
        }
    ],
    
    "oil_change": [
        {
            "name": "critical_contamination",
            "probability": 0.5,
            "description": "Very high contamination - almost certain 12hr trigger (targets 15.2 threshold)",
            "parameters": {
                "pump_oil_contamination": {"range": [15.18, 15.195], "distribution": "uniform"},
                "oil_temperature": {"range": [65, 75], "distribution": "normal"},
                "pump_oil_water_content": {"range": [0.085, 0.095], "distribution": "uniform"},
                "pump_oil_acid_number": {"range": [1.5, 1.58], "distribution": "normal"}
            }
        },
        {
            "name": "accelerated_degradation",
            "probability": 0.35,
            "description": "Accelerated oil degradation conditions (targets 15.2 threshold)",
            "parameters": {
                "pump_oil_contamination": {"range": [15.15, 15.17], "distribution": "uniform"},
                "oil_temperature": {"range": [60, 68], "distribution": "normal"},
                "pump_oil_water_content": {"range": [0.08, 0.09], "distribution": "uniform"},
                "pump_oil_acid_number": {"range": [1.4, 1.5], "distribution": "normal"}
            }
        },
        {
            "name": "good_oil_condition",
            "probability": 0.15,
            "description": "Good oil condition - unlikely trigger (below 15.2 threshold)",
            "parameters": {
                "pump_oil_contamination": {"range": [14.8, 15.0], "distribution": "uniform"},
                "oil_temperature": {"range": [58, 65], "distribution": "normal"},
                "pump_oil_water_content": {"range": [0.075, 0.08], "distribution": "uniform"},
                "pump_oil_acid_number": {"range": [1.3, 1.4], "distribution": "normal"}
            }
        }
    ],
    
    "thrust_bearing_replacement": [
        {
            "name": "high_axial_load",
            "probability": 0.6,
            "description": "Very high axial load - almost certain 12hr trigger (targets 4.5 threshold)",
            "parameters": {
                "thrust_bearing_wear": {"range": [4.45, 4.49], "distribution": "uniform"},
                "pump_vibrations": {"range": [18.0, 22.0], "distribution": "normal"},
                "cavitation_intensity": {"range": [0.18, 0.25], "distribution": "uniform"}
            }
        },
        {
            "name": "medium_load_high_speed",
            "probability": 0.25,
            "description": "High wear with very high axial stress (targets 4.5 threshold)",
            "parameters": {
                "thrust_bearing_wear": {"range": [4.4, 4.45], "distribution": "uniform"},
                "pump_vibrations": {"range": [15.0, 20.0], "distribution": "normal"},
                "cavitation_intensity": {"range": [0.15, 0.2], "distribution": "uniform"}
            }
        },
        {
            "name": "normal_thrust_conditions",
            "probability": 0.15,
            "description": "Elevated thrust conditions - possible trigger (targets 4.5 threshold)",
            "parameters": {
                "thrust_bearing_wear": {"range": [4.3, 4.4], "distribution": "uniform"},
                "pump_vibrations": {"range": [12.0, 16.0], "distribution": "normal"},
                "cavitation_intensity": {"range": [0.1, 0.15], "distribution": "uniform"}
            }
        }
    ],
    
    "seal_replacement": [
        {
            "name": "critical_seal_physics",
            "probability": 0.5,
            "description": "Physics-driven critical seal wear with cavitation acceleration - 6hr trigger via physics",
            "parameters": {
                "seal_face_wear": {"range": [15.7, 15.9], "distribution": "uniform"},  # Start 0.1-0.3% below 16.0% threshold
                "cavitation_intensity": {"range": [0.15, 0.25], "distribution": "uniform"},  # 5x seal acceleration from cavitation
                "oil_temperature": {"range": [60, 70], "distribution": "normal"},  # Heat degrades seal materials
                "pump_oil_contamination": {"range": [13.0, 14.0], "distribution": "uniform"},  # Contamination damages seal faces
                "pump_oil_water_content": {"range": [0.07, 0.075], "distribution": "uniform"},  # Moisture damages seals
                "motor_temperature": {"range": [75, 85], "distribution": "normal"},  # Supporting elevated conditions
                "pump_vibrations": {"range": [10.0, 15.0], "distribution": "normal"}  # Vibration affects seal alignment
            }
        },
        {
            "name": "moderate_seal_physics",
            "probability": 0.35,
            "description": "Physics-driven moderate seal wear with pressure effects - 8hr trigger via physics",
            "parameters": {
                "seal_face_wear": {"range": [15.5, 15.7], "distribution": "uniform"},  # Start 0.3-0.5% below 16.0% threshold
                "cavitation_intensity": {"range": [0.10, 0.20], "distribution": "uniform"},  # 4x seal acceleration from cavitation
                "oil_temperature": {"range": [55, 65], "distribution": "normal"},  # Moderate heat effects
                "pump_oil_contamination": {"range": [12.0, 13.5], "distribution": "uniform"},  # Moderate contamination
                "pump_oil_water_content": {"range": [0.06, 0.07], "distribution": "uniform"},  # Moderate moisture
                "motor_temperature": {"range": [70, 80], "distribution": "normal"},  # Supporting elevated conditions
                "pump_vibrations": {"range": [8.0, 12.0], "distribution": "normal"}  # Moderate vibration
            }
        },
        {
            "name": "low_seal_physics",
            "probability": 0.15,
            "description": "Physics-driven low seal wear with chemistry effects - 10hr trigger via physics",
            "parameters": {
                "seal_face_wear": {"range": [15.3, 15.5], "distribution": "uniform"},  # Start 0.5-0.7% below 16.0% threshold
                "cavitation_intensity": {"range": [0.05, 0.15], "distribution": "uniform"},  # 3x seal acceleration from cavitation
                "oil_temperature": {"range": [50, 60], "distribution": "normal"},  # Lower heat effects
                "pump_oil_contamination": {"range": [11.0, 12.5], "distribution": "uniform"},  # Lower contamination
                "pump_oil_water_content": {"range": [0.055, 0.065], "distribution": "uniform"},  # Lower moisture
                "motor_temperature": {"range": [65, 75], "distribution": "normal"},  # Supporting elevated conditions
                "pump_vibrations": {"range": [6.0, 10.0], "distribution": "normal"}  # Lower vibration
            }
        }
    ],
    
    "oil_top_off": [
        {
            "name": "low_oil_level",
            "probability": 0.3,
            "description": "Low oil level - high trigger probability",
            "parameters": {
                "pump_oil_levels": {"range": [59.2, 59.6], "distribution": "uniform", "array_handling": "preserve_pattern"}
            }
        },
        {
            "name": "moderate_oil_loss",
            "probability": 0.4,
            "description": "Moderate oil loss rate",
            "parameters": {
                "pump_oil_levels": {"range": [60.8, 61.2], "distribution": "uniform", "array_handling": "preserve_pattern"}
            }
        },
        {
            "name": "stable_oil_level",
            "probability": 0.3,
            "description": "Stable oil level - unlikely trigger",
            "parameters": {
                "pump_oil_levels": {"range": [61.5, 63.0], "distribution": "uniform", "array_handling": "preserve_pattern"}
            }
        }
    ]
}


def get_scenario_based_conditions(action: str, base_conditions: Dict, seed: Optional[int] = None) -> Dict:
    """
    Generate randomized conditions using scenario-based approach
    
    Args:
        action: Action name to generate scenario for
        base_conditions: Base conditions dictionary
        seed: Random seed for reproducibility
    
    Returns:
        Randomized conditions dictionary with physics-consistent parameters
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    
    # Get scenarios for this action
    scenarios = ACTION_SCENARIOS.get(action, [])
    if not scenarios:
        # Fallback to original randomization if no scenarios defined
        return add_randomness_to_conditions(base_conditions, seed=seed)
    
    # Select scenario based on probabilities
    scenario = select_weighted_scenario(scenarios)
    
    # Generate randomized values within scenario ranges
    randomized_conditions = copy.deepcopy(base_conditions)
    
    for param_name, param_config in scenario["parameters"].items():
        if param_name in randomized_conditions:
            randomized_conditions[param_name] = generate_scenario_value(param_config)
    
    return randomized_conditions


def select_weighted_scenario(scenarios: List[Dict]) -> Dict:
    """Select scenario based on probability weights"""
    if not scenarios:
        raise ValueError("No scenarios provided")
    
    # Extract probabilities
    probabilities = [scenario.get("probability", 1.0) for scenario in scenarios]
    total_prob = sum(probabilities)
    
    # Normalize probabilities
    normalized_probs = [p / total_prob for p in probabilities]
    
    # Select scenario using weighted random choice
    rand_val = random.random()
    cumulative_prob = 0.0
    
    for i, prob in enumerate(normalized_probs):
        cumulative_prob += prob
        if rand_val <= cumulative_prob:
            return scenarios[i]
    
    # Fallback to last scenario
    return scenarios[-1]


def generate_scenario_value(param_config: Dict) -> Union[float, List[float]]:
    """Generate value within scenario range using specified distribution"""
    range_min, range_max = param_config["range"]
    distribution = param_config.get("distribution", "uniform")
    array_handling = param_config.get("array_handling", None)
    
    if distribution == "uniform":
        value = random.uniform(range_min, range_max)
    elif distribution == "normal":
        # Use range as mean ± 2*std (95% within range)
        mean = (range_min + range_max) / 2
        std = (range_max - range_min) / 4  # 2*std = range
        value = np.random.normal(mean, std)
        # Clamp to range
        value = max(range_min, min(range_max, value))
    else:
        # Default to uniform
        value = random.uniform(range_min, range_max)
    
    # Handle array parameters
    if array_handling == "preserve_pattern":
        # For arrays like pump_oil_levels, apply same scaling to all elements
        # This will be handled by the calling code that knows the original array structure
        return value
    
    return value


def apply_scenario_to_array_parameter(base_array: List[float], scenario_value: float, 
                                    array_handling: str = "preserve_pattern") -> List[float]:
    """Apply scenario value to array parameter with specified handling"""
    if not base_array:
        return base_array
    
    if array_handling == "preserve_pattern":
        # Scale all elements proportionally
        if base_array[0] != 0:
            scale_factor = scenario_value / base_array[0]
            return [val * scale_factor for val in base_array]
        else:
            # If first element is zero, set all to scenario value
            return [scenario_value] + base_array[1:]
    elif array_handling == "first_element_only":
        # Only modify first element
        return [scenario_value] + base_array[1:]
    else:
        # Default: modify all elements to scenario value
        return [scenario_value] * len(base_array)
