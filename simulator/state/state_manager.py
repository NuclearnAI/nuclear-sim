"""
State Manager

This module provides the core state management functionality using pandas DataFrames
for efficient time series storage and CSV export capabilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
import warnings
from pathlib import Path

from .interfaces import StateProvider, StateCollector, StateVariable, StateCategory
from .state_registry import StateRegistry
from .component_metadata import (
    ComponentMetadata, EquipmentType, ComponentRegistry,
    infer_equipment_type_from_class_name, infer_capabilities_from_state_variables,
    extract_design_parameters_from_config
)


class StateManager(StateCollector):
    """
    Core state management system using pandas DataFrames for time series storage.
    
    This class collects state data from multiple StateProvider components and stores
    it in a pandas DataFrame for efficient analysis and CSV export.
    """
    
    def __init__(self, max_rows: int = 100000, auto_manage_memory: bool = True):
        """
        Initialize state manager.
        
        Args:
            max_rows: Maximum number of rows to keep in memory
            auto_manage_memory: Whether to automatically manage memory by removing old data
        """
        self.max_rows = max_rows
        self.auto_manage_memory = auto_manage_memory
        
        # Core components
        self.registry = StateRegistry()
        self.data = pd.DataFrame()
        self.providers: List[Tuple[StateProvider, str]] = []
        
        # State tracking
        self.current_time = 0.0
        self.row_count = 0
        self.last_collection_time = None
        
        # Performance tracking
        self._collection_times = []
        
        # Instance tracking for new decorator system
        self._instance_counters = {}  # Track instance numbers by component code
        self._registered_instances = {}  # Track all registered instances
        
    def register_provider(self, provider: StateProvider, category: str) -> None:
        """
        Register a state provider with the manager.
        
        Args:
            provider: Component that provides state variables
            category: Category name for organizing the provider's variables
        """
        # Register the provider
        self.providers.append((provider, category))
        
        # Register all state variables from this provider
        try:
            state_variables = provider.get_state_variables()
            self.registry.register_variables(state_variables)
        except Exception as e:
            warnings.warn(f"Failed to register state variables from provider {category}: {e}")
    
    def collect_states(self, timestamp: float) -> Dict[str, Any]:
        """
        Collect current state from all registered providers and add to DataFrame.
        
        Args:
            timestamp: Current simulation time
            
        Returns:
            Dictionary of collected state data
        """
        import time
        start_time = time.time()
        
        # Start with timestamp
        row_data = {'time': timestamp}
        
        # Collect from all providers
        for provider, category in self.providers:
            try:
                # Try StateProvider protocol first (get_current_state)
                if hasattr(provider, 'get_current_state') and callable(getattr(provider, 'get_current_state')):
                    current_state = provider.get_current_state()
                    row_data.update(current_state)
                # Fall back to get_state_dict for auto-registered components
                elif hasattr(provider, 'get_state_dict') and callable(getattr(provider, 'get_state_dict')):
                    state_dict = provider.get_state_dict()
                    # Convert state_dict to hierarchical names using category
                    for var_name, value in state_dict.items():
                        # Create hierarchical name: category.variable
                        full_name = f"{category}.{var_name}"
                        row_data[full_name] = value
                else:
                    warnings.warn(f"Provider {category} does not implement StateProvider protocol or get_state_dict method")
            except Exception as e:
                warnings.warn(f"Failed to collect state from provider {category}: {e}")
        
        # Validate collected data (skip validation for now to avoid blocking)
        # is_valid, errors = self.registry.validate_state_data(row_data)
        # if not is_valid:
        #     warnings.warn(f"State validation errors: {errors}")
        
        # Add to DataFrame
        self._add_row(row_data)
        
        # Update tracking
        self.current_time = timestamp
        self.last_collection_time = timestamp
        
        # Performance tracking
        collection_time = time.time() - start_time
        self._collection_times.append(collection_time)
        if len(self._collection_times) > 1000:
            self._collection_times = self._collection_times[-100:]  # Keep last 100
        
        return row_data
    
    def _add_row(self, row_data: Dict[str, Any]) -> None:
        """
        Add a row of data to the DataFrame with memory management.
        
        Args:
            row_data: Dictionary of state variable values
        """
        # Create new row DataFrame
        new_row = pd.DataFrame([row_data])
        
        # Concatenate with existing data
        if self.data.empty:
            self.data = new_row
        else:
            self.data = pd.concat([self.data, new_row], ignore_index=True)
        
        self.row_count += 1
        
        # Memory management
        if self.auto_manage_memory and len(self.data) > self.max_rows:
            self._manage_memory()
    
    def _manage_memory(self) -> None:
        """Manage memory by removing old data when limit is exceeded."""
        if len(self.data) > self.max_rows:
            # Keep most recent 80% of data
            keep_rows = int(self.max_rows * 0.8)
            rows_to_remove = len(self.data) - keep_rows
            
            self.data = self.data.tail(keep_rows).reset_index(drop=True)
            
            warnings.warn(f"Memory management: Removed {rows_to_remove} old rows, keeping {keep_rows} recent rows")
    
    def get_variable_history(self, variable_name: str, 
                           time_range: Optional[Tuple[float, float]] = None) -> pd.Series:
        """
        Get time series for a specific variable.
        
        Args:
            variable_name: Name of the variable
            time_range: Optional tuple of (start_time, end_time) to filter data
            
        Returns:
            pandas Series with the variable's time series data
        """
        if variable_name not in self.data.columns:
            warnings.warn(f"Variable '{variable_name}' not found in data")
            return pd.Series(dtype=float)
        
        if time_range is not None:
            start_time, end_time = time_range
            mask = (self.data['time'] >= start_time) & (self.data['time'] <= end_time)
            return self.data.loc[mask, variable_name]
        
        return self.data[variable_name]
    
    def get_time_series(self, variable_names: List[str],
                       time_range: Optional[Tuple[float, float]] = None) -> pd.DataFrame:
        """
        Get time series DataFrame for multiple variables.
        
        Args:
            variable_names: List of variable names to include
            time_range: Optional tuple of (start_time, end_time) to filter data
            
        Returns:
            pandas DataFrame with time and selected variables
        """
        # Always include time column
        columns = ['time'] + [name for name in variable_names if name in self.data.columns]
        
        # Check for missing variables
        missing = [name for name in variable_names if name not in self.data.columns]
        if missing:
            warnings.warn(f"Variables not found in data: {missing}")
        
        if time_range is not None:
            start_time, end_time = time_range
            mask = (self.data['time'] >= start_time) & (self.data['time'] <= end_time)
            return self.data.loc[mask, columns]
        
        return self.data[columns]
    
    def export_to_csv(self, filename: str, 
                     time_range: Optional[Tuple[float, float]] = None,
                     variables: Optional[List[str]] = None) -> None:
        """
        Export data to CSV file.
        
        Args:
            filename: Output CSV filename
            time_range: Optional tuple of (start_time, end_time) to filter data
            variables: Optional list of variables to include (default: all)
        """
        # Determine which data to export
        if variables is not None:
            data_to_export = self.get_time_series(variables, time_range)
        else:
            if time_range is not None:
                start_time, end_time = time_range
                mask = (self.data['time'] >= start_time) & (self.data['time'] <= end_time)
                data_to_export = self.data[mask]
            else:
                data_to_export = self.data
        
        # Export to CSV
        data_to_export.to_csv(filename, index=False)
        print(f"Exported {len(data_to_export)} rows to {filename}")
    
    def export_by_category(self, category: str, filename: str,
                          time_range: Optional[Tuple[float, float]] = None) -> None:
        """
        Export only variables from a specific category.
        
        Args:
            category: Category name (e.g., "primary", "secondary")
            filename: Output CSV filename
            time_range: Optional time range filter
        """
        # Get variables for this category
        category_vars = [col for col in self.data.columns 
                        if col.startswith(f'{category}.') or col == 'time']
        
        if not category_vars:
            warnings.warn(f"No variables found for category '{category}'")
            return
        
        # Export filtered data
        if time_range is not None:
            start_time, end_time = time_range
            mask = (self.data['time'] >= start_time) & (self.data['time'] <= end_time)
            data_to_export = self.data.loc[mask, category_vars]
        else:
            data_to_export = self.data[category_vars]
        
        data_to_export.to_csv(filename, index=False)
        print(f"Exported {len(data_to_export)} rows of {category} data to {filename}")
    
    def export_by_subcategory(self, category: str, subcategory: str, filename: str,
                             time_range: Optional[Tuple[float, float]] = None) -> None:
        """
        Export only variables from a specific subcategory.
        
        Args:
            category: Category name (e.g., "primary")
            subcategory: Subcategory name (e.g., "neutronics")
            filename: Output CSV filename
            time_range: Optional time range filter
        """
        # Get variables for this subcategory
        prefix = f'{category}.{subcategory}.'
        subcategory_vars = ['time'] + [col for col in self.data.columns if col.startswith(prefix)]
        
        if len(subcategory_vars) == 1:  # Only 'time' column
            warnings.warn(f"No variables found for subcategory '{category}.{subcategory}'")
            return
        
        # Export filtered data
        if time_range is not None:
            start_time, end_time = time_range
            mask = (self.data['time'] >= start_time) & (self.data['time'] <= end_time)
            data_to_export = self.data.loc[mask, subcategory_vars]
        else:
            data_to_export = self.data[subcategory_vars]
        
        data_to_export.to_csv(filename, index=False)
        print(f"Exported {len(data_to_export)} rows of {category}.{subcategory} data to {filename}")
    
    def export_summary_statistics(self, filename: str) -> None:
        """
        Export statistical summary of all variables.
        
        Args:
            filename: Output CSV filename for summary statistics
        """
        if self.data.empty:
            warnings.warn("No data available for summary statistics")
            return
        
        # Calculate summary statistics
        summary = self.data.describe()
        
        # Add additional statistics
        summary.loc['count_non_null'] = self.data.count()
        summary.loc['null_count'] = self.data.isnull().sum()
        summary.loc['data_type'] = self.data.dtypes.astype(str)
        
        # Export summary
        summary.to_csv(filename)
        print(f"Exported summary statistics to {filename}")
    
    def get_available_variables(self) -> List[str]:
        """
        Get list of all available variables in the current dataset.
        
        Returns:
            List of variable names
        """
        return [col for col in self.data.columns if col != 'time']
    
    def get_available_categories(self) -> List[str]:
        """
        Get list of all available categories in the current dataset.
        
        Returns:
            List of category names
        """
        categories = set()
        for col in self.data.columns:
            if col != 'time' and '.' in col:
                category = col.split('.')[0]
                categories.add(category)
        return sorted(list(categories))
    
    def get_available_subcategories(self, category: str) -> List[str]:
        """
        Get list of all available subcategories for a given category.
        
        Args:
            category: Category name
            
        Returns:
            List of subcategory names
        """
        subcategories = set()
        prefix = f'{category}.'
        for col in self.data.columns:
            if col.startswith(prefix) and col.count('.') >= 2:
                parts = col.split('.')
                if len(parts) >= 3:
                    subcategory = parts[1]
                    subcategories.add(subcategory)
        return sorted(list(subcategories))
    
    def get_data_info(self) -> Dict[str, Any]:
        """
        Get information about the current dataset.
        
        Returns:
            Dictionary with dataset information
        """
        if self.data.empty:
            return {
                'total_rows': 0,
                'total_variables': 0,
                'time_range': None,
                'categories': [],
                'memory_usage_mb': 0
            }
        
        return {
            'total_rows': len(self.data),
            'total_variables': len(self.data.columns) - 1,  # Exclude 'time'
            'time_range': (self.data['time'].min(), self.data['time'].max()),
            'categories': self.get_available_categories(),
            'memory_usage_mb': self.data.memory_usage(deep=True).sum() / 1024 / 1024,
            'avg_collection_time_ms': np.mean(self._collection_times) * 1000 if self._collection_times else 0
        }
    
    def clear_data(self) -> None:
        """Clear all collected data but keep registry and providers."""
        self.data = pd.DataFrame()
        self.row_count = 0
        self.current_time = 0.0
        self.last_collection_time = None
        self._collection_times.clear()
    
    
    def register_instance(self, instance: Any, instance_id: str, category: StateCategory, subcategory: str, 
                         registration_info: Optional[dict] = None) -> None:
        """
        Register a component instance with unique state variables and metadata.
        
        This method is used by the @auto_register decorator to register individual
        component instances with instance-specific state variable names and
        automatically generated component metadata.
        
        Args:
            instance: Component instance
            instance_id: Unique instance identifier (e.g., "FWP-1A", "SG-001")
            category: Component category enum
            subcategory: Component subcategory string
            registration_info: Optional registration info from @auto_register decorator
        """
        # Check if this is an auto-generated ID (format: CODE-###)
        is_auto_generated_id = (instance_id and 
                               len(instance_id.split('-')) == 2 and 
                               instance_id.split('-')[1].isdigit() and
                               len(instance_id.split('-')[1]) == 3)
        
        # Generate state variables with instance-specific names
        if hasattr(instance, 'get_state_dict'):
            try:
                state_dict = instance.get_state_dict()
                state_variables = {}
                
                for var_name, value in state_dict.items():
                    # Create hierarchical name based on whether ID is auto-generated
                    if is_auto_generated_id:
                        # For auto-generated IDs, use: category.subcategory.variable
                        full_name = f"{category.value}.{subcategory}.{var_name}"
                        subcategory_name = subcategory
                        description = f"{subcategory} {var_name}"
                    else:
                        # For real IDs, use: category.subcategory_instance.variable
                        full_name = f"{category.value}.{subcategory}_{instance_id}.{var_name}"
                        subcategory_name = f"{subcategory}_{instance_id}"
                        description = f"{instance_id} {var_name}"
                    
                    state_variables[full_name] = StateVariable(
                        name=full_name,
                        category=category,
                        subcategory=subcategory_name,
                        unit=self._infer_unit(var_name, value),
                        description=description,
                        data_type=type(value),
                        valid_range=self._infer_valid_range(var_name, value),
                        is_critical=self._auto_detect_critical(var_name)
                    )
                
                # Register state variables
                self.registry.register_variables(state_variables)
                
            except Exception as e:
                warnings.warn(f"Failed to generate state variables for {instance_id}: {e}")
        
        # Add to provider list with appropriate category
        if is_auto_generated_id:
            provider_category = f"{category.value}.{subcategory}"
        else:
            provider_category = f"{category.value}.{subcategory}_{instance_id}"
        
        self.providers.append((instance, provider_category))
        
        # Generate and register component metadata
        try:
            metadata = self._generate_component_metadata(
                instance, instance_id, category, subcategory, registration_info
            )
            ComponentRegistry.register_component(instance, metadata)
            
            # Update the ComponentRegistry entry with the actual state variables
            if hasattr(instance, 'get_state_dict'):
                try:
                    state_dict = instance.get_state_dict()
                    # Convert state_dict to StateVariable format
                    component_state_vars = {}
                    for var_name, value in state_dict.items():
                        # Create the full hierarchical name that matches what's in the StateManager
                        if is_auto_generated_id:
                            full_name = f"{category.value}.{subcategory}.{var_name}"
                        else:
                            full_name = f"{category.value}.{subcategory}_{instance_id}.{var_name}"
                        
                        component_state_vars[full_name] = StateVariable(
                            name=full_name,
                            category=category,
                            subcategory=subcategory if is_auto_generated_id else f"{subcategory}_{instance_id}",
                            unit=self._infer_unit(var_name, value),
                            description=f"{instance_id} {var_name}",
                            data_type=type(value),
                            valid_range=self._infer_valid_range(var_name, value),
                            is_critical=self._auto_detect_critical(var_name)
                        )
                    
                    # Update the ComponentRegistry with the state variables
                    component_info = ComponentRegistry.get_component(instance_id)
                    if component_info:
                        component_info['state_variables'] = component_state_vars
                        
                except Exception as e:
                    warnings.warn(f"Failed to link state variables for {instance_id}: {e}")
                    
        except Exception as e:
            warnings.warn(f"Failed to generate metadata for {instance_id}: {e}")
            import traceback
            traceback.print_exc()
        
        # Track the instance
        self._registered_instances[instance_id] = {
            'instance': instance,
            'category': category,
            'subcategory': subcategory,
            'class_name': instance.__class__.__name__,
            'provider_category': provider_category
        }
    
    @classmethod
    def get_next_instance_number(cls, component_code: str) -> int:
        """
        Get next available instance number for component code.
        
        Args:
            component_code: Component code (e.g., "FW", "TB", "SG")
            
        Returns:
            Next available instance number
        """
        # Use class-level counters for global instance numbering
        if not hasattr(cls, '_global_instance_counters'):
            cls._global_instance_counters = {}
        
        if component_code not in cls._global_instance_counters:
            cls._global_instance_counters[component_code] = 0
        cls._global_instance_counters[component_code] += 1
        return cls._global_instance_counters[component_code]
    
    def get_instances_by_class(self, target_class) -> Dict[str, Any]:
        """
        Get all registered instances of a specific class.
        
        Args:
            target_class: Python class to search for
            
        Returns:
            Dictionary mapping instance_id to instance object
        """
        return {
            instance_id: info['instance'] 
            for instance_id, info in self._registered_instances.items()
            if info['class_name'] == target_class.__name__
        }
    
    def get_instances_by_category(self, category: str) -> Dict[str, Any]:
        """
        Get all registered instances in a category.
        
        Args:
            category: Category name (e.g., "secondary", "primary")
            
        Returns:
            Dictionary mapping instance_id to instance object
        """
        return {
            instance_id: info['instance']
            for instance_id, info in self._registered_instances.items() 
            if info['category'].value == category.lower()
        }
    
    def get_instances_by_subcategory(self, category: str, subcategory: str) -> Dict[str, Any]:
        """
        Get all registered instances in a specific subcategory.
        
        Args:
            category: Category name (e.g., "secondary")
            subcategory: Subcategory name (e.g., "feedwater")
            
        Returns:
            Dictionary mapping instance_id to instance object
        """
        return {
            instance_id: info['instance']
            for instance_id, info in self._registered_instances.items()
            if (info['category'].value == category.lower() and 
                info['subcategory'] == subcategory)
        }
    
    def get_registered_instance_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered instances.
        
        Returns:
            Dictionary with instance information
        """
        return self._registered_instances.copy()
    
    # Metadata-driven query methods
    
    def get_components_by_equipment_type(self, equipment_type: EquipmentType) -> Dict[str, Any]:
        """
        Get all components of a specific equipment type using metadata.
        
        Args:
            equipment_type: Equipment type to search for
            
        Returns:
            Dictionary mapping component_id to component info
        """
        components = ComponentRegistry.get_components_by_type(equipment_type)
        return {comp_id: info for comp_id, info in components.items()}
    
    def get_components_with_capability(self, capability: str) -> Dict[str, Any]:
        """
        Get all components that have a specific capability using metadata.
        
        Args:
            capability: Capability to search for (e.g., "flow_control", "steam_flow")
            
        Returns:
            Dictionary mapping component_id to component info
        """
        components = ComponentRegistry.get_components_with_capability(capability)
        return {comp_id: info for comp_id, info in components.items()}
    
    def get_components_by_system(self, system: str) -> Dict[str, Any]:
        """
        Get all components in a specific system using metadata.
        
        Args:
            system: System name (e.g., "secondary", "primary")
            
        Returns:
            Dictionary mapping component_id to component info
        """
        components = ComponentRegistry.get_components_by_system(system)
        return {comp_id: info for comp_id, info in components.items()}
    
    def get_component_metadata(self, component_id: str) -> Optional[ComponentMetadata]:
        """
        Get metadata for a specific component.
        
        Args:
            component_id: Component ID to look up
            
        Returns:
            ComponentMetadata instance or None if not found
        """
        component_info = ComponentRegistry.get_component(component_id)
        if component_info:
            return component_info['metadata']
        return None
    
    def get_component_summary(self) -> str:
        """
        Get a summary of all registered components with metadata.
        
        Returns:
            Formatted summary string
        """
        return ComponentRegistry.generate_component_summary()
    
    def update_component_description(self, component_id: str, description: str) -> bool:
        """
        Update the description of a registered component.
        
        Args:
            component_id: Component ID
            description: New description
            
        Returns:
            True if successful, False if component not found
        """
        return ComponentRegistry.update_component_description(component_id, description)
    
    def find_components_with_description(self) -> Dict[str, str]:
        """
        Get all components that have descriptions.
        
        Returns:
            Dictionary mapping component_id to description
        """
        return ComponentRegistry.find_components_with_description()
    
    def _infer_unit(self, name: str, value: Any) -> str:
        """Infer units from variable names (copied from auto_provider for compatibility)"""
        name_lower = name.lower()
        
        # Temperature units
        if any(word in name_lower for word in ['temperature', 'temp']):
            return "°C"
        
        # Pressure units
        if any(word in name_lower for word in ['pressure']):
            return "MPa"
        
        # Flow units
        if any(word in name_lower for word in ['flow', 'rate']) and 'temp' not in name_lower:
            return "kg/s"
        
        # Power units
        if any(word in name_lower for word in ['power']):
            return "MW"
        
        # Speed units
        if any(word in name_lower for word in ['speed', 'rpm']):
            return "rpm"
        
        # Percentage units
        if any(word in name_lower for word in ['percent', 'efficiency', 'level', 'position']) or name_lower.endswith('_pct'):
            return "%"
        
        # Time units
        if any(word in name_lower for word in ['time', 'hours']):
            return "hours"
        
        # Vibration units
        if any(word in name_lower for word in ['vibration']):
            return "mm/s"
        
        # Wear units
        if any(word in name_lower for word in ['wear', 'erosion']):
            return "mm"
        
        # Default to dimensionless
        return "dimensionless"
    
    def _infer_valid_range(self, name: str, value: Any) -> Optional[Tuple[float, float]]:
        """Infer reasonable valid ranges for variables (copied from auto_provider for compatibility)"""
        if not isinstance(value, (int, float)):
            return None
        
        name_lower = name.lower()
        
        # Temperature ranges
        if 'temperature' in name_lower or 'temp' in name_lower:
            return (0.0, 600.0)  # 0°C to 600°C
        
        # Pressure ranges
        if 'pressure' in name_lower:
            return (0.0, 20.0)  # 0 to 20 MPa
        
        # Flow ranges
        if 'flow' in name_lower and 'temp' not in name_lower:
            return (0.0, 5000.0)  # 0 to 5000 kg/s
        
        # Power ranges
        if 'power' in name_lower:
            return (0.0, 1500.0)  # 0 to 1500 MW
        
        # Percentage ranges
        if any(word in name_lower for word in ['percent', 'efficiency', 'level', 'position']) or name_lower.endswith('_pct'):
            return (0.0, 100.0)
        
        # Speed ranges
        if 'speed' in name_lower or 'rpm' in name_lower:
            return (0.0, 4000.0)  # 0 to 4000 RPM
        
        # Vibration ranges
        if 'vibration' in name_lower:
            return (0.0, 50.0)  # 0 to 50 mm/s
        
        # Wear ranges
        if 'wear' in name_lower or 'erosion' in name_lower:
            return (0.0, 10.0)  # 0 to 10 mm
        
        return None
    
    def _auto_detect_critical(self, name: str) -> bool:
        """Automatically detect critical parameters (copied from auto_provider for compatibility)"""
        critical_keywords = [
            'trip', 'scram', 'safety', 'emergency', 'alarm',
            'temperature', 'pressure', 'flow', 'speed', 'vibration',
            'power', 'level', 'available', 'status'
        ]
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in critical_keywords)
    
    def _generate_component_metadata(self, instance: Any, instance_id: str, category: StateCategory, 
                                   subcategory: str, registration_info: Optional[dict] = None) -> ComponentMetadata:
        """
        Generate ComponentMetadata for a registered instance.
        
        Args:
            instance: Component instance
            instance_id: Unique instance identifier
            category: Component category enum
            subcategory: Component subcategory string
            registration_info: Optional registration info from @auto_register decorator
            
        Returns:
            ComponentMetadata instance
        """
        import time
        
        # Extract metadata parameters from registration info
        if registration_info:
            explicit_equipment_type = registration_info.get('equipment_type')
            explicit_description = registration_info.get('description')
            explicit_design_params = registration_info.get('design_parameters') or {}
        else:
            explicit_equipment_type = None
            explicit_description = None
            explicit_design_params = {}
        
        # 1. Determine equipment type
        if explicit_equipment_type:
            equipment_type = explicit_equipment_type
        else:
            equipment_type = infer_equipment_type_from_class_name(instance.__class__.__name__)
        
        # 2. Infer capabilities from state variables
        capabilities = {}
        if hasattr(instance, 'get_state_dict'):
            try:
                state_dict = instance.get_state_dict()
                # Convert to StateVariable format for capability inference
                state_variables = {}
                for var_name, value in state_dict.items():
                    state_variables[var_name] = StateVariable(
                        name=var_name,
                        category=category,
                        subcategory=subcategory,
                        unit=self._infer_unit(var_name, value),
                        description=f"{var_name}",
                        data_type=type(value),
                        valid_range=self._infer_valid_range(var_name, value),
                        is_critical=self._auto_detect_critical(var_name)
                    )
                capabilities = infer_capabilities_from_state_variables(state_variables)
            except Exception as e:
                warnings.warn(f"Failed to infer capabilities for {instance_id}: {e}")
        
        # 3. Extract design parameters
        design_parameters = explicit_design_params.copy()
        try:
            auto_design_params = extract_design_parameters_from_config(instance)
            design_parameters.update(auto_design_params)
        except Exception as e:
            warnings.warn(f"Failed to extract design parameters for {instance_id}: {e}")
        
        # 4. Create ComponentMetadata
        metadata = ComponentMetadata(
            component_id=instance_id,
            equipment_type=equipment_type,
            system=category.value,
            subsystem=subcategory,
            capabilities=capabilities,
            design_parameters=design_parameters,
            description=explicit_description,
            instance_class=instance.__class__.__name__,
            module_path=instance.__class__.__module__,
            registration_time=time.time()
        )
        
        return metadata
    
    def discover_registered_components(self) -> None:
        """
        Discover and register components that used @auto_register decorator.
        
        This method replaces the old auto_discover_providers() tree traversal
        with a simple collection of components that registered themselves
        via the @auto_register decorator.
        """
        # Import here to avoid circular imports
        from .auto_register import get_registered_info
        
        # Check for pending registrations from @auto_register decorator
        if hasattr(self.__class__, '_pending_registrations'):
            pending = self.__class__._pending_registrations
            registered_count = 0
            
            for registration in pending:
                try:
                    self.register_instance(
                        instance=registration['instance'],
                        instance_id=registration['instance_id'],
                        category=registration['category'],
                        subcategory=registration['subcategory'],
                        registration_info=registration.get('registration_info')
                    )
                    registered_count += 1
                except Exception as e:
                    warnings.warn(f"Failed to register component {registration['instance_id']}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Clear pending registrations after processing
            self.__class__._pending_registrations = []
            
            print(f"Component discovery complete: Registered {registered_count} @auto_register components")
        else:
            print("Component discovery complete: No @auto_register components found")
    
    def reset(self) -> None:
        """Reset the state manager completely."""
        self.clear_data()
        self.registry.clear()
        self.providers.clear()
        self._instance_counters.clear()
        self._registered_instances.clear()
        
        # Clear any pending registrations
        if hasattr(self.__class__, '_pending_registrations'):
            self.__class__._pending_registrations = []
    
    def __repr__(self) -> str:
        """String representation of state manager."""
        info = self.get_data_info()
        instance_count = len(self._registered_instances)
        return (f"StateManager(rows={info['total_rows']}, "
                f"variables={info['total_variables']}, "
                f"categories={len(info['categories'])}, "
                f"instances={instance_count}, "
                f"memory={info['memory_usage_mb']:.1f}MB)")
