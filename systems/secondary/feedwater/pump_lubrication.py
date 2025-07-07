"""
Feedwater Pump Lubrication System

This module implements a comprehensive lubrication system for feedwater pumps
using the abstract base lubrication system. It replaces the individual oil
tracking in the pump system with a unified lubrication approach.

Key Features:
1. Unified lubrication system for all feedwater pump components
2. Oil quality tracking and degradation modeling
3. Component wear calculation with lubrication effects
4. Maintenance scheduling and procedures
5. Integration with existing feedwater pump models

Physical Basis:
- High-pressure pump bearing lubrication
- Seal lubrication and leakage modeling
- Motor bearing lubrication systems
- Thrust bearing oil film dynamics
- Cavitation effects on lubrication
"""

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from simulator.state import auto_register

from ..lubrication_base import BaseLubricationSystem, BaseLubricationConfig, LubricationComponent
from ..component_descriptions import FEEDWATER_COMPONENT_DESCRIPTIONS

warnings.filterwarnings("ignore")


@dataclass
class FeedwaterPumpLubricationConfig(BaseLubricationConfig):
    """
    Configuration for feedwater pump lubrication system
    
    References:
    - API 610: Centrifugal Pumps for Petroleum, Petrochemical and Natural Gas Industries
    - ANSI/HI 9.6.6: Rotodynamic Pumps - Guideline for Operating Regions
    - Pump lubrication system specifications for nuclear applications
    """
    
    # Override base class defaults for feedwater pump-specific values
    system_id: str = "FWP-LUB-001"
    system_type: str = "feedwater_pump"
    oil_reservoir_capacity: float = 150.0       # liters (medium capacity for pump)
    oil_operating_pressure: float = 0.25        # MPa (lower pressure than governor)
    oil_temperature_range: Tuple[float, float] = (40.0, 85.0)  # °C wider range for pumps
    oil_viscosity_grade: str = "ISO VG 32"      # Standard pump oil viscosity
    
    # Feedwater pump-specific parameters
    pump_rated_power: float = 10.0              # MW pump rated power
    pump_rated_speed: float = 3600.0            # RPM pump rated speed
    pump_rated_flow: float = 555.0              # kg/s pump rated flow
    seal_water_system_pressure: float = 0.8     # MPa seal water pressure
    
    # Enhanced filtration for high-speed pumps
    filter_micron_rating: float = 10.0          # microns filter rating
    contamination_limit: float = 15.0           # ppm (aligned with maintenance threshold)
    
    # Maintenance intervals for critical feedwater service
    oil_change_interval: float = 6000.0         # hours (8 months)
    oil_analysis_interval: float = 500.0        # hours (3 weeks)


class FeedwaterPumpLubricationSystem(BaseLubricationSystem):
    """
    Feedwater pump-specific lubrication system implementation
    
    This system manages lubrication for all feedwater pump components including:
    1. Motor bearings (drive end and non-drive end)
    2. Pump bearings (radial and thrust bearings)
    3. Mechanical seals and seal support systems
    4. Coupling and alignment systems
    
    Physical Models:
    - High-speed bearing lubrication dynamics
    - Seal face lubrication and wear
    - Cavitation effects on bearing lubrication
    - High-pressure seal water interaction
    """
    
    def __init__(self, config: FeedwaterPumpLubricationConfig):
        """Initialize feedwater pump lubrication system"""
        
        # Initialize maintenance action tracking flags
        self.maintenance_action_flags = {
            'oil_change': False,
            'oil_top_off': False,
            'bearing_replacement': False,
            'seal_replacement': False,
            'component_overhaul': False,
            'system_cleaning': False,
            'bearing_inspection': False,
            'impeller_inspection': False,
            'impeller_replacement': False,
            'lubrication_system_check': False,
            'motor_inspection': False,
            'oil_analysis': False,
            'vibration_analysis': False
        }
        self.last_maintenance_action = None
        
        # Define feedwater pump-specific lubricated components
        pump_components = [
            LubricationComponent(
                component_id="impeller",
                component_type="impeller",
                oil_flow_requirement=0.0,          # L/min (no direct lubrication)
                oil_pressure_requirement=0.0,      # MPa (no direct lubrication)
                oil_temperature_max=100.0,         # °C (indirect through pump bearings)
                base_wear_rate=0.0006,             # %/hour (cavitation, erosion, corrosion)
                load_wear_exponent=1.8,            # High hydraulic load sensitivity
                speed_wear_exponent=2.0,           # Very high speed sensitivity (tip speed)
                contamination_wear_factor=1.5,     # Moderate contamination sensitivity
                wear_performance_factor=0.025,     # 2.5% performance loss per % wear
                lubrication_performance_factor=0.0, # No direct lubrication effect
                wear_alarm_threshold=10.0,         # % wear alarm (earlier than bearings)
                wear_trip_threshold=25.0           # % wear trip (earlier than bearings)
            ),
            LubricationComponent(
                component_id="motor_bearings",
                component_type="bearing",
                oil_flow_requirement=8.0,          # L/min
                oil_pressure_requirement=0.25,     # MPa
                oil_temperature_max=85.0,          # °C
                base_wear_rate=0.0005,             # %/hour (continuous high-speed operation)
                load_wear_exponent=1.5,            # High load sensitivity
                speed_wear_exponent=1.8,           # Very high speed sensitivity
                contamination_wear_factor=2.5,     # High contamination sensitivity
                wear_performance_factor=0.015,     # 1.5% performance loss per % wear
                lubrication_performance_factor=0.05, # 5% performance loss with poor lube (reduced)
                wear_alarm_threshold=20.0,         # % wear alarm - FIXED: Increased from 10.0% to realistic 20%
                wear_trip_threshold=60.0           # % wear trip - FIXED: Increased from 25.0% to realistic 60%
            ),
            LubricationComponent(
                component_id="pump_bearings",
                component_type="bearing",
                oil_flow_requirement=12.0,         # L/min (higher flow for pump bearings)
                oil_pressure_requirement=0.25,     # MPa
                oil_temperature_max=80.0,          # °C (stricter for pump bearings)
                base_wear_rate=0.0008,             # %/hour (higher wear due to hydraulic loads)
                load_wear_exponent=2.0,            # Very high load sensitivity
                speed_wear_exponent=1.6,           # High speed sensitivity
                contamination_wear_factor=3.0,     # Very sensitive to contamination
                wear_performance_factor=0.02,      # 2% performance loss per % wear
                lubrication_performance_factor=0.1, # 10% performance loss with poor lube (reduced)
                wear_alarm_threshold=15.0,         # % wear alarm - FIXED: Increased from 8.0% to realistic 15%
                wear_trip_threshold=50.0           # % wear trip - FIXED: Increased from 20.0% to realistic 50%
            ),
            LubricationComponent(
                component_id="thrust_bearing",
                component_type="bearing",
                oil_flow_requirement=15.0,         # L/min (highest flow for thrust bearing)
                oil_pressure_requirement=0.3,      # MPa (higher pressure for thrust loads)
                oil_temperature_max=75.0,          # °C (strictest for thrust bearing)
                base_wear_rate=0.001,              # %/hour (highest wear - takes axial loads)
                load_wear_exponent=2.2,            # Extremely high load sensitivity
                speed_wear_exponent=1.4,           # Moderate speed sensitivity
                contamination_wear_factor=3.5,     # Extremely sensitive to contamination
                wear_performance_factor=0.025,     # 2.5% performance loss per % wear
                lubrication_performance_factor=0.15, # 15% performance loss with poor lube (reduced)
                wear_alarm_threshold=12.0,         # % wear alarm - FIXED: Increased from 6.0% to realistic 12%
                wear_trip_threshold=40.0           # % wear trip - FIXED: Increased from 15.0% to realistic 40%
            ),
            LubricationComponent(
                component_id="mechanical_seals",
                component_type="seal",
                oil_flow_requirement=5.0,          # L/min
                oil_pressure_requirement=0.2,      # MPa
                oil_temperature_max=70.0,          # °C
                base_wear_rate=0.0012,             # %/hour (highest wear - sliding contact)
                load_wear_exponent=1.8,            # High load sensitivity
                speed_wear_exponent=1.2,           # Moderate speed sensitivity
                contamination_wear_factor=4.0,     # Extremely sensitive to contamination
                wear_performance_factor=0.03,      # 3% performance loss per % wear
                lubrication_performance_factor=0.2, # 20% performance loss with poor lube (reduced)
                wear_alarm_threshold=15.0,         # % wear alarm - FIXED: Increased from 5.0% to realistic 15%
                wear_trip_threshold=50.0           # % wear trip - FIXED: Increased from 12.0% to realistic 50%
            ),
            LubricationComponent(
                component_id="coupling_system",
                component_type="coupling",
                oil_flow_requirement=3.0,          # L/min
                oil_pressure_requirement=0.15,     # MPa
                oil_temperature_max=90.0,          # °C
                base_wear_rate=0.0003,             # %/hour (lowest wear - flexible coupling)
                load_wear_exponent=1.3,            # Moderate load sensitivity
                speed_wear_exponent=1.0,           # Low speed sensitivity
                contamination_wear_factor=1.5,     # Low contamination sensitivity
                wear_performance_factor=0.01,      # 1% performance loss per % wear
                lubrication_performance_factor=0.05, # 5% performance loss (reduced)
                wear_alarm_threshold=15.0,         # % wear alarm
                wear_trip_threshold=35.0           # % wear trip
            )
        ]
        
        # Initialize base lubrication system
        super().__init__(config, pump_components)
        
        # Feedwater pump-specific lubrication state
        self.pump_load_factor = 1.0                     # Current pump load factor
        self.cavitation_lubrication_effect = 1.0        # Cavitation effect on lubrication
        self.seal_water_pressure = config.seal_water_system_pressure  # MPa
        self.seal_leakage_rate = 0.0                    # L/min total seal leakage
        
        # Performance tracking (STATE VARIABLES - stored and tracked over time)
        self.pump_efficiency_degradation = 0.0          # % efficiency degradation
        self.pump_flow_degradation = 0.0                # % flow degradation  
        self.pump_head_degradation = 0.0                # % head degradation
        self.npsh_margin_degradation = 0.0              # NPSH margin loss
        self.vibration_increase = 0.0                   # Vibration increase from wear
        
        # NOTE: Performance factors (pump_efficiency_factor, pump_flow_factor, pump_head_factor)
        # are calculated on-the-fly as properties from the degradation values above.
        # This maintains DRY principles - single source of truth with calculated derived values.
        
        # Calculate initial lubrication effectiveness with proper weighting
        self._calculate_lubrication_effectiveness()
    
    # === PERFORMANCE FACTOR PROPERTIES (Calculated on-the-fly from degradation state) ===
    @property
    def pump_efficiency_factor(self) -> float:
        """Calculate efficiency factor from degradation percentage (single source of truth)"""
        return max(0.5, 1.0 - (self.pump_efficiency_degradation / 100.0))
    
    @property
    def pump_flow_factor(self) -> float:
        """Calculate flow factor from degradation percentage (single source of truth)"""
        return max(0.5, 1.0 - (self.pump_flow_degradation / 100.0))
    
    @property
    def pump_head_factor(self) -> float:
        """Calculate head factor from degradation percentage (single source of truth)"""
        return max(0.7, 1.0 - (self.pump_head_degradation / 100.0))
    
    def _calculate_lubrication_effectiveness(self):
        """
        Calculate lubrication effectiveness with realistic weighting
        
        This method fixes the issue where lubrication effectiveness gets stuck at low values.
        Uses weighted average instead of harsh min() to provide more realistic behavior.
        """
        # Calculate individual factors (0.1 to 1.0 range)
        contamination_factor = max(0.1, 1.0 - self.oil_contamination_level / self.config.contamination_limit)
        acidity_factor = max(0.1, 1.0 - self.oil_acidity_number / self.config.acidity_limit)
        moisture_factor = max(0.1, 1.0 - self.oil_moisture_content / self.config.moisture_limit)
        
        # Additive factors (0.0 to 1.0 range)
        antioxidant_factor = max(0.1, self.antioxidant_level / 100.0)
        aw_factor = max(0.1, self.anti_wear_additive_level / 100.0)
        ci_factor = max(0.1, self.corrosion_inhibitor_level / 100.0)
        
        # WEIGHTED AVERAGE instead of harsh min() - more realistic behavior
        # Contamination and additives are most important for pump lubrication
        self.lubrication_effectiveness = (
            contamination_factor * 0.25 +    # 25% weight - contamination is critical
            antioxidant_factor * 0.20 +      # 20% weight - prevents oil breakdown
            aw_factor * 0.20 +               # 20% weight - critical for bearing protection
            ci_factor * 0.15 +               # 15% weight - prevents corrosion
            acidity_factor * 0.10 +          # 10% weight - secondary indicator
            moisture_factor * 0.10           # 10% weight - secondary indicator
        )
        
        # Ensure reasonable bounds (minimum 10% effectiveness, maximum 100%)
        self.lubrication_effectiveness = max(0.1, min(1.0, self.lubrication_effectiveness))
        
    def get_lubricated_components(self) -> List[str]:
        """Return list of feedwater pump components requiring lubrication"""
        return list(self.components.keys())
    
    def calculate_component_wear(self, component_id: str, operating_conditions: Dict) -> float:
        """
        Calculate wear rate for feedwater pump components with bidirectional wear coupling
        
        Args:
            component_id: Component identifier
            operating_conditions: Operating conditions for the component
            
        Returns:
            Wear rate (%/hour)
        """
        component = self.components[component_id]
        
        # Get operating conditions
        load_factor = operating_conditions.get('load_factor', 1.0)        # 0-2 scale
        speed_factor = operating_conditions.get('speed_factor', 1.0)      # 0-2 scale
        temperature = operating_conditions.get('temperature', 55.0)       # °C
        cavitation_intensity = operating_conditions.get('cavitation_intensity', 0.0)  # 0-1 scale
        
        # === BIDIRECTIONAL WEAR COUPLING FACTORS ===
        # Get current wear levels for coupling calculations
        impeller_wear = self.component_wear.get('impeller', 0.0)
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        max_bearing_wear = max(motor_bearing_wear, pump_bearing_wear, thrust_bearing_wear)
        
        # Component-specific wear calculations with coupling
        if component_id == "impeller":
            # Impeller wear from cavitation, erosion, and bearing-induced effects
            hydraulic_load_factor = load_factor
            cavitation_factor = 1.0 + cavitation_intensity * 3.0  # Cavitation is primary impeller wear mechanism
            temp_factor = max(1.0, (temperature - 80.0) / 40.0)   # High temperature threshold for impeller
            
            # BEARING → IMPELLER COUPLING: Bearing wear causes shaft misalignment affecting impeller
            bearing_coupling_factor = 1.0 + (max_bearing_wear / 100.0) * 0.3  # Up to 30% acceleration
            
            wear_rate = (component.base_wear_rate * 
                        (hydraulic_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        cavitation_factor * temp_factor * bearing_coupling_factor)
            
        elif component_id == "motor_bearings":
            # Motor bearing wear depends on electrical load and speed
            electrical_load_factor = operating_conditions.get('electrical_load_factor', 1.0)
            temp_factor = max(1.0, (temperature - 60.0) / 25.0)
            
            # IMPELLER → BEARING COUPLING: Impeller wear creates unbalanced forces
            impeller_coupling_factor = 1.0 + (impeller_wear / 100.0) * 0.2  # Up to 20% acceleration
            
            wear_rate = (component.base_wear_rate * 
                        (electrical_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        temp_factor * impeller_coupling_factor)
            
        elif component_id == "pump_bearings":
            # Pump bearing wear depends on hydraulic load and cavitation
            hydraulic_load_factor = load_factor
            cavitation_factor = 1.0 + cavitation_intensity * 2.0  # Cavitation increases wear
            temp_factor = max(1.0, (temperature - 50.0) / 30.0)
            
            # IMPELLER → BEARING COUPLING: Impeller wear creates hydraulic imbalance
            impeller_coupling_factor = 1.0 + (impeller_wear / 100.0) * 0.4  # Up to 40% acceleration (highest coupling)
            
            wear_rate = (component.base_wear_rate * 
                        (hydraulic_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        cavitation_factor * temp_factor * impeller_coupling_factor)
            
        elif component_id == "thrust_bearing":
            # Thrust bearing wear depends on axial loads and pump head
            head_factor = operating_conditions.get('head_factor', 1.0)
            axial_load_factor = head_factor * load_factor  # Axial load proportional to head and flow
            
            # IMPELLER → BEARING COUPLING: Impeller wear affects axial thrust balance
            impeller_coupling_factor = 1.0 + (impeller_wear / 100.0) * 0.25  # Up to 25% acceleration
            
            wear_rate = (component.base_wear_rate * 
                        (axial_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        impeller_coupling_factor)
            
        elif component_id == "mechanical_seals":
            # Seal wear depends on pressure differential and seal water quality
            pressure_factor = operating_conditions.get('pressure_factor', 1.0)
            seal_water_quality = operating_conditions.get('seal_water_quality', 1.0)
            
            # Cavitation near seals increases wear dramatically
            cavitation_seal_factor = 1.0 + cavitation_intensity * 5.0
            
            # IMPELLER → SEAL COUPLING: Impeller wear creates flow disturbances affecting seals
            impeller_coupling_factor = 1.0 + (impeller_wear / 100.0) * 0.15  # Up to 15% acceleration
            
            # BEARING → SEAL COUPLING: Bearing wear causes shaft runout affecting seal faces
            bearing_coupling_factor = 1.0 + (max_bearing_wear / 100.0) * 0.2  # Up to 20% acceleration
            
            wear_rate = (component.base_wear_rate * 
                        (pressure_factor ** component.load_wear_exponent) *
                        seal_water_quality * cavitation_seal_factor *
                        impeller_coupling_factor * bearing_coupling_factor)
            
        elif component_id == "coupling_system":
            # Coupling wear depends on misalignment and torque variations
            misalignment_factor = operating_conditions.get('misalignment_factor', 1.0)
            torque_variation = operating_conditions.get('torque_variation', 1.0)
            
            # BEARING → COUPLING COUPLING: Bearing wear increases misalignment
            bearing_coupling_factor = 1.0 + (max_bearing_wear / 100.0) * 0.3  # Up to 30% acceleration
            
            wear_rate = (component.base_wear_rate * misalignment_factor * 
                        torque_variation * (load_factor ** component.load_wear_exponent) *
                        bearing_coupling_factor)
            
        else:
            # Default wear calculation
            wear_rate = component.base_wear_rate * load_factor
        
        # Apply chemistry wear factor if provided
        chemistry_wear_factor = operating_conditions.get('chemistry_wear_factor', 1.0)
        wear_rate *= chemistry_wear_factor
        
        return wear_rate
    
    def get_component_lubrication_requirements(self, component_id: str) -> Dict[str, float]:
        """Get lubrication requirements for specific feedwater pump component"""
        component = self.components[component_id]
        
        return {
            'oil_flow_rate': component.oil_flow_requirement,
            'oil_pressure': component.oil_pressure_requirement,
            'oil_temperature_max': component.oil_temperature_max,
            'contamination_sensitivity': component.contamination_wear_factor,
            'filtration_requirement': 5.0 if 'bearing' in component_id else 10.0  # microns
        }
    
    def calculate_chemistry_degradation_factors(self, chemistry_params: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate chemistry-based degradation factors for lubrication system
        
        Args:
            chemistry_params: Chemistry parameters from water chemistry system
            
        Returns:
            Dictionary with chemistry factors affecting pump performance
        """
        # If no chemistry data provided, use defaults
        if not chemistry_params:
            return {
                'water_aggressiveness': 1.0,
                'particle_content': 1.0,
                'corrosion_factor': 1.0,
                'scaling_factor': 1.0,
                'ph_factor': 1.0
            }
        
        # Extract chemistry parameters
        water_aggressiveness = chemistry_params.get('water_aggressiveness', 1.0)
        particle_content = chemistry_params.get('particle_content', 1.0)
        ph = chemistry_params.get('ph', 9.2)
        scaling_tendency = chemistry_params.get('scaling_tendency', 0.0)
        corrosion_tendency = chemistry_params.get('corrosion_tendency', 7.0)
        
        # Calculate degradation factors
        
        # pH factor (optimal around 9.2 for PWR)
        ph_factor = 1.0 + 0.3 * abs(ph - 9.2)  # Increases wear as pH deviates from optimal
        
        # Scaling factor (positive LSI increases scaling)
        scaling_factor = max(1.0, 1.0 + scaling_tendency * 0.2)  # LSI > 0 increases scaling
        
        # Corrosion factor (higher RSI indicates more corrosive)
        # RSI < 6.5 is corrosive, RSI > 7.5 is scale-forming
        if corrosion_tendency < 6.5:
            corrosion_factor = 1.0 + (6.5 - corrosion_tendency) * 0.1  # More corrosive
        elif corrosion_tendency > 7.5:
            corrosion_factor = 1.0 + (corrosion_tendency - 7.5) * 0.05  # Scale-forming
        else:
            corrosion_factor = 1.0  # Balanced
        
        return {
            'water_aggressiveness': water_aggressiveness,
            'particle_content': particle_content,
            'corrosion_factor': corrosion_factor,
            'scaling_factor': scaling_factor,
            'ph_factor': ph_factor
        }

    def update_comprehensive(self, 
                           operating_conditions: Dict,
                           chemistry_params: Dict = None,
                           dt: float = 1.0) -> Dict[str, float]:
        """
        Comprehensive update method that handles all lubrication effects in one place
        Following DRY principles - single source of truth for all mechanical/chemical effects
        
        Args:
            operating_conditions: Pump operating conditions
            chemistry_params: Water chemistry parameters
            dt: Time step (minutes)
            
        Returns:
            Dictionary with comprehensive lubrication results
        """
        if chemistry_params is None:
            chemistry_params = {}
        
        # Calculate chemistry degradation factors
        chemistry_factors = self.calculate_chemistry_degradation_factors(chemistry_params)
        
        # Enhanced oil temperature calculation with chemistry effects and thermal inertia
        load_factor = operating_conditions.get('load_factor', 1.0)
        electrical_load_factor = operating_conditions.get('electrical_load_factor', 1.0)
        
        # Enhanced base temperature calculation - more realistic range
        base_temp = 45.0 + load_factor * 15.0  # 45-60°C range instead of 40-50°C
        
        # Enhanced motor heat calculation with efficiency losses
        base_motor_heat = electrical_load_factor * 4.0  # Restored from 2.0 to realistic 4.0
        efficiency_loss_heat = (1.0 - self.lubrication_effectiveness) * 3.0  # Poor lube = more heat
        
        # Get bearing wear for friction heat calculation
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        bearing_friction_heat = (motor_bearing_wear + pump_bearing_wear) * 0.1  # Wear generates heat
        
        motor_heat = base_motor_heat + efficiency_loss_heat + bearing_friction_heat
        
        # Chemistry effects on temperature
        chemistry_temp_effect = (chemistry_factors['scaling_factor'] - 1.0) * 5.0  # Scaling increases temperature
        
        # Calculate target temperature
        target_oil_temp = base_temp + motor_heat + chemistry_temp_effect
        target_oil_temp = max(40.0, min(85.0, target_oil_temp))  # Realistic limits: 40-85°C
        
        # Add thermal inertia - oil temperature changes gradually (realistic thermal mass)
        thermal_time_constant = 0.15  # 15% change per time step
        oil_temp = self.oil_temperature * (1.0 - thermal_time_constant) + target_oil_temp * thermal_time_constant
        oil_temp = max(40.0, min(85.0, oil_temp))  # Final bounds check
        
        # Enhanced contamination with chemistry effects
        base_contamination_input = load_factor * 0.05
        
        # Chemistry-based contamination
        chemistry_contamination = (
            (chemistry_factors['particle_content'] - 1.0) * 0.1 +  # Particles increase contamination
            (chemistry_factors['corrosion_factor'] - 1.0) * 0.05   # Corrosion products
        )
        
        total_contamination_input = base_contamination_input + chemistry_contamination
        moisture_input = 0.0005
        
        # Update oil quality with chemistry effects
        oil_results = self.update_oil_quality(
            oil_temp, total_contamination_input, moisture_input, dt / 60.0
        )
        
        # Enhanced component wear with chemistry effects
        enhanced_component_conditions = {}
        for component_id, conditions in operating_conditions.get('component_conditions', {}).items():
            enhanced_conditions = conditions.copy()
            
            # Apply chemistry factors to component conditions
            if component_id in ['motor_bearings', 'pump_bearings', 'thrust_bearing']:
                # Bearing wear affected by corrosion and scaling
                enhanced_conditions['chemistry_wear_factor'] = (
                    chemistry_factors['corrosion_factor'] * chemistry_factors['scaling_factor']
                )
            elif component_id == 'mechanical_seals':
                # Seal wear affected by pH and corrosion
                enhanced_conditions['chemistry_wear_factor'] = (
                    chemistry_factors['corrosion_factor'] * chemistry_factors['ph_factor']
                )
            else:
                enhanced_conditions['chemistry_wear_factor'] = 1.0
            
            enhanced_component_conditions[component_id] = enhanced_conditions
        
        # Update component wear with enhanced conditions
        wear_results = self.update_component_wear(enhanced_component_conditions, dt / 60.0)
        
        # Update pump-specific effects
        pump_results = self.update_pump_lubrication_effects(operating_conditions, dt)
        
        # Calculate performance factors based on wear and oil quality
        self._calculate_pump_performance_factors()
        
        # Return comprehensive results
        return {
            **oil_results,
            **wear_results,
            **pump_results,
            'chemistry_factors': chemistry_factors,
            'comprehensive_update': True
        }

    def update_pump_lubrication_effects(self, 
                                      pump_operating_conditions: Dict,
                                      dt: float) -> Dict[str, float]:
        """
        Update pump-specific lubrication effects
        
        Args:
            pump_operating_conditions: Pump operating conditions
            dt: Time step (minutes)
            
        Returns:
            Dictionary with pump lubrication effects
        """
        # Extract pump conditions
        self.pump_load_factor = pump_operating_conditions.get('load_factor', 1.0)
        cavitation_intensity = pump_operating_conditions.get('cavitation_intensity', 0.0)
        
        # Cavitation effects on lubrication
        # Cavitation creates vibration and shock loads that affect oil film
        self.cavitation_lubrication_effect = max(0.3, 1.0 - cavitation_intensity * 0.5)
        
        # Calculate seal leakage based on seal wear - FIXED: Much more conservative progression
        seal_wear = self.component_wear['mechanical_seals']
        base_seal_leakage = self.seal_leakage_rate  # L/min base leakage (5 mL/min) - realistic baseline for modern seals
        wear_leakage = seal_wear * 0.002  # Additional leakage from wear - FIXED: Reduced from 0.02 to 0.002 (90% reduction)
        cavitation_leakage = cavitation_intensity * 0.001  # Cavitation damages seals - FIXED: Reduced from 0.01 to 0.001 (90% reduction)
        
        # Calculate total leakage with very conservative progression
        total_leakage = base_seal_leakage + wear_leakage + cavitation_leakage
        self.seal_leakage_rate = min(total_leakage, 0.0005)  # Cap at 50 mL/min maximum - FIXED: Reduced from 0.2 to 0.05
        
        # Oil level decreases due to seal leakage
        if self.seal_leakage_rate > 0:
            # Calculate oil lost during this time step
            # seal_leakage_rate is in L/min, dt is in minutes
            oil_lost_liters = self.seal_leakage_rate * dt  # L/min * minutes = L
            oil_loss_percentage = (oil_lost_liters / self.config.oil_reservoir_capacity) * 100.0
            # Reduce the impact by 50% to account for oil makeup systems and more realistic loss
            self.oil_level = max(0.0, self.oil_level - oil_loss_percentage * 0.5)
            
        # Apply bounds checking to prevent oil level exceeding 100%
        self.oil_level = min(100.0, max(0.0, self.oil_level))
        
        # Calculate performance factors with cavitation damage
        cavitation_damage = pump_operating_conditions.get('cavitation_damage', 0.0)
        self._calculate_pump_performance_factors(cavitation_damage)
        
        return {
            'cavitation_lubrication_effect': self.cavitation_lubrication_effect,
            'seal_leakage_rate': self.seal_leakage_rate,
            'pump_efficiency_degradation': self.pump_efficiency_degradation,
            'npsh_margin_degradation': self.npsh_margin_degradation,
            'vibration_increase': self.vibration_increase
        }
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, Any]:
        """
        Clean maintenance execution method for lubrication system
        
        This method handles all lubrication-related maintenance following DRY principles.
        Single source of truth for all oil, wear, and performance maintenance.
        The orchestrator has already made the decision - this just executes it.
        
        Args:
            maintenance_type: Type of maintenance to perform (decided by orchestrator)
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        
        # Set maintenance action flag when maintenance is performed
        if maintenance_type in self.maintenance_action_flags:
            self.maintenance_action_flags[maintenance_type] = True
        self.last_maintenance_action = maintenance_type
        
        # Dictionary mapping maintenance types to their handler methods
        maintenance_handlers = {
            "oil_change": self._perform_oil_change,
            "oil_top_off": self._perform_oil_top_off,
            "bearing_replacement": self._perform_bearing_replacement,
            "seal_replacement": self._perform_seal_replacement,
            "component_overhaul": self._perform_component_overhaul,
            "system_cleaning": self._perform_system_cleaning,
            "bearing_inspection": self._perform_bearing_inspection,
            "impeller_inspection": self._perform_impeller_inspection,
            "impeller_replacement": self._perform_impeller_replacement,
            "lubrication_system_check": self._perform_lubrication_system_check,
            "motor_inspection": self._perform_motor_inspection,
            "oil_analysis": self._perform_oil_analysis,
            "vibration_analysis": self._perform_vibration_analysis
        }
        
        # Execute the appropriate maintenance handler
        if maintenance_type in maintenance_handlers:
            return maintenance_handlers[maintenance_type](**kwargs)
        else:
            # Unknown maintenance type
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f"Unknown maintenance type: {maintenance_type}",
                'findings': "Maintenance type not supported by lubrication system",
                'effectiveness_score': 0.0
            }
    
    def _perform_oil_change(self, **kwargs) -> Dict[str, Any]:
        """
        Complete oil change with comprehensive system restoration
        
        This method resets all oil quality parameters and recalculates
        all performance factors comprehensively.
        """
        # Reset oil quality parameters to like-new condition
        self.oil_level = 100.0
        self.oil_temperature = 40.0
        self.oil_contamination_level = 5.0  # Fresh oil baseline
        self.oil_acidity_number = 0.5  # Fresh oil acidity
        self.oil_moisture_content = 0.02  # Minimal moisture
        
        # Recalculate lubrication effectiveness with fresh oil
        self._calculate_lubrication_effectiveness()
        
        # Recalculate all performance factors comprehensively
        self._calculate_pump_performance_factors()
        
        # Reset seal leakage (fresh oil improves sealing)
        self.seal_leakage_rate = max(0.0, self.seal_leakage_rate * 0.5)
        
        return {
            'success': True,
            'duration_hours': 4.0,
            'work_performed': 'Complete oil change with comprehensive system restoration',
            'findings': 'Oil quality restored to like-new condition, performance factors recalculated',
            'effectiveness_score': 1.0,
            'oil_level_after': self.oil_level,
            'lubrication_effectiveness_after': self.lubrication_effectiveness,
            'next_maintenance_due': 6000.0  # 8 months
        }
    
    def _perform_oil_top_off(self, target_level: float = 95.0, **kwargs) -> Dict[str, Any]:
        """
        Oil top-off with quality improvement
        
        Args:
            target_level: Target oil level percentage
        """
        old_level = self.oil_level
        oil_added = max(0.0, target_level - self.oil_level)
        
        if oil_added > 0:
            # Add fresh oil
            self.oil_level = min(100.0, target_level)
            
            # Fresh oil dilutes contamination
            dilution_factor = oil_added / 100.0
            self.oil_contamination_level *= (1.0 - dilution_factor * 0.5)
            self.oil_acidity_number *= (1.0 - dilution_factor * 0.3)
            self.oil_moisture_content *= (1.0 - dilution_factor * 0.4)
            
            # Recalculate lubrication effectiveness
            self._calculate_lubrication_effectiveness()
            
            # Recalculate performance factors
            self._calculate_pump_performance_factors()
            
            return {
                'success': True,
                'duration_hours': 0.5,
                'work_performed': f'Oil top-off from {old_level:.1f}% to {self.oil_level:.1f}%',
                'findings': f'Added {oil_added:.1f}% fresh oil, improved oil quality',
                'effectiveness_score': 0.8,
                'oil_level_after': self.oil_level,
                'lubrication_effectiveness_after': self.lubrication_effectiveness
            }
        else:
            return {
                'success': True,
                'duration_hours': 0.1,
                'work_performed': 'Oil level check - no top-off needed',
                'findings': f'Oil level already at {self.oil_level:.1f}%',
                'effectiveness_score': 1.0,
                'oil_level_after': self.oil_level
            }
    
    def _perform_bearing_replacement(self, component_id: str = "all", **kwargs) -> Dict[str, Any]:
        """
        Bearing replacement with comprehensive wear reset
        
        Args:
            component_id: Specific bearing to replace or "all"
        """
        components_replaced = []
        if component_id == "all":
            # Replace all bearings
            old_motor_wear = self.component_wear.get('motor_bearings', 0.0)
            old_pump_wear = self.component_wear.get('pump_bearings', 0.0)
            old_thrust_wear = self.component_wear.get('thrust_bearing', 0.0)
            
            self.component_wear['motor_bearings'] = 0.0
            self.component_wear['pump_bearings'] = 0.0
            self.component_wear['thrust_bearing'] = 0.0
            
            components_replaced = ['motor_bearings', 'pump_bearings', 'thrust_bearing']
            total_wear_removed = old_motor_wear + old_pump_wear + old_thrust_wear
            
        elif component_id in ['motor_bearings', 'pump_bearings', 'thrust_bearing']:
            # Replace specific bearing
            old_wear = self.component_wear.get(component_id, 0.0)
            self.component_wear[component_id] = 0.0
            components_replaced = [component_id]
            total_wear_removed = old_wear
        else:
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f'Invalid bearing component: {component_id}',
                'findings': 'Component not found in lubrication system',
                'effectiveness_score': 0.0
            }
        
        # Recalculate lubrication effectiveness and performance factors after bearing replacement
        self._calculate_lubrication_effectiveness()
        self._calculate_pump_performance_factors()
        
        # Reduce vibration from bearing replacement
        self.vibration_increase = max(0.0, self.vibration_increase - total_wear_removed * 0.1)
        
        return {
            'success': True,
            'duration_hours': 8.0,
            'work_performed': f'Bearing replacement: {", ".join(components_replaced)}',
            'findings': f'Replaced bearings, removed {total_wear_removed:.1f}% total wear',
            'performance_improvement': total_wear_removed * 2.0,  # 2% improvement per % wear removed
            'effectiveness_score': 1.0,
            'components_replaced': components_replaced,
            'vibration_reduction': total_wear_removed * 0.1,
            'next_maintenance_due': 17520.0  # 2 years
        }
    
    def _perform_seal_replacement(self, **kwargs) -> Dict[str, Any]:
        """
        Seal replacement with leakage elimination
        """
        old_seal_wear = self.component_wear.get('mechanical_seals', 0.0)
        old_leakage = self.seal_leakage_rate
        
        # Reset seal wear and leakage
        self.component_wear['mechanical_seals'] = 0.0
        self.seal_leakage_rate = 0.0
        
        # Recalculate lubrication effectiveness and performance factors
        self._calculate_lubrication_effectiveness()
        self._calculate_pump_performance_factors()
        
        return {
            'success': True,
            'duration_hours': 6.0,
            'work_performed': 'Mechanical seal replacement',
            'findings': f'Replaced seals with {old_seal_wear:.1f}% wear, eliminated {old_leakage:.3f} L/min leakage',
            'performance_improvement': old_seal_wear * 1.5,  # 1.5% improvement per % wear
            'effectiveness_score': 1.0,
            'seal_wear_removed': old_seal_wear,
            'leakage_eliminated': old_leakage,
            'next_maintenance_due': 8760.0  # 1 year
        }
    
    def _perform_component_overhaul(self, **kwargs) -> Dict[str, Any]:
        """
        Complete component overhaul - reset all wear and restore performance
        """
        # Store old values for reporting
        old_wear_values = self.component_wear.copy()
        old_oil_contamination = self.oil_contamination_level
        old_leakage = self.seal_leakage_rate
        
        # Reset all component wear to zero
        for component_id in self.component_wear:
            self.component_wear[component_id] = 0.0
        
        # Restore oil quality to like-new
        self.oil_level = 100.0
        self.oil_temperature = 40.0
        self.oil_contamination_level = 5.0
        self.oil_acidity_number = 0.5
        self.oil_moisture_content = 0.02
        
        # Reset seal leakage
        self.seal_leakage_rate = 0.0
        
        # Reset vibration
        self.vibration_increase = 0.0
        
        # Recalculate all effectiveness and performance factors
        self._calculate_lubrication_effectiveness()
        self._calculate_pump_performance_factors()
        
        total_wear_removed = sum(old_wear_values.values())
        
        return {
            'success': True,
            'duration_hours': 24.0,
            'work_performed': 'Complete lubrication system overhaul',
            'findings': f'All components overhauled, removed {total_wear_removed:.1f}% total wear, restored oil quality',
            'performance_improvement': 30.0,  # Major improvement from complete overhaul
            'effectiveness_score': 1.0,
            'total_wear_removed': total_wear_removed,
            'oil_quality_restored': True,
            'leakage_eliminated': old_leakage,
            'vibration_eliminated': True,
            'next_maintenance_due': 35040.0  # 4 years
        }
    
    def _perform_system_cleaning(self, **kwargs) -> Dict[str, Any]:
        """
        System cleaning to reduce contamination and improve performance
        """
        old_contamination = self.oil_contamination_level
        
        # Cleaning reduces contamination significantly
        contamination_reduction = min(old_contamination * 0.7, 50.0)  # Remove up to 70% or 50 ppm
        self.oil_contamination_level = max(5.0, old_contamination - contamination_reduction)
        
        # Cleaning also reduces acidity and moisture slightly
        self.oil_acidity_number *= 0.8
        self.oil_moisture_content *= 0.9
        
        # Minor wear reduction from cleaning (removes deposits)
        for component_id in self.component_wear:
            self.component_wear[component_id] = max(0.0, self.component_wear[component_id] - 0.5)
        
        # Recalculate effectiveness and performance
        self._calculate_lubrication_effectiveness()
        self._calculate_pump_performance_factors()
        
        return {
            'success': True,
            'duration_hours': 3.0,
            'work_performed': 'Lubrication system cleaning',
            'findings': f'Reduced contamination by {contamination_reduction:.1f} ppm, minor wear reduction',
            'performance_improvement': contamination_reduction * 0.1,  # 0.1% per ppm reduced
            'effectiveness_score': 0.9,
            'contamination_reduced': contamination_reduction,
            'lubrication_effectiveness_after': self.lubrication_effectiveness,
            'next_maintenance_due': 2190.0  # 3 months
        }
    
    def _perform_bearing_inspection(self, **kwargs) -> Dict[str, Any]:
        """
        Bearing inspection with cleaning and minor wear reduction
        """
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        max_bearing_wear = max(motor_bearing_wear, pump_bearing_wear, thrust_bearing_wear)
        
        # Inspection can detect and partially address minor wear
        if max_bearing_wear > 5.0:
            # Apply 10% improvement from cleaning to all bearings
            self.component_wear['motor_bearings'] *= 0.9
            self.component_wear['pump_bearings'] *= 0.9
            self.component_wear['thrust_bearing'] *= 0.9
            
            # Recalculate performance factors after cleaning
            self._calculate_pump_performance_factors()
            
            new_max_wear = max(
                self.component_wear['motor_bearings'],
                self.component_wear['pump_bearings'],
                self.component_wear['thrust_bearing']
            )
            
            findings = f"Bearing wear: {max_bearing_wear:.1f}% -> {new_max_wear:.1f}% (cleaned)"
            recommendations = ["Monitor bearing wear closely", "Consider replacement if wear exceeds 25%"]
        else:
            findings = f"Bearings in good condition, max wear: {max_bearing_wear:.1f}%"
            recommendations = ["Continue normal operation"]
        
        return {
            'success': True,
            'duration_hours': 4.0,
            'work_performed': 'Bearing inspection with cleaning',
            'findings': findings,
            'recommendations': recommendations,
            'effectiveness_score': 0.9,
            'max_bearing_wear_after': max(
                self.component_wear['motor_bearings'],
                self.component_wear['pump_bearings'],
                self.component_wear['thrust_bearing']
            ),
            'next_maintenance_due': 4380.0  # 6 months
        }
    
    def _perform_impeller_inspection(self, **kwargs) -> Dict[str, Any]:
        """
        Enhanced impeller inspection with explicit impeller wear tracking and coupling analysis
        """
        # Get explicit impeller wear and related component wear
        impeller_wear = self.component_wear.get('impeller', 0.0)
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        max_bearing_wear = max(motor_bearing_wear, pump_bearing_wear, thrust_bearing_wear)
        
        # Calculate coupling effects for assessment
        bearing_to_impeller_coupling = max_bearing_wear * 0.3  # 30% coupling factor
        impeller_to_bearing_coupling = impeller_wear * 0.4    # 40% coupling factor (highest)
        
        # Inspection can detect and partially address minor wear
        if impeller_wear > 3.0 or max_bearing_wear > 5.0:
            # Apply cleaning improvements
            old_impeller_wear = impeller_wear
            old_max_bearing_wear = max_bearing_wear
            
            # Clean impeller (10% improvement)
            self.component_wear['impeller'] = max(0.0, impeller_wear * 0.9)
            
            # Minor bearing cleaning due to reduced impeller loads
            bearing_improvement = 0.5  # 0.5% improvement from reduced impeller loads
            self.component_wear['motor_bearings'] = max(0.0, motor_bearing_wear - bearing_improvement)
            self.component_wear['pump_bearings'] = max(0.0, pump_bearing_wear - bearing_improvement)
            self.component_wear['thrust_bearing'] = max(0.0, thrust_bearing_wear - bearing_improvement)
            
            # Recalculate performance factors after cleaning
            self._calculate_pump_performance_factors()
            
            new_impeller_wear = self.component_wear['impeller']
            new_max_bearing_wear = max(
                self.component_wear['motor_bearings'],
                self.component_wear['pump_bearings'],
                self.component_wear['thrust_bearing']
            )
            
            findings = (f"Impeller wear: {old_impeller_wear:.1f}% → {new_impeller_wear:.1f}% (cleaned). "
                       f"Max bearing wear: {old_max_bearing_wear:.1f}% → {new_max_bearing_wear:.1f}% (improved). "
                       f"Coupling effects: Bearing→Impeller {bearing_to_impeller_coupling:.1f}%, "
                       f"Impeller→Bearing {impeller_to_bearing_coupling:.1f}%")
            
            # Enhanced recommendations based on coupling analysis
            recommendations = []
            if new_impeller_wear > 8.0:
                recommendations.append("Schedule impeller replacement within 3 months")
            elif new_impeller_wear > 5.0:
                recommendations.append("Monitor impeller wear closely")
            
            if new_max_bearing_wear > 10.0:
                recommendations.append("Consider bearing inspection due to impeller coupling effects")
            
            if bearing_to_impeller_coupling > 2.0:
                recommendations.append("Address bearing wear to prevent impeller degradation")
            
            if impeller_to_bearing_coupling > 3.0:
                recommendations.append("Monitor bearing condition due to impeller wear coupling")
            
            if not recommendations:
                recommendations.append("Continue normal operation with routine monitoring")
                
        else:
            findings = (f"Impeller in good condition: wear {impeller_wear:.1f}%, "
                       f"max bearing wear {max_bearing_wear:.1f}%. "
                       f"Minimal coupling effects detected.")
            recommendations = ["Continue normal operation", "Next inspection in 6 months"]
        
        return {
            'success': True,
            'duration_hours': 4.0,
            'work_performed': 'Enhanced impeller inspection with coupling analysis',
            'findings': findings,
            'recommendations': recommendations,
            'effectiveness_score': 0.9,
            'impeller_wear_after': self.component_wear['impeller'],
            'max_bearing_wear_after': max(
                self.component_wear['motor_bearings'],
                self.component_wear['pump_bearings'],
                self.component_wear['thrust_bearing']
            ),
            'bearing_to_impeller_coupling': bearing_to_impeller_coupling,
            'impeller_to_bearing_coupling': impeller_to_bearing_coupling,
            'next_maintenance_due': 4380.0  # 6 months
        }
    
    def _perform_impeller_replacement(self, **kwargs) -> Dict[str, Any]:
        """
        Enhanced impeller replacement with explicit wear tracking and coupling benefits
        """
        # Store old wear values for reporting
        old_impeller_wear = self.component_wear.get('impeller', 0.0)
        old_motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        old_pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        old_thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        
        # Calculate coupling benefits before replacement
        impeller_to_bearing_coupling_reduction = old_impeller_wear * 0.4  # 40% coupling factor
        
        # Reset impeller wear to zero (new impeller)
        self.component_wear['impeller'] = 0.0
        
        # Reduce bearing wear due to eliminated impeller coupling effects
        # New impeller eliminates unbalanced forces and hydraulic disturbances
        bearing_improvement_motor = min(old_motor_bearing_wear, impeller_to_bearing_coupling_reduction * 0.2)
        bearing_improvement_pump = min(old_pump_bearing_wear, impeller_to_bearing_coupling_reduction * 0.4)  # Highest coupling
        bearing_improvement_thrust = min(old_thrust_bearing_wear, impeller_to_bearing_coupling_reduction * 0.25)
        
        self.component_wear['motor_bearings'] = max(0.0, old_motor_bearing_wear - bearing_improvement_motor)
        self.component_wear['pump_bearings'] = max(0.0, old_pump_bearing_wear - bearing_improvement_pump)
        self.component_wear['thrust_bearing'] = max(0.0, old_thrust_bearing_wear - bearing_improvement_thrust)
        
        # Calculate total bearing improvement
        total_bearing_improvement = bearing_improvement_motor + bearing_improvement_pump + bearing_improvement_thrust
        
        # Recalculate performance factors after impeller replacement
        self._calculate_pump_performance_factors()
        
        # Reduce vibration from impeller replacement and bearing improvement
        vibration_reduction_impeller = old_impeller_wear * 0.08  # Direct impeller vibration reduction
        vibration_reduction_bearings = total_bearing_improvement * 0.05  # Bearing improvement vibration reduction
        total_vibration_reduction = vibration_reduction_impeller + vibration_reduction_bearings
        
        self.vibration_increase = max(0.0, self.vibration_increase - total_vibration_reduction)
        
        # Calculate new bearing wear levels for reporting
        new_motor_bearing_wear = self.component_wear['motor_bearings']
        new_pump_bearing_wear = self.component_wear['pump_bearings']
        new_thrust_bearing_wear = self.component_wear['thrust_bearing']
        
        findings = (f"Replaced impeller (wear: {old_impeller_wear:.1f}% → 0%). "
                   f"Bearing improvements from coupling elimination: "
                   f"Motor {old_motor_bearing_wear:.1f}% → {new_motor_bearing_wear:.1f}%, "
                   f"Pump {old_pump_bearing_wear:.1f}% → {new_pump_bearing_wear:.1f}%, "
                   f"Thrust {old_thrust_bearing_wear:.1f}% → {new_thrust_bearing_wear:.1f}%. "
                   f"Total vibration reduction: {total_vibration_reduction:.2f} mm/s")
        
        # Enhanced performance improvement calculation
        base_improvement = 15.0  # Base improvement from new impeller
        coupling_improvement = total_bearing_improvement * 2.0  # Additional improvement from bearing coupling benefits
        total_performance_improvement = base_improvement + coupling_improvement
        
        return {
            'success': True,
            'duration_hours': 8.0,
            'work_performed': 'Enhanced impeller replacement with coupling benefits',
            'findings': findings,
            'performance_improvement': total_performance_improvement,
            'effectiveness_score': 1.0,
            'impeller_wear_removed': old_impeller_wear,
            'bearing_improvements': {
                'motor_bearings': bearing_improvement_motor,
                'pump_bearings': bearing_improvement_pump,
                'thrust_bearing': bearing_improvement_thrust,
                'total': total_bearing_improvement
            },
            'vibration_reduction': total_vibration_reduction,
            'coupling_benefits_realized': True,
            'next_maintenance_due': 17520.0  # 2 years
        }
    
    def _perform_lubrication_system_check(self, **kwargs) -> Dict[str, Any]:
        """
        ENHANCED: Comprehensive lubrication system check with significant improvements
        
        This method performs the routine preventive maintenance task described in the user requirements:
        - Oil Level Check & Top-Off: Adds up to 5% oil if level is below 95%
        - Filter Maintenance: Removes up to 30% of contamination (max 5 ppm) simulating filter cleaning/replacement
        - System Assessment: Evaluates lubrication effectiveness and provides condition-based recommendations
        - Effectiveness Recalculation: Updates overall system performance after improvements
        
        Enhanced from original 10% contamination removal to 30% for more realistic maintenance effectiveness.
        """
        # Store initial conditions for reporting
        initial_oil_level = self.oil_level
        initial_contamination = self.oil_contamination_level
        initial_lubrication_effectiveness = self.lubrication_effectiveness
        initial_antioxidant = self.antioxidant_level
        initial_aw_level = self.anti_wear_additive_level
        
        # === 1. OIL LEVEL CHECK & TOP-OFF ===
        # Adds up to 5% oil if level is below 95%
        oil_added = 0.0
        if self.oil_level < 95.0:
            target_level = min(95.0, self.oil_level + 5.0)
            oil_added = target_level - self.oil_level
            self.oil_level = target_level
            
            # Fresh oil dilution effects (realistic for small amounts)
            if oil_added > 0:
                dilution_factor = oil_added / 100.0
                # Contamination dilution (fresh oil is cleaner)
                contamination_dilution = dilution_factor * 0.5  # 50% improvement factor for small amounts
                self.oil_contamination_level = max(1.0, self.oil_contamination_level * (1.0 - contamination_dilution))
                
                # Minor additive restoration from fresh oil
                additive_boost = dilution_factor * 15.0  # Up to 15% boost for small amounts
                self.antioxidant_level = min(100.0, self.antioxidant_level + additive_boost)
                self.anti_wear_additive_level = min(100.0, self.anti_wear_additive_level + additive_boost * 0.8)
        
        # === 2. FILTER MAINTENANCE ===
        # Enhanced filter cleaning/replacement simulation - removes up to 30% contamination (max 5 ppm)
        contamination_reduction = min(self.oil_contamination_level * 0.3, 5.0)  # ENHANCED: 30% removal, max 5 ppm
        self.oil_contamination_level = max(1.0, self.oil_contamination_level - contamination_reduction)
        
        # Filter replacement also improves filtration efficiency temporarily
        # This simulates the effect of new/clean filters
        # (This effect will be used in the oil quality update method)
        
        # === 3. ADDITIVE TREATMENT ===
        # Minor additive package restoration simulating additive treatment during maintenance
        additive_restoration = 15.0  # 15% restoration
        self.antioxidant_level = min(100.0, self.antioxidant_level + additive_restoration)
        self.anti_wear_additive_level = min(100.0, self.anti_wear_additive_level + additive_restoration * 0.8)
        self.corrosion_inhibitor_level = min(100.0, self.corrosion_inhibitor_level + additive_restoration * 0.6)
        
        # === 4. PUMP-SPECIFIC COMPONENT MAINTENANCE ===
        # Minor bearing cleaning and adjustment (reduces wear slightly)
        bearing_cleaning_improvement = 0.5  # 0.5% wear reduction from cleaning
        for bearing_id in ['motor_bearings', 'pump_bearings', 'thrust_bearing']:
            if bearing_id in self.component_wear:
                self.component_wear[bearing_id] = max(0.0, self.component_wear[bearing_id] - bearing_cleaning_improvement)
        
        # Seal system minor adjustments (reduces leakage slightly)
        if hasattr(self, 'seal_leakage_rate'):
            self.seal_leakage_rate = max(0.0, self.seal_leakage_rate * 0.9)  # 10% leakage reduction
        
        # === 5. SYSTEM ASSESSMENT & RECALCULATION ===
        # Recalculate lubrication effectiveness after all improvements
        self._calculate_lubrication_effectiveness()
        
        # Calculate total improvements achieved
        oil_level_improvement = self.oil_level - initial_oil_level
        contamination_improvement = initial_contamination - self.oil_contamination_level
        effectiveness_improvement = self.lubrication_effectiveness - initial_lubrication_effectiveness
        antioxidant_improvement = self.antioxidant_level - initial_antioxidant
        aw_improvement = self.anti_wear_additive_level - initial_aw_level
        
        # === 6. CONDITION-BASED RECOMMENDATIONS ===
        current_effectiveness = self.lubrication_effectiveness
        
        if current_effectiveness > 0.90:
            # Excellent condition
            findings = f"Lubrication system in excellent condition (effectiveness: {current_effectiveness:.1%})"
            recommendations = ["Continue normal operation", "Next routine check in 6 months"]
            next_maintenance_hours = 4380.0  # 6 months
            
        elif current_effectiveness > 0.80:
            # Good condition
            findings = f"Lubrication system in good condition (effectiveness: {current_effectiveness:.1%})"
            recommendations = [
                "Monitor oil quality trends", 
                "Consider oil analysis in 3 months",
                "Check filter condition at next opportunity"
            ]
            next_maintenance_hours = 2190.0  # 3 months
            
        else:
            # Poor condition - needs attention
            findings = f"Lubrication system needs attention (effectiveness: {current_effectiveness:.1%})"
            recommendations = [
                "Schedule oil change within 1 month", 
                "Investigate contamination sources",
                "Check filtration system performance",
                "Consider component inspection"
            ]
            next_maintenance_hours = 720.0  # 1 month
        
        # Add specific recommendations based on component conditions
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        seal_wear = self.component_wear.get('mechanical_seals', 0.0)
        
        if max(motor_bearing_wear, pump_bearing_wear, thrust_bearing_wear) > 5.0:
            recommendations.append("Monitor bearing condition closely")
        if seal_wear > 3.0:
            recommendations.append("Monitor seal leakage")
        if self.oil_contamination_level > 10.0:
            recommendations.append("Investigate contamination sources")
        
        # Create detailed work performed description
        work_details = []
        work_details.append("Comprehensive lubrication system check")
        if oil_added > 0:
            work_details.append(f"oil top-off (+{oil_added:.1f}%)")
        work_details.append(f"filter maintenance (-{contamination_improvement:.1f} ppm)")
        work_details.append(f"additive treatment (+{antioxidant_improvement:.0f}% AO)")
        work_details.append("bearing cleaning and adjustment")
        work_details.append("seal system minor adjustments")
        
        work_performed = f"Performed {', '.join(work_details)}"
        
        # Create detailed findings report
        findings_details = [
            f"Oil level: {initial_oil_level:.1f}% → {self.oil_level:.1f}%",
            f"Contamination: {initial_contamination:.1f} → {self.oil_contamination_level:.1f} ppm",
            f"Effectiveness: {initial_lubrication_effectiveness:.1%} → {current_effectiveness:.1%}",
            f"Antioxidants: {initial_antioxidant:.0f}% → {self.antioxidant_level:.0f}%"
        ]
        
        detailed_findings = f"{findings}. Improvements: {'; '.join(findings_details)}"
        
        return {
            'success': True,
            'duration_hours': 2.0,  # Standard 2-hour maintenance window
            'work_performed': work_performed,
            'findings': detailed_findings,
            'recommendations': recommendations,
            'effectiveness_score': 0.8,  # Good maintenance effectiveness
            
            # Detailed results for tracking
            'oil_level_after': self.oil_level,
            'oil_level_improvement': oil_level_improvement,
            'contamination_after': self.oil_contamination_level,
            'contamination_reduced': contamination_improvement,
            'lubrication_effectiveness_after': current_effectiveness,
            'effectiveness_improvement': effectiveness_improvement,
            'antioxidant_level_after': self.antioxidant_level,
            'antioxidant_improvement': antioxidant_improvement,
            'aw_level_after': self.anti_wear_additive_level,
            'aw_improvement': aw_improvement,
            'next_maintenance_due': next_maintenance_hours,
            
            # Component-specific results
            'motor_bearing_wear': motor_bearing_wear,
            'pump_bearing_wear': pump_bearing_wear,
            'thrust_bearing_wear': thrust_bearing_wear,
            'seal_wear': seal_wear,
            'seal_leakage_rate': getattr(self, 'seal_leakage_rate', 0.0)
        }
    
    def _perform_motor_inspection(self, **kwargs) -> Dict[str, Any]:
        """
        Motor inspection focusing on electrical and bearing components
        """
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        
        # Motor inspection can detect and partially address motor bearing issues
        if motor_bearing_wear > 3.0:
            # Apply 5% improvement from cleaning and adjustment
            old_wear = motor_bearing_wear
            self.component_wear['motor_bearings'] *= 0.95
            
            # Recalculate performance factors
            self._calculate_pump_performance_factors()
            
            new_wear = self.component_wear['motor_bearings']
            findings = f"Motor bearing wear: {old_wear:.1f}% -> {new_wear:.1f}% (cleaned and adjusted)"
            recommendations = ["Monitor motor bearing condition", "Consider bearing replacement if wear exceeds 20%"]
        else:
            findings = f"Motor in good condition, bearing wear: {motor_bearing_wear:.1f}%"
            recommendations = ["Continue normal operation"]
        
        return {
            'success': True,
            'duration_hours': 3.0,
            'work_performed': 'Motor inspection with bearing cleaning and adjustment',
            'findings': findings,
            'recommendations': recommendations,
            'effectiveness_score': 0.9,
            'motor_bearing_wear_after': self.component_wear['motor_bearings'],
            'next_maintenance_due': 4380.0  # 6 months
        }
    
    def _perform_oil_analysis(self, **kwargs) -> Dict[str, Any]:
        """
        Oil analysis and quality assessment
        """
        oil_contamination = self.oil_contamination_level
        oil_acidity = self.oil_acidity_number
        oil_moisture = self.oil_moisture_content
        lubrication_effectiveness = self.lubrication_effectiveness
        
        # Determine oil condition and recommendations
        if oil_contamination > 20.0:
            condition = "Poor - High contamination"
            recommendations = ["Immediate oil change required", "Investigate contamination source"]
            effectiveness = 0.6
        elif oil_contamination > 15.0:
            condition = "Fair - Elevated contamination"
            recommendations = ["Schedule oil change within 1 month", "Monitor contamination trends"]
            effectiveness = 0.8
        elif oil_contamination > 10.0:
            condition = "Good - Normal contamination"
            recommendations = ["Continue monitoring", "Next oil change in 3-6 months"]
            effectiveness = 0.9
        else:
            condition = "Excellent - Low contamination"
            recommendations = ["Continue current maintenance schedule"]
            effectiveness = 1.0
        
        findings = (f"Oil analysis results: Contamination: {oil_contamination:.1f} ppm, "
                   f"Acidity: {oil_acidity:.2f} mg KOH/g, Moisture: {oil_moisture:.3f}%. "
                   f"Overall condition: {condition}")
        
        return {
            'success': True,
            'duration_hours': 1.0,
            'work_performed': 'Comprehensive oil analysis and quality assessment',
            'findings': findings,
            'recommendations': recommendations,
            'effectiveness_score': effectiveness,
            'oil_contamination': oil_contamination,
            'oil_acidity': oil_acidity,
            'oil_moisture': oil_moisture,
            'lubrication_effectiveness': lubrication_effectiveness,
            'next_maintenance_due': 2190.0  # 3 months
        }
    
    def _perform_vibration_analysis(self, **kwargs) -> Dict[str, Any]:
        """
        Vibration analysis to assess mechanical condition
        """
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        vibration_increase = self.vibration_increase
        
        # Calculate overall vibration level
        base_vibration = 1.5  # mm/s baseline
        total_vibration = base_vibration + vibration_increase
        
        # Assess vibration condition
        if total_vibration > 8.0:
            condition = "Severe - Immediate attention required"
            recommendations = ["Stop pump and investigate", "Check bearing condition", "Consider emergency maintenance"]
            effectiveness = 0.5
        elif total_vibration > 5.0:
            condition = "High - Schedule maintenance"
            recommendations = ["Schedule bearing inspection", "Monitor vibration trends", "Reduce load if possible"]
            effectiveness = 0.7
        elif total_vibration > 3.0:
            condition = "Moderate - Monitor closely"
            recommendations = ["Continue monitoring", "Schedule routine bearing inspection"]
            effectiveness = 0.9
        else:
            condition = "Normal - Good mechanical condition"
            recommendations = ["Continue normal operation"]
            effectiveness = 1.0
        
        findings = (f"Vibration analysis: Total vibration: {total_vibration:.1f} mm/s "
                   f"(baseline: {base_vibration:.1f} + wear-induced: {vibration_increase:.1f}). "
                   f"Condition: {condition}")
        
        return {
            'success': True,
            'duration_hours': 2.0,
            'work_performed': 'Comprehensive vibration analysis and mechanical assessment',
            'findings': findings,
            'recommendations': recommendations,
            'effectiveness_score': effectiveness,
            'total_vibration': total_vibration,
            'vibration_increase': vibration_increase,
            'motor_bearing_wear': motor_bearing_wear,
            'pump_bearing_wear': pump_bearing_wear,
            'thrust_bearing_wear': thrust_bearing_wear,
            'next_maintenance_due': 2190.0  # 3 months
        }
    
    def _calculate_pump_performance_factors(self, cavitation_damage=0.0):
        """
        Enhanced performance factor calculation including cavitation effects
        
        This method now consolidates ALL performance degradation sources:
        - Bearing wear effects
        - Seal wear effects  
        - Lubrication quality effects
        - Cavitation damage effects (NEW)
        
        Args:
            cavitation_damage: Cavitation damage from pump system (0-100 scale)
        """
        
        # === MECHANICAL WEAR EFFECTS ===
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        
        # Calculate efficiency losses from mechanical wear
        # FIXED: Convert percentage (0-100) to fractional (0-1) first
        bearing_efficiency_loss = ((motor_bearing_wear / 100.0) * 0.01 + 
                                 (pump_bearing_wear / 100.0) * 0.015 + 
                                 (thrust_bearing_wear / 100.0) * 0.02)
        
        # Seal wear effects
        seal_wear = self.component_wear.get('mechanical_seals', 0.0)
        seal_efficiency_loss = (seal_wear / 100.0) * 0.01  # FIXED: Convert percentage to fractional first
        
        # === LUBRICATION QUALITY EFFECTS ===
        lubrication_efficiency_loss = (1.0 - self.lubrication_effectiveness) * 0.02
        
        # === CAVITATION EFFECTS (NEW - moved from pump system) ===
        cavitation_efficiency_loss = min(0.3, cavitation_damage * 0.01)
        cavitation_flow_loss = cavitation_efficiency_loss * 0.5
        
        # Impeller wear from cavitation (cavitation damages impeller)
        impeller_flow_loss = cavitation_damage * 0.02  # Cavitation erodes impeller
        impeller_efficiency_loss = cavitation_damage * 0.015
        
        # === COMBINED DEGRADATION FACTORS ===
        total_efficiency_loss = (bearing_efficiency_loss + 
                               seal_efficiency_loss + 
                               lubrication_efficiency_loss +
                               cavitation_efficiency_loss +
                               impeller_efficiency_loss)
        
        total_flow_loss = (cavitation_flow_loss + 
                          impeller_flow_loss +
                          bearing_efficiency_loss * 0.3)  # Bearing wear affects flow slightly
        
        total_head_loss = (impeller_flow_loss * 0.8 +  # Impeller wear primarily affects head
                          cavitation_efficiency_loss * 0.4)  # Cavitation reduces head capability
        
        # ENHANCED: Update degradation state variables (properties calculate factors on-the-fly)
        self.pump_efficiency_degradation = min(50.0, total_efficiency_loss * 100.0)  # Cap at 50% degradation
        self.pump_flow_degradation = min(50.0, total_flow_loss * 100.0)              # Cap at 50% degradation  
        self.pump_head_degradation = min(30.0, total_head_loss * 100.0)              # Cap at 30% degradation
        
        # NPSH margin degradation (cavitation damage reduces NPSH margin)
        self.npsh_margin_degradation = cavitation_damage * 0.5  # meters
        
        # Vibration increase from bearing wear and cavitation
        total_bearing_wear = motor_bearing_wear + pump_bearing_wear + thrust_bearing_wear
        bearing_vibration = total_bearing_wear * 0.1  # mm/s per % wear
        cavitation_vibration = cavitation_damage * 0.05  # Cavitation increases vibration
        self.vibration_increase = bearing_vibration + cavitation_vibration
    
    def calculate_heat_flow_contributions(self, pump_work_mw: float, feedwater_temp: float) -> Dict[str, float]:
        """
        Calculate heat flow contributions from lubrication system
        
        This method integrates motor temperature with heat flows to provide
        realistic energy balance and prevent rapid temperature drops.
        
        Args:
            pump_work_mw: Pump mechanical work input (MW)
            feedwater_temp: Current feedwater temperature (°C)
            
        Returns:
            Dictionary with heat flow contributions
        """
        # Motor efficiency losses based on temperature and lubrication
        motor_temp_excess = max(0.0, self.oil_temperature - 50.0)  # Above 50°C baseline
        temp_efficiency_loss = motor_temp_excess * 0.001  # 0.1% loss per °C above 50°C
        
        # Lubrication efficiency losses
        lube_efficiency_loss = (1.0 - self.lubrication_effectiveness) * 0.02  # Up to 2% loss
        
        # Bearing wear efficiency losses
        total_bearing_wear = (self.component_wear.get('motor_bearings', 0.0) + 
                             self.component_wear.get('pump_bearings', 0.0) + 
                             self.component_wear.get('thrust_bearing', 0.0))
        wear_efficiency_loss = total_bearing_wear * 0.0005  # 0.05% loss per % wear
        
        # Total efficiency loss factor
        total_efficiency_loss = 0.02 + temp_efficiency_loss + lube_efficiency_loss + wear_efficiency_loss
        total_efficiency_loss = min(0.15, total_efficiency_loss)  # Cap at 15% loss
        
        # Heat flows from mechanical losses
        mechanical_losses_mw = pump_work_mw * total_efficiency_loss
        motor_heat_to_oil_mw = mechanical_losses_mw * 0.6  # 60% goes to oil heating
        motor_heat_to_feedwater_mw = mechanical_losses_mw * 0.3  # 30% goes to feedwater
        motor_heat_to_ambient_mw = mechanical_losses_mw * 0.1  # 10% lost to ambient
        
        # Feedwater heating from motor (temperature rise calculation)
        if pump_work_mw > 0:
            # Estimate feedwater flow rate (simplified)
            feedwater_flow_rate = pump_work_mw * 50.0  # Rough estimate: 50 kg/s per MW
            feedwater_heating_effect = (motor_heat_to_feedwater_mw * 1000.0) / (feedwater_flow_rate * 4.18)  # °C rise
        else:
            feedwater_heating_effect = 0.0
        
        return {
            'mechanical_losses_mw': mechanical_losses_mw,
            'motor_heat_to_oil_mw': motor_heat_to_oil_mw,
            'motor_heat_to_feedwater_mw': motor_heat_to_feedwater_mw,
            'motor_heat_to_ambient_mw': motor_heat_to_ambient_mw,
            'feedwater_heating_effect_c': feedwater_heating_effect,
            'total_efficiency_loss_factor': total_efficiency_loss,
            'oil_temperature': self.oil_temperature,
            'lubrication_effectiveness': self.lubrication_effectiveness
        }

    def check_protection_trips(self) -> Optional[str]:
        """
        Check lubrication system protection trips
        
        This method handles all lubrication-related protection logic following
        the delegation architecture. Returns trip reason if a trip condition
        is detected, None otherwise.
        
        Returns:
            String with trip reason if trip detected, None if no trips
        """
        # Very low oil level - immediate trip
        if self.oil_level < 5.0:  # Below 5% - FIXED: Reduced from 10.0% to realistic 5%
            return "Very Low Oil Level"
        
        # Low oil level - trip if running (allow startup with low oil)
        if self.oil_level < 10.0:  # Below 10% - FIXED: Reduced from 20.0% to realistic 10%
            return "Low Oil Level"
        
        # High oil level - overfill protection
        if self.oil_level > 105.0:  # Above 105% (impossible overfill)
            return "Oil System Overfill"
        
        # Check component wear limits
        for component_id, wear in self.component_wear.items():
            component = self.components[component_id]
            if wear > component.wear_trip_threshold:
                return f"{component_id.replace('_', ' ').title()} Excessive Wear"
        
        # Seal leakage limit
        if self.seal_leakage_rate > 10.0:  # L/min
            return "Excessive Seal Leakage"
        
        # Combined wear threshold
        total_wear = sum(self.component_wear.values())
        if total_wear > 40.0:  # % total wear
            return "Combined Wear Limit"
        
        # Performance degradation threshold
        efficiency_loss = (1.0 - self.pump_efficiency_factor) * 100.0
        if efficiency_loss > 25.0:  # % efficiency loss
            return "Performance Degradation"
        
        # No trips detected
        return None

    def get_state_dict(self) -> Dict[str, float]:
        """Get pump-specific lubrication state for integration with pump models"""
        
        # NEW: Get explicit impeller wear and individual bearing wear
        impeller_wear = self.component_wear.get('impeller', 0.0)  # FIXED: Use explicit impeller wear
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        seal_wear = self.component_wear.get('mechanical_seals', 0.0)
        
        # Use maximum bearing wear to avoid double-counting
        max_bearing_wear = max(motor_bearing_wear, pump_bearing_wear, thrust_bearing_wear)
        
        # Calculate sum wear (additive approach) - now includes explicit impeller wear
        sum_wear_level = impeller_wear + max_bearing_wear + seal_wear
        
        state_dict = {
            # Oil system state (replaces individual pump oil tracking)
            'oil_level': self.oil_level,
            'oil_temperature': self.oil_temperature,
            'oil_contamination_level': self.oil_contamination_level,
            'oil_acidity_number': self.oil_acidity_number,
            'oil_moisture_content': self.oil_moisture_content,
            'lubrication_effectiveness': self.lubrication_effectiveness,
            
            # Enhanced component wear state with explicit impeller tracking
            'impeller_wear': impeller_wear,  # NEW: Explicit impeller wear
            'motor_bearing_wear': motor_bearing_wear,
            'pump_bearing_wear': pump_bearing_wear,
            'thrust_bearing_wear': thrust_bearing_wear,
            'seal_wear': seal_wear,
            'coupling_wear': self.component_wear.get('coupling_system', 0.0),
            
            # Enhanced sum wear tracking for maintenance system
            'sum_wear_level': sum_wear_level,
            
            # Performance factors (multipliers: 1.0 = perfect, 0.85 = 85% performance)
            'efficiency_factor': self.pump_efficiency_factor,
            'flow_factor': self.pump_flow_factor,
            'head_factor': self.pump_head_factor,
            
            # Seal system state
            'seal_leakage_rate': self.seal_leakage_rate,
            'seal_water_pressure': self.seal_water_pressure,
            
            # Vibration and condition monitoring
            'vibration_increase': self.vibration_increase,
            'npsh_margin_degradation': self.npsh_margin_degradation,
            
            # System health
            'system_health_factor': self.system_health_factor,
            'maintenance_due': self.maintenance_due,
            
            # Maintenance action flags (True or False)
            'maintenance_action_occurred': any(self.maintenance_action_flags.values()),
            **{f'{action}_occurred': flag for action, flag in self.maintenance_action_flags.items()}
        }
        
        # CLEAR FLAGS after including them in state dict (reset to False)
        self.maintenance_action_flags = {key: False for key in self.maintenance_action_flags}
        self.last_maintenance_action = None
        
        return state_dict


# Integration functions for existing feedwater pump models
def integrate_lubrication_with_pump(pump, lubrication_system: FeedwaterPumpLubricationSystem):
    """
    Integrate lubrication system with existing feedwater pump model
    
    This function replaces the individual oil tracking in the pump with
    the comprehensive lubrication system.
    """
    
    def enhanced_update_pump(original_update_method):
        """Wrapper for pump update method to include lubrication effects"""
        
        def update_with_lubrication(dt: float, system_conditions: Dict, 
                                  control_inputs: Dict = None) -> Dict:
            
            # Calculate pump operating conditions for lubrication system
            load_factor = pump.state.flow_rate / pump.config.rated_flow if pump.config.rated_flow > 0 else 0.0
            speed_factor = pump.state.speed_percent / 100.0
            electrical_load_factor = pump.state.power_consumption / pump.config.rated_power if pump.config.rated_power > 0 else 0.0
            
            pump_conditions = {
                'load_factor': load_factor,
                'speed_factor': speed_factor,
                'electrical_load_factor': electrical_load_factor,
                'cavitation_intensity': getattr(pump.state, 'cavitation_intensity', 0.0),
                'head_factor': 1.0,  # Could be calculated from pump curves
                'pressure_factor': pump.state.differential_pressure / 7.5 if hasattr(pump.state, 'differential_pressure') else 1.0,
                'seal_water_quality': 1.0,  # Could be input from system
                'misalignment_factor': 1.0,  # Could be from condition monitoring
                'torque_variation': 1.0  # Could be calculated from load variations
            }
            
            # Component-specific operating conditions
            component_conditions = {
                'motor_bearings': {
                    'load_factor': electrical_load_factor,
                    'speed_factor': speed_factor,
                    'temperature': 60.0 + electrical_load_factor * 25.0,
                    'electrical_load_factor': electrical_load_factor
                },
                'pump_bearings': {
                    'load_factor': load_factor,
                    'speed_factor': speed_factor,
                    'temperature': 50.0 + load_factor * 30.0,
                    'cavitation_intensity': pump_conditions['cavitation_intensity']
                },
                'thrust_bearing': {
                    'load_factor': load_factor,
                    'speed_factor': speed_factor,
                    'temperature': 45.0 + load_factor * 30.0,
                    'head_factor': pump_conditions['head_factor']
                },
                'mechanical_seals': {
                    'load_factor': load_factor,
                    'speed_factor': speed_factor,
                    'temperature': 40.0 + load_factor * 30.0,
                    'pressure_factor': pump_conditions['pressure_factor'],
                    'seal_water_quality': pump_conditions['seal_water_quality'],
                    'cavitation_intensity': pump_conditions['cavitation_intensity']
                },
                'coupling_system': {
                    'load_factor': load_factor,
                    'speed_factor': speed_factor,
                    'temperature': 50.0 + load_factor * 20.0,
                    'misalignment_factor': pump_conditions['misalignment_factor'],
                    'torque_variation': pump_conditions['torque_variation']
                }
            }
            
            # Enhanced oil temperature calculation targeting 55°C normal operation
            # Base temperature reduced to target 55°C at normal load
            base_temp = 40.0 + load_factor * 10.0  # 40-50°C range for main effect
            
            # Motor heat contribution (electrical losses) - reduced impact
            motor_heat = electrical_load_factor * 2.0  # Reduced from 5.0
            
            # Heat transfer from hot feedwater through pump casing - minimal effect due to insulation
            feedwater_temp = system_conditions['feedwater_temperature']
            feedwater_heat_effect = (feedwater_temp - 200.0) * 0.01  # Much reduced, only above 200°C
            
            # Pressure effects (higher pressure = more work = more heat) - reduced impact
            suction_pressure = system_conditions['suction_pressure']
            discharge_pressure = system_conditions['discharge_pressure']
            pressure_ratio = discharge_pressure / suction_pressure if suction_pressure > 0 else 16.0
            pressure_heat = max(0.0, (pressure_ratio - 12.0) * 0.5)  # Much reduced effect
            
            # Cavitation effects (energy dissipation) - reduced impact
            cavitation_heat = pump_conditions['cavitation_intensity'] * 3.0  # Reduced from 8.0
            
            # Calculate target oil temperature with conservative limits
            oil_temp = base_temp + motor_heat + feedwater_heat_effect + pressure_heat + cavitation_heat
            oil_temp = max(35.0, min(75.0, oil_temp))  # More conservative upper limit
            
            # STEP 5: Very conservative pump-specific contamination generation for stable behavior
            # ENHANCED: Ultra-conservative base contamination input reduced to 0.0002 (80% reduction from original)
            base_contamination_input = load_factor * 0.0002  # Very conservative base rate
            
            # Add wear-based contamination generation
            bearing_wear_contamination = 0.0
            seal_wear_contamination = 0.0
            
            # Get current component wear levels
            motor_bearing_wear = lubrication_system.component_wear.get('motor_bearings', 0.0)
            pump_bearing_wear = lubrication_system.component_wear.get('pump_bearings', 0.0)
            thrust_bearing_wear = lubrication_system.component_wear.get('thrust_bearing', 0.0)
            seal_wear = lubrication_system.component_wear.get('mechanical_seals', 0.0)
            
            # ENHANCED: Ultra-conservative bearing wear contamination (reduced rates by 75%)
            bearing_wear_contamination = (motor_bearing_wear + pump_bearing_wear + thrust_bearing_wear) * 0.0005
            
            # ENHANCED: Ultra-conservative seal wear contamination (reduced rate by 75%)
            seal_wear_contamination = seal_wear * 0.0008
            
            # ENHANCED: Ultra-conservative cavitation contamination (reduced rate by 75%)
            cavitation_contamination = pump_conditions['cavitation_intensity'] * 0.002
            
            # ENHANCED: Ultra-conservative temperature contamination (reduced rate by 75%)
            if oil_temp > 75.0:  # Higher threshold for temperature effects
                temp_contamination = (oil_temp - 75.0) * 0.0005
            else:
                temp_contamination = 0.0
            
            # ENHANCED: Add condition-based scaling - better lubrication = less contamination generation
            lubrication_quality_factor = max(0.5, lubrication_system.lubrication_effectiveness)
            contamination_scaling = 1.5 - (lubrication_quality_factor * 0.5)  # 1.0 to 1.25 range (reduced scaling)
            
            # Total contamination input with very conservative bounds and rate limiting
            total_contamination_input = (base_contamination_input + 
                                       bearing_wear_contamination + 
                                       seal_wear_contamination + 
                                       cavitation_contamination + 
                                       temp_contamination) * contamination_scaling
            
            # ENHANCED: Very conservative contamination bounds (cap at 0.05 ppm/hour maximum)
            total_contamination_input = min(0.05, max(0.00005, total_contamination_input))
            
            moisture_input = 0.0001  # Reduced moisture input to realistic level
            
            oil_quality_results = lubrication_system.update_oil_quality(
                oil_temp, total_contamination_input, moisture_input, dt / 60.0  # Convert minutes to hours
            )
            
            # Update component wear
            wear_results = lubrication_system.update_component_wear(
                component_conditions, dt / 60.0  # Convert minutes to hours
            )
            
            # Update pump-specific lubrication effects
            pump_lubrication_results = lubrication_system.update_pump_lubrication_effects(
                pump_conditions, dt  # dt already in minutes for this method
            )
            
            # Get lubrication state for pump integration
            lubrication_state = lubrication_system.get_state_dict()
            
            # UNIDIRECTIONAL UPDATE: Update pump state with lubrication effects (no sync needed)
            # Since we removed duplicate state variables, pump state gets values from lubrication system
            # This is simple value copying, not bidirectional synchronization
            pump.state.oil_level = lubrication_state['oil_level']
            pump.state.oil_temperature = lubrication_state['oil_temperature']
            pump.state.bearing_wear = lubrication_state['pump_bearing_wear']
            pump.state.seal_wear = lubrication_state['seal_wear']
            
            # CRITICAL FIX: Calculate motor temperature from lubrication system data (oil-driven approach)
            # Motor temperature is calculated from actual data sources with physically realistic relationships
            
            # Get values from their actual locations
            oil_temp = lubrication_system.oil_temperature  # From lubrication system (authoritative)
            motor_bearing_wear = lubrication_system.component_wear.get('motor_bearings', 0.0)  # From lubrication system
            lubrication_effectiveness = lubrication_system.lubrication_effectiveness  # From lubrication system
            electrical_load_factor = pump.state.power_consumption / pump.config.rated_power if pump.config.rated_power > 0 else 0.0  # From pump state
            
            # Calculate motor temperature with physically realistic relationships
            base_motor_temp = oil_temp + 8.0  # Motor always runs 8°C above oil baseline (heat transfer)
            electrical_load_effect = electrical_load_factor * 12.0  # 0-12°C from electrical losses (faster response than oil)
            bearing_wear_effect = (motor_bearing_wear / 100.0) * 5.0  # Worn bearings generate more heat (0-5°C)
            poor_lube_effect = (1.0 - lubrication_effectiveness) * 8.0  # Poor lubrication = more friction heat (0-8°C)
            
            # Final motor temperature calculation
            calculated_motor_temp = base_motor_temp + electrical_load_effect + bearing_wear_effect + poor_lube_effect
            calculated_motor_temp = max(45.0, min(120.0, calculated_motor_temp))  # Realistic physical bounds
            
            # Update pump state with calculated motor temperature (this is what maintenance systems use)
            pump.state.motor_temperature = calculated_motor_temp
            
            # Apply performance factors from lubrication system
            pump.state.efficiency_factor = lubrication_state['efficiency_factor']
            pump.state.flow_factor = lubrication_state['flow_factor']
            pump.state.head_factor = lubrication_state['head_factor']
            
            # No sync needed - lubrication system is the single source of truth
            
            # Call original pump update method
            result = original_update_method(dt, system_conditions, control_inputs)
            
            # Add lubrication results to pump output
            result.update({
                'lubrication_effectiveness': lubrication_state['lubrication_effectiveness'],
                'oil_contamination_level': lubrication_state['oil_contamination_level'],
                'system_health_factor': lubrication_state['system_health_factor'],
                'maintenance_due': lubrication_state['maintenance_due'],
                'vibration_increase': lubrication_state['vibration_increase'],
                'npsh_margin_degradation': lubrication_state['npsh_margin_degradation']
            })
            
            return result
        
        return update_with_lubrication
    
    # Replace pump's update method with enhanced version
    pump.update_pump = enhanced_update_pump(pump.update_pump)
    
    # Add lubrication system reference to pump
    pump.lubrication_system = lubrication_system
    
    return pump


# Example usage and testing
if __name__ == "__main__":
    print("Feedwater Pump Lubrication System - Parameter Validation")
    print("=" * 65)
    
    # Create lubrication system configuration
    config = FeedwaterPumpLubricationConfig(
        system_id="FWP-LUB-001",
        oil_reservoir_capacity=150.0,
        pump_rated_power=10.0,
        pump_rated_speed=3600.0,
        pump_rated_flow=555.0
    )
    
    # Create lubrication system
    lubrication_system = FeedwaterPumpLubricationSystem(config)
    
    print(f"Lubrication System ID: {config.system_id}")
    print(f"Oil Reservoir: {config.oil_reservoir_capacity} L")
    print(f"Oil Viscosity Grade: {config.oil_viscosity_grade}")
    print(f"Pump Rated Power: {config.pump_rated_power} MW")
    print(f"Lubricated Components: {len(lubrication_system.components)}")
    for comp_id in lubrication_system.components:
        print(f"  - {comp_id}")
    print()
    
    # Test lubrication system operation
    print("Testing Lubrication System Operation:")
    print(f"{'Time':<6} {'Oil Temp':<10} {'Contamination':<13} {'Effectiveness':<13} {'Health':<8}")
    print("-" * 60)
    
    # Simulate pump operating conditions
    for hour in range(24):
        # Varying load conditions
        if hour < 6:
            load_factor = 0.5 + 0.1 * hour  # Startup
        elif hour < 18:
            load_factor = 1.0  # Full load
        else:
            load_factor = 0.7  # Reduced load
        
        # Component operating conditions
        component_conditions = {
            'motor_bearings': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 60.0 + load_factor * 25.0,
                'electrical_load_factor': load_factor
            },
            'pump_bearings': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 50.0 + load_factor * 30.0,
                'cavitation_intensity': 0.1 if load_factor > 0.9 else 0.0
            },
            'thrust_bearing': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 45.0 + load_factor * 30.0,
                'head_factor': load_factor
            },
            'mechanical_seals': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 40.0 + load_factor * 30.0,
                'pressure_factor': load_factor,
                'seal_water_quality': 1.0,
                'cavitation_intensity': 0.1 if load_factor > 0.9 else 0.0
            },
            'coupling_system': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 50.0 + load_factor * 20.0,
                'misalignment_factor': 1.0,
                'torque_variation': 1.0
            }
        }
        
        # Update lubrication system - using enhanced temperature calculation from integration function
        # Note: In actual integration, temperature is calculated by the enhanced method above
        oil_temp = 45.0 + load_factor * 20.0  # Simplified for testing
        contamination_input = load_factor * 0.05
        moisture_input = 0.0005
        
        oil_results = lubrication_system.update_oil_quality(
            oil_temp, contamination_input, moisture_input, 1.0
        )
        
        wear_results = lubrication_system.update_component_wear(
            component_conditions, 1.0
        )
        
        pump_results = lubrication_system.update_pump_lubrication_effects({
            'load_factor': load_factor,
            'cavitation_intensity': 0.1 if load_factor > 0.9 else 0.0
        }, 1.0)
        
        # Print results every 4 hours
        if hour % 4 == 0:
            print(f"{hour:<6} {oil_results['oil_temperature']:<10.1f} "
                  f"{oil_results['contamination_level']:<13.2f} "
                  f"{oil_results['oil_quality_factor']:<13.3f} "
                  f"{lubrication_system.system_health_factor:<8.3f}")
    
    print()
    print("Final Component Wear Status:")
    for comp_id in lubrication_system.components:
        wear = lubrication_system.component_wear[comp_id]
        performance = lubrication_system
