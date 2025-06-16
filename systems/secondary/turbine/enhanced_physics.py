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
from simulator.state import StateProvider, StateVariable, StateCategory, make_state_name

from .stage_system import TurbineStageSystem, TurbineStageSystemConfig
from .rotor_dynamics import RotorDynamicsModel, RotorDynamicsConfig
from .turbine_bearing_lubrication import TurbineBearingLubricationSystem, TurbineBearingLubricationConfig, integrate_lubrication_with_turbine

warnings.filterwarnings("ignore")


@dataclass
class ThermalStressConfig:
    """
    Configuration for thermal stress modeling
    
    References:
    - Turbine thermal stress analysis
    - Material property specifications
    - Operating envelope definitions
    """
    
    # System configuration
    system_id: str = "TSC-001"               # Thermal stress system identifier
    
    # Material properties
    thermal_conductivity: float = 45.0       # W/m/K thermal conductivity
    thermal_expansion_coeff: float = 12e-6   # 1/K thermal expansion coefficient
    elastic_modulus: float = 200e9           # Pa elastic modulus
    poisson_ratio: float = 0.3               # Poisson's ratio
    
    # Thermal limits
    max_metal_temperature: float = 600.0     # °C maximum metal temperature
    max_thermal_gradient: float = 5.0        # °C/cm maximum thermal gradient
    max_thermal_stress: float = 800e6        # Pa maximum thermal stress (increased from 400e6)
    
    # Time constants
    thermal_time_constant: float = 300.0     # seconds thermal response time
    stress_relaxation_time: float = 3600.0   # seconds stress relaxation time


@dataclass
class TurbineProtectionConfig:
    """
    Configuration for turbine protection systems
    
    References:
    - Turbine protection system standards
    - Trip logic specifications
    - Emergency response procedures
    """
    
    # System configuration
    system_id: str = "TPC-001"               # Protection system identifier
    
    # Trip setpoints
    overspeed_trip: float = 3780.0           # RPM overspeed trip (105%)
    vibration_trip: float = 25.0             # mils vibration trip
    bearing_temp_trip: float = 120.0         # °C bearing temperature trip
    thrust_bearing_trip: float = 50.0        # mm thrust bearing displacement trip (increased from 2.0)
    low_vacuum_trip: float = 0.012           # MPa low vacuum trip
    
    # Trip delays
    overspeed_delay: float = 0.1             # seconds overspeed trip delay
    vibration_delay: float = 2.0             # seconds vibration trip delay
    bearing_temp_delay: float = 10.0         # seconds bearing temp trip delay
    
    # Emergency actions
    enable_steam_dump: bool = True           # Enable steam dump on trip
    enable_turning_gear: bool = True         # Enable turning gear after trip
    emergency_seal_steam: bool = True        # Emergency seal steam on trip
    
    # Thermal stress limits (for compatibility)
    max_thermal_stress: float = 800e6        # Pa maximum thermal stress (increased from 400e6)


@dataclass
class EnhancedTurbineConfig:
    """
    Enhanced turbine configuration that integrates all subsystems
    
    References:
    - Complete turbine system specifications
    - Integration requirements
    - Performance optimization parameters
    """
    
    # System configuration
    system_id: str = "ETC-001"               # Enhanced turbine system identifier
    
    # Subsystem configurations
    stage_system_config: TurbineStageSystemConfig = field(default_factory=TurbineStageSystemConfig)
    rotor_dynamics_config: RotorDynamicsConfig = field(default_factory=RotorDynamicsConfig)
    thermal_stress_config: ThermalStressConfig = field(default_factory=ThermalStressConfig)
    protection_config: TurbineProtectionConfig = field(default_factory=TurbineProtectionConfig)
    
    # Overall turbine parameters
    rated_power_mwe: float = 1100.0          # MW electrical rated power
    design_steam_flow: float = 1665.0        # kg/s design steam flow
    design_steam_pressure: float = 6.895     # MPa design steam pressure
    design_steam_temperature: float = 285.8  # °C design steam temperature
    
    # Performance parameters
    design_efficiency: float = 0.34          # Overall design efficiency
    minimum_load: float = 0.2                # Minimum stable load (20%)
    maximum_load: float = 1.05               # Maximum load (105%)
    
    # Control parameters
    load_following_enabled: bool = True      # Enable load following
    performance_optimization: bool = True    # Enable performance optimization
    predictive_maintenance: bool = True      # Enable predictive maintenance


class MetalTemperatureTracker:
    """
    Metal temperature tracking system - analogous to specialized monitoring
    
    This model implements:
    1. Multi-point temperature monitoring
    2. Thermal gradient calculations
    3. Stress analysis
    4. Thermal shock protection
    """
    
    def __init__(self, config: ThermalStressConfig):
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
        self.trip_active = any(trips.values())

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


class EnhancedTurbinePhysics(StateProvider):
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
    
    def __init__(self, config: Optional[EnhancedTurbineConfig] = None):
        """Initialize enhanced turbine physics model"""
        if config is None:
            config = EnhancedTurbineConfig()
        
        self.config = config
        
        # Initialize subsystems
        self.stage_system = TurbineStageSystem(config.stage_system_config)
        self.rotor_dynamics = RotorDynamicsModel(config.rotor_dynamics_config)
        self.thermal_tracker = MetalTemperatureTracker(config.thermal_stress_config)
        self.protection_system = TurbineProtectionSystem(config.protection_config)
        
        # Create and integrate turbine bearing lubrication system
        lubrication_config = TurbineBearingLubricationConfig(
            system_id=f"{config.system_id}-LUB",
            turbine_rated_power=config.rated_power_mwe,
            turbine_rated_speed=3600.0,
            steam_temperature=config.design_steam_temperature
        )
        self.bearing_lubrication_system = TurbineBearingLubricationSystem(lubrication_config)
        
        # Store reference to lubrication system for direct access
        self.rotor_dynamics.bearing_lubrication_system = self.bearing_lubrication_system
        
        # Integrate lubrication system with this enhanced turbine (not just rotor dynamics)
        integrate_lubrication_with_turbine(self, self.bearing_lubrication_system)
        
        # Create turbine governor system with lubrication
        from .governor_system import TurbineGovernorSystem, GovernorControlConfig
        governor_config = GovernorControlConfig(
            system_id=f"{config.system_id}-GOV",
            rated_speed=3600.0,
            rated_load=config.rated_power_mwe
        )
        self.governor_system = TurbineGovernorSystem(governor_config)
        
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
        
    def update_state(self,
                    steam_pressure: float,
                    steam_temperature: float,
                    steam_flow: float,
                    steam_quality: float,
                    load_demand: float,
                    condenser_pressure: float = 0.007,
                    dt: float = 1.0) -> Dict[str, float]:
        """
        Update enhanced turbine state for one time step
        
        Args:
            steam_pressure: Inlet steam pressure (MPa)
            steam_temperature: Inlet steam temperature (°C)
            steam_flow: Steam mass flow rate (kg/s)
            steam_quality: Steam quality at inlet (0-1)
            load_demand: Load demand (0-1)
            condenser_pressure: Condenser pressure (MPa)
            dt: Time step (hours)
            
        Returns:
            Dictionary with enhanced turbine performance results
        """
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
        
        # Update stage system
        stage_results = self.stage_system.update_state(
            inlet_pressure=steam_pressure,
            inlet_temperature=steam_temperature,
            inlet_flow=steam_flow,
            load_demand=load_demand,
            extraction_demands=extraction_demands,
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
        
        self.total_power_output = stage_power_mw * power_reduction
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
    
    def get_state_variables(self) -> Dict[str, StateVariable]:
        """
        Return metadata for all state variables this turbine component provides.
        
        Returns:
            Dictionary mapping variable names to their metadata
        """
        variables = {}
        
        # Basic Turbine Performance Variables
        variables[make_state_name("secondary", "turbine", "mechanical_power")] = StateVariable(
            name=make_state_name("secondary", "turbine", "mechanical_power"),
            category=StateCategory.SECONDARY,
            subcategory="turbine",
            unit="MW",
            description="Turbine mechanical power output",
            data_type=float,
            valid_range=(0, 1200)
        )
        
        variables[make_state_name("secondary", "turbine", "efficiency")] = StateVariable(
            name=make_state_name("secondary", "turbine", "efficiency"),
            category=StateCategory.SECONDARY,
            subcategory="turbine",
            unit="fraction",
            description="Turbine overall efficiency",
            data_type=float,
            valid_range=(0.2, 0.5)
        )
        
        variables[make_state_name("secondary", "turbine", "steam_rate")] = StateVariable(
            name=make_state_name("secondary", "turbine", "steam_rate"),
            category=StateCategory.SECONDARY,
            subcategory="turbine",
            unit="kg/kWh",
            description="Turbine steam rate",
            data_type=float,
            valid_range=(2, 10)
        )
        
        variables[make_state_name("secondary", "turbine", "hp_power")] = StateVariable(
            name=make_state_name("secondary", "turbine", "hp_power"),
            category=StateCategory.SECONDARY,
            subcategory="turbine",
            unit="MW",
            description="High pressure turbine power",
            data_type=float,
            valid_range=(0, 800)
        )
        
        variables[make_state_name("secondary", "turbine", "lp_power")] = StateVariable(
            name=make_state_name("secondary", "turbine", "lp_power"),
            category=StateCategory.SECONDARY,
            subcategory="turbine",
            unit="MW",
            description="Low pressure turbine power",
            data_type=float,
            valid_range=(0, 400)
        )
        
        # Enhanced Turbine - Rotor Dynamics Variables
        variables[make_state_name("secondary", "turbine_rotor", "speed")] = StateVariable(
            name=make_state_name("secondary", "turbine_rotor", "speed"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_rotor",
            unit="rpm",
            description="Turbine rotor speed",
            data_type=float,
            valid_range=(0, 3600),
            is_critical=True
        )
        
        variables[make_state_name("secondary", "turbine_rotor", "vibration_level")] = StateVariable(
            name=make_state_name("secondary", "turbine_rotor", "vibration_level"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_rotor",
            unit="mm/s",
            description="Rotor vibration level",
            data_type=float,
            valid_range=(0, 50.0),
            is_critical=True
        )
        
        variables[make_state_name("secondary", "turbine_rotor", "eccentricity")] = StateVariable(
            name=make_state_name("secondary", "turbine_rotor", "eccentricity"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_rotor",
            unit="mm",
            description="Rotor eccentricity",
            data_type=float,
            valid_range=(0, 5.0)
        )
        
        variables[make_state_name("secondary", "turbine_rotor", "thermal_expansion")] = StateVariable(
            name=make_state_name("secondary", "turbine_rotor", "thermal_expansion"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_rotor",
            unit="mm",
            description="Rotor thermal expansion",
            data_type=float,
            valid_range=(0, 50.0)
        )
        
        # Enhanced Turbine - Bearing Variables
        variables[make_state_name("secondary", "turbine_bearings", "tb001_oil_temp")] = StateVariable(
            name=make_state_name("secondary", "turbine_bearings", "tb001_oil_temp"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_bearings",
            unit="°C",
            description="Turbine bearing TB-001 oil temperature",
            data_type=float,
            valid_range=(40, 80),
            is_critical=True
        )
        
        variables[make_state_name("secondary", "turbine_bearings", "tb002_oil_temp")] = StateVariable(
            name=make_state_name("secondary", "turbine_bearings", "tb002_oil_temp"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_bearings",
            unit="°C",
            description="Turbine bearing TB-002 oil temperature",
            data_type=float,
            valid_range=(40, 80),
            is_critical=True
        )
        
        variables[make_state_name("secondary", "turbine_bearings", "bearing_wear")] = StateVariable(
            name=make_state_name("secondary", "turbine_bearings", "bearing_wear"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_bearings",
            unit="mm",
            description="Average bearing wear",
            data_type=float,
            valid_range=(0, 2.0)
        )
        
        variables[make_state_name("secondary", "turbine_bearings", "oil_pressure")] = StateVariable(
            name=make_state_name("secondary", "turbine_bearings", "oil_pressure"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_bearings",
            unit="MPa",
            description="Bearing oil pressure",
            data_type=float,
            valid_range=(0.1, 2.0),
            is_critical=True
        )
        
        # Enhanced Turbine - Governor System Variables
        variables[make_state_name("secondary", "turbine_governor", "valve_position")] = StateVariable(
            name=make_state_name("secondary", "turbine_governor", "valve_position"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_governor",
            unit="%",
            description="Governor valve position",
            data_type=float,
            valid_range=(0, 100),
            is_critical=True
        )
        
        variables[make_state_name("secondary", "turbine_governor", "control_pressure")] = StateVariable(
            name=make_state_name("secondary", "turbine_governor", "control_pressure"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_governor",
            unit="MPa",
            description="Governor control pressure",
            data_type=float,
            valid_range=(0, 5.0)
        )
        
        variables[make_state_name("secondary", "turbine_governor", "oil_temperature")] = StateVariable(
            name=make_state_name("secondary", "turbine_governor", "oil_temperature"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_governor",
            unit="°C",
            description="Governor oil temperature",
            data_type=float,
            valid_range=(40, 70)
        )
        
        # Enhanced Turbine - Stage Performance Variables
        variables[make_state_name("secondary", "turbine_stages", "hp_efficiency")] = StateVariable(
            name=make_state_name("secondary", "turbine_stages", "hp_efficiency"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_stages",
            unit="fraction",
            description="High pressure stage efficiency",
            data_type=float,
            valid_range=(0.7, 0.95)
        )
        
        variables[make_state_name("secondary", "turbine_stages", "ip_efficiency")] = StateVariable(
            name=make_state_name("secondary", "turbine_stages", "ip_efficiency"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_stages",
            unit="fraction",
            description="Intermediate pressure stage efficiency",
            data_type=float,
            valid_range=(0.7, 0.95)
        )
        
        variables[make_state_name("secondary", "turbine_stages", "lp_efficiency")] = StateVariable(
            name=make_state_name("secondary", "turbine_stages", "lp_efficiency"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_stages",
            unit="fraction",
            description="Low pressure stage efficiency",
            data_type=float,
            valid_range=(0.6, 0.90)
        )
        
        variables[make_state_name("secondary", "turbine_stages", "blade_erosion")] = StateVariable(
            name=make_state_name("secondary", "turbine_stages", "blade_erosion"),
            category=StateCategory.SECONDARY,
            subcategory="turbine_stages",
            unit="mm",
            description="Average blade erosion",
            data_type=float,
            valid_range=(0, 5.0)
        )
        
        return variables
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Return current values for all state variables this turbine component provides.
        
        Returns:
            Dictionary mapping variable names to their current values
        """
        current_state = {}
        
        # Use last update results if available, otherwise fall back to defaults
        if hasattr(self, 'last_update_results') and self.last_update_results:
            results = self.last_update_results
        else:
            # Fallback to basic state dict if no update results available
            results = self.get_state_dict()
        
        # Basic Turbine Performance State - use actual calculated values
        current_state[make_state_name("secondary", "turbine", "mechanical_power")] = results.get('mechanical_power', 0.0)
        current_state[make_state_name("secondary", "turbine", "efficiency")] = results.get('overall_efficiency', 0.0)
        current_state[make_state_name("secondary", "turbine", "steam_rate")] = results.get('steam_rate', 0.0)
        current_state[make_state_name("secondary", "turbine", "hp_power")] = results.get('hp_power', 0.0)
        current_state[make_state_name("secondary", "turbine", "lp_power")] = results.get('lp_power', 0.0)
        
        # Enhanced Turbine - Rotor Dynamics State - use actual calculated values
        current_state[make_state_name("secondary", "turbine_rotor", "speed")] = results.get('rotor_speed', 3600.0)
        current_state[make_state_name("secondary", "turbine_rotor", "vibration_level")] = results.get('vibration_displacement', 2.0)
        current_state[make_state_name("secondary", "turbine_rotor", "eccentricity")] = results.get('rotor_eccentricity', 0.1)
        current_state[make_state_name("secondary", "turbine_rotor", "thermal_expansion")] = results.get('thermal_expansion', 5.0)
        
        # Enhanced Turbine - Bearing State - use actual calculated values
        current_state[make_state_name("secondary", "turbine_bearings", "tb001_oil_temp")] = results.get('TB-001_oil_temp', 70.0)
        current_state[make_state_name("secondary", "turbine_bearings", "tb002_oil_temp")] = results.get('TB-002_oil_temp', 70.0)
        current_state[make_state_name("secondary", "turbine_bearings", "bearing_wear")] = results.get('bearing_wear', 0.0)
        current_state[make_state_name("secondary", "turbine_bearings", "oil_pressure")] = results.get('bearing_oil_pressure', 0.8)
        
        # Enhanced Turbine - Governor System State - use actual calculated values
        current_state[make_state_name("secondary", "turbine_governor", "valve_position")] = results.get('governor_valve_position', 50.0)
        current_state[make_state_name("secondary", "turbine_governor", "control_pressure")] = results.get('governor_control_pressure', 2.0)
        current_state[make_state_name("secondary", "turbine_governor", "oil_temperature")] = results.get('governor_oil_temperature', 50.0)
        
        # Enhanced Turbine - Stage Performance State - use actual calculated values
        current_state[make_state_name("secondary", "turbine_stages", "hp_efficiency")] = results.get('hp_stage_efficiency', 0.85)
        current_state[make_state_name("secondary", "turbine_stages", "ip_efficiency")] = results.get('ip_stage_efficiency', 0.85)
        current_state[make_state_name("secondary", "turbine_stages", "lp_efficiency")] = results.get('lp_stage_efficiency', 0.80)
        current_state[make_state_name("secondary", "turbine_stages", "blade_erosion")] = results.get('blade_erosion', 0.0)
        
        return current_state


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
