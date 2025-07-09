"""
Component Maintenance Registry

This module provides a simple registry for tracking components that
can receive maintenance, without requiring inheritance or code changes.

Key Features:
1. Simple component registration
2. Maintenance capability tracking
3. Component metadata storage
4. Integration with automatic maintenance system
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ComponentMaintenanceInfo:
    """Information about a component's maintenance capabilities"""
    component_id: str
    component_type: str
    class_name: str
    maintenance_methods: List[str] = field(default_factory=list)
    monitored_parameters: List[str] = field(default_factory=list)
    last_maintenance: Optional[float] = None
    maintenance_history: List[str] = field(default_factory=list)


class ComponentMaintenanceRegistry:
    """
    Registry for tracking components and their maintenance capabilities
    """
    
    def __init__(self):
        self.components: Dict[str, ComponentMaintenanceInfo] = {}
    
    def register_component(self, component_id: str, component: Any, 
                          component_type: str = None) -> ComponentMaintenanceInfo:
        """
        Register a component in the maintenance registry
        
        Args:
            component_id: Unique component identifier
            component: Component instance
            component_type: Type of component (auto-detected if not provided)
            
        Returns:
            ComponentMaintenanceInfo instance
        """
        # Auto-detect component type if not provided
        if not component_type:
            class_name = component.__class__.__name__.lower()
            if 'pump' in class_name:
                component_type = 'pump'
            elif 'turbine' in class_name:
                component_type = 'turbine'
            elif 'valve' in class_name:
                component_type = 'valve'
            elif 'motor' in class_name:
                component_type = 'motor'
            else:
                component_type = 'unknown'
        
        # Detect maintenance methods
        maintenance_methods = []
        if hasattr(component, 'perform_maintenance'):
            maintenance_methods.append('perform_maintenance')
        if hasattr(component, 'get_state_dict'):
            maintenance_methods.append('get_state_dict')
        
        # Detect monitored parameters
        monitored_parameters = []
        if hasattr(component, 'get_state_dict'):
            try:
                state_dict = component.get_state_dict()
                monitored_parameters = list(state_dict.keys())
            except:
                pass
        
        # Create component info
        info = ComponentMaintenanceInfo(
            component_id=component_id,
            component_type=component_type,
            class_name=component.__class__.__name__,
            maintenance_methods=maintenance_methods,
            monitored_parameters=monitored_parameters
        )
        
        self.components[component_id] = info
        return info
    
    def get_component_info(self, component_id: str) -> Optional[ComponentMaintenanceInfo]:
        """Get maintenance info for a component"""
        return self.components.get(component_id)
    
    def get_components_by_type(self, component_type: str) -> List[ComponentMaintenanceInfo]:
        """Get all components of a specific type"""
        return [info for info in self.components.values() 
                if info.component_type == component_type]
    
    def get_all_components(self) -> List[ComponentMaintenanceInfo]:
        """Get all registered components"""
        return list(self.components.values())
    
    def record_maintenance(self, component_id: str, maintenance_type: str, timestamp: float):
        """Record that maintenance was performed on a component"""
        if component_id in self.components:
            info = self.components[component_id]
            info.last_maintenance = timestamp
            info.maintenance_history.append(f"{timestamp}: {maintenance_type}")
            
            # Keep only last 10 maintenance records
            if len(info.maintenance_history) > 10:
                info.maintenance_history.pop(0)
    
    def get_maintenance_summary(self) -> Dict[str, Any]:
        """Get summary of all components and their maintenance status"""
        summary = {
            'total_components': len(self.components),
            'by_type': {},
            'maintenance_capable': 0,
            'monitored_components': 0
        }
        
        for info in self.components.values():
            # Count by type
            if info.component_type not in summary['by_type']:
                summary['by_type'][info.component_type] = 0
            summary['by_type'][info.component_type] += 1
            
            # Count capabilities
            if 'perform_maintenance' in info.maintenance_methods:
                summary['maintenance_capable'] += 1
            if info.monitored_parameters:
                summary['monitored_components'] += 1
        
        return summary
    
    def clear(self):
        """Clear all registered components"""
        self.components.clear()


# Global registry instance
_component_registry = ComponentMaintenanceRegistry()


def get_component_registry() -> ComponentMaintenanceRegistry:
    """Get the global component registry"""
    return _component_registry
