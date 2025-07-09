"""
State Management System

This package provides comprehensive state management for the nuclear simulator,
including time series storage, CSV export, and hierarchical organization of
physics state variables.

Key Components:
- StateManager: Core pandas-based state collection and storage
- StateRegistry: Metadata management and validation
- StateProvider: Interface for physics components to provide state data
- StateVariable: Metadata container for individual state variables
- auto_register: Decorator for automatic component registration

Usage:
    from simulator.state import auto_register, StateManager, StateCategory
    
    # Register components with decorator
    @auto_register("SECONDARY", "feedwater", "FWP", id_source="pump_id")
    class FeedwaterPump:
        def __init__(self, pump_id: str):
            self.pump_id = pump_id
        
        def get_state_dict(self):
            return {'flow_rate': self.flow_rate, 'power': self.power}
    
    # Components auto-register on creation
    pump = FeedwaterPump("FWP-1A")
    
    # Access global state manager
    state_manager = StateManager._global_instance
    state_manager.collect_states(simulation_time)
    state_manager.export_to_csv("simulation_data.csv")
"""

from .interfaces import (
    StateProvider,
    StateCollector, 
    StateVariable,
    StateCategory,
    make_state_name,
    parse_state_name,
    filter_states_by_category,
    filter_states_by_subcategory
)

from .state_registry import StateRegistry
from .state_manager import StateManager
from .auto_register import auto_register, get_registered_info, is_auto_registered
from .component_metadata import (
    ComponentMetadata,
    ComponentRegistry,
    EquipmentType,
    infer_equipment_type_from_class_name,
    infer_capabilities_from_state_variables,
    extract_design_parameters_from_config
)

__all__ = [
    # Core classes
    'StateManager',
    'StateRegistry',
    
    # New decorator system
    'auto_register',
    'get_registered_info',
    'is_auto_registered',
    
    # Component metadata classes
    'ComponentMetadata',
    'ComponentRegistry',
    'EquipmentType',
    
    # Interfaces and protocols
    'StateProvider',
    'StateCollector',
    'StateVariable',
    'StateCategory',
    
    # Utility functions
    'make_state_name',
    'parse_state_name',
    'filter_states_by_category',
    'filter_states_by_subcategory',
    'infer_equipment_type_from_class_name',
    'infer_capabilities_from_state_variables',
    'extract_design_parameters_from_config'
]

# Version information
__version__ = "1.0.0"
__author__ = "Nuclear Simulator Team"
__description__ = "Comprehensive state management system for nuclear reactor simulation"
