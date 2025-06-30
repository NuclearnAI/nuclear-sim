"""
Realistic Maintenance Test Composer

This module provides a simplified composer that creates nuclear plant configurations
with realistic industry-standard maintenance thresholds and targeted initial conditions
to trigger specific maintenance actions through natural degradation.
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

# Import initial conditions catalog
from ..initial_conditions import get_initial_conditions_catalog


class ComprehensiveComposer:
    """
    Main composer for creating realistic maintenance test configurations
    
    This composer creates configurations with realistic industry-standard maintenance
    thresholds and applies targeted initial conditions to trigger specific maintenance actions.
    """
    
    def __init__(self):
        """Initialize the comprehensive composer"""
        self.catalog = get_maintenance_catalog()
        self.initial_conditions_catalog = get_initial_conditions_catalog()
        
        # Load the comprehensive config template (now contains realistic thresholds)
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
            "motor_inspection": "feedwater",
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
        
        print(f"✅ Comprehensive Composer Initialized")
        print(f"   🎯 Action-subsystem mappings: {len(self.action_subsystem_map)}")
        print(f"   📋 Maintenance catalog: {len(self.catalog.actions)} actions")
        print(f"   📄 Base config loaded with realistic thresholds")
    
    def compose_action_test_scenario(
        self,
        target_action: str,
        duration_hours: float = 2.0,
        plant_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a realistic maintenance test scenario with targeted initial conditions
        
        Args:
            target_action: Maintenance action to target (e.g., "oil_top_off")
            duration_hours: Simulation duration
            plant_name: Optional plant name
            
        Returns:
            Complete comprehensive configuration dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if plant_name is None:
            plant_name = f"{target_action.replace('_', ' ').title()} Test Plant"
        
        plant_id = f"{target_action.upper()}-TEST-{timestamp}"
        
        print(f"🔧 Composing realistic test scenario for: {target_action}")
        
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
        
        print(f"   🎯 Target subsystem: {target_subsystem}")
        print(f"   ⏱️ Duration: {duration_hours} hours")
        
        # 3. Start with a deep copy of the base config (already has realistic thresholds)
        config = copy.deepcopy(self.base_config)
        
        # 4. Update plant identification (keep at top level)
        config['plant_name'] = plant_name
        config['plant_id'] = plant_id
        config['description'] = f"Realistic maintenance test scenario for {target_action}"
        
        # 5. Update simulation configuration
        config['simulation_config']['duration_hours'] = duration_hours
        config['simulation_config']['scenario'] = f"{target_action}_test"
        
        # 6. Ensure primary_system structure is preserved
        # The template should have primary system parameters under primary_system key
        # If they're at top level, move them to primary_system
        
        # 6. Add load profile for the test scenario
        if 'load_profiles' not in config:
            config['load_profiles'] = {'profiles': {}}
        
        config['load_profiles']['profiles'][f"{target_action}_test"] = {
            'type': 'steady_with_noise',
            'base_power_percent': 90.0,
            'noise_std_percent': 2.0,
            'description': f"Steady operation for {target_action} testing"
        }
        
        # 7. Apply targeted initial conditions to trigger the specific action
        self._apply_targeted_initial_conditions(config, target_action)
        
        # 8. Update metadata with enhanced information for state manager integration
        config['metadata'] = {
            'created_date': datetime.now().strftime("%Y-%m-%d"),
            'created_by': "Realistic Maintenance Composer",
            'configuration_type': "realistic_maintenance_test",
            'target_action': target_action,
            'target_subsystem': target_subsystem,
            'validation_status': "generated",
            'last_modified': datetime.now().strftime("%Y-%m-%d"),
            'version_notes': f"Generated for testing {target_action} with realistic thresholds and targeted initial conditions",
            'base_template': "nuclear_plant_comprehensive_config.yaml",
            # NEW: Add state manager configuration flags
            'state_manager_integration': True,
            'maintenance_monitoring_enabled': True,
            'threshold_verification_enabled': True
        }
        
        # 9. Ensure maintenance_system section is preserved from template
        # The template already has realistic industry-standard thresholds
        if 'maintenance_system' not in config:
            print(f"   ⚠️ Warning: maintenance_system section missing from template")
        else:
            maintenance_system = config['maintenance_system']
            print(f"   ✅ Preserved maintenance_system with {len(maintenance_system.get('component_configs', {}))} component configs")
            
            # Verify the target subsystem has maintenance configuration
            component_configs = maintenance_system.get('component_configs', {})
            if target_subsystem in component_configs:
                target_config = component_configs[target_subsystem]
                thresholds = target_config.get('thresholds', {})
                print(f"   🎯 Target subsystem '{target_subsystem}' has {len(thresholds)} maintenance thresholds")
            else:
                print(f"   ⚠️ Warning: Target subsystem '{target_subsystem}' not found in maintenance configs")
        
        print(f"✅ Generated realistic test config for {target_action}")
        print(f"   📊 Total sections: {len(config)}")
        
        return config
    
    def _apply_targeted_initial_conditions(self, config: Dict[str, Any], target_action: str):
        """
        Apply targeted initial conditions to trigger the specific maintenance action
        
        Args:
            config: Configuration dictionary to modify
            target_action: Maintenance action to target
        """
        print(f"   🎯 Applying targeted initial conditions for {target_action}")
        
        target_subsystem = self.action_subsystem_map.get(target_action)
        if not target_subsystem:
            print(f"   ⚠️ No subsystem mapping found for {target_action}")
            return
        
        # Get initial conditions from catalog
        conditions = self.initial_conditions_catalog.get_conditions(target_subsystem, target_action)
        if not conditions:
            print(f"   ⚠️ No initial conditions found for {target_subsystem}.{target_action}")
            return
        
        # Apply conditions to the appropriate subsystem configuration
        self._apply_conditions_to_config(config, target_subsystem, conditions)
        
        # Count applied parameters (exclude metadata)
        condition_params = {k: v for k, v in conditions.items() 
                          if k not in ['description', 'safety_notes', 'threshold_info']}
        
        print(f"   ✅ Applied {len(condition_params)} targeted initial conditions for {target_subsystem}.{target_action}")
        if 'description' in conditions:
            print(f"   📝 {conditions['description']}")
    
    def _apply_conditions_to_config(self, config: Dict[str, Any], subsystem: str, conditions: Dict[str, Any]):
        """
        Apply initial conditions to the appropriate subsystem configuration
        
        Args:
            config: Configuration dictionary to modify
            subsystem: Target subsystem name
            conditions: Initial conditions to apply
        """
        # Get the subsystem configuration path
        if subsystem in ["feedwater", "turbine", "steam_generator", "condenser"]:
            subsystem_config = config.get('secondary_system', {}).get(subsystem, {})
            if not subsystem_config:
                print(f"   ⚠️ Warning: Subsystem '{subsystem}' not found in secondary_system")
                return
        else:
            # For other subsystems, try to find them in the config
            subsystem_config = config.get(subsystem, {})
            if not subsystem_config:
                print(f"   ⚠️ Warning: Subsystem '{subsystem}' not found in config")
                return
        
        # Get initial_conditions section
        initial_conditions = subsystem_config.get('initial_conditions', {})
        if not initial_conditions:
            print(f"   ⚠️ Warning: No initial_conditions section found for {subsystem}")
            return
        
        # Apply all condition parameters (skip metadata fields)
        applied_count = 0
        for param, value in conditions.items():
            if param not in ['description', 'safety_notes', 'threshold_info']:
                if param in initial_conditions:
                    initial_conditions[param] = value
                    print(f"     🔧 {subsystem}.{param} = {value}")
                    applied_count += 1
                else:
                    print(f"     ⚠️ Parameter '{param}' not found in {subsystem} initial_conditions")
        
        print(f"   ✅ Applied {applied_count} parameters to {subsystem}")
    
    def _ensure_primary_system_structure(self, config: Dict[str, Any]):
        """
        Ensure primary system parameters are properly nested under primary_system key
        
        This fixes the YAML formatting issue where primary system parameters were at the top level
        instead of being properly nested under a primary_system section.
        
        Args:
            config: Configuration dictionary to restructure
        """
        # Define primary system parameters that should be moved under primary_system
        primary_system_params = {
            'thermal_power_mw',
            'electrical_power_mw', 
            'num_loops',
            'steam_generators_per_loop',
            'steam_pressure_mpa',
            'steam_temperature_c',
            'total_steam_flow_kgs',
            'feedwater_temperature_c',
            'minimum_power_fraction',
            'maximum_power_fraction',
            'normal_operating_efficiency',
            'design_efficiency',
            'enable_load_following',
            'enable_chemistry_tracking',
            'enable_maintenance_tracking',
            'enable_performance_monitoring',
            'enable_predictive_analytics',
            'enable_system_coordination'
        }
        
        # Check if any primary system parameters are at the top level
        top_level_primary_params = {key: value for key, value in config.items() 
                                  if key in primary_system_params}
        
        if top_level_primary_params:
            print(f"   🔧 Restructuring {len(top_level_primary_params)} primary system parameters")
            
            # Create primary_system section if it doesn't exist
            if 'primary_system' not in config:
                config['primary_system'] = {}
            
            # Move parameters from top level to primary_system
            for param_name, param_value in top_level_primary_params.items():
                config['primary_system'][param_name] = param_value
                # Remove from top level
                del config[param_name]
                print(f"   � Moved {param_name} to primary_system")
            
            print(f"   ✅ Primary system restructuring complete")
        else:
            print(f"   ✅ Primary system structure already correct")
    
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
    
# Convenience functions for easy usage
def create_action_test_config(target_action: str, duration_hours: float = 2.0) -> Dict[str, Any]:
    """
    Convenience function to create a realistic maintenance test configuration
    
    Args:
        target_action: Maintenance action to target
        duration_hours: Simulation duration
        
    Returns:
        Complete configuration dictionary
    """
    composer = ComprehensiveComposer()
    return composer.compose_action_test_scenario(target_action, duration_hours)


def save_action_test_config(target_action: str, duration_hours: float = 2.0,
                           output_dir: Optional[str] = None) -> Path:
    """
    Convenience function to create and save a realistic maintenance test configuration
    
    Args:
        target_action: Maintenance action to target
        duration_hours: Simulation duration
        output_dir: Output directory for config file
        
    Returns:
        Path to saved configuration file
    """
    composer = ComprehensiveComposer()
    config = composer.compose_action_test_scenario(target_action, duration_hours)
    return composer.save_config(config, f"{target_action}_test", output_dir)


# Example usage
if __name__ == "__main__":
    print("Realistic Maintenance Test Composer")
    print("=" * 50)
    
    composer = ComprehensiveComposer()
    
    # List available actions
    print("Available maintenance actions:")
    actions = composer.list_available_actions()
    for i, action in enumerate(actions[:10]):  # Show first 10
        print(f"  {i+1}. {action}")
    print(f"  ... and {len(actions) - 10} more")
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
        # Example 1: Oil top off test
        config1 = composer.compose_action_test_scenario("oil_top_off", 2.0)
        config_file1 = composer.save_config(config1, "oil_top_off_test")
        print(f"✅ Oil top off test config saved to: {config_file1}")
        
        # Example 2: Vibration analysis test
        config2 = composer.compose_action_test_scenario("vibration_analysis", 3.0)
        config_file2 = composer.save_config(config2, "vibration_analysis_test")
        print(f"✅ Vibration analysis test config saved to: {config_file2}")
        
        # Example 3: TSP cleaning test
        config3 = composer.compose_action_test_scenario("tsp_chemical_cleaning", 4.0)
        config_file3 = composer.save_config(config3, "tsp_cleaning_test")
        print(f"✅ TSP cleaning test config saved to: {config_file3}")
        
        print("\n📊 Example configuration summary:")
        print(f"   All configs use realistic industry-standard thresholds")
        print(f"   Initial conditions are targeted to trigger specific actions")
        print(f"   Natural degradation during simulation triggers maintenance")
        
    except Exception as e:
        print(f"❌ Error generating examples: {e}")
        import traceback
        traceback.print_exc()
