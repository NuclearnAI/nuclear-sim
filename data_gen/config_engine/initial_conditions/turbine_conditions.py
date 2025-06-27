"""
Turbine System Initial Conditions

This module defines initial conditions for triggering turbine system
maintenance actions through natural system degradation.

All conditions are set to realistic values that will naturally cross
maintenance thresholds during simulation operation.
"""

from typing import Dict, Any

# Turbine system initial conditions for maintenance action triggering
TURBINE_CONDITIONS: Dict[str, Dict[str, Any]] = {
    
    # === TURBINE BEARING ACTIONS ===
    
    "turbine_bearing_inspection": {
        "bearing_temperatures": [95.0, 96.0, 94.0, 95.5],  # °C, elevated but safe
        "bearing_vibrations": [18.0, 19.0, 17.0, 18.5],  # mils, elevated
        "bearing_clearances": [0.08, 0.09, 0.07, 0.085],  # mm, increasing
        "bearing_oil_flow": [0.88, 0.86, 0.90, 0.87],  # Fraction of design
        "description": "Bearing parameters requiring inspection",
        "safety_notes": "Conservative temperatures to avoid thermal expansion trips"
    },
    
    "turbine_bearing_replacement": {
        "bearing_temperatures": [105.0, 106.0, 104.0, 105.5],  # °C, near 110°C threshold
        "bearing_vibrations": [23.0, 24.0, 22.0, 23.5],  # mils, near 25 threshold
        "bearing_wear": [0.88, 0.90, 0.86, 0.89],  # Fraction of life used
        "bearing_metal_temperature": [108.0, 109.0, 107.0, 108.5],  # °C
        "description": "Bearing parameters indicating replacement needed",
        "safety_notes": "Carefully controlled to avoid thrust bearing displacement trips"
    },
    
    "bearing_clearance_check": {
        "bearing_clearances": [0.12, 0.13, 0.11, 0.125],  # mm, elevated
        "bearing_eccentricity": [0.65, 0.67, 0.63, 0.66],  # Fraction
        "shaft_position": [0.08, 0.09, 0.07, 0.085],  # mm from center
        "description": "Bearing clearance parameters requiring check"
    },
    
    "bearing_alignment": {
        "bearing_misalignment": [0.08, 0.09, 0.07, 0.085],  # mm
        "shaft_runout": [0.06, 0.07, 0.05, 0.065],  # mm
        "coupling_offset": [0.05, 0.06, 0.04, 0.055],  # mm
        "bearing_load_distribution": [0.75, 0.73, 0.77, 0.74],  # Uniformity index
        "description": "Bearing alignment parameters requiring correction"
    },
    
    "thrust_bearing_adjustment": {
        "thrust_bearing_temperature": [98.0, 99.0, 97.0, 98.5],  # °C, elevated
        "thrust_bearing_displacement": [35.0, 37.0, 33.0, 36.0],  # mm, approaching 50mm trip
        "axial_position": [0.08, 0.09, 0.07, 0.085],  # mm from nominal
        "thrust_load": [850.0, 870.0, 830.0, 860.0],  # kN
        "description": "Thrust bearing parameters requiring adjustment",
        "safety_notes": "Displacement kept well below 50mm trip point"
    },
    
    # === TURBINE LUBRICATION ACTIONS ===
    
    "turbine_oil_change": {
        "oil_contamination": [13.0, 14.0, 12.0, 13.5],  # ppm, near 15 threshold
        "oil_viscosity": [28.5, 29.0, 28.0, 28.8],  # cSt, degraded from 32
        "oil_acid_number": [1.8, 1.9, 1.7, 1.85],  # mg KOH/g
        "oil_water_content": [0.08, 0.09, 0.07, 0.085],  # % by volume
        "description": "Oil quality parameters indicating change needed"
    },
    
    "turbine_oil_top_off": {
        "oil_level": 72.0,  # %, just above 70% threshold
        "oil_consumption_rate": [0.8, 0.9, 0.7, 0.85],  # L/day, elevated
        "description": "Oil level near threshold requiring top-off",
        "threshold_info": {"parameter": "oil_level", "threshold": 70.0, "direction": "less_than"}
    },
    
    "oil_filter_replacement": {
        "filter_pressure_drop": [0.28, 0.29, 0.27, 0.285],  # MPa, near 0.3 threshold
        "filter_contamination": [88.0, 90.0, 86.0, 89.0],  # % capacity
        "filter_bypass_flow": [0.15, 0.17, 0.13, 0.16],  # % of total flow
        "description": "Filter parameters indicating replacement needed"
    },
    
    "oil_cooler_cleaning": {
        "oil_temperature": [62.0, 63.0, 61.0, 62.5],  # °C, elevated
        "cooler_effectiveness": [0.75, 0.73, 0.77, 0.74],  # Heat transfer fraction
        "cooling_water_temperature_rise": [18.0, 19.0, 17.0, 18.5],  # °C
        "fouling_factor": [0.28, 0.30, 0.26, 0.29],  # m²K/W
        "description": "Oil cooler parameters indicating cleaning needed"
    },
    
    "lubrication_system_test": {
        "oil_pressure": [0.18, 0.17, 0.19, 0.175],  # MPa, near 0.15 threshold
        "oil_flow_rate": [0.88, 0.86, 0.90, 0.87],  # Fraction of design
        "pump_efficiency": [0.82, 0.80, 0.84, 0.81],  # Fraction
        "system_response_time": [2.8, 3.0, 2.6, 2.9],  # Seconds
        "description": "Lubrication system parameters requiring testing"
    },
    
    # === TURBINE ROTOR ACTIONS ===
    
    "rotor_inspection": {
        "rotor_vibration": [18.0, 19.0, 17.0, 18.5],  # mils, elevated
        "rotor_temperature": [485.0, 488.0, 482.0, 486.0],  # °C
        "rotor_expansion": [12.5, 13.0, 12.0, 12.8],  # mm
        "blade_tip_clearance": [0.85, 0.87, 0.83, 0.86],  # mm, increasing
        "description": "Rotor parameters requiring inspection"
    },
    
    "thermal_bow_correction": {
        "rotor_bow": [0.08, 0.09, 0.07, 0.085],  # mm
        "thermal_gradient": [25.0, 27.0, 23.0, 26.0],  # °C/m
        "startup_vibration": [22.0, 24.0, 20.0, 23.0],  # mils
        "critical_speed_shift": [0.05, 0.06, 0.04, 0.055],  # % shift
        "description": "Thermal bow parameters requiring correction"
    },
    
    "critical_speed_test": {
        "critical_speed_1": [1785.0, 1788.0, 1782.0, 1786.0],  # rpm, shifted
        "critical_speed_2": [3565.0, 3570.0, 3560.0, 3568.0],  # rpm, shifted
        "resonance_amplitude": [15.0, 16.0, 14.0, 15.5],  # mils
        "damping_ratio": [0.08, 0.07, 0.09, 0.075],  # Fraction
        "description": "Critical speed parameters requiring testing"
    },
    
    "overspeed_test": {
        "overspeed_trip_setting": [3605.0, 3608.0, 3602.0, 3606.0],  # rpm, drift
        "governor_response_time": [0.18, 0.19, 0.17, 0.185],  # seconds
        "trip_valve_closure_time": [0.08, 0.09, 0.07, 0.085],  # seconds
        "description": "Overspeed protection parameters requiring testing"
    },
    
    # === TURBINE VIBRATION ACTIONS ===
    
    "vibration_monitoring_calibration": {
        "sensor_drift": [0.8, 0.9, 0.7, 0.85],  # % drift from calibration
        "sensor_sensitivity": [0.92, 0.90, 0.94, 0.91],  # Fraction of spec
        "frequency_response": [0.88, 0.86, 0.90, 0.87],  # Fraction of spec
        "description": "Vibration sensor parameters requiring calibration"
    },
    
    "dynamic_balancing": {
        "rotor_unbalance": [125.0, 130.0, 120.0, 128.0],  # g·mm, elevated
        "vibration_1x": [16.0, 17.0, 15.0, 16.5],  # mils at 1x frequency
        "vibration_2x": [8.0, 9.0, 7.0, 8.5],  # mils at 2x frequency
        "phase_angle": [85.0, 88.0, 82.0, 86.0],  # degrees
        "description": "Rotor balance parameters requiring dynamic balancing"
    },
    
    "vibration_analysis": {
        "overall_vibration": [18.0, 19.0, 17.0, 18.5],  # mils, elevated
        "bearing_vibrations": [16.0, 17.0, 15.0, 16.5],  # mils
        "casing_vibrations": [12.0, 13.0, 11.0, 12.5],  # mils
        "frequency_spectrum": [0.85, 0.87, 0.83, 0.86],  # Spectral content index
        "description": "Vibration levels requiring detailed analysis",
        "safety_notes": "Conservative values to avoid thrust bearing displacement"
    },
    
    # === TURBINE SYSTEM ACTIONS ===
    
    "turbine_performance_test": {
        "overall_efficiency": [0.31, 0.305, 0.315, 0.308],  # Just above 30% threshold
        "heat_rate": [11850.0, 11900.0, 11800.0, 11875.0],  # kJ/kWh, elevated
        "steam_consumption": [1.05, 1.06, 1.04, 1.055],  # Fraction of design
        "power_output": [0.95, 0.94, 0.96, 0.945],  # Fraction of rated
        "description": "Turbine performance parameters requiring testing"
    },
    
    "turbine_protection_test": {
        "trip_system_response": [0.12, 0.13, 0.11, 0.125],  # seconds
        "protection_logic_integrity": [0.95, 0.93, 0.97, 0.94],  # Fraction
        "sensor_redundancy": [0.88, 0.86, 0.90, 0.87],  # Available redundancy
        "description": "Protection system parameters requiring testing"
    },
    
    "thermal_stress_analysis": {
        "thermal_stress": [185.0, 190.0, 180.0, 188.0],  # MPa
        "temperature_gradient": [28.0, 30.0, 26.0, 29.0],  # °C/cm
        "thermal_fatigue_cycles": [8500, 8700, 8300, 8600],  # Cycles
        "creep_strain": [0.08, 0.09, 0.07, 0.085],  # % strain
        "description": "Thermal stress parameters requiring analysis"
    },
    
    "turbine_system_optimization": {
        "system_efficiency": [0.88, 0.86, 0.90, 0.87],  # Overall system efficiency
        "heat_balance": [0.92, 0.90, 0.94, 0.91],  # Heat balance closure
        "performance_degradation": [0.15, 0.17, 0.13, 0.16],  # % degradation from new
        "optimization_potential": [0.25, 0.27, 0.23, 0.26],  # % improvement potential
        "description": "System parameters indicating optimization opportunity"
    },
    
    # === EFFICIENCY AND PERFORMANCE ACTIONS ===
    
    "efficiency_analysis": {
        "turbine_efficiency": [0.31, 0.305, 0.315, 0.308],  # Just above 30% threshold
        "isentropic_efficiency": [0.85, 0.83, 0.87, 0.84],  # Fraction
        "mechanical_efficiency": [0.98, 0.975, 0.985, 0.978],  # Fraction
        "generator_efficiency": [0.96, 0.955, 0.965, 0.958],  # Fraction
        "description": "Efficiency parameters requiring analysis",
        "threshold_info": {"parameter": "overall_efficiency", "threshold": 0.30, "direction": "less_than"}
    },
    
    # === BLADE AND INTERNAL ACTIONS ===
    
    "blade_inspection": {
        "blade_vibration": [12.0, 13.0, 11.0, 12.5],  # mils
        "blade_temperature": [520.0, 525.0, 515.0, 522.0],  # °C
        "blade_stress": [165.0, 170.0, 160.0, 168.0],  # MPa
        "blade_tip_clearance": [0.88, 0.90, 0.86, 0.89],  # mm, increasing
        "description": "Blade parameters requiring inspection"
    },
    
    "blade_replacement": {
        "blade_wear": [0.85, 0.87, 0.83, 0.86],  # Fraction of life
        "blade_cracking": [0.15, 0.17, 0.13, 0.16],  # Crack density index
        "blade_erosion": [0.25, 0.27, 0.23, 0.26],  # mm material loss
        "blade_efficiency_loss": [0.12, 0.14, 0.10, 0.13],  # Efficiency reduction
        "description": "Blade condition indicating replacement needed"
    },
    
    # === CONTROL AND GOVERNOR ACTIONS ===
    
    "governor_system_check": {
        "governor_response_time": [0.15, 0.16, 0.14, 0.155],  # seconds
        "speed_regulation": [0.08, 0.09, 0.07, 0.085],  # % droop
        "load_rejection_response": [0.25, 0.27, 0.23, 0.26],  # seconds
        "control_valve_position": [0.75, 0.78, 0.72, 0.76],  # Fraction open
        "description": "Governor system parameters requiring check"
    },
    
    # === VACUUM AND CONDENSER INTERFACE ===
    
    "vacuum_system_check": {
        "turbine_back_pressure": [0.008, 0.0085, 0.0075, 0.0082],  # MPa
        "condenser_vacuum": [0.84, 0.82, 0.86, 0.83],  # Fraction of perfect vacuum
        "air_ejector_performance": [0.88, 0.86, 0.90, 0.87],  # Efficiency fraction
        "description": "Vacuum system parameters affecting turbine performance"
    },
    
    # === STARTUP AND SHUTDOWN ACTIONS ===
    
    "startup_sequence_test": {
        "warmup_time": [125.0, 130.0, 120.0, 128.0],  # minutes, extended
        "thermal_stress_rate": [2.8, 3.0, 2.6, 2.9],  # °C/min
        "synchronization_time": [8.5, 9.0, 8.0, 8.8],  # minutes
        "description": "Startup parameters requiring optimization"
    },
    
    "shutdown_sequence_test": {
        "cooldown_rate": [1.8, 2.0, 1.6, 1.9],  # °C/min
        "turning_gear_engagement": [2.5, 2.8, 2.2, 2.6],  # minutes
        "residual_vibration": [5.0, 5.5, 4.5, 5.2],  # mils after shutdown
        "description": "Shutdown parameters requiring optimization"
    }
}
