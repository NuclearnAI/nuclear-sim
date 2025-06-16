"""
Primary Coolant Pump Models for Nuclear Reactor Simulation

This module provides realistic pump models that integrate with the existing
thermal hydraulics system, focusing on flow control and system dynamics
rather than detailed pump performance curves.

This module now includes base classes that can be inherited by other pump types
(e.g., feedwater pumps, condensate pumps) for consistent behavior and code reuse.
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings("ignore")


class PumpStatus(Enum):
    """Pump operational status"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    TRIPPED = "tripped"


@dataclass
class BasePumpState:
    """Base state class for all pump types"""
    # Basic operational parameters
    speed_percent: float = 100.0  # Pump speed as % of rated
    flow_rate: float = 1000.0  # Actual flow rate (kg/s) - default generic value
    status: PumpStatus = PumpStatus.RUNNING
    
    # Control parameters
    speed_setpoint: float = 100.0  # Speed setpoint (% rated)
    auto_control: bool = True
    
    # Simplified performance metrics
    power_consumption: float = 1.0  # Motor power (MW) - default generic value
    available: bool = True  # Pump available for operation
    
    # Protection status
    trip_active: bool = False
    trip_reason: str = ""


@dataclass
class PumpState(BasePumpState):
    """State of a single reactor coolant pump - inherits from base"""
    # RCP-specific defaults
    flow_rate: float = 5700.0  # Actual flow rate (kg/s)
    power_consumption: float = 6.5  # Motor power (MW)


class BasePump:
    """
    Base pump class with common functionality for all pump types
    
    This base class provides:
    1. Common pump dynamics (start/stop, speed control)
    2. Basic protection systems
    3. Standard interfaces for control and monitoring
    4. Power consumption calculations
    
    Derived classes should override:
    - _calculate_flow_rate() for pump-specific performance
    - _check_protection_systems() for pump-specific protections
    - __init__() for pump-specific parameters
    """
    
    def __init__(self, pump_id: str = "PUMP-1", pump_type: str = "generic", 
                 rated_flow: float = 1000.0, state_class=BasePumpState):
        """
        Initialize base pump
        
        Args:
            pump_id: Unique identifier for the pump
            pump_type: Type of pump (for identification)
            rated_flow: Rated flow at 100% speed (kg/s)
            state_class: State class to use (allows pump-specific states)
        """
        self.pump_id = pump_id
        self.pump_type = pump_type
        self.rated_flow = rated_flow
        self.state = state_class()
        
        # Performance parameters (can be overridden by derived classes)
        self.rated_power = 1.0  # MW at rated conditions
        self.min_speed = 30.0  # Minimum operating speed (%)
        self.max_speed = 105.0  # Maximum speed (%)
        
        # Dynamic parameters (can be overridden by derived classes)
        self.speed_ramp_rate = 10.0  # %/s maximum speed change
        self.startup_time = 30.0  # seconds to reach rated speed
        self.coastdown_time = 120.0  # seconds to coast down from rated speed
        
        # Protection setpoints (can be overridden by derived classes)
        self.low_flow_trip = 25.0  # kg/s (generic default - reduced)
    
    def update_pump(self, dt: float, system_conditions: Dict, 
                   control_inputs: Dict = None) -> Dict:
        """
        Update pump state for one time step (base implementation)
        
        Args:
            dt: Time step (s)
            system_conditions: System operating conditions
            control_inputs: Control inputs for this pump
            
        Returns:
            Dictionary with pump performance
        """
        if control_inputs is None:
            control_inputs = {}
        
        # Handle control inputs
        self._process_control_inputs(control_inputs)
        
        # Update pump dynamics based on status
        self._update_pump_dynamics(dt)
        
        # Calculate flow rate based on speed and system conditions
        self._calculate_flow_rate(system_conditions)
        
        # Calculate power consumption
        self._calculate_power_consumption()
        
        # Check protection systems
        self._simulate_sensors(system_conditions)
        self._check_protection_systems(system_conditions)
        

        return {
            'pump_id': self.pump_id,
            'pump_type': self.pump_type,
            'flow_rate': self.state.flow_rate,
            'speed_percent': self.state.speed_percent,
            'power_consumption': self.state.power_consumption,
            'status': self.state.status.value,
            'available': self.state.available,
            'trip_active': self.state.trip_active
        }
    
    def _process_control_inputs(self, control_inputs: Dict):
        """Process control inputs for this pump (base implementation)"""
        # Speed setpoint changes
        if f'{self.pump_id}_speed_setpoint' in control_inputs:
            new_setpoint = control_inputs[f'{self.pump_id}_speed_setpoint']
            self.state.speed_setpoint = np.clip(new_setpoint, 
                                              self.min_speed, 
                                              self.max_speed)
        
        # Start/stop commands
        if f'{self.pump_id}_start' in control_inputs:
            if control_inputs[f'{self.pump_id}_start'] and self.state.available:
                self.start_pump()
        
        if f'{self.pump_id}_stop' in control_inputs:
            if control_inputs[f'{self.pump_id}_stop']:
                self.stop_pump()
    
    def _update_pump_dynamics(self, dt: float):
        """Update pump speed dynamics (base implementation)"""
        if self.state.status == PumpStatus.RUNNING:
            # Normal speed control with ramp rate limiting
            speed_error = self.state.speed_setpoint - self.state.speed_percent
            max_change = self.speed_ramp_rate * dt
            
            if abs(speed_error) <= max_change:
                self.state.speed_percent = self.state.speed_setpoint
            else:
                change = max_change * np.sign(speed_error)
                self.state.speed_percent += change
                
        elif self.state.status == PumpStatus.STARTING:
            # Startup sequence - accelerate to setpoint
            acceleration = 100.0 / self.startup_time  # %/s
            self.state.speed_percent += acceleration * dt
            
            if self.state.speed_percent >= self.state.speed_setpoint * 0.95:
                self.state.status = PumpStatus.RUNNING
                self.state.speed_percent = self.state.speed_setpoint
                
        elif self.state.status == PumpStatus.STOPPING:
            # Shutdown sequence - coast down
            deceleration = 100.0 / self.coastdown_time  # %/s
            self.state.speed_percent -= deceleration * dt
            
            if self.state.speed_percent <= 5.0:
                self.state.speed_percent = 0.0
                self.state.status = PumpStatus.STOPPED
        
        # Ensure speed stays within bounds
        self.state.speed_percent = np.clip(self.state.speed_percent, 0.0, self.max_speed)
    
    def _calculate_flow_rate(self, system_conditions: Dict):
        """
        Calculate pump flow rate (base implementation - should be overridden)
        
        This base implementation provides simple speed-proportional flow.
        Derived classes should override for pump-specific performance.
        """
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Simple speed-proportional flow
            speed_ratio = self.state.speed_percent / 100.0
            self.state.flow_rate = self.rated_flow * speed_ratio
            
            # Ensure minimum flow when running
            if self.state.status == PumpStatus.RUNNING:
                min_flow = self.rated_flow * self.min_speed / 100.0
                self.state.flow_rate = max(self.state.flow_rate, min_flow)
        else:
            # Pump stopped or tripped
            self.state.flow_rate = 0.0
    
    def _calculate_power_consumption(self):
        """Calculate pump motor power consumption (base implementation)"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Power roughly proportional to speed cubed for centrifugal pumps
            speed_ratio = self.state.speed_percent / 100.0
            self.state.power_consumption = self.rated_power * (speed_ratio ** 2.5)
            
            # Minimum power when starting
            if self.state.status == PumpStatus.STARTING:
                self.state.power_consumption = max(self.state.power_consumption, 
                                                 self.rated_power * 0.3)
        else:
            self.state.power_consumption = 0.0
    
    def _check_protection_systems(self, system_conditions: Dict):
        """
        Check pump protection systems (base implementation)
        
        Derived classes should override to add pump-specific protections.
        """
        # Reset trip if pump is stopped
        if self.state.status == PumpStatus.STOPPED:
            self.state.trip_active = False
            self.state.trip_reason = ""
            return
        
        # Basic low flow protection
        if (self.state.status == PumpStatus.RUNNING and 
            self.state.flow_rate < self.low_flow_trip):
            self._trip_pump("Low Flow")
            return
    
    def _trip_pump(self, reason: str):
        """Trip the pump due to protection system activation"""
        self.state.status = PumpStatus.TRIPPED
        self.state.trip_active = True
        self.state.trip_reason = reason
        self.state.available = False
        print(f"PUMP TRIP: {self.pump_id} - {reason}")
    
    def start_pump(self) -> bool:
        """Start the pump if conditions permit"""
        if (self.state.status == PumpStatus.STOPPED and 
            self.state.available and not self.state.trip_active):
            self.state.status = PumpStatus.STARTING
            return True
        return False
    
    def stop_pump(self) -> bool:
        """Stop the pump"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            self.state.status = PumpStatus.STOPPING
            return True
        return False
    
    def reset_trip(self) -> bool:
        """Reset pump trip (manual action)"""
        if self.state.status == PumpStatus.TRIPPED:
            self.state.trip_active = False
            self.state.trip_reason = ""
            self.state.available = True
            self.state.status = PumpStatus.STOPPED
            return True
        return False


class ReactorCoolantPump(BasePump):
    """
    Reactor coolant pump - inherits from BasePump
    
    This model emphasizes:
    1. Flow rate control based on speed
    2. Realistic startup/shutdown dynamics
    3. Protection system integration
    4. Integration with existing thermal hydraulics
    """
    
    def __init__(self, pump_id: str = "RCP-1", rated_flow: float = 5700.0):
        """
        Initialize reactor coolant pump
        
        Args:
            pump_id: Unique identifier for the pump
            rated_flow: Rated flow at 100% speed (kg/s)
        """
        # Initialize base pump with RCP-specific parameters
        super().__init__(pump_id, "reactor_coolant", rated_flow, PumpState)
        
        # RCP-specific performance parameters
        self.rated_power = 6.5  # MW at rated conditions
        self.min_speed = 30.0  # Minimum operating speed (%)
        self.max_speed = 105.0  # Maximum speed (%)
        
        # RCP-specific dynamic parameters
        self.speed_ramp_rate = 10.0  # %/s maximum speed change
        self.startup_time = 30.0  # seconds to reach rated speed
        self.coastdown_time = 120.0  # seconds to coast down from rated speed
        
        # RCP-specific protection setpoints
        self.low_flow_trip = 1000.0  # kg/s
        self.high_vibration_trip = False  # Simplified - not modeled in detail
    
    def _calculate_flow_rate(self, system_conditions: Dict):
        """
        Calculate pump flow rate based on speed and system conditions
        
        For nuclear reactor pumps, flow is approximately proportional to speed
        with some correction for system resistance changes.
        """
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Base flow proportional to speed
            speed_ratio = self.state.speed_percent / 100.0
            base_flow = self.rated_flow * speed_ratio
            
            # Apply system resistance correction (simplified)
            # In reality, this would be based on detailed hydraulic analysis
            system_pressure = system_conditions.get('system_pressure', 15.5)  # MPa
            coolant_temp = system_conditions.get('coolant_temperature', 280.0)  # °C
            
            # Pressure effect (higher pressure slightly reduces flow)
            pressure_factor = 1.0 - (system_pressure - 15.5) * 0.01
            
            # Temperature effect (higher temperature slightly reduces flow due to density)
            temp_factor = 1.0 - (coolant_temp - 280.0) * 0.0005
            
            # Calculate actual flow
            self.state.flow_rate = base_flow * pressure_factor * temp_factor
            
            # Ensure minimum flow when running
            if self.state.status == PumpStatus.RUNNING:
                min_flow = self.rated_flow * self.min_speed / 100.0
                self.state.flow_rate = max(self.state.flow_rate, min_flow)
        else:
            # Pump stopped or tripped
            self.state.flow_rate = 0.0
    
    def _calculate_power_consumption(self):
        """Calculate pump motor power consumption"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            # Power roughly proportional to speed cubed for centrifugal pumps
            speed_ratio = self.state.speed_percent / 100.0
            self.state.power_consumption = self.rated_power * (speed_ratio ** 2.5)
            
            # Minimum power when starting
            if self.state.status == PumpStatus.STARTING:
                self.state.power_consumption = max(self.state.power_consumption, 
                                                 self.rated_power * 0.3)
        else:
            self.state.power_consumption = 0.0
    
    def _check_protection_systems(self, system_conditions: Dict):
        """Check pump protection systems"""
        # Reset trip if pump is stopped
        if self.state.status == PumpStatus.STOPPED:
            self.state.trip_active = False
            self.state.trip_reason = ""
            return
        
        # Low flow protection
        if (self.state.status == PumpStatus.RUNNING and 
            self.state.flow_rate < self.low_flow_trip):
            self._trip_pump("Low Flow")
            return
        
        # System pressure protection (simplified)
        system_pressure = system_conditions.get('system_pressure', 15.5)
        if system_pressure < 10.0:  # Low system pressure
            self._trip_pump("Low System Pressure")
            return
        
        # High temperature protection
        coolant_temp = system_conditions.get('coolant_temperature', 280.0)
        if coolant_temp > 350.0:  # High coolant temperature
            self._trip_pump("High Coolant Temperature")
            return
    
    def _trip_pump(self, reason: str):
        """Trip the pump due to protection system activation"""
        self.state.status = PumpStatus.TRIPPED
        self.state.trip_active = True
        self.state.trip_reason = reason
        self.state.available = False
        print(f"PUMP TRIP: {self.pump_id} - {reason}")
    
    def start_pump(self) -> bool:
        """Start the pump if conditions permit"""
        if (self.state.status == PumpStatus.STOPPED and 
            self.state.available and not self.state.trip_active):
            self.state.status = PumpStatus.STARTING
            return True
        return False
    
    def stop_pump(self) -> bool:
        """Stop the pump"""
        if self.state.status in [PumpStatus.RUNNING, PumpStatus.STARTING]:
            self.state.status = PumpStatus.STOPPING
            return True
        return False
    
    def reset_trip(self) -> bool:
        """Reset pump trip (manual action)"""
        if self.state.status == PumpStatus.TRIPPED:
            self.state.trip_active = False
            self.state.trip_reason = ""
            self.state.available = True
            self.state.status = PumpStatus.STOPPED
            return True
        return False


class CoolantPumpSystem:
    """
    Complete coolant pump system for PWR primary loops
    
    This system manages multiple pumps and provides:
    1. Total system flow control
    2. Pump sequencing and protection
    3. Integration with reactor thermal hydraulics
    """
    
    def __init__(self, num_pumps: int = 4, num_loops: int = 3):
        """
        Initialize coolant pump system
        
        Args:
            num_pumps: Total number of pumps (typically 4 for PWR)
            num_loops: Number of primary loops (typically 3 for large PWR)
        """
        self.num_pumps = num_pumps
        self.num_loops = num_loops
        
        # Create pumps - typically 1 pump per loop + 1 spare
        self.pumps = {}
        for i in range(num_pumps):
            loop_num = (i % num_loops) + 1
            pump_letter = chr(65 + (i // num_loops))  # A, B, C, D...
            pump_id = f"RCP-{loop_num}{pump_letter}"
            self.pumps[pump_id] = ReactorCoolantPump(pump_id, rated_flow=5700.0)
        
        # System parameters
        self.total_design_flow = 17100.0  # kg/s (typical PWR)
        self.minimum_pumps_required = 2  # Minimum for safe operation
        
        # Control parameters
        self.auto_flow_control = True
        self.target_flow = self.total_design_flow
        self.flow_control_deadband = 200.0  # kg/s
        
        # System status
        self.system_available = True
        self.total_flow = 0.0
        self.total_power = 0.0
        self.running_pumps = []
    
    def update_system(self, dt: float, system_conditions: Dict, 
                     control_inputs: Dict = None) -> Dict:
        """
        Update complete pump system
        
        Args:
            dt: Time step (s)
            system_conditions: System operating conditions
            control_inputs: System control inputs
            
        Returns:
            Dictionary with system performance
        """
        if control_inputs is None:
            control_inputs = {}
        
        # Update individual pumps
        pump_results = {}
        total_flow = 0.0
        total_power = 0.0
        running_pumps = []
        
        for pump_id, pump in self.pumps.items():
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
        
        # Automatic flow control
        if self.auto_flow_control:
            self._automatic_flow_control(control_inputs)
        
        return {
            'total_flow_rate': self.total_flow,
            'total_power_consumption': self.total_power,
            'running_pumps': running_pumps,
            'num_running_pumps': len(running_pumps),
            'system_available': self.system_available,
            'pump_details': pump_results,
            'target_flow': self.target_flow,
            'auto_control': self.auto_flow_control
        }
    
    def _automatic_flow_control(self, control_inputs: Dict):
        """Implement automatic system flow control"""
        # Get target flow from control inputs or use default
        target = control_inputs.get('target_total_flow', self.target_flow)
        
        # Calculate flow error
        flow_error = target - self.total_flow
        
        # Only act if outside deadband
        if abs(flow_error) > self.flow_control_deadband:
            # Adjust speed of all running pumps proportionally
            if len(self.running_pumps) > 0:
                # Simple proportional control
                speed_adjustment = flow_error / (len(self.running_pumps) * 100.0)  # %
                
                for pump_id in self.running_pumps:
                    pump = self.pumps[pump_id]
                    new_setpoint = pump.state.speed_setpoint + speed_adjustment
                    new_setpoint = np.clip(new_setpoint, pump.min_speed, pump.max_speed)
                    pump.state.speed_setpoint = new_setpoint
    
    def set_target_flow(self, target_flow: float) -> bool:
        """Set target total flow rate"""
        if 5000.0 <= target_flow <= 20000.0:  # Reasonable bounds
            self.target_flow = target_flow
            return True
        return False
    
    def start_pump(self, pump_id: str) -> bool:
        """Start a specific pump"""
        if pump_id in self.pumps:
            return self.pumps[pump_id].start_pump()
        return False
    
    def stop_pump(self, pump_id: str) -> bool:
        """Stop a specific pump"""
        if pump_id in self.pumps and len(self.running_pumps) > self.minimum_pumps_required:
            return self.pumps[pump_id].stop_pump()
        return False
    
    def get_system_state(self) -> Dict:
        """Get complete system state for monitoring"""
        return {
            'total_flow_rate': self.total_flow,
            'total_power_consumption': self.total_power,
            'running_pumps': self.running_pumps,
            'system_available': self.system_available,
            'target_flow': self.target_flow,
            'auto_control': self.auto_flow_control,
            'pump_states': {pump_id: {
                'speed_percent': pump.state.speed_percent,
                'flow_rate': pump.state.flow_rate,
                'status': pump.state.status.value,
                'available': pump.state.available,
                'trip_active': pump.state.trip_active
            } for pump_id, pump in self.pumps.items()}
        }


# Example usage
if __name__ == "__main__":
    print("Reactor Coolant Pump System - Integration Test")
    print("=" * 60)
    
    # Create pump system
    pump_system = CoolantPumpSystem(num_pumps=4, num_loops=3)
    
    print(f"Created system with {pump_system.num_pumps} pumps:")
    for pump_id in pump_system.pumps.keys():
        print(f"  {pump_id}")
    print()
    
    # Test normal operation
    print("Normal Operation Test:")
    print(f"{'Time':<6} {'Total Flow':<12} {'Running':<8} {'Power MW':<10} {'Status':<15}")
    print("-" * 60)
    
    system_conditions = {
        'system_pressure': 15.5,
        'coolant_temperature': 285.0
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
    print("Pump system ready for integration with reactor simulation!")
