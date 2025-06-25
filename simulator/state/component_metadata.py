"""
Component Metadata System

This module provides enhanced metadata capabilities for nuclear plant components,
including automatic equipment type detection, capability inference, and component
registration for runtime introspection.

Key Features:
1. ComponentMetadata dataclass with auto-generated and manual fields
2. EquipmentType enumeration for component classification
3. ComponentRegistry for runtime component tracking
4. Enhanced StateProviderMixin with component metadata support
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import warnings
import inspect

from .interfaces import StateVariable, StateCategory


class EquipmentType(Enum):
    """Equipment type classification based on nuclear plant components"""
    PUMP = "pump"
    TURBINE_STAGE = "turbine_stage"
    BEARING = "bearing"
    STEAM_GENERATOR = "steam_generator"
    CONDENSER = "condenser"
    EJECTOR = "ejector"
    LUBRICATION_SYSTEM = "lubrication_system"
    CONTROL_SYSTEM = "control_system"
    PROTECTION_SYSTEM = "protection_system"
    HEAT_EXCHANGER = "heat_exchanger"
    VALVE = "valve"
    SENSOR = "sensor"
    REACTOR = "reactor"
    COOLANT_SYSTEM = "coolant_system"
    UNKNOWN = "unknown"


@dataclass
class ComponentMetadata:
    """
    Metadata for a nuclear plant component
    
    Combines auto-generated technical metadata with optional manual descriptions
    """
    # Auto-generated fields
    component_id: str                                    # e.g., "FWP-001", "HP-3", "SG-1"
    equipment_type: EquipmentType                        # Equipment classification
    system: str                                          # e.g., "feedwater", "turbine", "primary"
    subsystem: Optional[str] = None                      # e.g., "lubrication", "control"
    capabilities: Dict[str, List[str]] = field(default_factory=dict)  # What this component can do
    design_parameters: Dict[str, float] = field(default_factory=dict) # Design specifications
    
    # Manual field
    description: Optional[str] = None                    # Human-readable description
    
    # Runtime tracking
    instance_class: Optional[str] = None                 # Python class name
    module_path: Optional[str] = None                    # Module location
    registration_time: Optional[float] = None            # When component was registered


class ComponentRegistry:
    """
    Registry for tracking all nuclear plant components at runtime
    
    Provides centralized access to component metadata, instances, and relationships
    """
    
    _components: Dict[str, Dict[str, Any]] = {}
    _equipment_types: Dict[EquipmentType, Set[str]] = {}
    _systems: Dict[str, Set[str]] = {}
    _capabilities: Dict[str, Set[str]] = {}
    
    @classmethod
    def register_component(cls, component, metadata: ComponentMetadata) -> None:
        """
        Register a component with the registry
        
        Args:
            component: Component instance
            metadata: Component metadata
        """
        component_id = metadata.component_id
        
        if component_id in cls._components:
            warnings.warn(f"Component '{component_id}' is already registered. Overwriting.")
        
        # Store component information
        cls._components[component_id] = {
            'instance': component,
            'metadata': metadata,
            'state_variables': component.get_state_variables() if hasattr(component, 'get_state_variables') else {}
        }
        
        # Update equipment type index
        if metadata.equipment_type not in cls._equipment_types:
            cls._equipment_types[metadata.equipment_type] = set()
        cls._equipment_types[metadata.equipment_type].add(component_id)
        
        # Update system index
        if metadata.system not in cls._systems:
            cls._systems[metadata.system] = set()
        cls._systems[metadata.system].add(component_id)
        
        # Update capabilities index
        for capability_type, capabilities in metadata.capabilities.items():
            for capability in capabilities:
                if capability not in cls._capabilities:
                    cls._capabilities[capability] = set()
                cls._capabilities[capability].add(component_id)
    
    @classmethod
    def get_component(cls, component_id: str) -> Optional[Dict[str, Any]]:
        """Get component information by ID"""
        return cls._components.get(component_id)
    
    @classmethod
    def get_all_components(cls) -> Dict[str, Dict[str, Any]]:
        """Get all registered components"""
        return cls._components.copy()
    
    @classmethod
    def get_components_by_type(cls, equipment_type: EquipmentType) -> Dict[str, Dict[str, Any]]:
        """Get all components of a specific equipment type"""
        component_ids = cls._equipment_types.get(equipment_type, set())
        return {cid: cls._components[cid] for cid in component_ids if cid in cls._components}
    
    @classmethod
    def get_components_by_system(cls, system: str) -> Dict[str, Dict[str, Any]]:
        """Get all components in a specific system"""
        component_ids = cls._systems.get(system, set())
        return {cid: cls._components[cid] for cid in component_ids if cid in cls._components}
    
    @classmethod
    def get_components_with_capability(cls, capability: str) -> Dict[str, Dict[str, Any]]:
        """Get all components that have a specific capability"""
        component_ids = cls._capabilities.get(capability, set())
        return {cid: cls._components[cid] for cid in component_ids if cid in cls._components}
    
    @classmethod
    def update_component_description(cls, component_id: str, description: str) -> bool:
        """
        Update the description of a registered component
        
        Args:
            component_id: Component ID
            description: New description
            
        Returns:
            True if successful, False if component not found
        """
        if component_id in cls._components:
            cls._components[component_id]['metadata'].description = description
            return True
        return False
    
    @classmethod
    def find_components_with_description(cls) -> Dict[str, str]:
        """Get all components that have descriptions"""
        components_with_desc = {}
        for cid, info in cls._components.items():
            desc = info['metadata'].description
            if desc:
                components_with_desc[cid] = desc
        return components_with_desc
    
    @classmethod
    def get_component_count(cls) -> int:
        """Get total number of registered components"""
        return len(cls._components)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered components"""
        cls._components.clear()
        cls._equipment_types.clear()
        cls._systems.clear()
        cls._capabilities.clear()
    
    @classmethod
    def generate_component_summary(cls) -> str:
        """Generate a summary report of all registered components"""
        total = cls.get_component_count()
        type_counts = {eq_type.value: len(components) for eq_type, components in cls._equipment_types.items() if components}
        system_counts = {system: len(components) for system, components in cls._systems.items() if components}
        
        summary = f"Component Registry Summary\n"
        summary += f"========================\n"
        summary += f"Total Components: {total}\n\n"
        
        if type_counts:
            summary += f"By Equipment Type:\n"
            for eq_type, count in sorted(type_counts.items()):
                summary += f"  {eq_type}: {count}\n"
        
        if system_counts:
            summary += f"\nBy System:\n"
            for system, count in sorted(system_counts.items()):
                summary += f"  {system}: {count}\n"
        
        return summary


# Lookup tables for equipment type inference
EQUIPMENT_TYPE_KEYWORDS = {
    EquipmentType.PUMP: ['pump'],
    EquipmentType.TURBINE_STAGE: ['turbine', 'stage', 'hp', 'lp'],
    EquipmentType.BEARING: ['bearing'],
    EquipmentType.STEAM_GENERATOR: ['steam_generator', 'steamgenerator', 'tsp'],  # Fixed: single keywords for steam generators
    EquipmentType.CONDENSER: ['condenser'],
    EquipmentType.EJECTOR: ['ejector'],
    EquipmentType.LUBRICATION_SYSTEM: ['lubrication', 'lub'],
    EquipmentType.CONTROL_SYSTEM: ['control', 'governor'],
    EquipmentType.PROTECTION_SYSTEM: ['protection', 'safety'],
    EquipmentType.REACTOR: ['reactor'],
    EquipmentType.HEAT_EXCHANGER: ['heat', 'exchanger'],
}

# Lookup tables for capability inference
CAPABILITY_PATTERNS = {
    'provides': {
        'steam_flow': [['steam', 'flow'], ['steam', 'rate']],
        'water_flow': [['flow', 'rate'], ['feedwater'], ['water', 'flow']],
        'mechanical_power': [['power', 'output'], ['power_output']],
        'heat_transfer': [['heat', 'transfer'], ['heat', 'rejection']],
    },
    'requires': {
        'electrical_power': [['power', 'consumption']],
        'steam_supply': [['steam', 'inlet']],
        'water_supply': [['water', 'inlet']],
    },
    'controls': {
        'speed_control': [['speed', 'percent'], ['speed', 'control']],
        'valve_control': [['valve', 'position']],
        'level_control': [['level', 'control']],
    },
    'monitors': {
        'process_monitoring': [['temperature'], ['pressure'], ['vibration'], ['flow']],
        'safety_monitoring': [['trip'], ['alarm'], ['status'], ['available']],
        'performance_monitoring': [['efficiency'], ['performance'], ['wear']],
    }
}

# Design parameter mapping
DESIGN_PARAMETER_MAPPING = {
    'rated_power': ['power'],
    'design_flow': ['flow'],
    'design_pressure': ['pressure'],
    'design_temperature': ['temperature'],
    'rated_speed': ['speed'],
    'design_efficiency': ['efficiency'],
}


def infer_equipment_type_from_class_name(class_name: str) -> EquipmentType:
    """
    Infer equipment type from class name using lookup table
    
    Args:
        class_name: Python class name
        
    Returns:
        Inferred equipment type
    """
    class_name_lower = class_name.lower()
    
    for equipment_type, keywords in EQUIPMENT_TYPE_KEYWORDS.items():
        if all(keyword in class_name_lower for keyword in keywords):
            return equipment_type
    
    # Single keyword fallback
    for equipment_type, keywords in EQUIPMENT_TYPE_KEYWORDS.items():
        if any(keyword in class_name_lower for keyword in keywords):
            return equipment_type
    
    return EquipmentType.UNKNOWN


def infer_capabilities_from_state_variables(state_variables: Dict[str, StateVariable]) -> Dict[str, List[str]]:
    """
    Infer component capabilities from its state variables using lookup tables
    
    Args:
        state_variables: Dictionary of state variables
        
    Returns:
        Dictionary of capabilities organized by type
    """
    capabilities = {capability_type: [] for capability_type in CAPABILITY_PATTERNS.keys()}
    
    for var_name, var_metadata in state_variables.items():
        var_name_lower = var_name.lower()
        
        for capability_type, capability_map in CAPABILITY_PATTERNS.items():
            for capability_name, keyword_patterns in capability_map.items():
                # Check if any of the keyword patterns match
                for keywords in keyword_patterns:
                    if all(keyword in var_name_lower for keyword in keywords):
                        if capability_name not in capabilities[capability_type]:
                            capabilities[capability_type].append(capability_name)
                        break  # Found a match, no need to check other patterns for this capability
    
    return capabilities


def extract_design_parameters_from_config(component) -> Dict[str, float]:
    """
    Extract design parameters from component configuration using lookup table
    
    Args:
        component: Component instance
        
    Returns:
        Dictionary of design parameters
    """
    design_params = {}
    
    # Look for config attribute
    if hasattr(component, 'config'):
        config = component.config
        for attr_name in dir(config):
            if not attr_name.startswith('_'):
                attr_value = getattr(config, attr_name)
                if isinstance(attr_value, (int, float)):
                    # Map to standardized parameter names
                    attr_name_lower = attr_name.lower()
                    for param_name, keywords in DESIGN_PARAMETER_MAPPING.items():
                        if any(keyword in attr_name_lower for keyword in keywords):
                            design_params[param_name] = float(attr_value)
                            break
                    else:
                        # Keep original name if no mapping found
                        design_params[attr_name] = float(attr_value)
    
    # Look for direct attributes
    direct_attributes = ['rated_power', 'design_flow', 'design_pressure', 'rated_speed']
    for attr_name in direct_attributes:
        if hasattr(component, attr_name):
            attr_value = getattr(component, attr_name)
            if isinstance(attr_value, (int, float)):
                design_params[attr_name] = float(attr_value)
    
    return design_params
