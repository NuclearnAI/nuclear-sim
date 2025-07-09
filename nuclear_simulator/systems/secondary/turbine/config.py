"""
Turbine Configuration System

This module provides comprehensive configuration for turbine subsystems,
including all initial conditions and operational parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import warnings

# Import dataclass-wizard for configuration serialization
try:
    from dataclass_wizard import YAMLWizard, JSONWizard, TOMLWizard
    DATACLASS_WIZARD_AVAILABLE = True
    
    def dataclass_json(cls):
        return cls
        
except ImportError:
    warnings.warn("dataclass-wizard not available. Install with: pip install dataclass-wizard")
    DATACLASS_WIZARD_AVAILABLE = False
    
    def dataclass_json(cls):
        return cls
    
    class YAMLWizard:
        pass
    class JSONWizard:
        pass
    class TOMLWizard:
        pass


@dataclass_json
@dataclass
class TurbineStageSystemConfig:
    """Configuration for turbine stage system"""
    
    # Stage configuration
    hp_stages: int = 8                              # Number of HP stages
    lp_stages: int = 6                              # Number of LP stages
    
    # Extraction points
    extraction_points: List[str] = field(default_factory=lambda: ["HP-3", "HP-4", "HP-5", "LP-1", "LP-2"])
    
    # Stage design parameters
    hp_stage_efficiency: float = 0.85               # HP stage efficiency
    lp_stage_efficiency: float = 0.88               # LP stage efficiency
    
    # Extraction flow parameters (kg/s at full load)
    extraction_flows: Dict[str, float] = field(default_factory=lambda: {
        "HP-3": 25.0,
        "HP-4": 30.0,
        "HP-5": 20.0,
        "LP-1": 15.0,
        "LP-2": 10.0
    })
    
    # Stage pressure ratios
    hp_pressure_ratio_per_stage: float = 1.25       # Pressure ratio per HP stage
    lp_pressure_ratio_per_stage: float = 1.35       # Pressure ratio per LP stage
    
    # Physical geometry parameters (from stage_system.py TurbineStageConfig)
    blade_height: float = 0.05                      # m blade height
    blade_chord: float = 0.03                       # m blade chord length
    blade_count: int = 120                          # Number of blades
    nozzle_area: float = 0.1                        # m² nozzle throat area
    
    # Performance parameters (from stage_system.py TurbineStageConfig)
    reaction_ratio: float = 0.5                     # Reaction ratio (0=impulse, 1=reaction)
    velocity_coefficient: float = 0.95              # Velocity coefficient
    blade_speed_ratio: float = 0.47                 # Optimal blade speed ratio
    
    # Degradation parameters (from stage_system.py TurbineStageConfig)
    fouling_rate: float = 0.00001                   # Efficiency loss per hour
    erosion_rate: float = 0.000001                  # Blade wear rate
    deposit_buildup_rate: float = 0.00005           # Deposit accumulation rate
    
    # Control parameters (from stage_system.py TurbineStageSystemConfig)
    stage_loading_strategy: str = "optimal"         # "optimal", "uniform", "custom"
    extraction_control_mode: str = "pressure"       # "pressure", "flow", "enthalpy"
    performance_optimization: bool = True           # Enable performance optimization
    max_stage_loading: float = 1.2                  # Maximum stage loading factor
    min_stage_efficiency: float = 0.7               # Minimum allowable stage efficiency
    max_extraction_variation: float = 0.1           # Maximum extraction flow variation


@dataclass_json
@dataclass
class RotorDynamicsConfig:
    """Configuration for rotor dynamics system"""
    
    # System identification
    system_id: str = "RD-001"                       # Rotor dynamics system identifier
    
    # Rotor physical parameters
    rotor_mass: float = 150000.0                    # kg rotor mass
    rotor_length: float = 12.0                      # m rotor length
    rotor_diameter: float = 1.2                     # m rotor diameter
    moment_of_inertia: float = 45000.0              # kg⋅m² moment of inertia
    rotor_inertia: float = 45000.0                  # kg⋅m² rotor inertia (alias for compatibility)
    
    # Speed limits
    rated_speed: float = 3600.0                     # RPM rated speed
    max_speed: float = 3780.0                       # RPM maximum speed (105%)
    
    # Bearing configuration (from rotor_dynamics.py BearingConfig)
    num_bearings: int = 4                           # Number of bearings
    bearing_stiffness: float = 1e8                  # N/m bearing stiffness
    bearing_damping: float = 1e5                    # N⋅s/m bearing damping
    bearing_diameter: float = 0.6                   # m bearing diameter
    bearing_length: float = 0.4                     # m bearing length
    bearing_clearance: float = 0.15                 # mm bearing clearance
    design_load_capacity: float = 500.0             # kN design load capacity
    friction_coefficient: float = 0.001             # Friction coefficient
    
    # Vibration limits
    vibration_alarm_level: float = 15.0             # mils vibration alarm
    vibration_trip_level: float = 25.0              # mils vibration trip
    
    # Vibration monitoring (from rotor_dynamics.py VibrationConfig)
    sampling_frequency: float = 25600.0             # Hz sampling frequency
    frequency_range: List[float] = field(default_factory=lambda: [0.0, 1000.0])  # Hz frequency range
    displacement_alarm: float = 15.0                # mils displacement alarm
    displacement_trip: float = 25.0                 # mils displacement trip
    velocity_alarm: float = 7.5                     # mm/s velocity alarm
    velocity_trip: float = 12.0                     # mm/s velocity trip
    acceleration_alarm: float = 10.0                # g acceleration alarm
    acceleration_trip: float = 15.0                 # g acceleration trip
    
    # Critical speeds (from rotor_dynamics.py VibrationConfig)
    first_critical_speed: float = 1800.0            # RPM first critical speed
    second_critical_speed: float = 5400.0           # RPM second critical speed
    critical_speed_margin: float = 0.15             # 15% margin from critical speeds
    
    # Thermal expansion parameters
    thermal_expansion_coefficient: float = 12e-6    # 1/K thermal expansion coefficient
    reference_temperature: float = 20.0             # °C reference temperature
    max_thermal_expansion: float = 15.0             # mm maximum thermal expansion
    thermal_bow_limit: float = 2.0                  # mm maximum thermal bow


@dataclass_json
@dataclass
class TurbineThermalStressConfig:
    """Configuration for thermal stress monitoring and analysis"""
    
    # Material properties (from enhanced_physics.py ThermalStressConfig)
    thermal_conductivity: float = 45.0              # W/m/K thermal conductivity
    thermal_expansion_coeff: float = 12e-6          # 1/K thermal expansion coefficient
    elastic_modulus: float = 200e9                  # Pa elastic modulus
    
    # Thermal limits (from enhanced_physics.py ThermalStressConfig)
    max_thermal_gradient: float = 5.0               # °C/cm maximum thermal gradient
    max_thermal_stress: float = 800e6               # Pa maximum thermal stress
    thermal_time_constant: float = 3600.0           # seconds thermal time constant
    stress_relaxation_time: float = 7200.0          # seconds stress relaxation time
    
    # Monitoring parameters
    thermal_stress_alarm: float = 600e6             # Pa thermal stress alarm
    thermal_stress_trip: float = 800e6              # Pa thermal stress trip
    metal_temperature_alarm: float = 500.0          # °C metal temperature alarm
    metal_temperature_trip: float = 550.0           # °C metal temperature trip


@dataclass_json
@dataclass
class TurbineProtectionConfig:
    """Configuration for turbine protection system"""
    
    # Trip setpoints
    overspeed_trip: float = 3780.0                  # RPM overspeed trip (105%)
    vibration_trip: float = 25.0                    # mils vibration trip
    bearing_temp_trip: float = 120.0                # °C bearing temperature trip
    thrust_bearing_trip: float = 50.0               # mm thrust bearing displacement trip
    low_vacuum_trip: float = 0.012                  # MPa low vacuum trip
    thermal_stress_trip: float = 800e6              # Pa thermal stress trip
    max_thermal_stress: float = 800e6               # Pa maximum thermal stress (alias for compatibility)
    
    # Trip delays
    overspeed_delay: float = 0.1                    # seconds overspeed trip delay
    vibration_delay: float = 2.0                    # seconds vibration trip delay
    bearing_temp_delay: float = 10.0                # seconds bearing temp trip delay
    
    # Emergency actions
    enable_steam_dump: bool = True                  # Enable steam dump on trip
    enable_turning_gear: bool = True                # Enable turning gear after trip
    emergency_seal_steam: bool = True               # Emergency seal steam on trip
    
    # Protection system testing
    test_interval_hours: float = 168.0              # Weekly protection test
    calibration_interval_hours: float = 4380.0      # Semi-annual calibration


@dataclass_json
@dataclass
class TurbineGovernorConfig:
    """Configuration for turbine governor system"""
    
    # System identification
    system_id: str = "GOV-001"                      # Governor system identifier
    
    # Governor parameters
    rated_speed: float = 3600.0                     # RPM rated speed
    rated_load: float = 1000.0                      # MW rated load
    speed_droop: float = 0.04                       # 4% speed droop
    speed_deadband: float = 2.0                     # RPM speed deadband
    governor_gain: float = 10.0                     # Governor proportional gain
    governor_time_constant: float = 0.5             # seconds governor time constant
    governor_response_time: float = 0.2             # seconds governor response time
    
    # Control mode
    primary_control_mode: str = "speed"             # Primary control mode ("speed", "load", "pressure")
    
    # Valve parameters
    num_control_valves: int = 4                     # Number of control valves
    valve_opening_rate: float = 10.0                # %/second valve opening rate
    valve_closing_rate: float = 15.0                # %/second valve closing rate
    
    # Governor valve details (from governor_system.py GovernorValveConfig)
    valve_stroke: float = 100.0                     # mm valve stroke
    valve_area: float = 0.05                        # m² valve flow area
    valve_cv: float = 150.0                         # Valve flow coefficient
    valve_response_time: float = 0.2                # seconds valve response time
    valve_stroke_time: float = 5.0                  # seconds full stroke time
    valve_deadband: float = 0.5                     # % valve deadband
    valve_hysteresis: float = 0.5                   # % valve hysteresis
    
    # Actuator parameters (from governor_system.py GovernorValveConfig)
    actuator_pressure: float = 1.4                  # MPa actuator pressure
    actuator_force: float = 50000.0                 # N actuator force
    actuator_oil_flow: float = 10.0                 # L/min actuator oil flow
    
    # Load control
    load_following_enabled: bool = True             # Enable load following
    load_ramp_rate: float = 5.0                     # %/minute load ramp rate
    minimum_load: float = 0.2                       # 20% minimum load
    maximum_load: float = 1.05                      # 105% maximum load
    
    # Protection setpoints
    overspeed_trip: float = 3780.0                  # RPM overspeed trip (105%)
    underspeed_alarm: float = 3420.0                # RPM underspeed alarm (95%)
    
    # PID control parameters
    speed_kp: float = 0.5                           # Speed control proportional gain
    speed_ki: float = 0.1                           # Speed control integral gain
    speed_kd: float = 0.02                          # Speed control derivative gain
    speed_integral_limit: float = 100.0             # Speed integral windup limit
    
    load_kp: float = 0.3                            # Load control proportional gain
    load_ki: float = 0.05                           # Load control integral gain
    load_kd: float = 0.01                           # Load control derivative gain
    load_integral_limit: float = 150.0              # Load integral windup limit
    max_load_error: float = 5.0                     # % maximum load error


@dataclass_json
@dataclass
class TurbineLubricationConfig:
    """Configuration for turbine lubrication system"""
    
    # System identification (from turbine_bearing_lubrication.py TurbineBearingLubricationConfig)
    system_id: str = "TB-LUB-001"                   # Lubrication system identifier
    system_type: str = "turbine_bearing"            # System type
    
    # Main turbine bearing lubrication
    oil_reservoir_capacity: float = 800.0           # L bearing oil reservoir capacity
    oil_operating_pressure: float = 0.15            # MPa bearing oil operating pressure
    oil_temperature_range: List[float] = field(default_factory=lambda: [45.0, 95.0])  # °C bearing oil temperature range
    oil_viscosity_grade: str = "ISO VG 46"          # Bearing oil viscosity grade
    
    # Governor lubrication system (separate circuit from governor_system.py GovernorLubricationConfig)
    governor_system_id: str = "GOV-LUB-001"         # Governor lubrication system identifier
    governor_oil_reservoir_capacity: float = 200.0  # L governor oil reservoir capacity
    governor_oil_operating_pressure: float = 3.5    # MPa governor oil operating pressure (higher pressure for hydraulics)
    governor_oil_temperature_range: List[float] = field(default_factory=lambda: [35.0, 75.0])  # °C governor oil temperature range (tighter range)
    governor_oil_viscosity_grade: str = "ISO VG 46" # Governor oil viscosity grade (higher viscosity for hydraulics)
    
    # Governor hydraulic system parameters
    hydraulic_system_pressure: float = 3.5          # MPa hydraulic operating pressure
    servo_valve_flow_rate: float = 20.0             # L/min servo valve flow
    pilot_valve_flow_rate: float = 5.0              # L/min pilot valve flow
    accumulator_capacity: float = 50.0              # L hydraulic accumulator capacity
    
    # Governor filtration requirements (tighter for control systems)
    governor_filter_micron_rating: float = 5.0      # microns (finer filtration)
    governor_contamination_limit: float = 10.0      # ppm (stricter limit)
    
    # Governor maintenance intervals (more frequent for critical control)
    governor_oil_change_interval: float = 4380.0    # hours (6 months)
    governor_oil_analysis_interval: float = 360.0   # hours (bi-weekly)
    
    # Turbine-specific parameters
    turbine_rated_power: float = 1100.0             # MW turbine rated power
    turbine_rated_speed: float = 3600.0             # RPM turbine rated speed
    steam_temperature: float = 280.0                # °C steam temperature
    bearing_housing_temperature: float = 80.0       # °C bearing housing temperature
    
    # Enhanced filtration for steam environment
    filter_micron_rating: float = 5.0               # microns filtration rating
    contamination_limit: float = 8.0                # ppm contamination limit
    
    # High-temperature operation limits
    acidity_limit: float = 0.3                      # mg KOH/g acidity limit
    moisture_limit: float = 0.05                    # % water content limit
    viscosity_change_limit: float = 20.0            # % viscosity change limit
    
    # Maintenance intervals for critical turbine service
    oil_change_interval: float = 8760.0             # hours oil change interval
    oil_analysis_interval: float = 720.0            # hours oil analysis interval


@dataclass_json
@dataclass
class TurbineBearingConfig:
    """Configuration for turbine bearing system"""
    
    # Bearing design parameters
    bearing_type: str = "journal"                   # Bearing type
    bearing_diameter: float = 0.6                   # m bearing diameter
    bearing_length: float = 0.4                     # m bearing length
    bearing_clearance: float = 0.0002               # m bearing clearance
    
    # Lubrication parameters
    oil_viscosity: float = 0.032                    # Pa⋅s oil viscosity at operating temp
    oil_density: float = 850.0                      # kg/m³ oil density
    oil_specific_heat: float = 2100.0               # J/kg/K oil specific heat
    oil_supply_pressure: float = 0.2                # MPa oil supply pressure
    oil_supply_temperature: float = 40.0            # °C oil supply temperature
    
    # Performance parameters
    design_load_capacity: float = 500000.0          # N design load capacity
    friction_coefficient: float = 0.002             # Friction coefficient
    heat_generation_factor: float = 0.8             # Heat generation factor


@dataclass_json
@dataclass
class UnifiedLubricationInitialConditions:
    """
    Unified lubrication system initial conditions
    
    This replaces the per-bearing arrays with a realistic unified oil system
    that has one reservoir with component-specific local variations.
    """
    
    # System-wide base conditions (single oil reservoir)
    oil_reservoir_level: float = 100.0              # % oil level in main reservoir
    oil_base_temperature: float = 45.0              # °C base oil temperature
    oil_base_contamination: float = 5.0             # ppm base contamination level
    oil_base_pressure: float = 0.25                 # MPa system operating pressure
    oil_base_viscosity: float = 32.0                # cSt base oil viscosity
    oil_base_acidity: float = 0.1                   # mg KOH/g base acid number
    oil_base_moisture: float = 0.02                 # % base water content
    
    # Component-specific local factors (multipliers/offsets from base)
    component_contamination_factors: Dict[str, float] = field(default_factory=lambda: {
        'hp_journal_bearing': 1.2,      # 20% higher contamination (hot HP section)
        'lp_journal_bearing': 0.8,      # 20% lower contamination (cooler LP section)
        'thrust_bearing': 1.5,          # 50% higher contamination (high axial loads)
        'seal_oil_system': 1.1,         # 10% higher contamination (external exposure)
        'oil_coolers': 0.6              # 40% lower contamination (clean heat exchanger side)
    })
    
    component_temperature_offsets: Dict[str, float] = field(default_factory=lambda: {
        'hp_journal_bearing': +8.0,     # °C hotter due to HP steam heat
        'lp_journal_bearing': +3.0,     # °C hotter due to moderate heat
        'thrust_bearing': +12.0,        # °C hotter due to friction from axial loads
        'seal_oil_system': -2.0,        # °C cooler due to external cooling
        'oil_coolers': -5.0             # °C cooler due to heat exchanger function
    })
    
    component_wear_levels: Dict[str, float] = field(default_factory=lambda: {
        'hp_journal_bearing': 2.0,      # % initial wear level
        'lp_journal_bearing': 1.5,      # % initial wear level
        'thrust_bearing': 3.0,          # % initial wear level (highest stress)
        'seal_oil_system': 2.5,         # % initial wear level
        'oil_coolers': 1.0              # % initial wear level (lowest stress)
    })
    
    # System performance factors
    pump_efficiency: float = 0.9                    # Oil pump efficiency factor
    filter_effectiveness: float = 0.95              # Oil filter effectiveness
    cooler_effectiveness: float = 0.9               # Oil cooler heat transfer effectiveness
    system_health_factor: float = 1.0               # Overall system health (0-1)
    
    # Advanced parameters for maintenance scenarios
    oil_additive_depletion: float = 0.0             # % additive package depletion
    oil_oxidation_level: float = 0.0                # Oxidation level (0-100)
    system_cleanliness_level: float = 95.0          # % system cleanliness
    
    def get_effective_contamination(self, component_id: str) -> float:
        """Calculate effective contamination for a component"""
        factor = self.component_contamination_factors.get(component_id, 1.0)
        return self.oil_base_contamination * factor
    
    def get_effective_temperature(self, component_id: str) -> float:
        """Calculate effective oil temperature for a component"""
        offset = self.component_temperature_offsets.get(component_id, 0.0)
        return self.oil_base_temperature + offset
    
    def get_component_wear(self, component_id: str) -> float:
        """Get initial wear level for a component"""
        return self.component_wear_levels.get(component_id, 0.0)


@dataclass_json
@dataclass
class TurbineInitialConditions:
    """Initial conditions for turbine system - UNIFIED LUBRICATION VERSION"""
    
    # Rotor conditions
    rotor_speed: float = 3600.0                     # RPM initial rotor speed
    rotor_acceleration: float = 0.0                 # RPM/s initial acceleration
    rotor_temperature: float = 450.0                # °C initial rotor temperature
    
    # Load conditions
    load_demand: float = 1.0                        # Initial load demand (0-1)
    electrical_power_output: float = 1000.0         # MW initial electrical power
    mechanical_power_output: float = 1015.0         # MW initial mechanical power
    
    # Steam conditions
    steam_inlet_pressure: float = 6.9               # MPa steam inlet pressure
    steam_inlet_temperature: float = 285.8          # °C steam inlet temperature
    steam_inlet_flow: float = 1500.0                # kg/s steam inlet flow
    steam_quality: float = 0.99                     # Steam quality
    
    # Extraction conditions
    extraction_pressures: Dict[str, float] = field(default_factory=lambda: {
        "HP-3": 1.5,
        "HP-4": 1.2,
        "HP-5": 1.0,
        "LP-1": 0.3,
        "LP-2": 0.1
    })
    
    extraction_temperatures: Dict[str, float] = field(default_factory=lambda: {
        "HP-3": 200.0,
        "HP-4": 185.0,
        "HP-5": 180.0,
        "LP-1": 120.0,
        "LP-2": 80.0
    })
    
    # Governor and control
    governor_valve_position: float = 100.0          # % governor valve position
    control_valve_positions: List[float] = field(default_factory=lambda: [100.0, 100.0, 100.0, 100.0])
    
    # Bearing mechanical conditions (no individual oil tracking)
    bearing_temperatures: List[float] = field(default_factory=lambda: [80.0, 80.0, 80.0, 80.0])
    bearing_vibrations: List[float] = field(default_factory=lambda: [5.0, 5.0, 5.0, 5.0])  # mils
    bearing_oil_pressures: List[float] = field(default_factory=lambda: [0.2, 0.2, 0.2, 0.2])  # MPa
    
    # UNIFIED LUBRICATION SYSTEM (replaces all per-bearing oil arrays)
    lubrication_system: UnifiedLubricationInitialConditions = field(default_factory=UnifiedLubricationInitialConditions)
    
    # System performance conditions
    total_power_output: float = 1000.0              # MW total power output
    overall_efficiency: float = 0.34                # Overall efficiency
    
    # Thermal conditions
    casing_temperatures: List[float] = field(default_factory=lambda: [380.0, 360.0, 340.0, 320.0, 300.0, 280.0])
    blade_temperatures: List[float] = field(default_factory=lambda: [500.0, 480.0, 460.0, 440.0, 420.0, 400.0, 380.0, 360.0, 340.0, 320.0, 300.0, 280.0, 260.0, 240.0])
    
    # Protection system
    protection_system_armed: bool = True            # Protection system status
    trip_active: bool = False                       # Trip status


@dataclass_json
@dataclass
class TurbineMaintenanceConfig:
    """Maintenance configuration for turbine system"""
    
    # Performance monitoring
    efficiency_threshold: float = 0.30              # 30% efficiency threshold (below 90% of design)
    performance_factor_threshold: float = 0.85      # 85% performance factor threshold
    availability_threshold: float = 0.95            # 95% availability threshold
    
    # Thermal monitoring
    thermal_stress_threshold: float = 700e6         # Pa thermal stress threshold
    metal_temperature_threshold: float = 550.0      # °C metal temperature threshold
    thermal_gradient_threshold: float = 4.0         # °C/cm thermal gradient threshold
    
    # Vibration monitoring
    vibration_alarm_threshold: float = 15.0         # mils vibration alarm
    vibration_trend_threshold: float = 2.0          # mils/month vibration trend
    
    # Bearing monitoring
    bearing_temperature_threshold: float = 100.0    # °C bearing temperature threshold
    bearing_wear_threshold: float = 0.1             # mm bearing wear threshold
    oil_contamination_threshold: float = 10.0       # ppm oil contamination threshold
    
    # Maintenance actions
    performance_test_action: str = "turbine_performance_test"
    system_optimization_action: str = "turbine_system_optimization"
    protection_test_action: str = "turbine_protection_test"
    thermal_analysis_action: str = "thermal_stress_analysis"
    vibration_analysis_action: str = "vibration_analysis"
    bearing_inspection_action: str = "bearing_inspection"
    
    # Maintenance intervals
    performance_test_interval_hours: float = 168.0  # Weekly performance test
    system_optimization_interval_hours: float = 72.0  # 3-day optimization
    protection_test_interval_hours: float = 48.0    # 2-day protection test
    thermal_analysis_interval_hours: float = 24.0   # Daily thermal analysis
    vibration_analysis_interval_hours: float = 12.0  # 12-hour vibration analysis
    bearing_inspection_interval_hours: float = 720.0  # Monthly bearing inspection
    
    # Cooldown periods
    performance_test_cooldown_hours: float = 168.0  # Weekly cooldown
    system_optimization_cooldown_hours: float = 8760.0  # Annual cooldown
    protection_test_cooldown_hours: float = 4380.0  # Semi-annual cooldown
    thermal_analysis_cooldown_hours: float = 8760.0  # Annual cooldown
    vibration_analysis_cooldown_hours: float = 2190.0  # Quarterly cooldown
    bearing_inspection_cooldown_hours: float = 2190.0  # Quarterly cooldown


@dataclass_json
@dataclass
class TurbineConfig(YAMLWizard, JSONWizard, TOMLWizard):
    """
    Comprehensive Turbine Configuration
    
    This configuration class contains all parameters needed to initialize
    and operate the turbine system, including initial conditions,
    operational parameters, and maintenance settings.
    """
    
    # === SYSTEM IDENTIFICATION ===
    system_id: str = "TURB-001"                     # Turbine system identifier
    
    # === DESIGN PARAMETERS ===
    rated_power_mwe: float = 1000.0                 # MW electrical rated power
    design_steam_flow: float = 1500.0               # kg/s design steam flow
    design_steam_pressure: float = 6.9              # MPa design steam pressure
    design_steam_temperature: float = 285.8         # °C design steam temperature
    design_condenser_pressure: float = 0.007        # MPa design condenser pressure
    
    # === PERFORMANCE PARAMETERS ===
    design_efficiency: float = 0.34                 # Overall design efficiency
    mechanical_efficiency: float = 0.985            # Mechanical efficiency
    generator_efficiency: float = 0.985             # Generator efficiency
    auxiliary_power_fraction: float = 0.02          # Auxiliary power as fraction of gross
    
    # === OPERATIONAL PARAMETERS ===
    minimum_load: float = 0.2                       # Minimum stable load (20%)
    maximum_load: float = 1.05                      # Maximum load (105%)
    load_following_enabled: bool = True             # Enable load following
    performance_optimization: bool = True           # Enable performance optimization
    predictive_maintenance: bool = True             # Enable predictive maintenance
    
    # === SUBSYSTEM CONFIGURATIONS ===
    stage_system: TurbineStageSystemConfig = field(default_factory=TurbineStageSystemConfig)
    rotor_dynamics: RotorDynamicsConfig = field(default_factory=RotorDynamicsConfig)
    thermal_stress: TurbineThermalStressConfig = field(default_factory=TurbineThermalStressConfig)
    protection_system: TurbineProtectionConfig = field(default_factory=TurbineProtectionConfig)
    governor_system: TurbineGovernorConfig = field(default_factory=TurbineGovernorConfig)
    bearing_system: TurbineBearingConfig = field(default_factory=TurbineBearingConfig)
    lubrication_system: TurbineLubricationConfig = field(default_factory=TurbineLubricationConfig)
    
    # === INITIAL CONDITIONS ===
    initial_conditions: TurbineInitialConditions = field(default_factory=TurbineInitialConditions)
    
    # === MAINTENANCE CONFIGURATION ===
    maintenance: TurbineMaintenanceConfig = field(default_factory=TurbineMaintenanceConfig)
    
    def __post_init__(self):
        """Validate and auto-calculate derived parameters"""
        self._validate_parameters()
        self._calculate_derived_parameters()
    
    def _validate_parameters(self):
        """Validate configuration parameters"""
        errors = []
        
        # Validate basic parameters
        if self.rated_power_mwe <= 0:
            errors.append("Rated power must be positive")
        
        if self.design_steam_flow <= 0:
            errors.append("Design steam flow must be positive")
        
        if not (5.0 <= self.design_steam_pressure <= 8.0):
            errors.append("Steam pressure outside typical PWR range (5-8 MPa)")
        
        if not (280.0 <= self.design_steam_temperature <= 290.0):
            errors.append("Steam temperature outside typical PWR range (280-290°C)")
        
        if not (0.25 <= self.design_efficiency <= 0.40):
            errors.append("Turbine efficiency outside reasonable range (25-40%)")
        
        # Validate load range
        if self.minimum_load >= self.maximum_load:
            errors.append("Minimum load must be less than maximum load")
        
        if not (0.1 <= self.minimum_load <= 0.5):
            errors.append("Minimum load outside reasonable range (10-50%)")
        
        if not (1.0 <= self.maximum_load <= 1.2):
            errors.append("Maximum load outside reasonable range (100-120%)")
        
        # Validate stage configuration
        if self.stage_system.hp_stages <= 0 or self.stage_system.lp_stages <= 0:
            errors.append("Number of stages must be positive")
        
        # Note: Bearing array validation is handled in _calculate_derived_parameters
        # Arrays will be automatically adjusted to match the number of bearings
        
        if len(self.initial_conditions.control_valve_positions) != self.governor_system.num_control_valves:
            errors.append(f"Control valve positions array length ({len(self.initial_conditions.control_valve_positions)}) "
                         f"doesn't match number of valves ({self.governor_system.num_control_valves})")
        
        if errors:
            raise ValueError("Turbine configuration validation failed:\n" + 
                           "\n".join(f"  - {error}" for error in errors))
    
    def _calculate_derived_parameters(self):
        """Calculate derived parameters from design values"""
        # Calculate gross power from net power
        net_power = self.rated_power_mwe
        auxiliary_power = net_power * self.auxiliary_power_fraction / (1 - self.auxiliary_power_fraction)
        gross_power = net_power + auxiliary_power
        
        # Update initial conditions if they match defaults
        if self.initial_conditions.electrical_power_output == 1000.0:
            self.initial_conditions.electrical_power_output = net_power
        
        if self.initial_conditions.mechanical_power_output == 1015.0:
            self.initial_conditions.mechanical_power_output = gross_power / self.generator_efficiency
        
        # Ensure arrays are correct length
        while len(self.initial_conditions.bearing_temperatures) < self.rotor_dynamics.num_bearings:
            self.initial_conditions.bearing_temperatures.append(80.0)
        
        while len(self.initial_conditions.bearing_vibrations) < self.rotor_dynamics.num_bearings:
            self.initial_conditions.bearing_vibrations.append(5.0)
        
        while len(self.initial_conditions.bearing_oil_pressures) < self.rotor_dynamics.num_bearings:
            self.initial_conditions.bearing_oil_pressures.append(0.2)
        
        while len(self.initial_conditions.control_valve_positions) < self.governor_system.num_control_valves:
            self.initial_conditions.control_valve_positions.append(100.0)
        
        # Trim arrays if too long
        self.initial_conditions.bearing_temperatures = self.initial_conditions.bearing_temperatures[:self.rotor_dynamics.num_bearings]
        self.initial_conditions.bearing_vibrations = self.initial_conditions.bearing_vibrations[:self.rotor_dynamics.num_bearings]
        self.initial_conditions.bearing_oil_pressures = self.initial_conditions.bearing_oil_pressures[:self.rotor_dynamics.num_bearings]
        self.initial_conditions.control_valve_positions = self.initial_conditions.control_valve_positions[:self.governor_system.num_control_valves]
        
        # Update governor rated speed if needed
        if self.governor_system.rated_speed != self.initial_conditions.rotor_speed:
            self.governor_system.rated_speed = self.initial_conditions.rotor_speed
    
    def get_stage_config(self, stage_type: str) -> Dict[str, Any]:
        """
        Get configuration for HP or LP stages
        
        Args:
            stage_type: "HP" or "LP"
            
        Returns:
            Dictionary with stage-specific configuration
        """
        if stage_type.upper() == "HP":
            return {
                'stage_type': 'HP',
                'num_stages': self.stage_system.hp_stages,
                'stage_efficiency': self.stage_system.hp_stage_efficiency,
                'pressure_ratio_per_stage': self.stage_system.hp_pressure_ratio_per_stage,
                'extraction_points': [ep for ep in self.stage_system.extraction_points if ep.startswith('HP')],
                'inlet_pressure': self.design_steam_pressure,
                'inlet_temperature': self.design_steam_temperature
            }
        elif stage_type.upper() == "LP":
            # Calculate LP inlet conditions (after HP exhaust)
            hp_exhaust_pressure = self.design_steam_pressure / (self.stage_system.hp_pressure_ratio_per_stage ** self.stage_system.hp_stages)
            
            return {
                'stage_type': 'LP',
                'num_stages': self.stage_system.lp_stages,
                'stage_efficiency': self.stage_system.lp_stage_efficiency,
                'pressure_ratio_per_stage': self.stage_system.lp_pressure_ratio_per_stage,
                'extraction_points': [ep for ep in self.stage_system.extraction_points if ep.startswith('LP')],
                'inlet_pressure': hp_exhaust_pressure,
                'outlet_pressure': self.design_condenser_pressure
            }
        else:
            raise ValueError(f"Invalid stage type: {stage_type}. Must be 'HP' or 'LP'")
    
    def get_bearing_config(self, bearing_index: int) -> Dict[str, Any]:
        """
        Get configuration for a specific bearing
        
        Args:
            bearing_index: Bearing index (0-based)
            
        Returns:
            Dictionary with bearing-specific configuration
        """
        if not (0 <= bearing_index < self.rotor_dynamics.num_bearings):
            raise ValueError(f"Bearing index {bearing_index} out of range (0-{self.rotor_dynamics.num_bearings-1})")
        
        return {
            'bearing_id': f"BEARING-{bearing_index}",
            'bearing_type': self.bearing_system.bearing_type,
            'diameter': self.bearing_system.bearing_diameter,
            'length': self.bearing_system.bearing_length,
            'clearance': self.bearing_system.bearing_clearance,
            'design_load_capacity': self.bearing_system.design_load_capacity,
            'initial_temperature': self.initial_conditions.bearing_temperatures[bearing_index],
            'initial_vibration': self.initial_conditions.bearing_vibrations[bearing_index],
            'initial_oil_pressure': self.initial_conditions.bearing_oil_pressures[bearing_index],
            'oil_supply_temperature': self.bearing_system.oil_supply_temperature,
            'oil_viscosity': self.bearing_system.oil_viscosity,
            'friction_coefficient': self.bearing_system.friction_coefficient
        }
    
    def get_maintenance_config(self) -> Dict[str, Any]:
        """Get maintenance configuration for the turbine system"""
        return {
            'performance_monitoring': {
                'efficiency_threshold': self.maintenance.efficiency_threshold,
                'performance_factor_threshold': self.maintenance.performance_factor_threshold,
                'availability_threshold': self.maintenance.availability_threshold,
                'performance_test_action': self.maintenance.performance_test_action,
                'performance_test_interval_hours': self.maintenance.performance_test_interval_hours,
                'performance_test_cooldown_hours': self.maintenance.performance_test_cooldown_hours
            },
            'thermal_monitoring': {
                'thermal_stress_threshold': self.maintenance.thermal_stress_threshold,
                'metal_temperature_threshold': self.maintenance.metal_temperature_threshold,
                'thermal_gradient_threshold': self.maintenance.thermal_gradient_threshold,
                'thermal_analysis_action': self.maintenance.thermal_analysis_action,
                'thermal_analysis_interval_hours': self.maintenance.thermal_analysis_interval_hours,
                'thermal_analysis_cooldown_hours': self.maintenance.thermal_analysis_cooldown_hours
            },
            'vibration_monitoring': {
                'vibration_alarm_threshold': self.maintenance.vibration_alarm_threshold,
                'vibration_trend_threshold': self.maintenance.vibration_trend_threshold,
                'vibration_analysis_action': self.maintenance.vibration_analysis_action,
                'vibration_analysis_interval_hours': self.maintenance.vibration_analysis_interval_hours,
                'vibration_analysis_cooldown_hours': self.maintenance.vibration_analysis_cooldown_hours
            },
            'bearing_monitoring': {
                'bearing_temperature_threshold': self.maintenance.bearing_temperature_threshold,
                'bearing_wear_threshold': self.maintenance.bearing_wear_threshold,
                'oil_contamination_threshold': self.maintenance.oil_contamination_threshold,
                'bearing_inspection_action': self.maintenance.bearing_inspection_action,
                'bearing_inspection_interval_hours': self.maintenance.bearing_inspection_interval_hours,
                'bearing_inspection_cooldown_hours': self.maintenance.bearing_inspection_cooldown_hours
            },
            'system_optimization': {
                'system_optimization_action': self.maintenance.system_optimization_action,
                'system_optimization_interval_hours': self.maintenance.system_optimization_interval_hours,
                'system_optimization_cooldown_hours': self.maintenance.system_optimization_cooldown_hours
            },
            'protection_system': {
                'protection_test_action': self.maintenance.protection_test_action,
                'protection_test_interval_hours': self.maintenance.protection_test_interval_hours,
                'protection_test_cooldown_hours': self.maintenance.protection_test_cooldown_hours
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the turbine configuration"""
        return {
            'system_info': {
                'system_id': self.system_id,
                'rated_power_mwe': self.rated_power_mwe,
                'design_steam_flow_kgs': self.design_steam_flow,
                'design_steam_pressure_mpa': self.design_steam_pressure,
                'design_steam_temperature_c': self.design_steam_temperature,
                'design_efficiency': self.design_efficiency
            },
            'stage_system': {
                'hp_stages': self.stage_system.hp_stages,
                'lp_stages': self.stage_system.lp_stages,
                'total_stages': self.stage_system.hp_stages + self.stage_system.lp_stages,
                'extraction_points': len(self.stage_system.extraction_points),
                'hp_efficiency': self.stage_system.hp_stage_efficiency,
                'lp_efficiency': self.stage_system.lp_stage_efficiency
            },
            'rotor_dynamics': {
                'rotor_mass_kg': self.rotor_dynamics.rotor_mass,
                'rotor_length_m': self.rotor_dynamics.rotor_length,
                'moment_of_inertia_kgm2': self.rotor_dynamics.moment_of_inertia,
                'num_bearings': self.rotor_dynamics.num_bearings,
                'vibration_trip_level_mils': self.rotor_dynamics.vibration_trip_level
            },
            'initial_conditions': {
                'rotor_speed_rpm': self.initial_conditions.rotor_speed,
                'load_demand': self.initial_conditions.load_demand,
                'electrical_power_mw': self.initial_conditions.electrical_power_output,
                'mechanical_power_mw': self.initial_conditions.mechanical_power_output,
                'steam_inlet_pressure_mpa': self.initial_conditions.steam_inlet_pressure,
                'steam_inlet_temperature_c': self.initial_conditions.steam_inlet_temperature,
                'steam_inlet_flow_kgs': self.initial_conditions.steam_inlet_flow,
                'governor_valve_position_pct': self.initial_conditions.governor_valve_position,
                'avg_bearing_temperature_c': sum(self.initial_conditions.bearing_temperatures) / len(self.initial_conditions.bearing_temperatures),
                'max_bearing_vibration_mils': max(self.initial_conditions.bearing_vibrations)
            },
            'protection_system': {
                'overspeed_trip_rpm': self.protection_system.overspeed_trip,
                'vibration_trip_mils': self.protection_system.vibration_trip,
                'bearing_temp_trip_c': self.protection_system.bearing_temp_trip,
                'thermal_stress_trip_pa': self.protection_system.thermal_stress_trip,
                'protection_armed': self.initial_conditions.protection_system_armed
            },
            'maintenance': {
                'efficiency_threshold': self.maintenance.efficiency_threshold,
                'performance_factor_threshold': self.maintenance.performance_factor_threshold,
                'vibration_alarm_threshold_mils': self.maintenance.vibration_alarm_threshold,
                'bearing_temperature_threshold_c': self.maintenance.bearing_temperature_threshold,
                'performance_test_interval_hours': self.maintenance.performance_test_interval_hours
            }
        }


# Factory functions for creating common configurations
def create_standard_turbine_config() -> TurbineConfig:
    """Create standard PWR turbine configuration"""
    return TurbineConfig(
        system_id="TURB-STD-001",
        rated_power_mwe=1000.0,
        design_steam_flow=1500.0,
        design_steam_pressure=6.9,
        design_steam_temperature=285.8,
        design_efficiency=0.34
    )


def create_uprated_turbine_config() -> TurbineConfig:
    """Create uprated PWR turbine configuration"""
    return TurbineConfig(
        system_id="TURB-UP-001",
        rated_power_mwe=1100.0,          # Higher power
        design_steam_flow=1665.0,        # Higher steam flow
        design_steam_pressure=6.9,
        design_steam_temperature=285.8,
        design_efficiency=0.35,          # Higher efficiency
        maximum_load=1.08                # Higher maximum load
    )


def create_high_efficiency_turbine_config() -> TurbineConfig:
    """Create high-efficiency PWR turbine configuration"""
    config = TurbineConfig(
        system_id="TURB-HE-001",
        rated_power_mwe=1000.0,
        design_steam_flow=1500.0,
        design_steam_pressure=6.9,
        design_steam_temperature=285.8,
        design_efficiency=0.36           # Higher efficiency
    )
    
    # Optimize stage efficiencies
    config.stage_system.hp_stage_efficiency = 0.87
    config.stage_system.lp_stage_efficiency = 0.90
    
    return config


# Example usage and testing
if __name__ == "__main__":
    print("Turbine Configuration System")
    print("=" * 50)
    
    # Test standard configuration
    config = create_standard_turbine_config()
    summary = config.get_summary()
    
    print("Standard Configuration:")
    print(f"  System ID: {summary['system_info']['system_id']}")
    print(f"  Rated Power: {summary['system_info']['rated_power_mwe']:.0f} MW")
    print(f"  Design Steam Flow: {summary['system_info']['design_steam_flow_kgs']:.0f} kg/s")
    print(f"  Design Efficiency: {summary['system_info']['design_efficiency']:.1%}")
    print(f"  Steam Pressure: {summary['system_info']['design_steam_pressure_mpa']:.1f} MPa")
    print(f"  Steam Temperature: {summary['system_info']['design_steam_temperature_c']:.1f} °C")
    print()
    
    print("Stage System:")
    print(f"  HP Stages: {summary['stage_system']['hp_stages']}")
    print(f"  LP Stages: {summary['stage_system']['lp_stages']}")
    print(f"  Total Stages: {summary['stage_system']['total_stages']}")
    print(f"  Extraction Points: {summary['stage_system']['extraction_points']}")
    print(f"  HP Efficiency: {summary['stage_system']['hp_efficiency']:.1%}")
    print(f"  LP Efficiency: {summary['stage_system']['lp_efficiency']:.1%}")
    print()
    
    print("Rotor Dynamics:")
    print(f"  Rotor Mass: {summary['rotor_dynamics']['rotor_mass_kg']:.0f} kg")
    print(f"  Rotor Length: {summary['rotor_dynamics']['rotor_length_m']:.1f} m")
    print(f"  Moment of Inertia: {summary['rotor_dynamics']['moment_of_inertia_kgm2']:.0f} kg⋅m²")
    print(f"  Number of Bearings: {summary['rotor_dynamics']['num_bearings']}")
    print(f"  Vibration Trip Level: {summary['rotor_dynamics']['vibration_trip_level_mils']:.1f} mils")
    print()
    
    print("Initial Conditions:")
    print(f"  Rotor Speed: {summary['initial_conditions']['rotor_speed_rpm']:.0f} RPM")
    print(f"  Load Demand: {summary['initial_conditions']['load_demand']:.1%}")
    print(f"  Electrical Power: {summary['initial_conditions']['electrical_power_mw']:.0f} MW")
    print(f"  Mechanical Power: {summary['initial_conditions']['mechanical_power_mw']:.0f} MW")
    print(f"  Steam Inlet Pressure: {summary['initial_conditions']['steam_inlet_pressure_mpa']:.1f} MPa")
    print(f"  Steam Inlet Temperature: {summary['initial_conditions']['steam_inlet_temperature_c']:.1f} °C")
    print(f"  Steam Inlet Flow: {summary['initial_conditions']['steam_inlet_flow_kgs']:.0f} kg/s")
    print(f"  Governor Valve Position: {summary['initial_conditions']['governor_valve_position_pct']:.0f}%")
    print(f"  Avg Bearing Temperature: {summary['initial_conditions']['avg_bearing_temperature_c']:.1f} °C")
    print(f"  Max Bearing Vibration: {summary['initial_conditions']['max_bearing_vibration_mils']:.1f} mils")
    print()
    
    # Test individual bearing configuration
    bearing0_config = config.get_bearing_config(0)
    print("Bearing-0 Configuration:")
    print(f"  Bearing ID: {bearing0_config['bearing_id']}")
    print(f"  Bearing Type: {bearing0_config['bearing_type']}")
    print(f"  Diameter: {bearing0_config['diameter']:.2f} m")
    print(f"  Length: {bearing0_config['length']:.2f} m")
    print(f"  Initial Temperature: {bearing0_config['initial_temperature']:.1f} °C")
    print(f"  Initial Vibration: {bearing0_config['initial_vibration']:.1f} mils")
    print(f"  Oil Supply Temperature: {bearing0_config['oil_supply_temperature']:.1f} °C")
    print()
    
    # Test stage configuration
    hp_config = config.get_stage_config("HP")
    lp_config = config.get_stage_config("LP")
    print("HP Stage Configuration:")
    print(f"  Number of Stages: {hp_config['num_stages']}")
    print(f"  Stage Efficiency: {hp_config['stage_efficiency']:.1%}")
    print(f"  Pressure Ratio per Stage: {hp_config['pressure_ratio_per_stage']:.2f}")
    print(f"  Extraction Points: {hp_config['extraction_points']}")
    print()
    
    print("LP Stage Configuration:")
    print(f"  Number of Stages: {lp_config['num_stages']}")
    print(f"  Stage Efficiency: {lp_config['stage_efficiency']:.1%}")
    print(f"  Pressure Ratio per Stage: {lp_config['pressure_ratio_per_stage']:.2f}")
    print(f"  Extraction Points: {lp_config['extraction_points']}")
    print(f"  Inlet Pressure: {lp_config['inlet_pressure']:.3f} MPa")
    print(f"  Outlet Pressure: {lp_config['outlet_pressure']:.3f} MPa")
    print()
    
    # Test maintenance configuration
    maint_config = config.get_maintenance_config()
    print("Maintenance Configuration:")
    print(f"  Efficiency Threshold: {maint_config['performance_monitoring']['efficiency_threshold']:.1%}")
    print(f"  Performance Factor Threshold: {maint_config['performance_monitoring']['performance_factor_threshold']:.1%}")
    print(f"  Vibration Alarm Threshold: {maint_config['vibration_monitoring']['vibration_alarm_threshold']:.1f} mils")
    print(f"  Bearing Temperature Threshold: {maint_config['bearing_monitoring']['bearing_temperature_threshold']:.0f} °C")
    print(f"  Performance Test Interval: {maint_config['performance_monitoring']['performance_test_interval_hours']:.0f} hours")
    print()
    
    # Test file operations if available
    if DATACLASS_WIZARD_AVAILABLE:
        print("Testing YAML serialization...")
        try:
            # Save to YAML
            config.to_yaml_file("test_turbine_config.yaml")
            
            # Load from YAML
            loaded_config = TurbineConfig.from_yaml_file("test_turbine_config.yaml")
            
            print("  YAML serialization: SUCCESS")
            print(f"  Loaded config system ID: {loaded_config.system_id}")
            
            # Clean up
            import os
            os.remove("test_turbine_config.yaml")
            
        except Exception as e:
            print(f"  YAML serialization failed: {e}")
    else:
        print("Install dataclass-wizard for YAML serialization: pip install dataclass-wizard")
    
    print("Turbine configuration system ready!")
