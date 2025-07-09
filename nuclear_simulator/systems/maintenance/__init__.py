"""
Plant-Wide Maintenance Management System

This module provides comprehensive maintenance management capabilities for all
components in the nuclear plant simulation using a pure event-driven approach
with no inheritance requirements.

Key Features:
1. Event-driven architecture with pub/sub pattern
2. No inheritance conflicts - works with any existing component
3. Configuration-based component monitoring
4. Automatic work order generation and execution
5. Complete maintenance history and reporting
6. Integration with existing state management system

Design Pattern:
- Pure composition and event-driven design
- Components register via configuration, no code changes needed
- Maintenance system monitors component attributes automatically
- Events trigger automatic work order creation and execution
"""

from .event_bus import MaintenanceEventBus
from .auto_maintenance import AutoMaintenanceSystem
from .work_orders import WorkOrder, WorkOrderStatus, WorkOrderType, Priority
from .maintenance_actions import MaintenanceActionType, MaintenanceResult
from .component_registry import ComponentMaintenanceRegistry

__all__ = [
    'MaintenanceEventBus',
    'AutoMaintenanceSystem', 
    'WorkOrder',
    'WorkOrderStatus',
    'WorkOrderType',
    'Priority',
    'MaintenanceActionType',
    'MaintenanceResult',
    'ComponentMaintenanceRegistry'
]

# Version info
__version__ = "1.0.0"
__author__ = "Nuclear Plant Simulation Team"
