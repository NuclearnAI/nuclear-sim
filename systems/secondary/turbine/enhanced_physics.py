"""
Enhanced Turbine Physics Model for PWR Steam Turbine

This module implements the main enhanced turbine physics model that orchestrates
all turbine subsystems following the condenser's proven architectural pattern.

Parameter Sources:
- Steam Turbine Theory and Practice (Kearton)
- Power Plant Engineering (Black & Veatch)
- GE Steam Turbine Design Manual
- Advanced turbine control systems

Physical Basis:
- Integrated multi-stage steam expansion
- Rotor dynamics and mechanical modeling
- Thermal stress and expansion effects
- Protection systems and trip logic
- Performance optimization and control
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Import state management interfaces
from simulator.state import auto_register 

# Import heat flow tracking
from ..heat_flow_tracker import HeatFlowProvider, ThermodynamicProperties

from .stage_system import TurbineStageSystem
from .rotor_dynamics import RotorDynamicsModel
from .turbine_bearing_lubrication import TurbineBearingLubricationSystem, integrate_lubrication_with_turbine
from .config import TurbineConfig, TurbineThermalStressConfig, TurbineProtectionConfig
from ..component_descriptions import TURBINE_COMPONENT_DESCRIPTIONS

warnings.filterwarnings("ignore")


class MetalTemperatureTracker:
    """
    Metal temperature tracking system - analogous to specialized monitoring
    
    This model implements:
    1. Multi-point temperature monitoring
    2. Thermal gradient calculations
    3. Stress analysis
    4. Thermal shock protection
    """
    
    def __init__(self, config: TurbineThermalStressConfig):
        """Initialize metal temperature tracker"""
        self.config = config
        
        # Temperature monitoring points
        self.rotor_temperatures = [450.0] * 8    # °C rotor temperatures at 8 points
        self.casing_temperatures = [380.0] * 6   # °C casing temperatures at 6 points
        self.blade_temperatures = [500.0] * 14   # °C blade temperatures (8 HP + 6 LP)
        
        # Thermal gradients
        self.rotor_gradients = [0.0] * 7         # °C/cm gradients between points
        self.casing_gradients = [0.0] * 5        # °C/cm gradients between points
        
        # Thermal stress
        self.thermal_stress_levels = [0.0] * 8   # Pa thermal stress at critical points
        self.max_thermal_stress = 0.0            # Pa maximum thermal stress
        
        # Thermal shock monitoring
        self.temperature_rates = [0.0] * 8       # °C/min temperature change rates
        self.thermal_shock_risk = 0.0            # Risk factor (0-1)
        
    def update_temperatures(self,
                          steam_temperatures: List[float],
                          ambient_temperature: float,
                          dt: float) -> Dict[str, float]:
        """
        Update metal temperatures based on steam conditions
        
        Args:
            steam_temperatures: Steam temperatures at various stages (°C)
            ambient_temperature: Ambient temperature (°C)
            dt: Time step (hours)
            
        Returns:
            Dictionary with temperature results
        """
        # Update rotor temperatures (first-order lag)
        time_constant = self.config.thermal_time_constant / 3600.0  # Convert to hours
        
        for i in range(len(self.rotor_temperatures)):
            if i < len(steam_temperatures):
                target_temp = steam_temperatures[i] - 50.0  # Rotor runs cooler than steam
            else:
                target_temp = ambient_temperature + 100.0   # Minimum rotor temperature
            
            temp_change = (target_temp - self.rotor_temperatures[i]) / time_constant * dt
            
            # Rate limiting for thermal shock protection
            max_rate = 5.0 * dt  # 5°C/hour maximum rate
            temp_change = np.clip(temp_change, -max_rate, max_rate)
            
            self.rotor_temperatures[i] += temp_change
            self.temperature_rates[i] = temp_change / dt * 60.0  # °C/min
        
        # Update casing temperatures
        for i in range(len(self.casing_temperatures)):
            if i < len(steam_temperatures):
                target_temp = steam_temperatures[i] - 80.0  # Casing runs cooler than steam
            else:
                target_temp = ambient_temperature + 50.0
            
            temp_change = (target_temp - self.casing_temperatures[i]) / time_constant * dt
            temp_change = np.clip(temp_change, -3.0 * dt, 3.0 * dt)  # 3°C/hour max
            self.casing_temperatures[i] += temp_change
        
        # Update blade temperatures
        for i in range(len(self.blade_temperatures)):
            if i < len(steam_temperatures):
                target_temp = steam_temperatures[i] - 20.0  # Blades run close to steam temp
            else:
                target_temp = ambient_temperature + 150.0
            
            temp_change = (target_temp - self.blade_temperatures[i]) / (time_constant * 0.5) * dt
            temp_change = np.clip(temp_change, -10.0 * dt, 10.0 * dt)  # 10°C/hour max
            self.blade_temperatures[i] += temp_change
        
        # Calculate thermal gradients
        for i in range(len(self.rotor_gradients)):
            distance = 1.0  # 1 meter between measurement points
            self.rotor_gradients[i] = abs(self.rotor_temperatures[i+1] - self.rotor_temperatures[i]) / (distance * 100)  # °C/cm
        
        for i in range(len(self.casing_gradients)):
            distance = 1.5  # 1.5 meters between casing points
            self.casing_gradients[i] = abs(self.casing_temperatures[i+1] - self.casing_temperatures[i]) / (distance * 100)  # °C/cm
        
        # Calculate thermal stress
        for i in range(len(self.thermal_stress_levels)):
            temp_diff = self.rotor_temperatures[i] - ambient_temperature
            thermal_strain = self.config.thermal_expansion_coeff * temp_diff
            # Apply constraint factor - turbine rotors are designed to expand freely
            # Only about 10% of thermal expansion creates stress due to design constraints
            constraint_factor = 0.1
            self.thermal_stress_levels[i] = thermal_strain * self.config.elastic_modulus * constraint_factor
        
        self.max_thermal_stress = max(self.thermal_stress_levels)
        
        # Calculate thermal shock risk
        max_temp_rate = max(abs(rate) for rate in self.temperature_rates)
        max_gradient = max(max(self.rotor_gradients), max(self.casing_gradients))
        
        rate_risk = min(1.0, max_temp_rate / 10.0)  # Risk increases above 10°C/min
        gradient_risk = min(1.0, max_gradient / self.config.max_thermal_gradient)
        stress_risk = min(1.0, self.max_thermal_stress / self.config.max_thermal_stress)
        
        self.thermal_shock_risk = max(rate_risk, gradient_risk, stress_risk)
        
        return {
            'max_rotor_temperature': max(self.rotor_temperatures),
            'max_casing_temperature': max(self.casing_temperatures),
            'max_blade_temperature': max(self.blade_temperatures),
            'max_thermal_gradient': max_gradient,
            'max_thermal_stress': self.max_thermal_stress,
            'thermal_shock_risk': self.thermal_shock_risk,
            'max_temperature_rate': max_temp_rate
        }


class TurbineProtectionSystem:
    """
    Turbine protection system - analogous to condenser protection
    
    This model implements:
    1. Multi-parameter trip monitoring
    2. Emergency action sequences
    3. Protection logic coordination
    4. Safety system validation
    5. Maintenance event publishing for post-trip actions
    """
    
    def __init__(self, config: TurbineProtectionConfig):
        """Initialize turbine protection system"""
        self.config = config
        
        # Trip states
        self.trip_active = False
        self.trip_reasons = []
        self.trip_time = 0.0
        
        # Trip timers
        self.trip_timers = {
            'overspeed': 0.0,
            'vibration': 0.0,
            'bearing_temp': 0.0,
            'thrust_bearing': 0.0,
            'low_vacuum': 0.0,
            'thermal_stress': 0.0
        }
        
        # Emergency actions status
        self.emergency_actions = {
            'main_steam_valves_closed': False,
            'steam_dump_active': False,
            'turning_gear_engaged': False,
            'emergency_seal_steam': False,
            'generator_breaker_open': False
        }
        
        # Protection system health
        self.system_available = True
        self.last_test_time = 0.0
        
        # Maintenance event bus integration
        self.maintenance_event_bus = None
        self.component_id = "TURBINE_SYSTEM"  # Default component ID
    
    def set_maintenance_event_bus(self, event_bus, component_id: str = None):
        """
        Set the maintenance event bus for publishing trip events
        
        Args:
            event_bus: MaintenanceEventBus instance
            component_id: Component identifier for events
        """
        self.maintenance_event_bus = event_bus
        if component_id:
            self.component_id = component_id
    
    def _publish_trip_event(self, trip_type: str, trip_value: float, trip_setpoint: float, 
                           severity: str = "HIGH", recommended_actions: List[str] = None):
        """
        Publish a protection trip event to the maintenance system
        
        Args:
            trip_type: Type of trip that occurred
            trip_value: Current value that caused the trip
            trip_setpoint: Setpoint that was exceeded
            severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
            recommended_actions: List of recommended maintenance actions
        """
        if not self.maintenance_event_bus:
            return
        
        if recommended_actions is None:
            # Default recommended actions based on trip type
            action_map = {
                'overspeed': ['rotor_inspection', 'governor_system_check', 'overspeed_test'],
                'vibration': ['vibration_analysis', 'rotor_balancing', 'bearing_inspection'],
                'bearing_temp': ['bearing_inspection', 'lubrication_system_check', 'cooling_system_check'],
                'thrust_bearing': ['bearing_alignment', 'thrust_bearing_adjustment', 'bearing_clearance_check'],
                'low_vacuum': ['vacuum_system_check', 'condenser_tube_inspection', 'vacuum_leak_detection'],
                'thermal_stress': ['thermal_stress_analysis', 'rotor_inspection', 'blade_inspection']
            }
            
            # Find matching actions
            recommended_actions = []
            for key, actions in action_map.items():
                if key in trip_type:
                    recommended_actions = actions
                    break
            
            if not recommended_actions:
                recommended_actions = ['post_trip_inspection', 'trip_root_cause_analysis']
        
        # Determine priority based on severity
        priority_map = {
            'CRITICAL': 'CRITICAL',
            'HIGH': 'HIGH', 
            'MEDIUM': 'MEDIUM',
            'LOW': 'LOW'
        }
        priority = priority_map.get(severity, 'HIGH')
        
        # Publish the event
        self.maintenance_event_bus.publish(
            'protection_trip_occurred',
            self.component_id,
            {
                'trip_type': trip_type,
                'trip_value': trip_value,
                'trip_setpoint': trip_setpoint,
                'severity': severity,
                'recommended_actions': recommended_actions,
                'system_type': 'turbine_protection',
                'emergency_actions_taken': list(self.emergency_actions.keys())
            },
            priority=priority
        )
        
        print(f"TURBINE PROTECTION: Published trip event - {trip_type} ({severity})")
    
    def _publish_trip_events(self, trip_conditions: Dict[str, bool], 
                            rotor_speed: float, vibration_level: float, 
                            bearing_temperatures: List[float], thrust_displacement: float,
                            vacuum_pressure: float, thermal_stress: float):
        """
        Publish maintenance events for all trips that occurred
        
        Args:
            trip_conditions: Dictionary of trip conditions that are active
            rotor_speed: Current rotor speed (RPM)
            vibration_level: Current vibration level (mils)
            bearing_temperatures: Current bearing temperatures (°C)
            thrust_displacement: Current thrust displacement (mm)
            vacuum_pressure: Current vacuum pressure (MPa)
            thermal_stress: Current thermal stress (Pa)
        """
        if not self.maintenance_event_bus:
            return
        
        for trip_type, is_active in trip_conditions.items():
            if not is_active:
                continue
                
            # Extract trip value and setpoint based on trip type
            trip_value = 0.0
            trip_setpoint = 0.0
            severity = "HIGH"
            
            if trip_type == 'overspeed':
                trip_value = rotor_speed
                trip_setpoint = self.config.overspeed_trip
                severity = "CRITICAL"
            elif trip_type == 'vibration':
                trip_value = vibration_level
                trip_setpoint = self.config.vibration_trip
                severity = "HIGH"
            elif trip_type == 'bearing_temp':
                trip_value = max(bearing_temperatures) if bearing_temperatures else 0.0
                trip_setpoint = self.config.bearing_temp_trip
                severity = "HIGH"
            elif trip_type == 'thrust_bearing':
                trip_value = thrust_displacement
                trip_setpoint = self.config.thrust_bearing_trip
                severity = "CRITICAL"
            elif trip_type == 'low_vacuum':
                trip_value = vacuum_pressure
                trip_setpoint = self.config.low_vacuum_trip
                severity = "MEDIUM"
            elif trip_type == 'thermal_stress':
                trip_value = thermal_stress
                trip_setpoint = self.config.max_thermal_stress
                severity = "CRITICAL"
            
            # Publish the event for this specific trip
            self._publish_trip_event(trip_type, trip_value, trip_setpoint, severity)
        
    def check_trip_conditions(self,
                            rotor_speed: float,
                            vibration_level: float,
                            bearing_temperatures: List[float],
                            thrust_displacement: float,
                            vacuum_pressure: float,
                            thermal_stress: float,
                            dt: float) -> Dict[str, bool]:
        """
        Check all trip conditions
        
        Args:
            rotor_speed: Current rotor speed (RPM)
            vibration_level: Maximum vibration level (mils)
            bearing_temperatures: Bearing temperatures (°C)
            thrust_displacement: Thrust bearing displacement (mm)
            vacuum_pressure: Condenser pressure (MPa)
            thermal_stress: Maximum thermal stress (Pa)
            dt: Time step (hours)
            
        Returns:
            Dictionary with trip status
        """
        trips = {}
        dt_seconds = dt * 3600.0
        
        # Overspeed trip
        if rotor_speed > self.config.overspeed_trip:
            self.trip_timers['overspeed'] += dt_seconds
            if self.trip_timers['overspeed'] >= self.config.overspeed_delay:
                trips['overspeed'] = True
                if 'Overspeed' not in self.trip_reasons:
                    self.trip_reasons.append('Overspeed')
        else:
            self.trip_timers['overspeed'] = 0.0
        
        # Vibration trip
        if vibration_level > self.config.vibration_trip:
            self.trip_timers['vibration'] += dt_seconds
            if self.trip_timers['vibration'] >= self.config.vibration_delay:
                trips['vibration'] = True
                if 'High Vibration' not in self.trip_reasons:
                    self.trip_reasons.append('High Vibration')
        else:
            self.trip_timers['vibration'] = 0.0
        
        # Bearing temperature trip
        max_bearing_temp = max(bearing_temperatures) if bearing_temperatures else 0.0
        if max_bearing_temp > self.config.bearing_temp_trip:
            self.trip_timers['bearing_temp'] += dt_seconds
            if self.trip_timers['bearing_temp'] >= self.config.bearing_temp_delay:
                trips['bearing_temp'] = True
                if 'High Bearing Temperature' not in self.trip_reasons:
                    self.trip_reasons.append('High Bearing Temperature')
        else:
            self.trip_timers['bearing_temp'] = 0.0
        
        # Thrust bearing trip
        if thrust_displacement > self.config.thrust_bearing_trip:
            trips['thrust_bearing'] = True
            if 'Thrust Bearing Displacement' not in self.trip_reasons:
                self.trip_reasons.append('Thrust Bearing Displacement')
        
        # Low vacuum trip
        if vacuum_pressure > self.config.low_vacuum_trip:
            trips['low_vacuum'] = True
            if 'Low Vacuum' not in self.trip_reasons:
                self.trip_reasons.append('Low Vacuum')
        
        # Thermal stress trip
        if thermal_stress > self.config.max_thermal_stress:
            trips['thermal_stress'] = True
            if 'High Thermal Stress' not in self.trip_reasons:
                self.trip_reasons.append('High Thermal Stress')
        
        # Overall trip status
        previous_trip_state = self.trip_active
        self.trip_active = any(trips.values())
        
        # Publish trip events if new trips occurred
        if self.trip_active and not previous_trip_state:
            self._publish_trip_events(trips, rotor_speed, vibration_level, 
                                    bearing_temperatures, thrust_displacement, 
                                    vacuum_pressure, thermal_stress)

        if self.trip_active:
            print(f"Trip active: {self.trip_reasons}, time: {self.trip_time}")

        return trips
    
    def execute_emergency_actions(self, trip_types: List[str]) -> Dict[str, bool]:
        """
        Execute emergency actions based on trip types
        
        Args:
            trip_types: List of active trip types
            
        Returns:
            Dictionary with emergency action status
        """
        if not self.trip_active:
            return self.emergency_actions
        
        # Close main steam valves (always on trip)
        self.emergency_actions['main_steam_valves_closed'] = True
        
        # Open generator breaker
        self.emergency_actions['generator_breaker_open'] = True
        
        # Steam dump for overspeed
        if 'overspeed' in trip_types and self.config.enable_steam_dump:
            self.emergency_actions['steam_dump_active'] = True
        
        # Emergency seal steam
        if self.config.emergency_seal_steam:
            self.emergency_actions['emergency_seal_steam'] = True
        
        # Turning gear engagement (after speed drops)
        if self.config.enable_turning_gear:
            # Engage turning gear when speed drops below 200 RPM
            # This would be handled by the rotor dynamics system
            pass
        
        return self.emergency_actions
    
    def reset_protection_system(self) -> None:
        """Reset protection system after trip clearance"""
        self.trip_active = False
        self.trip_reasons = []
        self.trip_time = 0.0
        self.trip_timers = {key: 0.0 for key in self.trip_timers}
        self.emergency_actions = {key: False for key in self.emergency_actions}

@auto_register("SECONDARY", "turbine", allow_no_id=True,
               description=TURBINE_COMPONENT_DESCRIPTIONS['enhanced_turbine_physics'])
class EnhancedTurbinePhysics(HeatFlowProvider):
    """
    Enhanced turbine physics model - analogous to EnhancedCondenserPhysics
    
    This model integrates:
    1. Multi-stage turbine system coordination
    2. Rotor dynamics and mechanical modeling
    3. Thermal stress and expansion tracking
    4. Protection systems and trip logic
    5. Performance optimization and control
    6. Predictive maintenance capabilities
    
    Physical Models Used:
    - Stage-by-stage steam expansion with extraction flows
    - Rotor speed dynamics with bearing interactions
    - Thermal stress analysis with material properties
    - Protection logic with emergency response
    - Performance degradation with maintenance scheduling
    
    Implements StateProvider interface for automatic state collection.
    """
    
    def __init__(self, config: Optional[TurbineConfig] = None):
        """Initialize enhanced turbine physics model"""
        if config is None:
            config = TurbineConfig()
        
        self.config = config
        
        # Initialize subsystems
        self.stage_system = TurbineStageSystem(config.stage_system)
        self.rotor_dynamics = RotorDynamicsModel(config.rotor_dynamics)
        self.thermal_tracker = MetalTemperatureTracker(config.thermal_stress)
        self.protection_system = TurbineProtectionSystem(config.protection_system)
        
        # Create and integrate turbine bearing lubrication system
        self.bearing_lubrication_system = TurbineBearingLubricationSystem(config.lubrication_system)
        
        # Store reference to lubrication system for direct access
        self.rotor_dynamics.bearing_lubrication_system = self.bearing_lubrication_system
        
        # Integrate lubrication system with this enhanced turbine (not just rotor dynamics)
        integrate_lubrication_with_turbine(self, self.bearing_lubrication_system)
        
        # Create turbine governor system with lubrication
        from .governor_system import TurbineGovernorSystem
        self.governor_system = TurbineGovernorSystem(config.governor_system)
        
        # Enhanced turbine state
        self.total_power_output = 0.0            # MW total electrical power
        self.overall_efficiency = 0.0            # Overall turbine efficiency
        self.steam_rate = 0.0                    # kg/kWh steam rate
        self.heat_rate = 0.0                     # kJ/kWh heat rate
        
        # Performance tracking
        self.performance_factor = 1.0            # Overall performance factor
        self.availability_factor = 1.0           # Availability factor
        self.operating_hours = 0.0               # Total operating hours
        
        # Control state
        self.load_demand = 1.0                   # Load demand (0-1)
        self.control_mode = "automatic"          # Control mode
        
        # Store last update results for get_current_state()
        self.last_update_results = {}
        
        # CRITICAL: Apply initial conditions after creating components
        self._apply_initial_conditions()
        
        print(f"TURBINE: Applied initial conditions from config")
    
    def _apply_initial_conditions(self):
        """Apply unified initial conditions - CLEAN VERSION"""
        ic = self.config.initial_conditions
        
        print(f"TURBINE: Applying unified initial conditions")
        
        # Apply rotor conditions
        if hasattr(self.rotor_dynamics, 'rotor_speed'):
            self.rotor_dynamics.rotor_speed = ic.rotor_speed
            self.rotor_dynamics.rotor_temperature = ic.rotor_temperature
        
        # Apply bearing mechanical conditions (no oil)
        if hasattr(self.rotor_dynamics, 'bearings'):
            bearing_ids = list(self.rotor_dynamics.bearings.keys())
            for i, bearing_id in enumerate(bearing_ids):
                bearing = self.rotor_dynamics.bearings[bearing_id]
                if i < len(ic.bearing_temperatures):
                    bearing.metal_temperature = ic.bearing_temperatures[i]
                if i < len(ic.bearing_vibrations):
                    bearing.vibration_displacement = ic.bearing_vibrations[i]
        
        # Apply unified lubrication system
        if hasattr(self, 'bearing_lubrication_system'):
            self.bearing_lubrication_system.apply_unified_initial_conditions(ic.lubrication_system)
        
        # Apply thermal conditions
        if hasattr(self, 'thermal_tracker'):
            thermal_tracker = self.thermal_tracker
            
            # Apply rotor temperatures
            if hasattr(ic, 'rotor_temperatures') and hasattr(thermal_tracker, 'rotor_temperatures'):
                for i, temp in enumerate(ic.rotor_temperatures):
                    if i < len(thermal_tracker.rotor_temperatures):
                        thermal_tracker.rotor_temperatures[i] = temp
                print(f"    Applied rotor temperatures: {ic.rotor_temperatures}")
            
            # Apply casing temperatures
            if hasattr(ic, 'casing_temperatures') and hasattr(thermal_tracker, 'casing_temperatures'):
                for i, temp in enumerate(ic.casing_temperatures):
                    if i < len(thermal_tracker.casing_temperatures):
                        thermal_tracker.casing_temperatures[i] = temp
                print(f"    Applied casing temperatures: {ic.casing_temperatures}")
            
            # Apply blade temperatures
            if hasattr(ic, 'blade_temperatures') and hasattr(thermal_tracker, 'blade_temperatures'):
                for i, temp in enumerate(ic.blade_temperatures):
                    if i < len(thermal_tracker.blade_temperatures):
                        thermal_tracker.blade_temperatures[i] = temp
                print(f"    Applied blade temperatures: {ic.blade_temperatures}")
        
        # Apply system-level initial conditions
        self.total_power_output = ic.total_power_output
        self.overall_efficiency = ic.overall_efficiency
        self.load_demand = ic.load_demand
        
        print(f"TURBINE: Initial conditions applied successfully")
        
        # Validate that critical initial conditions were applied
        self._validate_initial_conditions_applied()
    
    def _validate_initial_conditions_applied(self):
        """Validate that initial conditions were properly applied"""
        ic = self.config.initial_conditions
        
        print(f"TURBINE: Validating initial conditions application:")
        
        # Validate rotor conditions
        if hasattr(self.rotor_dynamics, 'rotor_speed'):
            expected = ic.rotor_speed
            actual = self.rotor_dynamics.rotor_speed
            if abs(actual - expected) < 1.0:
                print(f"  ✓ Rotor speed: {actual} RPM (expected {expected} RPM)")
            else:
                print(f"  ✗ Rotor speed mismatch: {actual} RPM (expected {expected} RPM)")
        
        if hasattr(self.rotor_dynamics, 'rotor_temperature'):
            expected = ic.rotor_temperature
            actual = self.rotor_dynamics.rotor_temperature
            if abs(actual - expected) < 1.0:
                print(f"  ✓ Rotor temperature: {actual}°C (expected {expected}°C)")
            else:
                print(f"  ✗ Rotor temperature mismatch: {actual}°C (expected {expected}°C)")
        
        # Validate bearing conditions
        if hasattr(self.rotor_dynamics, 'bearings'):
            bearing_ids = list(self.rotor_dynamics.bearings.keys())
            
            for i, bearing_id in enumerate(bearing_ids):
                bearing = self.rotor_dynamics.bearings[bearing_id]
                print(f"  Bearing {bearing_id} verification:")
                
                # Validate bearing temperature
                if i < len(ic.bearing_temperatures):
                    expected = ic.bearing_temperatures[i]
                    actual = bearing.metal_temperature
                    if abs(actual - expected) < 1.0:
                        print(f"    ✓ Temperature: {actual}°C (expected {expected}°C)")
                    else:
                        print(f"    ✗ Temperature mismatch: {actual}°C (expected {expected}°C)")
                
                # Validate bearing vibration
                if i < len(ic.bearing_vibrations):
                    expected = ic.bearing_vibrations[i]
                    actual = bearing.vibration_displacement
                    if abs(actual - expected) < 0.1:
                        print(f"    ✓ Vibration: {actual} mm/s (expected {expected} mm/s)")
                    else:
                        print(f"    ✗ Vibration mismatch: {actual} mm/s (expected {expected} mm/s)")
                
                # Validate oil pressure
                if i < len(ic.bearing_oil_pressures):
                    expected = ic.bearing_oil_pressures[i]
                    actual = bearing.oil_pressure
                    if abs(actual - expected) < 0.01:
                        print(f"    ✓ Oil pressure: {actual} MPa (expected {expected} MPa)")
                    else:
                        print(f"    ✗ Oil pressure mismatch: {actual} MPa (expected {expected} MPa)")
        
        # Validate unified lubrication system
        if hasattr(self, 'bearing_lubrication_system'):
            lubrication_system = self.bearing_lubrication_system
            
            # Validate base contamination
            expected_contamination = ic.lubrication_system.oil_base_contamination
            actual_contamination = lubrication_system.oil_base_contamination
            if abs(actual_contamination - expected_contamination) < 0.1:
                print(f"  ✓ Oil base contamination: {actual_contamination:.1f} ppm (expected {expected_contamination:.1f} ppm)")
            else:
                print(f"  ✗ Oil contamination mismatch: {actual_contamination:.1f} ppm (expected {expected_contamination:.1f} ppm)")
            
            # Validate oil level
            expected_level = ic.lubrication_system.oil_reservoir_level
            actual_level = lubrication_system.oil_level
            if abs(actual_level - expected_level) < 1.0:
                print(f"  ✓ Oil reservoir level: {actual_level:.1f}% (expected {expected_level:.1f}%)")
            else:
                print(f"  ✗ Oil level mismatch: {actual_level:.1f}% (expected {expected_level:.1f}%)")
        
        print(f"TURBINE: Initial conditions validation complete")
        
    def update_state(self,
                    sg_conditions: Dict,
                    load_demand: float,
                    condenser_pressure: float = 0.007,
                    dt: float = 1.0) -> Dict[str, float]:
        """
        Update enhanced turbine state for one time step
        
        ENHANCED: Now uses rich steam generator conditions for improved integration
        
        Args:
            sg_conditions: Rich steam generator conditions dictionary from SG system
            load_demand: Load demand (0-1)
            condenser_pressure: Condenser pressure (MPa)
            dt: Time step (hours)
            
        Returns:
            Dictionary with enhanced turbine performance results
        """
        # STEP 1: Extract steam conditions from SG system
        steam_pressure = sg_conditions['average_steam_pressure']
        steam_temperature = sg_conditions['average_steam_temperature']
        steam_flow = sg_conditions['total_steam_flow']
        steam_quality = sg_conditions['average_steam_quality']
        
        # STEP 1: Extract additional SG data for enhanced calculations
        sg_pressures = sg_conditions.get('sg_pressures', [steam_pressure])
        sg_qualities = sg_conditions.get('sg_steam_qualities', [steam_quality])
        sg_flows = sg_conditions.get('sg_steam_flows', [steam_flow])
        system_availability = sg_conditions.get('system_availability', True)
        
        # Update load demand
        self.load_demand = load_demand
        
        # Define extraction demands (simplified)
        extraction_demands = {
            'HP-3': 25.0 * load_demand,  # kg/s extraction from HP-3
            'HP-4': 30.0 * load_demand,  # kg/s extraction from HP-4
            'HP-5': 20.0 * load_demand,  # kg/s extraction from HP-5
            'LP-1': 15.0 * load_demand,  # kg/s extraction from LP-1
            'LP-2': 10.0 * load_demand,  # kg/s extraction from LP-2
        }
        
        # STEP 2 & 3: Apply SG conditions to stage system with quality and pressure effects
        # Calculate pressure variation effects from individual SG pressures
        pressure_stability_factor = self._calculate_pressure_variation_effects(sg_pressures)
        
        # Update stage system with enhanced SG conditions
        stage_results = self.stage_system.update_state(
            inlet_pressure=steam_pressure,
            inlet_temperature=steam_temperature,
            inlet_flow=steam_flow,
            load_demand=load_demand,
            extraction_demands=extraction_demands,
            steam_quality=steam_quality,  # NEW: Pass actual SG steam quality
            pressure_stability_factor=pressure_stability_factor,  # NEW: Pressure variation effects
            dt=dt
        )
        
        # Calculate applied torque from stage power
        stage_power_mw = stage_results['total_power_output']
        applied_torque = stage_power_mw * 1e6 / (2 * np.pi * 3600 / 60)  # N⋅m at 3600 RPM
        
        # Update rotor dynamics
        rotor_results = self.rotor_dynamics.update_state(
            applied_torque=applied_torque,
            target_speed=3600.0,  # RPM rated speed
            steam_temperature=steam_temperature,
            steam_thrust=100.0 * load_demand,  # kN steam thrust
            oil_inlet_temperature=40.0,  # °C oil temperature
            oil_contamination=5.0,  # ppm oil contamination
            dt=dt
        )
        
        # Get stage temperatures for thermal analysis
        stage_temps = []
        for stage_id, stage_result in stage_results['stage_results'].items():
            stage_temps.append(stage_result['outlet_temperature'])
        
        # Update thermal tracker
        thermal_results = self.thermal_tracker.update_temperatures(
            steam_temperatures=stage_temps,
            ambient_temperature=25.0,  # °C ambient temperature
            dt=dt
        )
        
        # Check protection system
        bearing_temps = [result['metal_temperature'] for result in rotor_results['bearing_results'].values()]
        
        trip_conditions = self.protection_system.check_trip_conditions(
            rotor_speed=rotor_results['rotor_speed'],
            vibration_level=rotor_results['vibration_displacement'],
            bearing_temperatures=bearing_temps,
            thrust_displacement=rotor_results['thermal_expansion'],
            vacuum_pressure=condenser_pressure,
            thermal_stress=thermal_results['max_thermal_stress'],
            dt=dt
        )
        
        # Execute emergency actions if needed
        if any(trip_conditions.values()):
            emergency_actions = self.protection_system.execute_emergency_actions(
                list(trip_conditions.keys())
            )
            # If tripped, reduce power output
            power_reduction = 0.0 if self.protection_system.trip_active else 1.0
        else:
            emergency_actions = self.protection_system.emergency_actions
            power_reduction = 1.0
        
        # STEP 4: Apply SG system availability effects to turbine performance
        sg_availability_factor = 1.0 if system_availability else 0.5  # 50% power if SG system degraded
        
        # Combine all power reduction factors
        total_power_reduction = power_reduction * sg_availability_factor
        
        self.total_power_output = stage_power_mw * total_power_reduction
        
        self.overall_efficiency = stage_results['overall_efficiency']
        
        # Calculate steam rate and heat rate
        if self.total_power_output > 0:
            self.steam_rate = steam_flow / (self.total_power_output * 1000) * 3600  # kg/MWh
            steam_enthalpy = self._steam_enthalpy(steam_temperature, steam_pressure)
            self.heat_rate = steam_enthalpy * self.steam_rate / 1000  # kJ/kWh
        else:
            self.steam_rate = 0.0
            self.heat_rate = 0.0
        
        # Update performance factors
        stage_efficiency_factor = stage_results['system_efficiency']
        rotor_efficiency_factor = 1.0 - rotor_results['friction_torque'] / max(1.0, applied_torque) * 0.1
        thermal_efficiency_factor = 1.0 - thermal_results['thermal_shock_risk'] * 0.1
        
        self.performance_factor = stage_efficiency_factor * rotor_efficiency_factor * thermal_efficiency_factor
        self.availability_factor = 0.0 if self.protection_system.trip_active else 1.0
        
        # Update operating hours
        self.operating_hours += dt
        
        # Store results for get_current_state()
        self.last_update_results = {
            # Overall turbine performance
            'mechanical_power': self.total_power_output / 0.985,  # Account for generator efficiency
            'electrical_power_gross': self.total_power_output,
            'electrical_power_net': self.total_power_output * 0.98,  # Account for auxiliary power
            'overall_efficiency': self.overall_efficiency,
            'steam_rate': self.steam_rate,
            'heat_rate': self.heat_rate,
            'performance_factor': self.performance_factor,
            'availability_factor': self.availability_factor,
            
            # Stage system results
            'stage_total_power': stage_results['total_power_output'],
            'stage_efficiency': stage_results['overall_efficiency'],
            'total_extraction_flow': stage_results['total_extraction_flow'],
            'stage_results': stage_results['stage_results'],
            
            # Rotor dynamics results
            'rotor_speed': rotor_results['rotor_speed'],
            'rotor_acceleration': rotor_results['rotor_acceleration'],
            'vibration_displacement': rotor_results['vibration_displacement'],
            'vibration_velocity': rotor_results['vibration_velocity'],
            'total_bearing_load': rotor_results['total_bearing_load'],
            'max_bearing_temperature': rotor_results['max_bearing_temperature'],
            'thermal_expansion': rotor_results['thermal_expansion'],
            
            # Thermal results
            'max_metal_temperature': thermal_results['max_rotor_temperature'],
            'max_thermal_stress': thermal_results['max_thermal_stress'],
            'thermal_shock_risk': thermal_results['thermal_shock_risk'],
            
            # Protection system
            'trip_active': self.protection_system.trip_active,
            'trip_reasons': self.protection_system.trip_reasons,
            'emergency_actions': emergency_actions,
            
            # Operating conditions
            'load_demand': self.load_demand,
            'operating_hours': self.operating_hours,
            
            # Legacy compatibility (for existing SecondaryReactorPhysics)
            'condenser_pressure': condenser_pressure,
            'condenser_temperature': self._saturation_temperature(condenser_pressure),
            'effective_steam_flow': steam_flow - stage_results['total_extraction_flow'],
            'hp_power': sum(result['power_output'] for stage_id, result in stage_results['stage_results'].items() if 'HP' in stage_id),
            'lp_power': sum(result['power_output'] for stage_id, result in stage_results['stage_results'].items() if 'LP' in stage_id),
            'hp_exhaust_pressure': 1.2,  # MPa typical HP exhaust
            'hp_exhaust_temperature': self._saturation_temperature(1.2),
            'hp_exhaust_quality': 0.92,
            'lp_inlet_pressure': 1.15,  # MPa typical LP inlet
            'lp_inlet_temperature': 185.0,  # °C after reheat
            'governor_valve_position': load_demand * 100.0,
            'auxiliary_power': self.total_power_output * 0.02  # 2% auxiliary power
        }

        return self.last_update_results

    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'enhanced_turbine_power': self.total_power_output,
            'enhanced_turbine_efficiency': self.overall_efficiency,
            'enhanced_turbine_steam_rate': self.steam_rate,
            'enhanced_turbine_heat_rate': self.heat_rate,
            'enhanced_turbine_performance': self.performance_factor,
            'enhanced_turbine_availability': self.availability_factor,
            'enhanced_turbine_operating_hours': self.operating_hours,
            'enhanced_turbine_load_demand': self.load_demand
        }
        
        # Add subsystem states
        state_dict.update(self.stage_system.get_state_dict())
        state_dict.update(self.rotor_dynamics.get_state_dict())
        
        return state_dict
    
    def get_heat_flows(self) -> Dict[str, float]:
        """
        Get current heat flows for this component (MW)
        
        Returns:
            Dictionary with heat flow values in MW
        """
        # Get steam inlet conditions from last update
        if not self.last_update_results:
            return {
                'steam_enthalpy_input': 0.0,
                'mechanical_work_output': 0.0,
                'exhaust_enthalpy_output': 0.0,
                'extraction_enthalpy_output': 0.0,
                'internal_losses': 0.0
            }
        
        # Calculate steam inlet enthalpy flow
        steam_flow = self.config.design_steam_flow * self.load_demand  # Estimate current steam flow
        steam_enthalpy = self._steam_enthalpy(self.config.design_steam_temperature, self.config.design_steam_pressure)
        steam_enthalpy_input = ThermodynamicProperties.enthalpy_flow_mw(steam_flow, steam_enthalpy)
        
        # Get mechanical work output
        mechanical_work_output = self.last_update_results.get('mechanical_power', self.total_power_output / 0.985)
        
        # Calculate extraction enthalpy flow
        total_extraction_flow = self.last_update_results.get('total_extraction_flow', 0.0)
        extraction_enthalpy = ThermodynamicProperties.steam_enthalpy(200.0, 1.0)  # Typical extraction conditions
        extraction_enthalpy_output = ThermodynamicProperties.enthalpy_flow_mw(total_extraction_flow, extraction_enthalpy)
        
        # Calculate exhaust enthalpy flow
        effective_steam_flow = self.last_update_results.get('effective_steam_flow', steam_flow - total_extraction_flow)
        condenser_pressure = self.last_update_results.get('condenser_pressure', 0.007)
        exhaust_temperature = self._saturation_temperature(condenser_pressure)
        exhaust_enthalpy = ThermodynamicProperties.steam_enthalpy(exhaust_temperature, condenser_pressure, 0.90)
        exhaust_enthalpy_output = ThermodynamicProperties.enthalpy_flow_mw(effective_steam_flow, exhaust_enthalpy)
        
        # Calculate internal losses (approximately 5% of mechanical work)
        internal_losses = mechanical_work_output * 0.05
        
        return {
            'steam_enthalpy_input': steam_enthalpy_input,
            'mechanical_work_output': mechanical_work_output,
            'exhaust_enthalpy_output': exhaust_enthalpy_output,
            'extraction_enthalpy_output': extraction_enthalpy_output,
            'internal_losses': internal_losses
        }
    
    def get_enthalpy_flows(self) -> Dict[str, float]:
        """
        Get current enthalpy flows for this component (MW)
        
        Returns:
            Dictionary with enthalpy flow values in MW
        """
        heat_flows = self.get_heat_flows()
        
        return {
            'inlet_enthalpy_flow': heat_flows['steam_enthalpy_input'],
            'outlet_enthalpy_flow': heat_flows['exhaust_enthalpy_output'] + heat_flows['extraction_enthalpy_output'],
            'work_extracted': heat_flows['mechanical_work_output'],
            'enthalpy_converted_to_work': heat_flows['steam_enthalpy_input'] - heat_flows['exhaust_enthalpy_output'] - heat_flows['extraction_enthalpy_output']
        }
    
    def setup_maintenance_integration(self, maintenance_system, component_id: str):
        """
        Set up maintenance integration for enhanced turbine system
        
        Args:
            maintenance_system: AutoMaintenanceSystem instance
            component_id: Unique identifier for this turbine system
        """
        print(f"ENHANCED TURBINE {component_id}: Setting up maintenance integration")
        
        # Define monitoring configuration for turbine system parameters
        monitoring_config = {
            'turbine_efficiency': {
                'attribute': 'overall_efficiency',
                'threshold': 0.30,  # 30% efficiency threshold (below 90% of design)
                'comparison': 'less_than',
                'action': 'turbine_performance_test',
                'cooldown_hours': 168.0  # Weekly cooldown
            },
            'performance_factor': {
                'attribute': 'performance_factor',
                'threshold': 0.85,  # 85% performance factor threshold
                'comparison': 'less_than',
                'action': 'turbine_system_optimization',
                'cooldown_hours': 72.0  # 3-day cooldown
            },
            'availability_factor': {
                'attribute': 'availability_factor',
                'threshold': 0.95,  # 95% availability threshold
                'comparison': 'less_than',
                'action': 'turbine_protection_test',
                'cooldown_hours': 48.0  # 2-day cooldown
            },
            'thermal_stress': {
                'attribute': 'max_thermal_stress',
                'threshold': 700e6,  # Pa thermal stress threshold (87.5% of limit)
                'comparison': 'greater_than',
                'action': 'thermal_stress_analysis',
                'cooldown_hours': 24.0  # Daily cooldown
            },
            'vibration_level': {
                'attribute': 'vibration_displacement',
                'threshold': 20.0,  # mils vibration threshold (80% of trip)
                'comparison': 'greater_than',
                'action': 'vibration_analysis',
                'cooldown_hours': 12.0  # 12-hour cooldown
            }
        }
        
        # Register with maintenance system using event bus
        maintenance_system.register_component(component_id, self, monitoring_config)
        
        print(f"  Registered {component_id} with {len(monitoring_config)} monitoring parameters")
        
        # Set up maintenance integration for subsystems
        print(f"  Setting up subsystem maintenance integration...")
        
        # Register individual bearings
        for bearing_id, bearing in self.rotor_dynamics.bearings.items():
            bearing.setup_maintenance_integration(maintenance_system, bearing_id)
        
        # Register lubrication system
        if hasattr(self, 'bearing_lubrication_system'):
            self.bearing_lubrication_system.setup_maintenance_integration(
                maintenance_system, f"{component_id}-LUBRICATION"
            )
        
        # Connect protection system to maintenance event bus for trip events
        self.protection_system.set_maintenance_event_bus(
            maintenance_system.event_bus, 
            component_id
        )
        print(f"  Connected turbine protection system to maintenance event bus")
        
        # Store reference for coordination
        self.maintenance_system = maintenance_system
        self.component_id = component_id
        
        print(f"  Enhanced turbine maintenance integration complete")
    
    def perform_maintenance(self, maintenance_type: str = None, **kwargs):
        """
        Perform maintenance operations on enhanced turbine system
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        if maintenance_type == "turbine_performance_test":
            # Perform comprehensive turbine performance test
            current_efficiency = self.overall_efficiency
            current_power = self.total_power_output
            current_steam_rate = self.steam_rate
            
            # Simulate performance test and optimization
            # Test identifies performance degradation sources
            efficiency_improvement = 0.02  # 2% efficiency improvement
            self.overall_efficiency = min(0.34, self.overall_efficiency + efficiency_improvement)
            
            # Improve performance factor
            self.performance_factor = min(1.0, self.performance_factor + 0.05)
            
            # Calculate findings
            findings = f"Efficiency: {current_efficiency:.1%} → {self.overall_efficiency:.1%}, "
            findings += f"Steam rate: {current_steam_rate:.1f} kg/MWh, "
            findings += f"Power output: {current_power:.1f} MW"
            
            recommendations = []
            if current_efficiency < 0.32:
                recommendations.append("Consider turbine overhaul")
            if current_steam_rate > 3.5:
                recommendations.append("Optimize steam conditions")
            
            return {
                'success': True,
                'duration_hours': 8.0,
                'work_performed': 'Comprehensive turbine performance test and optimization',
                'findings': findings,
                'recommendations': recommendations,
                'performance_improvement': (efficiency_improvement / max(0.1, current_efficiency)) * 100.0,
                'effectiveness_score': 0.9,
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Test equipment', 'Calibration instruments']
            }
        
        elif maintenance_type == "turbine_system_optimization":
            # Perform system-wide optimization
            original_performance = self.performance_factor
            
            # Optimize all subsystems
            self.performance_factor = min(1.0, self.performance_factor + 0.08)
            
            # Optimize stage system efficiency
            if hasattr(self.stage_system, 'system_efficiency'):
                self.stage_system.system_efficiency = min(1.0, self.stage_system.system_efficiency + 0.03)
            
            # Optimize rotor dynamics
            for bearing in self.rotor_dynamics.bearings.values():
                bearing.efficiency_factor = min(1.0, bearing.efficiency_factor + 0.02)
            
            # Optimize lubrication system
            if hasattr(self, 'bearing_lubrication_system'):
                lubrication_system = self.bearing_lubrication_system
                lubrication_system.lubrication_effectiveness = min(1.0, 
                    lubrication_system.lubrication_effectiveness + 0.05)
            
            performance_improvement = ((self.performance_factor - original_performance) / 
                                     max(0.1, original_performance)) * 100.0
            
            return {
                'success': True,
                'duration_hours': 12.0,
                'work_performed': 'Complete turbine system optimization',
                'findings': f"Performance factor improved from {original_performance:.3f} to {self.performance_factor:.3f}",
                'performance_improvement': performance_improvement,
                'effectiveness_score': 0.95,
                'next_maintenance_due': 8760.0,  # Annual
                'parts_used': ['Optimization software', 'Adjustment tools']
            }
        
        elif maintenance_type == "turbine_protection_test":
            # Test turbine protection systems
            original_availability = self.availability_factor
            
            # Test and calibrate protection systems
            self.protection_system.system_available = True
            
            # Reset any nuisance trips
            if self.protection_system.trip_active:
                self.protection_system.reset_protection_system()
            
            # Improve availability factor
            self.availability_factor = min(1.0, self.availability_factor + 0.03)
            
            # Test findings
            trip_systems_tested = ['Overspeed', 'Vibration', 'Bearing Temperature', 'Thermal Stress']
            findings = f"Tested {len(trip_systems_tested)} protection systems. "
            findings += f"Availability improved from {original_availability:.1%} to {self.availability_factor:.1%}"
            
            return {
                'success': True,
                'duration_hours': 6.0,
                'work_performed': 'Turbine protection system test and calibration',
                'findings': findings,
                'performance_improvement': ((self.availability_factor - original_availability) / 
                                          max(0.1, original_availability)) * 100.0,
                'effectiveness_score': 0.9,
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Test equipment', 'Calibration tools']
            }
        
        elif maintenance_type == "thermal_stress_analysis":
            # Perform thermal stress analysis and mitigation
            if hasattr(self, 'thermal_tracker'):
                original_stress = self.thermal_tracker.max_thermal_stress
                
                # Thermal stress mitigation (simulated)
                stress_reduction = min(100e6, original_stress * 0.1)  # 10% reduction
                self.thermal_tracker.max_thermal_stress -= stress_reduction
                
                # Improve thermal shock risk
                self.thermal_tracker.thermal_shock_risk *= 0.8  # 20% reduction
                
                findings = f"Reduced thermal stress from {original_stress/1e6:.1f} MPa to {self.thermal_tracker.max_thermal_stress/1e6:.1f} MPa"
                
                return {
                    'success': True,
                    'duration_hours': 4.0,
                    'work_performed': 'Thermal stress analysis and mitigation',
                    'findings': findings,
                    'performance_improvement': (stress_reduction / max(1e6, original_stress)) * 100.0,
                    'effectiveness_score': 0.85,
                    'next_maintenance_due': 8760.0,  # Annual
                    'parts_used': ['Thermal analysis equipment', 'Stress relief tools']
                }
            else:
                return {
                    'success': False,
                    'duration_hours': 0.0,
                    'work_performed': 'Thermal stress analysis not available',
                    'error_message': 'Thermal tracker not available in this turbine configuration',
                    'effectiveness_score': 0.0
                }
        
        elif maintenance_type == "vibration_analysis":
            # Perform comprehensive vibration analysis
            current_vibration = self.last_update_results.get('vibration_displacement', 0.0)
            
            # Vibration analysis and correction
            vibration_reduction = min(5.0, current_vibration * 0.3)  # 30% reduction up to 5 mils
            
            # Apply vibration reduction to rotor dynamics
            for bearing in self.rotor_dynamics.bearings.values():
                bearing.vibration_displacement = max(0.0, bearing.vibration_displacement - vibration_reduction)
                bearing.vibration_velocity *= 0.8  # Reduce velocity
            
            # Improve rotor balance
            if hasattr(self.rotor_dynamics, 'thermal_bow'):
                self.rotor_dynamics.thermal_bow *= 0.7  # Reduce thermal bow
            
            findings = f"Reduced vibration from {current_vibration:.2f} mils to {current_vibration - vibration_reduction:.2f} mils"
            
            recommendations = []
            if current_vibration > 15.0:
                recommendations.append("Consider rotor balancing")
            if current_vibration > 20.0:
                recommendations.append("Schedule bearing inspection")
            
            return {
                'success': True,
                'duration_hours': 2.0,
                'work_performed': 'Comprehensive vibration analysis and correction',
                'findings': findings,
                'recommendations': recommendations,
                'performance_improvement': (vibration_reduction / max(1.0, current_vibration)) * 100.0,
                'effectiveness_score': 0.85,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['Vibration analysis equipment', 'Balancing weights']
            }
        
        elif maintenance_type == "routine_maintenance":
            # Perform routine turbine maintenance
            # Minor improvements across all systems
            self.performance_factor = min(1.0, self.performance_factor + 0.01)
            self.overall_efficiency = min(0.34, self.overall_efficiency + 0.002)
            
            # Routine maintenance on subsystems
            for bearing in self.rotor_dynamics.bearings.values():
                bearing.efficiency_factor = min(1.0, bearing.efficiency_factor + 0.005)
                bearing.metal_temperature = max(80.0, bearing.metal_temperature - 0.5)
            
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': 'Routine turbine maintenance completed',
                'findings': 'General maintenance activities completed across all turbine systems',
                'effectiveness_score': 0.7,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['General maintenance supplies', 'Lubricants', 'Filters']
            }
        
        else:
            # Unknown maintenance type
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f'Unknown maintenance type: {maintenance_type}',
                'error_message': f'Maintenance type {maintenance_type} not supported for enhanced turbine system',
                'effectiveness_score': 0.0
            }

    def reset(self) -> None:
        """Reset enhanced turbine to initial conditions"""
        self.stage_system.reset()
        self.rotor_dynamics.reset()
        self.protection_system.reset_protection_system()
        
        self.total_power_output = 0.0
        self.overall_efficiency = 0.0
        self.steam_rate = 0.0
        self.heat_rate = 0.0
        self.performance_factor = 1.0
        self.availability_factor = 1.0
        self.operating_hours = 0.0
        self.load_demand = 1.0
        self.control_mode = "automatic"
    
    def _steam_enthalpy(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate steam enthalpy (kJ/kg)"""
        sat_temp = self._saturation_temperature(pressure_mpa)
        if temp_c <= sat_temp:
            return self._saturation_enthalpy_vapor(pressure_mpa)
        else:
            h_g = self._saturation_enthalpy_vapor(pressure_mpa)
            superheat = temp_c - sat_temp
            return h_g + 2.1 * superheat
    
    def _saturation_temperature(self, pressure_mpa: float) -> float:
        """Calculate saturation temperature"""
        if pressure_mpa <= 0.001:
            return 10.0
        A, B, C = 8.07131, 1730.63, 233.426
        pressure_bar = pressure_mpa * 10.0
        pressure_bar = np.clip(pressure_bar, 0.01, 100.0)
        temp_c = B / (A - np.log10(pressure_bar)) - C
        return np.clip(temp_c, 10.0, 374.0)
    
    def _saturation_enthalpy_vapor(self, pressure_mpa: float) -> float:
        """Calculate saturation enthalpy of steam"""
        temp = self._saturation_temperature(pressure_mpa)
        h_f = 4.18 * temp
        h_fg = 2257.0 * (1.0 - temp / 374.0) ** 0.38
        return h_f + h_fg
    
    def _calculate_pressure_variation_effects(self, sg_pressures: List[float]) -> float:
        """
        Calculate impact of pressure variations between steam generators
        
        STEP 3: Pressure variation effects on turbine performance
        
        Args:
            sg_pressures: List of individual SG pressures (MPa)
            
        Returns:
            Pressure stability factor (0.0-1.0) where 1.0 = no variation impact
        """
        if len(sg_pressures) <= 1:
            return 1.0  # No variation with single SG
        
        # Calculate pressure statistics
        avg_pressure = sum(sg_pressures) / len(sg_pressures)
        max_deviation = max(abs(p - avg_pressure) for p in sg_pressures)
        
        # Normalize deviation (0.1 MPa = significant variation for turbine)
        # PWR steam generators typically operate within ±0.05 MPa of each other
        variation_factor = max_deviation / 0.1  # 0.1 MPa = 100% impact
        
        # Calculate stability factor
        # Small variations (< 0.02 MPa) have minimal impact
        # Large variations (> 0.1 MPa) significantly affect turbine performance
        if max_deviation < 0.02:
            stability_factor = 1.0  # No impact for small variations
        elif max_deviation < 0.05:
            # Linear reduction for moderate variations
            stability_factor = 1.0 - (max_deviation - 0.02) / 0.03 * 0.05  # Up to 5% impact
        else:
            # Significant impact for large variations
            stability_factor = 0.95 - min(variation_factor - 0.5, 0.25)  # 5-30% impact
        
        # Ensure reasonable bounds
        stability_factor = np.clip(stability_factor, 0.7, 1.0)
        
        return stability_factor
    


# Example usage and testing
if __name__ == "__main__":
    # Create enhanced turbine system with default configuration
    enhanced_turbine = EnhancedTurbinePhysics()
    
    print("Enhanced Turbine Physics Model - Parameter Validation")
    print("=" * 60)
    print(f"System ID: {enhanced_turbine.config.system_id}")
    print(f"Rated Power: {enhanced_turbine.config.rated_power_mwe} MW")
    print(f"Design Steam Flow: {enhanced_turbine.config.design_steam_flow} kg/s")
    print(f"Design Efficiency: {enhanced_turbine.config.design_efficiency:.1%}")
    print(f"Number of Stages: {len(enhanced_turbine.stage_system.stages)}")
    print(f"Number of Bearings: {len(enhanced_turbine.rotor_dynamics.bearings)}")
    print()
    
    # Test enhanced turbine operation
    for hour in range(24):  # 24 hours
        # Simulate load following operation
        if hour < 4:
            # Startup phase
            load_demand = 0.5 + 0.1 * hour  # 50% to 80% load
        elif hour < 8:
            # Ramp to full load
            load_demand = 0.8 + 0.05 * (hour - 4)  # 80% to 100% load
        elif hour < 16:
            # Full load operation
            load_demand = 1.0  # 100% load
        elif hour < 20:
            # Load reduction
            load_demand = 1.0 - 0.1 * (hour - 16)  # 100% to 60% load
        else:
            # Night operation
            load_demand = 0.6  # 60% load
        
        result = enhanced_turbine.update_state(
            steam_pressure=6.895,       # MPa inlet pressure
            steam_temperature=285.8,    # °C inlet temperature
            steam_flow=1665.0 * load_demand,  # kg/s inlet flow
            steam_quality=0.99,         # Steam quality
            load_demand=load_demand,    # Load demand
            condenser_pressure=0.007,   # MPa condenser pressure
            dt=1.0                      # 1 hour time step
        )
        
        if hour % 4 == 0:  # Print every 4 hours
            print(f"Hour {hour:2d}:")
            print(f"  Load Demand: {load_demand:.1%}")
            print(f"  Electrical Power: {result['electrical_power_net']:.1f} MW")
            print(f"  Overall Efficiency: {result['overall_efficiency']:.1%}")
            print(f"  Steam Rate: {result['steam_rate']:.1f} kg/MWh")
            print(f"  Rotor Speed: {result['rotor_speed']:.0f} RPM")
            print(f"  Vibration: {result['vibration_displacement']:.2f} mils")
            print(f"  Max Bearing Temp: {result['max_bearing_temperature']:.1f} °C")
            print(f"  Max Metal Temp: {result['max_metal_temperature']:.1f} °C")
            print(f"  Thermal Stress: {result['max_thermal_stress']/1e6:.1f} MPa")
            print(f"  Performance Factor: {result['performance_factor']:.3f}")
            
            # Show extraction flows
            total_extraction = result['total_extraction_flow']
            print(f"  Total Extraction: {total_extraction:.1f} kg/s")
            
            # Show any active trips
            if result['trip_active']:
                print(f"  TRIP ACTIVE: {', '.join(result['trip_reasons'])}")
            
            print()
    
    print(f"Final State Summary:")
    final_state = enhanced_turbine.get_state_dict()
    print(f"  Operating Hours: {final_state['enhanced_turbine_operating_hours']:.0f}")
    print(f"  Final Power: {final_state['enhanced_turbine_power']:.1f} MW")
    print(f"  Final Efficiency: {final_state['enhanced_turbine_efficiency']:.1%}")
    print(f"  Performance Factor: {final_state['enhanced_turbine_performance']:.3f}")
    print(f"  Availability Factor: {final_state['enhanced_turbine_availability']:.3f}")
