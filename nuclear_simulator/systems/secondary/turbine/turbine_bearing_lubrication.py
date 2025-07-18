"""
Turbine Bearing Lubrication System

This module implements a comprehensive lubrication system for turbine bearings
using the abstract base lubrication system. It replaces the individual oil
tracking in the rotor dynamics system with a unified lubrication approach.

Key Features:
1. Unified lubrication system for all turbine bearing components
2. Oil quality tracking and degradation modeling
3. Component wear calculation with lubrication effects
4. High-temperature operation modeling
5. Integration with existing turbine rotor dynamics

Physical Basis:
- High-speed turbine bearing lubrication
- High-temperature oil degradation
- Steam environment effects on lubrication
- Journal and thrust bearing oil film dynamics
- Seal oil systems and contamination control
"""

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..lubrication_base import BaseLubricationSystem, BaseLubricationConfig, LubricationComponent
from simulator.state import auto_register
from ..component_descriptions import TURBINE_COMPONENT_DESCRIPTIONS

warnings.filterwarnings("ignore")


@dataclass
class TurbineBearingLubricationConfig(BaseLubricationConfig):
    """
    Configuration for turbine bearing lubrication system
    
    References:
    - ASME TDP-1: Recommended Practices for the Prevention of Water Damage to Steam Turbines
    - API 614: Lubrication, Shaft-Sealing, and Oil-Control Systems for Special-Purpose Applications
    - Steam turbine bearing lubrication specifications
    """
    
    # Override base class defaults for turbine bearing-specific values
    system_id: str = "TB-LUB-001"
    system_type: str = "turbine_bearing"
    oil_reservoir_capacity: float = 800.0       # liters (large capacity for turbine)
    oil_operating_pressure: float = 0.15        # MPa (low pressure for gravity feed)
    oil_temperature_range: Tuple[float, float] = (45.0, 95.0)  # °C high temperature range
    oil_viscosity_grade: str = "ISO VG 46"      # Higher viscosity for high temperature
    
    # Turbine-specific parameters
    turbine_rated_power: float = 1100.0         # MW turbine rated power
    turbine_rated_speed: float = 3600.0         # RPM turbine rated speed
    steam_temperature: float = 280.0            # °C steam temperature
    bearing_housing_temperature: float = 80.0   # °C bearing housing temperature
    
    # Enhanced filtration for steam environment
    filter_micron_rating: float = 5.0           # microns (fine filtration)
    contamination_limit: float = 8.0            # ppm (strict limit for turbine)
    
    # High-temperature operation limits
    oil_temperature_range: Tuple[float, float] = (45.0, 95.0)  # °C extended range
    acidity_limit: float = 0.3                  # mg KOH/g (stricter for high temp)
    
    # Maintenance intervals for critical turbine service
    oil_change_interval: float = 8760.0         # hours (1 year)
    oil_analysis_interval: float = 720.0        # hours (monthly)


@auto_register('SECONDARY', 'turbine', id_source='config.system_id',
               description=TURBINE_COMPONENT_DESCRIPTIONS['turbine_bearing_lubrication'])
class TurbineBearingLubricationSystem(BaseLubricationSystem):
    """
    Turbine bearing-specific lubrication system implementation
    
    This system manages lubrication for all turbine bearing components including:
    1. Journal bearings (high-pressure and low-pressure turbine)
    2. Thrust bearings (axial load management)
    3. Seal oil systems and contamination control
    4. Oil cooling and conditioning systems
    
    Physical Models:
    - High-speed journal bearing lubrication dynamics
    - Thrust bearing oil film pressure distribution
    - High-temperature oil degradation kinetics
    - Steam contamination and moisture ingress
    - Seal oil pressure control and leakage
    """
    
    def __init__(self, config: TurbineBearingLubricationConfig):
        """Initialize turbine bearing lubrication system"""
        
        # Define turbine bearing-specific lubricated components
        turbine_components = [
            LubricationComponent(
                component_id="hp_journal_bearing",
                component_type="bearing",
                oil_flow_requirement=25.0,         # L/min (high flow for large bearing)
                oil_pressure_requirement=0.15,     # MPa
                oil_temperature_max=90.0,          # °C
                base_wear_rate=0.0003,             # %/hour (low wear for journal bearing)
                load_wear_exponent=1.8,            # High load sensitivity
                speed_wear_exponent=1.5,           # High speed sensitivity
                contamination_wear_factor=3.0,     # High contamination sensitivity
                wear_performance_factor=0.02,      # 2% performance loss per % wear
                lubrication_performance_factor=0.5, # 50% performance loss with poor lube
                wear_alarm_threshold=8.0,          # % wear alarm
                wear_trip_threshold=20.0           # % wear trip
            ),
            LubricationComponent(
                component_id="lp_journal_bearing",
                component_type="bearing",
                oil_flow_requirement=30.0,         # L/min (higher flow for larger LP bearing)
                oil_pressure_requirement=0.15,     # MPa
                oil_temperature_max=85.0,          # °C (cooler LP section)
                base_wear_rate=0.0004,             # %/hour (slightly higher wear)
                load_wear_exponent=1.6,            # High load sensitivity
                speed_wear_exponent=1.5,           # High speed sensitivity
                contamination_wear_factor=2.8,     # High contamination sensitivity
                wear_performance_factor=0.018,     # 1.8% performance loss per % wear
                lubrication_performance_factor=0.45, # 45% performance loss
                wear_alarm_threshold=10.0,         # % wear alarm
                wear_trip_threshold=25.0           # % wear trip
            ),
            LubricationComponent(
                component_id="thrust_bearing",
                component_type="bearing",
                oil_flow_requirement=40.0,         # L/min (highest flow for thrust bearing)
                oil_pressure_requirement=0.2,      # MPa (higher pressure for thrust loads)
                oil_temperature_max=80.0,          # °C (strictest for thrust bearing)
                base_wear_rate=0.0006,             # %/hour (higher wear due to axial loads)
                load_wear_exponent=2.5,            # Very high load sensitivity
                speed_wear_exponent=1.3,           # Moderate speed sensitivity
                contamination_wear_factor=4.0,     # Extremely sensitive to contamination
                wear_performance_factor=0.03,      # 3% performance loss per % wear
                lubrication_performance_factor=0.7, # 70% performance loss with poor lube
                wear_alarm_threshold=5.0,          # % wear alarm (very low threshold)
                wear_trip_threshold=15.0           # % wear trip
            ),
            LubricationComponent(
                component_id="seal_oil_system",
                component_type="seal",
                oil_flow_requirement=15.0,         # L/min
                oil_pressure_requirement=0.25,     # MPa (higher pressure for sealing)
                oil_temperature_max=75.0,          # °C
                base_wear_rate=0.0008,             # %/hour (seal wear)
                load_wear_exponent=1.4,            # Moderate load sensitivity
                speed_wear_exponent=1.1,           # Low speed sensitivity
                contamination_wear_factor=3.5,     # Very high contamination sensitivity
                wear_performance_factor=0.025,     # 2.5% performance loss per % wear
                lubrication_performance_factor=0.6, # 60% performance loss
                wear_alarm_threshold=6.0,          # % wear alarm
                wear_trip_threshold=18.0           # % wear trip
            ),
            LubricationComponent(
                component_id="oil_coolers",
                component_type="heat_exchanger",
                oil_flow_requirement=100.0,        # L/min (full system flow)
                oil_pressure_requirement=0.1,      # MPa
                oil_temperature_max=95.0,          # °C
                base_wear_rate=0.0001,             # %/hour (very low wear - no moving parts)
                load_wear_exponent=1.0,            # Low load sensitivity
                speed_wear_exponent=0.5,           # Very low speed sensitivity
                contamination_wear_factor=1.5,     # Low contamination sensitivity
                wear_performance_factor=0.01,      # 1% performance loss per % wear
                lubrication_performance_factor=0.2, # 20% performance loss
                wear_alarm_threshold=20.0,         # % wear alarm
                wear_trip_threshold=40.0           # % wear trip
            )
        ]
        
        # Initialize base lubrication system
        super().__init__(config, turbine_components)
        
        # Turbine-specific lubrication state
        self.turbine_load_factor = 1.0                   # Current turbine load factor
        self.steam_contamination_rate = 0.0              # Steam contamination input
        self.bearing_housing_temperature = config.bearing_housing_temperature  # °C
        self.seal_oil_pressure = 0.25                    # MPa seal oil pressure
        
        # Performance tracking
        self.turbine_efficiency_degradation = 0.0        # Turbine efficiency loss
        self.vibration_increase = 0.0                    # Vibration increase from wear
        self.oil_cooling_effectiveness = 1.0             # Oil cooling system effectiveness
    
    def apply_unified_initial_conditions(self, unified_ics):
        """Apply unified initial conditions to the lubrication system - NO BACKWARD COMPATIBILITY"""
        
        print(f"UNIFIED LUBRICATION: Applying initial conditions")
        
        # System base conditions
        self.oil_base_contamination = unified_ics.oil_base_contamination
        self.oil_base_temperature = unified_ics.oil_base_temperature
        self.oil_base_pressure = unified_ics.oil_base_pressure
        self.oil_base_viscosity = unified_ics.oil_base_viscosity
        self.oil_base_acidity = unified_ics.oil_base_acidity
        self.oil_base_moisture = unified_ics.oil_base_moisture
        self.oil_level = unified_ics.oil_reservoir_level
        
        # Component factors
        self.component_contamination_factors = unified_ics.component_contamination_factors.copy()
        self.component_temperature_offsets = unified_ics.component_temperature_offsets.copy()
        
        # Apply component wear
        for component_id, wear_level in unified_ics.component_wear_levels.items():
            if component_id in self.component_wear:
                self.component_wear[component_id] = wear_level
                
                # Update component performance based on initial wear
                component = self.components[component_id]
                performance_loss = wear_level * component.wear_performance_factor
                self.component_performance_factors[component_id] = max(0.1, 1.0 - performance_loss)
        
        # System performance
        self.pump_efficiency = unified_ics.pump_efficiency
        self.filter_effectiveness = unified_ics.filter_effectiveness
        self.cooler_effectiveness = unified_ics.cooler_effectiveness
        self.system_health_factor = unified_ics.system_health_factor
        
        # Set legacy compatibility values (for existing code that expects them)
        self.oil_contamination_level = self.oil_base_contamination
        self.oil_temperature = self.oil_base_temperature
        
        print(f"  Base contamination: {self.oil_base_contamination:.1f} ppm")
        print(f"  Base temperature: {self.oil_base_temperature:.1f}°C")
        print(f"  Component factors: {self.component_contamination_factors}")
        print(f"  Component wear: {unified_ics.component_wear_levels}")
    
    def get_effective_contamination(self, component_id: str) -> float:
        """Get effective contamination for component"""
        factor = self.component_contamination_factors.get(component_id, 1.0)
        return self.oil_base_contamination * factor
    
    def get_effective_temperature(self, component_id: str) -> float:
        """Get effective temperature for component"""
        offset = self.component_temperature_offsets.get(component_id, 0.0)
        return self.oil_base_temperature + offset
    
    def get_component_conditions(self) -> Dict[str, Dict[str, float]]:
        """Get current conditions for all components"""
        conditions = {}
        
        for component_id in self.components:
            conditions[component_id] = {
                'contamination': self.get_effective_contamination(component_id),
                'temperature': self.get_effective_temperature(component_id),
                'wear_level': self.component_wear.get(component_id, 0.0),
                'performance_factor': self.component_performance_factors.get(component_id, 1.0),
                'lubrication_effectiveness': self.lubrication_effectiveness
            }
        
        return conditions
        
    def get_lubricated_components(self) -> List[str]:
        """Return list of turbine bearing components requiring lubrication"""
        return list(self.components.keys())
    
    def calculate_component_wear(self, component_id: str, operating_conditions: Dict) -> float:
        """
        Calculate wear rate for turbine bearing components
        
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
        temperature = operating_conditions.get('temperature', 70.0)       # °C
        steam_quality = operating_conditions.get('steam_quality', 0.99)   # Steam quality
        
        # Component-specific wear calculations
        if component_id == "hp_journal_bearing":
            # HP journal bearing wear depends on steam conditions and load
            steam_temp_factor = max(1.0, (temperature - 70.0) / 20.0)
            load_factor_adj = load_factor * 1.2  # HP section sees higher loads
            
            wear_rate = (component.base_wear_rate * 
                        (load_factor_adj ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        steam_temp_factor)
            
        elif component_id == "lp_journal_bearing":
            # LP journal bearing wear depends on moisture and load
            moisture_factor = max(1.0, (1.0 - steam_quality) * 10.0)  # Moisture increases wear
            temp_factor = max(1.0, (temperature - 60.0) / 25.0)
            
            wear_rate = (component.base_wear_rate * 
                        (load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        moisture_factor * temp_factor)
            
        elif component_id == "thrust_bearing":
            # Thrust bearing wear depends on axial loads from steam pressure
            steam_pressure_factor = operating_conditions.get('steam_pressure_factor', 1.0)
            axial_load_factor = load_factor * steam_pressure_factor
            temp_factor = max(1.0, (temperature - 50.0) / 30.0)
            
            wear_rate = (component.base_wear_rate * 
                        (axial_load_factor ** component.load_wear_exponent) *
                        (speed_factor ** component.speed_wear_exponent) *
                        temp_factor)
            
        elif component_id == "seal_oil_system":
            # Seal oil system wear depends on pressure differential and contamination
            pressure_diff = operating_conditions.get('pressure_differential', 1.0)
            contamination_factor = 1.0 + self.oil_contamination_level / 10.0
            
            wear_rate = (component.base_wear_rate * 
                        (pressure_diff ** component.load_wear_exponent) *
                        contamination_factor)
            
        elif component_id == "oil_coolers":
            # Oil cooler wear depends on thermal cycling and fouling
            thermal_cycling = operating_conditions.get('thermal_cycling', 1.0)
            fouling_factor = operating_conditions.get('fouling_factor', 1.0)
            
            wear_rate = (component.base_wear_rate * thermal_cycling * fouling_factor)
            
        else:
            # Default wear calculation
            wear_rate = component.base_wear_rate * load_factor
        
        return wear_rate
    
    def get_component_lubrication_requirements(self, component_id: str) -> Dict[str, float]:
        """Get lubrication requirements for specific turbine bearing component"""
        component = self.components[component_id]
        
        return {
            'oil_flow_rate': component.oil_flow_requirement,
            'oil_pressure': component.oil_pressure_requirement,
            'oil_temperature_max': component.oil_temperature_max,
            'contamination_sensitivity': component.contamination_wear_factor,
            'filtration_requirement': 3.0 if 'bearing' in component_id else 5.0  # microns
        }
    
    def update_turbine_lubrication_effects(self, 
                                         turbine_operating_conditions: Dict,
                                         dt: float) -> Dict[str, float]:
        """
        Update turbine-specific lubrication effects
        
        Args:
            turbine_operating_conditions: Turbine operating conditions
            dt: Time step (hours)
            
        Returns:
            Dictionary with turbine lubrication effects
        """
        # Extract turbine conditions
        self.turbine_load_factor = turbine_operating_conditions.get('load_factor', 1.0)
        steam_quality = turbine_operating_conditions.get('steam_quality', 0.99)
        steam_temperature = turbine_operating_conditions.get('steam_temperature', 280.0)
        
        # Steam contamination effects
        # Poor steam quality increases contamination - SMALL FIX: reduced rate
        moisture_contamination = (1.0 - steam_quality) * 0.2  # Reduced from 0.5 to 0.2 ppm/hour
        self.steam_contamination_rate = moisture_contamination
        
        # High temperature effects on oil cooling
        temp_factor = (steam_temperature - 250.0) / 50.0  # Normalized temperature effect
        cooling_degradation = max(0.0, temp_factor * 0.1)  # Up to 10% cooling loss
        self.oil_cooling_effectiveness = max(0.5, 1.0 - cooling_degradation)
        
        # Calculate performance degradation
        self._calculate_turbine_performance_degradation()
        
        return {
            'steam_contamination_rate': self.steam_contamination_rate,
            'oil_cooling_effectiveness': self.oil_cooling_effectiveness,
            'turbine_efficiency_degradation': self.turbine_efficiency_degradation,
            'vibration_increase': self.vibration_increase,
            'bearing_housing_temperature': self.bearing_housing_temperature
        }
    
    def _calculate_turbine_performance_degradation(self):
        """Calculate turbine performance degradation due to lubrication issues"""
        
        # Bearing wear effects on turbine efficiency
        hp_bearing_wear = self.component_wear.get('hp_journal_bearing', 0.0)
        lp_bearing_wear = self.component_wear.get('lp_journal_bearing', 0.0)
        thrust_bearing_wear = self.component_wear.get('thrust_bearing', 0.0)
        
        # Bearing wear increases friction losses
        bearing_efficiency_loss = (hp_bearing_wear * 0.015 + 
                                 lp_bearing_wear * 0.012 + 
                                 thrust_bearing_wear * 0.02)
        
        # Seal oil system effects
        seal_wear = self.component_wear.get('seal_oil_system', 0.0)
        seal_efficiency_loss = seal_wear * 0.008  # Seal wear increases steam leakage
        
        # Oil cooling system effects
        cooler_wear = self.component_wear.get('oil_coolers', 0.0)
        cooling_efficiency_loss = cooler_wear * 0.005
        
        # Lubrication quality effects
        lubrication_efficiency_loss = (1.0 - self.lubrication_effectiveness) * 0.03
        
        # Total turbine efficiency degradation
        self.turbine_efficiency_degradation = (bearing_efficiency_loss + 
                                             seal_efficiency_loss + 
                                             cooling_efficiency_loss +
                                             lubrication_efficiency_loss)
        
        # Vibration increase from bearing wear
        total_bearing_wear = hp_bearing_wear + lp_bearing_wear + thrust_bearing_wear
        self.vibration_increase = total_bearing_wear * 0.05  # mm/s per % wear
        
        # Bearing housing temperature increase from poor lubrication
        lubrication_temp_increase = (1.0 - self.lubrication_effectiveness) * 15.0  # °C
        self.bearing_housing_temperature = 80.0 + lubrication_temp_increase
    
    def setup_maintenance_integration(self, maintenance_system, component_id: str):
        """
        Set up maintenance integration for turbine lubrication system
        
        Args:
            maintenance_system: AutoMaintenanceSystem instance
            component_id: Unique identifier for this lubrication system
        """
        print(f"TURBINE LUBRICATION {component_id}: Setting up maintenance integration")
        
        # Define monitoring configuration for lubrication parameters
        monitoring_config = {
            'oil_contamination': {
                'attribute': 'oil_contamination_level',
                'threshold': 8.0,  # ppm contamination threshold
                'comparison': 'greater_than',
                'action': 'turbine_oil_change',
                'cooldown_hours': 48.0  # 2-day cooldown
            },
            'oil_level': {
                'attribute': 'oil_level',
                'threshold': 30.0,  # % minimum oil level
                'comparison': 'less_than',
                'action': 'turbine_oil_top_off',
                'cooldown_hours': 12.0  # 12-hour cooldown
            },
            'oil_acidity': {
                'attribute': 'oil_acidity_number',
                'threshold': 0.3,  # mg KOH/g acidity limit
                'comparison': 'greater_than',
                'action': 'turbine_oil_change',
                'cooldown_hours': 72.0  # 3-day cooldown
            },
            'oil_temperature': {
                'attribute': 'oil_temperature',
                'threshold': 90.0,  # °C temperature threshold
                'comparison': 'greater_than',
                'action': 'oil_cooler_cleaning',
                'cooldown_hours': 24.0  # Daily cooldown
            },
            'lubrication_effectiveness': {
                'attribute': 'lubrication_effectiveness',
                'threshold': 0.8,  # 80% effectiveness threshold
                'comparison': 'less_than',
                'action': 'lubrication_system_test',
                'cooldown_hours': 168.0  # Weekly cooldown
            }
        }
        
        # Register with maintenance system using event bus
        maintenance_system.register_component(component_id, self, monitoring_config)
        
        print(f"  Registered {component_id} with {len(monitoring_config)} monitoring parameters")
        
        # Store reference for coordination
        self.maintenance_system = maintenance_system
        self.component_id = component_id
    
    def perform_maintenance(self, maintenance_type: str = None, **kwargs):
        """
        Perform maintenance operations on turbine lubrication system
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        if maintenance_type == "turbine_oil_change":
            # Perform complete oil change
            original_contamination = self.oil_contamination_level
            original_acidity = self.oil_acidity_number
            original_moisture = self.oil_moisture_content
            
            # Reset oil quality to new oil standards
            self.oil_contamination_level = 1.0  # Clean oil
            self.oil_acidity_number = 0.05      # Fresh oil acidity
            self.oil_moisture_content = 0.01    # Dry oil
            self.oil_level = 100.0              # Full reservoir
            
            # Improve lubrication effectiveness
            self.lubrication_effectiveness = min(1.0, self.lubrication_effectiveness + 0.15)
            
            # Reduce oil temperature slightly
            self.oil_temperature = max(45.0, self.oil_temperature - 5.0)
            
            # Calculate performance improvement
            contamination_improvement = (original_contamination - self.oil_contamination_level) / max(1.0, original_contamination) * 100.0
            
            return {
                'success': True,
                'duration_hours': 6.0,
                'work_performed': 'Complete turbine oil change and system flush',
                'findings': f"Reduced contamination from {original_contamination:.1f}ppm to {self.oil_contamination_level:.1f}ppm, "
                           f"acidity from {original_acidity:.2f} to {self.oil_acidity_number:.2f} mg KOH/g",
                'performance_improvement': contamination_improvement,
                'effectiveness_score': 0.95,
                'next_maintenance_due': 8760.0,  # Annual
                'parts_used': ['Turbine oil (800L)', 'Oil filters', 'Drain plugs', 'Gaskets']
            }
        
        elif maintenance_type == "turbine_oil_top_off":
            # Perform oil top-off
            original_level = self.oil_level
            oil_added = min(100.0 - self.oil_level, 50.0)  # Add up to 50% or to full
            
            self.oil_level += oil_added
            
            # Slightly improve oil quality with fresh oil addition
            dilution_factor = oil_added / 100.0
            self.oil_contamination_level = max(1.0, self.oil_contamination_level - dilution_factor * 2.0)
            self.oil_acidity_number = max(0.05, self.oil_acidity_number - dilution_factor * 0.1)
            
            return {
                'success': True,
                'duration_hours': 1.0,
                'work_performed': 'Turbine oil top-off completed',
                'findings': f"Added {oil_added:.1f}% oil, level increased from {original_level:.1f}% to {self.oil_level:.1f}%",
                'performance_improvement': (oil_added / max(1.0, original_level)) * 100.0,
                'effectiveness_score': 0.8,
                'next_maintenance_due': 720.0,  # Monthly
                'parts_used': [f'Turbine oil ({oil_added * 8:.0f}L)']
            }
        
        elif maintenance_type == "oil_filter_replacement":
            # Replace oil filters
            original_contamination = self.oil_contamination_level
            
            # Improve filtration effectiveness
            contamination_reduction = min(5.0, self.oil_contamination_level * 0.6)
            self.oil_contamination_level -= contamination_reduction
            self.oil_contamination_level = max(1.0, self.oil_contamination_level)
            
            # Improve lubrication effectiveness
            self.lubrication_effectiveness = min(1.0, self.lubrication_effectiveness + 0.05)
            
            return {
                'success': True,
                'duration_hours': 2.0,
                'work_performed': 'Oil filter replacement completed',
                'findings': f"Reduced contamination from {original_contamination:.1f}ppm to {self.oil_contamination_level:.1f}ppm",
                'performance_improvement': (contamination_reduction / max(1.0, original_contamination)) * 100.0,
                'effectiveness_score': 0.9,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['Oil filter elements (5 units)', 'O-rings', 'Filter housing gaskets']
            }
        
        elif maintenance_type == "oil_cooler_cleaning":
            # Clean oil coolers
            original_temperature = self.oil_temperature
            original_effectiveness = self.oil_cooling_effectiveness
            
            # Improve cooling effectiveness
            self.oil_cooling_effectiveness = min(1.0, self.oil_cooling_effectiveness + 0.15)
            
            # Reduce oil temperature
            temp_reduction = (1.0 - original_effectiveness) * 15.0  # Up to 15°C reduction
            self.oil_temperature = max(45.0, self.oil_temperature - temp_reduction)
            
            # Improve component wear for oil coolers
            if 'oil_coolers' in self.component_wear:
                self.component_wear['oil_coolers'] = max(0.0, self.component_wear['oil_coolers'] - 5.0)
            
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': 'Oil cooler cleaning and inspection completed',
                'findings': f"Improved cooling effectiveness from {original_effectiveness:.2f} to {self.oil_cooling_effectiveness:.2f}, "
                           f"reduced oil temperature by {original_temperature - self.oil_temperature:.1f}°C",
                'performance_improvement': ((self.oil_cooling_effectiveness - original_effectiveness) / max(0.1, original_effectiveness)) * 100.0,
                'effectiveness_score': 0.85,
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Cleaning chemicals', 'Tube brushes', 'Gaskets']
            }
        
        elif maintenance_type == "lubrication_system_test":
            # Perform comprehensive lubrication system test
            # Test all components and optimize performance
            original_effectiveness = self.lubrication_effectiveness
            
            # Optimize system performance
            self.lubrication_effectiveness = min(1.0, self.lubrication_effectiveness + 0.1)
            
            # Check and adjust oil flow rates (simulated)
            flow_optimization = 0.05  # 5% flow optimization
            
            # Identify any component issues
            issues_found = []
            recommendations = []
            
            for component_id, wear in self.component_wear.items():
                if wear > 15.0:
                    issues_found.append(f"{component_id}: {wear:.1f}% wear")
                    recommendations.append(f"Schedule {component_id} maintenance")
            
            if self.oil_contamination_level > 6.0:
                issues_found.append(f"Oil contamination: {self.oil_contamination_level:.1f}ppm")
                recommendations.append("Consider oil change")
            
            findings = f"System effectiveness improved from {original_effectiveness:.2f} to {self.lubrication_effectiveness:.2f}"
            if issues_found:
                findings += f". Issues found: {'; '.join(issues_found)}"
            
            return {
                'success': True,
                'duration_hours': 3.0,
                'work_performed': 'Comprehensive lubrication system test and optimization',
                'findings': findings,
                'recommendations': recommendations,
                'performance_improvement': ((self.lubrication_effectiveness - original_effectiveness) / max(0.1, original_effectiveness)) * 100.0,
                'effectiveness_score': 0.9,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['Test equipment', 'Calibration fluids']
            }
        
        elif maintenance_type == "routine_maintenance":
            # Perform routine lubrication system maintenance
            # Minor improvements across all parameters
            self.lubrication_effectiveness = min(1.0, self.lubrication_effectiveness + 0.02)
            self.oil_contamination_level = max(1.0, self.oil_contamination_level - 0.5)
            self.oil_temperature = max(45.0, self.oil_temperature - 1.0)
            
            # Minor component wear reduction
            for component_id in self.component_wear:
                self.component_wear[component_id] = max(0.0, self.component_wear[component_id] - 0.5)
            
            return {
                'success': True,
                'duration_hours': 2.0,
                'work_performed': 'Routine lubrication system maintenance completed',
                'findings': 'General maintenance activities completed, minor improvements achieved',
                'effectiveness_score': 0.7,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['General maintenance supplies', 'Lubricants']
            }
        
        else:
            # Unknown maintenance type
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f'Unknown maintenance type: {maintenance_type}',
                'error_message': f'Maintenance type {maintenance_type} not supported for turbine lubrication system',
                'effectiveness_score': 0.0
            }

    def get_state_dict(self) -> Dict[str, float]:
        """Get turbine-specific lubrication state for integration with turbine models"""
        return {
            # Oil system state (replaces individual bearing oil tracking)
            'oil_level': self.oil_level,
            'oil_temperature': self.oil_temperature,
            'oil_contamination_level': self.oil_contamination_level,
            'oil_acidity_number': self.oil_acidity_number,
            'oil_moisture_content': self.oil_moisture_content,
            'lubrication_effectiveness': self.lubrication_effectiveness,
            
            # Component wear state (replaces individual wear tracking)
            'hp_bearing_wear': self.component_wear.get('hp_journal_bearing', 0.0),
            'lp_bearing_wear': self.component_wear.get('lp_journal_bearing', 0.0),
            'thrust_bearing_wear': self.component_wear.get('thrust_bearing', 0.0),
            'seal_oil_wear': self.component_wear.get('seal_oil_system', 0.0),
            'oil_cooler_wear': self.component_wear.get('oil_coolers', 0.0),
            
            # Performance effects
            'efficiency_degradation_factor': 1.0 - self.turbine_efficiency_degradation,
            'bearing_housing_temperature': self.bearing_housing_temperature,
            'oil_cooling_effectiveness': self.oil_cooling_effectiveness,
            
            # Vibration and condition monitoring
            'vibration_increase': self.vibration_increase,
            'steam_contamination_rate': self.steam_contamination_rate,
            
            # System health
            'system_health_factor': self.system_health_factor,
            'maintenance_due': self.maintenance_due
        }


# Integration functions for existing turbine rotor dynamics models
def integrate_lubrication_with_turbine(turbine_model, lubrication_system: TurbineBearingLubricationSystem):
    """
    Enhanced integration of lubrication system with turbine rotor dynamics model
    
    This function implements proper bidirectional data flow between the lubrication
    system and individual bearing models to prevent NaN oil temperatures.
    """
    
    def enhanced_update_turbine(original_update_method):
        """Enhanced wrapper with proper data flow coordination"""
        
        def update_with_lubrication(*args, **kwargs) -> Dict:
            
            # Extract parameters from args/kwargs
            if len(args) >= 1:
                # Handle positional arguments
                if len(args) >= 6:
                    # Full positional call: applied_torque, target_speed, steam_temperature, steam_thrust, oil_inlet_temperature, oil_contamination, dt
                    applied_torque, target_speed, steam_temperature, steam_thrust, oil_inlet_temperature, oil_contamination = args[:6]
                    dt = args[6] if len(args) > 6 else kwargs.get('dt', 1.0)
                else:
                    # Partial positional call, get remaining from kwargs
                    applied_torque = args[0] if len(args) > 0 else kwargs.get('applied_torque', 0.0)
                    target_speed = args[1] if len(args) > 1 else kwargs.get('target_speed', 3600.0)
                    steam_temperature = args[2] if len(args) > 2 else kwargs.get('steam_temperature', 280.0)
                    steam_thrust = args[3] if len(args) > 3 else kwargs.get('steam_thrust', 100.0)
                    oil_inlet_temperature = args[4] if len(args) > 4 else kwargs.get('oil_inlet_temperature', 40.0)
                    oil_contamination = args[5] if len(args) > 5 else kwargs.get('oil_contamination', 5.0)
                    dt = args[6] if len(args) > 6 else kwargs.get('dt', 1.0)
            else:
                # All keyword arguments
                applied_torque = kwargs.get('applied_torque', 0.0)
                target_speed = kwargs.get('target_speed', 3600.0)
                steam_temperature = kwargs.get('steam_temperature', 280.0)
                steam_thrust = kwargs.get('steam_thrust', 100.0)
                oil_inlet_temperature = kwargs.get('oil_inlet_temperature', 40.0)
                oil_contamination = kwargs.get('oil_contamination', 5.0)
                dt = kwargs.get('dt', 1.0)
            
            # Extract load factor from turbine model if available
            actual_load_factor = 1.0
            if hasattr(turbine_model, 'load_demand'):
                actual_load_factor = turbine_model.load_demand
            elif 'load_demand' in kwargs:
                actual_load_factor = kwargs['load_demand']
            elif hasattr(turbine_model, 'total_power_output') and hasattr(turbine_model.config, 'rated_power_mwe'):
                # Calculate load factor from power output
                if turbine_model.config.rated_power_mwe > 0:
                    actual_load_factor = turbine_model.total_power_output / turbine_model.config.rated_power_mwe
            
            # Create operating conditions dictionary
            operating_conditions = {
                'applied_torque': applied_torque,
                'target_speed': target_speed,
                'steam_temperature': steam_temperature,
                'steam_thrust': steam_thrust,
                'oil_inlet_temperature': oil_inlet_temperature,
                'oil_contamination': oil_contamination,
                'load_factor': actual_load_factor,
                'steam_quality': kwargs.get('steam_quality', 0.99),
                'steam_pressure': kwargs.get('steam_pressure', 6.5)
            }
            
            # PHASE 1: Collect Bearing States for Lubrication Feedback
            bearing_feedback = collect_bearing_states(turbine_model, operating_conditions)
            
            # PHASE 2: Update Lubrication System with Bearing Feedback
            lubrication_results = update_lubrication_with_feedback(
                lubrication_system, bearing_feedback, operating_conditions, dt
            )
            
            # PHASE 3: Inject Lubrication Results into Bearing Models
            inject_lubrication_into_bearings(turbine_model, lubrication_results)
            
            # PHASE 4: Execute Original Rotor Dynamics with Corrected Bearings
            result = original_update_method(*args, **kwargs)
            
            # PHASE 5: Combine Results
            return combine_results(result, lubrication_results)
        
        return update_with_lubrication
    
    # Replace turbine's update method with enhanced version
    if hasattr(turbine_model, 'update_rotor_dynamics'):
        turbine_model.update_rotor_dynamics = enhanced_update_turbine(turbine_model.update_rotor_dynamics)
    elif hasattr(turbine_model, 'update_state'):
        turbine_model.update_state = enhanced_update_turbine(turbine_model.update_state)
    elif hasattr(turbine_model, 'update'):
        turbine_model.update = enhanced_update_turbine(turbine_model.update)
    
    # Add lubrication system reference to turbine
    turbine_model.lubrication_system = lubrication_system
    
    return turbine_model


def collect_bearing_states(turbine_model, operating_conditions: Dict) -> Dict:
    """
    Collect current bearing states for lubrication system feedback
    
    Args:
        turbine_model: Turbine model with rotor dynamics
        operating_conditions: Current operating conditions
        
    Returns:
        Dictionary with bearing feedback data
    """
    bearing_feedback = {}
    
    # Access rotor dynamics from turbine model
    if hasattr(turbine_model, 'rotor_dynamics'):
        rotor_dynamics = turbine_model.rotor_dynamics
    else:
        # Fallback for different model structures
        return {}
    
    # Get current rotor speed
    rotor_speed = getattr(rotor_dynamics, 'rotor_speed', 3600.0)
    
    for bearing_id, bearing in rotor_dynamics.bearings.items():
        # Calculate friction heat generation
        friction_power = calculate_bearing_friction_heat(bearing, rotor_speed)
        
        # Collect bearing operating conditions
        bearing_feedback[bearing_id] = {
            'load_factor': bearing.current_load / max(bearing.config.design_load_capacity, 1.0),
            'speed_factor': rotor_speed / 3600.0,
            'temperature': getattr(bearing, 'metal_temperature', 90.0),
            'friction_heat': friction_power,
            'operating_hours': getattr(bearing, 'operating_hours', 0.0),
            'wear_factor': getattr(bearing, 'wear_factor', 1.0),
            'current_load': bearing.current_load
        }
    
    return bearing_feedback


def calculate_bearing_friction_heat(bearing, rotor_speed: float) -> float:
    """
    Calculate friction heat generation for a bearing
    
    Args:
        bearing: Bearing model instance
        rotor_speed: Current rotor speed (RPM)
        
    Returns:
        Friction heat generation (Watts)
    """
    # Friction power calculation
    load_n = bearing.current_load * 1000.0  # Convert kN to N
    friction_coeff = getattr(bearing.config, 'friction_coefficient', 0.001)
    clearance_m = getattr(bearing.config, 'bearing_clearance', 0.15) / 1000.0  # Convert mm to m
    
    # Angular velocity (rad/s)
    omega = rotor_speed * 2 * np.pi / 60.0
    
    # Friction power (W)
    friction_power = load_n * friction_coeff * omega * clearance_m
    
    return max(0.0, friction_power)


def update_lubrication_with_feedback(lubrication_system: TurbineBearingLubricationSystem,
                                   bearing_feedback: Dict,
                                   operating_conditions: Dict,
                                   dt: float) -> Dict:
    """
    Update lubrication system with bearing feedback
    
    Args:
        lubrication_system: Lubrication system instance
        bearing_feedback: Bearing state feedback
        operating_conditions: Operating conditions
        dt: Time step (hours)
        
    Returns:
        Dictionary with lubrication results
    """
    # Convert bearing feedback to lubrication system format
    component_conditions = map_bearing_to_lubrication_components(bearing_feedback)
    
    # Calculate system oil temperature based on bearing heat generation
    total_heat_generation = sum(
        feedback['friction_heat'] for feedback in bearing_feedback.values()
    )
    
    # Base oil temperature calculation - adjusted for realistic nuclear turbine range
    load_factor = operating_conditions.get('load_factor', 1.0)
    base_oil_temp = 40.0 + load_factor * 15.0  # °C (40-55°C range)
    
    # Heat-based temperature rise
    if total_heat_generation > 0:
        # Assume 100 L/min total oil flow, 0.85 kg/L density, 2000 J/kg/K heat capacity
        oil_mass_flow = 100.0 / 60.0 * 0.85  # kg/s
        temp_rise = total_heat_generation / (oil_mass_flow * 2000.0)  # °C
        system_oil_temp = base_oil_temp + temp_rise
    else:
        system_oil_temp = base_oil_temp
    
    # Update lubrication system
    steam_quality = operating_conditions.get('steam_quality', 0.99)
    contamination_input = load_factor * 0.02 + (1.0 - steam_quality) * 0.5
    moisture_input = (1.0 - steam_quality) * 0.01
    
    oil_quality_results = lubrication_system.update_oil_quality(
        system_oil_temp, contamination_input, moisture_input, dt
    )
    
    # Update component wear with bearing feedback
    wear_results = lubrication_system.update_component_wear(
        component_conditions, dt
    )
    
    # Calculate component-specific oil temperatures
    component_oil_temps = calculate_component_oil_temperatures(
        lubrication_system, bearing_feedback, system_oil_temp
    )
    
    return {
        'oil_quality': oil_quality_results,
        'component_wear': wear_results,
        'component_oil_temps': component_oil_temps,
        'system_oil_temp': system_oil_temp,
        'lubrication_state': lubrication_system.get_state_dict()
    }


def map_bearing_to_lubrication_components(bearing_feedback: Dict) -> Dict:
    """
    Map bearing feedback to lubrication system component format
    
    Args:
        bearing_feedback: Bearing state feedback
        
    Returns:
        Component conditions for lubrication system
    """
    # Component mapping
    bearing_to_component = {
        'TB-001': 'hp_journal_bearing',
        'TB-002': 'lp_journal_bearing',
        'TB-003': 'thrust_bearing',
        'TB-004': 'seal_oil_system'
    }
    
    component_conditions = {}
    for bearing_id, feedback in bearing_feedback.items():
        component_id = bearing_to_component.get(bearing_id)
        if component_id:
            component_conditions[component_id] = {
                'load_factor': feedback['load_factor'],
                'speed_factor': feedback['speed_factor'],
                'temperature': feedback['temperature'],
                'steam_quality': 0.99,  # Default steam quality
                'steam_pressure_factor': 1.0,  # Default pressure factor
                'pressure_differential': 1.0,  # Default for seals
                'thermal_cycling': feedback['load_factor'],
                'fouling_factor': 1.0  # Default fouling
            }
    
    return component_conditions


def calculate_component_oil_temperatures(lubrication_system: TurbineBearingLubricationSystem,
                                       bearing_feedback: Dict,
                                       base_oil_temp: float) -> Dict:
    """
    Calculate realistic oil temperature for each component based on heat generation and thermal modeling
    
    Args:
        lubrication_system: Lubrication system instance
        bearing_feedback: Bearing feedback data
        base_oil_temp: Base system oil temperature (°C)
        
    Returns:
        Dictionary with component oil temperatures
    """
    component_temps = {}
    
    # Component mapping
    bearing_to_component = {
        'TB-001': 'hp_journal_bearing',
        'TB-002': 'lp_journal_bearing',
        'TB-003': 'thrust_bearing',
        'TB-004': 'seal_oil_system'
    }
    
    for bearing_id, feedback in bearing_feedback.items():
        component_id = bearing_to_component.get(bearing_id)
        if component_id and component_id in lubrication_system.components:
            
            # Get component oil flow requirement
            component = lubrication_system.components[component_id]
            oil_flow_lpm = component.oil_flow_requirement  # L/min
            
            # Calculate temperature rise for this component using corrected heat generation
            heat_generation = feedback['friction_heat']  # Watts (now corrected from rotor_dynamics)
            
            if oil_flow_lpm > 0 and heat_generation > 0:
                # Convert flow to mass flow (kg/s)
                oil_mass_flow = oil_flow_lpm / 60.0 * 0.85  # kg/s
                
                # Enhanced temperature rise calculation with heat transfer modeling
                heat_capacity = 2000.0  # J/kg/K for turbine oil
                
                # Basic temperature rise from heat generation
                temp_rise_basic = heat_generation / (oil_mass_flow * heat_capacity)  # °C
                
                # Apply heat transfer corrections
                # 1. Heat dissipation to bearing housing (convection)
                housing_temp = 80.0  # °C typical bearing housing temperature
                convection_coefficient = 50.0  # W/m²/K typical for oil-metal interface
                bearing_surface_area = 0.5  # m² typical bearing surface area
                
                heat_dissipated = convection_coefficient * bearing_surface_area * max(0, temp_rise_basic)
                net_heat = max(0, heat_generation - heat_dissipated)
                
                # Corrected temperature rise
                if net_heat > 0:
                    temp_rise = net_heat / (oil_mass_flow * heat_capacity)
                else:
                    temp_rise = 0.0
                
                # Apply realistic limits based on component type
                if component_id == 'hp_journal_bearing':
                    max_temp_rise = 25.0  # °C (HP section runs hotter)
                elif component_id == 'thrust_bearing':
                    max_temp_rise = 20.0  # °C (thrust bearings are critical)
                elif component_id == 'seal_oil_system':
                    max_temp_rise = 15.0  # °C (seals are cooler)
                else:
                    max_temp_rise = 20.0  # °C (LP bearings)
                
                temp_rise = min(max_temp_rise, max(0.0, temp_rise))
                
                # Component oil temperature with realistic thermal modeling
                component_oil_temp = base_oil_temp + temp_rise
                
                # Apply component-specific temperature adjustments
                if component_id == 'hp_journal_bearing':
                    # HP bearings run slightly hotter due to steam conditions
                    component_oil_temp += 2.0
                elif component_id == 'thrust_bearing':
                    # Thrust bearings have higher heat generation
                    component_oil_temp += 1.0
                elif component_id == 'seal_oil_system':
                    # Seal oil systems are typically cooler
                    component_oil_temp -= 5.0
                
                # Final temperature validation (realistic turbine bearing oil temps: 35-70°C)
                component_temps[component_id] = max(35.0, min(70.0, component_oil_temp))
                
            else:
                # No heat generation or flow - use base temperature with small offset
                if component_id == 'hp_journal_bearing':
                    component_temps[component_id] = base_oil_temp + 2.0
                elif component_id == 'thrust_bearing':
                    component_temps[component_id] = base_oil_temp + 1.0
                elif component_id == 'seal_oil_system':
                    component_temps[component_id] = base_oil_temp - 5.0
                else:
                    component_temps[component_id] = base_oil_temp
                
                # Ensure within realistic range
                component_temps[component_id] = max(35.0, min(70.0, component_temps[component_id]))
    
    return component_temps


def inject_lubrication_into_bearings(turbine_model, lubrication_results: Dict):
    """
    Inject lubrication system results into bearing models
    
    Args:
        turbine_model: Turbine model with rotor dynamics
        lubrication_results: Results from lubrication system update
    """
    # Access rotor dynamics
    if not hasattr(turbine_model, 'rotor_dynamics'):
        return
    
    rotor_dynamics = turbine_model.rotor_dynamics
    
    # Component mapping
    bearing_to_component = {
        'TB-001': 'hp_journal_bearing',
        'TB-002': 'lp_journal_bearing',
        'TB-003': 'thrust_bearing',
        'TB-004': 'seal_oil_system'
    }
    
    component_oil_temps = lubrication_results.get('component_oil_temps', {})
    lubrication_state = lubrication_results.get('lubrication_state', {})
    
    for bearing_id, bearing in rotor_dynamics.bearings.items():
        component_id = bearing_to_component.get(bearing_id)
        
        if component_id and component_id in component_oil_temps:
            # Get oil temperature from lubrication system
            oil_temp = component_oil_temps[component_id]
            
            # Get oil flow rate from lubrication requirements
            oil_flow = 25.0  # Default flow rate
            if hasattr(turbine_model, 'bearing_lubrication_system'):
                lubrication_system = turbine_model.bearing_lubrication_system
                if component_id in lubrication_system.components:
                    component = lubrication_system.components[component_id]
                    oil_flow = component.oil_flow_requirement
            
            # Create oil quality dictionary
            oil_quality = {
                'contamination': lubrication_state.get('oil_contamination_level', 5.0),
                'effectiveness': lubrication_state.get('lubrication_effectiveness', 1.0)
            }
            
            # Use the set_lubrication_state method to properly inject the data
            bearing.set_lubrication_state(oil_temp, oil_flow, oil_quality)
            
            # Update bearing efficiency based on lubrication effectiveness
            lubrication_effectiveness = lubrication_state.get('lubrication_effectiveness', 1.0)
            bearing.efficiency_factor = min(
                getattr(bearing, 'efficiency_factor', 1.0), 
                lubrication_effectiveness
            )


def combine_results(rotor_results: Dict, lubrication_results: Dict) -> Dict:
    """
    Combine rotor dynamics and lubrication results
    
    Args:
        rotor_results: Results from rotor dynamics update
        lubrication_results: Results from lubrication system update
        
    Returns:
        Combined results dictionary
    """
    # Handle case where rotor_results might be None
    if rotor_results is None:
        combined = {}
    else:
        combined = rotor_results.copy()
    
    # Add lubrication system results
    lubrication_state = lubrication_results.get('lubrication_state', {})
    
    combined.update({
        'lubrication_effectiveness': lubrication_state.get('lubrication_effectiveness', 1.0),
        'oil_contamination_level': lubrication_state.get('oil_contamination_level', 0.0),
        'oil_temperature': lubrication_results.get('system_oil_temp', 60.0),
        'bearing_housing_temperature': lubrication_state.get('bearing_housing_temperature', 80.0),
        'system_health_factor': lubrication_state.get('system_health_factor', 1.0),
        'maintenance_due': lubrication_state.get('maintenance_due', False),
        'vibration_increase': lubrication_state.get('vibration_increase', 0.0),
        'oil_cooling_effectiveness': lubrication_state.get('oil_cooling_effectiveness', 1.0),
        'hp_bearing_wear': lubrication_state.get('hp_bearing_wear', 0.0),
        'lp_bearing_wear': lubrication_state.get('lp_bearing_wear', 0.0),
        'thrust_bearing_wear': lubrication_state.get('thrust_bearing_wear', 0.0)
    })
    
    return combined


# Example usage and testing
if __name__ == "__main__":
    print("Turbine Bearing Lubrication System - Parameter Validation")
    print("=" * 65)
    
    # Create lubrication system configuration
    config = TurbineBearingLubricationConfig(
        system_id="TB-LUB-001",
        oil_reservoir_capacity=800.0,
        turbine_rated_power=1100.0,
        turbine_rated_speed=3600.0,
        steam_temperature=280.0
    )
    
    # Create lubrication system
    lubrication_system = TurbineBearingLubricationSystem(config)
    
    print(f"Lubrication System ID: {config.system_id}")
    print(f"Oil Reservoir: {config.oil_reservoir_capacity} L")
    print(f"Oil Viscosity Grade: {config.oil_viscosity_grade}")
    print(f"Turbine Rated Power: {config.turbine_rated_power} MW")
    print(f"Steam Temperature: {config.steam_temperature} °C")
    print(f"Lubricated Components: {len(lubrication_system.components)}")
    for comp_id in lubrication_system.components:
        print(f"  - {comp_id}")
    print()
    
    # Test lubrication system operation
    print("Testing Lubrication System Operation:")
    print(f"{'Time':<6} {'Oil Temp':<10} {'Contamination':<13} {'Effectiveness':<13} {'Health':<8}")
    print("-" * 60)
    
    # Simulate turbine operating conditions
    for hour in range(24):
        # Varying load and steam conditions
        if hour < 4:
            load_factor = 0.3 + 0.2 * hour  # Startup
            steam_quality = 0.95 + 0.01 * hour
        elif hour < 20:
            load_factor = 1.0  # Full load
            steam_quality = 0.99
        else:
            load_factor = 0.8  # Reduced load
            steam_quality = 0.98
        
        # Component operating conditions
        component_conditions = {
            'hp_journal_bearing': {
                'load_factor': load_factor * 1.2,
                'speed_factor': 1.0,
                'temperature': 70.0 + load_factor * 20.0,
                'steam_quality': steam_quality
            },
            'lp_journal_bearing': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 60.0 + load_factor * 25.0,
                'steam_quality': steam_quality
            },
            'thrust_bearing': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 50.0 + load_factor * 30.0,
                'steam_pressure_factor': load_factor
            },
            'seal_oil_system': {
                'load_factor': load_factor,
                'speed_factor': 1.0,
                'temperature': 45.0 + load_factor * 30.0,
                'pressure_differential': load_factor
            },
            'oil_coolers': {
                'load_factor': load_factor,
                'speed_factor': 0.0,
                'temperature': 60.0 + load_factor * 35.0,
                'thermal_cycling': load_factor,
                'fouling_factor': 1.0
            }
        }
        
        # Update lubrication system
        oil_temp = 60.0 + load_factor * 30.0
        contamination_input = load_factor * 0.02 + (1.0 - steam_quality) * 0.5
        moisture_input = (1.0 - steam_quality) * 0.01
        
        oil_results = lubrication_system.update_oil_quality(
            oil_temp, contamination_input, moisture_input, 1.0
        )
        
        wear_results = lubrication_system.update_component_wear(
            component_conditions, 1.0
        )
        
        turbine_results = lubrication_system.update_turbine_lubrication_effects({
            'load_factor': load_factor,
            'steam_quality': steam_quality,
            'steam_temperature': 280.0
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
        performance = lubrication_system.component_performance_factors[comp_id]
        print(f"  {comp_id}: {wear:.3f}% wear, {performance:.3f} performance factor")
    
    print()
    print("Turbine Bearing Lubrication System - Ready for Integration!")
    print("Key Features Implemented:")
    print("- Unified lubrication system for 5 turbine bearing components")
    print("- High-temperature oil degradation modeling")
    print("- Steam contamination and moisture effects")
    print("- Journal and thrust bearing wear modeling")
    print("- Seal oil system performance tracking")
    print("- Oil cooling system effectiveness")
    print("- Integration wrapper for existing turbine models")
