"""
Secondary System Configuration

This module provides comprehensive configuration for the entire secondary system,
integrating all subsystem configurations including steam generators, turbine,
feedwater, and condenser systems.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import warnings
import os

# Import subsystem configurations
from .steam_generator.config import SteamGeneratorConfig, create_standard_sg_config
from .turbine.config import TurbineConfig, create_standard_turbine_config
from .feedwater.config import FeedwaterConfig, create_standard_feedwater_config
from .condenser.config import CondenserConfig, create_standard_condenser_config

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
class SecondarySystemIntegrationConfig:
    """Configuration for secondary system integration and coordination"""
    
    # System coordination
    enable_system_coordination: bool = True         # Enable cross-system coordination
    load_following_enabled: bool = True             # Enable load following capability
    automatic_startup_enabled: bool = True         # Enable automatic startup sequences
    
    # Performance optimization
    enable_performance_optimization: bool = True   # Enable system-wide performance optimization
    optimization_interval_hours: float = 1.0       # Performance optimization interval
    efficiency_target: float = 0.33                # Target overall cycle efficiency
    
    # System protection and interlocks
    enable_system_interlocks: bool = True          # Enable system interlocks
    turbine_steam_generator_interlock: bool = True # Turbine-SG interlock
    feedwater_steam_generator_interlock: bool = True # Feedwater-SG interlock
    condenser_turbine_interlock: bool = True       # Condenser-turbine interlock
    
    # Load dispatch and control
    load_dispatch_mode: str = "automatic"          # Load dispatch mode ("automatic", "manual")
    load_ramp_rate: float = 5.0                     # %/minute maximum load ramp rate
    minimum_system_load: float = 0.2               # Minimum system load (20%)
    maximum_system_load: float = 1.05              # Maximum system load (105%)
    
    # System startup and shutdown
    startup_sequence_enabled: bool = True          # Enable automated startup sequence
    shutdown_sequence_enabled: bool = True         # Enable automated shutdown sequence
    startup_time_minutes: float = 180.0            # Target startup time (3 hours)
    shutdown_time_minutes: float = 120.0           # Target shutdown time (2 hours)
    
    # Emergency response
    emergency_shutdown_enabled: bool = True        # Enable emergency shutdown capability
    emergency_feedwater_enabled: bool = True       # Enable emergency feedwater
    steam_dump_enabled: bool = True                # Enable steam dump capability
    
    # System monitoring and diagnostics
    enable_system_diagnostics: bool = True         # Enable system-wide diagnostics
    diagnostic_interval_minutes: float = 15.0      # Diagnostic check interval
    performance_trending_enabled: bool = True      # Enable performance trending
    predictive_analytics_enabled: bool = True      # Enable predictive analytics


@dataclass_json
@dataclass
class SecondarySystemMaintenanceConfig:
    """Maintenance configuration for the entire secondary system"""
    
    # System-level maintenance
    system_efficiency_threshold: float = 0.30      # 30% system efficiency threshold (90% of design)
    system_availability_threshold: float = 0.95    # 95% system availability threshold
    system_reliability_threshold: float = 0.98     # 98% system reliability threshold
    
    # Coordinated maintenance
    enable_coordinated_maintenance: bool = True    # Enable coordinated maintenance planning
    maintenance_window_hours: float = 168.0        # Weekly maintenance window
    outage_planning_enabled: bool = True           # Enable outage planning
    
    # System maintenance actions
    system_performance_test_action: str = "secondary_system_performance_test"
    system_optimization_action: str = "secondary_system_optimization"
    system_coordination_test_action: str = "secondary_system_coordination_test"
    integrated_leak_test_action: str = "secondary_system_leak_test"
    system_calibration_action: str = "secondary_system_calibration"
    
    # System maintenance intervals
    system_performance_test_interval_hours: float = 720.0    # Monthly performance test
    system_optimization_interval_hours: float = 2190.0      # Quarterly optimization
    system_coordination_test_interval_hours: float = 4380.0  # Semi-annual coordination test
    integrated_leak_test_interval_hours: float = 8760.0     # Annual leak test
    system_calibration_interval_hours: float = 4380.0       # Semi-annual calibration
    
    # System maintenance cooldowns
    system_performance_test_cooldown_hours: float = 720.0    # Monthly cooldown
    system_optimization_cooldown_hours: float = 2190.0      # Quarterly cooldown
    system_coordination_test_cooldown_hours: float = 4380.0  # Semi-annual cooldown
    integrated_leak_test_cooldown_hours: float = 8760.0     # Annual cooldown
    system_calibration_cooldown_hours: float = 4380.0       # Semi-annual cooldown


@dataclass_json
@dataclass
class SecondarySystemConfig(YAMLWizard, JSONWizard, TOMLWizard):
    """
    Comprehensive Secondary System Configuration
    
    This configuration class integrates all secondary system subsystems
    including steam generators, turbine, feedwater, and condenser systems.
    """
    
    # === SYSTEM IDENTIFICATION ===
    system_id: str = "SECONDARY-001"               # Secondary system identifier
    plant_id: str = "PWR-PLANT-001"                # Plant identifier
    
    # === DESIGN PARAMETERS ===
    rated_thermal_power: float = 3000.0e6          # W rated thermal power
    rated_electrical_power: float = 1000.0         # MW rated electrical power
    design_efficiency: float = 0.33                # Design cycle efficiency
    num_loops: int = 3                             # Number of loops
    
    # === SUBSYSTEM CONFIGURATIONS ===
    steam_generator: SteamGeneratorConfig = field(default_factory=create_standard_sg_config)
    turbine: TurbineConfig = field(default_factory=create_standard_turbine_config)
    feedwater: FeedwaterConfig = field(default_factory=create_standard_feedwater_config)
    condenser: CondenserConfig = field(default_factory=create_standard_condenser_config)
    
    # === INTEGRATION CONFIGURATION ===
    integration: SecondarySystemIntegrationConfig = field(default_factory=SecondarySystemIntegrationConfig)
    
    # === MAINTENANCE CONFIGURATION ===
    maintenance: SecondarySystemMaintenanceConfig = field(default_factory=SecondarySystemMaintenanceConfig)
    
    def __post_init__(self):
        """Validate and synchronize subsystem configurations"""
        self._validate_parameters()
        self._synchronize_subsystems()
    
    def _validate_parameters(self):
        """Validate configuration parameters and subsystem compatibility"""
        errors = []
        
        # Validate basic parameters
        if self.rated_thermal_power <= 0:
            errors.append("Rated thermal power must be positive")
        
        if self.rated_electrical_power <= 0:
            errors.append("Rated electrical power must be positive")
        
        if not (0.25 <= self.design_efficiency <= 0.40):
            errors.append("Design efficiency outside reasonable range (25-40%)")
        
        if self.num_loops <= 0:
            errors.append("Number of loops must be positive")
        
        # Validate subsystem compatibility
        if self.steam_generator.num_steam_generators != self.num_loops:
            errors.append(f"Steam generator count ({self.steam_generator.num_steam_generators}) "
                         f"doesn't match number of loops ({self.num_loops})")
        
        if self.feedwater.num_steam_generators != self.num_loops:
            errors.append(f"Feedwater SG count ({self.feedwater.num_steam_generators}) "
                         f"doesn't match number of loops ({self.num_loops})")
        
        # Validate flow consistency
        sg_total_steam_flow = self.steam_generator.design_total_steam_flow
        turbine_steam_flow = self.turbine.design_steam_flow
        feedwater_total_flow = self.feedwater.design_total_flow
        condenser_steam_flow = self.condenser.design_steam_flow
        
        flow_tolerance = 0.05  # 5% tolerance
        if abs(sg_total_steam_flow - turbine_steam_flow) / sg_total_steam_flow > flow_tolerance:
            errors.append(f"Steam flow mismatch: SG ({sg_total_steam_flow:.0f}) vs Turbine ({turbine_steam_flow:.0f})")
        
        if abs(feedwater_total_flow - sg_total_steam_flow) / feedwater_total_flow > flow_tolerance:
            errors.append(f"Flow mismatch: Feedwater ({feedwater_total_flow:.0f}) vs SG ({sg_total_steam_flow:.0f})")
        
        if abs(condenser_steam_flow - turbine_steam_flow) / condenser_steam_flow > flow_tolerance:
            errors.append(f"Steam flow mismatch: Condenser ({condenser_steam_flow:.0f}) vs Turbine ({turbine_steam_flow:.0f})")
        
        # Validate pressure consistency
        sg_pressure = self.steam_generator.design_steam_pressure
        turbine_inlet_pressure = self.turbine.design_steam_pressure
        
        pressure_tolerance = 0.1  # 0.1 MPa tolerance
        if abs(sg_pressure - turbine_inlet_pressure) > pressure_tolerance:
            errors.append(f"Pressure mismatch: SG ({sg_pressure:.1f}) vs Turbine ({turbine_inlet_pressure:.1f}) MPa")
        
        # Validate power consistency
        calculated_electrical_power = self.rated_thermal_power * self.design_efficiency / 1e6
        if abs(calculated_electrical_power - self.rated_electrical_power) / self.rated_electrical_power > 0.1:
            errors.append(f"Power inconsistency: Calculated ({calculated_electrical_power:.0f}) vs "
                         f"Rated ({self.rated_electrical_power:.0f}) MW")
        
        if errors:
            raise ValueError("Secondary system configuration validation failed:\n" + 
                           "\n".join(f"  - {error}" for error in errors))
    
    def _synchronize_subsystems(self):
        """Synchronize parameters across subsystems"""
        # Update subsystem IDs to be consistent
        self.steam_generator.system_id = f"{self.system_id}-SG"
        self.turbine.system_id = f"{self.system_id}-TURB"
        self.feedwater.system_id = f"{self.system_id}-FW"
        self.condenser.system_id = f"{self.system_id}-COND"
        
        # Synchronize flow rates
        design_steam_flow = self.steam_generator.design_total_steam_flow
        self.turbine.design_steam_flow = design_steam_flow
        self.feedwater.design_total_flow = design_steam_flow
        self.condenser.design_steam_flow = design_steam_flow
        
        # Synchronize pressures
        steam_pressure = self.steam_generator.design_steam_pressure
        self.turbine.design_steam_pressure = steam_pressure
        
        # Synchronize temperatures
        steam_temperature = self.steam_generator.design_steam_temperature
        self.turbine.design_steam_temperature = steam_temperature
        
        feedwater_temperature = self.feedwater.design_feedwater_temperature
        self.steam_generator.design_feedwater_temperature = feedwater_temperature
        
        # Synchronize condenser parameters
        condenser_pressure = self.condenser.design_condenser_pressure
        self.turbine.design_condenser_pressure = condenser_pressure
        
        # Calculate and synchronize heat rejection
        turbine_heat_rejection = self.rated_thermal_power * (1 - self.design_efficiency)
        self.condenser.design_heat_duty = turbine_heat_rejection
        
        # Update number of loops consistency
        self.steam_generator.num_steam_generators = self.num_loops
        self.feedwater.num_steam_generators = self.num_loops
    
    def get_subsystem_config(self, subsystem: str) -> Dict[str, Any]:
        """
        Get configuration for a specific subsystem
        
        Args:
            subsystem: Subsystem name ("steam_generator", "turbine", "feedwater", "condenser")
            
        Returns:
            Dictionary with subsystem configuration
        """
        subsystem_map = {
            "steam_generator": self.steam_generator,
            "turbine": self.turbine,
            "feedwater": self.feedwater,
            "condenser": self.condenser
        }
        
        if subsystem not in subsystem_map:
            raise ValueError(f"Unknown subsystem: {subsystem}. "
                           f"Available: {list(subsystem_map.keys())}")
        
        config = subsystem_map[subsystem]
        return {
            'system_id': config.system_id,
            'config': config,
            'summary': config.get_summary()
        }
    
    def get_system_performance_summary(self) -> Dict[str, Any]:
        """Get overall system performance summary"""
        return {
            'thermal_performance': {
                'rated_thermal_power_mw': self.rated_thermal_power / 1e6,
                'rated_electrical_power_mw': self.rated_electrical_power,
                'design_efficiency': self.design_efficiency,
                'heat_rate_btu_per_kwh': 3412.14 / self.design_efficiency,  # Btu/kWh
                'steam_flow_total_kgs': self.steam_generator.design_total_steam_flow,
                'feedwater_flow_total_kgs': self.feedwater.design_total_flow
            },
            'system_configuration': {
                'num_loops': self.num_loops,
                'num_steam_generators': self.steam_generator.num_steam_generators,
                'steam_pressure_mpa': self.steam_generator.design_steam_pressure,
                'steam_temperature_c': self.steam_generator.design_steam_temperature,
                'condenser_pressure_mpa': self.condenser.design_condenser_pressure,
                'feedwater_temperature_c': self.feedwater.design_feedwater_temperature
            },
            'turbine_performance': {
                'rated_power_mw': self.turbine.rated_power_mwe,
                'design_efficiency': self.turbine.design_efficiency,
                'hp_stages': self.turbine.stage_system.hp_stages,
                'lp_stages': self.turbine.stage_system.lp_stages,
                'extraction_points': len(self.turbine.stage_system.extraction_points)
            },
            'heat_rejection': {
                'condenser_heat_duty_mw': self.condenser.design_heat_duty / 1e6,
                'cooling_water_flow_kgs': self.condenser.design_cooling_water_flow,
                'cooling_water_temp_rise_c': self.condenser.design_cooling_water_temp_rise,
                'condenser_tubes': self.condenser.heat_transfer.tube_count
            }
        }
    
    def get_maintenance_summary(self) -> Dict[str, Any]:
        """Get system-wide maintenance configuration summary"""
        return {
            'system_level': {
                'system_efficiency_threshold': self.maintenance.system_efficiency_threshold,
                'system_availability_threshold': self.maintenance.system_availability_threshold,
                'coordinated_maintenance_enabled': self.maintenance.enable_coordinated_maintenance,
                'maintenance_window_hours': self.maintenance.maintenance_window_hours,
                'system_performance_test_interval_hours': self.maintenance.system_performance_test_interval_hours
            },
            'steam_generator': {
                'tsp_fouling_threshold_mm': self.steam_generator.maintenance.tsp_fouling_threshold,
                'tube_wall_temp_threshold_c': self.steam_generator.maintenance.tube_wall_temperature_threshold,
                'individual_sg_check_interval_hours': self.steam_generator.maintenance.individual_sg_check_interval_hours
            },
            'turbine': {
                'efficiency_threshold': self.turbine.maintenance.efficiency_threshold,
                'vibration_alarm_threshold_mils': self.turbine.maintenance.vibration_alarm_threshold,
                'bearing_temperature_threshold_c': self.turbine.maintenance.bearing_temperature_threshold,
                'performance_test_interval_hours': self.turbine.maintenance.performance_test_interval_hours
            },
            'feedwater': {
                'pump_efficiency_threshold': self.feedwater.maintenance.pump_efficiency_threshold,
                'vibration_threshold_mms': self.feedwater.maintenance.vibration_threshold,
                'pump_maintenance_interval_hours': self.feedwater.maintenance.pump_maintenance_interval_hours
            },
            'condenser': {
                'thermal_performance_threshold': self.condenser.maintenance.thermal_performance_threshold,
                'tube_leak_rate_threshold_kgs': self.condenser.maintenance.tube_leak_rate_threshold,
                'active_tube_count_threshold': self.condenser.maintenance.active_tube_count_threshold,
                'tube_cleaning_interval_hours': self.condenser.maintenance.tube_cleaning_interval_hours
            }
        }
    
    def get_integration_config(self) -> Dict[str, Any]:
        """Get system integration configuration"""
        return {
            'coordination': {
                'system_coordination_enabled': self.integration.enable_system_coordination,
                'load_following_enabled': self.integration.load_following_enabled,
                'automatic_startup_enabled': self.integration.automatic_startup_enabled,
                'performance_optimization_enabled': self.integration.enable_performance_optimization
            },
            'interlocks': {
                'system_interlocks_enabled': self.integration.enable_system_interlocks,
                'turbine_sg_interlock': self.integration.turbine_steam_generator_interlock,
                'feedwater_sg_interlock': self.integration.feedwater_steam_generator_interlock,
                'condenser_turbine_interlock': self.integration.condenser_turbine_interlock
            },
            'load_control': {
                'load_dispatch_mode': self.integration.load_dispatch_mode,
                'load_ramp_rate_pct_per_min': self.integration.load_ramp_rate,
                'minimum_system_load': self.integration.minimum_system_load,
                'maximum_system_load': self.integration.maximum_system_load
            },
            'startup_shutdown': {
                'startup_sequence_enabled': self.integration.startup_sequence_enabled,
                'shutdown_sequence_enabled': self.integration.shutdown_sequence_enabled,
                'startup_time_minutes': self.integration.startup_time_minutes,
                'shutdown_time_minutes': self.integration.shutdown_time_minutes
            },
            'emergency_systems': {
                'emergency_shutdown_enabled': self.integration.emergency_shutdown_enabled,
                'emergency_feedwater_enabled': self.integration.emergency_feedwater_enabled,
                'steam_dump_enabled': self.integration.steam_dump_enabled
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive secondary system summary"""
        return {
            'system_info': {
                'system_id': self.system_id,
                'plant_id': self.plant_id,
                'rated_thermal_power_mw': self.rated_thermal_power / 1e6,
                'rated_electrical_power_mw': self.rated_electrical_power,
                'design_efficiency': self.design_efficiency,
                'num_loops': self.num_loops
            },
            'performance': self.get_system_performance_summary(),
            'maintenance': self.get_maintenance_summary(),
            'integration': self.get_integration_config(),
            'subsystems': {
                'steam_generator': self.steam_generator.get_summary(),
                'turbine': self.turbine.get_summary(),
                'feedwater': self.feedwater.get_summary(),
                'condenser': self.condenser.get_summary()
            }
        }


# Factory functions for creating common configurations
def create_standard_secondary_config() -> SecondarySystemConfig:
    """Create standard 3-loop PWR secondary system configuration"""
    return SecondarySystemConfig(
        system_id="SECONDARY-STD-001",
        plant_id="PWR-PLANT-STD-001",
        rated_thermal_power=3000.0e6,
        rated_electrical_power=1000.0,
        design_efficiency=0.33,
        num_loops=3
    )


def create_uprated_secondary_config() -> SecondarySystemConfig:
    """Create uprated PWR secondary system configuration"""
    config = SecondarySystemConfig(
        system_id="SECONDARY-UP-001",
        plant_id="PWR-PLANT-UP-001",
        rated_thermal_power=3255.0e6,        # Uprated thermal power
        rated_electrical_power=1100.0,       # Uprated electrical power
        design_efficiency=0.34,              # Higher efficiency
        num_loops=3
    )
    
    # Use uprated subsystem configurations
    from .steam_generator.config import create_uprated_sg_config
    from .turbine.config import create_uprated_turbine_config
    from .feedwater.config import create_uprated_feedwater_config
    from .condenser.config import create_uprated_condenser_config
    
    config.steam_generator = create_uprated_sg_config()
    config.turbine = create_uprated_turbine_config()
    config.feedwater = create_uprated_feedwater_config()
    config.condenser = create_uprated_condenser_config()
    
    return config


def create_four_loop_secondary_config() -> SecondarySystemConfig:
    """Create 4-loop PWR secondary system configuration"""
    config = SecondarySystemConfig(
        system_id="SECONDARY-4L-001",
        plant_id="PWR-PLANT-4L-001",
        rated_thermal_power=3000.0e6,
        rated_electrical_power=1000.0,
        design_efficiency=0.33,
        num_loops=4
    )
    
    # Use 4-loop subsystem configurations
    from .steam_generator.config import create_four_loop_sg_config
    from .feedwater.config import create_four_loop_feedwater_config
    
    config.steam_generator = create_four_loop_sg_config()
    config.feedwater = create_four_loop_feedwater_config()
    
    return config


def create_high_efficiency_secondary_config() -> SecondarySystemConfig:
    """Create high-efficiency PWR secondary system configuration"""
    config = SecondarySystemConfig(
        system_id="SECONDARY-HE-001",
        plant_id="PWR-PLANT-HE-001",
        rated_thermal_power=3000.0e6,
        rated_electrical_power=1080.0,       # Higher electrical output
        design_efficiency=0.36,              # Higher efficiency
        num_loops=3
    )
    
    # Use high-efficiency subsystem configurations
    from .turbine.config import create_high_efficiency_turbine_config
    from .condenser.config import create_high_efficiency_condenser_config
    
    config.turbine = create_high_efficiency_turbine_config()
    config.condenser = create_high_efficiency_condenser_config()
    
    return config


class PWRConfigManager:
    """Manager for loading PWR configurations from YAML files using dataclass-wizard"""
    
    @staticmethod
    def load_pwr_config(config_file: str) -> SecondarySystemConfig:
        """
        Load PWR configuration from YAML file using dataclass-wizard
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            SecondarySystemConfig loaded from YAML
        """
        import os
        
        # Handle relative paths - try multiple locations
        if not os.path.isabs(config_file):
            # Try relative to secondary directory first
            config_dir = os.path.dirname(__file__)
            full_path = os.path.join(config_dir, config_file)
            
            if not os.path.exists(full_path):
                # Try relative to current working directory
                full_path = config_file
                
            if not os.path.exists(full_path):
                # Try relative to project root
                project_root = os.path.dirname(os.path.dirname(config_dir))
                full_path = os.path.join(project_root, config_file)
            
            config_file = full_path
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            # Use dataclass-wizard's native YAML loading - this is the magic!
            return SecondarySystemConfig.from_yaml_file(config_file)
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {config_file}: {e}")


class PWR3000ConfigFactory:
    """Factory for creating standard PWR configurations"""
    
    @staticmethod
    def create_standard_pwr3000() -> SecondarySystemConfig:
        """
        Create standard PWR configuration from YAML
        
        Uses the restructured YAML file that matches our dataclass structure.
        
        Returns:
            SecondarySystemConfig loaded from YAML
        """
        # Load from the restructured YAML file
        config_file = os.path.join(os.path.dirname(__file__), 'secondary_system_config.yaml')
        if os.path.exists(config_file):
            return PWRConfigManager.load_pwr_config(config_file)
        else:
            # Fallback to programmatic creation if YAML not found
            print(f"Warning: YAML config file not found at {config_file}, using programmatic defaults")
            return create_standard_secondary_config()
    
    @staticmethod
    def create_uprated_pwr3000() -> SecondarySystemConfig:
        """Create uprated PWR configuration"""
        return create_uprated_secondary_config()
    
    @staticmethod
    def create_four_loop_pwr3000() -> SecondarySystemConfig:
        """Create 4-loop PWR configuration"""
        return create_four_loop_secondary_config()
    
    @staticmethod
    def create_high_efficiency_pwr3000() -> SecondarySystemConfig:
        """Create high-efficiency PWR configuration"""
        return create_high_efficiency_secondary_config()
    
    @staticmethod
    def load_from_comprehensive_yaml() -> SecondarySystemConfig:
        """
        Load configuration from the original comprehensive YAML structure
        
        This method handles the nested structure of the comprehensive config file.
        """
        try:
            import yaml
            config_file = os.path.join(os.path.dirname(__file__), 'nuclear_plant_comprehensive_config.yaml')
            
            with open(config_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            if 'secondary_system' in yaml_data:
                # Extract secondary system section
                secondary_data = yaml_data['secondary_system']
                
                # Create SecondarySystemConfig with the YAML values
                config = SecondarySystemConfig(
                    system_id=secondary_data.get('system_id', 'SECONDARY-001'),
                    plant_id=secondary_data.get('plant_id', 'PWR-PLANT-001'),
                    rated_thermal_power=secondary_data.get('rated_thermal_power', 3000.0e6),
                    rated_electrical_power=secondary_data.get('rated_electrical_power', 1000.0),
                    design_efficiency=secondary_data.get('design_efficiency', 0.33),
                    num_loops=secondary_data.get('num_loops', 3)
                )
                return config
            else:
                raise ValueError("No 'secondary_system' section found in comprehensive YAML")
                
        except Exception as e:
            print(f"Warning: Could not load from comprehensive YAML: {e}")
            return PWR3000ConfigFactory.create_standard_pwr3000()


# Example usage and testing
if __name__ == "__main__":
    print("Secondary System Configuration")
    print("=" * 50)
    
    # Test standard configuration
    config = create_standard_secondary_config()
    summary = config.get_summary()
    
    print("Standard Configuration:")
    print(f"  System ID: {summary['system_info']['system_id']}")
    print(f"  Plant ID: {summary['system_info']['plant_id']}")
    print(f"  Rated Thermal Power: {summary['system_info']['rated_thermal_power_mw']:.0f} MW")
    print(f"  Rated Electrical Power: {summary['system_info']['rated_electrical_power_mw']:.0f} MW")
    print(f"  Design Efficiency: {summary['system_info']['design_efficiency']:.1%}")
    print(f"  Number of Loops: {summary['system_info']['num_loops']}")
    print()
    
    print("System Performance:")
    perf = summary['performance']['thermal_performance']
    print(f"  Heat Rate: {perf['heat_rate_btu_per_kwh']:.0f} Btu/kWh")
    print(f"  Total Steam Flow: {perf['steam_flow_total_kgs']:.0f} kg/s")
    print(f"  Total Feedwater Flow: {perf['feedwater_flow_total_kgs']:.0f} kg/s")
    print()
    
    config_info = summary['performance']['system_configuration']
    print("System Configuration:")
    print(f"  Steam Pressure: {config_info['steam_pressure_mpa']:.1f} MPa")
    print(f"  Steam Temperature: {config_info['steam_temperature_c']:.1f} °C")
    print(f"  Condenser Pressure: {config_info['condenser_pressure_mpa']:.3f} MPa")
    print(f"  Feedwater Temperature: {config_info['feedwater_temperature_c']:.1f} °C")
    print()
    
    turb_perf = summary['performance']['turbine_performance']
    print("Turbine Performance:")
    print(f"  Rated Power: {turb_perf['rated_power_mw']:.0f} MW")
    print(f"  Design Efficiency: {turb_perf['design_efficiency']:.1%}")
    print(f"  HP Stages: {turb_perf['hp_stages']}")
    print(f"  LP Stages: {turb_perf['lp_stages']}")
    print(f"  Extraction Points: {turb_perf['extraction_points']}")
    print()
    
    heat_rej = summary['performance']['heat_rejection']
    print("Heat Rejection:")
    print(f"  Condenser Heat Duty: {heat_rej['condenser_heat_duty_mw']:.0f} MW")
    print(f"  Cooling Water Flow: {heat_rej['cooling_water_flow_kgs']:.0f} kg/s")
    print(f"  Cooling Water Temp Rise: {heat_rej['cooling_water_temp_rise_c']:.1f} °C")
    print(f"  Condenser Tubes: {heat_rej['condenser_tubes']:,}")
    print()
    
    # Test integration configuration
    integration = config.get_integration_config()
    print("Integration Configuration:")
    coord = integration['coordination']
    print(f"  System Coordination: {coord['system_coordination_enabled']}")
    print(f"  Load Following: {coord['load_following_enabled']}")
    print(f"  Automatic Startup: {coord['automatic_startup_enabled']}")
    print(f"  Performance Optimization: {coord['performance_optimization_enabled']}")
    print()
    
    interlocks = integration['interlocks']
    print("System Interlocks:")
    print(f"  System Interlocks Enabled: {interlocks['system_interlocks_enabled']}")
    print(f"  Turbine-SG Interlock: {interlocks['turbine_sg_interlock']}")
    print(f"  Feedwater-SG Interlock: {interlocks['feedwater_sg_interlock']}")
    print(f"  Condenser-Turbine Interlock: {interlocks['condenser_turbine_interlock']}")
    print()
    
    # Test subsystem access
    sg_config = config.get_subsystem_config("steam_generator")
    print("Steam Generator Subsystem:")
    print(f"  System ID: {sg_config['system_id']}")
    sg_summary = sg_config['summary']['system_info']
    print(f"  Number of SGs: {sg_summary['num_steam_generators']}")
    print(f"  Total Thermal Power: {sg_summary['design_total_thermal_power_mw']:.0f} MW")
    print(f"  Total Steam Flow: {sg_summary['design_total_steam_flow_kgs']:.0f} kg/s")
    print()
    
    # Test maintenance summary
    maint_summary = config.get_maintenance_summary()
    print("Maintenance Summary:")
    sys_maint = maint_summary['system_level']
    print(f"  System Efficiency Threshold: {sys_maint['system_efficiency_threshold']:.1%}")
    print(f"  System Availability Threshold: {sys_maint['system_availability_threshold']:.1%}")
    print(f"  Coordinated Maintenance: {sys_maint['coordinated_maintenance_enabled']}")
    print(f"  Maintenance Window: {sys_maint['maintenance_window_hours']:.0f} hours")
    print()
    
    # Test file operations if available
    if DATACLASS_WIZARD_AVAILABLE:
        print("Testing YAML serialization...")
        try:
            # Save to YAML
            config.to_yaml_file("test_secondary_config.yaml")
            
            # Load from YAML
            loaded_config = SecondarySystemConfig.from_yaml_file("test_secondary_config.yaml")
            
            print("  YAML serialization: SUCCESS")
            print(f"  Loaded config system ID: {loaded_config.system_id}")
            
            # Clean up
            import os
            os.remove("test_secondary_config.yaml")
            
        except Exception as e:
            print(f"  YAML serialization failed: {e}")
    else:
        print("Install dataclass-wizard for YAML serialization: pip install dataclass-wizard")
    
    print("Secondary system configuration ready!")
