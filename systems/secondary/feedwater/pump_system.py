"""
Feedwater Pump System Models

This module provides feedwater pump models and system coordination,
extracted and refactored from the original monolithic feedwater_pumps.py
to follow the modular architecture pattern.

Key Features:
1. Individual pump models with enhanced physics
2. Multi-pump system coordination
3. Load distribution and sequencing
4. Performance monitoring and diagnostics
5. Integration with base pump classes
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import warnings
import time
from simulator.state import auto_register

# Import base classes from primary pump models
from systems.primary.coolant.pump_models import (
    BasePump, BasePumpState, PumpStatus
)

# Import lubrication system components
from .pump_lubrication import (
    FeedwaterPumpLubricationSystem, 
    FeedwaterPumpLubricationConfig, 
    integrate_lubrication_with_pump
)

# Import chemistry flow interfaces
from ..chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies

from ..component_descriptions import FEEDWATER_COMPONENT_DESCRIPTIONS

# Import state management - removed StateProviderMixin to prevent double registration
# The FeedwaterPumpSystem is managed by EnhancedFeedwaterPhysics which handles state collection

warnings.filterwarnings("ignore")


@dataclass
class FeedwaterPumpConfig:
    """Configuration for individual feedwater pump"""
    pump_id: str = "FWP-1"                      # Pump identifier
    rated_flow: float = 555.0                   # kg/s rated flow per pump
    rated_power: float = 10.0                   # MW rated power
    rated_head: float = 1200.0                  # m rated head
    min_speed: float = 30.0                     # % minimum speed (was 0.0)
    max_speed: float = 110.0                    # % maximum speed
    speed_ramp_rate: float = 15.0               # %/s speed ramp rate
    startup_time: float = 20.0                  # seconds startup time
    coastdown_time: float = 60.0                # seconds coastdown time
    auto_start_enabled: bool = True             # Enable automatic startup
    min_flow_for_start: float = 50.0            # kg/s minimum flow to start


@dataclass
class FeedwaterPumpState(BasePumpState):
    """State of a single feedwater pump - inherits from base"""
    # Feedwater-specific defaults
    flow_rate: float = 555.0                    # Actual flow rate (kg/s)
    power_consumption: float = 10.0             # Motor power (MW)
    
    # Feedwater-specific state variables
    suction_pressure: float = 0.5               # MPa suction pressure
    discharge_pressure: float = 8.0             # MPa discharge pressure
    npsh_available: float = 20.0                # m Net Positive Suction Head available
    
    # Enhanced monitoring (pump-specific only)
    motor_temperature: float = 60.0             # °C motor temperature (electrical windings)
    motor_current: float = 0.0                  # A motor current
    motor_voltage: float = 6.6                  # kV motor voltage
    vibration_level: float = 1.5                # mm/s vibration level (combined signature)
    differential_pressure: float = 0.0          # MPa differential pressure
    
    # Enhanced Cavitation Modeling (pump hydraulic specific)
    cavitation_intensity: float = 0.0           # 0-1 scale cavitation intensity
    cavitation_damage: float = 0.0              # Accumulated damage (0-100 scale)
    cavitation_time: float = 0.0                # Time spent cavitating (seconds)
    cavitation_noise_level: float = 0.0         # Additional noise from cavitation (dB)
    
    # DELEGATION ARCHITECTURE - NO DUPLICATE STATE VARIABLES:
    # All lubrication data (oil_level, oil_temperature, bearing_temperature, 
    # bearing_wear, seal_wear, impeller_wear, efficiency_factor, flow_factor, 
    # head_factor) is accessed directly from lubrication_system when needed.
    # This ensures single source of truth and eliminates state duplication.


@auto_register("SECONDARY", "feedwater", id_source="config.pump_id",
               description=FEEDWATER_COMPONENT_DESCRIPTIONS['feedwater_pump'])
class FeedwaterPump(BasePump):
    """
    Enhanced feedwater pump model
    
    This model emphasizes:
    1. High head operation for steam generator injection
    2. Variable speed control for level regulation
    3. NPSH protection for cavitation prevention
    4. Integration with steam generator level control
    5. Advanced diagnostics and wear modeling
    """
    
    def __init__(self, config: FeedwaterPumpConfig):
        """Initialize feedwater pump with configuration"""
        # Initialize base pump with feedwater-specific parameters
        BasePump.__init__(self, config.pump_id, "feedwater", config.rated_flow, FeedwaterPumpState)
        self.config = config
        
        # Apply initial oil level from config if provided
        if hasattr(config, 'oil_level'):
            self.state.oil_level = config.initial_oil_level
            print(f"Pump {config.pump_id} initialized with oil level: {config.initial_oil_level}%")
        
        # Feedwater-specific performance parameters
        self.rated_power = config.rated_power
        self.rated_head = config.rated_head
        self.min_speed = config.min_speed
        self.max_speed = config.max_speed
        
        # Feedwater-specific dynamic parameters
        self.speed_ramp_rate = config.speed_ramp_rate
        self.startup_time = config.startup_time
        self.coastdown_time = config.coastdown_time
        
        # Feedwater-specific protection setpoints
        self.low_flow_trip = 25.0                       # kg/s low flow trip (reduced from 50.0)
        self.min_npsh_required = 15.0                   # m NPSH requirement
        self.max_discharge_pressure = 10.0              # MPa max discharge pressure
        self.min_suction_pressure = 0.2                 # MPa min suction pressure
        
        # Control parameters
        self.flow_demand = config.rated_flow            # kg/s flow setpoint
        self.auto_level_control = True
        
        # Steam quality control parameters
        self.target_steam_quality = 0.99                # Target steam quality
        self.quality_control_gain = 0.2                 # Proportional gain for quality error
        self.quality_feedforward_gain = 0.1             # Feedforward gain for quality changes
        
        # Enhanced Cavitation Protection Parameters
        self.cavitation_threshold_margin = 2.0          # m safety margin above min NPSH
        self.severe_cavitation_threshold = 0.7          # Intensity level for immediate trip
        self.sustained_cavitation_time_limit = 300.0    # seconds (5 minutes)
        self.cavitation_damage_trip_threshold = 10.0    # Damage level for maintenance trip
        self.npsh_critical_factor = 0.8                 # Factor of min NPSH for emergency trip
        
        # Mechanical Wear Parameters
        self.base_impeller_wear_rate = 0.001            # %/hour at rated conditions
        self.base_bearing_wear_rate = 0.0005            # %/hour at rated conditions
        self.base_seal_wear_rate = 0.0008               # %/hour at rated conditions
        
        # Wear Trip Thresholds
        self.impeller_wear_trip_threshold = 15.0        # % wear
        self.bearing_wear_trip_threshold = 25.0         # % wear
        self.seal_wear_trip_threshold = 30.0            # % wear
        self.combined_wear_trip_threshold = 40.0        # % total wear
        self.performance_degradation_trip_threshold = 25.0  # % efficiency loss
        self.seal_leakage_trip_threshold = 10.0         # L/min
    
    @property
    def seal_leakage(self) -> float:
        """Get seal leakage rate from lubrication system"""
        if hasattr(self, 'lubrication_system'):
            return self.lubrication_system.seal_leakage_rate
        return 0.0
    
    def _calculate_flow_rate(self, system_conditions: Dict):
        """Calculate feedwater pump flow rate based on head-flow curve"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # FIXED: Simplified flow calculation that properly honors flow demand
            speed_ratio = self.state.speed_percent / 100.0
            
            # Apply flow demand if set by control system
            if hasattr(self, 'flow_demand') and self.flow_demand > 0:
                # CRITICAL FIX: At high speeds (>80%), deliver the demanded flow directly
                # This represents proper pump control where speed is adjusted to meet demand
                target_flow = self.flow_demand
                
                if speed_ratio > 0.8:
                    # High speed operation - pump can deliver demanded flow
                    # Speed was already set to achieve this flow demand
                    self.state.flow_rate = target_flow
                else:
                    # Lower speed operation - limited by speed capability
                    max_flow_at_speed = self.config.rated_flow * speed_ratio
                    self.state.flow_rate = min(target_flow, max_flow_at_speed)
                
            else:
                # No specific demand, use speed-based flow (fallback)
                base_flow = self.config.rated_flow * speed_ratio
                self.state.flow_rate = base_flow
            
            # Apply system conditions (temperature effects, etc.)
            self._apply_system_effects(system_conditions)
            
            # Apply performance degradation from wear and cavitation
            flow_factor = self.lubrication_system.pump_flow_factor if hasattr(self, 'lubrication_system') else 1.0
            self.state.flow_rate *= flow_factor
            
            # Minimum flow constraint only when running at very low speeds
            if self.state.status == PumpStatus.RUNNING and self.state.speed_percent < 20.0:
                min_flow = self.config.rated_flow * 0.05  # 5% minimum only at very low speeds
                self.state.flow_rate = max(self.state.flow_rate, min_flow)
            
            # Ensure we don't exceed rated flow significantly
            max_flow = self.config.rated_flow * 1.2  # 120% maximum
            self.state.flow_rate = min(self.state.flow_rate, max_flow)
            
        else:
            # Pump stopped or tripped
            self.state.flow_rate = 0.0
    
    def _apply_system_effects(self, system_conditions: Dict):
        """Apply system conditions to pump performance"""
        # Temperature effects on pump performance
        feedwater_temp = system_conditions.get('feedwater_temperature', 227.0)  # °C
        temp_factor = 1.0 - (feedwater_temp - 227.0) * 0.0002  # Small effect
        
        # Suction pressure effects
        suction_pressure = system_conditions.get('suction_pressure', 0.5)  # MPa
        self.state.suction_pressure = suction_pressure
        
        # Calculate NPSH available (simplified)
        vapor_pressure = self._vapor_pressure(feedwater_temp)  # MPa
        npsh_available = (suction_pressure - vapor_pressure) * 100.0  # Convert to meters
        self.state.npsh_available = max(0, npsh_available)
        
        # Apply temperature factor
        self.state.flow_rate *= temp_factor
    
    def _vapor_pressure(self, temp_c: float) -> float:
        """Calculate vapor pressure of water at given temperature (MPa)"""
        # For feedwater pump NPSH calculation, effective vapor pressure
        # Feedwater is typically subcooled, so effective vapor pressure is much lower
        if temp_c <= 100:
            # Below boiling point - very low vapor pressure
            return 0.001 + (temp_c / 100.0) * 0.01  # Very low values
        else:
            # For subcooled feedwater, use much lower effective vapor pressure
            return 0.05 + (temp_c - 100) * 0.001  # Much more conservative
    
    def _calculate_power_consumption(self):
        """Calculate feedwater pump motor power consumption with efficiency effects"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Power calculation for centrifugal pump: P = Q * H * ρ * g / η
            speed_ratio = self.state.speed_percent / 100.0
            flow_ratio = self.state.flow_rate / self.config.rated_flow
            
            # Head varies with speed squared
            head_ratio = speed_ratio ** 2
            
            # Power roughly proportional to flow * head
            power_ratio = flow_ratio * head_ratio
            base_power = self.config.rated_power * power_ratio
            
            # ENHANCED: Apply efficiency factor (bearing wear increases power consumption)
            # efficiency_factor is a multiplier: 1.0 = perfect, 0.85 = 85% efficiency
            # Lower efficiency requires more electrical power for same hydraulic work
            efficiency_factor = self.lubrication_system.pump_efficiency_factor if hasattr(self, 'lubrication_system') else 1.0
            self.state.power_consumption = base_power / efficiency_factor
            
            # Minimum power when starting
            if self.state.status == PumpStatus.STARTING:
                self.state.power_consumption = max(self.state.power_consumption, 
                                                 self.config.rated_power * 0.2)
        else:
            self.state.power_consumption = 0.0
    
    def _check_protection_systems(self, system_conditions: Dict):
        """Check feedwater pump protection systems"""
        # Call base class protection first
        BasePump._check_protection_systems(self, system_conditions)
        
        # If already tripped by base class, don't check further
        if self.state.trip_active:
            return
        
        # Skip protection checks during startup phase to allow proper equilibrium initialization
        if self.state.status == PumpStatus.STARTING:
            return
        
        # NPSH protection (feedwater-specific)
        if (self.state.status == PumpStatus.RUNNING and 
            self.state.npsh_available < self.min_npsh_required):
            self._trip_pump("NPSH Violation")
            return
        
        # Suction pressure protection
        if (self.state.status == PumpStatus.RUNNING and 
            self.state.suction_pressure < self.min_suction_pressure):
            self._trip_pump("Low Suction Pressure")
            return
        
        # High discharge pressure protection
        discharge_pressure = system_conditions.get('discharge_pressure', 8.0)
        if discharge_pressure > self.max_discharge_pressure:
            self._trip_pump("High Discharge Pressure")
            return
        
        # Steam generator high level protection
        sg_levels = system_conditions.get('sg_levels', [12.5, 12.5, 12.5])
        max_sg_level = max(sg_levels) if sg_levels else 12.5
        
        # DEBUG: Print steam generator levels to understand the issue
        '''
        if self.state.status == PumpStatus.RUNNING and max_sg_level > 14.0:
            print(f"DEBUG {self.config.pump_id}: SG levels = {sg_levels}, max = {max_sg_level:.2f}m")
        '''
        # FIXED: Increase high level trip setpoint to prevent nuisance trips
        # Normal operating level is 12.5m, allow operation up to 16.0m
        if max_sg_level > 16.0:  # High level trip (was 15.0)
            self._trip_pump("Steam Generator High Level")
            return
        
        # Enhanced protection checks
        if self._check_cavitation_trips():
            return
        
        # Delegate lubrication protection to lubrication system
        if hasattr(self, 'lubrication_system'):
            lub_trip_reason = self.lubrication_system.check_protection_trips()
            if lub_trip_reason:
                self._trip_pump(f"Lubrication: {lub_trip_reason}")
                return
    
    def _check_cavitation_trips(self):
        """Check cavitation-related trip conditions"""
        # Severe cavitation - immediate trip
        if self.state.cavitation_intensity > self.severe_cavitation_threshold:
            self._trip_pump("Severe Cavitation")
            return True
            
        # Sustained cavitation - trip after time limit
        if self.state.cavitation_time > self.sustained_cavitation_time_limit:
            self._trip_pump("Sustained Cavitation")
            return True
            
        # Cavitation damage threshold
        if self.state.cavitation_damage > self.cavitation_damage_trip_threshold:
            self._trip_pump("Cavitation Damage Limit")
            return True
            
        # Critical NPSH - emergency trip
        npsh_critical = self.min_npsh_required * self.npsh_critical_factor
        if self.state.npsh_available < npsh_critical:
            self._trip_pump("Critical NPSH Violation")
            return True
            
        return False
    
    
    def set_flow_demand(self, flow_demand: float):
        """Set flow demand from level control system"""
        self.flow_demand = np.clip(flow_demand, 0.0, self.config.rated_flow * 1.2)
        
        # Convert flow demand to speed setpoint (simplified)
        if flow_demand > 0:
            # Approximate speed needed for desired flow
            flow_ratio = flow_demand / self.config.rated_flow
            speed_setpoint = np.sqrt(flow_ratio) * 100.0  # Approximate relationship
            self.state.speed_setpoint = np.clip(speed_setpoint, 0.0, self.max_speed)
        else:
            self.state.speed_setpoint = 0.0
    
    def update_pump(self, dt: float, system_conditions: Dict, 
                   control_inputs: Dict = None) -> Dict:
        """Enhanced update pump method with cavitation and wear simulation"""
        if control_inputs is None:
            control_inputs = {}
        
        # Call base class update first
        result = BasePump.update_pump(self, dt, system_conditions, control_inputs)
        
        # Run enhanced simulations
        self._simulate_cavitation(dt, system_conditions)
        self._simulate_mechanical_wear(dt, system_conditions)
        self._apply_performance_degradation()
        self._simulate_sensors(dt, system_conditions)
        
        # Add enhanced diagnostics to result - get from lubrication system where applicable
        impeller_wear = self.lubrication_system.component_wear.get('pump_bearings', 0.0) if hasattr(self, 'lubrication_system') else 0.0
        bearing_wear = max(
            self.lubrication_system.component_wear.get('motor_bearings', 0.0),
            self.lubrication_system.component_wear.get('pump_bearings', 0.0),
            self.lubrication_system.component_wear.get('thrust_bearing', 0.0)
        ) if hasattr(self, 'lubrication_system') else 0.0
        seal_wear = self.lubrication_system.component_wear.get('mechanical_seals', 0.0) if hasattr(self, 'lubrication_system') else 0.0
        
        oil_level = self.lubrication_system.oil_level if hasattr(self, 'lubrication_system') else 100.0
        oil_temperature = self.lubrication_system.oil_temperature if hasattr(self, 'lubrication_system') else 40.0
        bearing_temperature = oil_temperature + 5.0  # Bearing temp slightly higher than oil temp
        
        flow_factor = self.lubrication_system.pump_flow_factor if hasattr(self, 'lubrication_system') else 1.0
        efficiency_factor = self.lubrication_system.pump_efficiency_factor if hasattr(self, 'lubrication_system') else 1.0
        head_factor = self.lubrication_system.pump_head_factor if hasattr(self, 'lubrication_system') else 1.0
        
        result.update({
            # Cavitation diagnostics
            'cavitation_intensity': self.state.cavitation_intensity,
            'cavitation_damage': self.state.cavitation_damage,
            'cavitation_time': self.state.cavitation_time,
            'cavitation_noise_level': self.state.cavitation_noise_level,
            
            # Mechanical wear diagnostics - from lubrication system
            'impeller_wear': impeller_wear,
            'bearing_wear': bearing_wear,
            'seal_wear': seal_wear,
            'seal_leakage': self.seal_leakage,
            
            # Performance factors - from lubrication system
            'flow_factor': flow_factor,
            'efficiency_factor': efficiency_factor,
            'head_factor': head_factor,
            
            # Enhanced sensor readings
            'npsh_available': self.state.npsh_available,
            'suction_pressure': self.state.suction_pressure,
            'discharge_pressure': self.state.discharge_pressure,
            'differential_pressure': self.state.differential_pressure,
            'oil_level': oil_level,
            'oil_temperature': oil_temperature,
            'bearing_temperature': bearing_temperature,
            'motor_temperature': self.state.motor_temperature,
            'motor_current': self.state.motor_current,
            'motor_voltage': self.state.motor_voltage,
            'vibration_level': self.state.vibration_level
        })
        
        return result
    
    def _simulate_cavitation(self, dt: float, system_conditions: Dict):
        """Simulate enhanced cavitation modeling with damage accumulation"""
        if self.state.status != PumpStatus.RUNNING:
            # Reset cavitation when not running
            self.state.cavitation_intensity = 0.0
            self.state.cavitation_time = 0.0
            self.state.cavitation_noise_level = 0.0
            return
        
        # Calculate cavitation threshold with safety margin
        cavitation_threshold = self.min_npsh_required + self.cavitation_threshold_margin
        
        # Determine cavitation severity based on NPSH deficit
        if self.state.npsh_available < cavitation_threshold:
            npsh_deficit = cavitation_threshold - self.state.npsh_available
            cavitation_severity = min(1.0, npsh_deficit / cavitation_threshold)
            
            # Flow factor - higher flow rates increase cavitation intensity
            flow_factor = (self.state.flow_rate / self.config.rated_flow) ** 2
            
            # Calculate cavitation intensity (0-1 scale)
            self.state.cavitation_intensity = cavitation_severity * flow_factor
            
            # Accumulate cavitation time (dt is in minutes)
            self.state.cavitation_time += dt * 60.0  # Convert minutes to seconds
            
            # Calculate damage accumulation (exponential with intensity)
            if self.state.cavitation_intensity > 0.1:
                damage_rate = (self.state.cavitation_intensity ** 2) * dt / 60.0  # Convert minutes to hours for damage rate
                self.state.cavitation_damage += damage_rate
                
            # Calculate acoustic signature (noise increase)
            self.state.cavitation_noise_level = 20.0 + self.state.cavitation_intensity * 30.0
            
            # Add cavitation-induced vibration
            cavitation_vibration = self.state.cavitation_intensity * 2.0
            self.state.vibration_level += cavitation_vibration
            
        else:
            # No cavitation - reset intensity and noise
            self.state.cavitation_intensity = 0.0
            self.state.cavitation_noise_level = 0.0
            
            # Cavitation time decays slowly when not cavitating
            self.state.cavitation_time = max(0.0, self.state.cavitation_time - dt * 6.0)
    
    def _simulate_mechanical_wear(self, dt: float, system_conditions: Dict):
        """
        Simplified mechanical wear simulation - DRY principle applied
        
        Most wear calculations now handled by lubrication system.
        This method only handles pump-specific hydraulic effects.
        """
        if self.state.status != PumpStatus.RUNNING:
            return
        
        # Only handle cavitation damage (pump hydraulic specific)
        # All other wear is handled by lubrication system
        if self.state.cavitation_intensity > 0.1:
            damage_rate = (self.state.cavitation_intensity ** 2) * dt / 60.0
            self.state.cavitation_damage += damage_rate
    
    # REMOVED: _get_chemistry_degradation_factors() - DRY principle applied
    # Chemistry degradation logic moved to lubrication system's calculate_chemistry_degradation_factors()
    # This eliminates duplicate chemistry calculations and follows single source of truth
    
    def _apply_performance_degradation(self):
        """
        Simplified performance degradation - DRY principle applied
        
        Performance factors now calculated entirely by lubrication system.
        This method only handles pump-specific hydraulic effects not covered by lubrication.
        
        All mechanical wear, chemistry effects, and performance factor calculations
        are now handled by the lubrication system's comprehensive update method.
        """
        # Performance factors are now calculated by lubrication system
        # No duplicate calculations needed here
        pass
    
    def _simulate_sensors(self, dt: float, system_conditions: Dict):
        """
        Simulate sensor readings with DRY-compliant delegation architecture
        
        ARCHITECTURE:
        - Hydraulic sensors: Calculated locally (pump responsibility)
        - Electrical sensors: Calculated locally (pump motor responsibility)
        - Lubrication sensors: Accessed directly from lubrication system when needed
        - Vibration sensors: Hybrid approach combining pump and lubrication effects
        - No duplicate state management or state copying
        """
        
        # === PUMP-SPECIFIC HYDRAULIC SENSORS (Local Responsibility) ===
        self._simulate_hydraulic_sensors(system_conditions)
        
        # === ELECTRICAL SENSORS (Local Responsibility) ===  
        self._simulate_electrical_sensors(system_conditions)
        
        # === VIBRATION SENSORS (Hybrid - Base + Lubrication Effects) ===
        self._simulate_vibration_sensors()
        
        # NOTE: Lubrication sensors (oil_level, oil_temperature, bearing_temperature,
        # component_wear, performance_factors) are accessed directly from lubrication_system
        # when needed. No state copying or duplication.
    
    def _simulate_hydraulic_sensors(self, system_conditions: Dict):
        """
        Simulate pump-specific hydraulic sensor readings
        
        These sensors are pump-specific and not managed by lubrication system:
        - Suction/discharge pressures
        - Differential pressure  
        - NPSH calculations
        - Cavitation effects on hydraulic performance
        """
        # Suction pressure from system conditions
        self.state.suction_pressure = system_conditions.get('suction_pressure', 0.5)
        
        # Discharge pressure from system conditions
        self.state.discharge_pressure = system_conditions.get('discharge_pressure', 8.0)
        
        # Calculate differential pressure
        self.state.differential_pressure = self.state.discharge_pressure - self.state.suction_pressure
        
        # NPSH calculation (pump hydraulic responsibility)
        feedwater_temp = system_conditions.get('feedwater_temperature', 227.0)
        vapor_pressure = self._vapor_pressure(feedwater_temp)
        npsh_available = (self.state.suction_pressure - vapor_pressure) * 100.0  # Convert to meters
        self.state.npsh_available = max(0, npsh_available)
    
    def _simulate_electrical_sensors(self, system_conditions: Dict):
        """
        Simulate electrical sensor readings (pump motor responsibility)
        
        These sensors are specific to the pump motor and electrical system:
        - Motor current based on hydraulic load
        - Motor voltage (typically constant)
        - Motor temperature (electrical heating effects only)
        """
        # Load factor for electrical calculations
        load_factor = self.state.flow_rate / self.config.rated_flow if self.config.rated_flow > 0 else 0.0
        
        # Motor current based on hydraulic load
        base_current = 200.0  # Base current at no load
        load_current = 100.0 * load_factor  # Additional current from hydraulic load
        self.state.motor_current = base_current + load_current
        
        # Motor voltage (typically constant for grid-connected motors)
        self.state.motor_voltage = 6.6  # kV constant
        
        # Motor temperature (electrical heating only - no lubrication effects)
        # Lubrication system handles bearing temperature; this is winding temperature
        motor_base_temp = 60.0  # Base winding temperature
        electrical_heating = 20.0 * load_factor  # Electrical losses heating (reduced from 30.0)
        self.state.motor_temperature = motor_base_temp + electrical_heating
    
    
    def _simulate_vibration_sensors(self):
        """
        Simulate vibration sensors with hybrid approach
        
        HYBRID APPROACH:
        - Base mechanical vibration: Calculated locally from pump operation
        - Lubrication-induced vibration: From lubrication system wear effects
        - Cavitation-induced vibration: From pump hydraulic effects
        - Combined signature: Sum of all vibration sources
        """
        # Base mechanical vibration from pump operation
        base_vibration = 1.0 + 0.05 * self.state.speed_percent  # Speed-dependent base vibration
        
        # Lubrication-induced vibration (from bearing wear, oil quality, etc.)
        lubrication_vibration = 0.0
        if hasattr(self, 'lubrication_system'):
            lub_state = self.lubrication_system.get_state_dict()
            lubrication_vibration = lub_state.get('vibration_increase', 0.0)
        
        # Cavitation-induced vibration (pump hydraulic responsibility)
        cavitation_vibration = getattr(self.state, 'cavitation_intensity', 0.0) * 2.0
        
        # Combined vibration signature
        self.state.vibration_level = base_vibration + lubrication_vibration + cavitation_vibration
        
        # Ensure reasonable bounds
        self.state.vibration_level = max(0.5, min(15.0, self.state.vibration_level))
    
    # REMOVED: All bidirectional sync methods eliminated
    # Following DRY principles - states now live in single location (lubrication system)
    # Pump can directly access lubrication system data without sync complexity

    def perform_maintenance(self, maintenance_type: str = "general", **kwargs) -> Dict[str, Any]:
        """
        Clean maintenance dispatcher that delegates to lubrication system
        
        Args:
            maintenance_type: Type of maintenance to perform (decided by orchestrator)
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        # Delegate to lubrication system - orchestrator already made the decision
        if hasattr(self, 'lubrication_system'):
            return self.lubrication_system.perform_maintenance(
                maintenance_type=maintenance_type,
                **kwargs
            )
        
        # Fallback to individual pump maintenance methods if no lubrication system
        if maintenance_type == "oil_change":
            return self._perform_oil_change()
        elif maintenance_type == "oil_top_off":
            return self._perform_oil_top_off(**kwargs)
        elif maintenance_type == "impeller_inspection":
            return self._perform_impeller_inspection()
        elif maintenance_type == "impeller_replacement":
            return self._perform_impeller_replacement()
        elif maintenance_type == "bearing_inspection":
            return self._perform_bearing_inspection()
        elif maintenance_type == "bearing_replacement":
            return self._perform_bearing_replacement()
        elif maintenance_type == "seal_replacement":
            return self._perform_seal_replacement()
        elif maintenance_type == "vibration_analysis":
            return self._perform_vibration_analysis()
        elif maintenance_type == "component_overhaul":
            return self._perform_component_overhaul(**kwargs)
        elif maintenance_type == "routine_maintenance":
            return self._perform_routine_maintenance()
        else:
            # General maintenance (legacy behavior)
            return self._perform_general_maintenance()
    
    def _perform_oil_change(self) -> Dict[str, Any]:
        """Perform complete oil change - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            # Call the lubrication system's comprehensive oil change method
            return self.lubrication_system.perform_maintenance("oil_change")
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 2.0,
                'work_performed': f"Basic oil change on {self.config.pump_id}",
                'findings': "Oil level restored (no lubrication system integration)",
                'effectiveness_score': 0.7,
                'next_maintenance_due': 8760.0
            }
    
    def _perform_oil_top_off(self, target_level: float = 95.0, **kwargs) -> Dict[str, Any]:
        """Perform oil top-off - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            # Call the lubrication system's oil top-off method
            return self.lubrication_system.perform_maintenance("oil_top_off", target_level=target_level, **kwargs)
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 0.5,
                'work_performed': f"Basic oil top-off on {self.config.pump_id}",
                'findings': "Oil level restored (no lubrication system integration)",
                'effectiveness_score': 0.7
            }
    
    def _perform_impeller_inspection(self) -> Dict[str, Any]:
        """Perform impeller inspection - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            return self.lubrication_system.perform_maintenance("impeller_inspection")
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': f"Basic impeller inspection on {self.config.pump_id}",
                'findings': "Impeller inspection completed (no lubrication system integration)",
                'effectiveness_score': 0.8,
                'next_maintenance_due': 4380.0
            }
    
    def _perform_impeller_replacement(self) -> Dict[str, Any]:
        """Perform impeller replacement - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            return self.lubrication_system.perform_maintenance("impeller_replacement")
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 8.0,
                'work_performed': f"Basic impeller replacement on {self.config.pump_id}",
                'findings': "Impeller replaced (no lubrication system integration)",
                'effectiveness_score': 0.8,
                'next_maintenance_due': 17520.0
            }
    
    def _perform_bearing_inspection(self) -> Dict[str, Any]:
        """Perform bearing inspection - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            return self.lubrication_system.perform_maintenance("bearing_inspection")
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': f"Basic bearing inspection on {self.config.pump_id}",
                'findings': "Bearing inspection completed (no lubrication system integration)",
                'effectiveness_score': 0.8,
                'next_maintenance_due': 4380.0
            }
    
    def _perform_bearing_replacement(self) -> Dict[str, Any]:
        """Perform bearing replacement - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            # Use lubrication system's comprehensive bearing replacement
            lub_result = self.lubrication_system.perform_maintenance("bearing_replacement")
            
            # Add pump-specific effects (vibration reduction, etc.)
            self.state.vibration_level = max(1.0, self.state.vibration_level - 2.0)
            
            return lub_result
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 8.0,
                'work_performed': f"Basic bearing replacement on {self.config.pump_id}",
                'findings': "Bearings replaced (no lubrication system integration)",
                'effectiveness_score': 0.8,
                'next_maintenance_due': 17520.0
            }
    
    def _perform_seal_replacement(self) -> Dict[str, Any]:
        """Perform seal replacement - Delegate to lubrication system (no sync needed)"""
        # Delegate to comprehensive lubrication system maintenance
        if hasattr(self, 'lubrication_system'):
            # Use lubrication system's comprehensive seal replacement
            return self.lubrication_system.perform_maintenance("seal_replacement")
        else:
            # Fallback for systems without lubrication integration
            return {
                'success': True,
                'duration_hours': 6.0,
                'work_performed': f"Basic seal replacement on {self.config.pump_id}",
                'findings': "Seals replaced (no lubrication system integration)",
                'effectiveness_score': 0.8,
                'next_maintenance_due': 8760.0
            }
    
    def _perform_vibration_analysis(self) -> Dict[str, Any]:
        """Perform vibration analysis"""
        vibration = self.state.vibration_level
        
        if vibration > 5.0:
            findings = f"High vibration detected: {vibration:.1f} mm/s"
            recommendations = ["Investigate bearing condition", "Check alignment", "Consider balancing"]
            effectiveness = 0.7
        elif vibration > 3.0:
            findings = f"Moderate vibration: {vibration:.1f} mm/s"
            recommendations = ["Monitor vibration trends", "Schedule bearing inspection"]
            effectiveness = 0.8
        else:
            findings = f"Normal vibration levels: {vibration:.1f} mm/s"
            recommendations = ["Continue normal operation"]
            effectiveness = 1.0
        
        return {
            'success': True,
            'duration_hours': 2.0,
            'work_performed': f"Vibration analysis on {self.config.pump_id}",
            'findings': findings,
            'recommendations': recommendations,
            'effectiveness_score': effectiveness
        }
    
    def _perform_component_overhaul(self, component_id: str = "all", **kwargs) -> Dict[str, Any]:
        """Perform component overhaul"""
        if component_id == "impeller":
            return self._perform_impeller_replacement()
        elif component_id == "bearings":
            return self._perform_bearing_replacement()
        elif component_id == "seals":
            return self._perform_seal_replacement()
        else:
            # Complete overhaul
            self.state.impeller_wear = 0.0
            self.state.bearing_wear = 0.0
            self.state.seal_wear = 0.0
            self.state.cavitation_damage = 0.0
            self.state.oil_level = 100.0
            self.state.vibration_level = 1.5
            
            # Reset performance factors
            self.state.flow_factor = 1.0
            self.state.efficiency_factor = 1.0
            self.state.head_factor = 1.0
            
            return {
                'success': True,
                'duration_hours': 24.0,
                'work_performed': f"Complete overhaul of {self.config.pump_id}",
                'findings': "All major components overhauled, pump restored to like-new condition",
                'performance_improvement': 25.0,
                'effectiveness_score': 1.0,
                'next_maintenance_due': 35040.0  # 4 years
            }
    
    def _perform_routine_maintenance(self) -> Dict[str, Any]:
        """Perform routine maintenance"""
        # Minor improvements from routine maintenance
        self.state.oil_level = min(100.0, self.state.oil_level + 5.0)
        self.state.impeller_wear = max(0.0, self.state.impeller_wear - 0.5)
        self.state.bearing_wear = max(0.0, self.state.bearing_wear - 0.3)
        self.state.seal_wear = max(0.0, self.state.seal_wear - 0.2)
        
        return {
            'success': True,
            'duration_hours': 4.0,
            'work_performed': f"Routine maintenance on {self.config.pump_id}",
            'findings': "Performed standard maintenance tasks, minor improvements achieved",
            'effectiveness_score': 0.8,
            'next_maintenance_due': 2190.0  # 3 months
        }
    
    def _perform_general_maintenance(self) -> Dict[str, Any]:
        """Perform general maintenance (legacy behavior)"""
        # Reset wear and damage
        self.state.impeller_wear = 0.0
        self.state.bearing_wear = 0.0
        self.state.seal_wear = 0.0
        self.state.cavitation_damage = 0.0
        self.state.oil_level = 100.0
        
        # Reset performance factors
        self.state.flow_factor = 1.0
        self.state.efficiency_factor = 1.0
        self.state.head_factor = 1.0
        
        return {
            'success': True,
            'duration_hours': 8.0,
            'work_performed': f"General maintenance on {self.config.pump_id}",
            'findings': "All systems restored to optimal condition",
            'effectiveness_score': 1.0
        }

    def reset(self) -> None:
        """Reset feedwater pump to initial conditions"""
        # Reset basic pump state to initial values
        self.state.speed_percent = 0.0
        self.state.speed_setpoint = 0.0
        self.state.flow_rate = 0.0
        self.state.power_consumption = 0.0
        self.state.status = PumpStatus.STOPPED
        self.state.available = True
        self.state.auto_control = True
        
        # Reset trip conditions
        self.state.trip_active = False
        self.state.trip_reason = ""
        
        # Reset feedwater-specific hydraulic conditions
        self.state.suction_pressure = 0.5
        self.state.discharge_pressure = 8.0
        self.state.npsh_available = 20.0
        self.state.differential_pressure = 0.0
        
        # Reset enhanced monitoring to initial/nominal values
        self.state.oil_level = 100.0
        self.state.oil_temperature = 40.0
        self.state.bearing_temperature = 45.0
        self.state.motor_temperature = 60.0
        self.state.motor_current = 0.0
        self.state.motor_voltage = 6.6
        self.state.vibration_level = 1.5
        
        # Reset enhanced cavitation modeling
        self.state.cavitation_intensity = 0.0
        self.state.cavitation_damage = 0.0
        self.state.cavitation_time = 0.0
        self.state.cavitation_noise_level = 0.0
        
        # Reset detailed mechanical wear
        self.state.impeller_wear = 0.0
        self.state.bearing_wear = 0.0
        self.state.seal_wear = 0.0
        
        # Reset performance factors to optimal
        self.state.flow_factor = 1.0
        self.state.efficiency_factor = 1.0
        self.state.head_factor = 1.0
        
        # Reset control parameters
        self.flow_demand = self.config.rated_flow
        self.auto_level_control = True
        
        # No sync needed - lubrication system is single source of truth

    def get_state_dict(self):
        # Start with pump-specific state (no duplicated values)
        state_dict = {
            'flow_rate': self.state.flow_rate,
            'power_consumption': self.state.power_consumption,
            'speed_percent': self.state.speed_percent,
            'status': self.state.status.value,
            'available': float(self.state.available),
            'trip_active': float(self.state.trip_active),
            'npsh_available': self.state.npsh_available,
            'cavitation_intensity': self.state.cavitation_intensity,
            'cavitation_damage': self.state.cavitation_damage,
            'motor_temperature': self.state.motor_temperature,
            'motor_current': self.state.motor_current,
            'motor_voltage': self.state.motor_voltage,
            'vibration_level': self.state.vibration_level
        }
        
        # Merge lubrication system state at the same level (flat merge)
        if hasattr(self, 'lubrication_system'):
            lubrication_state = self.lubrication_system.get_state_dict()
            state_dict.update(lubrication_state)  # ← Flat merge, not nesting

        return state_dict

@dataclass
class FeedwaterPumpSystemConfig:
    """Configuration for feedwater pump system"""
    num_steam_generators: int = 3                       # Number of steam generators
    pumps_per_sg: int = 1                              # Pumps per steam generator
    spare_pumps: int = 1                               # Number of spare pumps
    pump_config: FeedwaterPumpConfig = field(default_factory=FeedwaterPumpConfig)
    auto_sequencing: bool = True                       # Enable automatic pump sequencing
    load_sharing: bool = True                          # Enable load sharing between pumps
    auto_start_enabled: bool = True                    # Enable system auto-start
    startup_sequence_enabled: bool = True              # Enable sequential startup
    min_running_pumps: int = 3                         # Minimum pumps for operation
    max_running_pumps: int = 4                         # Maximum pumps allowed


@auto_register("SECONDARY", "feedwater", allow_no_id=True,
               description=FEEDWATER_COMPONENT_DESCRIPTIONS['feedwater_pump_system'])
class FeedwaterPumpSystem(ChemistryFlowProvider):
    """
    Complete feedwater pump system for PWR steam generators
    
    This system manages feedwater pumps and provides:
    1. Multi-pump coordination and sequencing
    2. Load distribution and sharing
    3. System-level protection and control
    4. Performance monitoring and diagnostics
    
    Note: This class does not inherit from StateProviderMixin to prevent
    double registration. State collection is handled by EnhancedFeedwaterPhysics.
    """
    
    def __init__(self, config: FeedwaterPumpSystemConfig):
        """Initialize feedwater pump system"""
        self.config = config
        
        # Create pumps - typically 1 pump per steam generator + spares
        total_pumps = config.num_steam_generators * config.pumps_per_sg + config.spare_pumps
        self.pumps = {}
        
        # Create and integrate lubrication systems for each pump
        self.pump_lubrication_systems = {}
        
        for i in range(total_pumps):
            pump_config = FeedwaterPumpConfig(
                pump_id=f"FWP-{i+1}",
                rated_flow=config.pump_config.rated_flow,  # Use config value
                rated_power=config.pump_config.rated_power,  # Use config value
                rated_head=config.pump_config.rated_head   # Use config value
            )
            
            # Add initial_oil_level to pump config if provided in system config
            if hasattr(config, 'initial_oil_levels') and i < len(config.initial_oil_levels):
                pump_config.initial_oil_level = config.initial_oil_levels[i]
            elif hasattr(config, 'initial_oil_level'):
                pump_config.initial_oil_level = config.initial_oil_level
            
            
            # Create the pump
            pump = FeedwaterPump(pump_config)
            
            # Create lubrication system for this pump
            lubrication_config = FeedwaterPumpLubricationConfig(
                system_id=f"{pump_config.pump_id}-LUB",
                pump_rated_power=pump_config.rated_power,
                pump_rated_speed=3600.0,  # Standard pump speed
                pump_rated_flow=pump_config.rated_flow
            )
            lubrication_system = FeedwaterPumpLubricationSystem(lubrication_config)
            
            # Integrate lubrication system with the pump
            integrate_lubrication_with_pump(pump, lubrication_system)
            
            # Store pump and lubrication system
            self.pumps[pump_config.pump_id] = pump
            self.pump_lubrication_systems[pump_config.pump_id] = lubrication_system
        
        # System parameters
        self.total_design_flow = 555.0 * config.num_steam_generators
        self.minimum_pumps_required = config.num_steam_generators
        
        # System status
        self.system_available = True
        self.total_flow = 0.0
        self.total_power = 0.0
        self.running_pumps = []
        
        # Initialize pumps to proper operating state
        self._initialize_pumps()
    
    def _initialize_pumps(self):
        """Initialize pumps to proper operating state"""
        pump_ids = list(self.pumps.keys())
        
        # Configure all pumps for auto-start
        for pump_id, pump in self.pumps.items():
            pump.config.auto_start_enabled = True
            pump.config.min_flow_for_start = 50.0
            pump.state.auto_control = True
            pump.state.available = True
        
        # Start the required number of pumps with proper startup sequence
        for i in range(self.minimum_pumps_required):
            if i < len(pump_ids):
                pump_id = pump_ids[i]
                pump = self.pumps[pump_id]
                
                # CRITICAL FIX: Set proper flow demand and let set_flow_demand calculate speed
                design_flow_per_pump = pump.config.rated_flow  # Use rated flow (533.3 kg/s)
                pump.set_flow_demand(design_flow_per_pump)     # This calculates speed setpoint automatically
                
                # Set actual speed to match the calculated setpoint for steady state
                pump.state.speed_percent = pump.state.speed_setpoint
                
                # Start the pump and immediately transition to RUNNING for steady state
                if pump.state.status == PumpStatus.STOPPED:
                    pump.start_pump()
                    # For steady-state initialization, immediately transition to RUNNING
                    pump.state.status = PumpStatus.RUNNING
                
                print(f"Pump {pump_id} initialized: speed={pump.state.speed_percent:.1f}%, "
                      f"flow_demand={pump.flow_demand:.1f} kg/s, status={pump.state.status}")
        
        # Keep spare pumps stopped
        for i in range(self.minimum_pumps_required, len(pump_ids)):
            pump_id = pump_ids[i]
            pump = self.pumps[pump_id]
            if pump.state.status != PumpStatus.STOPPED:
                pump.stop_pump()
    
    def update_system(self, dt: float, system_conditions: Dict, 
                     control_inputs: Dict = None) -> Dict:
        """Update complete feedwater pump system"""
        if control_inputs is None:
            control_inputs = {}
        
        # Process control inputs for flow demands
        total_flow_demand = control_inputs.get('flow_demand', self.total_design_flow)
        
        # CRITICAL FIX: Properly redistribute total flow demand among running pumps
        # The control system may calculate demands for more SGs than we have running pumps
        if len(self.running_pumps) > 0:
            # Always use total flow demand divided by actual running pumps
            # This ensures proper mass balance regardless of control system configuration
            flow_per_pump = total_flow_demand / len(self.running_pumps)
            individual_demands = [flow_per_pump] * len(self.running_pumps)
            
            # Debug: Show the redistribution
            control_individual_demands = control_inputs.get('individual_demands', [])
            if control_individual_demands:
                control_total = sum(control_individual_demands)
        else:
            individual_demands = []

        # Update individual pumps
        pump_results = {}
        total_flow = 0.0
        total_power = 0.0
        running_pumps = []
        
        for pump_id, pump in self.pumps.items():
            # Set flow demand for running pumps
            if pump.state.status == PumpStatus.RUNNING and individual_demands:
                pump_index = len(running_pumps)
                if pump_index < len(individual_demands):
                    # CRITICAL FIX: Don't override flow demand if it's much lower than design
                    # This prevents control system from setting unrealistically low demands during initialization
                    new_demand = individual_demands[pump_index]
                    if new_demand < pump.config.rated_flow * 0.2:  # Less than 20% of rated flow
                        print(f"DEBUG: Rejecting low flow demand {new_demand:.1f} kg/s for {pump_id}, keeping {pump.flow_demand:.1f} kg/s")
                    else:
                        pump.set_flow_demand(new_demand)
                        # print(f"PUMP SYSTEM DEBUG: Set {pump_id} flow demand to {individual_demands[pump_index]:.1f} kg/s")
            
            result = pump.update_pump(dt, system_conditions, control_inputs)
            pump_results[pump_id] = result
            
            if pump.state.status == PumpStatus.RUNNING:
                total_flow += pump.state.flow_rate
                total_power += pump.state.power_consumption
                running_pumps.append(pump_id)
                # print(f"PUMP SYSTEM DEBUG: {pump_id} actual flow={pump.state.flow_rate:.1f} kg/s, "
                #      f"speed={pump.state.speed_percent:.1f}%")
        
        # print(f"PUMP SYSTEM DEBUG: Total system flow={total_flow:.1f} kg/s from {len(running_pumps)} pumps")
        
        # Update system totals
        self.total_flow = total_flow
        self.total_power = total_power
        self.running_pumps = running_pumps
        
        # System availability check
        self.system_available = len(running_pumps) >= self.minimum_pumps_required
        
        # Calculate system-level metrics
        average_pump_speed = 0.0
        average_pump_efficiency = 0.0
        average_performance_factor = 0.0
        
        if running_pumps:
            total_speed = sum(self.pumps[pump_id].state.speed_percent for pump_id in running_pumps)
            average_pump_speed = total_speed / len(running_pumps)
            
            total_efficiency = sum(self.pumps[pump_id].state.efficiency_factor for pump_id in running_pumps)
            average_pump_efficiency = total_efficiency / len(running_pumps)
            
            total_performance = sum(
                self.pumps[pump_id].state.flow_factor * 
                self.pumps[pump_id].state.efficiency_factor 
                for pump_id in running_pumps
            )
            average_performance_factor = total_performance / len(running_pumps)
        
        return {
            'total_flow_rate': self.total_flow,
            'total_power_consumption': self.total_power,
            'running_pumps': running_pumps,
            'num_running_pumps': len(running_pumps),
            'system_available': self.system_available,
            'pump_details': pump_results,
            'average_pump_speed': average_pump_speed,
            'average_pump_efficiency': average_pump_efficiency,
            'average_performance_factor': average_performance_factor,
            'sg_flow_distribution': self._calculate_sg_flow_distribution()
        }
    
    def _calculate_sg_flow_distribution(self) -> Dict[str, float]:
        """Calculate flow distribution to each steam generator"""
        distribution = {}
        
        # Simple equal distribution for now
        if self.total_flow > 0:
            flow_per_sg = self.total_flow / self.config.num_steam_generators
            
            for i in range(self.config.num_steam_generators):
                distribution[f'sg_{i+1}_flow'] = flow_per_sg
        else:
            for i in range(self.config.num_steam_generators):
                distribution[f'sg_{i+1}_flow'] = 0.0
        
        return distribution
    
    def start_pump(self, pump_id: str) -> bool:
        """Start a specific pump"""
        if pump_id in self.pumps:
            return self.pumps[pump_id].start_pump()
        return False
    
    def stop_pump(self, pump_id: str) -> bool:
        """Stop a specific pump"""
        if (pump_id in self.pumps and 
            len(self.running_pumps) > self.minimum_pumps_required):
            return self.pumps[pump_id].stop_pump()
        return False
    
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'pump_system_total_flow': self.total_flow,
            'pump_system_total_power': self.total_power,
            'pump_system_num_running': len(self.running_pumps),
            'pump_system_available': float(self.system_available)
        }
        
        return state_dict
    
    def reset(self) -> None:
        """Reset pump system to initial conditions"""
        for pump in self.pumps.values():
            pump.reset()
        
        self.system_available = True
        self.total_flow = 0.0
        self.total_power = 0.0
        self.running_pumps = []
        
        # Re-initialize pumps
        self._initialize_pumps()
    
    # === CHEMISTRY FLOW PROVIDER INTERFACE METHODS ===
    # These methods enable integration with chemistry_flow_tracker
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        
        Returns:
            Dictionary with chemistry flow data from feedwater pump perspective
        """
        # Feedwater pumps affect chemistry through material corrosion and wear
        total_iron_release = 0.0
        total_copper_release = 0.0
        total_wear_particles = 0.0
        
        for pump_id, pump in self.pumps.items():
            if pump.state.status == PumpStatus.RUNNING:
                # Iron release from pump materials (impeller, casing)
                iron_rate = pump.state.impeller_wear * 0.01  # kg/hr per % wear
                total_iron_release += iron_rate
                
                # Copper release from pump materials (bearings, seals)
                copper_rate = pump.state.bearing_wear * 0.005  # kg/hr per % wear
                total_copper_release += copper_rate
                
                # Wear particles affecting water quality
                wear_particles = (pump.state.impeller_wear + pump.state.bearing_wear) * 0.002
                total_wear_particles += wear_particles
        
        return {
            'feedwater_pump_corrosion': {
                ChemicalSpecies.IRON.value: total_iron_release,
                ChemicalSpecies.COPPER.value: total_copper_release,
                'wear_particles': total_wear_particles,
                'pump_efficiency_impact': self._calculate_chemistry_efficiency_impact()
            },
            'pump_system_effects': {
                'cavitation_chemistry_impact': self._calculate_cavitation_chemistry_impact(),
                'seal_leakage_rate': sum(pump.state.seal_leakage for pump in self.pumps.values()),
                'oil_contamination_risk': self._calculate_oil_contamination_risk(),
                'flow_distribution_uniformity': self._calculate_flow_uniformity()
            }
        }
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state from feedwater pump perspective
        
        Returns:
            Dictionary with feedwater pump chemistry state
        """
        # Calculate system-wide pump chemistry metrics
        total_wear = 0.0
        total_cavitation_damage = 0.0
        total_seal_leakage = 0.0
        running_pumps_count = 0
        
        for pump in self.pumps.values():
            if pump.state.status == PumpStatus.RUNNING:
                running_pumps_count += 1
                total_wear += (pump.state.impeller_wear + pump.state.bearing_wear + pump.state.seal_wear)
                total_cavitation_damage += pump.state.cavitation_damage
                total_seal_leakage += pump.state.seal_leakage
        
        avg_wear = total_wear / max(1, running_pumps_count)
        avg_cavitation_damage = total_cavitation_damage / max(1, running_pumps_count)
        
        return {
            'feedwater_pump_total_flow': self.total_flow,
            'feedwater_pump_system_available': float(self.system_available),
            'feedwater_pump_running_count': float(len(self.running_pumps)),
            'feedwater_pump_average_wear': avg_wear,
            'feedwater_pump_average_cavitation_damage': avg_cavitation_damage,
            'feedwater_pump_total_seal_leakage': total_seal_leakage,
            'feedwater_pump_efficiency_factor': self._calculate_system_efficiency_factor(),
            'feedwater_pump_chemistry_impact_factor': self._calculate_chemistry_impact_factor()
        }
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update feedwater pump system based on external chemistry effects
        
        This method allows the chemistry flow tracker to influence pump performance
        based on system-wide chemistry changes.
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Update all pumps with chemistry effects
        for pump_id, pump in self.pumps.items():
            # Apply water quality effects to pump wear rates
            if 'water_quality_effects' in chemistry_state:
                water_quality = chemistry_state['water_quality_effects']
                
                # pH effects on pump materials
                if 'ph_effects' in water_quality:
                    ph_factor = water_quality['ph_effects']
                    # Extreme pH accelerates corrosion and wear
                    if abs(ph_factor - 1.0) > 0.1:
                        wear_acceleration = 1.0 + abs(ph_factor - 1.0) * 0.5
                        pump.base_impeller_wear_rate *= wear_acceleration
                        pump.base_bearing_wear_rate *= wear_acceleration
                
                # Iron/copper concentration effects
                if 'corrosion_products' in water_quality:
                    corrosion_level = water_quality['corrosion_products']
                    if corrosion_level > 1.0:
                        # High corrosion products indicate aggressive water
                        pump.base_impeller_wear_rate *= (1.0 + (corrosion_level - 1.0) * 0.3)
                
                # Particle content effects
                if 'particle_content' in water_quality:
                    particle_factor = water_quality['particle_content']
                    pump.base_impeller_wear_rate *= particle_factor
                    pump.base_seal_wear_rate *= particle_factor
            
            # Apply chemical treatment effects
            if 'chemical_treatment_effects' in chemistry_state:
                treatment = chemistry_state['chemical_treatment_effects']
                
                # Chemical cleaning effects
                if 'cleaning_effectiveness' in treatment:
                    cleaning_eff = treatment['cleaning_effectiveness']
                    if cleaning_eff > 0.1:
                        # Chemical cleaning can reduce deposits and improve performance
                        pump.state.impeller_wear *= (1.0 - cleaning_eff * 0.2)
                        pump.state.bearing_wear *= (1.0 - cleaning_eff * 0.1)
                        
                        # Improve performance factors
                        improvement = cleaning_eff * 0.1
                        pump.state.flow_factor = min(1.0, 
                            pump.state.flow_factor + improvement)
                        pump.state.efficiency_factor = min(1.0, 
                            pump.state.efficiency_factor + improvement)
                
                # Corrosion inhibitor effects
                if 'corrosion_inhibitor_effectiveness' in treatment:
                    inhibitor_eff = treatment['corrosion_inhibitor_effectiveness']
                    # Reduce wear rates based on inhibitor effectiveness
                    wear_reduction = inhibitor_eff * 0.3
                    pump.base_impeller_wear_rate *= (1.0 - wear_reduction)
                    pump.base_bearing_wear_rate *= (1.0 - wear_reduction)
                    pump.base_seal_wear_rate *= (1.0 - wear_reduction)
            
            # Apply pH control system effects
            if 'ph_control_effects' in chemistry_state:
                ph_control = chemistry_state['ph_control_effects']
                
                # Stable pH control reduces corrosion
                if 'ph_stability' in ph_control:
                    stability = ph_control['ph_stability']
                    if stability > 0.8:  # Good pH control
                        # Reduce corrosion-related wear
                        pump.base_impeller_wear_rate *= 0.9
                        pump.base_bearing_wear_rate *= 0.95
    
    def _calculate_chemistry_efficiency_impact(self) -> float:
        """Calculate overall chemistry impact on pump efficiency"""
        if not self.running_pumps:
            return 1.0
        
        total_impact = 0.0
        for pump_id in self.running_pumps:
            pump = self.pumps[pump_id]
            # Chemistry impact based on wear and cavitation
            wear_impact = (pump.state.impeller_wear + pump.state.bearing_wear) * 0.01
            cavitation_impact = pump.state.cavitation_damage * 0.005
            pump_impact = 1.0 - (wear_impact + cavitation_impact)
            total_impact += max(0.5, pump_impact)
        
        return total_impact / len(self.running_pumps)
    
    def _calculate_cavitation_chemistry_impact(self) -> float:
        """Calculate chemistry impact from cavitation"""
        total_cavitation = 0.0
        for pump in self.pumps.values():
            if pump.state.status == PumpStatus.RUNNING:
                total_cavitation += pump.state.cavitation_intensity
        
        # Cavitation can release dissolved gases and affect chemistry
        return total_cavitation * 0.1  # Simplified impact factor
    
    def _calculate_oil_contamination_risk(self) -> float:
        """Calculate risk of oil contamination from seal leakage"""
        total_leakage = sum(pump.state.seal_leakage for pump in self.pumps.values())
        # Risk increases with total leakage rate
        return min(1.0, total_leakage / 50.0)  # Normalized to 50 L/min max
    
    def _calculate_flow_uniformity(self) -> float:
        """Calculate flow distribution uniformity between pumps"""
        if len(self.running_pumps) < 2:
            return 1.0
        
        flows = [self.pumps[pump_id].state.flow_rate for pump_id in self.running_pumps]
        if not flows:
            return 1.0
        
        mean_flow = sum(flows) / len(flows)
        if mean_flow == 0:
            return 1.0
        
        # Calculate coefficient of variation
        variance = sum((flow - mean_flow) ** 2 for flow in flows) / len(flows)
        std_dev = variance ** 0.5
        cv = std_dev / mean_flow
        
        # Convert to uniformity (1.0 = perfect uniformity)
        return max(0.0, 1.0 - cv)
    
    def _calculate_system_efficiency_factor(self) -> float:
        """Calculate overall system efficiency factor"""
        if not self.running_pumps:
            return 0.0
        
        total_efficiency = sum(
            self.pumps[pump_id].state.efficiency_factor 
            for pump_id in self.running_pumps
        )
        return total_efficiency / len(self.running_pumps)
    
    def _calculate_chemistry_impact_factor(self) -> float:
        """Calculate overall chemistry impact factor for the pump system"""
        chemistry_efficiency = self._calculate_chemistry_efficiency_impact()
        cavitation_impact = self._calculate_cavitation_chemistry_impact()
        oil_contamination = self._calculate_oil_contamination_risk()
        
        # Combined impact (lower is worse)
        impact_factor = chemistry_efficiency * (1.0 - cavitation_impact) * (1.0 - oil_contamination)
        return max(0.1, impact_factor)


# Example usage and testing
if __name__ == "__main__":
    print("Feedwater Pump System - Integration Test")
    print("=" * 60)
    
    # Create feedwater pump system
    config = FeedwaterPumpSystemConfig(num_steam_generators=3)
    pump_system = FeedwaterPumpSystem(config)
    
    print(f"Created system with {len(pump_system.pumps)} pumps:")
    for pump_id in pump_system.pumps.keys():
        print(f"  {pump_id}")
    print()
    
    # Test normal operation
    print("Normal Operation Test:")
    print(f"{'Time':<6} {'Total Flow':<12} {'Running':<8} {'Power MW':<10} {'Status':<15}")
    print("-" * 70)
    
    system_conditions = {
        'sg_levels': [12.5, 12.5, 12.5],
        'sg_pressures': [6.895, 6.895, 6.895],
        'feedwater_temperature': 227.0,
        'suction_pressure': 0.5,
        'discharge_pressure': 8.0
    }
    
    for t in range(10):
        result = pump_system.update_system(
            dt=1.0,
            system_conditions=system_conditions
        )
        
        status = "Available" if result['system_available'] else "Unavailable"
        
        print(f"{t:<6} {result['total_flow_rate']:<12.0f} "
              f"{result['num_running_pumps']:<8} "
              f"{result['total_power_consumption']:<10.1f} "
              f"{status:<15}")
    
    print()
    print("Feedwater pump system ready for integration!")
