"""
Turbine Governor System with Comprehensive Lubrication Tracking

This module implements a complete turbine governor system including:
1. Governor control logic (speed and load control)
2. Governor valve dynamics and positioning
3. Comprehensive lubrication system modeling
4. Protection systems and trip logic
5. Performance monitoring and diagnostics

Parameter Sources:
- IEEE Std 421.2: Guide for Identification, Testing, and Evaluation of the Dynamic Performance of Excitation Control Systems
- ASME PTC 6: Steam Turbines Performance Test Codes
- Woodward Governor Company Technical Manuals
- GE Steam Turbine Control Systems Documentation
- Turbine governor lubrication system specifications

Physical Basis:
- PID control theory for speed and load regulation
- Hydraulic valve dynamics and flow control
- Tribological lubrication and wear mechanisms
- Mechanical governor component modeling
- Protection system logic and coordination
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..lubrication_base import BaseLubricationSystem, BaseLubricationConfig, LubricationComponent

warnings.filterwarnings("ignore")


@dataclass
class GovernorValveConfig:
    """
    Configuration for governor valve system
    
    References:
    - Woodward Governor Valve Specifications
    - Steam turbine control valve design standards
    - Hydraulic actuator performance specifications
    """
    
    # Valve identification
    valve_id: str = "GV-001"                    # Governor valve identifier
    valve_type: str = "hydraulic"               # "hydraulic", "pneumatic", "electric"
    
    # Physical parameters
    valve_stroke: float = 100.0                 # mm full valve stroke
    valve_area: float = 0.1                     # m² valve flow area at full open
    valve_cv: float = 500.0                     # Flow coefficient
    
    # Dynamic parameters
    valve_response_time: float = 0.2            # seconds for 63% response
    valve_stroke_time: float = 5.0              # seconds for full stroke
    valve_deadband: float = 0.1                 # % deadband
    valve_hysteresis: float = 0.05              # % hysteresis
    
    # Operating limits
    min_position: float = 0.0                   # % minimum valve position
    max_position: float = 100.0                 # % maximum valve position
    max_stroke_rate: float = 20.0               # %/s maximum stroke rate
    
    # Actuator parameters
    actuator_pressure: float = 3.5              # MPa hydraulic pressure
    actuator_force: float = 50000.0             # N maximum actuator force
    actuator_oil_flow: float = 10.0             # L/min oil flow requirement


@dataclass
class GovernorControlConfig:
    """
    Configuration for governor control system
    
    References:
    - IEEE Std 421.2: Dynamic Performance of Excitation Control Systems
    - ASME PTC 6: Steam Turbines Performance Test Codes
    - Modern turbine control system specifications
    """
    
    # Control system identification
    system_id: str = "GCS-001"                  # Governor control system identifier
    
    # Control modes
    primary_control_mode: str = "speed"         # "speed", "load", "pressure"
    secondary_control_mode: str = "load"        # Secondary control mode
    
    # Speed control parameters
    rated_speed: float = 3600.0                 # RPM rated turbine speed
    speed_droop: float = 0.04                   # 4% speed droop (typical)
    speed_deadband: float = 0.1                 # % speed deadband
    max_speed_error: float = 5.0                # % maximum speed error
    
    # PID controller parameters for speed control
    speed_kp: float = 1.0                       # Proportional gain
    speed_ki: float = 0.5                       # Integral gain
    speed_kd: float = 0.1                       # Derivative gain
    speed_integral_limit: float = 10.0          # % integral windup limit
    
    # Load control parameters
    rated_load: float = 1100.0                  # MW rated electrical load
    load_ramp_rate: float = 5.0                 # %/min load ramp rate
    max_load_error: float = 2.0                 # % maximum load error
    
    # PID controller parameters for load control
    load_kp: float = 0.8                        # Proportional gain
    load_ki: float = 0.3                        # Integral gain
    load_kd: float = 0.05                       # Derivative gain
    load_integral_limit: float = 5.0            # % integral windup limit
    
    # Protection parameters
    overspeed_trip: float = 3780.0              # RPM overspeed trip (105%)
    underspeed_alarm: float = 3420.0            # RPM underspeed alarm (95%)
    load_rejection_rate: float = 100.0          # %/s emergency load rejection rate
    
    # Response characteristics
    governor_response_time: float = 0.1         # seconds governor response time
    control_update_rate: float = 100.0          # Hz control system update rate


@dataclass
class GovernorLubricationConfig(BaseLubricationConfig):
    """
    Configuration for governor lubrication system
    
    References:
    - Turbine governor lubrication specifications
    - Hydraulic system design standards
    - Oil analysis requirements for control systems
    """
    
    # Override base class defaults for governor-specific values
    system_id: str = "GOV-LUB-001"
    system_type: str = "governor"
    oil_reservoir_capacity: float = 200.0       # liters (smaller than main turbine)
    oil_operating_pressure: float = 3.5         # MPa (higher pressure for hydraulics)
    oil_temperature_range: Tuple[float, float] = (35.0, 75.0)  # °C tighter range
    oil_viscosity_grade: str = "ISO VG 46"      # Higher viscosity for hydraulics
    
    # Governor-specific parameters
    hydraulic_system_pressure: float = 3.5      # MPa hydraulic operating pressure
    servo_valve_flow_rate: float = 20.0         # L/min servo valve flow
    pilot_valve_flow_rate: float = 5.0          # L/min pilot valve flow
    accumulator_capacity: float = 50.0          # liters hydraulic accumulator
    
    # Filtration requirements (tighter for control systems)
    filter_micron_rating: float = 5.0           # microns (finer filtration)
    contamination_limit: float = 10.0           # ppm (stricter limit)
    
    # Maintenance intervals (more frequent for critical control)
    oil_change_interval: float = 4380.0         # hours (6 months)
    oil_analysis_interval: float = 360.0        # hours (bi-weekly)


class GovernorLubricationSystem(BaseLubricationSystem):
    """
    Governor-specific lubrication system implementation
    
    This system manages lubrication for all governor components including:
    1. Governor valve actuators and servo systems
    2. Speed sensing mechanisms and linkages
    3. Control system hydraulics and pilot valves
    4. Mechanical linkages and pivot points
    
    Physical Models:
    - Hydraulic fluid dynamics in control systems
    - Servo valve wear and contamination sensitivity
    - High-pressure seal performance and leakage
    - Precision component lubrication requirements
    """
    
    def __init__(self, config: GovernorLubricationConfig):
        """Initialize governor lubrication system"""
        
        # Define governor-specific lubricated components
        governor_components = [
            LubricationComponent(
                component_id="valve_actuator",
                component_type="actuator",
                oil_flow_requirement=10.0,         # L/min
                oil_pressure_requirement=3.5,      # MPa
                oil_temperature_max=75.0,          # °C
                base_wear_rate=0.0008,             # %/hour (high activity)
                load_wear_exponent=1.8,            # High load sensitivity
                speed_wear_exponent=1.0,           # Moderate speed sensitivity
                contamination_wear_factor=3.0,     # Very sensitive to contamination
                wear_performance_factor=0.02,      # 2% performance loss per % wear
                lubrication_performance_factor=0.6, # 60% performance loss with poor lube
                wear_alarm_threshold=8.0,          # % wear alarm
                wear_trip_threshold=20.0           # % wear trip
            ),
            LubricationComponent(
                component_id="speed_sensor",
                component_type="bearing",
                oil_flow_requirement=2.0,          # L/min
                oil_pressure_requirement=0.5,      # MPa
                oil_temperature_max=70.0,          # °C
                base_wear_rate=0.0003,             # %/hour (continuous operation)
                load_wear_exponent=1.2,            # Moderate load sensitivity
                speed_wear_exponent=1.5,           # High speed sensitivity
                contamination_wear_factor=2.5,     # High contamination sensitivity
                wear_performance_factor=0.015,     # 1.5% performance loss per % wear
                lubrication_performance_factor=0.4, # 40% performance loss
                wear_alarm_threshold=12.0,         # % wear alarm
                wear_trip_threshold=25.0           # % wear trip
            ),
            LubricationComponent(
                component_id="control_linkages",
                component_type="linkage",
                oil_flow_requirement=1.0,          # L/min
                oil_pressure_requirement=0.3,      # MPa
                oil_temperature_max=80.0,          # °C
                base_wear_rate=0.0005,             # %/hour (moderate activity)
                load_wear_exponent=1.5,            # Moderate load sensitivity
                speed_wear_exponent=0.8,           # Low speed sensitivity
                contamination_wear_factor=2.0,     # Moderate contamination sensitivity
                wear_performance_factor=0.01,      # 1% performance loss per % wear
                lubrication_performance_factor=0.3, # 30% performance loss
                wear_alarm_threshold=15.0,         # % wear alarm
                wear_trip_threshold=30.0           # % wear trip
            ),
            LubricationComponent(
                component_id="servo_valves",
                component_type="valve",
                oil_flow_requirement=15.0,         # L/min
                oil_pressure_requirement=3.5,      # MPa
                oil_temperature_max=70.0,          # °C
                base_wear_rate=0.001,              # %/hour (highest wear - precision component)
                load_wear_exponent=2.0,            # Very high load sensitivity
                speed_wear_exponent=1.3,           # High speed sensitivity
                contamination_wear_factor=4.0,     # Extremely sensitive to contamination
                wear_performance_factor=0.03,      # 3% performance loss per % wear
                lubrication_performance_factor=0.8, # 80% performance loss with poor lube
                wear_alarm_threshold=5.0,          # % wear alarm (very low threshold)
                wear_trip_threshold=15.0           # % wear trip
            ),
            LubricationComponent(
                component_id="pilot_valves",
                component_type="valve",
                oil_flow_requirement=5.0,          # L/min
                oil_pressure_requirement=3.5,      # MPa
                oil_temperature_max=70.0,          # °C
                base_wear_rate=0.0006,             # %/hour
                load_wear_exponent=1.6,            # High load sensitivity
                speed_wear_exponent=1.1,           # Moderate speed sensitivity
                contamination_wear_factor=3.5,     # Very high contamination sensitivity
                wear_performance_factor=0.025,     # 2.5% performance loss per % wear
                lubrication_performance_factor=0.7, # 70% performance loss
                wear_alarm_threshold=6.0,          # % wear alarm
                wear_trip_threshold=18.0           # % wear trip
            )
        ]
        
        # Initialize base lubrication system
        super().__init__(config, governor_components)
        
        # Governor-specific lubrication state
        self.hydraulic_pressure = config.hydraulic_system_pressure  # MPa
        self.servo_valve_contamination = 2.0                        # ppm local contamination
        self.pilot_valve_contamination = 1.5                        # ppm local contamination
        self.accumulator_pressure = config.hydraulic_system_pressure * 0.9  # MPa
        
        # Performance tracking
        self.valve_response_degradation = 0.0                       # Response time increase
        self.control_accuracy_degradation = 0.0                     # Control accuracy loss
        self.hydraulic_leakage_rate = 0.0                          # L/min internal leakage
        
    def get_lubricated_components(self) -> List[str]:
        """Return list of governor components requiring lubrication"""
        return list(self.components.keys())
    
    def calculate_component_wear(self, component_id: str, operating_conditions: Dict) -> float:
        """
        Calculate wear rate for governor components
        
        Args:
            component_id: Component identifier
            operating_conditions: Operating conditions for the component
            
        Returns:
            Wear rate (%/hour)
        """
        component = self.components[component_id]
        
        # Get operating conditions
        activity_level = operating_conditions.get('activity_level', 1.0)  # 0-2 scale
        load_factor = operating_conditions.get('load_factor', 1.0)        # 0-2 scale
        temperature = operating_conditions.get('temperature', 55.0)       # °C
        pressure = operating_conditions.get('pressure', 3.5)              # MPa
        
        # Component-specific wear calculations
        if component_id == "valve_actuator":
            # Valve actuator wear depends heavily on activity and pressure
            pressure_factor = (pressure / 3.5) ** component.load_wear_exponent
            activity_factor = activity_level ** 1.5  # High activity impact
            temp_factor = max(1.0, (temperature - 50.0) / 25.0)
            
            wear_rate = (component.base_wear_rate * pressure_factor * 
                        activity_factor * temp_factor)
            
        elif component_id == "speed_sensor":
            # Speed sensor wear depends on rotational speed and vibration
            speed_factor = operating_conditions.get('speed_factor', 1.0)
            vibration_factor = operating_conditions.get('vibration_factor', 1.0)
            
            wear_rate = (component.base_wear_rate * 
                        (speed_factor ** component.speed_wear_exponent) *
                        vibration_factor)
            
        elif component_id == "control_linkages":
            # Linkage wear depends on movement frequency and load
            movement_frequency = operating_conditions.get('movement_frequency', 1.0)
            load_cycles = operating_conditions.get('load_cycles', 1.0)
            
            wear_rate = (component.base_wear_rate * movement_frequency * 
                        (load_cycles ** component.load_wear_exponent))
            
        elif component_id == "servo_valves":
            # Servo valve wear is highly sensitive to contamination and pressure cycling
            pressure_cycling = operating_conditions.get('pressure_cycling', 1.0)
            flow_rate = operating_conditions.get('flow_rate', 1.0)
            
            # Contamination has exponential effect on servo valves
            contamination_factor = 1.0 + (self.servo_valve_contamination / 5.0) ** 2
            
            wear_rate = (component.base_wear_rate * pressure_cycling * 
                        flow_rate * contamination_factor)
            
        elif component_id == "pilot_valves":
            # Pilot valve wear similar to servo valves but less sensitive
            switching_frequency = operating_conditions.get('switching_frequency', 1.0)
            
            # Limit contamination factor to prevent extreme values
            contamination_factor = 1.0 + min(5.0, (self.pilot_valve_contamination / 8.0) ** 1.5)
            
            wear_rate = (component.base_wear_rate * switching_frequency * 
                        contamination_factor)
            
        else:
            # Default wear calculation
            wear_rate = component.base_wear_rate * activity_level
        
        return wear_rate
    
    def get_component_lubrication_requirements(self, component_id: str) -> Dict[str, float]:
        """Get lubrication requirements for specific governor component"""
        component = self.components[component_id]
        
        return {
            'oil_flow_rate': component.oil_flow_requirement,
            'oil_pressure': component.oil_pressure_requirement,
            'oil_temperature_max': component.oil_temperature_max,
            'contamination_sensitivity': component.contamination_wear_factor,
            'filtration_requirement': 5.0 if 'valve' in component_id else 10.0  # microns
        }
    
    def update_hydraulic_system(self, 
                               system_demand: float,
                               operating_temperature: float,
                               dt: float) -> Dict[str, float]:
        """
        Update hydraulic system performance based on lubrication quality
        
        Args:
            system_demand: Hydraulic system demand (0-1 scale)
            operating_temperature: System operating temperature (°C)
            dt: Time step (hours)
            
        Returns:
            Dictionary with hydraulic system results
        """
        # Hydraulic pressure affected by oil quality
        pressure_loss_factor = 1.0 - self.lubrication_effectiveness * 0.1
        self.hydraulic_pressure = (self.config.hydraulic_system_pressure * 
                                 (1.0 - pressure_loss_factor))
        
        # Internal leakage increases with wear and poor oil quality
        base_leakage = 0.5  # L/min base leakage
        wear_leakage = sum(self.component_wear.values()) * 0.1  # Leakage from wear
        contamination_leakage = (self.oil_contamination_level / 10.0) * 0.5
        
        self.hydraulic_leakage_rate = base_leakage + wear_leakage + contamination_leakage
        
        # Update local contamination levels for critical components
        # Servo valves accumulate contamination faster due to tight clearances
        servo_contamination_rate = self.oil_contamination_level * 0.02 * dt  # Reduced rate
        self.servo_valve_contamination += servo_contamination_rate
        self.servo_valve_contamination = min(20.0, self.servo_valve_contamination)
        
        # Pilot valves less sensitive but still accumulate contamination
        pilot_contamination_rate = self.oil_contamination_level * 0.01 * dt  # Reduced rate
        self.pilot_valve_contamination += pilot_contamination_rate
        self.pilot_valve_contamination = min(15.0, self.pilot_valve_contamination)
        
        # Accumulator pressure affected by leakage
        pressure_loss_rate = self.hydraulic_leakage_rate / 1000.0  # Convert to pressure loss
        self.accumulator_pressure = max(2.0, self.accumulator_pressure - pressure_loss_rate * dt)
        
        return {
            'hydraulic_pressure': self.hydraulic_pressure,
            'hydraulic_leakage_rate': self.hydraulic_leakage_rate,
            'accumulator_pressure': self.accumulator_pressure,
            'servo_valve_contamination': self.servo_valve_contamination,
            'pilot_valve_contamination': self.pilot_valve_contamination,
            'pressure_loss_factor': pressure_loss_factor
        }
    
    def calculate_performance_degradation(self) -> Dict[str, float]:
        """Calculate governor performance degradation due to lubrication issues"""
        
        # Valve response time degradation
        valve_wear = self.component_wear.get('valve_actuator', 0.0)
        servo_wear = self.component_wear.get('servo_valves', 0.0)
        
        # Response time increases with wear and poor lubrication
        response_degradation = (valve_wear * 0.02 + servo_wear * 0.03 + 
                              (1.0 - self.lubrication_effectiveness) * 0.1)
        self.valve_response_degradation = response_degradation
        
        # Control accuracy degradation
        linkage_wear = self.component_wear.get('control_linkages', 0.0)
        sensor_wear = self.component_wear.get('speed_sensor', 0.0)
        
        accuracy_degradation = (linkage_wear * 0.01 + sensor_wear * 0.015 + 
                              (1.0 - self.lubrication_effectiveness) * 0.05)
        self.control_accuracy_degradation = accuracy_degradation
        
        return {
            'valve_response_degradation': self.valve_response_degradation,
            'control_accuracy_degradation': self.control_accuracy_degradation,
            'overall_performance_factor': self.system_health_factor
        }


class GovernorValveModel:
    """
    Governor valve dynamics and positioning model
    
    This model implements:
    1. Hydraulic actuator dynamics
    2. Valve position control and feedback
    3. Steam flow calculation through valve
    4. Valve wear and performance degradation
    5. Lubrication effects on valve operation
    """
    
    def __init__(self, config: GovernorValveConfig):
        """Initialize governor valve model"""
        self.config = config
        
        # Valve state
        self.valve_position = 50.0                      # % current valve position
        self.valve_position_demand = 50.0               # % demanded valve position
        self.valve_velocity = 0.0                       # %/s valve velocity
        
        # Actuator state
        self.actuator_pressure = config.actuator_pressure  # MPa
        self.actuator_force = 0.0                       # N current actuator force
        self.actuator_oil_flow = 0.0                    # L/min oil flow to actuator
        
        # Performance state
        self.valve_response_time = config.valve_response_time  # seconds
        self.valve_deadband = config.valve_deadband     # %
        self.valve_hysteresis = config.valve_hysteresis # %
        
        # Steam flow state
        self.steam_flow_rate = 0.0                      # kg/s steam flow through valve
        self.pressure_drop = 0.0                        # MPa pressure drop across valve
        
        # Degradation tracking
        self.valve_wear_factor = 1.0                    # Valve condition factor
        self.seat_leakage = 0.0                         # % seat leakage
        self.actuator_efficiency = 1.0                  # Actuator efficiency factor
        
    def calculate_valve_dynamics(self, 
                                position_demand: float,
                                lubrication_factor: float,
                                dt: float) -> Dict[str, float]:
        """
        Calculate valve position dynamics with lubrication effects
        
        Args:
            position_demand: Demanded valve position (%)
            lubrication_factor: Lubrication effectiveness (0-1)
            dt: Time step (seconds)
            
        Returns:
            Dictionary with valve dynamics results
        """
        # Apply lubrication effects to valve performance
        effective_response_time = self.valve_response_time / max(0.3, lubrication_factor)
        effective_deadband = self.valve_deadband * (2.0 - lubrication_factor)
        
        # Position error calculation
        position_error = position_demand - self.valve_position
        
        # Apply deadband
        if abs(position_error) < effective_deadband:
            position_error = 0.0
        
        # Apply hysteresis (simplified)
        if abs(position_error) < self.valve_hysteresis and self.valve_velocity < 0.1:
            position_error = 0.0
        
        # First-order valve dynamics
        time_constant = effective_response_time / 0.63  # Convert to time constant
        velocity_demand = position_error / time_constant
        
        # Apply velocity limits
        max_velocity = self.config.max_stroke_rate * lubrication_factor
        velocity_demand = np.clip(velocity_demand, -max_velocity, max_velocity)
        
        # Update valve velocity (with some inertia)
        velocity_time_constant = 0.1  # seconds
        velocity_change = (velocity_demand - self.valve_velocity) / velocity_time_constant * dt
        self.valve_velocity += velocity_change
        
        # Update valve position
        position_change = self.valve_velocity * dt
        self.valve_position += position_change
        
        # Apply position limits
        self.valve_position = np.clip(self.valve_position, 
                                    self.config.min_position, 
                                    self.config.max_position)
        
        # Calculate actuator requirements
        force_demand = abs(position_error) * 1000.0  # Simplified force calculation
        self.actuator_force = min(force_demand, self.config.actuator_force)
        
        # Oil flow to actuator (proportional to velocity)
        self.actuator_oil_flow = abs(self.valve_velocity) * 0.5  # L/min per %/s
        
        return {
            'valve_position': self.valve_position,
            'valve_velocity': self.valve_velocity,
            'position_error': position_error,
            'actuator_force': self.actuator_force,
            'actuator_oil_flow': self.actuator_oil_flow,
            'effective_response_time': effective_response_time,
            'effective_deadband': effective_deadband
        }
    
    def calculate_steam_flow(self, 
                           inlet_pressure: float,
                           outlet_pressure: float,
                           steam_temperature: float) -> Dict[str, float]:
        """
        Calculate steam flow through governor valve
        
        Args:
            inlet_pressure: Steam inlet pressure (MPa)
            outlet_pressure: Steam outlet pressure (MPa)
            steam_temperature: Steam temperature (°C)
            
        Returns:
            Dictionary with steam flow results
        """
        # Effective valve area based on position and wear
        effective_area = (self.config.valve_area * self.valve_position / 100.0 * 
                         self.valve_wear_factor)
        
        # Pressure drop across valve
        self.pressure_drop = inlet_pressure - outlet_pressure
        
        # Initialize default values
        flow_coefficient = 0.75
        pressure_ratio = 1.0
        critical_pressure_ratio = 0.55  # Typical for steam
        
        # Steam flow calculation (simplified)
        if self.pressure_drop > 0 and effective_area > 0:
            # Critical flow check
            pressure_ratio = outlet_pressure / inlet_pressure
            
            if pressure_ratio < critical_pressure_ratio:
                # Critical (choked) flow
                flow_coefficient = 0.85  # Typical discharge coefficient
                steam_density = inlet_pressure * 1000.0 / (0.4615 * (steam_temperature + 273.15))
                self.steam_flow_rate = (flow_coefficient * effective_area * 
                                      np.sqrt(2.0 * inlet_pressure * 1e6 * steam_density))
            else:
                # Subcritical flow
                flow_coefficient = 0.75
                steam_density = ((inlet_pressure + outlet_pressure) / 2.0 * 1000.0 / 
                               (0.4615 * (steam_temperature + 273.15)))
                self.steam_flow_rate = (flow_coefficient * effective_area * 
                                      np.sqrt(2.0 * self.pressure_drop * 1e6 * steam_density))
        else:
            self.steam_flow_rate = 0.0
        
        # Add seat leakage
        leakage_flow = self.seat_leakage / 100.0 * self.config.valve_cv * 0.1
        total_flow = self.steam_flow_rate + leakage_flow
        
        return {
            'steam_flow_rate': total_flow,
            'pressure_drop': self.pressure_drop,
            'effective_area': effective_area,
            'seat_leakage_flow': leakage_flow,
            'flow_coefficient': flow_coefficient
        }
    
    def update_valve_wear(self, 
                         steam_flow: float,
                         pressure_drop: float,
                         lubrication_factor: float,
                         dt: float) -> Dict[str, float]:
        """Update valve wear based on operating conditions"""
        
        # Erosion wear from steam flow
        flow_factor = (steam_flow / 1000.0) ** 1.5  # Erosion proportional to flow^1.5
        pressure_factor = (pressure_drop / 1.0) ** 1.2  # Pressure effect
        
        erosion_rate = 0.00001 * flow_factor * pressure_factor  # %/hour
        
        # Mechanical wear from valve movement
        movement_rate = abs(self.valve_velocity) / 10.0  # Normalized movement
        mechanical_wear_rate = 0.000005 * movement_rate  # %/hour
        
        # Lubrication effect on wear
        lubrication_wear_factor = 2.0 - lubrication_factor
        total_wear_rate = (erosion_rate + mechanical_wear_rate) * lubrication_wear_factor
        
        # Update wear factors
        wear_increase = total_wear_rate * dt
        self.valve_wear_factor = max(0.5, self.valve_wear_factor - wear_increase)
        
        # Seat leakage increases with wear
        self.seat_leakage += wear_increase * 10.0  # 10% leakage per % wear
        self.seat_leakage = min(5.0, self.seat_leakage)  # Maximum 5% leakage
        
        # Actuator efficiency decreases with poor lubrication
        efficiency_loss = (1.0 - lubrication_factor) * 0.1 * dt
        self.actuator_efficiency = max(0.7, self.actuator_efficiency - efficiency_loss)
        
        return {
            'valve_wear_factor': self.valve_wear_factor,
            'seat_leakage': self.seat_leakage,
            'actuator_efficiency': self.actuator_efficiency,
            'erosion_rate': erosion_rate,
            'mechanical_wear_rate': mechanical_wear_rate,
            'total_wear_rate': total_wear_rate
        }


class TurbineGovernorSystem:
    """
    Complete turbine governor system with comprehensive lubrication tracking
    
    This system integrates:
    1. Governor control logic (PID controllers for speed and load)
    2. Governor valve dynamics and steam flow control
    3. Comprehensive lubrication system with component wear tracking
    4. Protection systems and trip logic
    5. Performance monitoring and diagnostics
    6. Maintenance scheduling and condition monitoring
    
    Physical Models:
    - Classical PID control theory
    - Hydraulic valve dynamics
    - Steam flow through control valves
    - Tribological wear mechanisms
    - Oil degradation kinetics
    - System performance degradation
    """
    
    def __init__(self, 
                 control_config: Optional[GovernorControlConfig] = None,
                 valve_config: Optional[GovernorValveConfig] = None,
                 lubrication_config: Optional[GovernorLubricationConfig] = None):
        """Initialize complete turbine governor system"""
        
        # Initialize configurations
        self.control_config = control_config if control_config else GovernorControlConfig()
        self.valve_config = valve_config if valve_config else GovernorValveConfig()
        self.lubrication_config = lubrication_config if lubrication_config else GovernorLubricationConfig()
        
        # Initialize subsystems
        self.lubrication_system = GovernorLubricationSystem(self.lubrication_config)
        self.governor_valve = GovernorValveModel(self.valve_config)
        
        # Governor control state
        self.control_mode = self.control_config.primary_control_mode  # "speed", "load", "pressure"
        self.governor_enabled = True                    # Governor system enabled
        self.manual_mode = False                        # Manual control mode
        
        # Speed control state
        self.speed_setpoint = self.control_config.rated_speed  # RPM speed setpoint
        self.speed_actual = 0.0                         # RPM actual turbine speed
        self.speed_error = 0.0                          # RPM speed error
        self.speed_error_integral = 0.0                 # RPM⋅s integral error
        self.speed_error_derivative = 0.0               # RPM/s derivative error
        self.speed_error_previous = 0.0                 # RPM previous error for derivative
        
        # Load control state
        self.load_setpoint = self.control_config.rated_load  # MW load setpoint
        self.load_actual = 0.0                          # MW actual electrical load
        self.load_error = 0.0                           # MW load error
        self.load_error_integral = 0.0                  # MW⋅s integral error
        self.load_error_derivative = 0.0                # MW/s derivative error
        self.load_error_previous = 0.0                  # MW previous error for derivative
        
        # Control output
        self.control_output = 50.0                      # % control output to valve
        self.valve_position_demand = 50.0               # % valve position demand
        
        # Protection state
        self.overspeed_trip_active = False              # Overspeed trip status
        self.protection_trip_active = False             # Any protection trip active
        self.trip_reasons = []                          # List of active trip reasons
        
        # Performance tracking
        self.governor_response_time = self.control_config.governor_response_time  # seconds
        self.control_accuracy = 1.0                     # Control accuracy factor
        self.system_availability = 1.0                  # System availability factor
        
        # Operating statistics
        self.operating_hours = 0.0                      # Total operating hours
        self.control_actions = 0                        # Number of control actions
        self.trip_events = 0                            # Number of trip events
        self.maintenance_cycles = 0                     # Number of maintenance cycles
        
    def update_speed_control(self, 
                           actual_speed: float,
                           speed_setpoint: float,
                           dt: float) -> float:
        """
        Update speed control PID controller
        
        Args:
            actual_speed: Current turbine speed (RPM)
            speed_setpoint: Speed setpoint (RPM)
            dt: Time step (seconds)
            
        Returns:
            Control output (%)
        """
        # Update speed values
        self.speed_actual = actual_speed
        self.speed_setpoint = speed_setpoint
        
        # Calculate speed error
        self.speed_error = speed_setpoint - actual_speed
        
        # Apply speed droop (permanent droop characteristic)
        droop_correction = self.speed_error * self.control_config.speed_droop
        corrected_error = self.speed_error - droop_correction
        
        # Apply deadband
        if abs(corrected_error) < self.control_config.speed_deadband:
            corrected_error = 0.0
        
        # PID controller calculations
        # Proportional term
        proportional = self.control_config.speed_kp * corrected_error
        
        # Integral term with windup protection
        self.speed_error_integral += corrected_error * dt
        integral_limit = self.control_config.speed_integral_limit
        self.speed_error_integral = np.clip(self.speed_error_integral, 
                                          -integral_limit, integral_limit)
        integral = self.control_config.speed_ki * self.speed_error_integral
        
        # Derivative term
        if dt > 0:
            self.speed_error_derivative = (corrected_error - self.speed_error_previous) / dt
        else:
            self.speed_error_derivative = 0.0
        derivative = self.control_config.speed_kd * self.speed_error_derivative
        
        # Total PID output
        pid_output = proportional + integral + derivative
        
        # Apply lubrication effects on control accuracy
        lubrication_factor = self.lubrication_system.lubrication_effectiveness
        control_degradation = self.lubrication_system.control_accuracy_degradation
        
        effective_output = pid_output * lubrication_factor * (1.0 - control_degradation)
        
        # Update previous error for next derivative calculation
        self.speed_error_previous = corrected_error
        
        return effective_output
    
    def update_load_control(self, 
                          actual_load: float,
                          load_setpoint: float,
                          dt: float) -> float:
        """
        Update load control PID controller
        
        Args:
            actual_load: Current electrical load (MW)
            load_setpoint: Load setpoint (MW)
            dt: Time step (seconds)
            
        Returns:
            Control output (%)
        """
        # Update load values
        self.load_actual = actual_load
        self.load_setpoint = load_setpoint
        
        # Calculate load error
        self.load_error = load_setpoint - actual_load
        
        # Apply deadband
        deadband = self.control_config.max_load_error * self.control_config.rated_load / 100.0
        if abs(self.load_error) < deadband:
            self.load_error = 0.0
        
        # PID controller calculations
        # Proportional term
        proportional = self.control_config.load_kp * self.load_error
        
        # Integral term with windup protection
        self.load_error_integral += self.load_error * dt
        integral_limit = self.control_config.load_integral_limit * self.control_config.rated_load
        self.load_error_integral = np.clip(self.load_error_integral, 
                                         -integral_limit, integral_limit)
        integral = self.control_config.load_ki * self.load_error_integral
        
        # Derivative term
        if dt > 0:
            self.load_error_derivative = (self.load_error - self.load_error_previous) / dt
        else:
            self.load_error_derivative = 0.0
        derivative = self.control_config.load_kd * self.load_error_derivative
        
        # Total PID output
        pid_output = proportional + integral + derivative
        
        # Apply load ramp rate limiting
        max_ramp_rate = self.control_config.load_ramp_rate / 60.0 * dt  # %/s to %/timestep
        if abs(pid_output) > max_ramp_rate:
            pid_output = np.sign(pid_output) * max_ramp_rate
        
        # Apply lubrication effects
        lubrication_factor = self.lubrication_system.lubrication_effectiveness
        control_degradation = self.lubrication_system.control_accuracy_degradation
        
        effective_output = pid_output * lubrication_factor * (1.0 - control_degradation)
        
        # Update previous error
        self.load_error_previous = self.load_error
        
        return effective_output
    
    def check_protection_systems(self, 
                               turbine_speed: float,
                               system_conditions: Dict) -> Dict[str, bool]:
        """
        Check governor protection systems and trip conditions
        
        Args:
            turbine_speed: Current turbine speed (RPM)
            system_conditions: System operating conditions
            
        Returns:
            Dictionary with protection system status
        """
        trips = {}
        alarms = []
        
        # Overspeed protection
        if turbine_speed > self.control_config.overspeed_trip:
            trips['overspeed'] = True
            if 'Overspeed Trip' not in self.trip_reasons:
                self.trip_reasons.append('Overspeed Trip')
                self.trip_events += 1
        else:
            trips['overspeed'] = False
        
        # Underspeed alarm
        if turbine_speed < self.control_config.underspeed_alarm:
            alarms.append('Underspeed Alarm')
        
        # Lubrication system trips
        lubrication_alarms = self.lubrication_system.check_alarms_and_trips()
        if lubrication_alarms['trip_count'] > 0:
            trips['lubrication'] = True
            self.trip_reasons.extend(lubrication_alarms['trips'])
        else:
            trips['lubrication'] = False
        
        # Governor valve trips
        valve_wear = self.lubrication_system.component_wear.get('valve_actuator', 0.0)
        servo_wear = self.lubrication_system.component_wear.get('servo_valves', 0.0)
        
        if valve_wear > 20.0:  # 20% wear trip threshold
            trips['valve_wear'] = True
            if 'Governor Valve Wear' not in self.trip_reasons:
                self.trip_reasons.append('Governor Valve Wear')
        else:
            trips['valve_wear'] = False
        
        if servo_wear > 15.0:  # 15% servo valve wear trip threshold
            trips['servo_wear'] = True
            if 'Servo Valve Wear' not in self.trip_reasons:
                self.trip_reasons.append('Servo Valve Wear')
        else:
            trips['servo_wear'] = False
        
        # Hydraulic system trips
        hydraulic_pressure = self.lubrication_system.hydraulic_pressure
        if hydraulic_pressure < 2.0:  # Minimum hydraulic pressure
            trips['hydraulic_pressure'] = True
            if 'Low Hydraulic Pressure' not in self.trip_reasons:
                self.trip_reasons.append('Low Hydraulic Pressure')
        else:
            trips['hydraulic_pressure'] = False
        
        # Overall trip status
        self.protection_trip_active = any(trips.values())
        self.overspeed_trip_active = trips.get('overspeed', False)
        
        # Emergency actions on trip
        if self.protection_trip_active:
            self.valve_position_demand = 0.0  # Close valve on trip
            self.governor_enabled = False
        
        return {
            'trips': trips,
            'alarms': alarms,
            'trip_active': self.protection_trip_active,
            'trip_reasons': self.trip_reasons,
            'overspeed_trip': self.overspeed_trip_active
        }
    
    def update_state(self,
                    turbine_speed: float,
                    electrical_load: float,
                    steam_pressure: float,
                    steam_temperature: float,
                    speed_setpoint: Optional[float] = None,
                    load_setpoint: Optional[float] = None,
                    dt: float = 1.0) -> Dict[str, float]:
        """
        Update complete governor system state
        
        Args:
            turbine_speed: Current turbine speed (RPM)
            electrical_load: Current electrical load (MW)
            steam_pressure: Steam pressure at governor valve (MPa)
            steam_temperature: Steam temperature (°C)
            speed_setpoint: Speed setpoint (RPM), optional
            load_setpoint: Load setpoint (MW), optional
            dt: Time step (hours)
            
        Returns:
            Dictionary with complete governor system results
        """
        # Convert dt to seconds for control calculations
        dt_seconds = dt * 3600.0
        
        # Update setpoints if provided
        if speed_setpoint is not None:
            self.speed_setpoint = speed_setpoint
        if load_setpoint is not None:
            self.load_setpoint = load_setpoint
        
        # Check protection systems first
        protection_status = self.check_protection_systems(turbine_speed, {
            'steam_pressure': steam_pressure,
            'steam_temperature': steam_temperature
        })
        
        # Update control logic if governor is enabled and not tripped
        if self.governor_enabled and not self.protection_trip_active and not self.manual_mode:
            
            if self.control_mode == "speed":
                # Speed control mode
                control_output = self.update_speed_control(
                    turbine_speed, self.speed_setpoint, dt_seconds
                )
                
            elif self.control_mode == "load":
                # Load control mode
                control_output = self.update_load_control(
                    electrical_load, self.load_setpoint, dt_seconds
                )
                
            else:
                # Default to current output
                control_output = 0.0
            
            # Apply control output to valve position demand
            self.control_output = control_output
            self.valve_position_demand += control_output
            self.valve_position_demand = np.clip(self.valve_position_demand, 0.0, 100.0)
            
            # Track control actions
            if abs(control_output) > 0.1:
                self.control_actions += 1
        
        # Calculate governor component operating conditions
        valve_activity = abs(self.governor_valve.valve_velocity) / 10.0  # Normalized activity
        hydraulic_demand = self.valve_position_demand / 100.0
        
        component_conditions = {
            'valve_actuator': {
                'activity_level': valve_activity,
                'load_factor': hydraulic_demand,
                'temperature': 55.0 + hydraulic_demand * 15.0,  # Temperature rises with activity
                'pressure': self.lubrication_system.hydraulic_pressure
            },
            'speed_sensor': {
                'speed_factor': turbine_speed / 3600.0,
                'vibration_factor': 1.0 + (turbine_speed - 3600.0) / 3600.0 * 0.1
            },
            'control_linkages': {
                'movement_frequency': valve_activity,
                'load_cycles': hydraulic_demand
            },
            'servo_valves': {
                'pressure_cycling': valve_activity,
                'flow_rate': hydraulic_demand
            },
            'pilot_valves': {
                'switching_frequency': valve_activity * 0.5
            }
        }
        
        # Update lubrication system
        oil_temp = 45.0 + hydraulic_demand * 20.0  # Oil temperature varies with load
        contamination_input = valve_activity * 0.1  # Contamination from activity
        moisture_input = 0.001  # Base moisture input
        
        oil_quality_results = self.lubrication_system.update_oil_quality(
            oil_temp, contamination_input, moisture_input, dt
        )
        
        # Update component wear
        wear_results = self.lubrication_system.update_component_wear(
            component_conditions, dt
        )
        
        # Update hydraulic system
        hydraulic_results = self.lubrication_system.update_hydraulic_system(
            hydraulic_demand, oil_temp, dt
        )
        
        # Update governor valve dynamics
        lubrication_factor = self.lubrication_system.lubrication_effectiveness
        valve_results = self.governor_valve.calculate_valve_dynamics(
            self.valve_position_demand, lubrication_factor, dt_seconds
        )
        
        # Calculate steam flow through valve
        steam_flow_results = self.governor_valve.calculate_steam_flow(
            steam_pressure, steam_pressure * 0.9, steam_temperature
        )
        
        # Update valve wear
        valve_wear_results = self.governor_valve.update_valve_wear(
            steam_flow_results['steam_flow_rate'],
            steam_flow_results['pressure_drop'],
            lubrication_factor,
            dt
        )
        
        # Calculate performance degradation
        performance_results = self.lubrication_system.calculate_performance_degradation()
        
        # Update system performance metrics
        self.governor_response_time = (self.control_config.governor_response_time * 
                                     (1.0 + performance_results['valve_response_degradation']))
        self.control_accuracy = 1.0 - performance_results['control_accuracy_degradation']
        self.system_availability = 0.0 if self.protection_trip_active else 1.0
        
        # Check maintenance requirements
        maintenance_flags = self.lubrication_system.check_maintenance_requirements()
        
        # Update operating hours
        self.operating_hours += dt
        
        return {
            # Control system results
            'governor_enabled': self.governor_enabled,
            'control_mode': self.control_mode,
            'speed_setpoint': self.speed_setpoint,
            'speed_actual': turbine_speed,
            'speed_error': self.speed_error,
            'load_setpoint': self.load_setpoint,
            'load_actual': electrical_load,
            'load_error': self.load_error,
            'control_output': self.control_output,
            'valve_position_demand': self.valve_position_demand,
            'valve_position_actual': self.governor_valve.valve_position,
            
            # Governor valve results
            'valve_position': valve_results['valve_position'],
            'valve_velocity': valve_results['valve_velocity'],
            'valve_response_time': valve_results['effective_response_time'],
            'steam_flow_rate': steam_flow_results['steam_flow_rate'],
            'valve_pressure_drop': steam_flow_results['pressure_drop'],
            'valve_wear_factor': valve_wear_results['valve_wear_factor'],
            'seat_leakage': valve_wear_results['seat_leakage'],
            
            # Lubrication system results
            'oil_temperature': oil_quality_results['oil_temperature'],
            'oil_contamination': oil_quality_results['contamination_level'],
            'oil_quality_factor': oil_quality_results['oil_quality_factor'],
            'lubrication_effectiveness': self.lubrication_system.lubrication_effectiveness,
            'hydraulic_pressure': hydraulic_results['hydraulic_pressure'],
            'hydraulic_leakage': hydraulic_results['hydraulic_leakage_rate'],
            
            # Component wear results
            'valve_actuator_wear': wear_results.get('valve_actuator', {}).get('total_wear', 0.0),
            'servo_valve_wear': wear_results.get('servo_valves', {}).get('total_wear', 0.0),
            'speed_sensor_wear': wear_results.get('speed_sensor', {}).get('total_wear', 0.0),
            'control_linkage_wear': wear_results.get('control_linkages', {}).get('total_wear', 0.0),
            
            # Performance metrics
            'governor_response_time': self.governor_response_time,
            'control_accuracy': self.control_accuracy,
            'system_availability': self.system_availability,
            'system_health_factor': self.lubrication_system.system_health_factor,
            
            # Protection system results
            'protection_trip_active': protection_status['trip_active'],
            'overspeed_trip_active': protection_status['overspeed_trip'],
            'trip_reasons': protection_status['trip_reasons'],
            'active_alarms': protection_status['alarms'],
            
            # Maintenance indicators
            'maintenance_due': maintenance_flags['oil_change_due'],
            'oil_analysis_due': maintenance_flags['oil_analysis_due'],
            'component_maintenance_due': any(
                maintenance_flags.get(f'{comp}_wear_alarm', False) 
                for comp in self.lubrication_system.components.keys()
            ),
            
            # Operating statistics
            'operating_hours': self.operating_hours,
            'control_actions': self.control_actions,
            'trip_events': self.trip_events,
            'oil_operating_hours': self.lubrication_system.oil_operating_hours
        }
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, float]:
        """
        Perform maintenance on governor system
        
        Args:
            maintenance_type: Type of maintenance
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results
        """
        results = {}
        
        if maintenance_type == "oil_change":
            # Perform oil change on lubrication system
            lube_results = self.lubrication_system.perform_maintenance("oil_change")
            results.update(lube_results)
            
        elif maintenance_type == "valve_overhaul":
            # Overhaul governor valve
            self.governor_valve.valve_wear_factor = 1.0
            self.governor_valve.seat_leakage = 0.0
            self.governor_valve.actuator_efficiency = 1.0
            
            # Reset valve actuator wear in lubrication system
            lube_results = self.lubrication_system.perform_maintenance(
                "component_overhaul", component_id="valve_actuator"
            )
            results.update(lube_results)
            results['valve_overhaul_completed'] = True
            
        elif maintenance_type == "servo_valve_replacement":
            # Replace servo valves
            lube_results = self.lubrication_system.perform_maintenance(
                "component_overhaul", component_id="servo_valves"
            )
            results.update(lube_results)
            results['servo_valve_replacement_completed'] = True
            
        elif maintenance_type == "complete_overhaul":
            # Complete governor system overhaul
            self.governor_valve.valve_wear_factor = 1.0
            self.governor_valve.seat_leakage = 0.0
            self.governor_valve.actuator_efficiency = 1.0
            
            # Reset all lubrication system components
            lube_results = self.lubrication_system.perform_maintenance("component_overhaul")
            oil_results = self.lubrication_system.perform_maintenance("oil_change")
            
            results.update(lube_results)
            results.update(oil_results)
            results['complete_overhaul_completed'] = True
            
            self.maintenance_cycles += 1
        
        elif maintenance_type == "calibration":
            # Calibrate control system
            self.speed_error_integral = 0.0
            self.load_error_integral = 0.0
            self.control_accuracy = 1.0
            results['calibration_completed'] = True
        
        return results
    
    def reset_trips(self) -> bool:
        """Reset governor protection trips"""
        if not self.protection_trip_active:
            return False
        
        # Reset trip conditions
        self.protection_trip_active = False
        self.overspeed_trip_active = False
        self.trip_reasons = []
        
        # Re-enable governor
        self.governor_enabled = True
        
        # Reset control integrators
        self.speed_error_integral = 0.0
        self.load_error_integral = 0.0
        
        return True
    
    def set_control_mode(self, mode: str) -> bool:
        """
        Set governor control mode
        
        Args:
            mode: Control mode ("speed", "load", "manual")
            
        Returns:
            True if mode change successful
        """
        if mode in ["speed", "load", "manual"]:
            self.control_mode = mode
            self.manual_mode = (mode == "manual")
            
            # Reset integrators when changing modes
            self.speed_error_integral = 0.0
            self.load_error_integral = 0.0
            
            return True
        return False
    
    def set_manual_valve_position(self, position: float) -> bool:
        """
        Set manual valve position (manual mode only)
        
        Args:
            position: Valve position (%)
            
        Returns:
            True if successful
        """
        if self.manual_mode and not self.protection_trip_active:
            self.valve_position_demand = np.clip(position, 0.0, 100.0)
            return True
        return False
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'governor_enabled': float(self.governor_enabled),
            'control_mode_speed': float(self.control_mode == "speed"),
            'control_mode_load': float(self.control_mode == "load"),
            'manual_mode': float(self.manual_mode),
            'speed_setpoint': self.speed_setpoint,
            'speed_actual': self.speed_actual,
            'speed_error': self.speed_error,
            'load_setpoint': self.load_setpoint,
            'load_actual': self.load_actual,
            'load_error': self.load_error,
            'control_output': self.control_output,
            'valve_position_demand': self.valve_position_demand,
            'valve_position_actual': self.governor_valve.valve_position,
            'governor_response_time': self.governor_response_time,
            'control_accuracy': self.control_accuracy,
            'system_availability': self.system_availability,
            'protection_trip_active': float(self.protection_trip_active),
            'overspeed_trip_active': float(self.overspeed_trip_active),
            'operating_hours': self.operating_hours,
            'control_actions': float(self.control_actions),
            'trip_events': float(self.trip_events),
            'maintenance_cycles': float(self.maintenance_cycles)
        }
        
        # Add lubrication system state
        state_dict.update(self.lubrication_system.get_state_dict())
        
        return state_dict
    
    def reset(self) -> None:
        """Reset governor system to initial conditions"""
        # Reset control state
        self.control_mode = self.control_config.primary_control_mode
        self.governor_enabled = True
        self.manual_mode = False
        
        # Reset control variables
        self.speed_setpoint = self.control_config.rated_speed
        self.speed_actual = 0.0
        self.speed_error = 0.0
        self.speed_error_integral = 0.0
        self.speed_error_derivative = 0.0
        self.speed_error_previous = 0.0
        
        self.load_setpoint = self.control_config.rated_load
        self.load_actual = 0.0
        self.load_error = 0.0
        self.load_error_integral = 0.0
        self.load_error_derivative = 0.0
        self.load_error_previous = 0.0
        
        self.control_output = 0.0
        self.valve_position_demand = 50.0
        
        # Reset protection state
        self.overspeed_trip_active = False
        self.protection_trip_active = False
        self.trip_reasons = []
        
        # Reset performance metrics
        self.governor_response_time = self.control_config.governor_response_time
        self.control_accuracy = 1.0
        self.system_availability = 1.0
        
        # Reset statistics
        self.operating_hours = 0.0
        self.control_actions = 0
        self.trip_events = 0
        self.maintenance_cycles = 0
        
        # Reset subsystems
        self.lubrication_system.reset()
        
        # Reset governor valve
        self.governor_valve.valve_position = 50.0
        self.governor_valve.valve_position_demand = 50.0
        self.governor_valve.valve_velocity = 0.0
        self.governor_valve.valve_wear_factor = 1.0
        self.governor_valve.seat_leakage = 0.0
        self.governor_valve.actuator_efficiency = 1.0


# Example usage and testing
if __name__ == "__main__":
    # Create governor system with default configuration
    governor_system = TurbineGovernorSystem()
    
    print("Turbine Governor System with Lubrication Tracking - Parameter Validation")
    print("=" * 80)
    print(f"Control System ID: {governor_system.control_config.system_id}")
    print(f"Primary Control Mode: {governor_system.control_config.primary_control_mode}")
    print(f"Rated Speed: {governor_system.control_config.rated_speed} RPM")
    print(f"Rated Load: {governor_system.control_config.rated_load} MW")
    print(f"Speed Droop: {governor_system.control_config.speed_droop:.1%}")
    print()
    print(f"Lubrication System ID: {governor_system.lubrication_config.system_id}")
    print(f"Oil Reservoir: {governor_system.lubrication_config.oil_reservoir_capacity} L")
    print(f"Hydraulic Pressure: {governor_system.lubrication_config.hydraulic_system_pressure} MPa")
    print(f"Lubricated Components: {len(governor_system.lubrication_system.components)}")
    for comp_id in governor_system.lubrication_system.components:
        print(f"  - {comp_id}")
    print()
    
    # Test governor operation
    print("Testing Governor System Operation:")
    print(f"{'Time':<6} {'Mode':<6} {'Speed':<8} {'Load':<8} {'Valve':<8} {'Oil':<8} {'Trips':<15}")
    print("-" * 70)
    
    # Simulate 24 hours of operation
    for hour in range(24):
        # Simulate varying operating conditions
        if hour < 4:
            # Startup phase
            turbine_speed = 1800.0 + 450.0 * hour  # Ramp up speed
            electrical_load = 200.0 + 100.0 * hour  # Ramp up load
            speed_setpoint = 3600.0
            load_setpoint = 800.0
        elif hour < 8:
            # Normal operation
            turbine_speed = 3600.0
            electrical_load = 800.0 + 50.0 * (hour - 4)  # Increase to full load
            speed_setpoint = 3600.0
            load_setpoint = 1100.0
        elif hour < 16:
            # Full load operation with minor variations
            turbine_speed = 3600.0 + 10.0 * np.sin(hour * 0.5)  # Small speed variations
            electrical_load = 1100.0 + 20.0 * np.sin(hour * 0.3)  # Small load variations
            speed_setpoint = 3600.0
            load_setpoint = 1100.0
        elif hour < 20:
            # Load reduction
            turbine_speed = 3600.0
            electrical_load = 1100.0 - 100.0 * (hour - 16)  # Reduce load
            speed_setpoint = 3600.0
            load_setpoint = 700.0
        else:
            # Night operation
            turbine_speed = 3600.0
            electrical_load = 700.0
            speed_setpoint = 3600.0
            load_setpoint = 700.0
        
        # Update governor system
        result = governor_system.update_state(
            turbine_speed=turbine_speed,
            electrical_load=electrical_load,
            steam_pressure=6.5,
            steam_temperature=280.0,
            speed_setpoint=speed_setpoint,
            load_setpoint=load_setpoint,
            dt=1.0  # 1 hour time step
        )
        
        # Print results every 4 hours
        if hour % 4 == 0:
            mode = result['control_mode']
            speed_err = abs(result['speed_error'])
            load_err = abs(result['load_error'])
            valve_pos = result['valve_position']
            oil_qual = result['oil_quality_factor']
            trips = "Yes" if result['protection_trip_active'] else "No"
            
            print(f"{hour:<6} {mode:<6} {speed_err:<8.1f} {load_err:<8.1f} "
                  f"{valve_pos:<8.1f} {oil_qual:<8.3f} {trips:<15}")
    
    print()
    print("Final System State:")
    final_state = governor_system.get_state_dict()
    print(f"  Operating Hours: {final_state['operating_hours']:.0f}")
    print(f"  Control Actions: {final_state['control_actions']:.0f}")
    print(f"  Trip Events: {final_state['trip_events']:.0f}")
    print(f"  Oil Operating Hours: {final_state['GOV-LUB-001_oil_operating_hours']:.0f}")
    print(f"  Lubrication Effectiveness: {final_state['GOV-LUB-001_lubrication_effectiveness']:.3f}")
    print(f"  System Health Factor: {final_state['GOV-LUB-001_system_health']:.3f}")
    print()
    
    # Test component wear
    print("Component Wear Status:")
    for comp_id in governor_system.lubrication_system.components:
        wear_key = f'GOV-LUB-001_{comp_id}_wear'
        perf_key = f'GOV-LUB-001_{comp_id}_performance'
        if wear_key in final_state and perf_key in final_state:
            print(f"  {comp_id}: {final_state[wear_key]:.3f}% wear, "
                  f"{final_state[perf_key]:.3f} performance factor")
    print()
    
    # Test maintenance
    print("Testing Maintenance Operations:")
    
    # Perform oil change
    oil_results = governor_system.perform_maintenance("oil_change")
    print(f"  Oil Change: {oil_results.get('oil_change_completed', False)}")
    
    # Perform valve overhaul
    valve_results = governor_system.perform_maintenance("valve_overhaul")
    print(f"  Valve Overhaul: {valve_results.get('valve_overhaul_completed', False)}")
    
    # Test control mode changes
    print()
    print("Testing Control Mode Changes:")
    print(f"  Current Mode: {governor_system.control_mode}")
    
    success = governor_system.set_control_mode("load")
    print(f"  Switch to Load Control: {success}")
    print(f"  New Mode: {governor_system.control_mode}")
    
    success = governor_system.set_control_mode("manual")
    print(f"  Switch to Manual: {success}")
    print(f"  Manual Mode: {governor_system.manual_mode}")
    
    # Test manual valve positioning
    success = governor_system.set_manual_valve_position(75.0)
    print(f"  Set Manual Position to 75%: {success}")
    print(f"  Valve Position Demand: {governor_system.valve_position_demand}%")
    
    print()
    print("Governor System with Comprehensive Lubrication Tracking - Ready!")
    print("Key Features Implemented:")
    print("- PID speed and load control with lubrication effects")
    print("- Comprehensive lubrication system with 5 tracked components")
    print("- Oil quality tracking (contamination, acidity, moisture, additives)")
    print("- Component wear modeling with performance degradation")
    print("- Hydraulic system modeling with pressure and leakage tracking")
    print("- Protection systems with trip logic")
    print("- Maintenance scheduling and procedures")
    print("- Performance monitoring and diagnostics")
