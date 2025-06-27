"""
Conditions injector for applying initial conditions to simulators.

This module handles the injection of generated initial conditions into
simulator configurations and running simulators.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import copy
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simulator.core.sim import NuclearPlantSimulator


class ConditionsInjector:
    """
    Injects initial conditions into simulator configurations and instances
    
    This class handles the application of generated initial conditions to
    both configuration dictionaries and running simulator instances.
    """
    
    def __init__(self):
        """Initialize conditions injector"""
        pass
    
    def inject_into_config(self, base_config: Dict[str, Any], 
                          initial_conditions: Dict[str, float]) -> Dict[str, Any]:
        """
        Inject initial conditions into a configuration dictionary
        
        Args:
            base_config: Base configuration dictionary
            initial_conditions: Dictionary mapping parameter names to values
            
        Returns:
            Modified configuration with initial conditions applied
        """
        # Create deep copy to avoid modifying original
        config = copy.deepcopy(base_config)
        
        print(f"INJECTOR: Injecting {len(initial_conditions)} initial conditions into config")
        
        # FIRST: Restructure primary system parameters to fix YAML formatting
        config = self._restructure_primary_system(config)
        
        # Group conditions by component and subsystem
        grouped_conditions = self._group_conditions_by_component(initial_conditions)
        
        for component_id, conditions in grouped_conditions.items():
            # Determine subsystem from component ID
            subsystem = self._determine_subsystem_from_component_id(component_id)
            
            if subsystem:
                # Inject into secondary_system section
                self._inject_into_subsystem_config(config, subsystem, component_id, conditions)
            else:
                print(f"INJECTOR: Warning - Could not determine subsystem for {component_id}")
        
        return config
    
    def _restructure_primary_system(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restructure configuration to move primary system parameters under primary_system key
        
        This fixes the YAML formatting issue where primary system parameters were at the top level
        instead of being properly nested under a primary_system section.
        
        Args:
            config: Configuration dictionary to restructure
            
        Returns:
            Restructured configuration with proper primary_system nesting
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
            print(f"INJECTOR: Restructuring {len(top_level_primary_params)} primary system parameters")
            
            # Create primary_system section if it doesn't exist
            if 'primary_system' not in config:
                config['primary_system'] = {}
            
            # Move parameters from top level to primary_system
            for param_name, param_value in top_level_primary_params.items():
                config['primary_system'][param_name] = param_value
                # Remove from top level
                del config[param_name]
                print(f"INJECTOR: Moved {param_name} to primary_system")
            
            print(f"INJECTOR: Primary system restructuring complete")
        else:
            print(f"INJECTOR: No primary system restructuring needed")
        
        return config
    
    def _group_conditions_by_component(self, initial_conditions: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        Group initial conditions by component ID
        
        Args:
            initial_conditions: Flat dictionary of parameter names to values
            
        Returns:
            Dictionary grouped by component ID
        """
        grouped = {}
        
        for full_param_name, value in initial_conditions.items():
            if '.' in full_param_name:
                component_id, param_name = full_param_name.split('.', 1)
                
                if component_id not in grouped:
                    grouped[component_id] = {}
                
                grouped[component_id][param_name] = value
            else:
                # Handle parameters without component prefix
                print(f"INJECTOR: Warning - Parameter {full_param_name} has no component prefix")
        
        return grouped
    
    def _determine_subsystem_from_component_id(self, component_id: str) -> Optional[str]:
        """
        Determine subsystem from component ID
        
        Args:
            component_id: Component identifier
            
        Returns:
            Subsystem name or None if not determinable
        """
        component_id_upper = component_id.upper()
        
        # Feedwater components
        if any(prefix in component_id_upper for prefix in ['FW', 'FEEDWATER', 'PUMP']):
            return 'feedwater'
        
        # Turbine components
        if any(prefix in component_id_upper for prefix in ['TB', 'TURB', 'TURBINE']):
            return 'turbine'
        
        # Steam generator components
        if any(prefix in component_id_upper for prefix in ['SG', 'STEAM']):
            return 'steam_generator'
        
        # Condenser components
        if any(prefix in component_id_upper for prefix in ['CD', 'COND', 'CONDENSER']):
            return 'condenser'
        
        return None
    
    def _inject_into_subsystem_config(self, config: Dict[str, Any], subsystem: str, 
                                    component_id: str, conditions: Dict[str, float]):
        """
        Inject conditions into a specific subsystem configuration
        
        Args:
            config: Configuration dictionary to modify
            subsystem: Subsystem name
            component_id: Component ID
            conditions: Conditions to inject
        """
        # Ensure secondary_system section exists
        if 'secondary_system' not in config:
            config['secondary_system'] = {}
        
        secondary_system = config['secondary_system']
        
        # Ensure subsystem section exists
        if subsystem not in secondary_system:
            secondary_system[subsystem] = {}
        
        subsystem_config = secondary_system[subsystem]
        
        # Ensure initial_conditions section exists
        if 'initial_conditions' not in subsystem_config:
            subsystem_config['initial_conditions'] = {}
        
        initial_conditions_section = subsystem_config['initial_conditions']
        
        # Inject conditions
        conditions_applied = 0
        for param_name, value in conditions.items():
            # Map parameter names to configuration format
            config_param_name = self._map_parameter_to_config_format(param_name, subsystem)
            
            if config_param_name:
                initial_conditions_section[config_param_name] = value
                conditions_applied += 1
                print(f"INJECTOR: {subsystem}.{config_param_name} = {value:.3f}")
            else:
                print(f"INJECTOR: Warning - Could not map parameter {param_name} for {subsystem}")
        
        print(f"INJECTOR: Applied {conditions_applied} conditions to {subsystem}")
    
    def _map_parameter_to_config_format(self, param_name: str, subsystem: str) -> Optional[str]:
        """
        Map parameter name to configuration format
        
        Args:
            param_name: Parameter name from threshold analysis
            subsystem: Target subsystem
            
        Returns:
            Configuration parameter name or None if not mappable
        """
        param_lower = param_name.lower()
        
        if subsystem == 'feedwater':
            # Feedwater parameter mappings
            if 'oil_level' in param_lower:
                return 'pump_oil_levels'  # Will be converted to list
            elif 'oil_contamination' in param_lower:
                return 'pump_oil_contamination'
            elif 'bearing_temperature' in param_lower:
                return 'bearing_temperatures'
            elif 'vibration' in param_lower:
                return 'pump_vibrations'
            elif 'efficiency' in param_lower:
                return 'pump_efficiencies'
        
        elif subsystem == 'turbine':
            # Turbine parameter mappings
            if 'oil_level' in param_lower:
                return 'oil_level'
            elif 'oil_contamination' in param_lower:
                return 'oil_contamination'
            elif 'bearing_temperature' in param_lower:
                return 'bearing_temperatures'
            elif 'vibration' in param_lower:
                return 'bearing_vibrations'
            elif 'efficiency' in param_lower:
                return 'overall_efficiency'
        
        elif subsystem == 'steam_generator':
            # Steam generator parameter mappings
            if 'tsp_fouling' in param_lower:
                return 'tsp_fouling_thicknesses'
            elif 'temperature' in param_lower:
                return 'sg_temperatures'
            elif 'steam_quality' in param_lower:
                return 'sg_steam_qualities'
            elif 'fouling_fraction' in param_lower:
                return 'tsp_fouling_fractions'
        
        elif subsystem == 'condenser':
            # Condenser parameter mappings
            if 'fouling_resistance' in param_lower:
                return 'total_fouling_resistance'
            elif 'biofouling' in param_lower:
                return 'biofouling_thickness'
            elif 'scale' in param_lower:
                return 'scale_thickness'
            elif 'pressure' in param_lower:
                return 'condenser_pressure'
            elif 'tube_leak' in param_lower:
                return 'tube_leak_rate'
        
        # Default: try to use parameter name as-is
        return param_name
    
    def inject_into_simulator(self, simulator: NuclearPlantSimulator, 
                            initial_conditions: Dict[str, float]) -> bool:
        """
        Inject initial conditions into a running simulator
        
        Args:
            simulator: Running simulator instance
            initial_conditions: Dictionary mapping parameter names to values
            
        Returns:
            True if successful, False otherwise
        """
        print(f"INJECTOR: Injecting {len(initial_conditions)} conditions into running simulator")
        
        if not simulator.state_manager:
            print("INJECTOR: Error - Simulator has no state manager")
            return False
        
        # Get registered components
        registered_components = simulator.state_manager.get_registered_instance_info()
        
        # Group conditions by component
        grouped_conditions = self._group_conditions_by_component(initial_conditions)
        
        conditions_applied = 0
        
        for component_id, conditions in grouped_conditions.items():
            if component_id in registered_components:
                component_info = registered_components[component_id]
                component_instance = component_info['instance']
                
                # Apply conditions to component
                applied = self._apply_conditions_to_component(component_instance, conditions)
                conditions_applied += applied
            else:
                print(f"INJECTOR: Warning - Component {component_id} not found in simulator")
        
        print(f"INJECTOR: Applied {conditions_applied} conditions to running simulator")
        return conditions_applied > 0
    
    def _apply_conditions_to_component(self, component: Any, conditions: Dict[str, float]) -> int:
        """
        Apply conditions to a specific component instance
        
        Args:
            component: Component instance
            conditions: Conditions to apply
            
        Returns:
            Number of conditions successfully applied
        """
        applied_count = 0
        
        for param_name, value in conditions.items():
            try:
                # Try to set the parameter directly
                if hasattr(component, param_name):
                    setattr(component, param_name, value)
                    applied_count += 1
                    print(f"INJECTOR: Set {component.__class__.__name__}.{param_name} = {value:.3f}")
                
                # Try to set via state object
                elif hasattr(component, 'state') and hasattr(component.state, param_name):
                    setattr(component.state, param_name, value)
                    applied_count += 1
                    print(f"INJECTOR: Set {component.__class__.__name__}.state.{param_name} = {value:.3f}")
                
                # Try to set via config object
                elif hasattr(component, 'config') and hasattr(component.config, param_name):
                    setattr(component.config, param_name, value)
                    applied_count += 1
                    print(f"INJECTOR: Set {component.__class__.__name__}.config.{param_name} = {value:.3f}")
                
                else:
                    print(f"INJECTOR: Warning - Could not set {param_name} on {component.__class__.__name__}")
            
            except Exception as e:
                print(f"INJECTOR: Error setting {param_name} on {component.__class__.__name__}: {e}")
        
        return applied_count
    
    def create_configured_simulator(self, base_config: Dict[str, Any], 
                                  initial_conditions: Dict[str, float],
                                  **simulator_kwargs) -> NuclearPlantSimulator:
        """
        Create a new simulator with initial conditions applied
        
        Args:
            base_config: Base configuration dictionary
            initial_conditions: Initial conditions to apply
            **simulator_kwargs: Additional arguments for simulator creation
            
        Returns:
            Configured simulator instance
        """
        # Inject conditions into config
        configured_config = self.inject_into_config(base_config, initial_conditions)
        
        # Create simulator with configured config
        simulator = NuclearPlantSimulator(
            enable_state_management=True,
            enable_secondary=True,
            secondary_config=configured_config.get('secondary_system'),
            **simulator_kwargs
        )
        
        print(f"INJECTOR: Created simulator with {len(initial_conditions)} initial conditions")
        
        return simulator
    
    def validate_injection(self, simulator: NuclearPlantSimulator, 
                          expected_conditions: Dict[str, float],
                          tolerance: float = 0.01) -> Dict[str, Any]:
        """
        Validate that initial conditions were properly applied
        
        Args:
            simulator: Simulator to validate
            expected_conditions: Expected parameter values
            tolerance: Tolerance for validation
            
        Returns:
            Validation report
        """
        validation_report = {
            'total_conditions': len(expected_conditions),
            'validated_conditions': 0,
            'failed_validations': 0,
            'validation_details': {},
            'errors': []
        }
        
        if not simulator.state_manager:
            validation_report['errors'].append("Simulator has no state manager")
            return validation_report
        
        # Group conditions by component
        grouped_conditions = self._group_conditions_by_component(expected_conditions)
        
        for component_id, conditions in grouped_conditions.items():
            try:
                # Get current component state
                current_state = simulator.state_manager.get_component_state_snapshot(component_id)
                
                for param_name, expected_value in conditions.items():
                    current_value = current_state.get(param_name)
                    
                    if current_value is not None:
                        # Check if values match within tolerance
                        if abs(current_value - expected_value) <= tolerance:
                            validation_report['validated_conditions'] += 1
                            validation_report['validation_details'][f"{component_id}.{param_name}"] = {
                                'expected': expected_value,
                                'actual': current_value,
                                'valid': True
                            }
                        else:
                            validation_report['failed_validations'] += 1
                            validation_report['validation_details'][f"{component_id}.{param_name}"] = {
                                'expected': expected_value,
                                'actual': current_value,
                                'valid': False,
                                'error': f"Value mismatch: expected {expected_value}, got {current_value}"
                            }
                    else:
                        validation_report['failed_validations'] += 1
                        validation_report['validation_details'][f"{component_id}.{param_name}"] = {
                            'expected': expected_value,
                            'actual': None,
                            'valid': False,
                            'error': "Parameter not found in component state"
                        }
            
            except Exception as e:
                validation_report['errors'].append(f"Error validating {component_id}: {e}")
        
        return validation_report
