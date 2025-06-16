"""
Automatic State Provider System

This module provides the StateProviderMixin that automatically converts existing
get_state_dict() methods to the StateProvider interface with zero manual work.

Key Features:
1. Path-based category inference from module location
2. Automatic hierarchical naming generation
3. Smart unit and range inference from variable names
4. Zero manual registration or metadata definition required
"""

import warnings
from typing import Dict, Any, Tuple, Optional
import numpy as np

from .interfaces import StateProvider, StateVariable, StateCategory, make_state_name


class StateProviderMixin:
    """
    Mixin to automatically convert get_state_dict() to StateProvider interface.
    
    Components just need to:
    1. Inherit from this mixin
    2. Keep their existing get_state_dict() method unchanged
    3. Everything else is automatic!
    
    The mixin automatically:
    - Infers category/subcategory from file path
    - Generates hierarchical state variable names
    - Creates metadata with smart unit/range inference
    - Handles StateProvider interface requirements
    """
    
    def get_state_variables(self) -> Dict[str, StateVariable]:
        """Automatically generate state variable metadata from get_state_dict()"""
        try:
            # Get current state to analyze structure
            state_dict = self.get_state_dict()
            category, subcategory = self._infer_category_and_subcategory()
            
            variables = {}
            for name, value in state_dict.items():
                # Create hierarchical name if not already present
                if not name.startswith(f"{category.value}."):
                    hierarchical_name = make_state_name(category.value, subcategory, name)
                else:
                    hierarchical_name = name
                
                variables[hierarchical_name] = StateVariable(
                    name=hierarchical_name,
                    category=category,
                    subcategory=subcategory,
                    unit=self._infer_unit(name, value),
                    description=f"Auto-generated from {self.__class__.__name__}.{name}",
                    data_type=type(value),
                    valid_range=self._infer_valid_range(name, value),
                    is_critical=self._auto_detect_critical(name)
                )
            
            return variables
        except Exception as e:
            warnings.warn(f"Could not generate state variables for {self.__class__.__name__}: {e}")
            return {}
    
    def get_current_state(self) -> Dict[str, Any]:
        """Return current state using existing get_state_dict() method"""
        try:
            state_dict = self.get_state_dict()
            category, subcategory = self._infer_category_and_subcategory()
            
            # Ensure all keys follow hierarchical naming
            current_state = {}
            for name, value in state_dict.items():
                if not name.startswith(f"{category.value}."):
                    hierarchical_name = make_state_name(category.value, subcategory, name)
                else:
                    hierarchical_name = name
                current_state[hierarchical_name] = value
            
            return current_state
        except Exception as e:
            warnings.warn(f"Could not get current state for {self.__class__.__name__}: {e}")
            return {}
    
    def _infer_category_and_subcategory(self) -> Tuple[StateCategory, str]:
        """Infer category and subcategory from module path"""
        module_path = self.__class__.__module__
        
        # Parse module path like 'systems.secondary.feedwater.pump_system'
        parts = module_path.split('.')
        
        # Determine category from path
        if 'systems.primary' in module_path:
            category = StateCategory.PRIMARY
        elif 'systems.secondary' in module_path:
            category = StateCategory.SECONDARY
        elif 'systems.safety' in module_path:
            category = StateCategory.SAFETY
        elif 'simulator.control' in module_path:
            category = StateCategory.CONTROL
        else:
            category = StateCategory.INTEGRATION
        
        # Determine subcategory from path
        if len(parts) >= 3 and parts[0] == 'systems':
            # For paths like 'systems.secondary.feedwater.pump_system'
            if len(parts) >= 4:
                subcategory = parts[2]  # 'feedwater', 'turbine', 'condenser'
            else:
                subcategory = parts[1]  # 'primary', 'secondary'
        else:
            # For other paths, use class name as subcategory
            subcategory = self.__class__.__name__.lower().replace('system', '').replace('model', '').replace('physics', '')
        
        return category, subcategory
    
    def _infer_unit(self, name: str, value: Any) -> str:
        """Infer units from variable names"""
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
        """Infer reasonable valid ranges for variables"""
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
        """Automatically detect critical parameters"""
        critical_keywords = [
            'trip', 'scram', 'safety', 'emergency', 'alarm',
            'temperature', 'pressure', 'flow', 'speed', 'vibration',
            'power', 'level', 'available', 'status'
        ]
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in critical_keywords)
