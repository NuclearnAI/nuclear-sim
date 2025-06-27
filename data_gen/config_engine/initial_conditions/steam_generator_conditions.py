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
        "tsp_fouling_thicknesses": [0.049, 0.048, 0.0485],  # Very close to 5% (0.05) threshold
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
        "sg_temperatures": [315.0, 318.0, 316.0],  # °C, near 320°C threshold
        "tube_wall_temperature": [325.0, 328.0, 322.0],  # °C, elevated
        "description": "Scale buildup affecting heat transfer and temperatures"
    },
    
    "secondary_side_cleaning": {
        "sg_steam_qualities": [0.992, 0.990, 0.994],  # Fraction, below 99.5% threshold
        "description": "Secondary side contamination requiring cleaning"
    },
    
    # === MOISTURE SEPARATION ACTIONS ===
    
    "moisture_separator_maintenance": {
        "sg_steam_qualities": [0.994, 0.993, 0.9935],  # Near 99.5% threshold
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
