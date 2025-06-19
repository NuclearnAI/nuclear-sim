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
from typing import Dict, List, Optional, Tuple
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
    
    # Enhanced monitoring
    oil_level: float = 100.0                    # % oil level
    oil_temperature: float = 40.0               # °C oil temperature
    bearing_temperature: float = 45.0           # °C bearing temperature
    motor_temperature: float = 60.0             # °C motor temperature
    motor_current: float = 0.0                  # A motor current
    motor_voltage: float = 6.6                  # kV motor voltage
    vibration_level: float = 1.5                # mm/s vibration level
    differential_pressure: float = 0.0          # MPa differential pressure
    
    # Enhanced Cavitation Modeling
    cavitation_intensity: float = 0.0           # 0-1 scale cavitation intensity
    cavitation_damage: float = 0.0              # Accumulated damage (0-100 scale)
    cavitation_time: float = 0.0                # Time spent cavitating (seconds)
    cavitation_noise_level: float = 0.0         # Additional noise from cavitation (dB)
    
    # Detailed Mechanical Wear
    impeller_wear: float = 0.0                  # % impeller wear (0-100)
    bearing_wear: float = 0.0                   # % bearing wear (0-100)
    seal_wear: float = 0.0                      # % seal wear (0-100)
    seal_leakage: float = 0.0                   # L/min seal leakage rate
    
    # Performance Degradation Factors
    flow_degradation_factor: float = 1.0        # Flow capacity multiplier
    efficiency_degradation_factor: float = 1.0  # Efficiency multiplier
    head_degradation_factor: float = 1.0        # Head capacity multiplier


@auto_register("SECONDARY", "feedwater", id_source="config.pump_id")
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
    
    def _calculate_flow_rate(self, system_conditions: Dict):
        """Calculate feedwater pump flow rate based on head-flow curve"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Simplified flow calculation based on speed and flow demand
            speed_ratio = self.state.speed_percent / 100.0
            
            # Base flow calculation: flow proportional to speed for centrifugal pumps
            base_flow = self.config.rated_flow * speed_ratio
            
            # Apply flow demand if set by control system
            if hasattr(self, 'flow_demand') and self.flow_demand > 0:
                # Use flow demand as target, but limit by pump capability
                target_flow = min(self.flow_demand, self.config.rated_flow * 1.2)
                # Blend between base flow and target flow based on speed
                if speed_ratio > 0.8:  # At high speed, follow demand closely
                    self.state.flow_rate = target_flow
                else:  # At low speed, limit by speed capability
                    self.state.flow_rate = min(target_flow, base_flow)
            else:
                # No specific demand, use speed-based flow
                self.state.flow_rate = base_flow
            
            # Apply system conditions (temperature effects, etc.)
            self._apply_system_effects(system_conditions)
            
            # Apply performance degradation from wear and cavitation
            self.state.flow_rate *= self.state.flow_degradation_factor
            
            # Reduce minimum flow constraint to allow load following
            if self.state.status == PumpStatus.RUNNING and self.state.speed_percent > 10.0:
                min_flow = self.config.rated_flow * 0.05  # 5% minimum when running
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
        """Calculate feedwater pump motor power consumption"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Power calculation for centrifugal pump: P = Q * H * ρ * g / η
            speed_ratio = self.state.speed_percent / 100.0
            flow_ratio = self.state.flow_rate / self.config.rated_flow
            
            # Head varies with speed squared
            head_ratio = speed_ratio ** 2
            
            # Power roughly proportional to flow * head
            power_ratio = flow_ratio * head_ratio
            self.state.power_consumption = self.config.rated_power * power_ratio
            
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
        
        if self._check_wear_trips():
            return
        
        if self._check_oil_level_trips():
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
    
    def _check_wear_trips(self):
        """Check mechanical wear-related trip conditions"""
        # Individual component wear limits
        if self.state.impeller_wear > self.impeller_wear_trip_threshold:
            self._trip_pump("Excessive Impeller Wear")
            return True
            
        if self.state.bearing_wear > self.bearing_wear_trip_threshold:
            self._trip_pump("Bearing Failure")
            return True
            
        if self.state.seal_wear > self.seal_wear_trip_threshold:
            self._trip_pump("Seal Failure")
            return True
            
        # Seal leakage limit
        if self.state.seal_leakage > self.seal_leakage_trip_threshold:
            self._trip_pump("Excessive Seal Leakage")
            return True
            
        # Combined wear threshold
        total_wear = (self.state.impeller_wear + 
                     self.state.bearing_wear + 
                     self.state.seal_wear)
        if total_wear > self.combined_wear_trip_threshold:
            self._trip_pump("Combined Wear Limit")
            return True
            
        # Performance degradation threshold
        efficiency_loss = (1.0 - self.state.efficiency_degradation_factor) * 100.0
        if efficiency_loss > self.performance_degradation_trip_threshold:
            self._trip_pump("Performance Degradation")
            return True
            
        return False
    
    def _check_oil_level_trips(self):
        """Check oil level-related trip conditions"""
        # Very low oil level - immediate trip
        if self.state.oil_level < 10.0:  # Below 10%
            self._trip_pump("Very Low Oil Level")
            return True
        
        # Low oil level - trip if running (allow startup with low oil)
        if (self.state.status == PumpStatus.RUNNING and 
            self.state.oil_level < 20.0):  # Below 20%
            self._trip_pump("Low Oil Level")
            return True
        
        # High oil level - overfill protection
        if self.state.oil_level > 105.0:  # Above 105% (impossible overfill)
            self._trip_pump("Oil System Overfill")
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
        self._simulate_sensors(system_conditions)
        
        # Add enhanced diagnostics to result
        result.update({
            # Cavitation diagnostics
            'cavitation_intensity': self.state.cavitation_intensity,
            'cavitation_damage': self.state.cavitation_damage,
            'cavitation_time': self.state.cavitation_time,
            'cavitation_noise_level': self.state.cavitation_noise_level,
            
            # Mechanical wear diagnostics
            'impeller_wear': self.state.impeller_wear,
            'bearing_wear': self.state.bearing_wear,
            'seal_wear': self.state.seal_wear,
            'seal_leakage': self.state.seal_leakage,
            
            # Performance degradation
            'flow_degradation_factor': self.state.flow_degradation_factor,
            'efficiency_degradation_factor': self.state.efficiency_degradation_factor,
            'head_degradation_factor': self.state.head_degradation_factor,
            
            # Enhanced sensor readings
            'npsh_available': self.state.npsh_available,
            'suction_pressure': self.state.suction_pressure,
            'discharge_pressure': self.state.discharge_pressure,
            'differential_pressure': self.state.differential_pressure,
            'oil_level': self.state.oil_level,
            'oil_temperature': self.state.oil_temperature,
            'bearing_temperature': self.state.bearing_temperature,
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
            
            # Accumulate cavitation time
            self.state.cavitation_time += dt * 60.0  # Convert minutes to seconds
            
            # Calculate damage accumulation (exponential with intensity)
            if self.state.cavitation_intensity > 0.1:
                damage_rate = (self.state.cavitation_intensity ** 2) * dt
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
        """Simulate detailed mechanical wear with realistic physics"""
        if self.state.status != PumpStatus.RUNNING:
            return
        
        # Load factors for wear calculation
        flow_factor = (self.state.flow_rate / self.config.rated_flow) ** 1.5
        speed_factor = (self.state.speed_percent / 100.0) ** 2
        
        # Environmental factors
        water_quality = system_conditions.get('water_quality', {})
        particle_content = water_quality.get('water_aggressiveness', 1.0)
        
        # === IMPELLER WEAR ===
        impeller_wear_rate = (self.base_impeller_wear_rate * 
                             flow_factor * speed_factor * particle_content)
        self.state.impeller_wear += impeller_wear_rate * dt / 60.0  # Convert minutes to hours
        
        # === BEARING WEAR ===
        load_factor = (self.state.power_consumption / self.config.rated_power) ** 1.2
        temp_factor = max(1.0, (self.state.bearing_temperature - 60.0) / 30.0)
        oil_factor = max(1.0, (100.0 - self.state.oil_level) / 50.0)
        
        bearing_wear_rate = (self.base_bearing_wear_rate * 
                           load_factor * temp_factor * oil_factor)
        self.state.bearing_wear += bearing_wear_rate * dt / 60.0  # Convert minutes to hours
        
        # === SEAL WEAR ===
        pressure_factor = (self.state.differential_pressure / 7.5) ** 1.5
        temp_factor_seal = max(1.0, (self.state.oil_temperature - 50.0) / 40.0)
        
        seal_wear_rate = (self.base_seal_wear_rate * 
                         pressure_factor * temp_factor_seal)
        self.state.seal_wear += seal_wear_rate * dt / 60.0  # Convert minutes to hours
        
        # === SEAL LEAKAGE ===
        self.state.seal_leakage = self.state.seal_wear * 0.5  # L/min per % wear
        
        # Oil level decreases due to seal leakage
        if self.state.seal_leakage > 0:
            oil_loss_rate = self.state.seal_leakage * dt / 100.0
            self.state.oil_level = max(0.0, self.state.oil_level - oil_loss_rate)
        
        # === VIBRATION EFFECTS FROM WEAR ===
        wear_vibration = (self.state.bearing_wear * 0.1 + 
                         self.state.impeller_wear * 0.05)
        self.state.vibration_level += wear_vibration
    
    def _apply_performance_degradation(self):
        """Apply performance degradation based on cavitation damage and mechanical wear"""
        # === CAVITATION EFFECTS ===
        cavitation_efficiency_loss = min(0.3, self.state.cavitation_damage * 0.01)
        cavitation_flow_loss = cavitation_efficiency_loss * 0.5
        
        # === WEAR EFFECTS ===
        impeller_flow_loss = self.state.impeller_wear * 0.02
        impeller_efficiency_loss = self.state.impeller_wear * 0.015
        bearing_efficiency_loss = self.state.bearing_wear * 0.01
        
        # === COMBINED DEGRADATION FACTORS ===
        total_flow_loss = cavitation_flow_loss + impeller_flow_loss
        total_efficiency_loss = (cavitation_efficiency_loss + 
                               impeller_efficiency_loss + 
                               bearing_efficiency_loss)
        
        # Update degradation factors
        self.state.flow_degradation_factor = max(0.5, 1.0 - total_flow_loss)
        self.state.efficiency_degradation_factor = max(0.5, 1.0 - total_efficiency_loss)
        self.state.head_degradation_factor = max(0.7, 1.0 - impeller_flow_loss * 0.8)
    
    def _simulate_sensors(self, system_conditions: Dict):
        """Simulate sensor readings based on current state and system inputs"""
        # Oil level drops slowly while running (ensure proper bounds)
        if self.state.status == PumpStatus.RUNNING:
            self.state.oil_level = max(0.0, self.state.oil_level - 0.01)
        
        # Apply strict bounds checking to oil level (0-100%)
        self.state.oil_level = min(100.0, max(0.0, self.state.oil_level))
        
        # Load factor for thermal and electrical simulation
        load_factor = self.state.flow_rate / self.config.rated_flow if self.config.rated_flow > 0 else 0.0
        
        # Temperatures (°C)
        self.state.oil_temperature = 40.0 + 20.0 * load_factor
        self.state.bearing_temperature = 45.0 + 25.0 * load_factor
        self.state.motor_temperature = 60.0 + 30.0 * load_factor
        
        # Vibration Level (mm/s) - base vibration plus wear effects
        base_vibration = 1.0 + 0.05 * self.state.speed_percent
        self.state.vibration_level = base_vibration
        
        # Electrical Load (A)
        self.state.motor_current = 200.0 + 100.0 * load_factor
        self.state.motor_voltage = 6.6  # constant
        
        # Hydraulic Conditions (MPa)
        self.state.discharge_pressure = system_conditions.get("discharge_pressure", 8.0)
        self.state.differential_pressure = self.state.discharge_pressure - self.state.suction_pressure
    
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
        self.state.seal_leakage = 0.0
        
        # Reset performance degradation factors to optimal
        self.state.flow_degradation_factor = 1.0
        self.state.efficiency_degradation_factor = 1.0
        self.state.head_degradation_factor = 1.0
        
        # Reset control parameters
        self.flow_demand = self.config.rated_flow
        self.auto_level_control = True

    def get_state_dict(self):
        state_dict = {
            f'flow_rate': self.state.flow_rate,
            f'power_consumption': self.state.power_consumption,
            f'speed_percent': self.state.speed_percent,
            f'status': self.state.status.value,
            f'available': float(self.state.available),
            f'trip_active': float(self.state.trip_active),
            f'npsh_available': self.state.npsh_available,
            f'cavitation_intensity': self.state.cavitation_intensity,
            f'impeller_wear': self.state.impeller_wear,
            f'bearing_wear': self.state.bearing_wear,
            f'vibration_level': self.state.vibration_level
        }
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


@auto_register("SECONDARY", "feedwater", allow_no_id=True)
class FeedwaterPumpSystem:
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
                rated_flow=555.0,  # kg/s per pump
                rated_power=10.0,  # MW per pump
                rated_head=1200.0  # m head
            )
            
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
                
                # Only set defaults if not already set by equilibrium initialization
                if pump.state.speed_setpoint == 0.0:
                    pump.state.speed_setpoint = 100.0
                if not hasattr(pump, 'flow_demand') or pump.flow_demand == 0.0:
                    pump.set_flow_demand(555.0)  # Design flow per pump
                
                # Start the pump (this will initiate STARTING state)
                # Only start if not already started by equilibrium initialization
                if pump.state.status == PumpStatus.STOPPED:
                    pump.start_pump()
        
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
        
        # Calculate individual demands, handling case where no pumps are running
        if len(self.running_pumps) > 0:
            individual_demands = control_inputs.get('individual_demands', 
                                                  [total_flow_demand / len(self.running_pumps)] * len(self.running_pumps))
        else:
            individual_demands = control_inputs.get('individual_demands', [])
        
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
                    pump.set_flow_demand(individual_demands[pump_index])
            
            result = pump.update_pump(dt, system_conditions, control_inputs)
            pump_results[pump_id] = result
            
            if pump.state.status == PumpStatus.RUNNING:
                total_flow += pump.state.flow_rate
                total_power += pump.state.power_consumption
                running_pumps.append(pump_id)
        
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
            
            total_efficiency = sum(self.pumps[pump_id].state.efficiency_degradation_factor for pump_id in running_pumps)
            average_pump_efficiency = total_efficiency / len(running_pumps)
            
            total_performance = sum(
                self.pumps[pump_id].state.flow_degradation_factor * 
                self.pumps[pump_id].state.efficiency_degradation_factor 
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
    
    def perform_maintenance(self, pump_id: str = None, **kwargs) -> Dict[str, float]:
        """Perform maintenance on pump(s)"""
        results = {}
        
        if pump_id and pump_id in self.pumps:
            # Maintenance on specific pump
            pump = self.pumps[pump_id]
            
            # Reset wear and damage
            pump.state.impeller_wear = 0.0
            pump.state.bearing_wear = 0.0
            pump.state.seal_wear = 0.0
            pump.state.cavitation_damage = 0.0
            pump.state.oil_level = 100.0
            
            # Reset performance factors
            pump.state.flow_degradation_factor = 1.0
            pump.state.efficiency_degradation_factor = 1.0
            pump.state.head_degradation_factor = 1.0
            
            results[f'{pump_id}_maintenance'] = True
            
        else:
            # Maintenance on all pumps
            for pid, pump in self.pumps.items():
                pump.state.impeller_wear *= 0.1  # Reduce wear by 90%
                pump.state.bearing_wear *= 0.1
                pump.state.seal_wear *= 0.1
                pump.state.cavitation_damage *= 0.1
                pump.state.oil_level = min(100.0, pump.state.oil_level + 50.0)
                
                # Improve performance factors
                pump.state.flow_degradation_factor = min(1.0, pump.state.flow_degradation_factor + 0.1)
                pump.state.efficiency_degradation_factor = min(1.0, pump.state.efficiency_degradation_factor + 0.1)
                pump.state.head_degradation_factor = min(1.0, pump.state.head_degradation_factor + 0.1)
            
            results['system_maintenance'] = True
        
        return results
    
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
