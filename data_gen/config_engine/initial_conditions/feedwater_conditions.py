"""
Feedwater System Initial Conditions

This module defines initial conditions for triggering feedwater system
maintenance actions through natural system degradation.

All conditions are set to realistic values that will naturally cross
maintenance thresholds during simulation operation.

NOTE: Only parameters that have corresponding implementations in the 
feedwater system are included. Unmapped parameters have been removed.
"""

from typing import Dict, Any

# Feedwater system initial conditions for maintenance action triggering
FEEDWATER_CONDITIONS: Dict[str, Dict[str, Any]] = {
    
    # === OIL AND LUBRICATION ACTIONS ===
    
    "oil_top_off": {
        "pump_oil_levels": [76.5, 76.0, 76.8, 76.2],  # Just above 75% threshold
        "description": "Oil levels set just above threshold to trigger top-off as levels decrease",
        "threshold_info": {"parameter": "oil_level", "threshold": 75.0, "direction": "less_than"},
        "safety_notes": "Conservative levels to avoid pump damage"
    },
    
    "oil_change": {
       "pump_oil_contamination": 14.5,          # ✅ Single float (system-wide)
        "pump_oil_water_content": 0.09,         # ✅ Single float (system-wide)
        "pump_oil_acid_number": 1.6,            # ✅ Single float (system-wide)
        "oil_temperature": 55.0,                # ✅ Single float (system-wide)
        "oil_filter_contamination": 78.0,       # ✅ Single float (system-wide)
        "feedwater_ph": 8.8,                    # ✅ Single float (system-wide)
    },
    
    "oil_analysis": {
        "pump_oil_contamination": 12.0,  # Moderate contamination (system-wide parameter)
        "pump_oil_water_content": 0.08,  # % water content (system-wide parameter)
        "pump_oil_acid_number": 1.8,  # mg KOH/g (system-wide parameter)
        "description": "Oil quality parameters requiring analysis"
    },
    
    "filter_change": {
        "oil_filter_pressure_drop": 0.25,  # MPa, near 0.3 threshold (system-wide parameter)
        "oil_filter_contamination": 85.0,  # % capacity (system-wide parameter)
        "description": "Filter pressure drop and contamination near limits"
    },
    
    "oil_system_flush": {
        "pump_oil_contamination": 18.0,  # Above 15 ppm threshold (system-wide parameter)
        "oil_system_debris_count": 450.0,  # particles/ml (system-wide parameter)
        "description": "High contamination requiring system flush"
    },
    
    # === MECHANICAL ACTIONS ===
    "bearing_inspection": {
        # Primary bearing failure indicators - trigger maintenance through vibration and wear
        "bearing_temperatures": [70.0, 71.0, 79.0, 70.5],   # Elevated but safe (below 110°C trip)
        #"pump_vibrations": [12.0, 12.5, 12.5, 12.2],           # Above 18.0 maintenance threshold
        #"bearing_wear": [0.11, 0.12, 0.10, 0.115],             # 10-12% wear (above 10% threshold)
        
        # Supporting oil parameters (degraded but below oil_change thresholds)
        #"pump_oil_contamination": 10.0,                        # Below 15.0 oil_change threshold
        #"pump_oil_water_content": 0.06,                        # Below 0.08 oil_analysis threshold
        #"pump_oil_acid_number": 1.4,                           # Below 1.8 oil_analysis threshold
        #"oil_temperature": 48.0,                               # Slightly elevated
        #"oil_filter_contamination": 65.0,                      # Below 85% filter_change threshold
        
        # Lubrication system (supporting bearing issues)
        #"oil_pressure": [0.20, 0.19, 0.21, 0.195],            # Above 0.15 threshold
        #"oil_flow_rate": [0.96, 0.95, 0.97, 0.955],           # Above 0.90 threshold
        
        # HIGH efficiency to prevent performance degradation trips
        #"pump_efficiencies": [0.92, 0.91, 0.93, 0.915],       # High efficiency (only 7-9% loss)
        #"pump_power": [1.01, 1.02, 1.00, 1.015],              # Minimal power increase
        #"motor_temperature": [78.0, 79.0, 77.0, 78.5],        # Moderate temperatures
        
        "description": "Bearing replacement triggered by vibration and wear, not efficiency degradation",
        "safety_notes": "High efficiency prevents performance trips, vibration triggers maintenance"
    },
    
    "seal_replacement": {
        "seal_leakage_rate": [0.10, 0.074, 0.04, 0.04],  # L/min, near 0.1 threshold
        #"seal_face_wear": [0.12, 0.11, 0.13, 0.11],  # Fraction of life
        #"seal_temperature": [84.0, 83.9, 84.2, 84.5],  # °C
        "description": "Seal parameters indicating replacement needed"
    },
    
    "impeller_replacement": {
        "impeller_wear": [0.08, 0.09, 0.086, 0.089],  # High wear fraction
        "pump_efficiencies": [0.78, 0.76, 0.80, 0.77],  # Below 80% threshold
        "impeller_cavitation_damage": [0.75, 0.78, 0.72, 0.76],  # Damage fraction
        "description": "Impeller wear and efficiency indicating replacement needed"
    },
    
    "impeller_inspection": {
        "impeller_wear": [0.0418, 0.0401, 0.0494, 0.0487],  # Moderate wear
        "pump_efficiencies": [0.82, 0.81, 0.83, 0.815],  # Slightly reduced
        "impeller_vibration": [2.0, 3.0, 1.0, 2.5],  # mm/s
        "description": "Impeller parameters requiring inspection"
    },
    
    # === VIBRATION ANALYSIS ===
    
    "vibration_analysis": {
        "pump_vibrations": [17.0, 18.0, 16.0, 17.5],  # mm/s, elevated
        "description": "Vibration levels requiring detailed analysis"
    },
    
    # === ELECTRICAL ACTIONS ===
    
    "motor_inspection": {
        "motor_temperature": [88.0, 89.0, 87.0, 88.5],  # °C, elevated
        "description": "Motor parameters requiring inspection"
    },
    
    # === PERFORMANCE AND SYSTEM ACTIONS ===
    
    "pump_inspection": {
        "efficiency_factor": [0.83, 0.82, 0.84, 0.825],  # Efficiency factor (multiplier)
        "flow_factor": [0.95, 0.94, 0.96, 0.945],        # Flow factor (multiplier)
        "head_factor": [0.97, 0.96, 0.98, 0.965],        # Head factor (multiplier)
        "pump_power": [1.05, 1.06, 1.04, 1.055],         # Fraction of design, elevated
        "description": "Pump performance factors requiring inspection"
    },
    
    "npsh_analysis": {
        "npsh_available": [8.5, 8.2, 8.8, 8.4],  # m, near 8.0 minimum
        "suction_pressure": 0.12,  # MPa, low (system-wide parameter)
        "cavitation_inception": [0.88, 0.90, 0.86, 0.89],  # Fraction of design flow
        "description": "NPSH conditions requiring analysis"
    },
    
    "cavitation_analysis": {
        "cavitation_intensity": [0.25, 0.27, 0.23, 0.26],  # Cavitation index
        "impeller_damage": [0.15, 0.17, 0.13, 0.16],  # Damage fraction
        "noise_level": [85.0, 87.0, 83.0, 86.0],  # dB, elevated
        "description": "Cavitation parameters requiring analysis"
    },
    
    "suction_system_check": {
        "suction_line_pressure_drop": [0.08, 0.09, 0.07, 0.085],  # MPa
        "suction_strainer_dp": [0.025, 0.028, 0.022, 0.026],  # MPa
        "suction_line_air_content": [2.8, 3.0, 2.6, 2.9],  # % by volume
        "description": "Suction system parameters requiring check"
    },
    
    "discharge_system_inspection": {
        "discharge_pressure": 1.85,  # MPa, variable (system-wide parameter)
        "discharge_valve_position": [0.88, 0.90, 0.86, 0.89],  # Fraction open
        "discharge_line_vibration": [12.0, 13.0, 11.0, 12.5],  # mm/s
        "description": "Discharge system parameters requiring inspection"
    },
    
    "lubrication_system_check": {
        "oil_pressure": [0.16, 0.15, 0.17, 0.155],  # MPa, near 0.15 threshold
        "oil_flow_rate": [0.92, 0.90, 0.94, 0.91],  # Fraction of design
        "oil_cooler_effectiveness": [0.85, 0.83, 0.87, 0.84],  # Heat transfer fraction
        "description": "Lubrication system parameters requiring check"
    },
    
    "cooling_system_check": {
        "cooling_water_temperature": [32.0, 33.0, 31.0, 32.5],  # °C, elevated
        "cooling_water_flow": [0.88, 0.86, 0.90, 0.87],  # Fraction of design
        "heat_exchanger_fouling": [0.25, 0.27, 0.23, 0.26],  # Fouling factor
        "description": "Cooling system parameters requiring check"
    },
    
    "component_overhaul": {
        "pump_efficiencies": [0.75, 0.73, 0.77, 0.74],  # Degraded efficiency requiring overhaul
        "bearing_wear": [0.85, 0.87, 0.83, 0.86],  # High bearing wear
        "impeller_wear": [0.78, 0.76, 0.80, 0.77],  # High impeller wear
        "seal_face_wear": [0.25, 0.23, 0.27, 0.24],  # Moderate seal wear (corrected parameter name)
        "description": "Component condition indicating overhaul needed"
    }
}
