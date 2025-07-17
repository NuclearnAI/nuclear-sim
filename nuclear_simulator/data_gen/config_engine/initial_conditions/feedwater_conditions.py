"""
Physics-Based Pump 1 Initial Conditions for 100-200 Minute Maintenance Triggers

Complete set of all scenarios from feedwater_conditions.py but with proper physics-based
calculations using actual degradation rates from pump_lubrication.py.

CRITICAL DISCOVERY - DRAMATICALLY FASTER DEGRADATION RATES:
1. Impeller: 0.002%/hour (was 0.0006) - 3.3x faster
2. Motor bearings: 0.0015%/hour (was 0.0005) - 3x faster  
3. Pump bearings: 0.0025%/hour (was 0.0008) - 3x faster
4. Thrust bearings: 0.003%/hour (was 0.001) - 3x faster
5. Seals: 0.004%/hour (was 0.0012) - 3.3x faster
6. Oil contamination: 0.001 ppm/hour (was 0.0002) - 5x faster

PHYSICS-BASED STRATEGY:
- Calculate actual degradation rates including load factors and coupling effects
- Set initial conditions based on target time to threshold (100-200 minutes)
- Only FWP-1 (index 0) has problematic conditions
- FWP-2, FWP-3, FWP-4 have safe baseline conditions

LOAD FACTOR CALCULATIONS:
- Motor bearings: base × electrical_load^1.5 × speed^1.8
- Pump bearings: base × hydraulic_load^2.0 × (1 + cavitation×2.0)
- Thrust bearings: base × axial_load^2.2
- Seals: base × pressure^1.8 × (1 + cavitation×5.0)
- Oil contamination: base × load + wear_contamination + chemistry_effects
"""

from typing import Dict, Any

# Physics-based pump 1 conditions - ALL SCENARIOS WITH PROPER CALCULATIONS
FEEDWATER_CONDITIONS: Dict[str, Dict[str, Any]] = {
    
    # === OIL CHANGE SCENARIO - THERMAL RUNAWAY CHAIN ===
    # Multi-system cascade: Heat → oil breakdown → contamination → seal wear → more contamination
    "oil_change": {
        # === BASE DEGRADATION LAYER ===
        "pump_oil_contamination": 12.8,                    # Moderate start, will accelerate via thermal/seal coupling
        "seal_face_wear": [10.5, 0.1, 0.1, 0.1],         # High seal wear drives contamination
        "motor_bearing_wear": [4.5, 0.1, 0.1, 0.0],      # Moderate wear creates heat
        "pump_bearing_wear": [3.2, 0.1, 0.1, 0.0],       # Moderate wear creates vibration
        "thrust_bearing_wear": [2.1, 0.1, 0.1, 0.0],     # Moderate wear contributes to system stress
        
        # === ACCELERATING CONDITIONS LAYER ===
        "oil_temperature": 72.0,                          # High temp accelerates breakdown + seal wear
        "motor_temperature": [95.0, 30.0, 30.0, 25.0],   # High electrical load creates heat (35°C safety margin)
        "bearing_temperatures": [82.0, 30.0, 30.0, 25.0], # Heat from friction (38°C safety margin)
        "pump_oil_water_content": 0.072,                  # Moisture accelerates oil breakdown
        "pump_oil_acid_number": 1.48,                     # Acidity accelerates seal + bearing wear
        "pump_vibrations": [12.5, 1.0, 1.0, 0.0],        # Vibration from bearing wear
        
        # === NPSH CHALLENGE LAYER ===
        "npsh_available": [14.2, 20.0, 20.0, 20.0],      # 2.2m from danger zone - moderate cavitation potential
        "feedwater_temperature": 242.0,                   # Higher vapor pressure reduces NPSH margin
        "suction_pressure": 0.38,                         # Lower suction pressure
        "discharge_pressure": 8.3,                        # Higher discharge pressure
        "pump_flows": [585.0, 500.0, 500.0, 0.0],        # Higher flow increases NPSH requirement
        
        # === PHYSICS COUPLING EFFECTS ===
        "cavitation_intensity": [0.08, 0.01, 0.01, 0.01], # Conservative cavitation accelerates seal wear (safe from trips)
        "impeller_wear": [1.8, 0.3, 0.3, 0.3],           # Pre-existing damage increases NPSH requirement
        "pump_oil_levels": [86.5, 98.0, 98.0, 100.0],    # Lower from seal leakage
        
        # Steam generator conditions
        "sg_levels": [12.5, 12.5, 12.5],                  # Normal SG levels
        "sg_pressures": [6.895, 6.895, 6.895],            # Normal SG pressures
        "sg_steam_flows": [500.0, 500.0, 500.0],          # Normal steam flows
        "sg_steam_qualities": [0.99, 0.99, 0.99],         # Normal steam qualities
        
        "description": "Thermal runaway chain: Heat → oil breakdown → contamination → seal wear → more contamination",
        "expected_action": "oil_change",
        "target_pump": "FWP-1",
        "physics_calculation": "Multi-system thermal cascade with 2.2m NPSH challenge"
    },
    
    # === OIL TOP-OFF SCENARIO ===
    # Seal leakage calculation: seal_wear × 0.002 L/min per % wear
    # 12% seal wear → 0.024 L/min leakage × 180 minutes = 4.32 L lost
    # 4.32 L / 150 L reservoir × 100% = 2.88% oil level loss
    # Initial level needed: 60.0% + 2.88% = 62.88%
    "oil_top_off": {
        "pump_oil_levels": [60.3, 98.0, 98.0, 100.0],    # 60.0 + 0.3 = 60.3 (aggressive 15min buffer)
        "seal_face_wear": [12.0, 0.1, 0.1, 0.1],         # Moderate seal wear causing leakage
        
        # Safe values for other parameters
        "pump_oil_contamination": 8.0,                    # Safe system-wide
        "motor_bearing_wear": [1.0, 0.1, 0.1, 0.0],      # Only FWP-1 has wear
        "pump_bearing_wear": [1.0, 0.1, 0.1, 0.0],       # Only FWP-1 has wear
        "thrust_bearing_wear": [0.5, 0.1, 0.1, 0.0],     # Only FWP-1 has wear
        "motor_temperature": [70.0, 30.0, 30.0, 25.0],   # Only FWP-1 elevated
        
        "description": "Oil level drop from seal leakage - 180 min target",
        "expected_action": "oil_top_off",
        "target_pump": "FWP-1",
        "physics_calculation": "12% seal wear → 0.024 L/min × 180 min = 2.88% loss"
    },
    
    # === MOTOR INSPECTION SCENARIO ===
    # Motor temperature rise from electrical heating: ~0.5°C/hour at high electrical load
    # Target: 100 minutes = 0.5 × 1.67 hours = 0.83°C distance needed
    "motor_inspection": {
        "motor_temperature": [84.2, 30.0, 30.0, 25.0],   # 85.0 - 0.8 = 84.2
        
        # Supporting conditions that cause motor heating
        "motor_bearing_wear": [6.0, 0.1, 0.1, 0.0],      # Bearing friction increases heat
        "pump_vibrations": [12.0, 1.0, 1.0, 0.0],        # Motor vibration from electrical issues
        
        # Safe values for other components
        "pump_oil_contamination": 10.0,                   # Safe system-wide
        "pump_bearing_wear": [1.0, 0.1, 0.1, 0.0],       # Only FWP-1 has wear
        "thrust_bearing_wear": [0.5, 0.1, 0.1, 0.0],     # Only FWP-1 has wear
        "pump_oil_levels": [90.0, 98.0, 98.0, 100.0],    # Only FWP-1 lower
        
        "description": "Motor temperature rise from electrical heating - 100 min target",
        "expected_action": "motor_inspection",
        "target_pump": "FWP-1",
        "physics_calculation": "0.5°C/hour × 1.67 hours = 0.8°C distance"
    },
    
    # === MOTOR BEARING REPLACEMENT - ELECTRICAL STRESS CASCADE ===
    # Multi-system cascade: High electrical load → heat → bearing wear → vibration → more wear
    "motor_bearing_replacement": {
        # === BASE DEGRADATION LAYER ===
        "motor_bearing_wear": [6.8, 0.1, 0.1, 0.0],      # Moderate start, will accelerate via electrical stress
        "pump_bearing_wear": [4.1, 0.1, 0.1, 0.0],       # Supporting wear creates vibration coupling
        "thrust_bearing_wear": [2.3, 0.1, 0.1, 0.0],     # Supporting wear creates system stress
        "seal_face_wear": [9.2, 0.1, 0.1, 0.1],          # Moderate seal wear
        
        # === ACCELERATING CONDITIONS LAYER ===
        "motor_temperature": [98.0, 30.0, 30.0, 25.0],   # High electrical load accelerates bearing wear 2x (32°C safety margin)
        "bearing_temperatures": [85.0, 30.0, 30.0, 25.0], # Heat from electrical losses (35°C safety margin)
        "oil_temperature": 74.0,                          # Heat reduces lubrication effectiveness
        "pump_oil_contamination": 13.2,                   # Contamination reduces lubrication quality
        "pump_vibrations": [14.8, 1.0, 1.0, 0.0],        # Vibration from bearing wear
        
        # === NPSH CHALLENGE LAYER ===
        "npsh_available": [13.9, 20.0, 20.0, 20.0],      # 1.9m from danger zone - creates cavitation stress
        "feedwater_temperature": 244.0,                   # High temperature
        "suction_pressure": 0.37,                         # Low suction pressure
        "pump_flows": [592.0, 500.0, 500.0, 0.0],        # High flow creates hydraulic stress
        "pump_speeds": [3720.0, 3600.0, 3600.0, 0.0],    # Overspeed creates electrical + mechanical stress
        
        # === PHYSICS COUPLING EFFECTS ===
        "cavitation_intensity": [0.06, 0.01, 0.01, 0.01], # Conservative cavitation creates additional vibration (safe from trips)
        "pump_oil_water_content": 0.068,                  # Moisture reduces lubrication effectiveness
        "pump_oil_acid_number": 1.44,                     # Acidity accelerates bearing wear
        "discharge_pressure": 8.4,                        # Higher discharge pressure
        
        # Steam generator conditions
        "sg_levels": [12.5, 12.5, 12.5],                  # Normal SG levels
        "sg_pressures": [6.895, 6.895, 6.895],            # Normal SG pressures
        "sg_steam_flows": [500.0, 500.0, 500.0],          # Normal steam flows
        "sg_steam_qualities": [0.99, 0.99, 0.99],         # Normal steam qualities
        
        "description": "Electrical stress cascade: High load → heat → bearing wear → vibration → more wear",
        "expected_action": "bearing_replacement",
        "component_id": "motor_bearings",
        "target_pump": "FWP-1",
        "physics_calculation": "Multi-system electrical cascade with 1.9m NPSH challenge"
    },
    
    # === PUMP BEARING REPLACEMENT ===
    # Physics-based pump bearing wear acceleration - dynamic progression to threshold
    # Target: Physics-driven wear progression from initial conditions to 6.5% threshold
    "pump_bearing_replacement": {
        # === TARGET PARAMETER - Below threshold, will increase via physics ===
        "pump_bearing_wear": [5.2, 0.1, 0.1, 0.0],         # 6.0 - 0.8 = 5.2 (aggressive 45min buffer)
        
        # === SUSTAINABLE CAVITATION SUPPORT CONDITIONS ===
        # DO NOT set cavitation_intensity directly - let physics calculate it
        # Instead, create conditions that will result in sustained cavitation
        
        # Pre-existing damage that increases NPSH requirements and sustains cavitation
        "impeller_cavitation_damage": [0.2, 0.1, 0.1, 0.1], # Conservative damage for balanced timing
        "impeller_wear": [1.2, 0.3, 0.3, 0.3],              # Conservative wear for balanced timing
        "motor_bearing_wear": [3.5, 0.1, 0.1, 0.0],         # Moderate motor bearing wear
        "thrust_bearing_wear": [1.8, 0.1, 0.1, 0.0],        # Moderate thrust bearing wear
        
        # NPSH conditions for sustained cavitation calculation
        "npsh_available": [20.0, 22.0, 22.0, 22.0],         # Increased NPSH margin for FWP-1 (5m+ safety margin)
        
        # System conditions that reduce NPSH available and promote cavitation
        "suction_pressure": 0.40,                           # Reduced suction pressure
        "feedwater_temperature": 245.0,                     # High temperature = high vapor pressure
        "discharge_pressure": 8.5,                          # Higher discharge pressure = more load
        
        # Operating conditions that increase NPSH requirement and velocity
        "pump_flows": [590.0, 500.0, 500.0, 0.0],          # FWP-1 higher flow = higher velocity
        "pump_speeds": [3700.0, 3600.0, 3600.0, 0.0],      # FWP-1 higher speed = higher NPSH requirement
        
        # Supporting conditions for bearing wear acceleration
        "oil_temperature": 68.0,                            # High oil temperature
        "pump_oil_contamination": 14.0,                     # Below 15.2 maintenance threshold
        "pump_oil_water_content": 0.065,                    # Moderate moisture
        "pump_oil_acid_number": 1.4,                        # Moderate acidity
        
        # Vibration from cavitation and bearing wear
        "pump_vibrations": [15.0, 5.0, 5.0, 0.0],          # FWP-1 high vibration
        
        # Motor conditions
        "motor_temperature": [90.0, 70.0, 70.0, 25.0],     # FWP-1 elevated motor temp
        "bearing_temperatures": [75.0, 50.0, 50.0, 25.0],  # FWP-1 elevated bearing temp
        
        # Seal conditions (supporting but not triggering)
        "seal_face_wear": [10.0, 0.1, 0.1, 0.1],           # FWP-1 moderate seal wear
        
        # Steam generator conditions
        "sg_levels": [12.5, 12.5, 12.5],                   # Normal SG levels
        "sg_pressures": [6.895, 6.895, 6.895],             # Normal SG pressures
        "sg_steam_flows": [500.0, 500.0, 500.0],           # Normal steam flows
        "sg_steam_qualities": [0.99, 0.99, 0.99],          # Normal steam qualities
        
        # Oil levels (normal)
        "pump_oil_levels": [90.0, 100.0, 100.0, 100.0],    # FWP-1 slightly lower
        
        "description": "Pump bearing wear with complete cavitation physics package - 80 min target",
        "expected_action": "bearing_replacement",
        "component_id": "pump_bearings",
        "target_pump": "FWP-1",
        "physics_calculation": "Complete NPSH deficit → sustained cavitation → 2.5x bearing acceleration"
    },
    
    # === THRUST BEARING REPLACEMENT ===
    # Base rate: 0.008%/hour (from code analysis)
    # With axial_load_factor^2.4 = 1.15^2.4 = 1.38x (from high flow/head)
    # Actual rate: 0.008 × 1.38 = 0.011%/hour
    # Target: 120 minutes = 0.011 × 2.0 hours = 1.5% distance needed
    "thrust_bearing_replacement": {
        "thrust_bearing_wear": [3.4, 0.1, 0.1, 0.0],     # 4.0 - 0.6 = 3.4 (aggressive 30min buffer)
        
        # Conditions that create high axial loads
        "pump_flows": [580.0, 500.0, 500.0, 0.0],        # High flow = high axial thrust for FWP-1
        "pump_speeds": [3700.0, 3600.0, 3600.0, 0.0],    # Slightly overspeed for FWP-1
        "bearing_temperatures": [65.0, 30.0, 30.0, 25.0], # Heat from high axial loads
        
        # Safe values for other components
        "motor_bearing_wear": [1.0, 0.1, 0.1, 0.0],      # Only FWP-1 has wear
        "pump_bearing_wear": [1.2, 0.1, 0.1, 0.0],       # Only FWP-1 has wear
        "motor_temperature": [68.0, 30.0, 30.0, 25.0],   # Only FWP-1 elevated
        "pump_oil_contamination": 8.0,                    # Safe system-wide
        
        "description": "Thrust bearing wear with axial load acceleration - 60 min target",
        "expected_action": "bearing_replacement",
        "component_id": "thrust_bearing",
        "target_pump": "FWP-1",
        "physics_calculation": "0.003 × 1.35 = 0.004%/hour × 1.0h = 0.004% distance"
    },
    
    # === MULTIPLE BEARING REPLACEMENT ===
    # All bearings approaching thresholds at different rates based on their physics
    
    #"multiple_bearing_replacement": {
    #    "motor_bearing_wear": [7.994, 0.1, 0.1, 0.0],    # 100 min target (0.0022%/h × 1.67h = 0.004%)
    #    "pump_bearing_wear": [5.992, 0.1, 0.1, 0.0],     # 80 min target (0.0036%/h × 1.33h = 0.005%)
    #    "thrust_bearing_wear": [3.992, 0.1, 0.1, 0.0],   # 60 min target (0.004%/h × 1.0h = 0.004%)
        
        # Supporting conditions for multiple bearing issues
    #    "vibration_increase": [2.0, 0.1, 0.1, 0.1],      # High vibration from multiple bearing wear
    #    "oil_temperature": 52.0,                          # Elevated from multiple heat sources
    #    "motor_temperature": [80.0, 30.0, 30.0, 25.0],   # Elevated electrical load
    #    "bearing_temperatures": [66.0, 30.0, 30.0, 25.0], # Heat from multiple bearing friction
        
    #    "description": "Multiple bearing wear with staggered physics-based timing - 60-100 min targets",
    #    "expected_action": "bearing_replacement",
    #    "component_id": "all",
    #    "target_pump": "FWP-1"
    #},
    
    # === SEAL REPLACEMENT ===
    # Complete physics package for cavitation-driven seal wear
    # Target: cavitation_intensity = 0.20 → 6.0x seal acceleration → 150 min trigger
    "seal_replacement": {
        # === TARGET PARAMETER ===
        "seal_face_wear": [15.85, 0.1, 0.1, 0.1],        # 16.0 - 0.15 = 15.85 (aggressive 15min buffer)
        
        # === CAVITATION PHYSICS PACKAGE ===
        "cavitation_intensity": [0.12, 0.05, 0.05, 0.05], # Conservative intensity for FWP-1 (safe from trips)
        
        # Pre-existing damage to increase NPSH requirements
        "impeller_cavitation_damage": [1.0, 0.1, 0.1, 0.1], # Reduced damage for proper 2+ hour timing
        "impeller_wear": [3.0, 0.3, 0.3, 0.3],              # Reduced wear for proper 2+ hour timing
        "motor_bearing_wear": [4.0, 0.1, 0.1, 0.0],         # +0.2m NPSH penalty
        "pump_bearing_wear": [3.0, 0.1, 0.1, 0.0],          # +0.15m NPSH penalty
        "thrust_bearing_wear": [2.0, 0.1, 0.1, 0.0],        # +0.1m NPSH penalty
        # Total NPSH required = 15.0 + 0.75 = 15.75m
        # Cavitation threshold = 15.75 + 2.0 = 17.75m
        
        # NPSH conditions for sustained cavitation
        "npsh_available": [20.0, 22.0, 22.0, 22.0],         # Increased NPSH margin for FWP-1 (4m+ safety margin)
        # NPSH deficit = 17.75 - 20.0 = -2.25m (no immediate cavitation, allows physics progression)
        
        # System conditions that reduce NPSH available
        "suction_pressure": 0.40,                           # Reduced suction pressure
        "feedwater_temperature": 235.0,                     # Elevated temperature
        "discharge_pressure": 8.2,                          # Slightly higher discharge
        
        # Operating conditions that amplify cavitation
        "pump_flows": [570.0, 500.0, 500.0, 0.0],          # FWP-1 higher flow
        "pump_speeds": [3650.0, 3600.0, 3600.0, 0.0],      # FWP-1 slight overspeed
        
        # Supporting conditions for seal wear acceleration
        "oil_temperature": 65.0,                            # Elevated oil temperature
        "pump_oil_contamination": 13.0,                     # Below 15.2 maintenance threshold
        "pump_oil_water_content": 0.07,                     # Moderate moisture
        "pump_oil_acid_number": 1.3,                        # Moderate acidity
        
        # Vibration from cavitation
        "pump_vibrations": [12.0, 5.0, 5.0, 0.0],          # FWP-1 elevated vibration
        
        # Motor conditions (supporting but not triggering)
        "motor_temperature": [85.0, 70.0, 70.0, 25.0],     # FWP-1 elevated motor temp
        "bearing_temperatures": [70.0, 50.0, 50.0, 25.0],  # FWP-1 elevated bearing temp
        
        # Steam generator conditions
        "sg_levels": [12.5, 12.5, 12.5],                   # Normal SG levels
        "sg_pressures": [6.895, 6.895, 6.895],             # Normal SG pressures
        "sg_steam_flows": [500.0, 500.0, 500.0],           # Normal steam flows
        "sg_steam_qualities": [0.99, 0.99, 0.99],          # Normal steam qualities
        
        # Oil levels (lower from seal leakage)
        "pump_oil_levels": [85.0, 100.0, 100.0, 100.0],    # FWP-1 lower from leakage
        
        "description": "Seal wear with complete cavitation physics package - 150 min target",
        "expected_action": "seal_replacement",
        "target_pump": "FWP-1",
        "physics_calculation": "Complete NPSH deficit → sustained cavitation → 6x seal acceleration"
    },
    
    # === OIL ANALYSIS ===
    # Multiple oil quality parameters approaching thresholds with realistic degradation
    "oil_analysis": {
        # Oil moisture increase: ~0.0015%/hour from system operation
        # Target: 120 minutes = 0.0015 × 2.0 = 0.003% distance needed
        "oil_water_content": 0.077,                       # 0.08 - 0.003 = 0.077
        
        # Oil acidity increase: ~0.01 mg KOH/g per hour from oxidation
        # Target: 120 minutes = 0.01 × 2.0 = 0.02 distance needed
        "oil_acid_number": 1.58,                          # 1.6 - 0.02 = 1.58
        
        "oil_contamination_level": 13.5,                  # Moderate contamination
        "pump_oil_contamination": 13.5,                   # System-wide parameter
        
        # Safe bearing wear levels
        "motor_bearing_wear": [1.0, 0.1, 0.1, 0.0],      # Only FWP-1 has wear
        "pump_bearing_wear": [1.0, 0.1, 0.1, 0.0],       # Only FWP-1 has wear
        "thrust_bearing_wear": [0.5, 0.1, 0.1, 0.0],     # Only FWP-1 has wear
        
        "description": "Oil quality parameters requiring analysis - 120 min target",
        "expected_action": "oil_analysis",
        "physics_calculation": "Moisture: 0.0015%/h × 2h = 0.003%, Acidity: 0.01/h × 2h = 0.02"
    },
    
    # === LUBRICATION SYSTEM CHECK ===
    # Lubrication effectiveness degradation from contamination and additive depletion
    # Rate: ~0.002/hour from oil quality degradation
    # Target: 150 minutes = 0.002 × 2.5 hours = 0.005 distance needed
    "lubrication_system_check": {
        "lubrication_effectiveness": [0.845, 0.95, 0.95, 0.95], # 0.85 - 0.005 = 0.845
        
        # Supporting degraded lubrication conditions
        "oil_pressure": [0.16, 0.25, 0.25, 0.25],        # Slightly low pressure for FWP-1
        "oil_flow_rate": [0.89, 0.95, 0.95, 0.95],       # Slightly low flow for FWP-1
        "pump_oil_contamination": 14.0,                   # High contamination affects effectiveness
        "pump_oil_water_content": 0.075,                  # High moisture affects effectiveness
        "oil_temperature": 54.0,                          # High temperature affects effectiveness
        
        # Safe bearing wear levels
        "motor_bearing_wear": [1.0, 0.1, 0.1, 0.0],      # Only FWP-1 has wear
        "pump_bearing_wear": [1.0, 0.1, 0.1, 0.0],       # Only FWP-1 has wear
        "thrust_bearing_wear": [0.5, 0.1, 0.1, 0.0],     # Only FWP-1 has wear
        
        "description": "Lubrication effectiveness degradation - 150 min target",
        "expected_action": "lubrication_system_check",
        "target_pump": "FWP-1",
        "physics_calculation": "0.002/hour × 2.5 hours = 0.005 effectiveness loss"
    },
    
    # === PUMP INSPECTION ===
    # Performance factor degradation from accumulated wear and lubrication effects
    "pump_inspection": {
        # Efficiency degradation from bearing wear and lubrication quality
        "efficiency_factor": [0.845, 0.95, 0.95, 0.95],  # 0.85 - 0.005 = 0.845
        "flow_factor": [0.965, 0.98, 0.98, 0.98],        # 0.97 - 0.005 = 0.965
        "head_factor": [0.945, 0.96, 0.96, 0.96],        # 0.95 - 0.005 = 0.945
        
        # Supporting system health indicators
        "system_health_factor": [0.82, 0.90, 0.90, 0.90], # Overall health declining
        "lubrication_effectiveness": [0.86, 0.92, 0.92, 0.92], # Lubrication quality declining
        
        # Moderate wear levels causing performance degradation
        "motor_bearing_wear": [3.0, 0.1, 0.1, 0.0],      # Moderate wear affecting efficiency
        "pump_bearing_wear": [2.5, 0.1, 0.1, 0.0],       # Moderate wear affecting flow
        "thrust_bearing_wear": [2.0, 0.1, 0.1, 0.0],     # Moderate wear affecting head
        
        "description": "Performance degradation requiring inspection - 120 min target",
        "expected_action": "pump_inspection",
        "target_pump": "FWP-1"
    },
    
    # === VIBRATION ANALYSIS ===
    # Vibration increase from bearing wear: ~0.1 mm/s per % bearing wear
    # With 4% total bearing wear → 0.4 mm/s increase over time
    "vibration_analysis": {
        # Vibration approaching threshold with physics-based calculation
        "pump_vibrations": [19.85, 1.0, 1.0, 0.0],       # 20.0 - 0.15 = 19.85
        "vibration_increase": [1.45, 0.1, 0.1, 0.1],     # 1.5 - 0.05 = 1.45
        
        # Bearing wear levels that contribute to vibration
        "motor_bearing_wear": [4.0, 0.1, 0.1, 0.0],      # 4% wear → 0.4 mm/s vibration
        "pump_bearing_wear": [3.5, 0.1, 0.1, 0.0],       # 3.5% wear → 0.35 mm/s vibration
        "thrust_bearing_wear": [2.5, 0.1, 0.1, 0.0],     # 2.5% wear → 0.25 mm/s vibration
        
        # Supporting temperature indicators
        "motor_temperature": [75.0, 30.0, 30.0, 25.0],   # Elevated from bearing friction
        "bearing_temperatures": [65.0, 30.0, 30.0, 25.0], # Heat from bearing wear
        
        "description": "Vibration increase from bearing wear - 90 min target",
        "expected_action": "vibration_analysis",
        "target_pump": "FWP-1",
        "physics_calculation": "Total bearing wear → vibration increase over 90 minutes"
    },
    
    # === COMPONENT OVERHAUL ===
    # System health degradation from multiple accumulated factors
    "component_overhaul": {
        # System health below threshold from multiple degraded components
        "system_health_factor": [0.795, 0.85, 0.85, 0.85], # 0.80 - 0.005 = 0.795
        
        # High wear levels across multiple components
        "motor_bearing_wear": [12.0, 0.1, 0.1, 0.0],     # High motor bearing wear
        "pump_bearing_wear": [8.5, 0.1, 0.1, 0.0],       # High pump bearing wear
        "thrust_bearing_wear": [6.0, 0.1, 0.1, 0.0],     # High thrust bearing wear
        "seal_wear": [7.0, 0.1, 0.1, 0.1],               # High seal wear
        
        # Severely degraded oil system
        "oil_contamination_level": 25.0,                  # Severely contaminated oil
        "pump_oil_contamination": 25.0,                   # System-wide contamination
        "lubrication_effectiveness": [0.70, 0.85, 0.85, 0.85], # Poor lubrication
        
        # Severely degraded performance
        "efficiency_factor": [0.75, 0.90, 0.90, 0.90],   # Severely degraded efficiency
        "flow_factor": [0.78, 0.92, 0.92, 0.92],         # Severely degraded flow
        
        "description": "Multiple system degradation requiring overhaul - 120 min target",
        "expected_action": "component_overhaul",
        "target_pump": "FWP-1"
    },
    
    # === ROUTINE MAINTENANCE ===
    # Gradual system health decline requiring preventive maintenance
    "routine_maintenance": {
        # System health approaching routine maintenance threshold
        "system_health_factor": [0.895, 0.95, 0.95, 0.95], # 0.90 - 0.005 = 0.895
        
        # Moderate oil quality degradation
        "oil_contamination_level": 8.0,                   # Moderate contamination
        "pump_oil_contamination": 8.0,                    # System-wide parameter
        "lubrication_effectiveness": [0.915, 0.95, 0.95, 0.95], # Good but declining
        
        # Low wear levels but accumulating
        "motor_bearing_wear": [2.0, 0.1, 0.1, 0.0],      # Low but measurable wear
        "pump_bearing_wear": [1.5, 0.1, 0.1, 0.0],       # Low but measurable wear
        "thrust_bearing_wear": [1.0, 0.1, 0.1, 0.0],     # Low but measurable wear
        
        "description": "Gradual system decline - routine maintenance - 180 min target",
        "expected_action": "routine_maintenance",
        "target_pump": "FWP-1"
    },
    
    # === NORMAL OPERATION ===
    # Normal operational conditions with minor wear - no maintenance required
    #"normal_operation": {
        ## FIXED: Update SG flows to match actual simulation data
        #"sg_steam_flows": [450.0, 450.0, 450.0],         # Match actual simulation data (not 500.0)
        #"total_flow_rate": 1350.0,                        # Sum of SG flows (450×3=1350)
        
        ## Minor bearing wear - well below maintenance thresholds
        #"motor_bearing_wear": [2.5, 0.1, 0.1, 0.0],      # 2.5% wear (threshold: 8.0%)
        #"pump_bearing_wear": [1.8, 0.1, 0.1, 0.0],       # 1.8% wear (threshold: 6.0%)
        #"thrust_bearing_wear": [1.2, 0.1, 0.1, 0.0],     # 1.2% wear (threshold: 4.0%)
        
        ## Good oil quality with minor operational degradation
        #"pump_oil_contamination": 8.0,                    # 8.0 ppm (threshold: 15.0 ppm)
        #"pump_oil_water_content": 0.04,                   # 0.04% (threshold: 0.08%)
        #"pump_oil_acid_number": 1.2,                      # 1.2 mg KOH/g (threshold: 1.6)
        #"oil_temperature": 48.0,                          # 48°C (threshold: 55.0°C)
        
        ## Good performance with minor efficiency loss
        #"lubrication_effectiveness": [0.92, 0.95, 0.95, 0.95], # 92% effectiveness (threshold: 85%)
        #"system_health_factor": [0.88, 0.92, 0.92, 0.92], # 88% health (threshold: 80%)
        
        ## Normal operational temperatures and vibrations
        #"motor_temperature": [65.0, 45.0, 45.0, 25.0],   # 65°C FWP-1 (threshold: 85.0°C)
        #"bearing_temperatures": [60.0, 40.0, 40.0, 25.0], # Normal bearing temps
        #"pump_vibrations": [8.0, 3.0, 3.0, 0.0],         # 8.0 mm/s FWP-1 (threshold: 20.0 mm/s)
        
        ## Good NPSH conditions
        #"npsh_available": [19.5, 20.0, 20.0, 20.0],      # 19.5m FWP-1 (threshold: 18.0m)
        #"cavitation_intensity": [0.08, 0.02, 0.02, 0.02], # Low cavitation (threshold: 0.25)
        
        ## Minor seal and impeller wear
        #"seal_face_wear": [3.0, 0.5, 0.5, 0.5],          # 3.0% wear (threshold: 15.0%)
        #"impeller_wear": [1.5, 0.3, 0.3, 0.3],           # 1.5% wear (threshold: 8.0%)
        #"impeller_cavitation_damage": [0.8, 0.1, 0.1, 0.1], # Minor damage (threshold: 8.0)
        
        ## Good oil levels and pressures
        #"pump_oil_levels": [95.0, 98.0, 98.0, 100.0],    # Good oil levels (threshold: 60.0%)
        #"oil_pressure": [0.22, 0.25, 0.25, 0.25],        # Good pressure (threshold: 0.15 MPa)
        #"oil_flow_rate": [0.95, 1.0, 1.0, 1.0],          # Good flow (threshold: 0.90)
        
        ## Normal system pressures
        #"suction_pressure": 0.45,                         # Good suction pressure
        #"discharge_pressure": 7.8,                        # Normal discharge pressure
        
        #"description": "Normal operational conditions after several months of service - minor wear but no maintenance required",
        #"expected_action": "none",
        #"target_pump": "All pumps operating normally",
        #"physics_notes": [
            #"Represents typical operational wear after 3-6 months of service",
            #"All parameters comfortably below maintenance thresholds",
            #"Minor efficiency loss from normal wear patterns",
            #"Oil quality showing expected operational degradation",
            #"No maintenance actions triggered - normal operations",
            #"FIXED: SG flows updated to match actual simulation data (450 kg/s per SG)"
        #]
    #},
    
    # === GRADUAL DEGRADATION ===
    # Multiple actions triggered at different time intervals based on different degradation rates
    #"gradual_degradation": {
    #    # Immediate action (Week 1)
    #    "pump_oil_contamination": 15.2,                   # Already above 15.0 → immediate oil_change
    #    "pump_oil_levels": [62.0, 58.0, 90.0, 100.0],    # FWP-2 below 60% → immediate oil_top_off
    #    
    #    # Medium-term actions (Month 2-3)
    #    "seal_face_wear": [12.0, 8.0, 11.0, 9.5],        # Moderate seal wear
    #    "motor_bearing_wear": [7.8, 6.1, 7.2, 0.0],      # FWP-1,3 approaching 8.0% threshold
    #    "pump_bearing_wear": [5.0, 4.5, 4.0, 0.3],       # FWP-1 approaching 6.0% threshold
    #    "thrust_bearing_wear": [2.0, 3.5, 3.0, 0.3],     # Various levels approaching thresholds
    #    
    #    # Long-term indicators
    #    "motor_temperature": [82.0, 70.0, 78.0, 25.0],   # Elevated but below 85°C threshold
    #    "oil_temperature": 52.0,                          # Elevated but below 55°C threshold
    #    "bearing_temperatures": [65.0, 60.0, 68.0, 25.0], # Elevated but below 70°C threshold
    #    
    #    "description": "Staggered degradation timeline - multiple actions over different timeframes",
    #    "target_pump": "Multiple pumps at different times"
    #},
    
    # === DYNAMIC CAVITATION COUPLING TEST ===
    # Conditions that drive cavitation calculation dynamically with proper physics
    # "dynamic_cavitation_coupling_test": {
        # # NPSH conditions that promote cavitation
        # "npsh_available": [17.0, 18.5, 19.5, 20.0],      # FWP-1 has reduced NPSH margin
        # "suction_pressure": 0.35,                         # Low suction pressure system-wide
        # "feedwater_temperature": 240.0,                   # High temperature increases vapor pressure
        # "oil_temperature": 54.0,                          # Elevated oil temperature
        
        # # Initial wear levels that will couple with cavitation
        # "impeller_wear": [2.0, 2.5, 1.5, 0.0],          # Small initial impeller wear
        # "motor_bearing_wear": [1.5, 2.0, 1.0, 0.0],     # Small initial motor bearing wear
        # "pump_bearing_wear": [1.0, 1.5, 0.8, 0.0],      # Small initial pump bearing wear
        # "thrust_bearing_wear": [0.5, 0.8, 0.3, 0.0],    # Small initial thrust bearing wear
        
        # # Lubrication conditions
        # "pump_oil_contamination": 12.0,                  # Moderate contamination
        # "pump_oil_water_content": 0.07,                  # Elevated moisture
        # "pump_oil_acid_number": 1.4,                     # Elevated acidity
        # "lubrication_effectiveness": [0.88, 0.85, 0.90, 0.95], # Declining effectiveness
        
        # # Operational conditions that create high loads
        # "motor_temperature": [82.0, 84.0, 80.0, 25.0],  # Elevated motor temperatures
        # "pump_oil_levels": [88.0, 85.0, 90.0, 100.0],   # Lower oil levels
        # "pump_vibrations": [8.0, 9.0, 7.0, 0.0],        # Elevated vibration
        # "pump_flows": [520.0, 530.0, 510.0, 0.0],       # Above rated flow
        # "pump_speeds": [3700.0, 3750.0, 3650.0, 0.0],   # Above rated speed
        
        # "description": "Dynamic cavitation coupling test with physics-based progression",
        # "physics_notes": [
            # "Reduced NPSH margin triggers cavitation calculation",
            # "Above-rated flow increases cavitation intensity", 
            # "Initial wear increases NPSH requirements",
            # "Cavitation accelerates wear through coupling",
            # "Positive feedback loop develops over time"
        # ]
    # }
}

# === ARCHITECTURE VALIDATION ===
# State variable mappings for validation (same as feedwater_conditions.py)
STATE_VARIABLE_MAPPINGS = {
    # Pump System State Variables (pump.state.*)
    "pump_hydraulic_variables": {
        "cavitation_damage": "pump.state.cavitation_damage",  # 0-100 scale
        "cavitation_intensity": "pump.state.cavitation_intensity",  # 0-1 scale
        "npsh_available": "pump.state.npsh_available",  # meters
        "motor_temperature": "pump.state.motor_temperature",  # °C
        "suction_pressure": "system_conditions['suction_pressure']",  # MPa
        "discharge_pressure": "system_conditions['discharge_pressure']",  # MPa
    },
    
    # Lubrication System State Variables (lubrication_system.*)
    "lubrication_system_variables": {
        "oil_level": "lubrication_system.oil_level",  # %
        "oil_temperature": "lubrication_system.oil_temperature",  # °C
        "oil_contamination_level": "lubrication_system.oil_contamination_level",  # ppm
        "oil_moisture_content": "lubrication_system.oil_moisture_content",  # %
        "oil_acidity_number": "lubrication_system.oil_acidity_number",  # mg KOH/g
        "lubrication_effectiveness": "lubrication_system.lubrication_effectiveness",  # 0-1
        "seal_leakage_rate": "lubrication_system.seal_leakage_rate",  # L/min
        "system_health_factor": "lubrication_system.system_health_factor",  # 0-1
    },
    
    # Component Wear Variables (lubrication_system.component_wear[])
    "component_wear_variables": {
        "motor_bearing_wear": "lubrication_system.component_wear['motor_bearings']",  # %
        "pump_bearing_wear": "lubrication_system.component_wear['pump_bearings']",  # %
        "thrust_bearing_wear": "lubrication_system.component_wear['thrust_bearing']",  # %
        "seal_wear": "lubrication_system.component_wear['mechanical_seals']",  # %
    },
    
    # Performance Factor Variables (lubrication_system.*)
    "performance_factor_variables": {
        "efficiency_factor": "lubrication_system.pump_efficiency_factor",  # 0-1 multiplier
        "flow_factor": "lubrication_system.pump_flow_factor",  # 0-1 multiplier
        "head_factor": "lubrication_system.pump_head_factor",  # 0-1 multiplier
        "vibration_increase": "lubrication_system.vibration_increase",  # mm/s
    }
}

# === MAINTENANCE THRESHOLD ALIGNMENT ===
# These thresholds match the corrected values in nuclear_plant_comprehensive_config.yaml
MAINTENANCE_THRESHOLD_ALIGNMENT = {
    "cavitation_damage": 8.0,  # ✅ Matches config threshold
    "cavitation_intensity": 0.25,  # ✅ Matches config threshold
    "npsh_available": 8.5,  # ✅ Matches config threshold (less_than)
    "motor_bearing_wear": 8.0,  # ✅ Matches config threshold
    "pump_bearing_wear": 6.0,  # ✅ Matches config threshold
    "thrust_bearing_wear": 4.0,  # ✅ Matches config threshold
    "seal_wear": 15.0,  # ✅ Matches config threshold - Updated to realistic 15%
    "oil_level": 60.0,  # ✅ Matches config threshold (less_than)
    "oil_water_content": 0.08,  # ✅ Matches config threshold
    "oil_acid_number": 1.6,  # ✅ Matches config threshold
    "oil_temperature": 55.0,  # ✅ Matches config threshold
    "efficiency_factor": 0.85,  # ✅ Matches config threshold (less_than)
    "system_health_factor": 0.80,  # ✅ Matches config threshold (less_than)
    "lubrication_effectiveness": 0.85,  # ✅ Matches config threshold (less_than)
    "motor_temperature": 85.0,  # ✅ Matches config threshold
    "seal_leakage_rate": 0.15,  # ✅ Matches config threshold
}


# === RANDOMIZATION SUPPORT ===

from typing import Optional
from .randomization_utils import (
    add_randomness_to_conditions, 
    validate_safety_limits,
    get_scenario_based_conditions,
    apply_scenario_to_array_parameter
)

def get_randomized_feedwater_conditions(
    action: str,
    seed: Optional[int] = None,
    scaling_factor: float = 0.1
) -> Dict[str, Any]:
    """
    Get randomized conditions for a specific feedwater action using scenario-based approach
    
    This function is called by the initial conditions catalog to provide
    randomized variants that interface with ComprehensiveComposer.
    
    Args:
        action: Feedwater action name
        seed: Random seed for reproducibility
        scaling_factor: Scaling factor for randomization (used for fallback only)
    
    Returns:
        Randomized conditions dictionary with physics-consistent parameters
    """
    if action not in FEEDWATER_CONDITIONS:
        raise ValueError(f"Unknown feedwater action: {action}")
    
    base_conditions = FEEDWATER_CONDITIONS[action]
    
    # Use scenario-based randomization for supported actions
    randomized = get_scenario_based_conditions(action, base_conditions, seed)
    
    # Handle array parameters that need special processing
    if "pump_oil_levels" in randomized and isinstance(randomized["pump_oil_levels"], (int, float)):
        # Convert single scenario value to array with preserved pattern
        original_array = base_conditions.get("pump_oil_levels", [100.0, 100.0, 100.0, 100.0])
        randomized["pump_oil_levels"] = apply_scenario_to_array_parameter(
            original_array, randomized["pump_oil_levels"], "preserve_pattern"
        )
    
    # Handle motor_bearing_wear array
    if "motor_bearing_wear" in randomized and isinstance(randomized["motor_bearing_wear"], (int, float)):
        original_array = base_conditions.get("motor_bearing_wear", [0.0, 0.1, 0.1, 0.0])
        randomized["motor_bearing_wear"] = apply_scenario_to_array_parameter(
            original_array, randomized["motor_bearing_wear"], "first_element_only"
        )
    
    # Handle pump_bearing_wear array
    if "pump_bearing_wear" in randomized and isinstance(randomized["pump_bearing_wear"], (int, float)):
        original_array = base_conditions.get("pump_bearing_wear", [0.0, 0.1, 0.1, 0.0])
        randomized["pump_bearing_wear"] = apply_scenario_to_array_parameter(
            original_array, randomized["pump_bearing_wear"], "first_element_only"
        )
    
    # Handle thrust_bearing_wear array
    if "thrust_bearing_wear" in randomized and isinstance(randomized["thrust_bearing_wear"], (int, float)):
        original_array = base_conditions.get("thrust_bearing_wear", [0.0, 0.1, 0.1, 0.0])
        randomized["thrust_bearing_wear"] = apply_scenario_to_array_parameter(
            original_array, randomized["thrust_bearing_wear"], "first_element_only"
        )
    
    # Handle motor_temperature array
    if "motor_temperature" in randomized and isinstance(randomized["motor_temperature"], (int, float)):
        original_array = base_conditions.get("motor_temperature", [70.0, 30.0, 30.0, 25.0])
        randomized["motor_temperature"] = apply_scenario_to_array_parameter(
            original_array, randomized["motor_temperature"], "first_element_only"
        )
    
    # Handle pump_vibrations array
    if "pump_vibrations" in randomized and isinstance(randomized["pump_vibrations"], (int, float)):
        original_array = base_conditions.get("pump_vibrations", [5.0, 1.0, 1.0, 0.0])
        randomized["pump_vibrations"] = apply_scenario_to_array_parameter(
            original_array, randomized["pump_vibrations"], "first_element_only"
        )
    
    # Handle npsh_available array
    if "npsh_available" in randomized and isinstance(randomized["npsh_available"], (int, float)):
        original_array = base_conditions.get("npsh_available", [20.0, 20.0, 20.0, 20.0])
        randomized["npsh_available"] = apply_scenario_to_array_parameter(
            original_array, randomized["npsh_available"], "first_element_only"
        )
    
    # Handle cavitation_intensity array
    if "cavitation_intensity" in randomized and isinstance(randomized["cavitation_intensity"], (int, float)):
        original_array = base_conditions.get("cavitation_intensity", [0.05, 0.01, 0.01, 0.01])
        randomized["cavitation_intensity"] = apply_scenario_to_array_parameter(
            original_array, randomized["cavitation_intensity"], "first_element_only"
        )
    
    # Feedwater-specific safety validation rules
    feedwater_safety_rules = {
        "motor_temperature": {
            "safety_limit": 130.0,
            "threshold_type": "safety",
            "safety_direction": "greater_than"
        },
        "npsh_available": {
            "safety_limit": 12.0,
            "threshold_type": "safety",
            "safety_direction": "less_than"
        },
        "pump_vibrations": {
            "safety_limit": 25.0,
            "threshold_type": "safety",
            "safety_direction": "greater_than"
        },
        "bearing_temperatures": {
            "safety_limit": 120.0,
            "threshold_type": "safety",
            "safety_direction": "greater_than"
        }
    }
    
    # Validate safety
    violations = validate_safety_limits(randomized, feedwater_safety_rules)
    if violations["errors"]:
        raise ValueError(f"Safety violations in randomized conditions: {violations['errors']}")
    
    return randomized

# Convenience functions for common scenarios
def create_randomized_feedwater_scenario(action: str, num_variants: int = 5, base_seed: int = 42):
    """Create multiple randomized variants of a feedwater scenario"""
    variants = {}
    for i in range(num_variants):
        seed = base_seed + i
        randomized = get_randomized_feedwater_conditions(action, seed)
        variants[f"{action}_variant_{i+1}"] = randomized
    return variants

def get_randomized_oil_change_conditions(seed: int = None):
    """Get randomized oil change scenario"""
    return get_randomized_feedwater_conditions("oil_change", seed)

def get_randomized_bearing_replacement_conditions(seed: int = None):
    """Get randomized bearing replacement scenario"""
    return get_randomized_feedwater_conditions("motor_bearing_replacement", seed)

def get_randomized_oil_top_off_conditions(seed: int = None):
    """Get randomized oil top-off scenario"""
    return get_randomized_feedwater_conditions("oil_top_off", seed)
