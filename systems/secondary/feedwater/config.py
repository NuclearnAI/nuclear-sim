"""
Feedwater Configuration System

This module provides comprehensive configuration for feedwater subsystems,
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
class FeedwaterPumpSystemConfig:
    """Configuration for feedwater pump system"""
    
    # Pump system design
    num_pumps: int = 4                              # Total number of pumps
    pumps_normally_running: int = 3                 # Number of pumps normally running
    design_flow_per_pump: float = 500.0             # kg/s design flow per pump
    design_head_per_pump: float = 800.0             # m design head per pump
    
    # Pump physical parameters
    pump_efficiency: float = 0.85                   # Pump efficiency
    motor_efficiency: float = 0.95                  # Motor efficiency
    pump_speed: float = 3600.0                      # RPM pump speed
    impeller_diameter: float = 0.8                  # m impeller diameter
    
    # Pump performance curves (simplified)
    flow_coefficients: List[float] = field(default_factory=lambda: [1.0, -0.0001, -0.000001])  # Head vs flow curve
    efficiency_coefficients: List[float] = field(default_factory=lambda: [0.85, 0.0001, -0.000001])  # Efficiency vs flow
    
    # Pump control
    variable_speed_control: bool = True             # Enable variable speed control
    minimum_speed_fraction: float = 0.5             # Minimum speed as fraction of rated
    maximum_speed_fraction: float = 1.1             # Maximum speed as fraction of rated
    
    # Pump protection
    minimum_flow_protection: bool = True            # Enable minimum flow protection
    minimum_flow_fraction: float = 0.1              # Minimum flow as fraction of design
    cavitation_protection: bool = True              # Enable cavitation protection
    npsh_required: float = 8.0                      # m NPSH required


@dataclass_json
@dataclass
class ThreeElementControlConfig:
    """Configuration for three-element feedwater control"""
    
    # Control system parameters
    enable_three_element_control: bool = True       # Enable three-element control
    steam_flow_weight: float = 0.5                  # Steam flow feedforward weight
    level_control_weight: float = 0.4               # Level feedback weight
    feedwater_flow_weight: float = 0.1              # Feedwater flow feedback weight
    
    # Level control parameters
    level_setpoint: float = 12.5                    # m level setpoint
    level_deadband: float = 0.1                     # m level control deadband
    level_proportional_gain: float = 10.0           # Level proportional gain
    level_integral_time: float = 60.0               # seconds level integral time
    level_derivative_time: float = 5.0              # seconds level derivative time
    
    # Flow control parameters
    flow_proportional_gain: float = 5.0             # Flow proportional gain
    flow_integral_time: float = 30.0                # seconds flow integral time
    steam_flow_lag_time: float = 10.0               # seconds steam flow measurement lag
    
    # Control limits
    maximum_flow_demand: float = 1.2                # Maximum flow demand (fraction of design)
    minimum_flow_demand: float = 0.1                # Minimum flow demand (fraction of design)
    flow_rate_limit: float = 0.1                    # Flow rate limit (fraction/second)
    
    # Steam quality compensation
    enable_steam_quality_compensation: bool = True  # Enable steam quality compensation
    quality_compensation_gain: float = 1.0          # Steam quality compensation gain


@dataclass_json
@dataclass
class FeedwaterWaterTreatmentConfig:
    """Configuration for feedwater water treatment"""
    
    # Chemical treatment
    enable_chemical_treatment: bool = True          # Enable chemical treatment
    oxygen_scavenger_dose: float = 10.0             # mg/L oxygen scavenger dose
    ph_control_agent_dose: float = 5.0              # mg/L pH control agent dose
    corrosion_inhibitor_dose: float = 2.0           # mg/L corrosion inhibitor dose
    
    # Water quality targets
    target_ph: float = 9.2                          # Target pH
    target_dissolved_oxygen: float = 0.005          # mg/L target dissolved oxygen
    target_iron_concentration: float = 0.1          # mg/L target iron concentration
    target_copper_concentration: float = 0.05       # mg/L target copper concentration
    
    # Treatment system parameters
    chemical_injection_rate: float = 1.0            # L/min chemical injection rate
    mixing_time: float = 300.0                      # seconds mixing time
    treatment_efficiency: float = 0.95              # Treatment efficiency
    
    # Monitoring parameters
    ph_measurement_accuracy: float = 0.1            # pH measurement accuracy
    dissolved_oxygen_accuracy: float = 0.001        # mg/L DO measurement accuracy
    conductivity_accuracy: float = 0.1              # µS/cm conductivity accuracy


@dataclass_json
@dataclass
class FeedwaterPerformanceConfig:
    """Configuration for feedwater performance monitoring"""
    
    # Performance monitoring
    enable_performance_monitoring: bool = True      # Enable performance monitoring
    efficiency_monitoring_interval: float = 60.0    # minutes efficiency monitoring interval
    cavitation_monitoring_interval: float = 10.0    # minutes cavitation monitoring interval
    
    # Performance thresholds
    pump_efficiency_threshold: float = 0.80         # Pump efficiency threshold (below 95% of design)
    system_efficiency_threshold: float = 0.75       # System efficiency threshold
    cavitation_threshold: float = 0.1               # Cavitation index threshold
    vibration_threshold: float = 10.0               # mm/s vibration threshold
    
    # Wear monitoring
    enable_wear_monitoring: bool = True             # Enable wear monitoring
    impeller_wear_threshold: float = 2.0            # mm impeller wear threshold
    bearing_wear_threshold: float = 0.5             # mm bearing wear threshold
    seal_leakage_threshold: float = 1.0             # L/min seal leakage threshold
    
    # Trending parameters
    performance_trend_window: float = 168.0         # hours performance trend window (1 week)
    efficiency_trend_threshold: float = 0.02        # Efficiency trend threshold (2% per week)
    vibration_trend_threshold: float = 1.0          # mm/s vibration trend threshold


@dataclass_json
@dataclass
class FeedwaterProtectionConfig:
    """Configuration for feedwater protection system"""
    
    # Pump protection trips
    low_suction_pressure_trip: float = 0.1          # MPa low suction pressure trip
    high_discharge_pressure_trip: float = 10.0      # MPa high discharge pressure trip
    low_flow_trip: float = 0.05                     # Fraction of design flow for low flow trip
    high_vibration_trip: float = 25.0               # mm/s high vibration trip
    high_bearing_temperature_trip: float = 120.0    # °C high bearing temperature trip
    
    # System protection trips
    low_sg_level_trip: float = 10.0                 # m low SG level trip
    high_sg_level_trip: float = 15.0                # m high SG level trip
    feedwater_line_break_trip: float = 2.0          # Fraction of design flow for line break detection
    
    # Trip delays
    low_suction_pressure_delay: float = 5.0         # seconds low suction pressure delay
    high_discharge_pressure_delay: float = 2.0      # seconds high discharge pressure delay
    low_flow_delay: float = 10.0                    # seconds low flow delay
    high_vibration_delay: float = 5.0               # seconds high vibration delay
    
    # Emergency actions
    enable_pump_runback: bool = True                # Enable pump runback on trip
    enable_backup_pump_start: bool = True          # Enable backup pump auto-start
    enable_emergency_feedwater: bool = True        # Enable emergency feedwater system
    enable_steam_dump: bool = True

    # Protection system testing
    test_interval_hours: float = 168.0              # Weekly protection test
    calibration_interval_hours: float = 4380.0      # Semi-annual calibration


@dataclass_json
@dataclass
class FeedwaterInitialConditions:
    """Initial conditions for feedwater system"""
    
    # System flow conditions
    total_flow_rate: float = 1500.0                 # kg/s total system flow rate
    total_power_consumption: float = 15.0           # MW total power consumption
    system_efficiency: float = 0.85                 # System efficiency
    
    # Steam generator conditions
    sg_levels: List[float] = field(default_factory=lambda: [12.5, 12.5, 12.5])  # m SG levels
    sg_pressures: List[float] = field(default_factory=lambda: [6.9, 6.9, 6.9])  # MPa SG pressures
    sg_steam_flows: List[float] = field(default_factory=lambda: [500.0, 500.0, 500.0])  # kg/s steam flows
    sg_steam_qualities: List[float] = field(default_factory=lambda: [0.99, 0.99, 0.99])  # Steam qualities
    
    # Pump conditions
    pump_speeds: List[float] = field(default_factory=lambda: [3600.0, 3600.0, 3600.0, 0.0])  # RPM pump speeds
    pump_flows: List[float] = field(default_factory=lambda: [500.0, 500.0, 500.0, 0.0])  # kg/s pump flows
    pump_heads: List[float] = field(default_factory=lambda: [800.0, 800.0, 800.0, 0.0])  # m pump heads
    pump_efficiencies: List[float] = field(default_factory=lambda: [0.85, 0.85, 0.85, 0.0])  # Pump efficiencies
    running_pumps: List[bool] = field(default_factory=lambda: [True, True, True, False])  # Pump running status
    
    # System pressures and temperatures
    suction_pressure: float = 0.5                   # MPa suction pressure
    discharge_pressure: float = 8.0                 # MPa discharge pressure
    feedwater_temperature: float = 227.0            # °C feedwater temperature
    condensate_temperature: float = 39.0            # °C condensate temperature
    
    # Control system conditions
    control_mode: str = "automatic"                 # Control mode ("automatic", "manual")
    level_control_active: bool = True               # Level control status
    flow_control_active: bool = True                # Flow control status
    level_setpoint: float = 12.5                    # m level setpoint
    flow_demand: float = 1500.0                     # kg/s flow demand
    
    # Water quality conditions
    feedwater_ph: float = 9.2                       # Feedwater pH
    dissolved_oxygen: float = 0.005                 # mg/L dissolved oxygen
    iron_concentration: float = 0.1                 # mg/L iron concentration
    copper_concentration: float = 0.05              # mg/L copper concentration
    conductivity: float = 1.0                       # µS/cm conductivity
    
    # Performance monitoring (existing)
    pump_vibrations: List[float] = field(default_factory=lambda: [5.0, 5.0, 5.0, 0.0])  # mm/s pump vibrations
    bearing_temperatures: List[float] = field(default_factory=lambda: [80.0, 80.0, 80.0, 25.0])  # °C bearing temps
    seal_leakage_rate: List[float] = field(default_factory=lambda: [0.1, 0.1, 0.1, 0.0])  # L/min seal leakage rates (authoritative)
    pump_oil_levels: List[float] = field(default_factory=lambda: [100.0, 100.0, 100.0, 100.0])  # % pump oil levels
    
    # === EXTENDED OIL & LUBRICATION PARAMETERS ===
    # Oil quality parameters - FIXED: Match YAML structure (single values for system-wide parameters)
    pump_oil_contamination: float = 5.0             # ppm oil contamination (system-wide)
    pump_oil_viscosity: float = 46.0                # cSt oil viscosity (system-wide)
    pump_oil_water_content: float = 0.05            # % water content (system-wide)
    pump_oil_acid_number: float = 1.0               # mg KOH/g acid number (system-wide)
    oil_temperature: float = 45.0                   # °C oil temperature (system-wide)
    oil_system_debris_count: float = 200.0          # particles/ml debris count (system-wide)
    
    # Oil filtration parameters - FIXED: Match YAML structure (single values)
    oil_filter_pressure_drop: float = 0.15          # MPa filter pressure drop (system-wide)
    oil_filter_contamination: float = 50.0          # % filter capacity used (system-wide)
    
    # Lubrication system parameters - FIXED: Match YAML structure (single value)
    lubrication_system_pressure: float = 0.25       # MPa lubrication system pressure (system-wide)
    oil_pressure: List[float] = field(default_factory=lambda: [0.25, 0.25, 0.25, 0.25])  # MPa oil pressure per pump
    oil_flow_rate: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction of design flow per pump
    oil_cooler_effectiveness: List[float] = field(default_factory=lambda: [0.95, 0.95, 0.95, 0.95])  # Heat transfer effectiveness per pump
    
    # === EXTENDED MECHANICAL PARAMETERS ===
    # Enhanced bearing parameters
    bearing_vibrations: List[float] = field(default_factory=lambda: [10.0, 10.0, 10.0, 10.0])  # mm/s bearing vibrations per pump
    bearing_noise_level: List[float] = field(default_factory=lambda: [70.0, 70.0, 70.0, 70.0])  # dB bearing noise per pump
    
    # === INDIVIDUAL BEARING WEAR PARAMETERS ===
    # Individual bearing wear by type
    motor_bearing_wear: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])    # Motor bearing wear per pump (fraction 0-1)
    pump_bearing_wear: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])     # Pump bearing wear per pump (fraction 0-1)  
    thrust_bearing_wear: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])   # Thrust bearing wear per pump (fraction 0-1)
    
    # Enhanced seal parameters
    seal_face_wear: List[float] = field(default_factory=lambda: [0.3, 0.3, 0.3, 0.3])  # Fraction of seal life used per pump
    seal_temperature: List[float] = field(default_factory=lambda: [70.0, 70.0, 70.0, 70.0])  # °C seal temperature per pump
    seal_pressure_drop: List[float] = field(default_factory=lambda: [0.08, 0.08, 0.08, 0.08])  # MPa seal pressure drop per pump
    seal_leakage_rate: List[float] = field(default_factory=lambda: [0.02, 0.02, 0.02, 0.02])  # L/min seal leakage rate per pump
    
    # Enhanced impeller parameters
    impeller_wear: List[float] = field(default_factory=lambda: [0.3, 0.3, 0.3, 0.3])  # Fraction of impeller life used per pump
    impeller_cavitation_damage: List[float] = field(default_factory=lambda: [0.1, 0.1, 0.1, 0.1])  # Cavitation damage fraction per pump
    impeller_vibration: List[float] = field(default_factory=lambda: [8.0, 8.0, 8.0, 8.0])  # mm/s impeller vibration per pump
    impeller_damage: List[float] = field(default_factory=lambda: [0.05, 0.05, 0.05, 0.05])  # Impeller damage fraction per pump
    
    # Motor parameters
    motor_temperature: List[float] = field(default_factory=lambda: [70.0, 70.0, 70.0, 70.0])  # °C motor temperature per pump
    
    # === EXTENDED PERFORMANCE & SYSTEM PARAMETERS ===
    # Performance parameters (as fractions of design values)
    pump_head: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction of design head per pump
    pump_flow: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction of design flow per pump
    pump_power: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction of design power per pump
    
    # NPSH and cavitation parameters
    npsh_available: List[float] = field(default_factory=lambda: [12.0, 12.0, 12.0, 12.0])  # m NPSH available per pump
    cavitation_inception: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction of design flow for cavitation per pump
    cavitation_intensity: List[float] = field(default_factory=lambda: [0.05, 0.05, 0.05, 0.05])  # Cavitation intensity index per pump
    noise_level: List[float] = field(default_factory=lambda: [75.0, 75.0, 75.0, 75.0])  # dB noise level per pump
    
    # === SYSTEM CHECK PARAMETERS ===
    # Suction system parameters
    suction_line_pressure_drop: List[float] = field(default_factory=lambda: [0.03, 0.03, 0.03, 0.03])  # MPa suction line pressure drop per pump
    suction_strainer_dp: List[float] = field(default_factory=lambda: [0.01, 0.01, 0.01, 0.01])  # MPa suction strainer pressure drop per pump
    suction_line_air_content: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # % air content by volume per pump
    
    # Discharge system parameters
    discharge_valve_position: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction valve open per pump
    discharge_line_vibration: List[float] = field(default_factory=lambda: [8.0, 8.0, 8.0, 8.0])  # mm/s discharge line vibration per pump
    
    # === COOLING SYSTEM PARAMETERS ===
    # Cooling water parameters
    cooling_water_temperature: List[float] = field(default_factory=lambda: [25.0, 25.0, 25.0, 25.0])  # °C cooling water temperature per pump
    cooling_water_flow: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # Fraction of design flow per pump
    heat_exchanger_fouling: List[float] = field(default_factory=lambda: [0.1, 0.1, 0.1, 0.1])  # Fouling factor per pump
    
    # Protection system
    protection_system_armed: bool = True            # Protection system status
    trip_active: bool = False                       # Trip status


@dataclass_json
@dataclass
class FeedwaterMaintenanceConfig:
    """Maintenance configuration for feedwater system"""
    
    # Pump performance monitoring (factor-based thresholds)
    efficiency_factor_threshold: float = 0.80       # 80% efficiency factor threshold
    flow_factor_threshold: float = 0.90             # 90% flow factor threshold
    head_factor_threshold: float = 0.92             # 92% head factor threshold
    system_efficiency_threshold: float = 0.75       # 75% system efficiency threshold
    performance_factor_threshold: float = 0.85      # 85% performance factor threshold
    
    # Mechanical monitoring
    vibration_threshold: float = 15.0               # mm/s vibration threshold
    bearing_temperature_threshold: float = 100.0    # °C bearing temperature threshold
    seal_leakage_threshold: float = 0.5             # L/min seal leakage threshold
    impeller_wear_threshold: float = 1.5            # mm impeller wear threshold
    
    # Water quality monitoring
    ph_deviation_threshold: float = 0.3             # pH deviation from target
    dissolved_oxygen_threshold: float = 0.01        # mg/L dissolved oxygen threshold
    iron_concentration_threshold: float = 0.2       # mg/L iron concentration threshold
    conductivity_threshold: float = 2.0             # µS/cm conductivity threshold
    
    # Cavitation monitoring
    cavitation_index_threshold: float = 0.2         # Cavitation index threshold
    npsh_margin_threshold: float = 2.0              # m NPSH margin threshold
    suction_pressure_threshold: float = 0.2         # MPa minimum suction pressure
    
    # Maintenance actions
    pump_maintenance_action: str = "pump_maintenance"
    oil_change_action: str = "oil_change"
    oil_top_off_action: str = "oil_top_off"
    impeller_inspection_action: str = "impeller_inspection"
    bearing_replacement_action: str = "bearing_replacement"
    seal_replacement_action: str = "seal_replacement"
    vibration_analysis_action: str = "vibration_analysis"
    component_overhaul_action: str = "component_overhaul"
    water_treatment_action: str = "water_treatment"
    control_calibration_action: str = "control_calibration"
    system_cleaning_action: str = "system_cleaning"
    
    # Maintenance intervals
    pump_maintenance_interval_hours: float = 2190.0  # Quarterly pump maintenance
    oil_change_interval_hours: float = 4380.0       # Semi-annual oil change
    oil_top_off_interval_hours: float = 720.0       # Monthly oil top-off
    impeller_inspection_interval_hours: float = 8760.0  # Annual impeller inspection
    bearing_replacement_interval_hours: float = 17520.0  # Biennial bearing replacement
    seal_replacement_interval_hours: float = 8760.0  # Annual seal replacement
    vibration_analysis_interval_hours: float = 168.0  # Weekly vibration analysis
    component_overhaul_interval_hours: float = 43800.0  # 5-year component overhaul
    water_treatment_interval_hours: float = 720.0    # Monthly water treatment
    control_calibration_interval_hours: float = 4380.0  # Semi-annual control calibration
    system_cleaning_interval_hours: float = 2190.0   # Quarterly system cleaning
    
    # Cooldown periods
    pump_maintenance_cooldown_hours: float = 2190.0  # Quarterly cooldown
    oil_change_cooldown_hours: float = 4380.0       # Semi-annual cooldown
    oil_top_off_cooldown_hours: float = 168.0       # Weekly cooldown
    impeller_inspection_cooldown_hours: float = 8760.0  # Annual cooldown
    bearing_replacement_cooldown_hours: float = 17520.0  # Biennial cooldown
    seal_replacement_cooldown_hours: float = 8760.0  # Annual cooldown
    vibration_analysis_cooldown_hours: float = 168.0  # Weekly cooldown
    component_overhaul_cooldown_hours: float = 43800.0  # 5-year cooldown
    water_treatment_cooldown_hours: float = 720.0    # Monthly cooldown
    control_calibration_cooldown_hours: float = 4380.0  # Semi-annual cooldown
    system_cleaning_cooldown_hours: float = 2190.0   # Quarterly cooldown


@dataclass_json
@dataclass
class FeedwaterConfig(YAMLWizard, JSONWizard, TOMLWizard):
    """
    Comprehensive Feedwater Configuration
    
    This configuration class contains all parameters needed to initialize
    and operate the feedwater system, including initial conditions,
    operational parameters, and maintenance settings.
    """
    
    # === SYSTEM IDENTIFICATION ===
    system_id: str = "FW-001"                       # Feedwater system identifier
    
    # === DESIGN PARAMETERS ===
    num_steam_generators: int = 3                   # Number of steam generators
    design_total_flow: float = 1500.0               # kg/s total design flow
    design_sg_level: float = 12.5                   # m design steam generator level
    design_feedwater_temperature: float = 227.0     # °C design feedwater temperature
    design_pressure: float = 8.0                    # MPa design system pressure
    design_suction_pressure: float = 0.5            # MPa design suction pressure
    
    # === PERFORMANCE PARAMETERS ===
    design_efficiency: float = 0.85                 # Overall system design efficiency
    minimum_flow_fraction: float = 0.1              # Minimum flow as fraction of design
    maximum_flow_fraction: float = 1.2              # Maximum flow as fraction of design
    
    # === OPERATIONAL PARAMETERS ===
    auto_level_control: bool = True                 # Enable automatic level control
    load_following_enabled: bool = True             # Enable load following
    steam_quality_compensation: bool = True         # Enable steam quality compensation
    predictive_maintenance: bool = True             # Enable predictive maintenance
    
    # === SUBSYSTEM CONFIGURATIONS ===
    pump_system: FeedwaterPumpSystemConfig = field(default_factory=FeedwaterPumpSystemConfig)
    control_system: ThreeElementControlConfig = field(default_factory=ThreeElementControlConfig)
    water_treatment: FeedwaterWaterTreatmentConfig = field(default_factory=FeedwaterWaterTreatmentConfig)
    performance_monitoring: FeedwaterPerformanceConfig = field(default_factory=FeedwaterPerformanceConfig)
    protection_system: FeedwaterProtectionConfig = field(default_factory=FeedwaterProtectionConfig)
    
    # === INITIAL CONDITIONS ===
    initial_conditions: FeedwaterInitialConditions = field(default_factory=FeedwaterInitialConditions)
    
    # === MAINTENANCE CONFIGURATION ===
    maintenance: FeedwaterMaintenanceConfig = field(default_factory=FeedwaterMaintenanceConfig)
    
    def __post_init__(self):
        """Validate and auto-calculate derived parameters"""
        self._validate_parameters()
        self._calculate_derived_parameters()
    
    def _validate_parameters(self):
        """Validate configuration parameters"""
        errors = []
        
        # Validate basic parameters
        if self.num_steam_generators <= 0:
            errors.append("Number of steam generators must be positive")
        
        if self.design_total_flow <= 0:
            errors.append("Design total flow must be positive")
        
        if self.design_sg_level <= 0:
            errors.append("Design SG level must be positive")
        
        if not (200.0 <= self.design_feedwater_temperature <= 250.0):
            errors.append("Feedwater temperature outside reasonable range (200-250°C)")
        
        if not (5.0 <= self.design_pressure <= 12.0):
            errors.append("Design pressure outside reasonable range (5-12 MPa)")
        
        # Validate pump system
        if self.pump_system.num_pumps <= 0:
            errors.append("Number of pumps must be positive")
        
        if self.pump_system.pumps_normally_running >= self.pump_system.num_pumps:
            errors.append("Number of normally running pumps must be less than total pumps")
        
        # Validate initial conditions arrays
        if len(self.initial_conditions.sg_levels) != self.num_steam_generators:
            errors.append(f"SG levels array length ({len(self.initial_conditions.sg_levels)}) "
                         f"doesn't match number of SGs ({self.num_steam_generators})")
        
        if len(self.initial_conditions.pump_speeds) != self.pump_system.num_pumps:
            errors.append(f"Pump speeds array length ({len(self.initial_conditions.pump_speeds)}) "
                         f"doesn't match number of pumps ({self.pump_system.num_pumps})")
        
        if len(self.initial_conditions.running_pumps) != self.pump_system.num_pumps:
            errors.append(f"Running pumps array length doesn't match number of pumps")
        
        if errors:
            raise ValueError("Feedwater configuration validation failed:\n" + 
                           "\n".join(f"  - {error}" for error in errors))
    
    def _calculate_derived_parameters(self):
        """Calculate derived parameters from design values"""
        # Calculate per-pump design flow
        if self.pump_system.design_flow_per_pump == 500.0:  # Default value
            self.pump_system.design_flow_per_pump = self.design_total_flow / self.pump_system.pumps_normally_running
        
        # Ensure initial conditions arrays are correct length
        while len(self.initial_conditions.sg_levels) < self.num_steam_generators:
            self.initial_conditions.sg_levels.append(self.design_sg_level)
        
        while len(self.initial_conditions.sg_pressures) < self.num_steam_generators:
            self.initial_conditions.sg_pressures.append(6.9)
        
        while len(self.initial_conditions.sg_steam_flows) < self.num_steam_generators:
            self.initial_conditions.sg_steam_flows.append(self.design_total_flow / self.num_steam_generators)
        
        while len(self.initial_conditions.sg_steam_qualities) < self.num_steam_generators:
            self.initial_conditions.sg_steam_qualities.append(0.99)
        
        # Ensure pump arrays are correct length
        while len(self.initial_conditions.pump_speeds) < self.pump_system.num_pumps:
            self.initial_conditions.pump_speeds.append(0.0)
        
        while len(self.initial_conditions.pump_flows) < self.pump_system.num_pumps:
            self.initial_conditions.pump_flows.append(0.0)
        
        while len(self.initial_conditions.pump_heads) < self.pump_system.num_pumps:
            self.initial_conditions.pump_heads.append(0.0)
        
        while len(self.initial_conditions.pump_efficiencies) < self.pump_system.num_pumps:
            self.initial_conditions.pump_efficiencies.append(0.0)
        
        while len(self.initial_conditions.running_pumps) < self.pump_system.num_pumps:
            self.initial_conditions.running_pumps.append(False)
        
        while len(self.initial_conditions.pump_vibrations) < self.pump_system.num_pumps:
            self.initial_conditions.pump_vibrations.append(0.0)
        
        while len(self.initial_conditions.bearing_temperatures) < self.pump_system.num_pumps:
            self.initial_conditions.bearing_temperatures.append(25.0)
        
        # Set initial conditions for running pumps
        for i in range(self.pump_system.pumps_normally_running):
            if i < len(self.initial_conditions.running_pumps):
                self.initial_conditions.running_pumps[i] = True
                self.initial_conditions.pump_speeds[i] = self.pump_system.pump_speed
                self.initial_conditions.pump_flows[i] = self.pump_system.design_flow_per_pump
                self.initial_conditions.pump_heads[i] = self.pump_system.design_head_per_pump
                self.initial_conditions.pump_efficiencies[i] = self.pump_system.pump_efficiency
                self.initial_conditions.pump_vibrations[i] = 5.0
                # CRITICAL FIX: Only set bearing temperature if it's still at default (25.0°C)
                # This prevents overriding scenario-specific initial conditions
                # TEMPORARILY COMMENTED OUT to preserve scenario initial conditions
                # if self.initial_conditions.bearing_temperatures[i] == 25.0:
                #     self.initial_conditions.bearing_temperatures[i] = 80.0
        
        # Trim arrays if too long
        self.initial_conditions.sg_levels = self.initial_conditions.sg_levels[:self.num_steam_generators]
        self.initial_conditions.sg_pressures = self.initial_conditions.sg_pressures[:self.num_steam_generators]
        self.initial_conditions.sg_steam_flows = self.initial_conditions.sg_steam_flows[:self.num_steam_generators]
        self.initial_conditions.sg_steam_qualities = self.initial_conditions.sg_steam_qualities[:self.num_steam_generators]
        
        self.initial_conditions.pump_speeds = self.initial_conditions.pump_speeds[:self.pump_system.num_pumps]
        self.initial_conditions.pump_flows = self.initial_conditions.pump_flows[:self.pump_system.num_pumps]
        self.initial_conditions.pump_heads = self.initial_conditions.pump_heads[:self.pump_system.num_pumps]
        self.initial_conditions.pump_efficiencies = self.initial_conditions.pump_efficiencies[:self.pump_system.num_pumps]
        self.initial_conditions.running_pumps = self.initial_conditions.running_pumps[:self.pump_system.num_pumps]
        self.initial_conditions.pump_vibrations = self.initial_conditions.pump_vibrations[:self.pump_system.num_pumps]
        self.initial_conditions.bearing_temperatures = self.initial_conditions.bearing_temperatures[:self.pump_system.num_pumps]
        
        # Update control system setpoint
        self.control_system.level_setpoint = self.design_sg_level
        self.initial_conditions.level_setpoint = self.design_sg_level
        
        # Update initial flow demand
        self.initial_conditions.flow_demand = self.design_total_flow
    
    def get_pump_config(self, pump_index: int) -> Dict[str, Any]:
        """
        Get configuration for a specific pump
        
        Args:
            pump_index: Pump index (0-based)
            
        Returns:
            Dictionary with pump-specific configuration
        """
        if not (0 <= pump_index < self.pump_system.num_pumps):
            raise ValueError(f"Pump index {pump_index} out of range (0-{self.pump_system.num_pumps-1})")
        
        return {
            'pump_id': f"FWP-{pump_index}",
            'design_flow': self.pump_system.design_flow_per_pump,
            'design_head': self.pump_system.design_head_per_pump,
            'pump_efficiency': self.pump_system.pump_efficiency,
            'motor_efficiency': self.pump_system.motor_efficiency,
            'pump_speed': self.pump_system.pump_speed,
            'impeller_diameter': self.pump_system.impeller_diameter,
            'initial_speed': self.initial_conditions.pump_speeds[pump_index],
            'initial_flow': self.initial_conditions.pump_flows[pump_index],
            'initial_head': self.initial_conditions.pump_heads[pump_index],
            'initial_efficiency': self.initial_conditions.pump_efficiencies[pump_index],
            'initially_running': self.initial_conditions.running_pumps[pump_index],
            'initial_vibration': self.initial_conditions.pump_vibrations[pump_index],
            'initial_bearing_temperature': self.initial_conditions.bearing_temperatures[pump_index],
            'initial_seal_leakage': self.initial_conditions.seal_leakages[pump_index],
            'initial_oil_level': self.initial_conditions.pump_oil_levels[pump_index],
            'variable_speed_control': self.pump_system.variable_speed_control,
            'minimum_speed_fraction': self.pump_system.minimum_speed_fraction,
            'maximum_speed_fraction': self.pump_system.maximum_speed_fraction
        }
    
    def get_sg_config(self, sg_index: int) -> Dict[str, Any]:
        """
        Get configuration for a specific steam generator
        
        Args:
            sg_index: Steam generator index (0-based)
            
        Returns:
            Dictionary with SG-specific configuration
        """
        if not (0 <= sg_index < self.num_steam_generators):
            raise ValueError(f"SG index {sg_index} out of range (0-{self.num_steam_generators-1})")
        
        return {
            'sg_id': f"SG-{sg_index}",
            'design_level': self.design_sg_level,
            'design_feedwater_flow': self.design_total_flow / self.num_steam_generators,
            'initial_level': self.initial_conditions.sg_levels[sg_index],
            'initial_pressure': self.initial_conditions.sg_pressures[sg_index],
            'initial_steam_flow': self.initial_conditions.sg_steam_flows[sg_index],
            'initial_steam_quality': self.initial_conditions.sg_steam_qualities[sg_index],
            'level_setpoint': self.control_system.level_setpoint,
            'level_deadband': self.control_system.level_deadband
        }
    
    def get_maintenance_config(self) -> Dict[str, Any]:
        """Get maintenance configuration for the feedwater system"""
        return {
            'pump_performance': {
                'pump_efficiency_threshold': self.maintenance.pump_efficiency_threshold,
                'system_efficiency_threshold': self.maintenance.system_efficiency_threshold,
                'performance_factor_threshold': self.maintenance.performance_factor_threshold,
                'pump_maintenance_action': self.maintenance.pump_maintenance_action,
                'pump_maintenance_interval_hours': self.maintenance.pump_maintenance_interval_hours,
                'pump_maintenance_cooldown_hours': self.maintenance.pump_maintenance_cooldown_hours
            },
            'mechanical_monitoring': {
                'vibration_threshold': self.maintenance.vibration_threshold,
                'bearing_temperature_threshold': self.maintenance.bearing_temperature_threshold,
                'seal_leakage_threshold': self.maintenance.seal_leakage_threshold,
                'impeller_wear_threshold': self.maintenance.impeller_wear_threshold,
                'vibration_analysis_action': self.maintenance.vibration_analysis_action,
                'vibration_analysis_interval_hours': self.maintenance.vibration_analysis_interval_hours,
                'vibration_analysis_cooldown_hours': self.maintenance.vibration_analysis_cooldown_hours
            },
            'water_quality': {
                'ph_deviation_threshold': self.maintenance.ph_deviation_threshold,
                'dissolved_oxygen_threshold': self.maintenance.dissolved_oxygen_threshold,
                'iron_concentration_threshold': self.maintenance.iron_concentration_threshold,
                'conductivity_threshold': self.maintenance.conductivity_threshold,
                'water_treatment_action': self.maintenance.water_treatment_action,
                'water_treatment_interval_hours': self.maintenance.water_treatment_interval_hours,
                'water_treatment_cooldown_hours': self.maintenance.water_treatment_cooldown_hours
            },
            'cavitation_monitoring': {
                'cavitation_index_threshold': self.maintenance.cavitation_index_threshold,
                'npsh_margin_threshold': self.maintenance.npsh_margin_threshold,
                'suction_pressure_threshold': self.maintenance.suction_pressure_threshold
            },
            'maintenance_actions': {
                'oil_change_action': self.maintenance.oil_change_action,
                'oil_top_off_action': self.maintenance.oil_top_off_action,
                'impeller_inspection_action': self.maintenance.impeller_inspection_action,
                'bearing_replacement_action': self.maintenance.bearing_replacement_action,
                'seal_replacement_action': self.maintenance.seal_replacement_action,
                'component_overhaul_action': self.maintenance.component_overhaul_action,
                'control_calibration_action': self.maintenance.control_calibration_action,
                'system_cleaning_action': self.maintenance.system_cleaning_action
            },
            'maintenance_intervals': {
                'oil_change_interval_hours': self.maintenance.oil_change_interval_hours,
                'oil_top_off_interval_hours': self.maintenance.oil_top_off_interval_hours,
                'impeller_inspection_interval_hours': self.maintenance.impeller_inspection_interval_hours,
                'bearing_replacement_interval_hours': self.maintenance.bearing_replacement_interval_hours,
                'seal_replacement_interval_hours': self.maintenance.seal_replacement_interval_hours,
                'component_overhaul_interval_hours': self.maintenance.component_overhaul_interval_hours,
                'control_calibration_interval_hours': self.maintenance.control_calibration_interval_hours,
                'system_cleaning_interval_hours': self.maintenance.system_cleaning_interval_hours
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the feedwater configuration"""
        return {
            'system_info': {
                'system_id': self.system_id,
                'num_steam_generators': self.num_steam_generators,
                'design_total_flow_kgs': self.design_total_flow,
                'design_sg_level_m': self.design_sg_level,
                'design_feedwater_temperature_c': self.design_feedwater_temperature,
                'design_pressure_mpa': self.design_pressure,
                'design_efficiency': self.design_efficiency
            },
            'pump_system': {
                'num_pumps': self.pump_system.num_pumps,
                'pumps_normally_running': self.pump_system.pumps_normally_running,
                'design_flow_per_pump_kgs': self.pump_system.design_flow_per_pump,
                'design_head_per_pump_m': self.pump_system.design_head_per_pump,
                'pump_efficiency': self.pump_system.pump_efficiency,
                'motor_efficiency': self.pump_system.motor_efficiency,
                'variable_speed_control': self.pump_system.variable_speed_control
            },
            'control_system': {
                'three_element_control': self.control_system.enable_three_element_control,
                'level_setpoint_m': self.control_system.level_setpoint,
                'level_deadband_m': self.control_system.level_deadband,
                'steam_quality_compensation': self.control_system.enable_steam_quality_compensation,
                'steam_flow_weight': self.control_system.steam_flow_weight,
                'level_control_weight': self.control_system.level_control_weight
            },
            'initial_conditions': {
                'total_flow_rate_kgs': self.initial_conditions.total_flow_rate,
                'total_power_consumption_mw': self.initial_conditions.total_power_consumption,
                'system_efficiency': self.initial_conditions.system_efficiency,
                'avg_sg_level_m': sum(self.initial_conditions.sg_levels) / len(self.initial_conditions.sg_levels),
                'num_running_pumps': sum(self.initial_conditions.running_pumps),
                'avg_pump_speed_rpm': sum(speed for speed, running in zip(self.initial_conditions.pump_speeds, self.initial_conditions.running_pumps) if running) / max(1, sum(self.initial_conditions.running_pumps)),
                'feedwater_temperature_c': self.initial_conditions.feedwater_temperature,
                'suction_pressure_mpa': self.initial_conditions.suction_pressure,
                'discharge_pressure_mpa': self.initial_conditions.discharge_pressure,
                'control_mode': self.initial_conditions.control_mode
            },
            'water_treatment': {
                'chemical_treatment_enabled': self.water_treatment.enable_chemical_treatment,
                'target_ph': self.water_treatment.target_ph,
                'target_dissolved_oxygen_mgl': self.water_treatment.target_dissolved_oxygen,
                'treatment_efficiency': self.water_treatment.treatment_efficiency
            },
            'protection_system': {
                'low_suction_pressure_trip_mpa': self.protection_system.low_suction_pressure_trip,
                'high_discharge_pressure_trip_mpa': self.protection_system.high_discharge_pressure_trip,
                'high_vibration_trip_mms': self.protection_system.high_vibration_trip,
                'high_bearing_temp_trip_c': self.protection_system.high_bearing_temperature_trip,
                'pump_runback_enabled': self.protection_system.enable_pump_runback,
                'backup_pump_start_enabled': self.protection_system.enable_backup_pump_start
            },
            'maintenance': {
                'pump_efficiency_threshold': self.maintenance.pump_efficiency_threshold,
                'system_efficiency_threshold': self.maintenance.system_efficiency_threshold,
                'vibration_threshold_mms': self.maintenance.vibration_threshold,
                'bearing_temperature_threshold_c': self.maintenance.bearing_temperature_threshold,
                'pump_maintenance_interval_hours': self.maintenance.pump_maintenance_interval_hours,
                'oil_change_interval_hours': self.maintenance.oil_change_interval_hours
            }
        }


# Factory functions for creating common configurations
def create_standard_feedwater_config() -> FeedwaterConfig:
    """Create standard PWR feedwater configuration"""
    return FeedwaterConfig(
        system_id="FW-STD-001",
        num_steam_generators=3,
        design_total_flow=1500.0,
        design_sg_level=12.5,
        design_feedwater_temperature=227.0,
        design_pressure=8.0
    )


def create_uprated_feedwater_config() -> FeedwaterConfig:
    """Create uprated PWR feedwater configuration"""
    return FeedwaterConfig(
        system_id="FW-UP-001",
        num_steam_generators=3,
        design_total_flow=1665.0,        # Higher flow
        design_sg_level=12.5,
        design_feedwater_temperature=227.0,
        design_pressure=8.5,             # Higher pressure
        maximum_flow_fraction=1.25       # Higher maximum flow
    )


def create_four_loop_feedwater_config() -> FeedwaterConfig:
    """Create 4-loop PWR feedwater configuration"""
    config = FeedwaterConfig(
        system_id="FW-4L-001",
        num_steam_generators=4,
        design_total_flow=1500.0,
        design_sg_level=12.5,
        design_feedwater_temperature=227.0,
        design_pressure=8.0
    )
    
    # Extend initial conditions for 4th SG
    config.initial_conditions.sg_levels.append(12.5)
    config.initial_conditions.sg_pressures.append(6.9)
    config.initial_conditions.sg_steam_flows.append(375.0)  # 1500/4
    config.initial_conditions.sg_steam_qualities.append(0.99)
    
    return config


# Example usage and testing
if __name__ == "__main__":
    print("Feedwater Configuration System")
    print("=" * 50)
    
    # Test standard configuration
    config = create_standard_feedwater_config()
    summary = config.get_summary()
    
    print("Standard Configuration:")
    print(f"  System ID: {summary['system_info']['system_id']}")
    print(f"  Number of SGs: {summary['system_info']['num_steam_generators']}")
    print(f"  Design Total Flow: {summary['system_info']['design_total_flow_kgs']:.0f} kg/s")
    print(f"  Design SG Level: {summary['system_info']['design_sg_level_m']:.1f} m")
    print(f"  Design Feedwater Temperature: {summary['system_info']['design_feedwater_temperature_c']:.1f} °C")
    print(f"  Design Pressure: {summary['system_info']['design_pressure_mpa']:.1f} MPa")
    print(f"  Design Efficiency: {summary['system_info']['design_efficiency']:.1%}")
    print()
    
    print("Pump System:")
    print(f"  Number of Pumps: {summary['pump_system']['num_pumps']}")
    print(f"  Pumps Normally Running: {summary['pump_system']['pumps_normally_running']}")
    print(f"  Design Flow per Pump: {summary['pump_system']['design_flow_per_pump_kgs']:.0f} kg/s")
    print(f"  Design Head per Pump: {summary['pump_system']['design_head_per_pump_m']:.0f} m")
    print(f"  Pump Efficiency: {summary['pump_system']['pump_efficiency']:.1%}")
    print(f"  Motor Efficiency: {summary['pump_system']['motor_efficiency']:.1%}")
    print(f"  Variable Speed Control: {summary['pump_system']['variable_speed_control']}")
    print()
    
    print("Control System:")
    print(f"  Three-Element Control: {summary['control_system']['three_element_control']}")
    print(f"  Level Setpoint: {summary['control_system']['level_setpoint_m']:.1f} m")
    print(f"  Level Deadband: {summary['control_system']['level_deadband_m']:.1f} m")
    print(f"  Steam Quality Compensation: {summary['control_system']['steam_quality_compensation']}")
    print(f"  Steam Flow Weight: {summary['control_system']['steam_flow_weight']:.1f}")
    print(f"  Level Control Weight: {summary['control_system']['level_control_weight']:.1f}")
    print()
    
    print("Initial Conditions:")
    print(f"  Total Flow Rate: {summary['initial_conditions']['total_flow_rate_kgs']:.0f} kg/s")
    print(f"  Total Power Consumption: {summary['initial_conditions']['total_power_consumption_mw']:.1f} MW")
    print(f"  System Efficiency: {summary['initial_conditions']['system_efficiency']:.1%}")
    print(f"  Average SG Level: {summary['initial_conditions']['avg_sg_level_m']:.1f} m")
    print(f"  Number of Running Pumps: {summary['initial_conditions']['num_running_pumps']}")
    print(f"  Average Pump Speed: {summary['initial_conditions']['avg_pump_speed_rpm']:.0f} RPM")
    print(f"  Feedwater Temperature: {summary['initial_conditions']['feedwater_temperature_c']:.1f} °C")
    print(f"  Suction Pressure: {summary['initial_conditions']['suction_pressure_mpa']:.1f} MPa")
    print(f"  Discharge Pressure: {summary['initial_conditions']['discharge_pressure_mpa']:.1f} MPa")
    print(f"  Control Mode: {summary['initial_conditions']['control_mode']}")
    print()
    
    # Test individual pump configuration
    pump0_config = config.get_pump_config(0)
    print("Pump-0 Configuration:")
    print(f"  Pump ID: {pump0_config['pump_id']}")
    print(f"  Design Flow: {pump0_config['design_flow']:.0f} kg/s")
    print(f"  Design Head: {pump0_config['design_head']:.0f} m")
    print(f"  Pump Efficiency: {pump0_config['pump_efficiency']:.1%}")
    print(f"  Initially Running: {pump0_config['initially_running']}")
    print(f"  Initial Speed: {pump0_config['initial_speed']:.0f} RPM")
    print(f"  Initial Vibration: {pump0_config['initial_vibration']:.1f} mm/s")
    print(f"  Initial Bearing Temperature: {pump0_config['initial_bearing_temperature']:.1f} °C")
    print()
    
    # Test SG configuration
    sg0_config = config.get_sg_config(0)
    print("SG-0 Configuration:")
    print(f"  SG ID: {sg0_config['sg_id']}")
    print(f"  Design Level: {sg0_config['design_level']:.1f} m")
    print(f"  Design Feedwater Flow: {sg0_config['design_feedwater_flow']:.0f} kg/s")
    print(f"  Initial Level: {sg0_config['initial_level']:.1f} m")
    print(f"  Initial Steam Flow: {sg0_config['initial_steam_flow']:.0f} kg/s")
    print(f"  Level Setpoint: {sg0_config['level_setpoint']:.1f} m")
    print(f"  Level Deadband: {sg0_config['level_deadband']:.1f} m")
    print()
    
    # Test maintenance configuration
    maint_config = config.get_maintenance_config()
    print("Maintenance Configuration:")
    print(f"  Pump Efficiency Threshold: {maint_config['pump_performance']['pump_efficiency_threshold']:.1%}")
    print(f"  System Efficiency Threshold: {maint_config['pump_performance']['system_efficiency_threshold']:.1%}")
    print(f"  Vibration Threshold: {maint_config['mechanical_monitoring']['vibration_threshold']:.1f} mm/s")
    print(f"  Bearing Temperature Threshold: {maint_config['mechanical_monitoring']['bearing_temperature_threshold']:.0f} °C")
    print(f"  pH Deviation Threshold: {maint_config['water_quality']['ph_deviation_threshold']:.1f}")
    print(f"  Pump Maintenance Interval: {maint_config['pump_performance']['pump_maintenance_interval_hours']:.0f} hours")
    print()
    
    # Test file operations if available
    if DATACLASS_WIZARD_AVAILABLE:
        print("Testing YAML serialization...")
        try:
            # Save to YAML
            config.to_yaml_file("test_feedwater_config.yaml")
            
            # Load from YAML
            loaded_config = FeedwaterConfig.from_yaml_file("test_feedwater_config.yaml")
            
            print("  YAML serialization: SUCCESS")
            print(f"  Loaded config system ID: {loaded_config.system_id}")
            
            # Clean up
            import os
            os.remove("test_feedwater_config.yaml")
            
        except Exception as e:
            print(f"  YAML serialization failed: {e}")
    else:
        print("Install dataclass-wizard for YAML serialization: pip install dataclass-wizard")
    
    print("Feedwater configuration system ready!")
