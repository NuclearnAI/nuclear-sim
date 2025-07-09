"""
Generic Initial Conditions

This module defines initial conditions for maintenance actions that can apply
to multiple subsystems or are generic in nature.

These conditions serve as fallbacks when subsystem-specific conditions are not available.
"""

from typing import Dict, Any

# Generic initial conditions for maintenance action triggering
GENERIC_CONDITIONS: Dict[str, Dict[str, Any]] = {
    
    # === CLEANING ACTIONS ===
    
    "chemical_cleaning": {
        "fouling_factor": [0.28, 0.30, 0.26],  # General fouling factor
        "deposit_thickness": [0.6, 0.7, 0.5],  # mm
        "cleaning_effectiveness": [0.75, 0.73, 0.77],  # Previous cleaning effectiveness
        "chemical_consumption": [1.15, 1.18, 1.12],  # Fraction of design
        "description": "General chemical deposits requiring cleaning"
    },
    
    "mechanical_cleaning": {
        "hard_deposits": [1.0, 1.2, 0.8],  # mm thickness
        "surface_roughness": [0.08, 0.09, 0.07],  # mm
        "mechanical_damage_risk": [0.15, 0.17, 0.13],  # Risk index
        "cleaning_frequency": [0.85, 0.83, 0.87],  # Frequency optimization
        "description": "Hard deposits requiring mechanical cleaning"
    },
    
    "system_flush": {
        "contamination_level": [450, 480, 420],  # ppm
        "debris_count": [350, 380, 320],  # particles/ml
        "system_cleanliness": [0.75, 0.73, 0.77],  # Cleanliness index
        "flush_effectiveness": [0.82, 0.80, 0.84],  # Previous flush effectiveness
        "description": "System contamination requiring flush"
    },
    
    "descaling": {
        "scale_thickness": [0.8, 0.9, 0.7],  # mm
        "scale_hardness": [0.85, 0.87, 0.83],  # Relative hardness
        "heat_transfer_loss": [0.22, 0.25, 0.19],  # Fraction loss
        "descaling_chemical_effectiveness": [0.78, 0.76, 0.80],  # Chemical effectiveness
        "description": "Scale deposits requiring removal"
    },
    
    # === INSPECTION ACTIONS ===
    
    "visual_inspection": {
        "visual_condition_index": [0.75, 0.73, 0.77],  # Overall visual condition
        "surface_defects": [15, 18, 12],  # Number of visible defects
        "wear_indicators": [0.25, 0.27, 0.23],  # Wear indication level
        "inspection_frequency": [0.88, 0.86, 0.90],  # Inspection interval optimization
        "description": "Component condition requiring visual inspection"
    },
    
    "ndt_inspection": {
        "material_integrity": [0.82, 0.80, 0.84],  # Material integrity index
        "defect_indications": [8, 10, 6],  # Number of NDT indications
        "crack_growth_rate": [0.05, 0.06, 0.04],  # mm/year
        "structural_margin": [0.78, 0.76, 0.80],  # Safety margin
        "description": "Material condition requiring NDT inspection"
    },
    
    "performance_test": {
        "performance_index": [0.85, 0.83, 0.87],  # Overall performance
        "efficiency_degradation": [0.15, 0.17, 0.13],  # Efficiency loss
        "baseline_deviation": [0.12, 0.14, 0.10],  # Deviation from baseline
        "test_frequency": [0.88, 0.86, 0.90],  # Test interval optimization
        "description": "Performance parameters requiring testing"
    },
    
    "leak_test": {
        "leak_rate": [0.05, 0.06, 0.04],  # General leak rate
        "pressure_drop": [0.08, 0.09, 0.07],  # Pressure drop across system
        "seal_integrity": [0.85, 0.83, 0.87],  # Seal condition index
        "leak_detection_sensitivity": [0.92, 0.90, 0.94],  # Detection capability
        "description": "System integrity requiring leak testing"
    },
    
    # === VALVE ACTIONS ===
    
    "valve_inspection": {
        "valve_position_accuracy": [0.92, 0.90, 0.94],  # Position accuracy
        "valve_response_time": [1.8, 2.0, 1.6],  # seconds
        "valve_leakage": [0.05, 0.06, 0.04],  # % of full flow
        "actuator_condition": [0.85, 0.83, 0.87],  # Actuator condition index
        "description": "Valve parameters requiring inspection"
    },
    
    "valve_replacement": {
        "valve_wear": [0.85, 0.87, 0.83],  # Fraction of life used
        "seat_leakage": [0.12, 0.14, 0.10],  # % leakage
        "actuator_failure_rate": [0.15, 0.17, 0.13],  # Failures per year
        "maintenance_cost": [1.25, 1.30, 1.20],  # Cost escalation factor
        "description": "Valve condition indicating replacement needed"
    },
    
    "valve_packing_replacement": {
        "packing_leakage": [0.08, 0.09, 0.07],  # Leakage rate
        "stem_friction": [1.15, 1.18, 1.12],  # Friction increase factor
        "packing_compression": [0.75, 0.73, 0.77],  # Compression remaining
        "environmental_exposure": [0.85, 0.87, 0.83],  # Exposure severity
        "description": "Valve packing condition requiring replacement"
    },
    
    # === HEAT EXCHANGER ACTIONS ===
    
    "tube_cleaning": {
        "fouling_resistance": [0.0008, 0.0009, 0.0007],  # m²K/W
        "heat_transfer_coefficient": [0.82, 0.80, 0.84],  # Fraction of clean
        "pressure_drop": [1.15, 1.18, 1.12],  # Fraction of clean
        "cleaning_cycle_time": [0.85, 0.83, 0.87],  # Cycle optimization
        "description": "Heat exchanger fouling requiring tube cleaning"
    },
    
    "tube_inspection": {
        "tube_wall_thickness": [0.88, 0.86, 0.90],  # Fraction of original
        "tube_defects": [12, 15, 9],  # Number of defects
        "corrosion_rate": [0.08, 0.09, 0.07],  # mm/year
        "remaining_life": [0.75, 0.73, 0.77],  # Fraction of design life
        "description": "Tube condition requiring inspection"
    },
    
    "tube_plugging": {
        "defective_tubes": [8, 10, 6],  # Number of defective tubes
        "leak_rate": [0.006, 0.007, 0.005],  # kg/s
        "heat_transfer_margin": [0.92, 0.90, 0.94],  # Remaining capacity
        "plugging_percentage": [0.5, 0.6, 0.4],  # % of total tubes
        "description": "Tube defects requiring plugging"
    },
    
    # === COMPONENT REPLACEMENT AND OVERHAUL ===
    
    "component_replacement": {
        "component_condition": [0.25, 0.23, 0.27],  # Remaining life fraction
        "failure_probability": [0.15, 0.17, 0.13],  # Probability of failure
        "maintenance_cost_ratio": [1.35, 1.40, 1.30],  # Repair vs replace cost
        "availability_impact": [0.85, 0.83, 0.87],  # Impact on availability
        "description": "Component condition indicating replacement needed"
    },
    
    "component_overhaul": {
        "overall_condition": [0.65, 0.63, 0.67],  # Overall condition index
        "performance_degradation": [0.25, 0.27, 0.23],  # Performance loss
        "reliability_index": [0.75, 0.73, 0.77],  # Reliability fraction
        "overhaul_interval": [0.88, 0.86, 0.90],  # Interval optimization
        "description": "Component condition requiring overhaul"
    },
    
    "adjustment": {
        "parameter_drift": [0.08, 0.09, 0.07],  # Parameter drift from setpoint
        "control_accuracy": [0.92, 0.90, 0.94],  # Control accuracy
        "calibration_drift": [1.5, 1.7, 1.3],  # % drift from calibration
        "adjustment_frequency": [0.85, 0.83, 0.87],  # Frequency optimization
        "description": "System parameters requiring adjustment"
    },
    
    "repair": {
        "damage_extent": [0.15, 0.17, 0.13],  # Damage severity index
        "repair_urgency": [0.75, 0.73, 0.77],  # Urgency index
        "repair_complexity": [0.65, 0.67, 0.63],  # Complexity index
        "temporary_fix_effectiveness": [0.82, 0.80, 0.84],  # Temporary repair effectiveness
        "description": "Component damage requiring repair"
    },
    
    "routine_maintenance": {
        "maintenance_interval": [0.88, 0.86, 0.90],  # Interval compliance
        "preventive_effectiveness": [0.85, 0.83, 0.87],  # PM effectiveness
        "condition_trend": [0.92, 0.90, 0.94],  # Condition trending
        "maintenance_optimization": [0.78, 0.76, 0.80],  # Optimization potential
        "description": "Routine maintenance parameters"
    },
    
    # === INSTRUMENTATION AND CONTROL ===
    
    "calibration": {
        "instrument_drift": [1.8, 2.0, 1.6],  # % drift from calibration
        "accuracy_degradation": [0.08, 0.09, 0.07],  # Accuracy loss
        "calibration_interval": [0.88, 0.86, 0.90],  # Interval optimization
        "measurement_uncertainty": [0.05, 0.06, 0.04],  # Uncertainty increase
        "description": "Instrument parameters requiring calibration"
    },
    
    "sensor_replacement": {
        "sensor_failure_rate": [0.12, 0.14, 0.10],  # Failures per year
        "response_time_degradation": [0.15, 0.17, 0.13],  # Response time increase
        "signal_quality": [0.85, 0.83, 0.87],  # Signal quality index
        "environmental_degradation": [0.25, 0.27, 0.23],  # Environmental impact
        "description": "Sensor condition indicating replacement needed"
    },
    
    "control_system_test": {
        "control_loop_performance": [0.85, 0.83, 0.87],  # Loop performance index
        "setpoint_tracking": [0.92, 0.90, 0.94],  # Tracking accuracy
        "disturbance_rejection": [0.88, 0.86, 0.90],  # Disturbance handling
        "system_stability": [0.95, 0.93, 0.97],  # Stability margin
        "description": "Control system parameters requiring testing"
    },
    
    # === ELECTRICAL ACTIONS ===
    
    "electrical_testing": {
        "insulation_resistance": [12.0, 11.0, 13.0],  # MΩ
        "power_factor": [0.85, 0.83, 0.87],  # Power factor
        "harmonic_distortion": [4.5, 5.0, 4.0],  # % THD
        "electrical_safety": [0.92, 0.90, 0.94],  # Safety compliance
        "description": "Electrical parameters requiring testing"
    },
    
    "insulation_testing": {
        "insulation_degradation": [0.15, 0.17, 0.13],  # Degradation rate
        "moisture_content": [0.08, 0.09, 0.07],  # % moisture
        "temperature_cycling": [850, 900, 800],  # Thermal cycles
        "dielectric_strength": [0.88, 0.86, 0.90],  # Strength fraction
        "description": "Insulation condition requiring testing"
    },
    
    # === LUBRICATION ACTIONS ===
    
    "lubrication_inspection": {
        "lubricant_condition": [0.82, 0.80, 0.84],  # Condition index
        "contamination_level": [8.5, 9.0, 8.0],  # ppm
        "viscosity_change": [0.08, 0.09, 0.07],  # Viscosity deviation
        "additive_depletion": [0.25, 0.27, 0.23],  # Additive loss fraction
        "description": "Lubrication system requiring inspection"
    },
    
    # === CONDITION MONITORING ===
    
    "condition_monitoring": {
        "overall_health_index": [0.78, 0.76, 0.80],  # Overall health
        "trending_indicators": [0.85, 0.83, 0.87],  # Trend analysis
        "alarm_frequency": [0.12, 0.14, 0.10],  # Alarm rate
        "predictive_accuracy": [0.88, 0.86, 0.90],  # Prediction accuracy
        "description": "Condition monitoring parameters"
    },
    
    # === ENVIRONMENTAL AND SAFETY ===
    
    "environmental_compliance": {
        "emission_levels": [0.85, 0.87, 0.83],  # Fraction of limit
        "waste_generation": [1.08, 1.10, 1.06],  # Fraction of baseline
        "environmental_impact": [0.82, 0.80, 0.84],  # Impact index
        "compliance_margin": [0.15, 0.13, 0.17],  # Margin to limits
        "description": "Environmental parameters requiring compliance check"
    },
    
    "safety_system_test": {
        "safety_function_availability": [0.995, 0.993, 0.997],  # Availability
        "response_time": [0.85, 0.87, 0.83],  # Fraction of required
        "false_alarm_rate": [0.05, 0.06, 0.04],  # False alarms per month
        "system_integrity": [0.98, 0.97, 0.99],  # Integrity level
        "description": "Safety system parameters requiring testing"
    }
}
