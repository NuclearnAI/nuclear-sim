"""
Maintenance Configuration System

This module provides a comprehensive configuration system for the maintenance
management system, allowing users to configure maintenance behavior through
YAML files rather than hard-coded templates.

Key Features:
1. Flexible threshold configuration per component type
2. Multiple preset modes (conservative, aggressive, ultra-aggressive, custom)
3. Global multipliers for easy adjustment
4. Component-specific overrides
5. YAML/JSON serialization support
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import warnings

# Import dataclass-wizard for configuration serialization
try:
    from dataclass_wizard import YAMLWizard, JSONWizard
    DATACLASS_WIZARD_AVAILABLE = True
except ImportError:
    warnings.warn("dataclass-wizard not available. Install with: pip install dataclass-wizard")
    DATACLASS_WIZARD_AVAILABLE = False
    
    # Fallback base classes
    class YAMLWizard:
        def to_yaml_file(self, filepath: str):
            raise NotImplementedError("dataclass-wizard not installed")
        
        @classmethod
        def from_yaml_file(cls, filepath: str):
            raise NotImplementedError("dataclass-wizard not installed")
    
    class JSONWizard:
        pass

from simulator.state.component_metadata import EquipmentType


class MaintenanceMode(Enum):
    """Predefined maintenance modes"""
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    ULTRA_AGGRESSIVE = "ultra_aggressive"
    CUSTOM = "custom"


@dataclass
class ComponentThresholds:
    """Threshold configuration for a specific component parameter"""
    threshold: float
    comparison: str = "greater_than"  # greater_than, less_than, equals
    action: str = "routine_maintenance"
    cooldown_hours: float = 24.0
    priority: str = "MEDIUM"  # EMERGENCY, CRITICAL, HIGH, MEDIUM, LOW


@dataclass
class ComponentTypeConfig:
    """Configuration for a specific equipment type"""
    check_interval_hours: float = 24.0
    thresholds: Dict[str, ComponentThresholds] = field(default_factory=dict)
    
    def add_threshold(self, parameter: str, threshold: float, **kwargs):
        """Add a threshold configuration for a parameter"""
        self.thresholds[parameter] = ComponentThresholds(threshold=threshold, **kwargs)


@dataclass
class MaintenanceConfig(YAMLWizard, JSONWizard):
    """
    Comprehensive maintenance configuration
    
    This configuration allows fine-grained control over maintenance behavior
    through YAML files, supporting multiple modes and custom overrides.
    """
    
    # === BASIC CONFIGURATION ===
    mode: MaintenanceMode = MaintenanceMode.CONSERVATIVE
    description: str = "Default maintenance configuration"
    
    # === GLOBAL SETTINGS ===
    default_check_interval_hours: float = 24.0
    auto_execute_maintenance: bool = True
    
    # === GLOBAL MULTIPLIERS ===
    # These are applied to all thresholds and can be used for easy adjustment
    threshold_multiplier: float = 1.0      # Multiply all thresholds by this factor
    cooldown_reduction_factor: float = 1.0  # Multiply all cooldowns by this factor
    check_interval_multiplier: float = 1.0  # Multiply all check intervals by this factor
    
    # === COMPONENT TYPE CONFIGURATIONS ===
    # Configuration for each equipment type
    component_types: Dict[str, ComponentTypeConfig] = field(default_factory=dict)
    
    # === COMPONENT-SPECIFIC OVERRIDES ===
    # Override settings for specific component instances
    component_overrides: Dict[str, ComponentTypeConfig] = field(default_factory=dict)
    
    # === ADVANCED SETTINGS ===
    enable_predictive_maintenance: bool = True
    enable_condition_based_maintenance: bool = True
    work_order_cooldown_hours: float = 1.0
    
    def __post_init__(self):
        """Initialize with default configurations if none provided"""
        if not self.component_types:
            self._load_default_configurations()
    
    def _load_default_configurations(self):
        """Load default configurations based on the selected mode"""
        if self.mode == MaintenanceMode.CONSERVATIVE:
            self._load_conservative_config()
        elif self.mode == MaintenanceMode.AGGRESSIVE:
            self._load_aggressive_config()
        elif self.mode == MaintenanceMode.ULTRA_AGGRESSIVE:
            self._load_ultra_aggressive_config()
        # CUSTOM mode starts with empty config for user to define
    
    def _load_conservative_config(self):
        """Load conservative maintenance thresholds"""
        # PUMP configuration
        pump_config = ComponentTypeConfig(check_interval_hours=24.0)
        pump_config.add_threshold("oil_level", 20.0, comparison="less_than", action="oil_top_off", cooldown_hours=8.0, priority="HIGH")
        pump_config.add_threshold("oil_temperature", 70.0, action="oil_change", cooldown_hours=24.0, priority="MEDIUM")
        pump_config.add_threshold("oil_contamination_level", 15.0, action="oil_change", cooldown_hours=24.0, priority="MEDIUM")
        pump_config.add_threshold("vibration_level", 10.0, action="vibration_analysis", cooldown_hours=12.0, priority="HIGH")
        pump_config.add_threshold("bearing_temperature", 90.0, action="bearing_inspection", cooldown_hours=24.0, priority="HIGH")
        pump_config.add_threshold("bearing_wear", 30.0, action="bearing_replacement", cooldown_hours=168.0, priority="CRITICAL")
        pump_config.add_threshold("impeller_wear", 20.0, action="impeller_inspection", cooldown_hours=72.0, priority="MEDIUM")
        pump_config.add_threshold("seal_wear", 40.0, action="seal_replacement", cooldown_hours=48.0, priority="HIGH")
        pump_config.add_threshold("efficiency_degradation_factor", 0.85, comparison="less_than", action="efficiency_analysis", cooldown_hours=168.0, priority="MEDIUM")
        self.component_types["pump"] = pump_config
        
        # TURBINE_STAGE configuration
        turbine_config = ComponentTypeConfig(check_interval_hours=24.0)
        turbine_config.add_threshold("efficiency", 0.80, comparison="less_than", action="efficiency_analysis", cooldown_hours=168.0, priority="MEDIUM")
        turbine_config.add_threshold("blade_wear", 15.0, action="blade_inspection", cooldown_hours=168.0, priority="HIGH")
        turbine_config.add_threshold("vibration_level", 8.0, action="vibration_analysis", cooldown_hours=24.0, priority="HIGH")
        turbine_config.add_threshold("blade_temperature", 550.0, action="blade_inspection", cooldown_hours=48.0, priority="CRITICAL")
        self.component_types["turbine_stage"] = turbine_config
        
        # STEAM_GENERATOR configuration
        sg_config = ComponentTypeConfig(check_interval_hours=24.0)
        sg_config.add_threshold("tsp_fouling_fraction", 0.15, action="tsp_chemical_cleaning", cooldown_hours=168.0, priority="MEDIUM")
        sg_config.add_threshold("tube_fouling_factor", 0.15, action="tsp_chemical_cleaning", cooldown_hours=168.0, priority="MEDIUM")
        sg_config.add_threshold("efficiency", 0.85, comparison="less_than", action="secondary_side_cleaning", cooldown_hours=168.0, priority="MEDIUM")
        sg_config.add_threshold("steam_quality", 0.99, comparison="less_than", action="moisture_separator_maintenance", cooldown_hours=48.0, priority="HIGH")
        sg_config.add_threshold("tube_wall_temperature", 350.0, action="scale_removal", cooldown_hours=24.0, priority="HIGH")
        sg_config.add_threshold("water_level", 10.0, comparison="less_than", action="routine_maintenance", cooldown_hours=8.0, priority="HIGH")
        sg_config.add_threshold("tube_integrity", 0.90, comparison="less_than", action="eddy_current_testing", cooldown_hours=720.0, priority="CRITICAL")
        self.component_types["steam_generator"] = sg_config
        
        # CONDENSER configuration
        condenser_config = ComponentTypeConfig(check_interval_hours=24.0)
        condenser_config.add_threshold("vacuum_level", 85.0, comparison="less_than", action="vacuum_system_check", cooldown_hours=24.0, priority="MEDIUM")
        condenser_config.add_threshold("tube_cleanliness", 0.80, comparison="less_than", action="tube_cleaning", cooldown_hours=168.0, priority="MEDIUM")
        condenser_config.add_threshold("cooling_water_outlet_temp", 40.0, action="cooling_water_check", cooldown_hours=24.0, priority="MEDIUM")
        condenser_config.add_threshold("heat_rejection_efficiency", 0.85, comparison="less_than", action="efficiency_analysis", cooldown_hours=168.0, priority="MEDIUM")
        self.component_types["condenser"] = condenser_config
    
    def _load_aggressive_config(self):
        """Load aggressive maintenance thresholds"""
        self._load_conservative_config()  # Start with conservative
        
        # Apply aggressive multipliers
        self.threshold_multiplier = 1.2  # 20% more sensitive thresholds
        self.cooldown_reduction_factor = 0.5  # 50% shorter cooldowns
        self.check_interval_multiplier = 0.25  # Check 4x more frequently
        self.work_order_cooldown_hours = 0.5
    
    def _load_ultra_aggressive_config(self):
        """Load ultra-aggressive maintenance thresholds"""
        self._load_conservative_config()  # Start with conservative
        
        # Apply ultra-aggressive multipliers
        self.threshold_multiplier = 2.0  # 100% more sensitive thresholds
        self.cooldown_reduction_factor = 0.1  # 90% shorter cooldowns
        self.check_interval_multiplier = 0.05  # Check 20x more frequently (3 minutes)
        self.work_order_cooldown_hours = 0.1  # 6 minutes between work orders
        
        # Override specific thresholds for maximum work order generation
        pump_config = self.component_types["pump"]
        
        # Disable oil changes by making thresholds very low
        pump_config.thresholds["oil_level"].threshold = 5.0
        pump_config.thresholds["oil_level"].cooldown_hours = 8.0
        pump_config.thresholds["oil_contamination_level"].threshold = 1.0
        pump_config.thresholds["oil_contamination_level"].cooldown_hours = 10.0
        
        # Make mechanical issues very sensitive
        pump_config.add_threshold("bearing_wear", 0.1, action="bearing_inspection", cooldown_hours=0.2, priority="HIGH")
        pump_config.add_threshold("impeller_wear", 0.1, action="impeller_inspection", cooldown_hours=0.3, priority="HIGH")
        pump_config.add_threshold("vibration_level", 0.1, action="vibration_analysis", cooldown_hours=0.15, priority="HIGH")
        pump_config.add_threshold("seal_wear", 0.1, action="seal_replacement", cooldown_hours=0.25, priority="HIGH")
        
        # Make turbine stages very sensitive
        turbine_config = self.component_types["turbine_stage"]
        turbine_config.add_threshold("efficiency", 0.995, comparison="less_than", action="efficiency_analysis", cooldown_hours=0.3, priority="HIGH")
        turbine_config.add_threshold("blade_wear", 0.5, action="blade_inspection", cooldown_hours=0.4, priority="HIGH")
        turbine_config.add_threshold("vibration_level", 1.0, action="vibration_analysis", cooldown_hours=0.2, priority="HIGH")
        
        # Make steam generators very sensitive
        sg_config = self.component_types["steam_generator"]
        sg_config.add_threshold("tsp_fouling_fraction", 0.01, action="tsp_chemical_cleaning", cooldown_hours=0.5, priority="HIGH")
        sg_config.add_threshold("efficiency", 0.98, comparison="less_than", action="secondary_side_cleaning", cooldown_hours=0.4, priority="HIGH")
        sg_config.add_threshold("steam_quality", 0.999, comparison="less_than", action="moisture_separator_maintenance", cooldown_hours=0.3, priority="HIGH")
        sg_config.add_threshold("tube_wall_temperature", 250.0, action="scale_removal", cooldown_hours=0.2, priority="HIGH")
        
        # Make condensers very sensitive
        condenser_config = self.component_types["condenser"]
        condenser_config.add_threshold("vacuum_level", 98.0, comparison="less_than", action="vacuum_system_check", cooldown_hours=0.2, priority="HIGH")
        condenser_config.add_threshold("tube_cleanliness", 0.98, comparison="less_than", action="tube_cleaning", cooldown_hours=0.8, priority="HIGH")
        condenser_config.add_threshold("cooling_water_outlet_temp", 25.0, action="cooling_water_check", cooldown_hours=0.3, priority="HIGH")
    
    def get_component_config(self, component_id: str, equipment_type: EquipmentType) -> Optional[ComponentTypeConfig]:
        """Get configuration for a specific component"""
        # Check for component-specific override first
        if component_id in self.component_overrides:
            return self.component_overrides[component_id]
        
        # Fall back to equipment type configuration
        type_key = equipment_type.value.lower()
        if type_key in self.component_types:
            return self.component_types[type_key]
        
        return None
    
    def get_effective_threshold(self, base_threshold: float, comparison: str = "greater_than") -> float:
        """Apply global multipliers to get effective threshold"""
        if comparison == "greater_than":
            # For greater_than comparisons, lower threshold = more sensitive
            return base_threshold / self.threshold_multiplier
        else:
            # For less_than comparisons, higher threshold = more sensitive
            return base_threshold * self.threshold_multiplier
    
    def get_effective_cooldown(self, base_cooldown: float) -> float:
        """Apply global multipliers to get effective cooldown"""
        return base_cooldown * self.cooldown_reduction_factor
    
    def get_effective_check_interval(self, base_interval: float) -> float:
        """Apply global multipliers to get effective check interval"""
        return base_interval * self.check_interval_multiplier
    
    def add_component_override(self, component_id: str, config: ComponentTypeConfig):
        """Add configuration override for a specific component"""
        self.component_overrides[component_id] = config
    
    def validate_configuration(self) -> List[str]:
        """Validate the maintenance configuration"""
        errors = []
        
        # Check multipliers are reasonable
        if self.threshold_multiplier <= 0 or self.threshold_multiplier > 10:
            errors.append(f"Threshold multiplier {self.threshold_multiplier} outside reasonable range (0-10)")
        
        if self.cooldown_reduction_factor <= 0 or self.cooldown_reduction_factor > 2:
            errors.append(f"Cooldown reduction factor {self.cooldown_reduction_factor} outside reasonable range (0-2)")
        
        if self.check_interval_multiplier <= 0 or self.check_interval_multiplier > 2:
            errors.append(f"Check interval multiplier {self.check_interval_multiplier} outside reasonable range (0-2)")
        
        # Validate component configurations
        for comp_type, config in self.component_types.items():
            if config.check_interval_hours <= 0:
                errors.append(f"Component type {comp_type} has invalid check interval")
            
            for param, threshold_config in config.thresholds.items():
                if threshold_config.cooldown_hours < 0:
                    errors.append(f"Component type {comp_type}, parameter {param} has negative cooldown")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the maintenance configuration"""
        return {
            'mode': self.mode.value,
            'description': self.description,
            'global_settings': {
                'threshold_multiplier': self.threshold_multiplier,
                'cooldown_reduction_factor': self.cooldown_reduction_factor,
                'check_interval_multiplier': self.check_interval_multiplier,
                'work_order_cooldown_hours': self.work_order_cooldown_hours
            },
            'component_types_configured': list(self.component_types.keys()),
            'component_overrides': len(self.component_overrides),
            'total_thresholds': sum(len(config.thresholds) for config in self.component_types.values())
        }


class MaintenanceConfigFactory:
    """Factory for creating maintenance configurations"""
    
    @staticmethod
    def create_conservative() -> MaintenanceConfig:
        """Create conservative maintenance configuration"""
        return MaintenanceConfig(
            mode=MaintenanceMode.CONSERVATIVE,
            description="Conservative maintenance with realistic thresholds"
        )
    
    @staticmethod
    def create_aggressive() -> MaintenanceConfig:
        """Create aggressive maintenance configuration"""
        return MaintenanceConfig(
            mode=MaintenanceMode.AGGRESSIVE,
            description="Aggressive maintenance for demonstrations"
        )
    
    @staticmethod
    def create_ultra_aggressive() -> MaintenanceConfig:
        """Create ultra-aggressive maintenance configuration"""
        return MaintenanceConfig(
            mode=MaintenanceMode.ULTRA_AGGRESSIVE,
            description="Ultra-aggressive maintenance for maximum work order generation"
        )
    
    @staticmethod
    def create_custom(**kwargs) -> MaintenanceConfig:
        """Create custom maintenance configuration"""
        config = MaintenanceConfig(mode=MaintenanceMode.CUSTOM, **kwargs)
        return config


# Example usage and testing
if __name__ == "__main__":
    print("Maintenance Configuration System")
    print("=" * 50)
    
    # Test different configurations
    configs = {
        "Conservative": MaintenanceConfigFactory.create_conservative(),
        "Aggressive": MaintenanceConfigFactory.create_aggressive(),
        "Ultra-Aggressive": MaintenanceConfigFactory.create_ultra_aggressive()
    }
    
    for name, config in configs.items():
        summary = config.get_summary()
        print(f"\n{name} Configuration:")
        print(f"  Mode: {summary['mode']}")
        print(f"  Threshold Multiplier: {summary['global_settings']['threshold_multiplier']}")
        print(f"  Cooldown Reduction: {summary['global_settings']['cooldown_reduction_factor']}")
        print(f"  Check Interval Multiplier: {summary['global_settings']['check_interval_multiplier']}")
        print(f"  Component Types: {len(summary['component_types_configured'])}")
        print(f"  Total Thresholds: {summary['total_thresholds']}")
        
        # Validate
        errors = config.validate_configuration()
        print(f"  Validation: {'PASSED' if not errors else f'FAILED ({len(errors)} errors)'}")
    
    print(f"\nMaintenance configuration system ready!")
