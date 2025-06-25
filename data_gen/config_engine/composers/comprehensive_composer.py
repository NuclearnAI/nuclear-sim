"""
Comprehensive Configuration Composer - Subsystem-Specific Maintenance Modes

This module provides the main composer that creates nuclear plant configurations
with subsystem-specific maintenance modes for precise targeting of maintenance actions.
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict
import copy

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import maintenance system
from systems.maintenance.maintenance_actions import (
    MaintenanceActionType,
    get_maintenance_catalog
)


class ComprehensiveComposer:
    """
    Main composer for creating subsystem-specific maintenance mode configurations
    
    This composer creates configurations where each subsystem can be independently
    configured with different maintenance modes (ultra_aggressive, aggressive, 
    conservative, quiet, disabled) for precise targeting of maintenance actions.
    """
    
    def __init__(self):
        """Initialize the comprehensive composer"""
        self.catalog = get_maintenance_catalog()
        
        # Load the comprehensive config template
        template_path = Path(__file__).parent.parent / "templates" / "nuclear_plant_comprehensive_config.yaml"
        try:
            with open(template_path, 'r') as f:
                self.base_config = yaml.safe_load(f)
            print(f"✅ Loaded comprehensive config template from {template_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Comprehensive config template not found at {template_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing comprehensive config template: {e}")
        
        # Action to subsystem mapping
        self.action_subsystem_map = {
            # Steam Generator Actions
            "tsp_chemical_cleaning": "steam_generator",
            "tsp_mechanical_cleaning": "steam_generator",
            "scale_removal": "steam_generator",
            "moisture_separator_maintenance": "steam_generator",
            "secondary_side_cleaning": "steam_generator",
            "steam_dryer_cleaning": "steam_generator",
            "water_chemistry_adjustment": "steam_generator",
            "tube_bundle_inspection": "steam_generator",
            "eddy_current_testing": "steam_generator",
            "tube_sheet_inspection": "steam_generator",
            
            # Turbine Actions
            "turbine_bearing_inspection": "turbine",
            "turbine_bearing_replacement": "turbine",
            "bearing_clearance_check": "turbine",
            "bearing_alignment": "turbine",
            "thrust_bearing_adjustment": "turbine",
            "turbine_oil_change": "turbine",
            "turbine_oil_top_off": "turbine",
            "oil_filter_replacement": "turbine",
            "oil_cooler_cleaning": "turbine",
            "lubrication_system_test": "turbine",
            "rotor_inspection": "turbine",
            "thermal_bow_correction": "turbine",
            "critical_speed_test": "turbine",
            "overspeed_test": "turbine",
            "vibration_monitoring_calibration": "turbine",
            "dynamic_balancing": "turbine",
            "turbine_performance_test": "turbine",
            "turbine_protection_test": "turbine",
            "thermal_stress_analysis": "turbine",
            "turbine_system_optimization": "turbine",
            "vibration_analysis": "turbine",
            "efficiency_analysis": "turbine",
            
            # Feedwater Actions
            "oil_top_off": "feedwater",
            "oil_change": "feedwater",
            "pump_inspection": "feedwater",
            "impeller_inspection": "feedwater",
            "impeller_replacement": "feedwater",
            "bearing_replacement": "feedwater",
            "seal_replacement": "feedwater",
            "bearing_inspection": "feedwater",
            "seal_inspection": "feedwater",
            "coupling_alignment": "feedwater",
            "pump_alignment_check": "feedwater",
            "npsh_analysis": "feedwater",
            "cavitation_analysis": "feedwater",
            "suction_system_check": "feedwater",
            "discharge_system_inspection": "feedwater",
            "flow_system_inspection": "feedwater",
            "flow_control_inspection": "feedwater",
            "lubrication_system_check": "feedwater",
            "cooling_system_check": "feedwater",
            "component_overhaul": "feedwater",
            
            # Condenser Actions
            "condenser_tube_cleaning": "condenser",
            "condenser_tube_plugging": "condenser",
            "condenser_tube_inspection": "condenser",
            "condenser_biofouling_removal": "condenser",
            "condenser_scale_removal": "condenser",
            "condenser_chemical_cleaning": "condenser",
            "condenser_mechanical_cleaning": "condenser",
            "condenser_hydroblast_cleaning": "condenser",
            "condenser_water_treatment": "condenser",
            "condenser_performance_test": "condenser",
            "vacuum_ejector_cleaning": "condenser",
            "vacuum_ejector_nozzle_replacement": "condenser",
            "vacuum_ejector_inspection": "condenser",
            "vacuum_system_test": "condenser",
            "vacuum_leak_detection": "condenser",
            "intercondenser_cleaning": "condenser",
            "aftercondenser_cleaning": "condenser",
            "motive_steam_system_check": "condenser",
            "vacuum_system_check": "condenser",
        }
        
        # Subsystem maintenance modes
        self.subsystem_modes = {
            "ultra_aggressive": {
                "threshold_multiplier": 20.0,
                "cooldown_hours": 0.1,
                "check_interval_hours": 0.05
            },
            "aggressive": {
                "threshold_multiplier": 10.0,
                "cooldown_hours": 0.5,
                "check_interval_hours": 0.1
            },
            "conservative": {
                "threshold_multiplier": 1.0,
                "cooldown_hours": 24.0,
                "check_interval_hours": 4.0
            },
            "quiet": {
                "threshold_multiplier": 0.1,
                "cooldown_hours": 168.0,
                "check_interval_hours": 24.0
            },
            "disabled": {
                "check_interval_hours": 9999.0,
                "thresholds": {}
            }
        }
        
        print(f"✅ Comprehensive Composer Initialized")
        print(f"   🎯 Action-subsystem mappings: {len(self.action_subsystem_map)}")
        print(f"   📋 Maintenance catalog: {len(self.catalog.actions)} actions")
        print(f"   🔧 Subsystem modes: {list(self.subsystem_modes.keys())}")
        print(f"   📄 Base config loaded with {len(self.base_config)} top-level sections")
    
    def compose_action_test_scenario(
        self,
        target_action: str,
        subsystem_modes: Dict[str, str],
        duration_hours: float = 2.0,
        plant_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a scenario with subsystem-specific maintenance modes
        
        Args:
            target_action: Maintenance action to target (e.g., "oil_top_off")
            subsystem_modes: Dict mapping subsystem to mode
                            {"feedwater": "aggressive", "steam_generator": "conservative", 
                             "turbine": "quiet", "condenser": "disabled"}
            duration_hours: Simulation duration
            plant_name: Optional plant name
            
        Returns:
            Complete comprehensive configuration dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if plant_name is None:
            plant_name = f"{target_action.replace('_', ' ').title()} Test Plant"
        
        plant_id = f"{target_action.upper()}-TEST-{timestamp}"
        
        print(f"🔧 Composing subsystem-specific scenario for: {target_action}")
        
        # 1. Validate action exists in catalog
        try:
            action_type = MaintenanceActionType(target_action)
            action_metadata = self.catalog.get_action_metadata(action_type)
            if not action_metadata:
                raise ValueError(f"No metadata found for action: {target_action}")
        except ValueError as e:
            raise ValueError(f"Unknown maintenance action: {target_action}") from e
        
        # 2. Determine target subsystem
        target_subsystem = self.action_subsystem_map.get(target_action)
        if not target_subsystem:
            raise ValueError(f"No subsystem mapping found for action: {target_action}")
        
        # 3. Validate subsystem modes
        all_subsystems = ["steam_generator", "turbine", "feedwater", "condenser"]
        for subsystem, mode in subsystem_modes.items():
            if subsystem not in all_subsystems:
                raise ValueError(f"Unknown subsystem: {subsystem}")
            if mode not in self.subsystem_modes:
                raise ValueError(f"Unknown mode: {mode}")
        
        print(f"   🎯 Target subsystem: {target_subsystem}")
        print(f"   ⏱️ Duration: {duration_hours} hours")
        print(f"   🔧 Subsystem modes: {subsystem_modes}")
        
        # 4. Start with a deep copy of the base config
        config = copy.deepcopy(self.base_config)
        
        # 5. Update plant identification
        config['plant_name'] = plant_name
        config['plant_id'] = plant_id
        config['description'] = f"Subsystem-specific test scenario for {target_action}"
        
        # 6. Update simulation configuration
        config['simulation_config']['duration_hours'] = duration_hours
        config['simulation_config']['scenario'] = f"{target_action}_subsystem_test"
        
        # 7. Add load profile for the test scenario
        if 'load_profiles' not in config:
            config['load_profiles'] = {'profiles': {}}
        
        config['load_profiles']['profiles'][f"{target_action}_subsystem_test"] = {
            'type': 'steady_with_noise',
            'base_power_percent': 90.0,
            'noise_std_percent': 2.0,
            'description': f"Steady operation for {target_action} subsystem testing"
        }
        
        # 8. Generate maintenance system configuration (single path)
        config['maintenance_system'] = self._generate_maintenance_system_config(
            target_action, subsystem_modes
        )
        
        # 9. Remove individual subsystem maintenance configs (clean single path)
        self._remove_individual_subsystem_maintenance_configs(config)
        
        # 10. Apply initial degradation for target subsystem only
        self._apply_initial_degradation(config, target_action, target_subsystem, subsystem_modes)
        
        # 11. Update metadata
        config['metadata'] = {
            'created_date': datetime.now().strftime("%Y-%m-%d"),
            'created_by': "Subsystem-Specific Composer",
            'configuration_type': "subsystem_specific_test",
            'target_action': target_action,
            'target_subsystem': target_subsystem,
            'subsystem_modes': subsystem_modes,
            'validation_status': "generated",
            'last_modified': datetime.now().strftime("%Y-%m-%d"),
            'version_notes': f"Generated for testing {target_action} with subsystem-specific modes",
            'base_template': "nuclear_plant_comprehensive_config.yaml"
        }
        
        print(f"✅ Generated subsystem-specific config for {target_action}")
        print(f"   📊 Total sections: {len(config)}")
        
        return config
    
    def _generate_maintenance_system_config(self, target_action: str, subsystem_modes: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate maintenance_system configuration with subsystem-specific modes
        
        Args:
            target_action: Maintenance action to target
            subsystem_modes: Dict mapping subsystem to mode
            
        Returns:
            Dictionary with complete maintenance_system configuration
        """
        maintenance_config = {
            'maintenance_mode': 'subsystem_specific',
            'maintenance_auto_execute': True,
            'component_configs': {}
        }
        
        # Configure each subsystem according to its specified mode
        for subsystem, mode in subsystem_modes.items():
            mode_config = self.subsystem_modes[mode]
            
            if mode == 'disabled':
                # Disabled subsystem
                maintenance_config['component_configs'][subsystem] = {
                    'mode': mode,
                    'check_interval_hours': 9999.0,
                    'thresholds': {}
                }
            else:
                # Active subsystem with specific mode
                maintenance_config['component_configs'][subsystem] = {
                    'mode': mode,
                    'check_interval_hours': mode_config['check_interval_hours'],
                    'threshold_multiplier': mode_config['threshold_multiplier'],
                    'cooldown_hours': mode_config['cooldown_hours'],
                    'thresholds': self._get_thresholds_for_subsystem_action(
                        subsystem, target_action, mode_config
                    )
                }
        
        return maintenance_config
    
    def _get_thresholds_for_subsystem_action(self, subsystem: str, target_action: str, mode_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get maintenance thresholds for subsystem and action with mode-specific adjustments
        
        Args:
            subsystem: Subsystem name
            target_action: Target maintenance action
            mode_config: Mode configuration with multipliers
            
        Returns:
            Dictionary of thresholds for the subsystem
        """
        thresholds = {}
        
        # Get base thresholds for subsystem
        base_thresholds = self._get_base_thresholds_for_subsystem(subsystem)
        
        # Apply mode-specific adjustments
        threshold_multiplier = mode_config.get('threshold_multiplier', 1.0)
        cooldown_hours = mode_config.get('cooldown_hours', 24.0)
        
        for param_name, base_threshold in base_thresholds.items():
            # Apply threshold multiplier based on comparison type
            if base_threshold['comparison'] == 'greater_than':
                # For "greater than" thresholds, divide to make more sensitive
                adjusted_threshold = base_threshold['threshold'] / threshold_multiplier
            else:
                # For "less than" thresholds, divide to make more sensitive (lower threshold triggers sooner)
                adjusted_threshold = base_threshold['threshold'] / threshold_multiplier
            
            # Special handling for target action
            if base_threshold['action'] == target_action:
                # Make target action even more sensitive
                if base_threshold['comparison'] == 'greater_than':
                    adjusted_threshold = adjusted_threshold / 2.0
                else:
                    adjusted_threshold = adjusted_threshold * 2.0
                priority = 'HIGH'
            else:
                priority = base_threshold.get('priority', 'MEDIUM')
            
            thresholds[param_name] = {
                'threshold': adjusted_threshold,
                'comparison': base_threshold['comparison'],
                'action': base_threshold['action'],
                'cooldown_hours': cooldown_hours,
                'priority': priority
            }
        
        return thresholds
    
    def _get_base_thresholds_for_subsystem(self, subsystem: str) -> Dict[str, Any]:
        """Get base maintenance thresholds for a subsystem"""
        
        if subsystem == "steam_generator":
            return {
                'tsp_fouling_fraction': {
                    'threshold': 0.10,
                    'comparison': 'greater_than',
                    'action': 'tsp_chemical_cleaning',
                    'priority': 'HIGH'
                },
                'tube_wall_temperature': {
                    'threshold': 320.0,
                    'comparison': 'greater_than',
                    'action': 'scale_removal',
                    'priority': 'HIGH'
                },
                'steam_quality': {
                    'threshold': 0.995,
                    'comparison': 'less_than',
                    'action': 'moisture_separator_maintenance',
                    'priority': 'MEDIUM'
                },
                'efficiency': {
                    'threshold': 0.95,
                    'comparison': 'less_than',
                    'action': 'secondary_side_cleaning',
                    'priority': 'MEDIUM'
                }
            }
        
        elif subsystem == "turbine":
            return {
                'efficiency': {
                    'threshold': 0.90,
                    'comparison': 'less_than',
                    'action': 'efficiency_analysis',
                    'priority': 'MEDIUM'
                },
                'vibration_level': {
                    'threshold': 20.0,
                    'comparison': 'greater_than',
                    'action': 'vibration_analysis',
                    'priority': 'HIGH'
                },
                'bearing_temperature': {
                    'threshold': 110.0,
                    'comparison': 'greater_than',
                    'action': 'turbine_bearing_inspection',
                    'priority': 'HIGH'
                },
                'oil_contamination_level': {
                    'threshold': 15.0,
                    'comparison': 'greater_than',
                    'action': 'turbine_oil_change',
                    'priority': 'MEDIUM'
                }
            }
        
        elif subsystem == "feedwater":
            return {
                'oil_level': {
                    'threshold': 70.0,
                    'comparison': 'less_than',
                    'action': 'oil_top_off',
                    'priority': 'HIGH'
                },
                'oil_contamination_level': {
                    'threshold': 15.0,
                    'comparison': 'greater_than',
                    'action': 'oil_change',
                    'priority': 'MEDIUM'
                },
                'vibration_level': {
                    'threshold': 20.0,
                    'comparison': 'greater_than',
                    'action': 'vibration_analysis',
                    'priority': 'HIGH'
                },
                'bearing_temperature': {
                    'threshold': 110.0,
                    'comparison': 'greater_than',
                    'action': 'bearing_inspection',
                    'priority': 'HIGH'
                },
                'efficiency_degradation_factor': {
                    'threshold': 0.85,
                    'comparison': 'less_than',
                    'action': 'pump_inspection',
                    'priority': 'MEDIUM'
                }
            }
        
        elif subsystem == "condenser":
            return {
                'vacuum_level': {
                    'threshold': 85.0,
                    'comparison': 'less_than',
                    'action': 'vacuum_system_check',
                    'priority': 'MEDIUM'
                },
                'tube_cleanliness': {
                    'threshold': 0.80,
                    'comparison': 'less_than',
                    'action': 'condenser_tube_cleaning',
                    'priority': 'MEDIUM'
                },
                'heat_rejection_efficiency': {
                    'threshold': 0.85,
                    'comparison': 'less_than',
                    'action': 'condenser_performance_test',
                    'priority': 'MEDIUM'
                },
                'fouling_resistance': {
                    'threshold': 0.001,
                    'comparison': 'greater_than',
                    'action': 'condenser_chemical_cleaning',
                    'priority': 'HIGH'
                }
            }
        
        return {}
    
    def _remove_individual_subsystem_maintenance_configs(self, config: Dict[str, Any]):
        """Remove individual subsystem maintenance configs to enforce single path"""
        
        # Remove maintenance sections from individual subsystem configs
        subsystem_paths = [
            ['secondary_system', 'steam_generator'],
            ['secondary_system', 'turbine'],
            ['secondary_system', 'feedwater'],
            ['secondary_system', 'condenser'],
            ['steam_generator'],
            ['turbine'],
            ['feedwater'],
            ['condenser']
        ]
        
        for path in subsystem_paths:
            subsystem_config = config
            for key in path:
                if key in subsystem_config:
                    subsystem_config = subsystem_config[key]
                else:
                    break
            else:
                # Successfully navigated to subsystem config
                if 'maintenance' in subsystem_config:
                    del subsystem_config['maintenance']
                    print(f"   🧹 Removed maintenance config from {'.'.join(path)}")
    
    def _apply_initial_degradation(self, config: Dict[str, Any], target_action: str, 
                                 target_subsystem: str, subsystem_modes: Dict[str, str]):
        """Apply initial degradation only for subsystems that need it"""
        
        if 'initial_degradation' not in config:
            config['initial_degradation'] = {}
        
        # Only apply degradation to subsystems that are not disabled
        for subsystem, mode in subsystem_modes.items():
            if mode != 'disabled':
                self._apply_subsystem_degradation(config, subsystem, target_action, mode)
    
    def _apply_subsystem_degradation(self, config: Dict[str, Any], subsystem: str, 
                                   target_action: str, mode: str):
        """Apply degradation for a specific subsystem"""
        
        # Get mode-specific degradation intensity
        mode_config = self.subsystem_modes[mode]
        intensity = mode_config.get('threshold_multiplier', 1.0)
        
        if subsystem == "steam_generator":
            if target_action == "tsp_chemical_cleaning":
                config['initial_degradation']['steam_generator_tsp_fouling_fraction'] = 0.08 * intensity
            elif target_action == "scale_removal":
                config['initial_degradation']['steam_generator_tube_wall_temperature'] = 315.0 + (5.0 * intensity)
            elif target_action == "moisture_separator_maintenance":
                config['initial_degradation']['steam_generator_steam_quality'] = 0.992 - (0.001 * intensity)
        
        elif subsystem == "turbine":
            if "bearing" in target_action:
                config['initial_degradation']['turbine_bearing_temperature'] = 105.0 + (2.0 * intensity)
                config['initial_degradation']['turbine_vibration_level'] = 18.0 + (1.0 * intensity)
            elif "oil" in target_action:
                if target_action == "turbine_oil_top_off":
                    config['initial_degradation']['turbine_oil_level'] = 35.0 - (5.0 * intensity)
                elif target_action == "turbine_oil_change":
                    config['initial_degradation']['turbine_oil_contamination'] = 12.0 + (2.0 * intensity)
            elif "vibration" in target_action:
                config['initial_degradation']['turbine_vibration_level'] = 18.0 + (1.0 * intensity)
            elif "efficiency" in target_action:
                config['initial_degradation']['turbine_efficiency'] = 0.315 - (0.01 * intensity)
        
        elif subsystem == "feedwater":
            if target_action == "oil_top_off":
                # Set oil level to a low value that will trigger the threshold
                # For ultra_aggressive (intensity=20): 35.0 - 5.0*20 = -65.0 (bad!)
                # Fixed: Use realistic low oil level that will trigger 7.0% threshold
                config['initial_degradation']['feedwater_pump_oil_level'] = max(5.0, 35.0 - (1.5 * intensity))
            elif target_action == "oil_change":
                config['initial_degradation']['feedwater_pump_oil_contamination'] = 85.0 + (5.0 * intensity)
            elif "bearing" in target_action:
                config['initial_degradation']['feedwater_pump_bearing_temperature'] = 105.0 + (2.0 * intensity)
            elif "vibration" in target_action:
                config['initial_degradation']['feedwater_pump_vibration_level'] = 18.0 + (1.0 * intensity)
        
        elif subsystem == "condenser":
            if "tube_cleaning" in target_action:
                config['initial_degradation']['condenser_tube_fouling_resistance'] = 0.0018 + (0.0002 * intensity)
            elif "vacuum" in target_action:
                config['initial_degradation']['condenser_vacuum_efficiency'] = 0.82 - (0.02 * intensity)
    
    # Helper methods for easy usage
    def create_single_target_scenario(self, target_action: str, target_mode: str = "aggressive") -> Dict[str, Any]:
        """Helper for single subsystem targeting"""
        target_subsystem = self.action_subsystem_map[target_action]
        
        subsystem_modes = {
            "steam_generator": "disabled",
            "turbine": "disabled", 
            "feedwater": "disabled",
            "condenser": "disabled"
        }
        subsystem_modes[target_subsystem] = target_mode
        
        return self.compose_action_test_scenario(target_action, subsystem_modes)
    
    def create_focused_scenario(self, target_action: str, target_mode: str = "aggressive", 
                              background_mode: str = "quiet") -> Dict[str, Any]:
        """Helper for focused targeting with quiet background"""
        target_subsystem = self.action_subsystem_map[target_action]
        
        subsystem_modes = {
            "steam_generator": background_mode,
            "turbine": background_mode,
            "feedwater": background_mode, 
            "condenser": background_mode
        }
        subsystem_modes[target_subsystem] = target_mode
        
        return self.compose_action_test_scenario(target_action, subsystem_modes)
    
    def save_config(self, config: Dict[str, Any], filename: str, output_dir: Optional[str] = None) -> Path:
        """Save configuration to YAML file"""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "generated_configs"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp if not provided
        if not filename.endswith('.yaml'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}.yaml"
        
        filepath = output_dir / filename
        
        # Save configuration
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"💾 Saved configuration to {filepath}")
        return filepath
    
    def list_available_actions(self) -> List[str]:
        """List all available maintenance actions"""
        return list(self.action_subsystem_map.keys())
    
    def get_actions_by_subsystem(self, subsystem: str) -> List[str]:
        """Get all actions for a specific subsystem"""
        return [action for action, sub in self.action_subsystem_map.items() if sub == subsystem]
    
    def list_available_modes(self) -> List[str]:
        """List all available subsystem modes"""
        return list(self.subsystem_modes.keys())


# Convenience functions for easy usage
def create_single_target_config(target_action: str, target_mode: str = "aggressive", 
                               duration_hours: float = 2.0) -> Dict[str, Any]:
    """
    Convenience function to create a single-target configuration
    
    Args:
        target_action: Maintenance action to target
        target_mode: Mode for target subsystem
        duration_hours: Simulation duration
        
    Returns:
        Complete configuration dictionary
    """
    composer = ComprehensiveComposer()
    return composer.create_single_target_scenario(target_action, target_mode)


def create_focused_config(target_action: str, target_mode: str = "aggressive", 
                         background_mode: str = "quiet", duration_hours: float = 2.0) -> Dict[str, Any]:
    """
    Convenience function to create a focused configuration
    
    Args:
        target_action: Maintenance action to target
        target_mode: Mode for target subsystem
        background_mode: Mode for other subsystems
        duration_hours: Simulation duration
        
    Returns:
        Complete configuration dictionary
    """
    composer = ComprehensiveComposer()
    return composer.create_focused_scenario(target_action, target_mode, background_mode)


def save_single_target_config(target_action: str, target_mode: str = "aggressive",
                             output_dir: Optional[str] = None) -> Path:
    """
    Convenience function to create and save a single-target configuration
    
    Args:
        target_action: Maintenance action to target
        target_mode: Mode for target subsystem
        output_dir: Output directory for config file
        
    Returns:
        Path to saved configuration file
    """
    composer = ComprehensiveComposer()
    config = composer.create_single_target_scenario(target_action, target_mode)
    return composer.save_config(config, f"{target_action}_single_target", output_dir)


# Example usage
if __name__ == "__main__":
    print("Subsystem-Specific Maintenance Mode Composer")
    print("=" * 60)
    
    composer = ComprehensiveComposer()
    
    # List available actions and modes
    print("Available maintenance actions:")
    actions = composer.list_available_actions()
    for i, action in enumerate(actions[:10]):  # Show first 10
        print(f"  {i+1}. {action}")
    print(f"  ... and {len(actions) - 10} more")
    print()
    
    print("Available subsystem modes:")
    modes = composer.list_available_modes()
    for mode in modes:
        mode_config = composer.subsystem_modes[mode]
        print(f"  - {mode}: {mode_config}")
    print()
    
    # Show actions by subsystem
    for subsystem in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
        subsystem_actions = composer.get_actions_by_subsystem(subsystem)
        print(f"{subsystem.title()} actions ({len(subsystem_actions)}):")
        for action in subsystem_actions[:3]:  # Show first 3
            print(f"  - {action}")
        if len(subsystem_actions) > 3:
            print(f"  ... and {len(subsystem_actions) - 3} more")
        print()
    
    # Generate example configurations
    print("Generating example configurations...")
    
    try:
        # Example 1: Single target (feedwater aggressive, others disabled)
        config1 = composer.create_single_target_scenario("oil_top_off", "aggressive")
        config_file1 = composer.save_config(config1, "example_single_target")
        print(f"✅ Single target config saved to: {config_file1}")
        
        # Example 2: Focused (feedwater aggressive, others quiet)
        config2 = composer.create_focused_scenario("oil_top_off", "aggressive", "quiet")
        config_file2 = composer.save_config(config2, "example_focused")
        print(f"✅ Focused config saved to: {config_file2}")
        
        # Example 3: Custom subsystem modes
        custom_modes = {
            "feedwater": "ultra_aggressive",
            "steam_generator": "conservative",
            "turbine": "quiet",
            "condenser": "disabled"
        }
        config3 = composer.compose_action_test_scenario("oil_top_off", custom_modes)
        config_file3 = composer.save_config(config3, "example_custom")
        print(f"✅ Custom config saved to: {config_file3}")
        
        print("\n📊 Example configuration summary:")
        print(f"   Single target: Only feedwater aggressive, others disabled")
        print(f"   Focused: Feedwater aggressive, others quiet background")
        print(f"   Custom: Ultra-aggressive feedwater, mixed other modes")
        
    except Exception as e:
        print(f"❌ Error generating examples: {e}")
        import traceback
        traceback.print_exc()
