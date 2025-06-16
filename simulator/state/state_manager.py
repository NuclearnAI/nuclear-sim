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
                current_state = provider.get_current_state()
                row_data.update(current_state)
            except Exception as e:
                warnings.warn(f"Failed to collect state from provider {category}: {e}")
        
        # Validate collected data
        is_valid, errors = self.registry.validate_state_data(row_data)
        if not is_valid:
            warnings.warn(f"State validation errors: {errors}")
        
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
    
    def reset(self) -> None:
        """Reset the state manager completely."""
        self.clear_data()
        self.registry.clear()
        self.providers.clear()
    
    def __repr__(self) -> str:
        """String representation of state manager."""
        info = self.get_data_info()
        return (f"StateManager(rows={info['total_rows']}, "
                f"variables={info['total_variables']}, "
                f"categories={len(info['categories'])}, "
                f"memory={info['memory_usage_mb']:.1f}MB)")
