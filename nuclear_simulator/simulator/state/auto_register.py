"""
Auto-Registration Decorator System

This module provides a unified decorator-based approach for automatic component
registration in the state management system. It replaces the complex path-based
inference system with explicit, clean decorators.

Key Features:
1. Explicit registration via @auto_register decorator
2. Config-aware ID extraction from nested attributes
3. Support for components with or without IDs
4. Multiple instances of same class with unique namespaces
5. Flexible ID source specification
"""

from typing import Optional, Union, Any
import warnings
import time

from .interfaces import StateCategory, StateVariable
from .component_metadata import (
    ComponentMetadata, EquipmentType, ComponentRegistry,
    infer_equipment_type_from_class_name, infer_capabilities_from_state_variables,
    extract_design_parameters_from_config
)


def auto_register(
    category: Union[str, StateCategory],
    subcategory: str,
    component_code: Optional[str] = None,
    id_source: Optional[str] = None,
    allow_no_id: bool = False,
    use_global: bool = False,
    equipment_type: Optional[EquipmentType] = None,
    description: Optional[str] = None,
    design_parameters: Optional[dict] = None
):
    """
    Decorator for automatic component registration in the state management system.
    
    This decorator replaces the StateProviderMixin approach with a cleaner,
    more explicit registration system that supports multiple instances,
    config-based ID extraction, and automatic metadata generation.
    
    Args:
        category: Component category (PRIMARY, SECONDARY, SAFETY, CONTROL)
        subcategory: Component subcategory (feedwater, turbine, reactor, etc.)
        component_code: Short code for ID generation (FW, TB, RX, etc.)
        id_source: Where to find the ID, supports:
            - "config.system_id" (nested attribute)
            - "pump_id" (direct attribute) 
            - None (auto-detect common patterns)
        allow_no_id: If True, components without IDs get auto-generated IDs
        use_global: If True, register with global StateManager. If False (default),
                   register with current local StateManager (sim.py pattern)
        equipment_type: Optional explicit equipment type (auto-inferred if not provided)
        description: Optional human-readable description
        design_parameters: Optional dict of design parameters (auto-extracted if not provided)
    
    Examples:
        # With explicit metadata
        @auto_register("SECONDARY", "feedwater", "FWP", id_source="pump_id",
                       equipment_type=EquipmentType.PUMP,
                       description="Main feedwater circulation pump")
        class FeedwaterPump:
            def __init__(self, pump_id):
                self.pump_id = pump_id
        
        # Auto-inferred metadata (recommended)
        @auto_register("SECONDARY", "turbine", "TB", id_source="config.stage_id")
        class TurbineStage:
            def __init__(self, config):
                self.config = config  # Metadata auto-inferred from class name and config
        
        # Auto-generated IDs with metadata
        @auto_register("PRIMARY", "neutronics", "NEU", allow_no_id=True,
                       description="Reactor neutronics calculation model")
        class NeutronicsModel:
            def __init__(self):
                pass  # Gets auto-generated ID like "NEU-001" with inferred metadata
    """
    def decorator(cls):
        # Convert string category to enum if needed
        if isinstance(category, str):
            try:
                cat_enum = StateCategory[category.upper()]
            except KeyError:
                raise ValueError(f"Invalid category '{category}'. Must be one of: {list(StateCategory)}")
        else:
            cat_enum = category
        
        # Store registration info on class
        cls._auto_register_info = {
            'category': cat_enum,
            'subcategory': subcategory,
            'component_code': component_code or subcategory[:3].upper(),
            'id_source': id_source,
            'allow_no_id': allow_no_id,
            'equipment_type': equipment_type,
            'description': description,
            'design_parameters': design_parameters
        }
        
        # Wrap __init__ for instance registration
        original_init = cls.__init__
        
        def enhanced_init(self, *args, **kwargs):
            # Call original __init__ first
            original_init(self, *args, **kwargs)
            
            # Extract instance ID
            instance_id = _extract_instance_id(
                self, 
                id_source,
                cls._auto_register_info['component_code'],
                allow_no_id
            )
            
            # Only register if we have an ID or allow_no_id is True
            if instance_id:
                try:
                    # Import here to avoid circular imports
                    from .state_manager import StateManager
                    
                    if use_global:
                        # Register with global state manager
                        if not hasattr(StateManager, '_global_instance'):
                            StateManager._global_instance = StateManager()
                        
                        StateManager._global_instance.register_instance(
                            instance=self,
                            instance_id=instance_id,
                            category=cat_enum,
                            subcategory=subcategory,
                            registration_info=cls._auto_register_info
                        )
                    else:
                        # Register with current local state manager (sim.py pattern)
                        # Add to pending registration list for discovery
                        if not hasattr(StateManager, '_pending_registrations'):
                            StateManager._pending_registrations = []
                        
                        StateManager._pending_registrations.append({
                            'instance': self,
                            'instance_id': instance_id,
                            'category': cat_enum,
                            'subcategory': subcategory,
                            'registration_info': cls._auto_register_info
                        })
                    
                    # Store instance ID on object for reference
                    self._instance_id = instance_id
                    
                except Exception as e:
                    warnings.warn(f"Failed to auto-register {cls.__name__} instance '{instance_id}': {e}")
            else:
                if not allow_no_id:
                    warnings.warn(f"No ID found for {cls.__name__} instance and allow_no_id=False")
        
        cls.__init__ = enhanced_init
        return cls
    
    return decorator


def _extract_instance_id(instance: Any, id_source: Optional[str], component_code: str, allow_no_id: bool) -> Optional[str]:
    """
    Enhanced ID extraction with config support and fallback generation.
    
    Args:
        instance: Component instance
        id_source: Specified source for ID extraction
        component_code: Component code for auto-generation
        allow_no_id: Whether to auto-generate IDs when none found
        
    Returns:
        Instance ID string or None if not found/allowed
    """
    
    # 1. Try specified id_source
    if id_source:
        try:
            # Handle nested attributes like "config.system_id"
            if '.' in id_source:
                obj = instance
                for attr in id_source.split('.'):
                    obj = getattr(obj, attr)
                if obj is not None:
                    return str(obj)
            else:
                # Handle direct attributes
                if hasattr(instance, id_source):
                    value = getattr(instance, id_source)
                    if value is not None:
                        return str(value)
        except (AttributeError, TypeError):
            pass
    
    # 2. Try common ID patterns in config objects
    if hasattr(instance, 'config') and instance.config is not None:
        config = instance.config
        for attr in ['system_id', 'component_id', 'pump_id', 'stage_id', 'sg_id', 'reactor_id', 'id']:
            if hasattr(config, attr):
                value = getattr(config, attr)
                if value is not None:
                    return str(value)
    
    # 3. Try direct attributes on instance
    for attr in ['component_id', 'pump_id', 'system_id', 'stage_id', 'sg_id', 'reactor_id', 'id']:
        if hasattr(instance, attr):
            value = getattr(instance, attr)
            if value is not None:
                return str(value)
    
    # 4. Generate ID if allowed
    if allow_no_id:
        # Import here to avoid circular imports
        from .state_manager import StateManager
        counter = StateManager.get_next_instance_number(component_code)
        return f"{component_code}-{counter:03d}"
    
    # 5. No ID found and not allowed
    return None


def get_registered_info(instance: Any) -> Optional[dict]:
    """
    Get registration information for an instance.
    
    Args:
        instance: Component instance
        
    Returns:
        Dictionary with registration info or None if not registered
    """
    if hasattr(instance, '_auto_register_info'):
        info = instance._auto_register_info.copy()
        if hasattr(instance, '_instance_id'):
            info['instance_id'] = instance._instance_id
        return info
    return None


def is_auto_registered(cls_or_instance: Any) -> bool:
    """
    Check if a class or instance is auto-registered.
    
    Args:
        cls_or_instance: Class or instance to check
        
    Returns:
        True if auto-registered, False otherwise
    """
    return hasattr(cls_or_instance, '_auto_register_info')
