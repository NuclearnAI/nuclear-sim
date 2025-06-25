"""
Maintenance Templates - New Configuration-Driven System

This module provides a simplified interface to the new maintenance configuration
system, replacing the old hard-coded templates with flexible, configurable
maintenance behavior.
"""

from typing import Dict, Any, Optional, List
from .config import MaintenanceConfig, MaintenanceConfigFactory, MaintenanceMode, ComponentTypeConfig
from simulator.state.component_metadata import EquipmentType


def generate_monitoring_config(component_state_variables: Dict[str, Any], 
                             equipment_type: EquipmentType,
                             component_id: str = "",
                             maintenance_config: Optional[MaintenanceConfig] = None,
                             aggressive_mode: bool = False,
                             ultra_aggressive_mode: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Generate monitoring configuration for a component using the new config system
    
    Args:
        component_state_variables: Dictionary of component's state variables
        equipment_type: Type of equipment
        component_id: Specific component ID for overrides
        maintenance_config: MaintenanceConfig instance to use. If None, creates based on mode flags.
        aggressive_mode: Legacy parameter - creates aggressive config if maintenance_config is None
        ultra_aggressive_mode: Legacy parameter - creates ultra-aggressive config if maintenance_config is None
        
    Returns:
        Monitoring configuration dictionary
    """
    # Create maintenance config if not provided (for backward compatibility)
    if maintenance_config is None:
        if ultra_aggressive_mode:
            maintenance_config = MaintenanceConfigFactory.create_ultra_aggressive()
        elif aggressive_mode:
            maintenance_config = MaintenanceConfigFactory.create_aggressive()
        else:
            maintenance_config = MaintenanceConfigFactory.create_conservative()
    
    # Get component configuration
    component_config = maintenance_config.get_component_config(component_id, equipment_type)
    if not component_config:
        return {}
    
    monitoring_config = {}
    
    # Variable name aliases for better matching
    variable_aliases = {
        'blade_condition': 'blade_wear',
        'tsp_fouling_fraction': 'tube_fouling_factor',
    }
    
    # Match state variables to configured thresholds
    for var_name, var_value in component_state_variables.items():
        var_name_lower = var_name.lower()
        
        # Extract the base variable name from dotted paths
        base_var_name = var_name.split('.')[-1] if '.' in var_name else var_name
        base_var_name_lower = base_var_name.lower()
        
        # Check aliases
        aliased_name = variable_aliases.get(base_var_name_lower, base_var_name_lower)
        
        # Find matching threshold configuration
        best_match = None
        best_score = 0
        
        for threshold_name, threshold_config in component_config.thresholds.items():
            threshold_name_lower = threshold_name.lower()
            
            # Score the match quality
            score = 0
            
            # Exact match with base variable name gets highest score
            if threshold_name_lower == base_var_name_lower:
                score = 100
            # Exact match with aliased name
            elif threshold_name_lower == aliased_name:
                score = 95
            # Exact match with full variable name
            elif threshold_name_lower == var_name_lower:
                score = 90
            # Substring match with base name
            elif threshold_name_lower in base_var_name_lower:
                score = 80
            elif base_var_name_lower in threshold_name_lower:
                score = 75
            # Substring match with full name
            elif threshold_name_lower in var_name_lower:
                score = 70
            elif var_name_lower in threshold_name_lower:
                score = 65
            # Keyword match (less preferred)
            elif any(keyword in base_var_name_lower for keyword in threshold_name_lower.split('_')):
                score = 50
            elif any(keyword in var_name_lower for keyword in threshold_name_lower.split('_')):
                score = 45
            
            # Use the best match
            if score > best_score:
                best_score = score
                best_match = (threshold_name, threshold_config)
        
        # Only create monitoring if we have a good match (score > 60)
        if best_match and best_score > 60:
            threshold_name, threshold_config = best_match
            
            # Apply global multipliers to get effective values
            effective_threshold = maintenance_config.get_effective_threshold(
                threshold_config.threshold, threshold_config.comparison
            )
            effective_cooldown = maintenance_config.get_effective_cooldown(
                threshold_config.cooldown_hours
            )
            
            monitoring_config[var_name] = {
                'attribute': var_name,  # Use full dotted path for state variables
                'threshold': effective_threshold,
                'comparison': threshold_config.comparison,
                'action': threshold_config.action,
                'cooldown_hours': effective_cooldown,
                'priority': threshold_config.priority
            }
    
    return monitoring_config


def get_maintenance_template(equipment_type: EquipmentType, 
                           aggressive_mode: bool = False, 
                           ultra_aggressive_mode: bool = False,
                           maintenance_config: Optional[MaintenanceConfig] = None) -> Dict[str, Any]:
    """
    Get maintenance template for a specific equipment type using new config system
    
    Args:
        equipment_type: Type of equipment
        aggressive_mode: Legacy parameter - creates aggressive config if maintenance_config is None
        ultra_aggressive_mode: Legacy parameter - creates ultra-aggressive config if maintenance_config is None
        maintenance_config: MaintenanceConfig instance to use. If None, creates based on mode flags.
        
    Returns:
        Maintenance template dictionary (converted from new config format)
    """
    # Create maintenance config if not provided
    if maintenance_config is None:
        if ultra_aggressive_mode:
            maintenance_config = MaintenanceConfigFactory.create_ultra_aggressive()
        elif aggressive_mode:
            maintenance_config = MaintenanceConfigFactory.create_aggressive()
        else:
            maintenance_config = MaintenanceConfigFactory.create_conservative()
    
    # Get component configuration
    component_config = maintenance_config.get_component_config("", equipment_type)
    if not component_config:
        return None
    
    # Convert new config format to legacy template format
    template = {
        'description': f'{equipment_type.value} maintenance monitoring with {maintenance_config.mode.value} thresholds',
        'check_interval_hours': maintenance_config.get_effective_check_interval(component_config.check_interval_hours),
        'state_variable_patterns': {}
    }
    
    # Convert thresholds to legacy format
    for param_name, threshold_config in component_config.thresholds.items():
        effective_threshold = maintenance_config.get_effective_threshold(
            threshold_config.threshold, threshold_config.comparison
        )
        effective_cooldown = maintenance_config.get_effective_cooldown(
            threshold_config.cooldown_hours
        )
        
        template['state_variable_patterns'][param_name] = {
            'threshold': effective_threshold,
            'comparison': threshold_config.comparison,
            'action': threshold_config.action,
            'cooldown_hours': effective_cooldown,
            'priority': threshold_config.priority
        }
    
    return template


def get_supported_equipment_types() -> List[EquipmentType]:
    """Get list of equipment types that have maintenance configurations"""
    # Return the equipment types we have configurations for
    return [
        EquipmentType.PUMP,
        EquipmentType.TURBINE_STAGE,
        EquipmentType.STEAM_GENERATOR,
        EquipmentType.CONDENSER
    ]


def get_template_description(equipment_type: EquipmentType, 
                           maintenance_config: Optional[MaintenanceConfig] = None) -> str:
    """Get description of maintenance template for equipment type"""
    if maintenance_config is None:
        maintenance_config = MaintenanceConfigFactory.create_conservative()
    
    component_config = maintenance_config.get_component_config("", equipment_type)
    if component_config:
        return f'{equipment_type.value} maintenance monitoring with {maintenance_config.mode.value} thresholds'
    return f'No maintenance configuration available for {equipment_type.value}'


def get_default_check_interval(equipment_type: EquipmentType, 
                             aggressive_mode: bool = False,
                             maintenance_config: Optional[MaintenanceConfig] = None) -> float:
    """Get default check interval for equipment type"""
    if maintenance_config is None:
        if aggressive_mode:
            maintenance_config = MaintenanceConfigFactory.create_aggressive()
        else:
            maintenance_config = MaintenanceConfigFactory.create_conservative()
    
    component_config = maintenance_config.get_component_config("", equipment_type)
    if component_config:
        return maintenance_config.get_effective_check_interval(component_config.check_interval_hours)
    return 24.0  # Default to daily checks


# Convenience functions for creating specific maintenance configurations
def create_ultra_aggressive_maintenance_config() -> MaintenanceConfig:
    """Create ultra-aggressive maintenance configuration for maximum work order generation"""
    return MaintenanceConfigFactory.create_ultra_aggressive()


def create_aggressive_maintenance_config() -> MaintenanceConfig:
    """Create aggressive maintenance configuration for demonstrations"""
    return MaintenanceConfigFactory.create_aggressive()


def create_conservative_maintenance_config() -> MaintenanceConfig:
    """Create conservative maintenance configuration for realistic operation"""
    return MaintenanceConfigFactory.create_conservative()


# Export the new config classes for direct use
from .config import (
    MaintenanceConfig,
    MaintenanceConfigFactory,
    MaintenanceMode,
    ComponentThresholds,
    ComponentTypeConfig
)

__all__ = [
    'generate_monitoring_config',
    'get_maintenance_template', 
    'get_supported_equipment_types',
    'get_template_description',
    'get_default_check_interval',
    'create_ultra_aggressive_maintenance_config',
    'create_aggressive_maintenance_config', 
    'create_conservative_maintenance_config',
    'MaintenanceConfig',
    'MaintenanceConfigFactory',
    'MaintenanceMode',
    'ComponentThresholds',
    'ComponentTypeConfig'
]
