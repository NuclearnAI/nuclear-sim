"""
Condenser Configuration System

This module provides comprehensive configuration for condenser subsystems,
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
class CondenserHeatTransferConfig:
    """Configuration for condenser heat transfer system"""
    
    # Heat transfer design parameters
    design_heat_duty: float = 2000.0e6              # W design heat duty
    heat_transfer_area: float = 75000.0             # m² heat transfer area
    tube_count: int = 84000                         # Number of tubes
    tube_inner_diameter: float = 0.0254             # m tube inner diameter (1 inch)
    tube_wall_thickness: float = 0.00159            # m tube wall thickness
    tube_length: float = 12.0                       # m tube length
    
    # Heat transfer coefficients
    steam_side_htc: float = 12000.0                 # W/m²/K steam side heat transfer coefficient
    water_side_htc: float = 5000.0                  # W/m²/K water side heat transfer coefficient
    tube_wall_conductivity: float = 385.0           # W/m/K tube wall conductivity (copper)
    
    # Material properties
    tube_material: str = "copper"                   # Tube material
    tube_material_density: float = 8960.0           # kg/m³ tube material density
    tube_material_specific_heat: float = 385.0      # J/kg/K tube material specific heat
    
    # Performance parameters
    design_overall_htc: float = 3000.0              # W/m²/K design overall heat transfer coefficient
    design_lmtd: float = 10.0                       # °C design log mean temperature difference
    fouling_resistance_design: float = 0.0001       # m²K/W design fouling resistance


@dataclass_json
@dataclass
class CondenserVacuumSystemConfig:
    """Configuration for condenser vacuum system"""
    
    # System configuration
    system_id: str = "VS-001"                       # Vacuum system identifier
    
    # Vacuum system design
    target_pressure: float = 0.007                  # MPa target condenser pressure
    design_air_leakage: float = 0.1                 # kg/s design air leakage
    base_air_leakage: float = 0.05                  # kg/s base air leakage
    
    # Steam ejector configuration
    num_ejectors: int = 2                           # Number of steam ejectors
    ejector_capacity: float = 25.0                  # kg/s steam capacity per ejector
    ejector_efficiency: float = 0.85                # Ejector efficiency
    
    # Ejector design parameters
    motive_steam_pressure: float = 1.2              # MPa motive steam pressure
    motive_steam_temperature: float = 185.0         # °C motive steam temperature
    suction_pressure: float = 0.007                 # MPa suction pressure
    discharge_pressure: float = 0.02                # MPa discharge pressure
    
    # Performance parameters
    air_removal_efficiency: float = 0.95            # Air removal efficiency
    steam_consumption_rate: float = 3.0             # kg steam/kg air removed
    nozzle_efficiency: float = 0.9                  # Nozzle efficiency
    diffuser_efficiency: float = 0.8                # Diffuser efficiency
    
    # Control parameters (from vacuum_system.py)
    auto_start_pressure: float = 0.008              # MPa pressure to auto-start backup ejector
    auto_stop_pressure: float = 0.006               # MPa pressure to auto-stop backup ejector
    rotation_interval: float = 168.0                # hours between ejector rotation (weekly)
    control_strategy: str = "lead_lag"              # "lead_lag", "parallel", "sequential"
    
    # Air leakage parameters
    leakage_degradation_rate: float = 0.00001       # Increase in leakage per hour
    
    # System performance
    condenser_volume: float = 500.0                 # m³ condenser steam space volume
    air_holdup_time: float = 60.0                   # seconds average air residence time
    
    # Motive steam supply
    motive_steam_header_pressure: float = 1.2       # MPa motive steam header pressure
    steam_pressure_drop: float = 0.1                # MPa pressure drop to ejectors
    
    # Alarm and trip settings
    high_pressure_alarm: float = 0.010              # MPa high condenser pressure alarm
    high_pressure_trip: float = 0.012               # MPa high pressure trip (turbine trip)
    low_motive_pressure_alarm: float = 0.9          # MPa low motive steam pressure alarm


@dataclass_json
@dataclass
class CondenserTubeDegradationConfig:
    """Configuration for tube degradation modeling"""
    
    # Tube degradation parameters
    initial_tube_count: int = 84000                 # Initial number of tubes
    tube_failure_rate: float = 0.000001             # Tubes/hour base failure rate
    vibration_damage_threshold: float = 3.0         # m/s velocity threshold for damage
    wall_thickness_initial: float = 0.00159         # m initial wall thickness
    wall_thickness_minimum: float = 0.001           # m minimum allowable thickness
    corrosion_rate: float = 0.0000001               # m/hour wall thinning rate
    leak_detection_threshold: float = 0.01          # kg/s leak rate for detection
    
    # Degradation factors
    chemistry_degradation_factor: float = 1.0       # Chemistry effect on degradation
    temperature_degradation_factor: float = 1.0     # Temperature effect on degradation
    flow_degradation_factor: float = 1.0            # Flow effect on degradation
    
    # Maintenance parameters
    plugging_threshold: float = 0.005               # kg/s leak rate for plugging
    inspection_interval_hours: float = 8760.0       # Annual inspection
    replacement_threshold: float = 0.8              # Wall thickness fraction for replacement


@dataclass_json
@dataclass
class CondenserFoulingConfig:
    """Configuration for condenser fouling modeling"""
    
    # Biofouling parameters
    biofouling_base_rate: float = 0.001             # mm/1000hrs base growth rate
    biofouling_temp_coefficient: float = 0.1        # Temperature effect coefficient
    biofouling_nutrient_factor: float = 1.0         # Nutrient availability factor
    biofouling_chlorine_kill_rate: float = 2.0      # Chlorine kill rate factor
    
    # Scale formation parameters
    scale_base_rate: float = 0.0005                 # mm/1000hrs base formation rate
    scale_hardness_coefficient: float = 0.002       # Water hardness effect
    scale_temp_coefficient: float = 0.15            # Temperature effect
    scale_ph_optimum: float = 7.5                   # Optimal pH for minimum scaling
    
    # Corrosion product parameters
    corrosion_base_rate: float = 0.0002             # mm/1000hrs base rate
    corrosion_oxygen_coefficient: float = 0.01      # Dissolved oxygen effect
    corrosion_ph_optimum: float = 7.5               # Optimal pH for minimum corrosion
    corrosion_velocity_factor: float = 0.5          # Velocity effect on corrosion
    
    # Fouling limits and cleaning
    max_fouling_thickness: float = 5.0              # mm maximum fouling thickness
    cleaning_threshold: float = 2.0                 # mm fouling thickness for cleaning
    cleaning_effectiveness: Dict[str, float] = field(default_factory=lambda: {
        "chemical": 0.8,
        "mechanical": 0.6,
        "hydroblast": 0.9
    })


@dataclass_json
@dataclass
class SteamEjectorConfig:
    """Configuration parameters for steam jet ejectors"""
    
    # Basic ejector parameters
    ejector_id: str = "SJE-001"                     # Unique ejector identifier
    ejector_type: str = "two_stage"                 # "single_stage", "two_stage", "three_stage"
    design_capacity: float = 25.0                   # kg/s air at design conditions
    design_suction_pressure: float = 0.007          # MPa design suction pressure
    design_compression_ratio: float = 14.3          # Discharge/suction pressure ratio
    
    # Motive steam parameters
    motive_steam_pressure: float = 1.0              # MPa motive steam pressure
    motive_steam_temperature: float = 180.0         # °C motive steam temperature
    design_steam_consumption: float = 2.5           # kg steam / kg air removed
    
    # Performance characteristics
    base_steam_consumption: float = 2.5             # kg steam / kg air at design
    steam_consumption_exponent: float = 0.8         # Exponent for capacity scaling
    pressure_effect_coefficient: float = 1.5        # Effect of suction pressure on steam consumption
    
    # Operating limits
    min_suction_pressure: float = 0.003             # MPa minimum operating pressure
    max_suction_pressure: float = 0.015             # MPa maximum operating pressure
    min_motive_pressure: float = 0.8                # MPa minimum motive steam pressure
    max_capacity_factor: float = 1.2                # Maximum capacity vs design
    
    # Inter-stage condenser (for multi-stage ejectors)
    has_intercondenser: bool = True                 # Inter-stage condenser present
    intercondenser_pressure: float = 0.02           # MPa inter-stage pressure
    intercondenser_cooling_water: float = 50.0      # kg/s cooling water flow
    
    # After-condenser
    has_aftercondenser: bool = True                 # After-condenser present
    aftercondenser_cooling_water: float = 25.0      # kg/s cooling water flow
    
    # Degradation and fouling
    nozzle_fouling_rate: float = 0.00001            # Fouling rate per hour
    diffuser_fouling_rate: float = 0.00002          # Diffuser fouling rate per hour
    erosion_rate: float = 0.000001                  # Nozzle erosion rate per hour


@dataclass_json
@dataclass
class CondenserCoolingWaterConfig:
    """Configuration for cooling water system"""
    
    # Cooling water design
    design_flow_rate: float = 45000.0               # kg/s design cooling water flow
    design_inlet_temperature: float = 25.0          # °C design inlet temperature
    design_outlet_temperature: float = 35.0         # °C design outlet temperature
    design_temperature_rise: float = 10.0           # °C design temperature rise
    
    # Water quality parameters
    design_ph: float = 7.5                          # Design pH
    design_hardness: float = 150.0                  # mg/L design hardness as CaCO3
    design_chloride: float = 50.0                   # mg/L design chloride
    design_dissolved_oxygen: float = 8.0            # mg/L design dissolved oxygen
    design_tds: float = 500.0                       # mg/L design total dissolved solids
    
    # Chemical treatment
    chlorine_dose: float = 1.0                      # mg/L chlorine dose
    antiscalant_dose: float = 5.0                   # mg/L antiscalant dose
    corrosion_inhibitor_dose: float = 10.0          # mg/L corrosion inhibitor dose
    biocide_dose: float = 0.5                       # mg/L biocide dose
    
    # Water system parameters
    circulation_pumps: int = 3                      # Number of circulation pumps
    pump_capacity: float = 15000.0                  # kg/s capacity per pump
    pump_efficiency: float = 0.85                   # Pump efficiency
    pump_head: float = 30.0                         # m pump head
    
    # Cooling tower parameters (if applicable)
    cooling_tower_efficiency: float = 0.8           # Cooling tower efficiency
    approach_temperature: float = 5.0               # °C approach temperature
    wet_bulb_temperature: float = 20.0              # °C design wet bulb temperature


@dataclass_json
@dataclass
class CondenserInitialConditions:
    """Initial conditions for condenser system"""
    
    # Steam conditions
    steam_inlet_pressure: float = 0.007             # MPa steam inlet pressure
    steam_inlet_temperature: float = 39.0           # °C steam inlet temperature
    steam_inlet_flow: float = 1500.0                # kg/s steam inlet flow
    steam_inlet_quality: float = 0.90               # Steam quality at inlet
    
    # Condensate conditions
    condensate_temperature: float = 39.0            # °C condensate temperature
    condensate_flow: float = 1500.0                 # kg/s condensate flow
    condensate_subcooling: float = 0.0              # °C condensate subcooling
    
    # Cooling water conditions
    cooling_water_inlet_temp: float = 25.0          # °C cooling water inlet temperature
    cooling_water_outlet_temp: float = 35.0         # °C cooling water outlet temperature
    cooling_water_flow: float = 45000.0             # kg/s cooling water flow
    cooling_water_velocity: float = 2.0             # m/s cooling water velocity
    
    # Heat transfer conditions
    heat_rejection_rate: float = 2000.0e6           # W heat rejection rate
    overall_htc: float = 3000.0                     # W/m²/K overall heat transfer coefficient
    lmtd: float = 10.0                              # °C log mean temperature difference
    thermal_performance_factor: float = 1.0         # Thermal performance factor
    
    # Vacuum system conditions
    condenser_pressure: float = 0.007               # MPa condenser pressure
    air_partial_pressure: float = 0.0005            # MPa air partial pressure
    air_removal_rate: float = 0.1                   # kg/s air removal rate
    vacuum_steam_consumption: float = 0.3           # kg/s vacuum steam consumption
    
    # Tube conditions
    active_tube_count: int = 84000                  # Active tube count
    plugged_tube_count: int = 0                     # Plugged tube count
    average_wall_thickness: float = 0.00159         # m average wall thickness
    tube_leak_rate: float = 0.0                     # kg/s tube leak rate
    
    # Fouling conditions
    biofouling_thickness: float = 0.0               # mm biofouling thickness
    scale_thickness: float = 0.0                    # mm scale thickness
    corrosion_thickness: float = 0.0                # mm corrosion product thickness
    total_fouling_resistance: float = 0.0           # m²K/W total fouling resistance
    time_since_cleaning: float = 0.0                # hours since last cleaning
    
    # Water quality conditions
    water_ph: float = 7.5                           # Water pH
    water_hardness: float = 150.0                   # mg/L water hardness
    chlorine_residual: float = 1.0                  # mg/L chlorine residual
    dissolved_oxygen: float = 8.0                   # mg/L dissolved oxygen
    water_temperature: float = 30.0                 # °C average water temperature
    
    # Operating conditions
    operating_hours: float = 0.0                    # Total operating hours
    system_availability: bool = True                # System availability status


@dataclass_json
@dataclass
class CondenserMaintenanceConfig:
    """Maintenance configuration for condenser system"""
    
    # Performance monitoring
    thermal_performance_threshold: float = 0.85     # 85% thermal performance threshold
    heat_transfer_degradation_threshold: float = 0.1  # 10% heat transfer degradation
    fouling_resistance_threshold: float = 0.001     # m²K/W fouling resistance threshold
    
    # Tube monitoring
    tube_leak_rate_threshold: float = 0.01          # kg/s tube leak rate threshold
    active_tube_count_threshold: int = 75600        # 90% of initial tube count
    wall_thickness_threshold: float = 0.0012        # m wall thickness threshold (75% of initial)
    
    # Fouling monitoring
    biofouling_thickness_threshold: float = 1.0     # mm biofouling thickness threshold
    scale_thickness_threshold: float = 1.5          # mm scale thickness threshold
    total_fouling_thickness_threshold: float = 2.0  # mm total fouling thickness threshold
    time_since_cleaning_threshold: float = 4320.0   # hours (6 months) since cleaning
    
    # Vacuum system monitoring
    condenser_pressure_threshold: float = 0.008     # MPa condenser pressure threshold
    air_leakage_threshold: float = 0.15             # kg/s air leakage threshold
    vacuum_efficiency_threshold: float = 0.8        # Vacuum system efficiency threshold
    
    # Water quality monitoring
    ph_deviation_threshold: float = 0.5             # pH deviation from target
    hardness_threshold: float = 200.0               # mg/L hardness threshold
    chlorine_residual_threshold: float = 0.5        # mg/L minimum chlorine residual
    dissolved_oxygen_threshold: float = 12.0        # mg/L maximum dissolved oxygen
    
    # Maintenance actions
    tube_cleaning_action: str = "condenser_tube_cleaning"
    chemical_cleaning_action: str = "condenser_chemical_cleaning"
    tube_plugging_action: str = "condenser_tube_plugging"
    tube_inspection_action: str = "condenser_tube_inspection"
    hydroblast_cleaning_action: str = "condenser_hydroblast_cleaning"
    water_treatment_action: str = "condenser_water_treatment"
    vacuum_system_test_action: str = "vacuum_system_test"
    vacuum_leak_detection_action: str = "vacuum_leak_detection"
    ejector_cleaning_action: str = "vacuum_ejector_cleaning"
    ejector_nozzle_replacement_action: str = "vacuum_ejector_nozzle_replacement"
    
    # Maintenance intervals
    tube_cleaning_interval_hours: float = 4320.0    # Semi-annual tube cleaning
    chemical_cleaning_interval_hours: float = 8760.0  # Annual chemical cleaning
    tube_inspection_interval_hours: float = 8760.0  # Annual tube inspection
    hydroblast_cleaning_interval_hours: float = 4320.0  # Semi-annual hydroblast
    water_treatment_interval_hours: float = 720.0   # Monthly water treatment
    vacuum_system_test_interval_hours: float = 2190.0  # Quarterly vacuum test
    vacuum_leak_detection_interval_hours: float = 4320.0  # Semi-annual leak detection
    ejector_cleaning_interval_hours: float = 4320.0  # Semi-annual ejector cleaning
    ejector_nozzle_replacement_interval_hours: float = 17520.0  # Biennial nozzle replacement
    
    # Cooldown periods
    tube_cleaning_cooldown_hours: float = 168.0     # Weekly cooldown
    chemical_cleaning_cooldown_hours: float = 8760.0  # Annual cooldown
    tube_plugging_cooldown_hours: float = 24.0      # Daily cooldown
    tube_inspection_cooldown_hours: float = 8760.0  # Annual cooldown
    hydroblast_cleaning_cooldown_hours: float = 4320.0  # Semi-annual cooldown
    water_treatment_cooldown_hours: float = 720.0   # Monthly cooldown
    vacuum_system_test_cooldown_hours: float = 2190.0  # Quarterly cooldown
    vacuum_leak_detection_cooldown_hours: float = 4320.0  # Semi-annual cooldown
    ejector_cleaning_cooldown_hours: float = 4320.0  # Semi-annual cooldown
    ejector_nozzle_replacement_cooldown_hours: float = 17520.0  # Biennial cooldown


@dataclass_json
@dataclass
class CondenserConfig(YAMLWizard, JSONWizard, TOMLWizard):
    """
    Comprehensive Condenser Configuration
    
    This configuration class contains all parameters needed to initialize
    and operate the condenser system, including initial conditions,
    operational parameters, and maintenance settings.
    """
    
    # === SYSTEM IDENTIFICATION ===
    system_id: str = "COND-001"                     # Condenser system identifier
    
    # === DESIGN PARAMETERS ===
    design_heat_duty: float = 2000.0e6              # W design heat duty
    design_steam_flow: float = 1500.0               # kg/s design steam flow
    design_cooling_water_flow: float = 45000.0      # kg/s design cooling water flow
    design_condenser_pressure: float = 0.007        # MPa design condenser pressure
    design_cooling_water_temp_rise: float = 10.0    # °C design cooling water temperature rise
    
    # === PERFORMANCE PARAMETERS ===
    design_thermal_efficiency: float = 0.95         # Design thermal efficiency
    minimum_load_fraction: float = 0.2              # Minimum load as fraction of design
    maximum_load_fraction: float = 1.1              # Maximum load as fraction of design
    
    # === OPERATIONAL PARAMETERS ===
    auto_vacuum_control: bool = True                # Enable automatic vacuum control
    fouling_monitoring_enabled: bool = True         # Enable fouling monitoring
    tube_leak_monitoring_enabled: bool = True       # Enable tube leak monitoring
    predictive_maintenance: bool = True             # Enable predictive maintenance
    
    # === SUBSYSTEM CONFIGURATIONS ===
    heat_transfer: CondenserHeatTransferConfig = field(default_factory=CondenserHeatTransferConfig)
    vacuum_system: CondenserVacuumSystemConfig = field(default_factory=CondenserVacuumSystemConfig)
    tube_degradation: CondenserTubeDegradationConfig = field(default_factory=CondenserTubeDegradationConfig)
    fouling_system: CondenserFoulingConfig = field(default_factory=CondenserFoulingConfig)
    cooling_water: CondenserCoolingWaterConfig = field(default_factory=CondenserCoolingWaterConfig)
    
    # === STEAM EJECTOR CONFIGURATIONS ===
    steam_ejectors: List[SteamEjectorConfig] = field(default_factory=lambda: [
        SteamEjectorConfig(ejector_id="SJE-001", ejector_type="two_stage"),
        SteamEjectorConfig(ejector_id="SJE-002", ejector_type="two_stage")
    ])
    
    # === INITIAL CONDITIONS ===
    initial_conditions: CondenserInitialConditions = field(default_factory=CondenserInitialConditions)
    
    # === MAINTENANCE CONFIGURATION ===
    maintenance: CondenserMaintenanceConfig = field(default_factory=CondenserMaintenanceConfig)
    
    def __post_init__(self):
        """Validate and auto-calculate derived parameters"""
        self._validate_parameters()
        self._calculate_derived_parameters()
    
    def _validate_parameters(self):
        """Validate configuration parameters"""
        errors = []
        
        # Validate basic parameters
        if self.design_heat_duty <= 0:
            errors.append("Design heat duty must be positive")
        
        if self.design_steam_flow <= 0:
            errors.append("Design steam flow must be positive")
        
        if self.design_cooling_water_flow <= 0:
            errors.append("Design cooling water flow must be positive")
        
        if not (0.005 <= self.design_condenser_pressure <= 0.015):
            errors.append("Condenser pressure outside reasonable range (0.005-0.015 MPa)")
        
        if not (5.0 <= self.design_cooling_water_temp_rise <= 15.0):
            errors.append("Cooling water temperature rise outside reasonable range (5-15°C)")
        
        # Validate heat transfer parameters
        if self.heat_transfer.tube_count <= 0:
            errors.append("Tube count must be positive")
        
        if self.heat_transfer.heat_transfer_area <= 0:
            errors.append("Heat transfer area must be positive")
        
        # Validate vacuum system
        if self.vacuum_system.num_ejectors <= 0:
            errors.append("Number of ejectors must be positive")
        
        if not (0.005 <= self.vacuum_system.target_pressure <= 0.015):
            errors.append("Target pressure outside reasonable range")
        
        # Validate initial conditions
        if self.initial_conditions.active_tube_count > self.heat_transfer.tube_count:
            errors.append("Active tube count cannot exceed total tube count")
        
        if errors:
            raise ValueError("Condenser configuration validation failed:\n" + 
                           "\n".join(f"  - {error}" for error in errors))
    
    def _calculate_derived_parameters(self):
        """Calculate derived parameters from design values"""
        # Update initial conditions to match design parameters
        if self.initial_conditions.steam_inlet_flow == 1500.0:  # Default value
            self.initial_conditions.steam_inlet_flow = self.design_steam_flow
        
        if self.initial_conditions.cooling_water_flow == 45000.0:  # Default value
            self.initial_conditions.cooling_water_flow = self.design_cooling_water_flow
        
        if self.initial_conditions.heat_rejection_rate == 2000.0e6:  # Default value
            self.initial_conditions.heat_rejection_rate = self.design_heat_duty
        
        if self.initial_conditions.condenser_pressure == 0.007:  # Default value
            self.initial_conditions.condenser_pressure = self.design_condenser_pressure
        
        # Update tube degradation initial count
        if self.tube_degradation.initial_tube_count != self.heat_transfer.tube_count:
            self.tube_degradation.initial_tube_count = self.heat_transfer.tube_count
        
        if self.initial_conditions.active_tube_count == 84000:  # Default value
            self.initial_conditions.active_tube_count = self.heat_transfer.tube_count
        
        # Calculate cooling water outlet temperature
        cp_water = 4180.0  # J/kg/K
        temp_rise = self.design_heat_duty / (self.design_cooling_water_flow * cp_water)
        self.initial_conditions.cooling_water_outlet_temp = (
            self.initial_conditions.cooling_water_inlet_temp + temp_rise
        )
        
        # Update vacuum system target pressure
        self.vacuum_system.target_pressure = self.design_condenser_pressure
        
        # Update maintenance thresholds based on design parameters
        self.maintenance.active_tube_count_threshold = int(self.heat_transfer.tube_count * 0.9)  # 90% threshold
    
    def get_heat_transfer_config(self) -> Dict[str, Any]:
        """Get heat transfer system configuration"""
        return {
            'design_heat_duty_mw': self.heat_transfer.design_heat_duty / 1e6,
            'heat_transfer_area_m2': self.heat_transfer.heat_transfer_area,
            'tube_count': self.heat_transfer.tube_count,
            'tube_inner_diameter_m': self.heat_transfer.tube_inner_diameter,
            'tube_wall_thickness_m': self.heat_transfer.tube_wall_thickness,
            'tube_length_m': self.heat_transfer.tube_length,
            'steam_side_htc': self.heat_transfer.steam_side_htc,
            'water_side_htc': self.heat_transfer.water_side_htc,
            'tube_wall_conductivity': self.heat_transfer.tube_wall_conductivity,
            'tube_material': self.heat_transfer.tube_material,
            'design_overall_htc': self.heat_transfer.design_overall_htc,
            'design_lmtd_c': self.heat_transfer.design_lmtd,
            'fouling_resistance_design': self.heat_transfer.fouling_resistance_design
        }
    
    def get_vacuum_system_config(self) -> Dict[str, Any]:
        """Get vacuum system configuration"""
        return {
            'target_pressure_mpa': self.vacuum_system.target_pressure,
            'design_air_leakage_kgs': self.vacuum_system.design_air_leakage,
            'base_air_leakage_kgs': self.vacuum_system.base_air_leakage,
            'num_ejectors': self.vacuum_system.num_ejectors,
            'ejector_capacity_kgs': self.vacuum_system.ejector_capacity,
            'ejector_efficiency': self.vacuum_system.ejector_efficiency,
            'motive_steam_pressure_mpa': self.vacuum_system.motive_steam_pressure,
            'motive_steam_temperature_c': self.vacuum_system.motive_steam_temperature,
            'air_removal_efficiency': self.vacuum_system.air_removal_efficiency,
            'steam_consumption_rate': self.vacuum_system.steam_consumption_rate,
            'nozzle_efficiency': self.vacuum_system.nozzle_efficiency,
            'diffuser_efficiency': self.vacuum_system.diffuser_efficiency
        }
    
    def get_cooling_water_config(self) -> Dict[str, Any]:
        """Get cooling water system configuration"""
        return {
            'design_flow_rate_kgs': self.cooling_water.design_flow_rate,
            'design_inlet_temperature_c': self.cooling_water.design_inlet_temperature,
            'design_outlet_temperature_c': self.cooling_water.design_outlet_temperature,
            'design_temperature_rise_c': self.cooling_water.design_temperature_rise,
            'design_ph': self.cooling_water.design_ph,
            'design_hardness_mgl': self.cooling_water.design_hardness,
            'design_chloride_mgl': self.cooling_water.design_chloride,
            'design_dissolved_oxygen_mgl': self.cooling_water.design_dissolved_oxygen,
            'design_tds_mgl': self.cooling_water.design_tds,
            'chlorine_dose_mgl': self.cooling_water.chlorine_dose,
            'antiscalant_dose_mgl': self.cooling_water.antiscalant_dose,
            'corrosion_inhibitor_dose_mgl': self.cooling_water.corrosion_inhibitor_dose,
            'biocide_dose_mgl': self.cooling_water.biocide_dose,
            'circulation_pumps': self.cooling_water.circulation_pumps,
            'pump_capacity_kgs': self.cooling_water.pump_capacity,
            'pump_efficiency': self.cooling_water.pump_efficiency,
            'pump_head_m': self.cooling_water.pump_head
        }
    
    def get_maintenance_config(self) -> Dict[str, Any]:
        """Get maintenance configuration for the condenser system"""
        return {
            'performance_monitoring': {
                'thermal_performance_threshold': self.maintenance.thermal_performance_threshold,
                'heat_transfer_degradation_threshold': self.maintenance.heat_transfer_degradation_threshold,
                'fouling_resistance_threshold': self.maintenance.fouling_resistance_threshold,
                'tube_cleaning_action': self.maintenance.tube_cleaning_action,
                'tube_cleaning_interval_hours': self.maintenance.tube_cleaning_interval_hours,
                'tube_cleaning_cooldown_hours': self.maintenance.tube_cleaning_cooldown_hours
            },
            'tube_monitoring': {
                'tube_leak_rate_threshold': self.maintenance.tube_leak_rate_threshold,
                'active_tube_count_threshold': self.maintenance.active_tube_count_threshold,
                'wall_thickness_threshold': self.maintenance.wall_thickness_threshold,
                'tube_plugging_action': self.maintenance.tube_plugging_action,
                'tube_inspection_action': self.maintenance.tube_inspection_action,
                'tube_inspection_interval_hours': self.maintenance.tube_inspection_interval_hours,
                'tube_plugging_cooldown_hours': self.maintenance.tube_plugging_cooldown_hours
            },
            'fouling_monitoring': {
                'biofouling_thickness_threshold': self.maintenance.biofouling_thickness_threshold,
                'scale_thickness_threshold': self.maintenance.scale_thickness_threshold,
                'total_fouling_thickness_threshold': self.maintenance.total_fouling_thickness_threshold,
                'time_since_cleaning_threshold': self.maintenance.time_since_cleaning_threshold,
                'chemical_cleaning_action': self.maintenance.chemical_cleaning_action,
                'hydroblast_cleaning_action': self.maintenance.hydroblast_cleaning_action,
                'chemical_cleaning_interval_hours': self.maintenance.chemical_cleaning_interval_hours,
                'hydroblast_cleaning_interval_hours': self.maintenance.hydroblast_cleaning_interval_hours
            },
            'vacuum_system': {
                'condenser_pressure_threshold': self.maintenance.condenser_pressure_threshold,
                'air_leakage_threshold': self.maintenance.air_leakage_threshold,
                'vacuum_efficiency_threshold': self.maintenance.vacuum_efficiency_threshold,
                'vacuum_system_test_action': self.maintenance.vacuum_system_test_action,
                'vacuum_leak_detection_action': self.maintenance.vacuum_leak_detection_action,
                'ejector_cleaning_action': self.maintenance.ejector_cleaning_action,
                'vacuum_system_test_interval_hours': self.maintenance.vacuum_system_test_interval_hours,
                'ejector_cleaning_interval_hours': self.maintenance.ejector_cleaning_interval_hours
            },
            'water_quality': {
                'ph_deviation_threshold': self.maintenance.ph_deviation_threshold,
                'hardness_threshold': self.maintenance.hardness_threshold,
                'chlorine_residual_threshold': self.maintenance.chlorine_residual_threshold,
                'dissolved_oxygen_threshold': self.maintenance.dissolved_oxygen_threshold,
                'water_treatment_action': self.maintenance.water_treatment_action,
                'water_treatment_interval_hours': self.maintenance.water_treatment_interval_hours,
                'water_treatment_cooldown_hours': self.maintenance.water_treatment_cooldown_hours
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the condenser configuration"""
        return {
            'system_info': {
                'system_id': self.system_id,
                'design_heat_duty_mw': self.design_heat_duty / 1e6,
                'design_steam_flow_kgs': self.design_steam_flow,
                'design_cooling_water_flow_kgs': self.design_cooling_water_flow,
                'design_condenser_pressure_mpa': self.design_condenser_pressure,
                'design_thermal_efficiency': self.design_thermal_efficiency
            },
            'heat_transfer': {
                'heat_transfer_area_m2': self.heat_transfer.heat_transfer_area,
                'tube_count': self.heat_transfer.tube_count,
                'tube_inner_diameter_m': self.heat_transfer.tube_inner_diameter,
                'tube_length_m': self.heat_transfer.tube_length,
                'design_overall_htc': self.heat_transfer.design_overall_htc,
                'design_lmtd_c': self.heat_transfer.design_lmtd,
                'tube_material': self.heat_transfer.tube_material
            },
            'vacuum_system': {
                'target_pressure_mpa': self.vacuum_system.target_pressure,
                'num_ejectors': self.vacuum_system.num_ejectors,
                'ejector_capacity_kgs': self.vacuum_system.ejector_capacity,
                'ejector_efficiency': self.vacuum_system.ejector_efficiency,
                'air_removal_efficiency': self.vacuum_system.air_removal_efficiency
            },
            'cooling_water': {
                'design_flow_rate_kgs': self.cooling_water.design_flow_rate,
                'design_inlet_temperature_c': self.cooling_water.design_inlet_temperature,
                'design_outlet_temperature_c': self.cooling_water.design_outlet_temperature,
                'design_temperature_rise_c': self.cooling_water.design_temperature_rise,
                'circulation_pumps': self.cooling_water.circulation_pumps,
                'pump_capacity_kgs': self.cooling_water.pump_capacity
            },
            'initial_conditions': {
                'steam_inlet_flow_kgs': self.initial_conditions.steam_inlet_flow,
                'steam_inlet_pressure_mpa': self.initial_conditions.steam_inlet_pressure,
                'steam_inlet_temperature_c': self.initial_conditions.steam_inlet_temperature,
                'cooling_water_flow_kgs': self.initial_conditions.cooling_water_flow,
                'cooling_water_inlet_temp_c': self.initial_conditions.cooling_water_inlet_temp,
                'cooling_water_outlet_temp_c': self.initial_conditions.cooling_water_outlet_temp,
                'heat_rejection_rate_mw': self.initial_conditions.heat_rejection_rate / 1e6,
                'condenser_pressure_mpa': self.initial_conditions.condenser_pressure,
                'active_tube_count': self.initial_conditions.active_tube_count,
                'plugged_tube_count': self.initial_conditions.plugged_tube_count,
                'thermal_performance_factor': self.initial_conditions.thermal_performance_factor,
                'total_fouling_resistance': self.initial_conditions.total_fouling_resistance,
                'system_availability': self.initial_conditions.system_availability
            },
            'fouling_system': {
                'biofouling_thickness_mm': self.initial_conditions.biofouling_thickness,
                'scale_thickness_mm': self.initial_conditions.scale_thickness,
                'corrosion_thickness_mm': self.initial_conditions.corrosion_thickness,
                'time_since_cleaning_hours': self.initial_conditions.time_since_cleaning,
                'cleaning_threshold_mm': self.fouling_system.cleaning_threshold
            },
            'maintenance': {
                'thermal_performance_threshold': self.maintenance.thermal_performance_threshold,
                'tube_leak_rate_threshold': self.maintenance.tube_leak_rate_threshold,
                'active_tube_count_threshold': self.maintenance.active_tube_count_threshold,
                'fouling_resistance_threshold': self.maintenance.fouling_resistance_threshold,
                'tube_cleaning_interval_hours': self.maintenance.tube_cleaning_interval_hours,
                'chemical_cleaning_interval_hours': self.maintenance.chemical_cleaning_interval_hours
            }
        }


# Factory functions for creating common configurations
def create_standard_condenser_config() -> CondenserConfig:
    """Create standard PWR condenser configuration"""
    return CondenserConfig(
        system_id="COND-STD-001",
        design_heat_duty=2000.0e6,
        design_steam_flow=1500.0,
        design_cooling_water_flow=45000.0,
        design_condenser_pressure=0.007,
        design_cooling_water_temp_rise=10.0
    )


def create_uprated_condenser_config() -> CondenserConfig:
    """Create uprated PWR condenser configuration"""
    return CondenserConfig(
        system_id="COND-UP-001",
        design_heat_duty=2200.0e6,           # Higher heat duty
        design_steam_flow=1665.0,            # Higher steam flow
        design_cooling_water_flow=49500.0,   # Higher cooling water flow
        design_condenser_pressure=0.007,
        design_cooling_water_temp_rise=10.0,
        maximum_load_fraction=1.15           # Higher maximum load
    )


def create_high_efficiency_condenser_config() -> CondenserConfig:
    """Create high-efficiency PWR condenser configuration"""
    config = CondenserConfig(
        system_id="COND-HE-001",
        design_heat_duty=2000.0e6,
        design_steam_flow=1500.0,
        design_cooling_water_flow=45000.0,
        design_condenser_pressure=0.006,     # Lower pressure for higher efficiency
        design_cooling_water_temp_rise=10.0,
        design_thermal_efficiency=0.97       # Higher efficiency
    )
    
    # Optimize heat transfer parameters
    config.heat_transfer.design_overall_htc = 3200.0  # Higher heat transfer coefficient
    config.heat_transfer.design_lmtd = 9.0            # Lower LMTD for better performance
    
    return config


# Example usage and testing
if __name__ == "__main__":
    print("Condenser Configuration System")
    print("=" * 50)
    
    # Test standard configuration
    config = create_standard_condenser_config()
    summary = config.get_summary()
    
    print("Standard Configuration:")
    print(f"  System ID: {summary['system_info']['system_id']}")
    print(f"  Design Heat Duty: {summary['system_info']['design_heat_duty_mw']:.0f} MW")
    print(f"  Design Steam Flow: {summary['system_info']['design_steam_flow_kgs']:.0f} kg/s")
    print(f"  Design Cooling Water Flow: {summary['system_info']['design_cooling_water_flow_kgs']:.0f} kg/s")
    print(f"  Design Condenser Pressure: {summary['system_info']['design_condenser_pressure_mpa']:.3f} MPa")
    print(f"  Design Thermal Efficiency: {summary['system_info']['design_thermal_efficiency']:.1%}")
    print()
    
    print("Heat Transfer System:")
    print(f"  Heat Transfer Area: {summary['heat_transfer']['heat_transfer_area_m2']:.0f} m²")
    print(f"  Tube Count: {summary['heat_transfer']['tube_count']:,}")
    print(f"  Tube Inner Diameter: {summary['heat_transfer']['tube_inner_diameter_m']:.4f} m")
    print(f"  Tube Length: {summary['heat_transfer']['tube_length_m']:.1f} m")
    print(f"  Design Overall HTC: {summary['heat_transfer']['design_overall_htc']:.0f} W/m²/K")
    print(f"  Design LMTD: {summary['heat_transfer']['design_lmtd_c']:.1f} °C")
    print(f"  Tube Material: {summary['heat_transfer']['tube_material']}")
    print()
    
    print("Vacuum System:")
    print(f"  Target Pressure: {summary['vacuum_system']['target_pressure_mpa']:.3f} MPa")
    print(f"  Number of Ejectors: {summary['vacuum_system']['num_ejectors']}")
    print(f"  Ejector Capacity: {summary['vacuum_system']['ejector_capacity_kgs']:.0f} kg/s")
    print(f"  Ejector Efficiency: {summary['vacuum_system']['ejector_efficiency']:.1%}")
    print(f"  Air Removal Efficiency: {summary['vacuum_system']['air_removal_efficiency']:.1%}")
    print()
    
    print("Cooling Water System:")
    print(f"  Design Flow Rate: {summary['cooling_water']['design_flow_rate_kgs']:.0f} kg/s")
    print(f"  Design Inlet Temperature: {summary['cooling_water']['design_inlet_temperature_c']:.1f} °C")
    print(f"  Design Outlet Temperature: {summary['cooling_water']['design_outlet_temperature_c']:.1f} °C")
    print(f"  Design Temperature Rise: {summary['cooling_water']['design_temperature_rise_c']:.1f} °C")
    print(f"  Circulation Pumps: {summary['cooling_water']['circulation_pumps']}")
    print(f"  Pump Capacity: {summary['cooling_water']['pump_capacity_kgs']:.0f} kg/s")
    print()
    
    print("Initial Conditions:")
    print(f"  Steam Inlet Flow: {summary['initial_conditions']['steam_inlet_flow_kgs']:.0f} kg/s")
    print(f"  Steam Inlet Pressure: {summary['initial_conditions']['steam_inlet_pressure_mpa']:.3f} MPa")
    print(f"  Steam Inlet Temperature: {summary['initial_conditions']['steam_inlet_temperature_c']:.1f} °C")
    print(f"  Cooling Water Flow: {summary['initial_conditions']['cooling_water_flow_kgs']:.0f} kg/s")
    print(f"  Heat Rejection Rate: {summary['initial_conditions']['heat_rejection_rate_mw']:.0f} MW")
    print(f"  Condenser Pressure: {summary['initial_conditions']['condenser_pressure_mpa']:.3f} MPa")
    print(f"  Active Tube Count: {summary['initial_conditions']['active_tube_count']:,}")
    print(f"  Thermal Performance Factor: {summary['initial_conditions']['thermal_performance_factor']:.2f}")
    print(f"  System Availability: {summary['initial_conditions']['system_availability']}")
    print()
    
    # Test heat transfer configuration
    ht_config = config.get_heat_transfer_config()
    print("Heat Transfer Configuration:")
    print(f"  Design Heat Duty: {ht_config['design_heat_duty_mw']:.0f} MW")
    print(f"  Heat Transfer Area: {ht_config['heat_transfer_area_m2']:.0f} m²")
    print(f"  Steam Side HTC: {ht_config['steam_side_htc']:.0f} W/m²/K")
    print(f"  Water Side HTC: {ht_config['water_side_htc']:.0f} W/m²/K")
    print(f"  Tube Wall Conductivity: {ht_config['tube_wall_conductivity']:.0f} W/m/K")
    print(f"  Fouling Resistance Design: {ht_config['fouling_resistance_design']:.6f} m²K/W")
    print()
    
    # Test vacuum system configuration
    vac_config = config.get_vacuum_system_config()
    print("Vacuum System Configuration:")
    print(f"  Design Air Leakage: {vac_config['design_air_leakage_kgs']:.2f} kg/s")
    print(f"  Base Air Leakage: {vac_config['base_air_leakage_kgs']:.2f} kg/s")
    print(f"  Motive Steam Pressure: {vac_config['motive_steam_pressure_mpa']:.1f} MPa")
    print(f"  Motive Steam Temperature: {vac_config['motive_steam_temperature_c']:.0f} °C")
    print(f"  Steam Consumption Rate: {vac_config['steam_consumption_rate']:.1f} kg steam/kg air")
    print(f"  Nozzle Efficiency: {vac_config['nozzle_efficiency']:.1%}")
    print(f"  Diffuser Efficiency: {vac_config['diffuser_efficiency']:.1%}")
    print()
    
    # Test maintenance configuration
    maint_config = config.get_maintenance_config()
    print("Maintenance Configuration:")
    print(f"  Thermal Performance Threshold: {maint_config['performance_monitoring']['thermal_performance_threshold']:.1%}")
    print(f"  Tube Leak Rate Threshold: {maint_config['tube_monitoring']['tube_leak_rate_threshold']:.3f} kg/s")
    print(f"  Active Tube Count Threshold: {maint_config['tube_monitoring']['active_tube_count_threshold']:,}")
    print(f"  Fouling Resistance Threshold: {maint_config['performance_monitoring']['fouling_resistance_threshold']:.6f} m²K/W")
    print(f"  Tube Cleaning Interval: {maint_config['performance_monitoring']['tube_cleaning_interval_hours']:.0f} hours")
    print(f"  Chemical Cleaning Interval: {maint_config['fouling_monitoring']['chemical_cleaning_interval_hours']:.0f} hours")
    print()
    
    # Test file operations if available
    if DATACLASS_WIZARD_AVAILABLE:
        print("Testing YAML serialization...")
        try:
            # Save to YAML
            config.to_yaml_file("test_condenser_config.yaml")
            
            # Load from YAML
            loaded_config = CondenserConfig.from_yaml_file("test_condenser_config.yaml")
            
            print("  YAML serialization: SUCCESS")
            print(f"  Loaded config system ID: {loaded_config.system_id}")
            
            # Clean up
            import os
            os.remove("test_condenser_config.yaml")
            
        except Exception as e:
            print(f"  YAML serialization failed: {e}")
    else:
        print("Install dataclass-wizard for YAML serialization: pip install dataclass-wizard")
    
    print("Condenser configuration system ready!")
