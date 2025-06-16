"""
State Management Interfaces

This module defines the interfaces and protocols for the state management system.
All physics components that want to provide state data should implement StateProvider.
"""

from typing import Dict, Any, Protocol, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class StateCategory(Enum):
    """Categories for organizing state variables"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    INTEGRATION = "integration"
    CONTROL = "control"
    SAFETY = "safety"


@dataclass
class StateVariable:
    """Metadata for a state variable"""
    name: str                                    # Full hierarchical name (e.g., "primary.neutronics.flux")
    category: StateCategory                      # High-level category
    subcategory: str                            # Subcategory (e.g., "neutronics", "thermal")
    unit: str                                   # Physical unit
    description: str                            # Human-readable description
    data_type: type                             # Python data type
    valid_range: Optional[Tuple[float, float]] = None  # Valid range for numeric values
    is_critical: bool = False                   # Whether this is a critical safety parameter
    sampling_rate: float = 1.0                 # Desired sampling rate (Hz)


class StateProvider(Protocol):
    """
    Protocol for components that provide state variables to the state management system.
    
    All physics components (primary, secondary, etc.) should implement this protocol
    to automatically contribute their state variables to the centralized tracking system.
    """
    
    def get_state_variables(self) -> Dict[str, StateVariable]:
        """
        Return metadata for all state variables this component provides.
        
        Returns:
            Dictionary mapping variable names to their metadata.
            Variable names should use hierarchical naming (e.g., "primary.neutronics.flux")
        """
        ...
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Return current values for all state variables this component provides.
        
        Returns:
            Dictionary mapping variable names to their current values.
            Keys should match those returned by get_state_variables().
        """
        ...


class StateCollector(Protocol):
    """
    Protocol for objects that can collect state from multiple providers.
    """
    
    def register_provider(self, provider: StateProvider, category: str) -> None:
        """Register a state provider with the collector"""
        ...
    
    def collect_states(self, timestamp: float) -> Dict[str, Any]:
        """Collect current state from all registered providers"""
        ...


# Utility functions for state variable naming
def make_state_name(category: str, subcategory: str, variable: str) -> str:
    """
    Create a hierarchical state variable name.
    
    Args:
        category: High-level category (e.g., "primary", "secondary")
        subcategory: Subcategory (e.g., "neutronics", "thermal")
        variable: Variable name (e.g., "neutron_flux")
    
    Returns:
        Hierarchical name (e.g., "primary.neutronics.neutron_flux")
    """
    return f"{category}.{subcategory}.{variable}"


def parse_state_name(state_name: str) -> Tuple[str, str, str]:
    """
    Parse a hierarchical state variable name.
    
    Args:
        state_name: Hierarchical name (e.g., "primary.neutronics.neutron_flux")
    
    Returns:
        Tuple of (category, subcategory, variable)
    """
    parts = state_name.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid state name format: {state_name}. Expected 'category.subcategory.variable'")
    return parts[0], parts[1], parts[2]


def filter_states_by_category(states: Dict[str, Any], category: str) -> Dict[str, Any]:
    """
    Filter state dictionary to include only variables from a specific category.
    
    Args:
        states: Dictionary of state variables
        category: Category to filter by
    
    Returns:
        Filtered dictionary containing only variables from the specified category
    """
    return {name: value for name, value in states.items() if name.startswith(f"{category}.")}


def filter_states_by_subcategory(states: Dict[str, Any], category: str, subcategory: str) -> Dict[str, Any]:
    """
    Filter state dictionary to include only variables from a specific subcategory.
    
    Args:
        states: Dictionary of state variables
        category: Category to filter by
        subcategory: Subcategory to filter by
    
    Returns:
        Filtered dictionary containing only variables from the specified subcategory
    """
    prefix = f"{category}.{subcategory}."
    return {name: value for name, value in states.items() if name.startswith(prefix)}
