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

Usage:
    from simulator.state import StateManager, StateProvider, StateVariable, StateCategory
    
    # Create state manager
    state_manager = StateManager()
    
    # Register physics components
    state_manager.register_provider(primary_physics, "primary")
    state_manager.register_provider(secondary_physics, "secondary")
    
    # Collect states during simulation
    state_manager.collect_states(simulation_time)
    
    # Export to CSV
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

__all__ = [
    # Core classes
    'StateManager',
    'StateRegistry',
    
    # Interfaces and protocols
    'StateProvider',
    'StateCollector',
    'StateVariable',
    'StateCategory',
    
    # Utility functions
    'make_state_name',
    'parse_state_name',
    'filter_states_by_category',
    'filter_states_by_subcategory'
]

# Version information
__version__ = "1.0.0"
__author__ = "Nuclear Simulator Team"
__description__ = "Comprehensive state management system for nuclear reactor simulation"
