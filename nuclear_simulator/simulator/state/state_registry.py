"""
State Registry

This module manages the registry of all state variables in the nuclear simulator.
It provides metadata storage, validation, and organization capabilities.
"""

from typing import Dict, List, Set, Optional, Tuple
import warnings
from .interfaces import StateVariable, StateCategory


class StateRegistry:
    """
    Registry for managing state variable metadata and organization.
    
    The registry maintains metadata for all state variables in the system,
    provides validation, and supports querying and filtering operations.
    """
    
    def __init__(self):
        """Initialize empty state registry"""
        self._variables: Dict[str, StateVariable] = {}
        self._categories: Dict[StateCategory, Set[str]] = {
            category: set() for category in StateCategory
        }
        self._subcategories: Dict[str, Set[str]] = {}
        
    def register_variable(self, variable: StateVariable) -> None:
        """
        Register a state variable in the registry.
        
        Args:
            variable: StateVariable metadata to register
            
        Raises:
            ValueError: If variable name is already registered or invalid
        """
        if variable.name in self._variables:
            warnings.warn(f"State variable '{variable.name}' is already registered. Overwriting.")
        
        # Validate variable name format
        try:
            parts = variable.name.split('.')
            if len(parts) != 3:
                raise ValueError(f"Invalid variable name format: {variable.name}")
            category_str, subcategory, var_name = parts
        except Exception as e:
            raise ValueError(f"Invalid variable name '{variable.name}': {e}")
        
        # Validate category
        if variable.category.value != category_str:
            raise ValueError(f"Category mismatch: name has '{category_str}' but category is '{variable.category.value}'")
        
        # Register the variable
        self._variables[variable.name] = variable
        self._categories[variable.category].add(variable.name)
        
        # Track subcategories
        subcategory_key = f"{category_str}.{subcategory}"
        if subcategory_key not in self._subcategories:
            self._subcategories[subcategory_key] = set()
        self._subcategories[subcategory_key].add(variable.name)
    
    def register_variables(self, variables: Dict[str, StateVariable]) -> None:
        """
        Register multiple state variables.
        
        Args:
            variables: Dictionary of variable name to StateVariable metadata
        """
        for name, variable in variables.items():
            if variable.name != name:
                warnings.warn(f"Variable name mismatch: key='{name}', variable.name='{variable.name}'")
            self.register_variable(variable)
    
    def get_variable(self, name: str) -> Optional[StateVariable]:
        """
        Get metadata for a specific state variable.
        
        Args:
            name: Variable name
            
        Returns:
            StateVariable metadata or None if not found
        """
        return self._variables.get(name)
    
    def get_all_variables(self) -> Dict[str, StateVariable]:
        """
        Get all registered state variables.
        
        Returns:
            Dictionary of all registered variables
        """
        return self._variables.copy()
    
    def get_variables_by_category(self, category: StateCategory) -> Dict[str, StateVariable]:
        """
        Get all variables in a specific category.
        
        Args:
            category: Category to filter by
            
        Returns:
            Dictionary of variables in the specified category
        """
        variable_names = self._categories[category]
        return {name: self._variables[name] for name in variable_names}
    
    def get_variables_by_subcategory(self, category: str, subcategory: str) -> Dict[str, StateVariable]:
        """
        Get all variables in a specific subcategory.
        
        Args:
            category: Category name (e.g., "primary")
            subcategory: Subcategory name (e.g., "neutronics")
            
        Returns:
            Dictionary of variables in the specified subcategory
        """
        subcategory_key = f"{category}.{subcategory}"
        if subcategory_key not in self._subcategories:
            return {}
        
        variable_names = self._subcategories[subcategory_key]
        return {name: self._variables[name] for name in variable_names}
    
    def get_critical_variables(self) -> Dict[str, StateVariable]:
        """
        Get all variables marked as critical.
        
        Returns:
            Dictionary of critical variables
        """
        return {name: var for name, var in self._variables.items() if var.is_critical}
    
    def get_categories(self) -> List[StateCategory]:
        """
        Get list of all categories that have registered variables.
        
        Returns:
            List of categories with registered variables
        """
        return [category for category, variables in self._categories.items() if variables]
    
    def get_subcategories(self, category: str) -> List[str]:
        """
        Get list of all subcategories for a given category.
        
        Args:
            category: Category name
            
        Returns:
            List of subcategory names
        """
        prefix = f"{category}."
        subcategories = []
        for subcategory_key in self._subcategories.keys():
            if subcategory_key.startswith(prefix):
                subcategory = subcategory_key[len(prefix):]
                subcategories.append(subcategory)
        return sorted(subcategories)
    
    def validate_state_data(self, state_data: Dict[str, any]) -> Tuple[bool, List[str]]:
        """
        Validate state data against registered variables.
        
        Args:
            state_data: Dictionary of state variable names to values
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for unknown variables
        for name in state_data.keys():
            if name not in self._variables and name != 'time':
                errors.append(f"Unknown state variable: {name}")
        
        # Check for missing critical variables
        critical_vars = self.get_critical_variables()
        for name in critical_vars.keys():
            if name not in state_data:
                errors.append(f"Missing critical variable: {name}")
        
        # Validate data types and ranges
        for name, value in state_data.items():
            if name == 'time':
                continue  # Skip time validation
                
            variable = self._variables.get(name)
            if variable is None:
                continue  # Already reported as unknown
            
            # Type validation
            if not isinstance(value, variable.data_type) and value is not None:
                # Allow numeric conversions
                if variable.data_type in (int, float) and isinstance(value, (int, float)):
                    pass  # Allow int/float conversion
                else:
                    errors.append(f"Type mismatch for {name}: expected {variable.data_type.__name__}, got {type(value).__name__}")
            
            # Range validation for numeric values
            if variable.valid_range is not None and isinstance(value, (int, float)):
                min_val, max_val = variable.valid_range
                if value < min_val or value > max_val:
                    errors.append(f"Value out of range for {name}: {value} not in [{min_val}, {max_val}]")
        
        return len(errors) == 0, errors
    
    def get_variable_count(self) -> int:
        """Get total number of registered variables"""
        return len(self._variables)
    
    def get_category_counts(self) -> Dict[str, int]:
        """
        Get count of variables in each category.
        
        Returns:
            Dictionary mapping category names to variable counts
        """
        return {category.value: len(variables) for category, variables in self._categories.items()}
    
    def get_subcategory_counts(self) -> Dict[str, int]:
        """
        Get count of variables in each subcategory.
        
        Returns:
            Dictionary mapping subcategory keys to variable counts
        """
        return {subcategory: len(variables) for subcategory, variables in self._subcategories.items()}
    
    def clear(self) -> None:
        """Clear all registered variables"""
        self._variables.clear()
        for category_set in self._categories.values():
            category_set.clear()
        self._subcategories.clear()
    
    def __len__(self) -> int:
        """Return number of registered variables"""
        return len(self._variables)
    
    def __contains__(self, name: str) -> bool:
        """Check if a variable is registered"""
        return name in self._variables
    
    def __repr__(self) -> str:
        """String representation of registry"""
        counts = self.get_category_counts()
        total = sum(counts.values())
        return f"StateRegistry(total={total}, {', '.join(f'{cat}={count}' for cat, count in counts.items())})"
