"""
Vacuum System Model for PWR Condenser

This module implements a comprehensive vacuum system model that manages
multiple steam jet ejectors, control logic, and system-level performance.

Parameter Sources:
- EPRI Condenser Performance Guidelines
- Power Plant Engineering (Black & Veatch)
- Vacuum system design specifications for large PWR plants
- Steam jet ejector system arrangements

Physical Basis:
- Air mass balance in condenser
- Multiple ejector coordination
- Automatic control logic
- System redundancy and backup operation
"""

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from simulator.state import auto_register

from .vacuum_pump import SteamJetEjector, SteamEjectorConfig

warnings.filterwarnings("ignore")


@dataclass
class VacuumSystemConfig:
    """
    Configuration parameters for the complete vacuum system
    
    References:
    - Typical PWR vacuum system arrangements
    - Steam ejector system design practices
    - Plant operating procedures
    """
    
    # System configuration
    system_id: str = "VS-001"              # Vacuum system identifier
    ejector_configs: List[SteamEjectorConfig] = None  # List of ejector configurations
    
    # Control parameters
    auto_start_pressure: float = 0.008     # MPa pressure to auto-start backup ejector
    auto_stop_pressure: float = 0.006      # MPa pressure to auto-stop backup ejector
    rotation_interval: float = 168.0       # hours between ejector rotation (weekly)
    control_strategy: str = "lead_lag"     # "lead_lag", "parallel", "sequential"
    
    # Air leakage parameters
    base_air_leakage: float = 0.1          # kg/s base air in-leakage
    leakage_degradation_rate: float = 0.00001  # Increase in leakage per hour
    
    # System performance
    condenser_volume: float = 500.0        # m³ condenser steam space volume
    air_holdup_time: float = 60.0          # seconds average air residence time
    
    # Motive steam supply
    motive_steam_header_pressure: float = 1.2  # MPa motive steam header pressure
    motive_steam_temperature: float = 185.0    # °C motive steam temperature
    steam_pressure_drop: float = 0.1           # MPa pressure drop to ejectors
    
    # Alarm and trip settings
    high_pressure_alarm: float = 0.010     # MPa high condenser pressure alarm
    high_pressure_trip: float = 0.012      # MPa high pressure trip (turbine trip)
    low_motive_pressure_alarm: float = 0.9 # MPa low motive steam pressure alarm


class VacuumControlLogic:
    """
    Vacuum system control logic
    
    Handles:
    - Automatic ejector start/stop
    - Lead/lag ejector rotation
    - Load balancing between ejectors
    - Emergency backup activation
    - Alarm and trip logic
    """
    
    def __init__(self, config: VacuumSystemConfig):
        self.config = config
        self.lead_ejector_id = None           # Current lead ejector
        self.lag_ejector_id = None            # Current lag ejector
        self.rotation_timer = 0.0             # Hours since last rotation
        self.auto_start_enabled = True       # Automatic start enabled
        self.manual_override = False          # Manual control override
        
        # Control state
        self.pressure_trend = 0.0             # MPa/hour pressure trend
        self.demand_forecast = 0.0            # Predicted air removal demand
        
    def update_control_logic(self, 
                           ejectors: Dict[str, SteamJetEjector],
                           condenser_pressure: float,
                           air_removal_demand: float,
                           dt: float) -> Dict[str, bool]:
        """
        Update vacuum system control logic
        
        Args:
            ejectors: Dictionary of ejector objects
            condenser_pressure: Current condenser pressure (MPa)
            air_removal_demand: Required air removal capacity (kg/s)
            dt: Time step (hours)
            
        Returns:
            Dictionary with ejector start/stop commands
        """
        commands = {}
        
        if self.manual_override:
            return commands  # No automatic control in manual mode
        
        # Update rotation timer
        self.rotation_timer += dt
        
        # Identify available ejectors
        available_ejectors = [eid for eid, ejector in ejectors.items() 
                            if ejector.motive_steam_available]
        
        if not available_ejectors:
            return commands  # No ejectors available
        
        # Initialize lead/lag if not set
        if self.lead_ejector_id is None and available_ejectors:
            self.lead_ejector_id = available_ejectors[0]
            if len(available_ejectors) > 1:
                self.lag_ejector_id = available_ejectors[1]
        
        # Control strategy implementation
        if self.config.control_strategy == "lead_lag":
            commands.update(self._lead_lag_control(
                ejectors, condenser_pressure, air_removal_demand
            ))
        elif self.config.control_strategy == "parallel":
            commands.update(self._parallel_control(
                ejectors, condenser_pressure, air_removal_demand
            ))
        elif self.config.control_strategy == "sequential":
            commands.update(self._sequential_control(
                ejectors, condenser_pressure, air_removal_demand
            ))
        
        # Handle ejector rotation
        if self.rotation_timer >= self.config.rotation_interval:
            commands.update(self._rotate_ejectors(available_ejectors))
            self.rotation_timer = 0.0
        
        return commands
    
    def _lead_lag_control(self,
                         ejectors: Dict[str, SteamJetEjector],
                         pressure: float,
                         demand: float) -> Dict[str, bool]:
        """Lead/lag control strategy"""
        commands = {}
        
        # Lead ejector should always be running if available
        if (self.lead_ejector_id and 
            self.lead_ejector_id in ejectors and
            not ejectors[self.lead_ejector_id].is_operating):
            commands[self.lead_ejector_id] = True  # Start lead
        
        # Lag ejector control based on pressure
        if self.lag_ejector_id and self.lag_ejector_id in ejectors:
            lag_ejector = ejectors[self.lag_ejector_id]
            
            if pressure > self.config.auto_start_pressure and not lag_ejector.is_operating:
                commands[self.lag_ejector_id] = True  # Start lag
            elif pressure < self.config.auto_stop_pressure and lag_ejector.is_operating:
                commands[self.lag_ejector_id] = False  # Stop lag
        
        return commands
    
    def _parallel_control(self,
                         ejectors: Dict[str, SteamJetEjector],
                         pressure: float,
                         demand: float) -> Dict[str, bool]:
        """Parallel control strategy - all ejectors share load"""
        commands = {}
        
        # Calculate total required capacity
        total_design_capacity = sum(e.config.design_capacity for e in ejectors.values())
        load_factor = demand / max(1.0, total_design_capacity)
        
        # Start/stop ejectors based on load
        for eid, ejector in ejectors.items():
            if load_factor > 0.3 and not ejector.is_operating:
                commands[eid] = True  # Start if significant load
            elif load_factor < 0.1 and ejector.is_operating:
                # Keep at least one ejector running
                running_count = sum(1 for e in ejectors.values() if e.is_operating)
                if running_count > 1:
                    commands[eid] = False  # Stop if low load and others running
        
        return commands
    
    def _sequential_control(self,
                           ejectors: Dict[str, SteamJetEjector],
                           pressure: float,
                           demand: float) -> Dict[str, bool]:
        """Sequential control strategy - start ejectors in sequence"""
        commands = {}
        
        # Sort ejectors by priority (could be based on efficiency, condition, etc.)
        sorted_ejectors = sorted(ejectors.items(), 
                               key=lambda x: x[1].overall_performance_factor, 
                               reverse=True)
        
        # Determine how many ejectors needed
        single_capacity = sorted_ejectors[0][1].config.design_capacity if sorted_ejectors else 25.0
        ejectors_needed = max(1, int(np.ceil(demand / single_capacity)))
        ejectors_needed = min(ejectors_needed, len(sorted_ejectors))
        
        # Start/stop ejectors sequentially
        for i, (eid, ejector) in enumerate(sorted_ejectors):
            if i < ejectors_needed and not ejector.is_operating:
                commands[eid] = True  # Start needed ejector
            elif i >= ejectors_needed and ejector.is_operating:
                commands[eid] = False  # Stop unneeded ejector
        
        return commands
    
    def _rotate_ejectors(self, available_ejectors: List[str]) -> Dict[str, bool]:
        """Rotate lead/lag ejectors for even wear"""
        commands = {}
        
        if len(available_ejectors) < 2:
            return commands
        
        # Find current positions
        try:
            lead_index = available_ejectors.index(self.lead_ejector_id)
            lag_index = available_ejectors.index(self.lag_ejector_id) if self.lag_ejector_id else -1
        except ValueError:
            # Reset if current ejectors not available
            self.lead_ejector_id = available_ejectors[0]
            self.lag_ejector_id = available_ejectors[1] if len(available_ejectors) > 1 else None
            return commands
        
        # Rotate positions
        new_lead_index = (lead_index + 1) % len(available_ejectors)
        new_lag_index = (lag_index + 1) % len(available_ejectors) if lag_index >= 0 else -1
        
        # Ensure lead and lag are different
        if new_lag_index == new_lead_index:
            new_lag_index = (new_lag_index + 1) % len(available_ejectors)
        
        # Update assignments
        old_lead = self.lead_ejector_id
        old_lag = self.lag_ejector_id
        
        self.lead_ejector_id = available_ejectors[new_lead_index]
        self.lag_ejector_id = available_ejectors[new_lag_index] if new_lag_index >= 0 else None
        
        # Generate rotation commands (stop old, start new)
        if old_lead != self.lead_ejector_id:
            commands[old_lead] = False  # Stop old lead
            commands[self.lead_ejector_id] = True  # Start new lead
        
        return commands


@auto_register("SECONDARY", "condenser", id_source="config.system_id")
class VacuumSystem:
    """
    Complete vacuum system model for PWR condenser
    
    This model implements:
    1. Multiple steam jet ejector coordination
    2. Air mass balance in condenser
    3. Automatic control logic
    4. System performance monitoring
    5. Alarm and trip logic
    6. Motive steam supply effects
    
    Physical Models Used:
    - Air mass balance: dm/dt = in-leakage - removal
    - Pressure calculation: Ideal gas law in condenser volume
    - Ejector performance: Individual ejector models
    - Control logic: Plant operating procedures
    """
    
    def __init__(self, config: Optional[VacuumSystemConfig] = None):
        """Initialize vacuum system model"""

        if config is None:
            # Create default configuration with two ejectors
            ejector_configs = [
                SteamEjectorConfig(ejector_id="SJE-001", ejector_type="two_stage"),
                SteamEjectorConfig(ejector_id="SJE-002", ejector_type="two_stage")
            ]
            config = VacuumSystemConfig(ejector_configs=ejector_configs)
        
        self.config = config
        
        # Create ejector objects
        self.ejectors = {}
        if config.ejector_configs:
            for ejector_config in config.ejector_configs:
                self.ejectors[ejector_config.ejector_id] = SteamJetEjector(ejector_config)
        
        # Control system
        self.control_logic = VacuumControlLogic(config)
        
        # System state
        self.condenser_pressure = 0.007        # MPa total condenser pressure
        self.air_partial_pressure = 0.0005    # MPa air partial pressure
        self.steam_partial_pressure = 0.0065  # MPa steam partial pressure
        self.total_air_removal_rate = 0.0     # kg/s total air removal
        self.total_steam_consumption = 0.0    # kg/s total motive steam
        
        # Air leakage and mass balance
        self.current_air_leakage = config.base_air_leakage
        self.air_mass_in_condenser = 0.1      # kg air mass in condenser
        
        # Motive steam supply
        self.motive_steam_pressure = config.motive_steam_header_pressure
        self.motive_steam_temperature = config.motive_steam_temperature
        self.motive_steam_available = True
        
        # Performance tracking
        self.system_efficiency = 1.0          # Overall system efficiency
        self.availability_factor = 1.0        # System availability
        self.operating_hours = 0.0            # Total system operating hours
        
        # Alarms and trips
        self.alarms = {
            'high_pressure': False,
            'low_motive_pressure': False,
            'ejector_failure': False,
            'excessive_air_leakage': False
        }
        self.trips = {
            'high_pressure_trip': False
        }
    
    def calculate_air_mass_balance(self,
                                 air_leakage_rate: float,
                                 total_removal_rate: float,
                                 dt: float) -> Dict[str, float]:
        """
        Calculate air mass balance in condenser
        
        Physical Basis:
        - Mass conservation: dm/dt = m_in - m_out
        - Ideal gas law: P = (m/V) * R * T
        
        Args:
            air_leakage_rate: Air in-leakage rate (kg/s)
            total_removal_rate: Total air removal rate (kg/s)
            dt: Time step (hours)
            
        Returns:
            Dictionary with air mass balance results
        """
        # Convert time step to seconds
        dt_seconds = dt * 3600.0
        
        # Air mass change rate
        air_mass_change_rate = air_leakage_rate - total_removal_rate
        
        # Update air mass in condenser
        new_air_mass = self.air_mass_in_condenser + air_mass_change_rate * dt_seconds
        new_air_mass = max(0.001, new_air_mass)  # Minimum air mass
        
        # Calculate air partial pressure using ideal gas law
        # P = (m/V) * R * T, where R = 287 J/kg/K for air
        condenser_temp = 39.0 + 273.15  # K (approximate condenser temperature)
        air_density = new_air_mass / self.config.condenser_volume
        new_air_partial_pressure = (air_density * 287.0 * condenser_temp) / 1e6  # Convert to MPa
        
        # Limit air partial pressure to reasonable range
        new_air_partial_pressure = np.clip(new_air_partial_pressure, 0.0001, 0.005)
        
        # Update state
        self.air_mass_in_condenser = new_air_mass
        self.air_partial_pressure = new_air_partial_pressure
        
        return {
            'air_mass': new_air_mass,
            'air_partial_pressure': new_air_partial_pressure,
            'air_mass_change_rate': air_mass_change_rate,
            'air_leakage_rate': air_leakage_rate,
            'air_removal_rate': total_removal_rate
        }
    
    def update_air_leakage(self, dt: float) -> float:
        """
        Update air in-leakage rate (increases over time due to seal degradation)
        
        Args:
            dt: Time step (hours)
            
        Returns:
            Updated air leakage rate (kg/s)
        """
        # Air leakage increases over time due to seal degradation
        leakage_increase = self.config.leakage_degradation_rate * dt
        self.current_air_leakage += leakage_increase
        
        # Limit maximum leakage
        max_leakage = self.config.base_air_leakage * 3.0  # 3x base leakage maximum
        self.current_air_leakage = min(self.current_air_leakage, max_leakage)
        
        return self.current_air_leakage
    
    def calculate_required_capacity(self, target_pressure: float) -> float:
        """
        Calculate required air removal capacity to maintain target pressure
        
        Args:
            target_pressure: Target condenser pressure (MPa)
            
        Returns:
            Required air removal capacity (kg/s)
        """
        # Simple PI controller for pressure control
        pressure_error = self.condenser_pressure - target_pressure
        
        # Proportional term
        kp = 50.0  # Proportional gain
        proportional = kp * pressure_error
        
        # Base capacity to handle air leakage
        base_capacity = self.current_air_leakage
        
        # Total required capacity
        required_capacity = base_capacity + proportional
        
        # Limit to reasonable range
        max_capacity = sum(e.config.design_capacity for e in self.ejectors.values())
        required_capacity = np.clip(required_capacity, 0.0, max_capacity * 1.2)
        
        return required_capacity
    
    def update_alarms_and_trips(self) -> None:
        """Update alarm and trip states"""
        # High pressure alarm and trip
        self.alarms['high_pressure'] = self.condenser_pressure > self.config.high_pressure_alarm
        self.trips['high_pressure_trip'] = self.condenser_pressure > self.config.high_pressure_trip
        
        # Low motive steam pressure
        self.alarms['low_motive_pressure'] = (self.motive_steam_pressure < 
                                            self.config.low_motive_pressure_alarm)
        
        # Ejector failure (no ejectors running)
        running_ejectors = sum(1 for e in self.ejectors.values() if e.is_operating)
        self.alarms['ejector_failure'] = running_ejectors == 0 and self.motive_steam_available
        
        # Excessive air leakage
        leakage_ratio = self.current_air_leakage / self.config.base_air_leakage
        self.alarms['excessive_air_leakage'] = leakage_ratio > 2.0
    
    def update_state(self,
                    target_pressure: float,
                    motive_steam_pressure: float,
                    motive_steam_temperature: float,
                    dt: float) -> Dict[str, float]:
        """
        Update vacuum system state for one time step
        
        Args:
            target_pressure: Target condenser pressure (MPa)
            motive_steam_pressure: Available motive steam pressure (MPa)
            motive_steam_temperature: Motive steam temperature (°C)
            dt: Time step (hours)
            
        Returns:
            Dictionary with vacuum system performance results
        """
        # Update motive steam conditions
        self.motive_steam_pressure = motive_steam_pressure - self.config.steam_pressure_drop
        self.motive_steam_temperature = motive_steam_temperature
        self.motive_steam_available = self.motive_steam_pressure > self.config.low_motive_pressure_alarm
        
        # Update air leakage
        self.update_air_leakage(dt)
        
        # Calculate required air removal capacity
        required_capacity = self.calculate_required_capacity(target_pressure)
        
        # Update control logic
        control_commands = self.control_logic.update_control_logic(
            self.ejectors, self.condenser_pressure, required_capacity, dt
        )
        
        # Execute control commands
        for ejector_id, start_command in control_commands.items():
            if ejector_id in self.ejectors:
                if start_command:
                    self.ejectors[ejector_id].start_ejector(self.motive_steam_pressure)
                else:
                    self.ejectors[ejector_id].stop_ejector()
        
        # Update individual ejectors
        total_capacity = 0.0
        total_steam_consumption = 0.0
        ejector_results = {}
        
        for ejector_id, ejector in self.ejectors.items():
            # Distribute required capacity among running ejectors
            running_ejectors = [e for e in self.ejectors.values() if e.is_operating]
            ejector_capacity_request = (required_capacity / max(1, len(running_ejectors)) 
                                      if ejector.is_operating else 0.0)
            
            result = ejector.update_state(
                suction_pressure=self.condenser_pressure,
                required_capacity=ejector_capacity_request,
                motive_steam_pressure=self.motive_steam_pressure,
                motive_steam_temperature=self.motive_steam_temperature,
                dt=dt
            )
            
            ejector_results[ejector_id] = result
            total_capacity += result['capacity']
            total_steam_consumption += result['motive_steam_flow']
        
        # Update air mass balance
        air_balance = self.calculate_air_mass_balance(
            self.current_air_leakage, total_capacity, dt
        )
        
        # Update total condenser pressure
        # Assume steam partial pressure is relatively constant
        self.steam_partial_pressure = max(0.005, target_pressure - self.air_partial_pressure)
        self.condenser_pressure = self.steam_partial_pressure + self.air_partial_pressure
        
        # Update system performance metrics
        self.total_air_removal_rate = total_capacity
        self.total_steam_consumption = total_steam_consumption
        self.operating_hours += dt
        
        # Calculate system efficiency
        total_design_capacity = sum(e.config.design_capacity for e in self.ejectors.values())
        self.system_efficiency = (total_capacity / max(1.0, total_design_capacity) 
                                if total_design_capacity > 0 else 0.0)
        
        # Update alarms and trips
        self.update_alarms_and_trips()
        
        return {
            # System performance
            'condenser_pressure': self.condenser_pressure,
            'air_partial_pressure': self.air_partial_pressure,
            'steam_partial_pressure': self.steam_partial_pressure,
            'total_air_removal_rate': self.total_air_removal_rate,
            'total_steam_consumption': self.total_steam_consumption,
            'system_efficiency': self.system_efficiency,
            
            # Air balance
            'air_leakage_rate': self.current_air_leakage,
            'air_mass_in_condenser': self.air_mass_in_condenser,
            
            # Motive steam
            'motive_steam_pressure': self.motive_steam_pressure,
            'motive_steam_temperature': self.motive_steam_temperature,
            'motive_steam_available': self.motive_steam_available,
            
            # Control system
            'lead_ejector': self.control_logic.lead_ejector_id,
            'lag_ejector': self.control_logic.lag_ejector_id,
            'rotation_timer': self.control_logic.rotation_timer,
            
            # Individual ejectors
            'ejector_results': ejector_results,
            
            # Alarms and trips
            'alarms': self.alarms.copy(),
            'trips': self.trips.copy()
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'vacuum_system_pressure': self.condenser_pressure,
            'vacuum_system_air_pressure': self.air_partial_pressure,
            'vacuum_system_air_removal': self.total_air_removal_rate,
            'vacuum_system_steam_consumption': self.total_steam_consumption,
            'vacuum_system_efficiency': self.system_efficiency,
            'vacuum_system_air_leakage': self.current_air_leakage,
            'vacuum_system_operating_hours': self.operating_hours
        }
        
        '''
        # Add individual ejector states
        for ejector in self.ejectors.values():
            state_dict.update(ejector.get_state_dict())
        '''
        return state_dict
    
    def reset(self) -> None:
        """Reset vacuum system to initial conditions"""
        self.condenser_pressure = 0.007
        self.air_partial_pressure = 0.0005
        self.steam_partial_pressure = 0.0065
        self.total_air_removal_rate = 0.0
        self.total_steam_consumption = 0.0
        self.current_air_leakage = self.config.base_air_leakage
        self.air_mass_in_condenser = 0.1
        self.operating_hours = 0.0
        self.alarms = {key: False for key in self.alarms}
        self.trips = {key: False for key in self.trips}
        
        # Reset individual ejectors
        for ejector in self.ejectors.values():
            ejector.reset()
        
        # Reset control logic
        self.control_logic.lead_ejector_id = None
        self.control_logic.lag_ejector_id = None
        self.control_logic.rotation_timer = 0.0


# Example usage and testing
if __name__ == "__main__":
    # Create vacuum system with two ejectors
    ejector_configs = [
        SteamEjectorConfig(ejector_id="SJE-001", design_capacity=25.0),
        SteamEjectorConfig(ejector_id="SJE-002", design_capacity=25.0)
    ]
    
    config = VacuumSystemConfig(
        ejector_configs=ejector_configs,
        control_strategy="lead_lag"
    )
    
    vacuum_system = VacuumSystem(config)
    
    print("Vacuum System Model - Parameter Validation")
    print("=" * 50)
    print(f"System ID: {config.system_id}")
    print(f"Number of Ejectors: {len(vacuum_system.ejectors)}")
    print(f"Control Strategy: {config.control_strategy}")
    print(f"Total Design Capacity: {sum(e.config.design_capacity for e in vacuum_system.ejectors.values())} kg/s")
    print()
    
    # Test system operation
    for hour in range(48):  # 48 hours
        result = vacuum_system.update_state(
            target_pressure=0.007,      # MPa target pressure
            motive_steam_pressure=1.2,  # MPa motive steam pressure
            motive_steam_temperature=185.0,  # °C motive steam temperature
            dt=1.0                      # 1 hour time step
        )
        
        if hour % 8 == 0:  # Print every 8 hours
            print(f"Hour {hour}:")
            print(f"  Condenser Pressure: {result['condenser_pressure']:.4f} MPa")
            print(f"  Air Removal Rate: {result['total_air_removal_rate']:.2f} kg/s")
            print(f"  Steam Consumption: {result['total_steam_consumption']:.2f} kg/s")
            print(f"  Lead Ejector: {result['lead_ejector']}")
            print(f"  System Efficiency: {result['system_efficiency']:.3f}")
            
            # Show ejector status
            for eid, ejector_result in result['ejector_results'].items():
                status = "Running" if ejector_result['is_operating'] else "Stopped"
                print(f"    {eid}: {status}, {ejector_result['capacity']:.1f} kg/s")
            print()
