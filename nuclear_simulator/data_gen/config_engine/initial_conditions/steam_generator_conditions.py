"""
Steam Generator System Initial Conditions

This module defines initial conditions for triggering steam generator system
maintenance actions through natural system degradation.

All conditions are set to realistic values that will naturally cross
maintenance thresholds during simulation operation.
"""

from typing import Dict, Any

# Steam generator system initial conditions for maintenance action triggering
# STANDARDIZED VERSION - Only parameters that exist in config.py and YAML
STEAM_GENERATOR_CONDITIONS: Dict[str, Dict[str, Any]] = {
    
    # === TSP (TUBE SUPPORT PLATE) ACTIONS ===
    
    "tsp_chemical_cleaning": {
        "tsp_fouling_thicknesses": [15.49, 18.48, 5.485], 
        "description": "TSP fouling near threshold requiring chemical cleaning",
        "threshold_info": {"parameter": "tsp_fouling_thicknesses", "threshold": 0.05, "direction": "greater_than"},
        "safety_notes": "Fouling set just below threshold to trigger during operation"
    },
    
    "tsp_mechanical_cleaning": {
        "tsp_fouling_thicknesses": [0.065, 0.068, 0.062],  # Above chemical cleaning threshold
        "description": "Heavy TSP fouling requiring mechanical cleaning"
    },
    
    # === SCALE AND DEPOSIT ACTIONS ===
    
    "scale_removal": {
        "scale_thicknesses": [0., 1.8, 2.5],  # mm, scale buildup causing high tube wall temps
        "description": "Scale buildup affecting heat transfer and temperatures - tube wall temp calculated from scale",
        "threshold_info": {"parameter": "scale_thicknesses", "threshold": 0.5, "direction": "greater_than"},
        "safety_notes": "Scale thickness set to cause tube wall temps >320°C - tube wall temp is calculated from thermal resistance"
    },
    
    "secondary_side_cleaning": {
        "sg_steam_qualities": [0.992, 0.990, 0.994],  # Fraction, below 99.5% threshold
        "description": "Secondary side contamination requiring cleaning"
    },
    
    # === MOISTURE SEPARATION ACTIONS ===
    
    "moisture_separator_maintenance": {
        "sg_steam_qualities": [0.84, 0.83, 0.85],  # Near 99.5% threshold
        # TODO: Revisit - removed non-standard parameters: moisture_separator_efficiency, steam_dryer_pressure_drop, carryover_solids
        "description": "Steam quality parameters requiring moisture separator maintenance"
    },
    
    "steam_dryer_cleaning": {
        # TODO: Revisit - removed non-standard parameters: steam_dryer_fouling, steam_dryer_pressure_drop, steam_purity, dryer_vane_deposits
        "description": "Steam dryer fouling requiring cleaning"
    },
    
    # === TUBE BUNDLE ACTIONS ===
    
    "tube_bundle_inspection": {
        # TODO: Revisit - removed non-standard parameters: tube_vibration, tube_wall_thinning, tube_support_wear, flow_induced_vibration
        "description": "Tube bundle parameters requiring inspection"
    },
    
    "eddy_current_testing": {
        # TODO: Revisit - removed non-standard parameters: tube_wall_thickness, tube_defect_indications, tube_integrity_margin, previous_inspection_growth
        "description": "Tube condition requiring eddy current testing"
    },
    
    "tube_sheet_inspection": {
        # TODO: Revisit - removed non-standard parameters: tube_sheet_corrosion, tube_to_tubesheet_joint, crevice_corrosion, tube_sheet_stress
        "description": "Tube sheet condition requiring inspection"
    },
    
    # === WATER CHEMISTRY ACTIONS ===
    
    "water_chemistry_adjustment": {
        # TODO: Revisit - removed non-standard parameters: secondary_water_ph, chloride_concentration, sulfate_concentration, dissolved_oxygen, conductivity
        "description": "Water chemistry parameters requiring adjustment"
    },
    
    # === HEAT TRANSFER ACTIONS ===
    
    "heat_exchanger_cleaning": {
        "tsp_heat_transfer_degradations": [0.18, 0.20, 0.16],  # Heat transfer degradation from fouling
        # TODO: Revisit - removed non-standard parameters: overall_heat_transfer, fouling_resistance, temperature_approach, heat_flux
        "description": "Heat transfer degradation requiring cleaning"
    },
    
    # === STEAM QUALITY AND PERFORMANCE ===
    
    "steam_quality_improvement": {
        "sg_steam_qualities": [0.992, 0.985, 0.991],  # Steam quality below optimal
        # TODO: Revisit - removed non-standard parameters: steam_moisture_content, steam_carryover, steam_purity, separator_efficiency
        "description": "Steam quality parameters requiring improvement"
    },
    
    # === FLOW AND CIRCULATION ===
    
    "circulation_system_check": {
        "sg_steam_flows": [485.0, 483.0, 487.0],  # kg/s, slightly below design
        "sg_feedwater_flows": [485.0, 483.0, 487.0],  # kg/s, matching steam flows
        "primary_flow_rates": [5650.0, 5630.0, 5670.0],  # kg/s, slightly reduced
        # TODO: Revisit - removed non-standard parameters: natural_circulation_flow, downcomer_flow, riser_flow_distribution, circulation_ratio
        "description": "Circulation parameters requiring check"
    },
    
    # === STRUCTURAL AND MECHANICAL ===
    
    "structural_inspection": {
        # TODO: Revisit - removed non-standard parameters: thermal_stress, thermal_fatigue_cycles, support_structure_deflection, vessel_expansion
        "description": "Structural parameters requiring inspection"
    },
    
    "tube_plugging": {
        # TODO: Revisit - removed non-standard parameters: defective_tube_count, tube_leak_rate, plugged_tube_percentage, remaining_heat_transfer
        "description": "Tube condition requiring plugging"
    },
    
    # === BLOWDOWN AND CHEMISTRY CONTROL ===
    
    "blowdown_system_check": {
        # TODO: Revisit - removed non-standard parameters: blowdown_rate, blowdown_heat_recovery, blowdown_valve_position, continuous_blowdown
        "description": "Blowdown system parameters requiring check"
    },
    
    # === LEVEL CONTROL ACTIONS ===
    
    "level_control_check": {
        "sg_levels": [12.3, 12.2, 12.4],  # m, slightly below setpoint
        "sg_feedwater_flows": [495.0, 505.0, 490.0],  # kg/s, variable flows
        # TODO: Revisit - removed non-standard parameters: water_level_stability, level_control_response, feedwater_flow_variation, steam_flow_variation
        "description": "Level control parameters requiring check"
    },
    
    # === PRESSURE CONTROL ===
    
    "pressure_control_check": {
        "sg_pressures": [6.85, 6.82, 6.88],  # MPa, variable pressures
        # TODO: Revisit - removed non-standard parameters: steam_pressure_stability, pressure_control_response, steam_header_pressure, pressure_relief_margin
        "description": "Pressure control parameters requiring check"
    },
    
    # === FEEDWATER SYSTEM INTERFACE ===
    
    "feedwater_system_check": {
        "sg_feedwater_flows": [485.0, 483.0, 487.0],  # kg/s, uneven distribution
        # TODO: Revisit - removed non-standard parameters: feedwater_temperature, feedwater_flow_distribution, feedwater_chemistry, economizer_performance
        "description": "Feedwater system interface parameters requiring check"
    },
    
    # === STEAM SYSTEM INTERFACE ===
    
    "steam_system_check": {
        "sg_steam_flows": [488.0, 486.0, 490.0],  # kg/s, uneven distribution
        "sg_temperatures": [285.0, 287.0, 283.0],  # °C, temperature variation
        # TODO: Revisit - removed non-standard parameters: steam_flow_distribution, steam_pressure_balance, main_steam_isolation
        "description": "Steam system interface parameters requiring check"
    },
    
    # === INSTRUMENTATION AND CONTROL ===
    
    "instrumentation_calibration": {
        # TODO: Revisit - removed non-standard parameters: level_instrument_drift, pressure_instrument_drift, temperature_instrument_drift, flow_instrument_drift
        "description": "Instrumentation drift requiring calibration"
    },
    
    # === PERFORMANCE MONITORING ===
    
    "performance_test": {
        "sg_steam_flows": [492.0, 490.0, 494.0],  # kg/s, slightly below design
        "tsp_heat_transfer_degradations": [0.12, 0.10, 0.14],  # Heat transfer effectiveness reduction
        # TODO: Revisit - removed non-standard parameters: thermal_efficiency, steam_generation_rate, heat_transfer_effectiveness, overall_performance_index
        "description": "Performance parameters requiring testing"
    },
    
    # === MAINTENANCE PLANNING ===
    
    "maintenance_planning": {
        # TODO: Revisit - removed non-standard parameters: component_condition_index, maintenance_backlog, reliability_index, availability_target
        "description": "Maintenance planning parameters"
    }
}


# === RANDOMIZATION SUPPORT ===

from typing import Optional
from .randomization_utils import add_randomness_to_conditions, validate_safety_limits

def get_randomized_sg_conditions(
    action: str,
    seed: Optional[int] = None,
    scaling_factor: float = 0.1
) -> Dict[str, Any]:
    """
    Get randomized conditions for a specific steam generator action
    
    This function is called by the initial conditions catalog to provide
    randomized variants that interface with ComprehensiveComposer.
    
    Args:
        action: Steam generator action name
        seed: Random seed for reproducibility
        scaling_factor: Scaling factor for randomization
    
    Returns:
        Randomized conditions dictionary
    """
    if action not in STEAM_GENERATOR_CONDITIONS:
        raise ValueError(f"Unknown steam generator action: {action}")
    
    base_conditions = STEAM_GENERATOR_CONDITIONS[action]
    
    # Steam generator-specific safety-aware rules
    sg_rules = {
        # MAINTENANCE TARGETS (we want to hit these)
        "tsp_fouling_thicknesses": {
            "scale_factor": 0.08,
            "min_value": 0.04,
            "max_value": 0.07,
            "target_threshold": 0.05,  # 5% fouling threshold
            "threshold_type": "maintenance",
            "array_handling": "individual"
        },
        "sg_steam_qualities": {
            "scale_factor": 0.02,
            "min_value": 0.985,
            "max_value": 1.0,
            "target_threshold": 0.995,  # 99.5% quality threshold
            "threshold_type": "maintenance",
            "array_handling": "individual"
        },
        "tsp_heat_transfer_degradations": {
            "scale_factor": 0.10,
            "min_value": 0.05,
            "max_value": 0.25,
            "target_threshold": 0.15,  # 15% degradation threshold
            "threshold_type": "maintenance",
            "array_handling": "individual"
        },
        
        # OPERATIONAL PARAMETERS (moderate scaling)
        "scale_thicknesses": {
            "scale_factor": 0.15,
            "min_value": 0.0,
            "max_value": 2.0,  # Keep well below levels that cause >305°C tube wall
            "threshold_type": "operational",
            "array_handling": "individual"
        },
        "sg_steam_flows": {
            "scale_factor": 0.05,
            "min_value": 400.0,
            "max_value": 520.0,  # Reasonable operational range
            "threshold_type": "operational",
            "array_handling": "individual"
        },
        "sg_feedwater_flows": {
            "scale_factor": 0.05,
            "min_value": 400.0,
            "max_value": 520.0,  # Reasonable operational range
            "threshold_type": "operational",
            "array_handling": "individual"
        },
        "sg_pressures": {
            "scale_factor": 0.03,
            "min_value": 6.5,
            "max_value": 7.2,  # Reasonable pressure range
            "threshold_type": "operational",
            "array_handling": "individual"
        },
        "sg_temperatures": {
            "scale_factor": 0.03,
            "min_value": 280.0,
            "max_value": 290.0,  # Reasonable temperature range
            "threshold_type": "operational",
            "array_handling": "individual"
        },
        "sg_levels": {
            "scale_factor": 0.05,
            "min_value": 10.0,
            "max_value": 15.0,  # Reasonable level range
            "threshold_type": "operational",
            "array_handling": "individual"
        },
        "primary_flow_rates": {
            "scale_factor": 0.05,
            "min_value": 5000.0,
            "max_value": 6000.0,  # Reasonable primary flow range
            "threshold_type": "operational",
            "array_handling": "individual"
        }
    }
    
    randomized = add_randomness_to_conditions(
        base_conditions,
        sg_rules,
        scaling_factor,
        seed
    )
    
    # Validate safety (steam generators have fewer hard safety trips)
    violations = validate_safety_limits(randomized, sg_rules)
    if violations["errors"]:
        raise ValueError(f"Safety violations in randomized conditions: {violations['errors']}")
    
    return randomized

# Convenience functions for common scenarios
def create_randomized_sg_scenario(action: str, num_variants: int = 5, base_seed: int = 42):
    """Create multiple randomized variants of a steam generator scenario"""
    variants = {}
    for i in range(num_variants):
        seed = base_seed + i
        randomized = get_randomized_sg_conditions(action, seed)
        variants[f"{action}_variant_{i+1}"] = randomized
    return variants

def get_randomized_tsp_cleaning_conditions(seed: int = None):
    """Get randomized TSP chemical cleaning scenario"""
    return get_randomized_sg_conditions("tsp_chemical_cleaning", seed)

def get_randomized_steam_quality_conditions(seed: int = None):
    """Get randomized steam quality improvement scenario"""
    return get_randomized_sg_conditions("steam_quality_improvement", seed)

def get_randomized_scale_removal_conditions(seed: int = None):
    """Get randomized scale removal scenario"""
    return get_randomized_sg_conditions("scale_removal", seed)
