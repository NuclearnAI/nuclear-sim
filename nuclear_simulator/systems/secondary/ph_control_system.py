"""
pH Control System for Nuclear Plant Secondary Side

This module provides comprehensive pH control functionality for the secondary
water chemistry system, including automatic control, manual override, and
failure simulation capabilities.

Key Features:
1. PID-based pH control algorithm
2. Chemical dosing rate calculations (NH₃, morpholine)
3. Control mode management (Auto/Manual/Failed)
4. Chemical supply monitoring
5. Integration with chemistry flow tracker
6. Realistic control response dynamics

Design Philosophy:
- Integrate seamlessly with chemistry_flow_tracker.py
- Provide realistic PWR pH control behavior
- Enable operator training scenarios
- Support failure mode simulation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings

# Handle imports that may not be available during standalone testing
try:
    from simulator.state import auto_register
    from .component_descriptions import SECONDARY_SYSTEM_DESCRIPTIONS
    from .chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies
    IMPORTS_AVAILABLE = True
except ImportError:
    # Define minimal interfaces for standalone testing
    IMPORTS_AVAILABLE = False
    
    def auto_register(*args, **kwargs):
        def decorator(cls):
            return cls
        return decorator
    
    SECONDARY_SYSTEM_DESCRIPTIONS = {}
    
    class ChemistryFlowProvider:
        def get_chemistry_flows(self):
            return {}
        def get_chemistry_state(self):
            return {}
        def update_chemistry_effects(self, chemistry_state):
            pass
    
    class ChemicalSpecies:
        PH = "ph"
        AMMONIA = "ammonia"
        MORPHOLINE = "morpholine"
        
        @property
        def value(self):
            return self

warnings.filterwarnings("ignore")


class PHControlMode(Enum):
    """pH control system operating modes"""
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    FAILED = "FAILED"
    MAINTENANCE = "MAINTENANCE"


class PHControlChemical(Enum):
    """pH control chemicals"""
    AMMONIA = "ammonia"
    MORPHOLINE = "morpholine"
    SODIUM_HYDROXIDE = "sodium_hydroxide"  # Emergency use only


@dataclass
class PHControllerConfig:
    """
    Configuration for pH control system
    
    Typical PWR secondary system pH control parameters
    """
    
    # === CONTROL SETPOINTS ===
    target_ph: float = 9.2                          # Target pH setpoint
    ph_deadband: float = 0.05                       # ±0.05 pH control deadband
    ph_alarm_low: float = 8.8                       # Low pH alarm
    ph_alarm_high: float = 9.6                      # High pH alarm
    ph_trip_low: float = 8.5                        # Low pH trip point
    ph_trip_high: float = 10.0                      # High pH trip point
    
    # === PID CONTROLLER PARAMETERS ===
    # Tuned for typical PWR secondary system response
    kp: float = 2.0                                  # Proportional gain
    ki: float = 0.1                                  # Integral gain (1/min)
    kd: float = 0.5                                  # Derivative gain (min)
    integral_windup_limit: float = 50.0             # Integral windup limit
    output_rate_limit: float = 10.0                 # %/min output rate limit
    
    # === CHEMICAL DOSING PARAMETERS ===
    primary_chemical: PHControlChemical = PHControlChemical.AMMONIA
    secondary_chemical: PHControlChemical = PHControlChemical.MORPHOLINE
    
    # Ammonia dosing system
    ammonia_max_dose_rate: float = 5.0               # kg/hr maximum dosing rate
    ammonia_concentration: float = 25.0              # % NH₃ solution concentration
    ammonia_efficiency: float = 0.95                # Dosing system efficiency
    
    # Morpholine dosing system  
    morpholine_max_dose_rate: float = 10.0           # kg/hr maximum dosing rate
    morpholine_concentration: float = 10.0           # % morpholine solution
    morpholine_efficiency: float = 0.98              # Dosing system efficiency
    
    # === SYSTEM RESPONSE CHARACTERISTICS ===
    transport_delay: float = 5.0                     # minutes - chemical transport delay
    mixing_time_constant: float = 10.0               # minutes - system mixing time
    ph_sensor_time_constant: float = 1.0             # minutes - sensor response time
    
    # === SUPPLY TANK PARAMETERS ===
    ammonia_tank_capacity: float = 1000.0            # kg tank capacity
    morpholine_tank_capacity: float = 2000.0         # kg tank capacity
    low_level_alarm: float = 20.0                    # % tank level alarm
    very_low_level_trip: float = 5.0                 # % tank level trip
    
    # === FAILURE SIMULATION PARAMETERS ===
    dosing_pump_mtbf: float = 8760.0                 # hours - mean time between failures
    ph_sensor_drift_rate: float = 0.001              # pH units/hour drift rate
    control_valve_stiction: float = 0.02             # % stiction in control valve


@dataclass
class PHControllerState:
    """Current state of the pH control system"""
    
    # === CONTROL STATUS ===
    control_mode: PHControlMode = PHControlMode.AUTO
    controller_enabled: bool = True
    manual_output: float = 0.0                       # % manual output (0-100)
    
    # === PROCESS VARIABLES ===
    measured_ph: float = 9.2                         # Current pH measurement
    ph_setpoint: float = 9.2                         # Current pH setpoint
    ph_error: float = 0.0                            # pH error (setpoint - measured)
    
    # === CONTROLLER OUTPUTS ===
    controller_output: float = 0.0                   # % controller output (0-100)
    ammonia_dose_rate: float = 0.0                   # kg/hr actual ammonia dosing
    morpholine_dose_rate: float = 0.0                # kg/hr actual morpholine dosing
    
    # === PID CONTROLLER INTERNALS ===
    proportional_term: float = 0.0
    integral_term: float = 0.0
    derivative_term: float = 0.0
    previous_error: float = 0.0
    integral_sum: float = 0.0
    
    # === CHEMICAL SUPPLY STATUS ===
    ammonia_tank_level: float = 80.0                 # % tank level
    morpholine_tank_level: float = 80.0              # % tank level
    ammonia_supply_available: bool = True
    morpholine_supply_available: bool = True
    
    # === EQUIPMENT STATUS ===
    ammonia_pump_status: bool = True                 # Dosing pump operational
    morpholine_pump_status: bool = True
    ph_sensor_status: bool = True                    # pH sensor operational
    control_valve_position: float = 0.0              # % valve position
    
    # === ALARMS AND TRIPS ===
    ph_low_alarm: bool = False
    ph_high_alarm: bool = False
    low_chemical_alarm: bool = False
    equipment_failure_alarm: bool = False
    
    # === PERFORMANCE METRICS ===
    control_deviation_rms: float = 0.0               # RMS pH deviation
    chemical_consumption_rate: float = 0.0           # kg/hr total consumption
    time_in_control: float = 100.0                   # % time within deadband
    
    # === MAINTENANCE TRACKING ===
    operating_hours: float = 0.0                     # Total operating hours
    last_calibration_time: float = 0.0               # Hours since last calibration
    maintenance_due: bool = False


class PHController:
    """
    PID-based pH controller with realistic dynamics
    
    Implements industry-standard pH control algorithms with
    PWR-specific tuning and characteristics.
    """
    
    def __init__(self, config: PHControllerConfig):
        self.config = config
        self.state = PHControllerState()
        
        # Initialize setpoint
        self.state.ph_setpoint = config.target_ph
        
        # Control algorithm variables
        self._last_update_time = 0.0
        self._ph_history = []  # For derivative calculation
        self._output_history = []  # For rate limiting
        
        # Transport delay simulation
        self._dose_rate_delay_buffer = []
        self._ph_response_delay_buffer = []
        
        # Performance tracking
        self._deviation_history = []
        self._control_start_time = 0.0
    
    def update_controller(self, 
                         measured_ph: float, 
                         dt: float,
                         system_conditions: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Update pH controller for one time step
        
        Args:
            measured_ph: Current pH measurement
            dt: Time step (hours)
            system_conditions: Optional system operating conditions
            
        Returns:
            Dictionary with controller outputs and status
        """
        dt_minutes = dt * 60.0  # Convert to minutes for control calculations
        
        # Update operating time
        self.state.operating_hours += dt
        
        # Apply sensor dynamics and failures
        self.state.measured_ph = self._apply_sensor_dynamics(measured_ph, dt_minutes)
        
        # Calculate pH error
        self.state.ph_error = self.state.ph_setpoint - self.state.measured_ph
        
        # Update alarms and trips
        self._update_alarms_and_trips()
        
        # Calculate controller output based on mode
        if self.state.control_mode == PHControlMode.AUTO and self.state.controller_enabled:
            controller_output = self._calculate_pid_output(dt_minutes)
        elif self.state.control_mode == PHControlMode.MANUAL:
            controller_output = self.state.manual_output
        else:
            controller_output = 0.0
        
        # Apply output rate limiting
        controller_output = self._apply_rate_limiting(controller_output, dt_minutes)
        self.state.controller_output = controller_output
        
        # Calculate chemical dosing rates
        self._calculate_dosing_rates(controller_output)
        
        # Update chemical supply levels
        self._update_chemical_supplies(dt)
        
        # Update equipment status
        self._update_equipment_status(dt)
        
        # Update performance metrics
        self._update_performance_metrics(dt)
        
        return self.get_controller_outputs()
    
    def _apply_sensor_dynamics(self, true_ph: float, dt_minutes: float) -> float:
        """Apply pH sensor dynamics and potential failures"""
        if not self.state.ph_sensor_status:
            # Sensor failed - return last good reading with some drift
            return self.state.measured_ph + np.random.normal(0, 0.01)
        
        # First-order lag for sensor response
        tau = self.config.ph_sensor_time_constant
        alpha = dt_minutes / (tau + dt_minutes)
        
        # Apply sensor dynamics
        filtered_ph = self.state.measured_ph + alpha * (true_ph - self.state.measured_ph)
        
        # Add sensor noise and drift
        noise = np.random.normal(0, 0.005)  # ±0.005 pH units noise
        drift = self.config.ph_sensor_drift_rate * dt_minutes / 60.0
        
        return filtered_ph + noise + drift
    
    def _calculate_pid_output(self, dt_minutes: float) -> float:
        """Calculate PID controller output"""
        error = self.state.ph_error
        
        # Proportional term
        self.state.proportional_term = self.config.kp * error
        
        # Integral term with windup protection
        self.state.integral_sum += error * dt_minutes
        self.state.integral_sum = np.clip(
            self.state.integral_sum, 
            -self.config.integral_windup_limit, 
            self.config.integral_windup_limit
        )
        self.state.integral_term = self.config.ki * self.state.integral_sum
        
        # Derivative term
        if dt_minutes > 0:
            derivative = (error - self.state.previous_error) / dt_minutes
            self.state.derivative_term = self.config.kd * derivative
        else:
            self.state.derivative_term = 0.0
        
        # Calculate total output
        output = (self.state.proportional_term + 
                 self.state.integral_term + 
                 self.state.derivative_term)
        
        # Store error for next derivative calculation
        self.state.previous_error = error
        
        # Clamp output to 0-100%
        return np.clip(output, 0.0, 100.0)
    
    def _apply_rate_limiting(self, desired_output: float, dt_minutes: float) -> float:
        """Apply output rate limiting"""
        if not self._output_history:
            return desired_output
        
        last_output = self._output_history[-1]
        max_change = self.config.output_rate_limit * dt_minutes
        
        # Limit rate of change
        if desired_output > last_output + max_change:
            limited_output = last_output + max_change
        elif desired_output < last_output - max_change:
            limited_output = last_output - max_change
        else:
            limited_output = desired_output
        
        # Store in history
        self._output_history.append(limited_output)
        if len(self._output_history) > 10:  # Keep last 10 values
            self._output_history.pop(0)
        
        return limited_output
    
    def _calculate_dosing_rates(self, controller_output: float) -> None:
        """Calculate actual chemical dosing rates"""
        # Primary chemical (ammonia) dosing
        if (self.state.ammonia_supply_available and 
            self.state.ammonia_pump_status and 
            controller_output > 0):
            
            max_rate = self.config.ammonia_max_dose_rate
            efficiency = self.config.ammonia_efficiency
            self.state.ammonia_dose_rate = (controller_output / 100.0) * max_rate * efficiency
        else:
            self.state.ammonia_dose_rate = 0.0
        
        # Secondary chemical (morpholine) dosing - used when ammonia unavailable
        if (not self.state.ammonia_supply_available and 
            self.state.morpholine_supply_available and 
            self.state.morpholine_pump_status and 
            controller_output > 0):
            
            max_rate = self.config.morpholine_max_dose_rate
            efficiency = self.config.morpholine_efficiency
            self.state.morpholine_dose_rate = (controller_output / 100.0) * max_rate * efficiency
        else:
            self.state.morpholine_dose_rate = 0.0
        
        # Update total consumption rate
        self.state.chemical_consumption_rate = (self.state.ammonia_dose_rate + 
                                              self.state.morpholine_dose_rate)
    
    def _update_chemical_supplies(self, dt: float) -> None:
        """Update chemical supply tank levels"""
        # Ammonia consumption
        if self.state.ammonia_dose_rate > 0:
            consumption = self.state.ammonia_dose_rate * dt  # kg
            tank_capacity = self.config.ammonia_tank_capacity
            level_decrease = (consumption / tank_capacity) * 100.0
            self.state.ammonia_tank_level = max(0.0, self.state.ammonia_tank_level - level_decrease)
        
        # Morpholine consumption
        if self.state.morpholine_dose_rate > 0:
            consumption = self.state.morpholine_dose_rate * dt  # kg
            tank_capacity = self.config.morpholine_tank_capacity
            level_decrease = (consumption / tank_capacity) * 100.0
            self.state.morpholine_tank_level = max(0.0, self.state.morpholine_tank_level - level_decrease)
        
        # Update supply availability
        self.state.ammonia_supply_available = (
            self.state.ammonia_tank_level > self.config.very_low_level_trip
        )
        self.state.morpholine_supply_available = (
            self.state.morpholine_tank_level > self.config.very_low_level_trip
        )
    
    def _update_equipment_status(self, dt: float) -> None:
        """Update equipment status and simulate failures"""
        # Simplified failure simulation based on MTBF
        failure_probability = dt / self.config.dosing_pump_mtbf
        
        # Ammonia pump failure simulation
        if self.state.ammonia_pump_status and np.random.random() < failure_probability:
            self.state.ammonia_pump_status = False
            self.state.equipment_failure_alarm = True
        
        # Morpholine pump failure simulation
        if self.state.morpholine_pump_status and np.random.random() < failure_probability:
            self.state.morpholine_pump_status = False
            self.state.equipment_failure_alarm = True
        
        # pH sensor failure simulation
        sensor_failure_prob = failure_probability * 0.5  # Sensors more reliable
        if self.state.ph_sensor_status and np.random.random() < sensor_failure_prob:
            self.state.ph_sensor_status = False
            self.state.equipment_failure_alarm = True
    
    def _update_alarms_and_trips(self) -> None:
        """Update alarm and trip status"""
        # pH alarms
        self.state.ph_low_alarm = self.state.measured_ph < self.config.ph_alarm_low
        self.state.ph_high_alarm = self.state.measured_ph > self.config.ph_alarm_high
        
        # Chemical supply alarms
        low_ammonia = self.state.ammonia_tank_level < self.config.low_level_alarm
        low_morpholine = self.state.morpholine_tank_level < self.config.low_level_alarm
        self.state.low_chemical_alarm = low_ammonia or low_morpholine
        
        # Trip conditions
        ph_trip = (self.state.measured_ph < self.config.ph_trip_low or 
                  self.state.measured_ph > self.config.ph_trip_high)
        
        if ph_trip and self.state.control_mode == PHControlMode.AUTO:
            self.state.control_mode = PHControlMode.FAILED
            self.state.controller_enabled = False
    
    def _update_performance_metrics(self, dt: float) -> None:
        """Update controller performance metrics"""
        # Track pH deviation
        deviation = abs(self.state.ph_error)
        self._deviation_history.append(deviation)
        
        # Keep last 100 values for RMS calculation
        if len(self._deviation_history) > 100:
            self._deviation_history.pop(0)
        
        # Calculate RMS deviation
        if self._deviation_history:
            self.state.control_deviation_rms = np.sqrt(np.mean(np.square(self._deviation_history)))
        
        # Calculate time in control
        in_control = deviation <= self.config.ph_deadband
        if hasattr(self, '_time_in_control_sum'):
            self._time_in_control_sum += dt if in_control else 0.0
            self._total_time += dt
            self.state.time_in_control = (self._time_in_control_sum / self._total_time) * 100.0
        else:
            self._time_in_control_sum = dt if in_control else 0.0
            self._total_time = dt
            self.state.time_in_control = 100.0 if in_control else 0.0
    
    def get_controller_outputs(self) -> Dict[str, float]:
        """Get current controller outputs for chemistry system"""
        return {
            'ammonia_dose_rate': self.state.ammonia_dose_rate,  # kg/hr
            'morpholine_dose_rate': self.state.morpholine_dose_rate,  # kg/hr
            'controller_output': self.state.controller_output,  # %
            'ph_setpoint': self.state.ph_setpoint,
            'ph_error': self.state.ph_error,
            'control_mode': self.state.control_mode.value,
            'controller_enabled': float(self.state.controller_enabled)
        }
    
    def set_manual_mode(self, manual_output: float) -> None:
        """Switch to manual mode with specified output"""
        self.state.control_mode = PHControlMode.MANUAL
        self.state.manual_output = np.clip(manual_output, 0.0, 100.0)
        self.state.controller_enabled = True
    
    def set_auto_mode(self) -> None:
        """Switch to automatic mode"""
        if not self.state.equipment_failure_alarm:
            self.state.control_mode = PHControlMode.AUTO
            self.state.controller_enabled = True
            # Reset integral term to prevent bump
            self.state.integral_sum = 0.0
    
    def set_ph_setpoint(self, new_setpoint: float) -> None:
        """Change pH setpoint"""
        self.state.ph_setpoint = np.clip(
            new_setpoint, 
            self.config.ph_trip_low, 
            self.config.ph_trip_high
        )
    
    def reset_controller(self) -> None:
        """Reset controller to initial state"""
        self.state = PHControllerState()
        self.state.ph_setpoint = self.config.target_ph
        self._last_update_time = 0.0
        self._ph_history = []
        self._output_history = []
        self._deviation_history = []


@auto_register("SECONDARY", "ph_control", allow_no_id=True,
               description=SECONDARY_SYSTEM_DESCRIPTIONS.get("ph_control", "pH Control System"))
class PHControlSystem(ChemistryFlowProvider):
    """
    Complete pH control system for nuclear plant secondary side
    
    Integrates with chemistry flow tracker and provides realistic
    pH control behavior for operator training and system analysis.
    """
    
    def __init__(self, config: Optional[PHControllerConfig] = None):
        """Initialize pH control system"""
        self.config = config if config is not None else PHControllerConfig()
        self.controller = PHController(self.config)
        
        # Integration with chemistry system
        self._last_chemistry_update = {}
        self._ph_effect_delay_buffer = []
        
        # Performance tracking
        self.total_chemical_consumed = 0.0  # kg total consumption
        self.control_actions_count = 0
        
    def update_system(self, 
                     current_ph: float,
                     dt: float,
                     system_conditions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update pH control system
        
        Args:
            current_ph: Current system pH
            dt: Time step (hours)
            system_conditions: Optional system operating conditions
            
        Returns:
            Dictionary with system status and outputs
        """
        # Update controller
        controller_outputs = self.controller.update_controller(current_ph, dt, system_conditions)
        
        # Track chemical consumption
        chemical_consumed = (controller_outputs['ammonia_dose_rate'] + 
                           controller_outputs['morpholine_dose_rate']) * dt
        self.total_chemical_consumed += chemical_consumed
        
        # Count control actions
        if controller_outputs['controller_output'] > 0:
            self.control_actions_count += 1
        
        return {
            'controller_outputs': controller_outputs,
            'system_status': self.get_system_status(),
            'performance_metrics': self.get_performance_metrics()
        }
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """Get chemistry flows for chemistry flow tracker integration"""
        outputs = self.controller.get_controller_outputs()
        
        # Convert dosing rates to mass flows (kg/s)
        ammonia_flow = outputs['ammonia_dose_rate'] / 3600.0  # kg/hr to kg/s
        morpholine_flow = outputs['morpholine_dose_rate'] / 3600.0
        
        # Handle both real ChemicalSpecies enum and standalone string version
        if IMPORTS_AVAILABLE:
            ammonia_key = ChemicalSpecies.AMMONIA.value
            morpholine_key = ChemicalSpecies.MORPHOLINE.value
        else:
            ammonia_key = ChemicalSpecies.AMMONIA
            morpholine_key = ChemicalSpecies.MORPHOLINE
        
        return {
            'chemical_addition': {
                ammonia_key: ammonia_flow,
                morpholine_key: morpholine_flow
            }
        }
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """Get current chemistry state"""
        # Handle both real ChemicalSpecies enum and standalone string version
        if IMPORTS_AVAILABLE:
            ph_key = ChemicalSpecies.PH.value
        else:
            ph_key = ChemicalSpecies.PH
            
        return {
            ph_key: self.controller.state.ph_setpoint,
            'ph_control_output': self.controller.state.controller_output,
            'ammonia_supply_level': self.controller.state.ammonia_tank_level,
            'morpholine_supply_level': self.controller.state.morpholine_tank_level
        }
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """Update system based on chemistry state feedback"""
        # This would be used for more complex interactions
        # For now, just store the chemistry state
        self._last_chemistry_update = chemistry_state.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        state = self.controller.state
        
        return {
            'control_mode': state.control_mode.value,
            'controller_enabled': state.controller_enabled,
            'ph_setpoint': state.ph_setpoint,
            'measured_ph': state.measured_ph,
            'ph_error': state.ph_error,
            'controller_output': state.controller_output,
            'ammonia_dose_rate': state.ammonia_dose_rate,
            'morpholine_dose_rate': state.morpholine_dose_rate,
            'ammonia_tank_level': state.ammonia_tank_level,
            'morpholine_tank_level': state.morpholine_tank_level,
            'alarms': {
                'ph_low': state.ph_low_alarm,
                'ph_high': state.ph_high_alarm,
                'low_chemical': state.low_chemical_alarm,
                'equipment_failure': state.equipment_failure_alarm
            },
            'equipment_status': {
                'ammonia_pump': state.ammonia_pump_status,
                'morpholine_pump': state.morpholine_pump_status,
                'ph_sensor': state.ph_sensor_status
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics"""
        state = self.controller.state
        
        return {
            'control_deviation_rms': state.control_deviation_rms,
            'time_in_control': state.time_in_control,
            'chemical_consumption_rate': state.chemical_consumption_rate,
            'total_chemical_consumed': self.total_chemical_consumed,
            'control_actions_count': self.control_actions_count,
            'operating_hours': state.operating_hours
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get state dictionary for logging/monitoring"""
        state = self.controller.state
        
        return {
            # Control status
            'ph_control_mode_auto': 1.0 if state.control_mode == PHControlMode.AUTO else 0.0,
            'ph_control_enabled': 1.0 if state.controller_enabled else 0.0,
            'ph_control_setpoint': state.ph_setpoint,
            'ph_control_measured': state.measured_ph,
            'ph_control_error': state.ph_error,
            'ph_control_output': state.controller_output,
            
            # Chemical dosing
            'ph_control_ammonia_dose_rate': state.ammonia_dose_rate,
            'ph_control_morpholine_dose_rate': state.morpholine_dose_rate,
            'ph_control_total_consumption': state.chemical_consumption_rate,
            
            # Supply levels
            'ph_control_ammonia_level': state.ammonia_tank_level,
            'ph_control_morpholine_level': state.morpholine_tank_level,
            
            # Performance
            'ph_control_deviation_rms': state.control_deviation_rms,
            'ph_control_time_in_control': state.time_in_control,
            
            # Alarms (encoded as 0/1)
            'ph_control_alarm_low': 1.0 if state.ph_low_alarm else 0.0,
            'ph_control_alarm_high': 1.0 if state.ph_high_alarm else 0.0,
            'ph_control_alarm_chemical': 1.0 if state.low_chemical_alarm else 0.0,
            'ph_control_alarm_equipment': 1.0 if state.equipment_failure_alarm else 0.0
        }
    
    def reset(self) -> None:
        """Reset pH control system"""
        self.controller.reset_controller()
        self.total_chemical_consumed = 0.0
        self.control_actions_count = 0
        self._last_chemistry_update = {}


# Example usage and testing
if __name__ == "__main__":
    print("pH Control System - Validation Test")
    print("=" * 40)
    
    # Create pH control system
    config = PHControllerConfig()
    ph_control = PHControlSystem(config)
    
    print(f"pH Control System Configuration:")
    print(f"  Target pH: {config.target_ph}")
    print(f"  Control Deadband: ±{config.ph_deadband}")
    print(f"  PID Parameters: Kp={config.kp}, Ki={config.ki}, Kd={config.kd}")
    print(f"  Max Ammonia Dose: {config.ammonia_max_dose_rate} kg/hr")
    print(f"  Max Morpholine Dose: {config.morpholine_max_dose_rate} kg/hr")
    print()
    
    # Simulate pH control response
    print("pH Control Response Simulation:")
    print(f"{'Time':<6} {'pH':<6} {'Error':<8} {'Output':<8} {'NH3 Dose':<10} {'Mode':<8}")
    print("-" * 50)
    
    # Simulate pH disturbance and control response
    time = 0.0
    dt = 0.1  # 6 minutes time step
    
    for step in range(50):
        # Simulate pH disturbance
        if step < 10:
            actual_ph = 9.2  # Normal operation
        elif step < 20:
            actual_ph = 9.0  # pH drops (acid addition)
        elif step < 30:
            actual_ph = 9.1 + (step - 20) * 0.02  # pH recovering
        elif step < 40:
            actual_ph = 9.4  # pH rises (base addition)
        else:
            actual_ph = 9.4 - (step - 40) * 0.02  # pH recovering
        
        # Update pH control system
        result = ph_control.update_system(actual_ph, dt)
        
        # Print status every 5 steps
        if step % 5 == 0:
            status = result['system_status']
            print(f"{time:<6.1f} {status['measured_ph']:<6.2f} "
                  f"{status['ph_error']:<8.3f} {status['controller_output']:<8.1f} "
                  f"{status['ammonia_dose_rate']:<10.2f} {status['control_mode']:<8}")
        
        time += dt
    
    print()
    
    # Test manual mode
    print("Testing Manual Mode:")
    ph_control.controller.set_manual_mode(25.0)  # 25% output
    result = ph_control.update_system(9.0, 0.1)
    status = result['system_status']
    print(f"  Manual Output: {status['controller_output']:.1f}%")
    print(f"  Ammonia Dose Rate: {status['ammonia_dose_rate']:.2f} kg/hr")
    print(f"  Control Mode: {status['control_mode']}")
    
    # Switch back to auto mode
    ph_control.controller.set_auto_mode()
    result = ph_control.update_system(9.0, 0.1)
    status = result['system_status']
    print(f"  Auto Mode - Output: {status['controller_output']:.1f}%")
    print()
    
    # Performance metrics
    metrics = result['performance_metrics']
    print("Performance Metrics:")
    print(f"  Control Deviation RMS: {metrics['control_deviation_rms']:.3f} pH units")
    print(f"  Time in Control: {metrics['time_in_control']:.1f}%")
    print(f"  Chemical Consumption: {metrics['chemical_consumption_rate']:.2f} kg/hr")
    print(f"  Total Consumed: {metrics['total_chemical_consumed']:.3f} kg")
    print()
    
    # Test chemistry flow integration
    chemistry_flows = ph_control.get_chemistry_flows()
    chemistry_state = ph_control.get_chemistry_state()
    
    print("Chemistry Flow Integration:")
    print(f"  Ammonia Flow: {chemistry_flows['chemical_addition']['ammonia']:.6f} kg/s")
    print(f"  Morpholine Flow: {chemistry_flows['chemical_addition']['morpholine']:.6f} kg/s")
    print(f"  pH Setpoint: {chemistry_state['ph']:.2f}")
    print(f"  Ammonia Supply: {chemistry_state['ammonia_supply_level']:.1f}%")
    
    print("\npH control system ready for integration!")
