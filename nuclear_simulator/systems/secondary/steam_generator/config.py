"""
Steam Generator Configuration System

This module provides comprehensive configuration for steam generator subsystems,
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
class TSPFoulingConfig:
    """
    Configuration for TSP (Tube Support Plate) fouling model
    
    MIGRATED: Complete TSP fouling configuration from tsp_fouling_model.py
    """
    
    # Identification
    fouling_model_id: str = "TSP-FOULING-001"      # Unique identifier for this TSP fouling instance
    
    # Enable/disable fouling simulation
    enable_fouling: bool = True
    
    # MIGRATED: Physical TSP parameters from tsp_fouling_model.py
    tsp_count: int = 7                              # Number of TSP elevations (typical PWR)
    tsp_hole_diameter: float = 0.023                # m (23mm typical hole diameter)
    tsp_thickness: float = 0.025                    # m (25mm typical TSP thickness)
    tsp_open_area_fraction: float = 0.06            # 6% open area (typical PWR design)
    
    # Initial fouling conditions
    initial_fouling_thickness: float = 0.0          # mm initial fouling thickness
    initial_heat_transfer_degradation: float = 0.0  # Initial degradation factor (0-1)
    
    # MIGRATED: Deposit formation rates from tsp_fouling_model.py (mg/cm²/year)
    magnetite_base_rate: float = 2.5               # Base magnetite deposition rate
    copper_base_rate: float = 0.8                  # Base copper deposition rate  
    silica_base_rate: float = 1.2                  # Base silica deposition rate
    biological_base_rate: float = 0.5              # Base biological fouling rate
    
    # MIGRATED: Water chemistry effects on fouling rates from tsp_fouling_model.py
    iron_concentration_factor: float = 1.5          # Multiplier per ppm Fe
    copper_concentration_factor: float = 2.0        # Multiplier per ppm Cu
    silica_concentration_factor: float = 1.8        # Multiplier per ppm SiO2
    ph_optimal: float = 9.2                        # Optimal pH for minimal fouling
    temperature_activation_energy: float = 45000.0  # J/mol (Arrhenius activation energy)
    
    # MIGRATED: Flow and heat transfer impact parameters from tsp_fouling_model.py
    flow_restriction_exponent: float = 2.0          # Flow restriction vs. fouling relationship
    heat_transfer_degradation_factor: float = 0.6   # HTC reduction factor
    mixing_degradation_exponent: float = 1.5        # Mixing reduction vs. fouling
    
    # MIGRATED: Cleaning effectiveness parameters from tsp_fouling_model.py
    chemical_cleaning_effectiveness: float = 0.75    # 75% deposit removal
    mechanical_cleaning_effectiveness: float = 0.85  # 85% deposit removal
    
    # MIGRATED: Lifecycle and replacement parameters from tsp_fouling_model.py
    design_life_years: float = 40.0                 # Design life (years)
    fouling_replacement_threshold: float = 0.80     # 80% fouling triggers replacement consideration
    
    # MIGRATED: Shutdown protection thresholds from tsp_fouling_model.py
    fouling_trip_threshold: float = 0.85            # 85% fouling triggers automatic trip
    heat_transfer_trip_threshold: float = 0.60      # 60% HTC triggers trip
    pressure_drop_trip_threshold: float = 5.0       # 5x normal ΔP triggers trip
    flow_maldistribution_limit: float = 0.30        # 30% flow imbalance limit
    
    # Legacy fouling rate parameters (for backward compatibility)
    base_fouling_rate: float = 0.001                # mm/1000hrs base fouling rate
    temperature_coefficient: float = 0.1            # Temperature effect on fouling
    chemistry_coefficient: float = 0.05             # Chemistry effect on fouling
    flow_coefficient: float = 0.02                  # Flow effect on fouling
    
    # Fouling limits and thresholds
    max_fouling_thickness: float = 5.0              # mm maximum fouling thickness
    cleaning_threshold: float = 2.0                 # mm fouling thickness for cleaning
    performance_degradation_threshold: float = 0.1  # Performance degradation threshold
    
    # Per-SG fouling rate factors (allows individual SG variation)
    fouling_rate_factors: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])


@dataclass_json
@dataclass
class SteamGeneratorInitialConditions:
    """
    Initial conditions for steam generator system
    
    CLEANED VERSION - Only parameters that map to actual physics model state variables.
    This dataclass now perfectly matches the cleaned YAML template initial_conditions section.
    """
    
    # Basic SG operational parameters (map to SteamGenerator class state)
    sg_levels: List[float] = field(default_factory=lambda: [12.5, 12.5, 12.5])                    # → water_level
    sg_pressures: List[float] = field(default_factory=lambda: [6.9, 6.9, 6.9])                    # → secondary_pressure
    sg_temperatures: List[float] = field(default_factory=lambda: [285.8, 285.8, 285.8])           # → secondary_temperature
    sg_steam_qualities: List[float] = field(default_factory=lambda: [0.99, 0.99, 0.99])           # → steam_quality
    sg_steam_flows: List[float] = field(default_factory=lambda: [500.0, 500.0, 500.0])            # → steam_flow_rate
    sg_feedwater_flows: List[float] = field(default_factory=lambda: [500.0, 500.0, 500.0])        # → feedwater_flow_rate
    primary_inlet_temps: List[float] = field(default_factory=lambda: [327.0, 327.0, 327.0])       # → primary_inlet_temp
    primary_outlet_temps: List[float] = field(default_factory=lambda: [293.0, 293.0, 293.0])      # → primary_outlet_temp
    primary_flow_rates: List[float] = field(default_factory=lambda: [5700.0, 5700.0, 5700.0])     # → primary flow parameter
    
    # TSP fouling parameters (map to TSPFoulingModel class state)
    tsp_fouling_thicknesses: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])         # → deposits.get_total_thickness() → heat_transfer_degradation (calculated)
    
    # Tube interior scale parameters (map to TubeInteriorFouling class state)
    scale_thicknesses: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])               # → scale_thickness → scale_thermal_resistance (calculated)
    
    # Heat transfer parameters (map to SteamGenerator class state)
    tube_wall_temperature: List[float] = field(default_factory=lambda: [300.0, 300.0, 300.0])     # → tube_wall_temp


@dataclass_json
@dataclass
class SteamGeneratorMaintenanceConfig:
    """Maintenance configuration for steam generator system"""
    
    # Tube wall temperature monitoring
    tube_wall_temperature_threshold: float = 280.0  # °C threshold for scale removal
    tube_wall_temperature_action: str = "scale_removal"
    tube_wall_temperature_priority: str = "HIGH"
    tube_wall_temperature_cooldown_hours: float = 24.0
    
    # Steam quality monitoring
    steam_quality_threshold: float = 0.98           # Steam quality threshold
    steam_quality_action: str = "moisture_separator_maintenance"
    steam_quality_priority: str = "MEDIUM"
    steam_quality_cooldown_hours: float = 48.0
    
    # TSP fouling monitoring
    tsp_fouling_threshold: float = 2.0              # mm fouling thickness threshold
    tsp_fouling_action: str = "tsp_chemical_cleaning"
    tsp_fouling_priority: str = "HIGH"
    tsp_fouling_cooldown_hours: float = 168.0       # Weekly
    
    # Heat transfer degradation monitoring
    heat_transfer_degradation_threshold: float = 0.05  # 5% degradation threshold
    heat_transfer_degradation_action: str = "heat_transfer_optimization"
    heat_transfer_degradation_priority: str = "MEDIUM"
    heat_transfer_degradation_cooldown_hours: float = 72.0
    
    # System-level monitoring
    system_availability_threshold: float = 0.95     # 95% availability threshold
    system_coordination_action: str = "system_coordination_maintenance"
    system_coordination_cooldown_hours: float = 24.0
    
    # Check intervals
    individual_sg_check_interval_hours: float = 0.25  # 15 minutes
    system_check_interval_hours: float = 1.0          # 1 hour


@dataclass_json
@dataclass
class SteamGeneratorConfig(YAMLWizard, JSONWizard, TOMLWizard):
    """
    Comprehensive Steam Generator Configuration
    
    This configuration class contains all parameters needed to initialize
    and operate the steam generator system, including initial conditions,
    operational parameters, and maintenance settings.
    
    Migrated from old system to include all missing parameters for complete compatibility.
    """
    
    # === SYSTEM IDENTIFICATION ===
    system_id: str = "SGS-001"                       # Steam generator system identifier
    
    # === DESIGN PARAMETERS ===
    num_steam_generators: int = 3                   # Number of steam generators
    design_total_thermal_power: float = 3000.0e6    # W total design thermal power
    design_total_steam_flow: float = 1665.0         # kg/s total design steam flow (FIXED: Correct for 3000 MW PWR)
    design_steam_pressure: float = 6.9              # MPa design steam pressure
    design_steam_temperature: float = 285.8         # °C design steam temperature
    design_feedwater_temperature: float = 227.0     # °C design feedwater temperature
    
    # Individual SG design parameters
    design_thermal_power_per_sg: float = 1000.0e6   # W thermal power per SG
    design_steam_flow_per_sg: float = 500.0         # kg/s steam flow per SG
    design_feedwater_flow_per_sg: float = 500.0     # kg/s feedwater flow per SG
    primary_design_flow: float = 5700.0             # kg/s primary flow per SG
    secondary_design_flow: float = 500.0            # kg/s secondary flow per SG (alias for steam flow)
    
    # === PHYSICAL PARAMETERS ===
    # Heat transfer parameters
    design_overall_htc: float = 3000.0              # W/m²/K overall heat transfer coefficient
    heat_transfer_area_per_sg: float = 5000.0       # m² heat transfer area per SG
    tube_count_per_sg: int = 3388                    # Number of tubes per SG
    tube_inner_diameter: float = 0.0191             # m tube inner diameter
    tube_wall_thickness: float = 0.00109            # m tube wall thickness
    
    # MIGRATED: Missing physical design parameters from old system
    tube_outer_diameter: float = 0.0222             # m tube outer diameter (from old config)
    tube_length: float = 19.8                       # m effective heat transfer length (from old config)
    secondary_water_mass: float = 68000.0           # kg total water inventory per SG (from old config)
    steam_dome_volume: float = 28.0                 # m³ steam space volume (from old config)
    
    # MIGRATED: Heat transfer coefficients from old system
    primary_htc: float = 28000.0                    # W/m²/K primary side heat transfer coefficient (from old config)
    secondary_htc: float = 18000.0                  # W/m²/K secondary side heat transfer coefficient (from old config)
    
    # MIGRATED: Design pressures from old system
    design_pressure_primary: float = 15.51          # MPa design pressure primary side (from old config)
    design_pressure_secondary: float = 6.895        # MPa design pressure secondary side (from old config)
    
    # Material properties
    tube_material_conductivity: float = 385.0       # W/m/K (copper)
    tube_material_density: float = 8960.0           # kg/m³ (copper)
    tube_material_specific_heat: float = 385.0      # J/kg/K (copper)
    
    # === OPERATIONAL PARAMETERS ===
    # Operating envelope
    minimum_power_fraction: float = 0.1             # Minimum power as fraction of design
    maximum_power_fraction: float = 1.05            # Maximum power as fraction of design
    minimum_steam_quality: float = 0.95             # Minimum acceptable steam quality
    maximum_tube_wall_temperature: float = 350.0    # °C maximum tube wall temperature
    
    # Control parameters
    level_control_enabled: bool = True               # Enable automatic level control
    pressure_control_enabled: bool = True           # Enable automatic pressure control
    load_following_enabled: bool = True             # Enable load following capability
    
    # MIGRATED: Control gains from old system
    feedwater_control_gain: float = 0.08            # Proportional gain for level control (from old config)
    steam_pressure_control_gain: float = 0.05       # Proportional gain for pressure control (from old config)
    
    # === SYSTEM COORDINATION PARAMETERS ===
    # MIGRATED: System coordination parameters from enhanced physics
    auto_load_balancing: bool = True                 # Enable automatic load balancing (from enhanced config)
    system_coordination: bool = True                 # Enable system-level coordination (from enhanced config)
    performance_optimization: bool = True           # Enable performance optimization (from enhanced config)
    predictive_maintenance: bool = True             # Enable predictive maintenance (from enhanced config)
    auto_pressure_control: bool = True              # Enable automatic pressure control (from enhanced config)
    system_optimization: bool = True                # Enable system optimization (from enhanced config)
    
    # === INITIAL CONDITIONS ===
    initial_conditions: SteamGeneratorInitialConditions = field(
        default_factory=SteamGeneratorInitialConditions
    )
    
    # === TSP FOULING CONFIGURATION ===
    tsp_fouling: TSPFoulingConfig = field(default_factory=TSPFoulingConfig)
    
    # === MAINTENANCE CONFIGURATION ===
    maintenance: SteamGeneratorMaintenanceConfig = field(
        default_factory=SteamGeneratorMaintenanceConfig
    )
    
    # === PERFORMANCE PARAMETERS ===
    design_efficiency: float = 0.98                 # Overall design efficiency
    thermal_performance_factor: float = 1.0         # Initial thermal performance factor
    availability_factor: float = 1.0                # Initial availability factor
    
    # === WATER CHEMISTRY INTEGRATION ===
    enable_chemistry_tracking: bool = True          # Enable water chemistry tracking
    chemistry_update_interval_hours: float = 1.0    # Chemistry update interval
    
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
        
        if self.design_total_thermal_power <= 0:
            errors.append("Design thermal power must be positive")
        
        if self.design_total_steam_flow <= 0:
            errors.append("Design steam flow must be positive")
        
        if not (5.0 <= self.design_steam_pressure <= 8.0):
            errors.append("Steam pressure outside typical PWR range (5-8 MPa)")
        
        if not (280.0 <= self.design_steam_temperature <= 290.0):
            errors.append("Steam temperature outside typical PWR range (280-290°C)")
        
        # Validate initial conditions arrays
        if len(self.initial_conditions.sg_levels) != self.num_steam_generators:
            errors.append(f"SG levels array length ({len(self.initial_conditions.sg_levels)}) "
                         f"doesn't match number of SGs ({self.num_steam_generators})")
        
        if len(self.initial_conditions.sg_pressures) != self.num_steam_generators:
            errors.append(f"SG pressures array length doesn't match number of SGs")
        
        if len(self.initial_conditions.sg_temperatures) != self.num_steam_generators:
            errors.append(f"SG temperatures array length doesn't match number of SGs")
        
        # Validate TSP fouling factors
        if len(self.tsp_fouling.fouling_rate_factors) != self.num_steam_generators:
            errors.append(f"TSP fouling rate factors array length doesn't match number of SGs")
        
        if errors:
            raise ValueError("Steam Generator configuration validation failed:\n" + 
                           "\n".join(f"  - {error}" for error in errors))
    
    def _calculate_derived_parameters(self):
        """Calculate derived parameters from design values"""
        # Calculate per-SG parameters if not explicitly set
        if self.design_thermal_power_per_sg == 1000.0e6:  # Default value
            self.design_thermal_power_per_sg = self.design_total_thermal_power / self.num_steam_generators
        
        if self.design_steam_flow_per_sg == 500.0:  # Default value
            self.design_steam_flow_per_sg = self.design_total_steam_flow / self.num_steam_generators
        
        if self.design_feedwater_flow_per_sg == 500.0:  # Default value
            self.design_feedwater_flow_per_sg = self.design_total_steam_flow / self.num_steam_generators
        
        # Ensure initial conditions arrays are correct length
        while len(self.initial_conditions.sg_levels) < self.num_steam_generators:
            self.initial_conditions.sg_levels.append(12.5)
        
        while len(self.initial_conditions.sg_pressures) < self.num_steam_generators:
            self.initial_conditions.sg_pressures.append(self.design_steam_pressure)
        
        while len(self.initial_conditions.sg_temperatures) < self.num_steam_generators:
            self.initial_conditions.sg_temperatures.append(self.design_steam_temperature)
        
        while len(self.initial_conditions.sg_steam_qualities) < self.num_steam_generators:
            self.initial_conditions.sg_steam_qualities.append(0.99)
        
        while len(self.initial_conditions.sg_steam_flows) < self.num_steam_generators:
            self.initial_conditions.sg_steam_flows.append(self.design_steam_flow_per_sg)
        
        while len(self.initial_conditions.sg_feedwater_flows) < self.num_steam_generators:
            self.initial_conditions.sg_feedwater_flows.append(self.design_feedwater_flow_per_sg)
        
        while len(self.initial_conditions.primary_inlet_temps) < self.num_steam_generators:
            self.initial_conditions.primary_inlet_temps.append(327.0)
        
        while len(self.initial_conditions.primary_outlet_temps) < self.num_steam_generators:
            self.initial_conditions.primary_outlet_temps.append(293.0)
        
        while len(self.initial_conditions.primary_flow_rates) < self.num_steam_generators:
            self.initial_conditions.primary_flow_rates.append(5700.0)
        
        while len(self.initial_conditions.tsp_fouling_thicknesses) < self.num_steam_generators:
            self.initial_conditions.tsp_fouling_thicknesses.append(self.tsp_fouling.initial_fouling_thickness)
        
        while len(self.initial_conditions.scale_thicknesses) < self.num_steam_generators:
            self.initial_conditions.scale_thicknesses.append(0.0)
        
        while len(self.initial_conditions.tube_wall_temperature) < self.num_steam_generators:
            self.initial_conditions.tube_wall_temperature.append(300.0)
        
        # Ensure TSP fouling rate factors array is correct length
        while len(self.tsp_fouling.fouling_rate_factors) < self.num_steam_generators:
            self.tsp_fouling.fouling_rate_factors.append(1.0)
        
        # Trim arrays if too long
        self.initial_conditions.sg_levels = self.initial_conditions.sg_levels[:self.num_steam_generators]
        self.initial_conditions.sg_pressures = self.initial_conditions.sg_pressures[:self.num_steam_generators]
        self.initial_conditions.sg_temperatures = self.initial_conditions.sg_temperatures[:self.num_steam_generators]
        self.initial_conditions.sg_steam_qualities = self.initial_conditions.sg_steam_qualities[:self.num_steam_generators]
        self.initial_conditions.sg_steam_flows = self.initial_conditions.sg_steam_flows[:self.num_steam_generators]
        self.initial_conditions.sg_feedwater_flows = self.initial_conditions.sg_feedwater_flows[:self.num_steam_generators]
        self.initial_conditions.primary_inlet_temps = self.initial_conditions.primary_inlet_temps[:self.num_steam_generators]
        self.initial_conditions.primary_outlet_temps = self.initial_conditions.primary_outlet_temps[:self.num_steam_generators]
        self.initial_conditions.primary_flow_rates = self.initial_conditions.primary_flow_rates[:self.num_steam_generators]
        self.initial_conditions.tsp_fouling_thicknesses = self.initial_conditions.tsp_fouling_thicknesses[:self.num_steam_generators]
        self.initial_conditions.scale_thicknesses = self.initial_conditions.scale_thicknesses[:self.num_steam_generators]
        self.tsp_fouling.fouling_rate_factors = self.tsp_fouling.fouling_rate_factors[:self.num_steam_generators]
    
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
            'design_thermal_power': self.design_thermal_power_per_sg,
            'design_steam_flow': self.design_steam_flow_per_sg,
            'design_feedwater_flow': self.design_feedwater_flow_per_sg,
            'design_steam_pressure': self.design_steam_pressure,
            'design_steam_temperature': self.design_steam_temperature,
            'design_feedwater_temperature': self.design_feedwater_temperature,
            'heat_transfer_area': self.heat_transfer_area_per_sg,
            'tube_count': self.tube_count_per_sg,
            'initial_level': self.initial_conditions.sg_levels[sg_index],
            'initial_pressure': self.initial_conditions.sg_pressures[sg_index],
            'initial_temperature': self.initial_conditions.sg_temperatures[sg_index],
            'initial_steam_quality': self.initial_conditions.sg_steam_qualities[sg_index],
            'initial_steam_flow': self.initial_conditions.sg_steam_flows[sg_index],
            'initial_feedwater_flow': self.initial_conditions.sg_feedwater_flows[sg_index],
            'initial_primary_inlet_temp': self.initial_conditions.primary_inlet_temps[sg_index],
            'initial_primary_outlet_temp': self.initial_conditions.primary_outlet_temps[sg_index],
            'initial_primary_flow': self.initial_conditions.primary_flow_rates[sg_index],
            'initial_tsp_fouling_thickness': self.initial_conditions.tsp_fouling_thicknesses[sg_index],
            'tsp_fouling_rate_factor': self.tsp_fouling.fouling_rate_factors[sg_index]
        }
    
    def get_maintenance_config(self) -> Dict[str, Any]:
        """Get maintenance configuration for the steam generator system"""
        return {
            'tube_wall_temperature': {
                'threshold': self.maintenance.tube_wall_temperature_threshold,
                'action': self.maintenance.tube_wall_temperature_action,
                'priority': self.maintenance.tube_wall_temperature_priority,
                'cooldown_hours': self.maintenance.tube_wall_temperature_cooldown_hours
            },
            'steam_quality': {
                'threshold': self.maintenance.steam_quality_threshold,
                'action': self.maintenance.steam_quality_action,
                'priority': self.maintenance.steam_quality_priority,
                'cooldown_hours': self.maintenance.steam_quality_cooldown_hours
            },
            'tsp_fouling': {
                'threshold': self.maintenance.tsp_fouling_threshold,
                'action': self.maintenance.tsp_fouling_action,
                'priority': self.maintenance.tsp_fouling_priority,
                'cooldown_hours': self.maintenance.tsp_fouling_cooldown_hours
            },
            'heat_transfer_degradation': {
                'threshold': self.maintenance.heat_transfer_degradation_threshold,
                'action': self.maintenance.heat_transfer_degradation_action,
                'priority': self.maintenance.heat_transfer_degradation_priority,
                'cooldown_hours': self.maintenance.heat_transfer_degradation_cooldown_hours
            },
            'system_availability': {
                'threshold': self.maintenance.system_availability_threshold,
                'action': self.maintenance.system_coordination_action,
                'cooldown_hours': self.maintenance.system_coordination_cooldown_hours
            },
            'check_intervals': {
                'individual_sg_hours': self.maintenance.individual_sg_check_interval_hours,
                'system_hours': self.maintenance.system_check_interval_hours
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the steam generator configuration"""
        return {
            'system_info': {
                'system_id': self.system_id,
                'num_steam_generators': self.num_steam_generators,
                'design_total_thermal_power_mw': self.design_total_thermal_power / 1e6,
                'design_total_steam_flow_kgs': self.design_total_steam_flow,
                'design_steam_pressure_mpa': self.design_steam_pressure,
                'design_steam_temperature_c': self.design_steam_temperature
            },
            'per_sg_design': {
                'thermal_power_mw': self.design_thermal_power_per_sg / 1e6,
                'steam_flow_kgs': self.design_steam_flow_per_sg,
                'feedwater_flow_kgs': self.design_feedwater_flow_per_sg,
                'heat_transfer_area_m2': self.heat_transfer_area_per_sg,
                'tube_count': self.tube_count_per_sg
            },
            'initial_conditions': {
                'avg_sg_level_m': sum(self.initial_conditions.sg_levels) / len(self.initial_conditions.sg_levels),
                'avg_sg_pressure_mpa': sum(self.initial_conditions.sg_pressures) / len(self.initial_conditions.sg_pressures),
                'avg_sg_temperature_c': sum(self.initial_conditions.sg_temperatures) / len(self.initial_conditions.sg_temperatures),
                'avg_steam_quality': sum(self.initial_conditions.sg_steam_qualities) / len(self.initial_conditions.sg_steam_qualities),
                'total_steam_flow_kgs': sum(self.initial_conditions.sg_steam_flows),
                'total_feedwater_flow_kgs': sum(self.initial_conditions.sg_feedwater_flows)
            },
            'tsp_fouling': {
                'enabled': self.tsp_fouling.enable_fouling,
                'initial_thickness_mm': self.tsp_fouling.initial_fouling_thickness,
                'base_rate_mm_per_1000hrs': self.tsp_fouling.base_fouling_rate,
                'cleaning_threshold_mm': self.tsp_fouling.cleaning_threshold
            },
            'maintenance': {
                'tube_wall_temp_threshold_c': self.maintenance.tube_wall_temperature_threshold,
                'steam_quality_threshold': self.maintenance.steam_quality_threshold,
                'tsp_fouling_threshold_mm': self.maintenance.tsp_fouling_threshold,
                'individual_check_interval_hours': self.maintenance.individual_sg_check_interval_hours
            }
        }


# Factory functions for creating common configurations
def create_standard_sg_config() -> SteamGeneratorConfig:
    """Create standard 3-loop PWR steam generator configuration"""
    return SteamGeneratorConfig(
        system_id="SG-STD-001",
        num_steam_generators=3,
        design_total_thermal_power=3000.0e6,
        design_total_steam_flow=1500.0,
        design_steam_pressure=6.9,
        design_steam_temperature=285.8
    )


def create_uprated_sg_config() -> SteamGeneratorConfig:
    """Create uprated PWR steam generator configuration"""
    return SteamGeneratorConfig(
        system_id="SG-UP-001",
        num_steam_generators=3,
        design_total_thermal_power=3255.0e6,  # Uprated power
        design_total_steam_flow=1665.0,       # Higher steam flow
        design_steam_pressure=6.9,
        design_steam_temperature=285.8,
        maximum_power_fraction=1.08           # Higher maximum power
    )


def create_four_loop_sg_config() -> SteamGeneratorConfig:
    """Create 4-loop PWR steam generator configuration"""
    config = SteamGeneratorConfig(
        system_id="SG-4L-001",
        num_steam_generators=4,
        design_total_thermal_power=3000.0e6,
        design_total_steam_flow=1500.0,
        design_steam_pressure=6.9,
        design_steam_temperature=285.8
    )
    
    # Extend initial conditions for 4th SG
    config.initial_conditions.sg_levels.append(12.5)
    config.initial_conditions.sg_pressures.append(6.9)
    config.initial_conditions.sg_temperatures.append(285.8)
    config.initial_conditions.sg_steam_qualities.append(0.99)
    config.initial_conditions.sg_steam_flows.append(375.0)  # 1500/4
    config.initial_conditions.sg_feedwater_flows.append(375.0)
    config.initial_conditions.primary_inlet_temps.append(327.0)
    config.initial_conditions.primary_outlet_temps.append(293.0)
    config.initial_conditions.primary_flow_rates.append(5700.0)
    config.initial_conditions.tsp_fouling_thicknesses.append(0.0)
    config.tsp_fouling.fouling_rate_factors.append(1.0)
    
    return config


# Example usage and testing
if __name__ == "__main__":
    print("Steam Generator Configuration System")
    print("=" * 50)
    
    # Test standard configuration
    config = create_standard_sg_config()
    summary = config.get_summary()
    
    print("Standard Configuration:")
    print(f"  System ID: {summary['system_info']['system_id']}")
    print(f"  Number of SGs: {summary['system_info']['num_steam_generators']}")
    print(f"  Total Thermal Power: {summary['system_info']['design_total_thermal_power_mw']:.0f} MW")
    print(f"  Total Steam Flow: {summary['system_info']['design_total_steam_flow_kgs']:.0f} kg/s")
    print(f"  Steam Pressure: {summary['system_info']['design_steam_pressure_mpa']:.1f} MPa")
    print(f"  Steam Temperature: {summary['system_info']['design_steam_temperature_c']:.1f} °C")
    print()
    
    print("Per-SG Design:")
    print(f"  Thermal Power: {summary['per_sg_design']['thermal_power_mw']:.0f} MW")
    print(f"  Steam Flow: {summary['per_sg_design']['steam_flow_kgs']:.0f} kg/s")
    print(f"  Heat Transfer Area: {summary['per_sg_design']['heat_transfer_area_m2']:.0f} m²")
    print(f"  Tube Count: {summary['per_sg_design']['tube_count']}")
    print()
    
    print("Initial Conditions:")
    print(f"  Average SG Level: {summary['initial_conditions']['avg_sg_level_m']:.1f} m")
    print(f"  Average SG Pressure: {summary['initial_conditions']['avg_sg_pressure_mpa']:.1f} MPa")
    print(f"  Average Steam Quality: {summary['initial_conditions']['avg_steam_quality']:.3f}")
    print(f"  Total Steam Flow: {summary['initial_conditions']['total_steam_flow_kgs']:.0f} kg/s")
    print()
    
    # Test individual SG configuration
    sg0_config = config.get_sg_config(0)
    print("SG-0 Configuration:")
    print(f"  SG ID: {sg0_config['sg_id']}")
    print(f"  Design Power: {sg0_config['design_thermal_power']/1e6:.0f} MW")
    print(f"  Initial Level: {sg0_config['initial_level']:.1f} m")
    print(f"  Initial Steam Flow: {sg0_config['initial_steam_flow']:.0f} kg/s")
    print(f"  TSP Fouling Rate Factor: {sg0_config['tsp_fouling_rate_factor']:.1f}")
    print()
    
    # Test maintenance configuration
    maint_config = config.get_maintenance_config()
    print("Maintenance Configuration:")
    print(f"  Tube Wall Temp Threshold: {maint_config['tube_wall_temperature']['threshold']:.0f} °C")
    print(f"  Steam Quality Threshold: {maint_config['steam_quality']['threshold']:.3f}")
    print(f"  TSP Fouling Threshold: {maint_config['tsp_fouling']['threshold']:.1f} mm")
    print(f"  Individual SG Check Interval: {maint_config['check_intervals']['individual_sg_hours']:.2f} hours")
    print()
    
    # Test file operations if available
    if DATACLASS_WIZARD_AVAILABLE:
        print("Testing YAML serialization...")
        try:
            # Save to YAML
            config.to_yaml_file("test_sg_config.yaml")
            
            # Load from YAML
            loaded_config = SteamGeneratorConfig.from_yaml_file("test_sg_config.yaml")
            
            print("  YAML serialization: SUCCESS")
            print(f"  Loaded config system ID: {loaded_config.system_id}")
            
            # Clean up
            import os
            os.remove("test_sg_config.yaml")
            
        except Exception as e:
            print(f"  YAML serialization failed: {e}")
    else:
        print("Install dataclass-wizard for YAML serialization: pip install dataclass-wizard")
    
    print("Steam Generator configuration system ready!")
