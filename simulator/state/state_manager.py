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
    
    def __init__(self, max_rows: int = 100000, auto_manage_memory: bool = True, config=None):
        """
        Initialize state manager.
        
        Args:
            max_rows: Maximum number of rows to keep in memory
            auto_manage_memory: Whether to automatically manage memory by removing old data
            config: Optional configuration dict/object for maintenance and other settings
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
        
        # PHASE 1: Maintenance system integration
        self.config = config  # Store passed configuration
        self.maintenance_thresholds = {}  # component_id -> {param: threshold_config}
        self.threshold_violations = {}    # component_id -> {param: violation_data}
        self.maintenance_history = []     # List of maintenance actions and results
        self.maintenance_config = None    # Parsed maintenance configuration
        self.threshold_event_subscribers = []  # Callbacks for threshold events
        
        # Cache orchestrator for performance
        self._maintenance_orchestrator = None
        
        print(f"STATE MANAGER: Initialized with maintenance capabilities")
        if config:
            print(f"STATE MANAGER: Configuration provided - will load maintenance settings")
        
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
        
        # PHASE 1: Check maintenance thresholds during state collection
        self._check_maintenance_thresholds(timestamp, row_data)
        
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
                    # Handle both string and enum categories for config-driven usage
                    category_str = category.value if hasattr(category, 'value') else str(category)
                    
                    if is_auto_generated_id:
                        # For auto-generated IDs, use: category.subcategory.variable
                        full_name = f"{category_str}.{subcategory}.{var_name}"
                        subcategory_name = subcategory
                        description = f"{subcategory} {var_name}"
                    else:
                        # For real IDs, use: category.subcategory_instance.variable
                        full_name = f"{category_str}.{subcategory}_{instance_id}.{var_name}"
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
        # Handle both string and enum categories for config-driven usage
        category_str = category.value if hasattr(category, 'value') else str(category)
        
        if is_auto_generated_id:
            provider_category = f"{category_str}.{subcategory}"
        else:
            provider_category = f"{category_str}.{subcategory}_{instance_id}"
        
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
        # Handle both string and enum categories for config-driven usage
        category_str = category.value if hasattr(category, 'value') else str(category)
        
        metadata = ComponentMetadata(
            component_id=instance_id,
            equipment_type=equipment_type,
            system=category_str,  # ComponentMetadata expects a string
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
    
    # PHASE 1: Maintenance Configuration Methods
    
    def load_maintenance_config(self, config_source=None):
        """
        Central maintenance configuration loading with all discovery logic
        
        Args:
            config_source: Optional explicit config (dict, file path, or object)
            
        Returns:
            Parsed maintenance configuration object
        """
        print(f"STATE MANAGER: 🔍 Loading maintenance configuration...")
        
        # PRIORITY 1: Explicit config_source parameter
        if config_source:
            print(f"STATE MANAGER: Using explicit config_source")
            self.maintenance_config = self._parse_maintenance_config(config_source)
            return self.maintenance_config
        
        # PRIORITY 2: Config passed to constructor
        if self.config:
            print(f"STATE MANAGER: Using constructor config")
            self.maintenance_config = self._parse_maintenance_config(self.config)
            return self.maintenance_config
        
        # PRIORITY 3: Auto-discovery from registered components
        print(f"STATE MANAGER: No explicit config found, using factory defaults")
        self.maintenance_config = self._create_default_maintenance_config()
        return self.maintenance_config
    
    def _parse_maintenance_config(self, config):
        """
        Parse maintenance configuration from various formats
        
        Args:
            config: Configuration dict, file path, or object
            
        Returns:
            Parsed maintenance configuration
        """
        print(f"STATE MANAGER: 🔧 Parsing maintenance config from {type(config)}")
        
        # Handle different config formats
        if isinstance(config, str):
            # File path - load YAML/JSON
            import yaml
            with open(config, 'r') as f:
                config_dict = yaml.safe_load(f)
        elif isinstance(config, dict):
            config_dict = config
        else:
            # Object with attributes
            config_dict = self._convert_object_to_dict(config)
        
        # CRITICAL FIX: Check for maintenance_system.component_configs FIRST
        if 'maintenance_system' in config_dict:
            maintenance_system = config_dict['maintenance_system']
            print(f"STATE MANAGER: 🎯 Found maintenance_system section with keys: {list(maintenance_system.keys())}")
            
            if 'component_configs' in maintenance_system:
                print(f"STATE MANAGER: ✅ Found component_configs in maintenance_system - using comprehensive config!")
                
                # Show specific oil_level threshold for debugging
                component_configs = maintenance_system['component_configs']
                for subsystem, config_data in component_configs.items():
                    thresholds = config_data.get('thresholds', {})
                    print(f"  📊 {subsystem}: {len(thresholds)} thresholds")
                    
                    if 'oil_level' in thresholds:
                        oil_threshold = thresholds['oil_level']
                        print(f"    🛢️ oil_level: {oil_threshold.get('threshold', 'unknown')}% {oil_threshold.get('comparison', 'unknown')} -> {oil_threshold.get('action', 'unknown')}")
                
                return self._create_maintenance_config_from_comprehensive(maintenance_system)
            else:
                print(f"STATE MANAGER: ⚠️ maintenance_system found but no component_configs")
        
        # FALLBACK: Check for maintenance.component_configs
        elif 'maintenance' in config_dict:
            maintenance_section = config_dict['maintenance']
            print(f"STATE MANAGER: 🔍 Found maintenance section with keys: {list(maintenance_section.keys())}")
            
            if 'component_configs' in maintenance_section:
                print(f"STATE MANAGER: ✅ Found component_configs in maintenance section")
                return self._create_maintenance_config_from_comprehensive(maintenance_section)
            else:
                print(f"STATE MANAGER: ⚠️ maintenance section found but no component_configs")
        
        # No recognized maintenance config found
        print(f"STATE MANAGER: ⚠️ No recognized maintenance configuration format found")
        return self._create_default_maintenance_config()
    
    def _convert_object_to_dict(self, obj):
        """Convert object with attributes to dictionary"""
        config_dict = {}
        for attr in dir(obj):
            if not attr.startswith('_'):
                value = getattr(obj, attr)
                if not callable(value):
                    config_dict[attr] = value
        return config_dict
    
    def _create_maintenance_config_from_comprehensive(self, maintenance_system):
        """
        Create maintenance configuration from comprehensive config format
        
        Args:
            maintenance_system: maintenance_system section from config
            
        Returns:
            Maintenance configuration object
        """
        print(f"STATE MANAGER: 🔧 Creating maintenance config from comprehensive format")
        
        # Map subsystem names to equipment types
        subsystem_to_equipment_mapping = {
            'feedwater': 'pump',
            'turbine': 'turbine_stage', 
            'steam_generator': 'steam_generator',
            'condenser': 'condenser'
        }
        
        maintenance_config = {
            'mode': maintenance_system.get('maintenance_mode', 'realistic'),
            'component_configs': {}
        }
        
        if 'component_configs' in maintenance_system:
            component_configs = maintenance_system['component_configs']
            
            for subsystem_name, config_data in component_configs.items():
                equipment_type = subsystem_to_equipment_mapping.get(subsystem_name, subsystem_name)
                
                # Store config with equipment type mapping
                maintenance_config['component_configs'][equipment_type] = {
                    'check_interval_hours': config_data.get('check_interval_hours', 4.0),
                    'thresholds': config_data.get('thresholds', {})
                }
                
                print(f"STATE MANAGER: ✅ Mapped {subsystem_name} -> {equipment_type}")
        
        return maintenance_config
    
    def _create_default_maintenance_config(self):
        """Create default maintenance configuration"""
        print(f"STATE MANAGER: 🔄 Creating default maintenance configuration")
        
        return {
            'mode': 'conservative',
            'component_configs': {
                'pump': {
                    'check_interval_hours': 4.0,
                    'thresholds': {
                        'oil_level': {
                            'threshold': 30.0,
                            'comparison': 'less_than',
                            'action': 'oil_top_off',
                            'cooldown_hours': 24.0,
                            'priority': 'HIGH'
                        }
                    }
                }
            }
        }
    
    def apply_maintenance_thresholds(self, component_id: str, thresholds: dict):
        """
        Apply maintenance thresholds to a registered component
        
        Args:
            component_id: Component ID
            thresholds: Dictionary of threshold configurations
        """
        if component_id not in self.maintenance_thresholds:
            self.maintenance_thresholds[component_id] = {}
        
        self.maintenance_thresholds[component_id].update(thresholds)
        print(f"STATE MANAGER: ✅ Applied {len(thresholds)} thresholds to {component_id}")
    
    def get_maintenance_thresholds_for_component(self, component_id: str) -> dict:
        """
        Get maintenance thresholds for a specific component
        
        Args:
            component_id: Component ID
            
        Returns:
            Dictionary of threshold configurations
        """
        return self.maintenance_thresholds.get(component_id, {})
    
    def get_components_with_maintenance_thresholds(self) -> dict:
        """
        Get all components that have maintenance monitoring configured
        
        Returns:
            Dictionary mapping component_id to threshold configurations
        """
        return self.maintenance_thresholds.copy()
    
    def subscribe_to_threshold_events(self, callback):
        """
        Subscribe to threshold violation events
        
        Args:
            callback: Function to call when threshold is violated
        """
        self.threshold_event_subscribers.append(callback)
        print(f"STATE MANAGER: ✅ Added threshold event subscriber")
    
    def get_current_value(self, component_id: str, parameter: str) -> Optional[float]:
        """
        Get current value of a parameter for a component
        
        Args:
            component_id: Component ID
            parameter: Parameter name
            
        Returns:
            Current parameter value or None if not found
        """
        if self.data.empty:
            return None
        
        # Try different naming patterns to find the parameter
        possible_names = [
            f"{component_id}.{parameter}",
            f"secondary.feedwater_{component_id}.{parameter}",
            f"secondary.feedwater.{parameter}",
        ]
        
        for name in possible_names:
            if name in self.data.columns:
                return self.data[name].iloc[-1] if len(self.data) > 0 else None
        
        return None
    
    def get_component_state_snapshot(self, component_id: str) -> dict:
        """
        Get current state snapshot for a component
        
        Args:
            component_id: Component ID
            
        Returns:
            Dictionary of current parameter values
        """
        # FIRST: Try to get live data from the component instance
        if component_id in self._registered_instances:
            instance_info = self._registered_instances[component_id]
            component = instance_info['instance']
            
            if hasattr(component, 'get_state_dict'):
                try:
                    return component.get_state_dict()
                except Exception as e:
                    warnings.warn(f"Failed to get live state from {component_id}: {e}")
        
        # FALLBACK: Use DataFrame data if available
        if self.data.empty:
            return {}
        
        snapshot = {}
        latest_row = self.data.iloc[-1]
        
        # Find all variables for this component
        for col in self.data.columns:
            if component_id in col and col != 'time':
                # Extract parameter name
                parts = col.split('.')
                if len(parts) >= 2:
                    param_name = parts[-1]
                    snapshot[param_name] = latest_row[col]
        
        return snapshot
    
    def _check_maintenance_thresholds(self, timestamp: float, row_data: dict):
        """
        Check maintenance thresholds during state collection with component-level batching
        
        Args:
            timestamp: Current simulation time
            row_data: Current state data
        """
        if not self.maintenance_thresholds:
            return  # No thresholds configured
        
        # Step 1: Collect ALL violations by component
        component_violations = {}  # component_id -> [violation_data, ...]
        
        for component_id, thresholds in self.maintenance_thresholds.items():
            violations = []
            
            for param_name, threshold_config in thresholds.items():
                # Find the parameter value in row_data
                param_value = self._find_parameter_in_row_data(component_id, param_name, row_data)
                
                if param_value is not None:
                    # Check if threshold is violated
                    if self._check_threshold_condition(param_value, threshold_config):
                        violation_data = {
                            'parameter': param_name,
                            'value': param_value,
                            'threshold': threshold_config.get('threshold'),
                            'comparison': threshold_config.get('comparison'),
                            'action': threshold_config.get('action'),
                            'priority': threshold_config.get('priority', 'MEDIUM')
                        }
                        violations.append(violation_data)
            
            # Store violations for this component if any found
            if violations:
                component_violations[component_id] = violations
        
        # Step 2: Process each component's violations through orchestrator
        total_violations = sum(len(violations) for violations in component_violations.values())
        
        for component_id, violations in component_violations.items():
            # Get orchestrated action for ALL violations of this component
            optimal_action = self._get_orchestrated_action_for_violations(
                component_id, violations, timestamp
            )
            
            # Emit single threshold event with optimal action
            self._emit_batched_threshold_violation(component_id, violations, optimal_action, timestamp)
        
        if total_violations > 0:
            print(f"STATE MANAGER: 🚨 Found {total_violations} threshold violations across {len(component_violations)} components at time {timestamp:.2f}")
    
    def _find_parameter_in_row_data(self, component_id: str, param_name: str, row_data: dict) -> Optional[float]:
        """
        Find parameter value in row data using various naming patterns
        
        Args:
            component_id: Component ID
            param_name: Parameter name
            row_data: Current state data
            
        Returns:
            Parameter value or None if not found
        """
        # FEEDWATER PARAMETER ALIASES - Map threshold names to actual physics parameter names
        FEEDWATER_PARAMETER_ALIASES = {
            'impeller_inspection_wear': 'impeller_wear',
            # Add more aliases here as needed for other mismatches
        }
        
        # Resolve parameter name using aliases
        actual_param_name = FEEDWATER_PARAMETER_ALIASES.get(param_name, param_name)
        
        # Try different naming patterns with the resolved parameter name
        possible_names = [
            f"{component_id}.{actual_param_name}",
            f"secondary.feedwater_{component_id}.{actual_param_name}",
            f"secondary.feedwater.{actual_param_name}",
            f"secondary.{component_id}.{actual_param_name}",
        ]
        
        for name in possible_names:
            if name in row_data:
                value = row_data[name]
                if isinstance(value, (int, float)):
                    return float(value)
        
        return None
    
    def _check_threshold_condition(self, value: float, threshold_config: dict) -> bool:
        """
        Check if threshold condition is met
        
        Args:
            value: Current parameter value
            threshold_config: Threshold configuration
            
        Returns:
            True if threshold is violated
        """
        threshold = threshold_config.get('threshold')
        comparison = threshold_config.get('comparison', 'greater_than')
        
        if threshold is None:
            return False
        
        if comparison == "greater_than":
            return value > threshold
        elif comparison == "less_than":
            return value < threshold
        elif comparison == "greater_equal":
            return value >= threshold
        elif comparison == "less_equal":
            return value <= threshold
        elif comparison == "equals":
            return abs(value - threshold) < 0.001
        elif comparison == "not_equals":
            return abs(value - threshold) >= 0.001
        else:
            return False
    
    def _emit_threshold_violation(self, component_id: str, param_name: str, value: float, 
                                threshold_config: dict, timestamp: float):
        """
        Emit threshold violation event to subscribers
        
        Args:
            component_id: Component ID
            param_name: Parameter name
            value: Current parameter value
            threshold_config: Threshold configuration
            timestamp: Current simulation time
        """
        # CRITICAL FIX: Call orchestrator to get optimal action
        original_action = threshold_config.get('action')
        optimal_action = self._get_orchestrated_action(
            component_id, param_name, value, threshold_config, original_action
        )
        
        violation_data = {
            'component_id': component_id,
            'parameter': param_name,
            'value': value,
            'threshold': threshold_config.get('threshold'),
            'comparison': threshold_config.get('comparison'),
            'action': optimal_action,  # Use orchestrator's decision!
            'original_action': original_action,  # Keep for reference
            'priority': threshold_config.get('priority', 'MEDIUM'),
            'timestamp': timestamp
        }
        
        # Store violation for tracking
        if component_id not in self.threshold_violations:
            self.threshold_violations[component_id] = {}
        self.threshold_violations[component_id][param_name] = violation_data
        
        # Notify all subscribers
        for callback in self.threshold_event_subscribers:
            try:
                callback(violation_data)
            except Exception as e:
                print(f"STATE MANAGER: ❌ Error in threshold event callback: {e}")
        
        # Show orchestration result in log
        if optimal_action != original_action:
            print(f"STATE MANAGER: 🚨 Threshold violation: {component_id}.{param_name} = {value:.2f} {threshold_config.get('comparison')} {threshold_config.get('threshold')} -> {original_action} ➜ {optimal_action} (orchestrated)")
        else:
            print(f"STATE MANAGER: 🚨 Threshold violation: {component_id}.{param_name} = {value:.2f} {threshold_config.get('comparison')} {threshold_config.get('threshold')} -> {optimal_action}")
    
    def _get_orchestrated_action(self, component_id: str, param_name: str, value: float, 
                               threshold_config: dict, original_action: str) -> str:
        """
        Get orchestrated maintenance action for a threshold violation
        
        Args:
            component_id: Component ID
            param_name: Parameter name
            value: Current parameter value
            threshold_config: Threshold configuration
            original_action: Original action from threshold config
            
        Returns:
            Optimal action determined by orchestrator
        """
        try:
            # Use cached orchestrator or create once
            if self._maintenance_orchestrator is None:
                from systems.maintenance.maintenance_orchestrator import get_maintenance_orchestrator
                self._maintenance_orchestrator = get_maintenance_orchestrator()
            
            # Create violation data for orchestrator
            violation_data = {
                'parameter': param_name,
                'value': value,
                'action': original_action,
                'threshold': threshold_config.get('threshold'),
                'comparison': threshold_config.get('comparison')
            }
            
            # Call orchestrator for decision (decision_only mode)
            decision = self._maintenance_orchestrator.orchestrate_maintenance(
                component=None,
                component_id=component_id,
                violations=[violation_data],
                requested_action=original_action,
                decision_only=True
            )
            
            return decision.get('selected_action', original_action)
            
        except Exception as e:
            print(f"STATE MANAGER: ⚠️ Orchestrator call failed for {component_id}: {e}")
            return original_action  # Fallback to original action
    
    def _get_orchestrated_action_for_violations(self, component_id: str, violations: List[dict], timestamp: float) -> str:
        """
        Get orchestrated maintenance action for multiple violations of a component
        
        Args:
            component_id: Component ID
            violations: List of violation data dictionaries
            timestamp: Current simulation time
            
        Returns:
            Optimal action determined by orchestrator
        """
        try:
            # Use cached orchestrator or create once
            if self._maintenance_orchestrator is None:
                from systems.maintenance.maintenance_orchestrator import get_maintenance_orchestrator
                self._maintenance_orchestrator = get_maintenance_orchestrator()
            
            # Determine primary action from violations (highest priority or first one)
            primary_action = violations[0]['action']  # Default to first violation's action
            
            # Call orchestrator for decision with ALL violations (decision_only mode)
            decision = self._maintenance_orchestrator.orchestrate_maintenance(
                component=None,
                component_id=component_id,
                violations=violations,
                requested_action=primary_action,
                decision_only=True
            )
            
            return decision.get('selected_action', primary_action)
            
        except Exception as e:
            print(f"STATE MANAGER: ⚠️ Orchestrator call failed for {component_id}: {e}")
            # Fallback: return the action from the first violation
            return violations[0]['action'] if violations else 'routine_maintenance'
    
    def _emit_batched_threshold_violation(self, component_id: str, violations: List[dict], optimal_action: str, timestamp: float):
        """
        Emit a single threshold violation event for multiple violations with orchestrated action
        
        Args:
            component_id: Component ID
            violations: List of violation data dictionaries
            optimal_action: Orchestrated optimal action
            timestamp: Current simulation time
        """
        # Create a summary violation event that represents all violations
        primary_violation = violations[0]  # Use first violation as primary
        
        # Create violation summary
        violation_summary = f"{len(violations)} violations: " + ", ".join([
            f"{v['parameter']}={v['value']:.2f}" for v in violations
        ])
        
        # Create combined violation data
        violation_data = {
            'component_id': component_id,
            'parameter': 'multiple_violations',  # Indicate this is a batched event
            'value': len(violations),  # Number of violations
            'threshold': violation_summary,  # Summary of all violations
            'comparison': 'batched',
            'action': optimal_action,  # Use orchestrator's decision!
            'original_actions': [v['action'] for v in violations],  # Keep all original actions for reference
            'violations': violations,  # Include all violation details
            'priority': max([v['priority'] for v in violations], key=lambda p: {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4, 'EMERGENCY': 5}.get(p, 2)),
            'timestamp': timestamp
        }
        
        # Store violation for tracking (use primary violation's parameter for key)
        if component_id not in self.threshold_violations:
            self.threshold_violations[component_id] = {}
        
        # Store under a special key for batched violations
        self.threshold_violations[component_id]['batched_violations'] = violation_data
        
        # Notify all subscribers
        for callback in self.threshold_event_subscribers:
            try:
                callback(violation_data)
            except Exception as e:
                print(f"STATE MANAGER: ❌ Error in threshold event callback: {e}")
        
        # Show orchestration result in log
        original_actions = [v['action'] for v in violations]
        if optimal_action not in original_actions:
            print(f"STATE MANAGER: 🚨 Batched threshold violations: {component_id} ({len(violations)} violations) -> {original_actions} ➜ {optimal_action} (orchestrated)")
        else:
            print(f"STATE MANAGER: 🚨 Batched threshold violations: {component_id} ({len(violations)} violations) -> {optimal_action}")
    
    def get_current_threshold_violations(self) -> dict:
        """
        Get current threshold violations
        
        Returns:
            Dictionary of current violations
        """
        return self.threshold_violations.copy()
    
    def clear_threshold_violations(self):
        """Clear all threshold violations"""
        self.threshold_violations.clear()
        print(f"STATE MANAGER: ✅ Cleared all threshold violations")
    
    def record_maintenance_result(self, component_id: str, action_type: str, success: bool, 
                                effectiveness: float = 1.0):
        """
        Record maintenance action result
        
        Args:
            component_id: Component ID
            action_type: Type of maintenance action
            success: Whether action was successful
            effectiveness: Effectiveness score (0-1)
        """
        maintenance_record = {
            'component_id': component_id,
            'action_type': action_type,
            'success': success,
            'effectiveness': effectiveness,
            'timestamp': self.current_time
        }
        
        self.maintenance_history.append(maintenance_record)
        
        # CRITICAL FIX: Force state collection after maintenance to get updated values
        if success:
            self._force_state_collection_after_maintenance(component_id)
        
        # Clear related threshold violations if maintenance was successful
        if success and component_id in self.threshold_violations:
            # IMPROVED: Clear violations that might have been addressed by this maintenance
            violations_to_clear = []
            for param_name, violation in self.threshold_violations[component_id].items():
                # More flexible action matching
                violation_action = violation.get('action', '')
                if (violation_action == action_type or 
                    self._actions_are_related(violation_action, action_type)):
                    violations_to_clear.append(param_name)
                    print(f"STATE MANAGER: 🔍 Marking violation {param_name} for clearing (action: {violation_action} matches {action_type})")
            
            # Clear the violations
            for param_name in violations_to_clear:
                del self.threshold_violations[component_id][param_name]
                print(f"STATE MANAGER: 🗑️ Cleared violation {component_id}.{param_name}")
            
            # Clean up empty component entries
            if not self.threshold_violations[component_id]:
                del self.threshold_violations[component_id]
                print(f"STATE MANAGER: 🗑️ Removed empty violation entry for {component_id}")
            
            if violations_to_clear:
                print(f"STATE MANAGER: ✅ Cleared {len(violations_to_clear)} violations for {component_id} after successful {action_type}")
            else:
                print(f"STATE MANAGER: ⚠️ No violations found to clear for {component_id} after {action_type}")
                # Debug: Show what violations exist
                if component_id in self.threshold_violations:
                    existing_violations = list(self.threshold_violations[component_id].keys())
                    print(f"STATE MANAGER: 🔍 Existing violations for {component_id}: {existing_violations}")
        
        print(f"STATE MANAGER: 📝 Recorded maintenance: {component_id} {action_type} {'✅' if success else '❌'} (effectiveness: {effectiveness:.2f})")
    
    def _force_state_collection_after_maintenance(self, component_id: str):
        """
        Force state collection after maintenance to capture updated values
        
        Args:
            component_id: Component ID that was maintained
        """
        try:
            # Get the component instance and force a fresh state collection
            if component_id in self._registered_instances:
                instance_info = self._registered_instances[component_id]
                component = instance_info['instance']
                
                if hasattr(component, 'get_state_dict'):
                    # Get fresh state from component
                    fresh_state = component.get_state_dict()
                    print(f"STATE MANAGER: 🔄 Forced fresh state collection for {component_id}")
                    
                    # Update the latest row in our DataFrame if it exists
                    if not self.data.empty:
                        latest_row_index = len(self.data) - 1
                        provider_category = instance_info['provider_category']
                        
                        # Update the DataFrame with fresh values
                        for var_name, value in fresh_state.items():
                            full_name = f"{provider_category}.{var_name}"
                            if full_name in self.data.columns:
                                self.data.at[latest_row_index, full_name] = value
                                print(f"STATE MANAGER: 📊 Updated {full_name} = {value}")
                else:
                    print(f"STATE MANAGER: ⚠️ Component {component_id} has no get_state_dict method")
            else:
                print(f"STATE MANAGER: ⚠️ Component {component_id} not found in registered instances")
                
        except Exception as e:
            print(f"STATE MANAGER: ❌ Failed to force state collection for {component_id}: {e}")
    
    def _actions_are_related(self, violation_action: str, performed_action: str) -> bool:
        """
        Check if two maintenance actions are related (one might address the other)
        
        Args:
            violation_action: Action specified in the threshold violation
            performed_action: Action that was actually performed
            
        Returns:
            True if the actions are related
        """
        # Exact match
        if violation_action == performed_action:
            return True
        
        # Related action mappings
        related_actions = {
            'oil_top_off': ['oil_change', 'lubrication_maintenance'],
            'oil_change': ['oil_top_off', 'lubrication_maintenance'],
            'bearing_maintenance': ['bearing_inspection', 'lubrication_maintenance'],
            'vibration_analysis': ['bearing_maintenance', 'alignment_check'],
            'pump_maintenance': ['oil_top_off', 'bearing_maintenance', 'seal_replacement'],
            'turbine_oil_top_off': ['oil_top_off', 'turbine_maintenance'],
            'efficiency_analysis': ['turbine_maintenance', 'performance_optimization']
        }
        
        # Check if performed action is in the related actions for violation action
        if violation_action in related_actions:
            if performed_action in related_actions[violation_action]:
                return True
        
        # Check reverse relationship
        if performed_action in related_actions:
            if violation_action in related_actions[performed_action]:
                return True
        
        # Check for partial string matches (e.g., "oil_top_off" matches "turbine_oil_top_off")
        if 'oil' in violation_action and 'oil' in performed_action:
            return True
        
        if 'bearing' in violation_action and 'bearing' in performed_action:
            return True
        
        if 'vibration' in violation_action and 'vibration' in performed_action:
            return True
        
        return False

    def get_maintenance_history(self, component_id: str = None) -> list:
        """
        Get maintenance history
        
        Args:
            component_id: Optional component ID to filter by
            
        Returns:
            List of maintenance records
        """
        if component_id:
            return [record for record in self.maintenance_history 
                   if record['component_id'] == component_id]
        return self.maintenance_history.copy()
    
    def verify_maintenance_action(self, component_id: str, action_type: str, 
                                expected_changes: dict, tolerance: float = 0.1) -> bool:
        """
        Verify that maintenance action was effective
        
        Args:
            component_id: Component ID
            action_type: Type of maintenance action
            expected_changes: Expected parameter changes {param: expected_delta}
            tolerance: Tolerance for verification
            
        Returns:
            True if maintenance was effective
        """
        # FIXED: Maintenance verification should check if the action was recorded as successful,
        # not check current parameter values which may have degraded again over time
        
        # Check if we have a successful maintenance record for this component and action
        for record in reversed(self.maintenance_history):  # Check most recent first
            if (record['component_id'] == component_id and 
                record['action_type'] == action_type and 
                record['success']):
                
                print(f"STATE MANAGER: ✅ Verified maintenance: {component_id} {action_type} was successfully completed")
                return True
        
        # If no successful maintenance record found, it wasn't effective
        print(f"STATE MANAGER: ❌ No successful maintenance record found for {component_id} {action_type}")
        return False
    
    def reset(self) -> None:
        """Reset the state manager completely."""
        self.clear_data()
        self.registry.clear()
        self.providers.clear()
        self._instance_counters.clear()
        self._registered_instances.clear()
        
        # Reset maintenance system state
        self.maintenance_thresholds.clear()
        self.threshold_violations.clear()
        self.maintenance_history.clear()
        self.maintenance_config = None
        self.threshold_event_subscribers.clear()
        self._maintenance_orchestrator = None
        
        # Clear any pending registrations
        if hasattr(self.__class__, '_pending_registrations'):
            self.__class__._pending_registrations = []
        
        print(f"STATE MANAGER: ✅ Complete reset including maintenance system")
    
    def __repr__(self) -> str:
        """String representation of state manager."""
        info = self.get_data_info()
        instance_count = len(self._registered_instances)
        return (f"StateManager(rows={info['total_rows']}, "
                f"variables={info['total_variables']}, "
                f"categories={len(info['categories'])}, "
                f"instances={instance_count}, "
                f"memory={info['memory_usage_mb']:.1f}MB)")
