"""
Condenser System Initial Conditions

This module defines initial conditions for triggering condenser system
maintenance actions through natural system degradation.

All conditions are set to realistic values that will naturally cross
maintenance thresholds during simulation operation.

CLEANED VERSION - Parameters aligned with CondenserInitialConditions dataclass
"""

from typing import Dict, Any

# Condenser system initial conditions for maintenance action triggering
CONDENSER_CONDITIONS: Dict[str, Dict[str, Any]] = {
    
    # === TUBE CLEANING ACTIONS ===
    
    "condenser_tube_cleaning": {
        "total_fouling_resistance": 0.0009,  # m²K/W, near 0.001 threshold
        "biofouling_thickness": 0.8,  # mm
        "scale_thickness": 0.4,  # mm
        "overall_htc": 2460.0,  # W/m²/K (0.82 × 3000.0 design)
        "thermal_performance_factor": 0.85,  # Thermal performance factor
        "description": "Tube fouling near threshold requiring cleaning",
        "threshold_info": {"parameter": "total_fouling_resistance", "threshold": 0.001, "direction": "greater_than"}
    },
    
    "condenser_biofouling_removal": {
        "biofouling_thickness": 1.2,  # mm, heavy biological growth
        "description": "Heavy biofouling requiring removal"
    },
    
    "condenser_scale_removal": {
        "scale_thickness": 0.8,  # mm mineral scale
        "description": "Mineral scale requiring removal"
    },
    
    "condenser_chemical_cleaning": {
        "corrosion_thickness": 0.6,  # mm corrosion product thickness
        "description": "Chemical deposits requiring cleaning"
    },
    
    "condenser_mechanical_cleaning": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Hard deposits requiring mechanical cleaning"
    },
    
    "condenser_hydroblast_cleaning": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Stubborn deposits requiring high-pressure cleaning"
    },
    
    # === TUBE INSPECTION AND PLUGGING ===
    
    "condenser_tube_inspection": {
        "average_wall_thickness": 0.00127,  # m (0.18mm loss from 0.00159m initial)
        "description": "Tube condition requiring inspection"
    },
    
    "condenser_tube_plugging": {
        "tube_leak_rate": 0.008,  # kg/s, near 0.01 threshold
        "plugged_tube_count": 75,  # Already plugged tubes
        "active_tube_count": 83925,  # 84000 - 75 plugged
        "description": "Tube leakage requiring plugging",
        "threshold_info": {"parameter": "tube_leak_rate", "threshold": 0.01, "direction": "greater_than"}
    },
    
    # === VACUUM SYSTEM ACTIONS ===
    
    "vacuum_ejector_cleaning": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Ejector fouling requiring cleaning"
    },
    
    "vacuum_ejector_nozzle_replacement": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Nozzle wear requiring replacement"
    },
    
    "vacuum_ejector_inspection": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Ejector condition requiring inspection"
    },
    
    "vacuum_system_test": {
        "condenser_pressure": 0.0083,  # MPa (converted from 84% vacuum level)
        "air_removal_rate": 0.08,  # kg/s
        "description": "Vacuum system performance requiring testing"
    },
    
    "vacuum_leak_detection": {
        "air_removal_rate": 0.12,  # kg/s, elevated
        "condenser_pressure": 0.008,  # MPa, corresponds to ~84% vacuum
        "air_partial_pressure": 0.001,  # MPa, elevated
        "description": "Air leakage requiring detection and repair"
    },
    
    "intercondenser_cleaning": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Intercondenser fouling requiring cleaning"
    },
    
    "aftercondenser_cleaning": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Aftercondenser fouling requiring cleaning"
    },
    
    "motive_steam_system_check": {
        "steam_inlet_quality": 0.985,  # Steam quality
        "steam_inlet_temperature": 285.0,  # °C
        "description": "Motive steam system parameters requiring check"
    },
    
    # === COOLING WATER SYSTEM ===
    
    "condenser_water_treatment": {
        "water_ph": 7.2,  # pH, outside 7.5-8.5 range
        "water_hardness": 185.0,  # mg/L, elevated
        "chlorine_residual": 0.8,  # mg/L, low
        "description": "Cooling water chemistry requiring treatment"
    },
    
    "cooling_water_system_check": {
        "cooling_water_flow": 39600.0,  # kg/s (0.88 × 45000.0 design)
        "cooling_water_inlet_temp": 28.0,  # °C inlet
        "cooling_water_outlet_temp": 36.5,  # °C (28.0 + 8.5 rise)
        "description": "Cooling water system parameters requiring check"
    },
    
    # === PERFORMANCE TESTING ===
    
    "condenser_performance_test": {
        "heat_rejection_rate": 1760000000.0,  # W (0.88 × 2000.0e6 design)
        "thermal_performance_factor": 0.82,  # Overall efficiency
        "lmtd": 8.5,  # °C, elevated terminal temperature difference
        "description": "Condenser performance parameters requiring testing"
    },
    
    # === STRUCTURAL AND MECHANICAL ===
    
    "structural_inspection": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Structural condition requiring inspection"
    },
    
    "tube_bundle_inspection": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Tube bundle condition requiring inspection"
    },
    
    # === INSTRUMENTATION AND CONTROL ===
    
    "instrumentation_calibration": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Instrumentation drift requiring calibration"
    },
    
    "control_system_test": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Control system parameters requiring testing"
    },
    
    # === WATER CHEMISTRY AND QUALITY ===
    
    "condensate_quality_check": {
        "dissolved_oxygen": 8.0,  # mg/L (converted from 0.008 ppm)
        "water_ph": 7.2,  # pH
        "description": "Condensate quality parameters requiring check"
    },
    
    "corrosion_monitoring": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Corrosion parameters requiring monitoring"
    },
    
    # === ENVIRONMENTAL AND EFFICIENCY ===
    
    "thermal_efficiency_check": {
        "heat_rejection_rate": 2160000000.0,  # W (1.08 × 2000.0e6 design)
        "thermal_performance_factor": 0.85,  # Performance index
        "description": "Thermal efficiency parameters requiring check"
    },
    
    "environmental_compliance": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Environmental parameters requiring compliance check"
    },
    
    # === MAINTENANCE PLANNING ===
    
    "maintenance_scheduling": {
        # TODO: Revisit scenario - most parameters were unmapped
        "description": "Maintenance planning parameters"
    },
    
    "reliability_assessment": {
        "operating_hours": 8500.0,  # Hours (using mean_time_between_failures as operating hours)
        "system_availability": True,  # System availability
        "description": "Reliability parameters for assessment"
    }
}
