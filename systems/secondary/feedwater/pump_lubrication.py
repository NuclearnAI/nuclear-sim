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
from typing import Dict, List, Optional, Tuple
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
    contamination_limit: float = 12.0           # ppm (moderate limit for pumps)
    
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
        
        # Define feedwater pump-specific lubricated components
        pump_components = [
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
                wear_alarm_threshold=10.0,         # % wear alarm
                wear_trip_threshold=25.0           # % wear trip
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
                wear_alarm_threshold=8.0,          # % wear alarm (lower threshold)
                wear_trip_threshold=20.0           # % wear trip
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
                wear_alarm_threshold=6.0,          # % wear alarm (very low threshold)
                wear_trip_threshold=15.0           # % wear trip
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
                wear_alarm_threshold=5.0,          # % wear alarm (very low threshold)
                wear_trip_threshold=12.0           # % wear trip
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
        
        # Performance tracking
        self.pump_efficiency_degradation = 0.0          # Pump efficiency loss
        self.npsh_margin_degradation = 0.0              # NPSH margin loss
        self.vibration_increase = 0.0                   # Vibration increase from wear
        
    def get_lubricated_components(self) -> List[str]:
        """Return list of feedwater pump components requiring lubrication"""
        return list(self.components.keys())
    
    def calculate_component_wear(self, component_id: str, operating_conditions: Dict) -> float:
        """
        Calculate wear rate for feedwater pump components
        
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
        
        # Component-specific wear calculations
        if component_id == "motor_bearings":
            # Motor bearing wear depends on electrical load and speed
            electrical_load_factor = operating_conditions.get('electrical_load_factor', 1.0)
            temp_factor = max(1.0, (temperature - 60.0) / 25.0)
            
            wear_rate = (component.base_wear_rate * 
                        (electrical_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        temp_factor)
            
        elif component_id == "pump_bearings":
            # Pump bearing wear depends on hydraulic load and cavitation
            hydraulic_load_factor = load_factor
            cavitation_factor = 1.0 + cavitation_intensity * 2.0  # Cavitation increases wear
            temp_factor = max(1.0, (temperature - 50.0) / 30.0)
            
            wear_rate = (component.base_wear_rate * 
                        (hydraulic_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        cavitation_factor * temp_factor)
            
        elif component_id == "thrust_bearing":
            # Thrust bearing wear depends on axial loads and pump head
            head_factor = operating_conditions.get('head_factor', 1.0)
            axial_load_factor = head_factor * load_factor  # Axial load proportional to head and flow
            
            wear_rate = (component.base_wear_rate * 
                        (axial_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent))
            
        elif component_id == "mechanical_seals":
            # Seal wear depends on pressure differential and seal water quality
            pressure_factor = operating_conditions.get('pressure_factor', 1.0)
            seal_water_quality = operating_conditions.get('seal_water_quality', 1.0)
            
            # Cavitation near seals increases wear dramatically
            cavitation_seal_factor = 1.0 + cavitation_intensity * 5.0
            
            wear_rate = (component.base_wear_rate * 
                        (pressure_factor ** component.load_wear_exponent) *
                        seal_water_quality * cavitation_seal_factor)
            
        elif component_id == "coupling_system":
            # Coupling wear depends on misalignment and torque variations
            misalignment_factor = operating_conditions.get('misalignment_factor', 1.0)
            torque_variation = operating_conditions.get('torque_variation', 1.0)
            
            wear_rate = (component.base_wear_rate * misalignment_factor * 
                        torque_variation * (load_factor ** component.load_wear_exponent))
            
        else:
            # Default wear calculation
            wear_rate = component.base_wear_rate * load_factor
        
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
        
        # Calculate seal leakage based on seal wear
        seal_wear = self.component_wear.get('mechanical_seals', 0.0)
        base_seal_leakage = 0.005  # L/min base leakage (5 mL/min) - realistic for modern seals
        wear_leakage = seal_wear * 0.02  # Additional leakage from wear (reduced from 0.8)
        cavitation_leakage = cavitation_intensity * 0.01  # Cavitation damages seals (reduced from 0.5)
        
        # Calculate total leakage and apply realistic maximum cap
        total_leakage = base_seal_leakage + wear_leakage + cavitation_leakage
        self.seal_leakage_rate = min(total_leakage, 0.2)  # Cap at 200 mL/min maximum
        
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
        
        # Calculate performance factors
        self._calculate_pump_performance_factors()
        
        return {
            'cavitation_lubrication_effect': self.cavitation_lubrication_effect,
            'seal_leakage_rate': self.seal_leakage_rate,
            'pump_efficiency_degradation': self.pump_efficiency_degradation,
            'npsh_margin_degradation': self.npsh_margin_degradation,
            'vibration_increase': self.vibration_increase
        }
    
    def _calculate_pump_performance_factors(self):
        """Calculate pump performance factors due to lubrication effects"""
        
        # Bearing wear effects on pump efficiency
        motor_bearing_wear = self.component_wear.get('motor_bearings', 0.0)
        pump_bearing_wear = self.component_wear.get('pump_bearings', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        
        # Calculate efficiency losses (intermediate values)
        bearing_efficiency_loss = (motor_bearing_wear * 0.01 + 
                                 pump_bearing_wear * 0.015 + 
                                 thrust_bearing_wear * 0.02)
        
        # Seal wear effects
        seal_wear = self.component_wear.get('mechanical_seals', 0.0)
        seal_efficiency_loss = seal_wear * 0.01  # Seal wear increases internal leakage
        
        # Lubrication quality effects
        lubrication_efficiency_loss = (1.0 - self.lubrication_effectiveness) * 0.02
        
        # Calculate total efficiency loss
        total_efficiency_loss = (bearing_efficiency_loss + 
                               seal_efficiency_loss + 
                               lubrication_efficiency_loss)
        
        # ENHANCED: Convert losses to factors directly (factor system)
        self.pump_efficiency_factor = max(0.5, 1.0 - total_efficiency_loss)
        self.pump_flow_factor = max(0.5, 1.0 - total_efficiency_loss * 0.5)
        self.pump_head_factor = max(0.7, 1.0 - total_efficiency_loss * 0.3)
        
        # NPSH margin degradation (cavitation damage reduces NPSH margin)
        cavitation_damage = sum(self.component_wear.values()) * 0.1  # Simplified
        self.npsh_margin_degradation = cavitation_damage * 0.5  # meters
        
        # Vibration increase from bearing wear
        total_bearing_wear = motor_bearing_wear + pump_bearing_wear + thrust_bearing_wear
        self.vibration_increase = total_bearing_wear * 0.1  # mm/s per % wear
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get pump-specific lubrication state for integration with pump models"""
        return {
            
            # Oil system state (replaces individual pump oil tracking)
            'oil_level': self.oil_level,
            'oil_temperature': self.oil_temperature,
            'oil_contamination_level': self.oil_contamination_level,
            'oil_acidity_number': self.oil_acidity_number,
            'oil_moisture_content': self.oil_moisture_content,
            'lubrication_effectiveness': self.lubrication_effectiveness,
            
            # Component wear state (replaces individual wear tracking)
            'motor_bearing_wear': self.component_wear.get('motor_bearings', 0.0),
            'pump_bearing_wear': self.component_wear.get('pump_bearings', 0.0),
            'thrust_bearing_wear': self.component_wear.get('thrust_bearing', 0.0),
            'seal_wear': self.component_wear.get('mechanical_seals', 0.0),
            'coupling_wear': self.component_wear.get('coupling_system', 0.0),
            
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
            'maintenance_due': self.maintenance_due
        }


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
            
            # ENHANCED contamination input with wear-based generation
            base_contamination_input = load_factor * 0.05  # Increased from 0.01 to 0.05
            
            # Add wear-based contamination generation
            bearing_wear_contamination = 0.0
            seal_wear_contamination = 0.0
            
            # Get current component wear levels
            motor_bearing_wear = lubrication_system.component_wear.get('motor_bearings', 0.0)
            pump_bearing_wear = lubrication_system.component_wear.get('pump_bearings', 0.0)
            thrust_bearing_wear = lubrication_system.component_wear.get('thrust_bearing', 0.0)
            seal_wear = lubrication_system.component_wear.get('mechanical_seals', 0.0)
            
            # Bearing wear generates metal particles
            bearing_wear_contamination = (motor_bearing_wear + pump_bearing_wear + thrust_bearing_wear) * 0.02
            
            # Seal wear generates rubber/carbon particles
            seal_wear_contamination = seal_wear * 0.03
            
            # Cavitation generates debris
            cavitation_contamination = pump_conditions['cavitation_intensity'] * 0.08
            
            # High temperature accelerates contamination generation
            if oil_temp > 70.0:
                temp_contamination = (oil_temp - 70.0) * 0.02
            else:
                temp_contamination = 0.0
            
            # Total contamination input
            total_contamination_input = (base_contamination_input + 
                                       bearing_wear_contamination + 
                                       seal_wear_contamination + 
                                       cavitation_contamination + 
                                       temp_contamination)
            
            moisture_input = 0.0005  # Increased moisture input
            
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
            
            # BIDIRECTIONAL SYNC: Update pump state with lubrication effects
            pump.state.oil_level = lubrication_state['oil_level']
            pump.state.oil_temperature = lubrication_state['oil_temperature']
            pump.state.bearing_wear = lubrication_state['pump_bearing_wear']
            pump.state.seal_wear = lubrication_state['seal_wear']
            pump.state.seal_leakage = lubrication_state['seal_leakage_rate']
            
            # Apply performance factors
            pump.state.efficiency_factor = lubrication_state['efficiency_factor']
            pump.state.flow_factor = lubrication_state['flow_factor']
            pump.state.head_factor = lubrication_state['head_factor']
            
            # BIDIRECTIONAL SYNC: Check if pump state was manually changed and sync back
            pump.sync_oil_levels_bidirectional("lubrication")
            
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
