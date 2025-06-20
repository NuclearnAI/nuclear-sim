"""
Automatic Maintenance System

This module provides the main automatic maintenance management system that
coordinates event monitoring, work order generation, and maintenance execution.

Key Features:
1. Automatic component monitoring and maintenance triggering
2. Work order generation and execution
3. Integration with event bus and component registry
4. Maintenance scheduling and prioritization
5. Complete maintenance automation like virtual plant operators
"""

from typing import Dict, List, Optional, Any
import time

from .event_bus import MaintenanceEventBus, MaintenanceEvent
from .work_orders import WorkOrder, WorkOrderManager, WorkOrderType, Priority, WorkOrderStatus
from .maintenance_actions import MaintenanceActionType, MaintenanceResult, get_maintenance_catalog


class AutoMaintenanceSystem:
    """
    Automatic maintenance system that acts like virtual plant operators
    
    This system continuously monitors all registered components and automatically
    creates and executes maintenance work orders when needed.
    """
    
    def __init__(self):
        # Core components
        self.event_bus = MaintenanceEventBus()
        self.work_order_manager = WorkOrderManager()
        self.maintenance_catalog = get_maintenance_catalog()
        
        # System settings
        self.auto_execute_maintenance = True
        self.check_interval_hours = 0.25  # Check every 15 minutes
        self.last_check_time = 0.0
        
        # Maintenance scheduling
        self.emergency_delay_hours = 0.0    # Execute immediately
        self.high_priority_delay_hours = 1.0  # 1 hour delay
        self.medium_priority_delay_hours = 4.0  # 4 hour delay
        self.low_priority_delay_hours = 24.0   # 24 hour delay
        
        # Statistics
        self.work_orders_created = 0
        self.work_orders_executed = 0
        self.maintenance_actions_performed = 0
        
        # Subscribe to maintenance events
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Set up event subscriptions for automatic maintenance responses"""
        self.event_bus.subscribe('threshold_exceeded', self._handle_threshold_exceeded)
        self.event_bus.subscribe('component_failure', self._handle_component_failure)
        self.event_bus.subscribe('parameter_changed', self._handle_parameter_changed)
    
    def register_component(self, component_id: str, component: Any, 
                          monitoring_config: Dict[str, Dict[str, Any]]):
        """
        Register a component for automatic maintenance monitoring
        
        Args:
            component_id: Unique component identifier
            component: Component instance
            monitoring_config: Configuration for parameter monitoring
            
        Example monitoring_config:
        {
            'oil_level': {
                'attribute': 'state.oil_level',
                'threshold': 30.0,
                'comparison': 'less_than',
                'action': 'oil_top_off',
                'cooldown_hours': 1.0
            },
            'impeller_wear': {
                'attribute': 'state.impeller_wear',
                'threshold': 15.0,
                'comparison': 'greater_than',
                'action': 'impeller_inspection',
                'cooldown_hours': 24.0
            }
        }
        """
        self.event_bus.register_component(component_id, component, monitoring_config)
        print(f"AUTO MAINTENANCE: Registered {component_id} for automatic maintenance")
    
    def unregister_component(self, component_id: str):
        """Unregister a component from automatic maintenance"""
        self.event_bus.unregister_component(component_id)
        print(f"AUTO MAINTENANCE: Unregistered {component_id}")
    
    def update(self, current_time: float, dt: float) -> List[WorkOrder]:
        """
        Main update loop for automatic maintenance system
        
        Args:
            current_time: Current simulation time
            dt: Time step
            
        Returns:
            List of work orders created or executed this update
        """
        # Only check periodically, not every simulation step
        if current_time - self.last_check_time < self.check_interval_hours:
            return []
        
        self.last_check_time = current_time
        new_work_orders = []
        
        # 1. Check all components for maintenance needs
        self.event_bus.check_all_components(current_time)
        
        # 2. Execute scheduled work orders
        if self.auto_execute_maintenance:
            executed_orders = self._execute_scheduled_work_orders(current_time)
            new_work_orders.extend(executed_orders)
        
        return new_work_orders
    
    def _handle_threshold_exceeded(self, event: MaintenanceEvent):
        """Handle threshold exceeded events by creating work orders"""
        component_id = event.component_id
        data = event.data
        
        # Extract event information
        parameter = data.get('parameter', 'unknown')
        value = data.get('value', 0.0)
        threshold = data.get('threshold', 0.0)
        action = data.get('action')
        
        if not action:
            print(f"AUTO MAINTENANCE: No action specified for {component_id} {parameter} threshold")
            return
        
        # Determine priority based on how far over threshold
        if isinstance(threshold, (int, float)) and threshold > 0:
            threshold_ratio = value / threshold
            if threshold_ratio > 2.0:
                priority = Priority.EMERGENCY
            elif threshold_ratio > 1.5:
                priority = Priority.CRITICAL
            elif threshold_ratio > 1.2:
                priority = Priority.HIGH
            else:
                priority = Priority.MEDIUM
        else:
            priority = Priority.HIGH
        
        # Create work order
        work_order = self._create_automatic_work_order(
            component_id=component_id,
            action_type=action,
            priority=priority,
            trigger_reason=f"{parameter} = {value:.2f} exceeded threshold {threshold:.2f}",
            event=event
        )
        
        if work_order:
            print(f"AUTO MAINTENANCE: Created {work_order.work_order_id} for {component_id} - {action}")
    
    def _handle_component_failure(self, event: MaintenanceEvent):
        """Handle component failure events"""
        component_id = event.component_id
        data = event.data
        
        # Create emergency work order for component failure
        work_order = self._create_automatic_work_order(
            component_id=component_id,
            action_type="repair",
            priority=Priority.EMERGENCY,
            trigger_reason=f"Component failure: {data.get('failure_reason', 'Unknown')}",
            event=event
        )
        
        if work_order:
            print(f"AUTO MAINTENANCE: Created emergency work order {work_order.work_order_id} for {component_id}")
    
    def _handle_parameter_changed(self, event: MaintenanceEvent):
        """Handle parameter change events (for logging/trending)"""
        # For now, just log significant parameter changes
        # Could be extended to trigger predictive maintenance
        component_id = event.component_id
        data = event.data
        parameter = data.get('parameter', 'unknown')
        change = data.get('change', 0.0)
        
        if change > 1.0:  # Significant change
            print(f"AUTO MAINTENANCE: Significant change in {component_id} {parameter}: {change:.2f}")
    
    def _create_automatic_work_order(self, component_id: str, action_type: str, 
                                   priority: Priority, trigger_reason: str,
                                   event: MaintenanceEvent) -> Optional[WorkOrder]:
        """Create an automatic work order"""
        
        # Convert action string to MaintenanceActionType if needed
        if isinstance(action_type, str):
            try:
                action_enum = MaintenanceActionType(action_type)
            except ValueError:
                print(f"AUTO MAINTENANCE: Unknown action type '{action_type}' for {component_id}")
                return None
        else:
            action_enum = action_type
        
        # Get component information
        component_status = self.event_bus.get_component_status(component_id)
        if not component_status:
            print(f"AUTO MAINTENANCE: Component {component_id} not found")
            return None
        
        # Determine work order type
        if priority == Priority.EMERGENCY:
            work_type = WorkOrderType.EMERGENCY
        elif "inspection" in action_type or "analysis" in action_type:
            work_type = WorkOrderType.INSPECTION
        elif "cleaning" in action_type or "flush" in action_type:
            work_type = WorkOrderType.CLEANING
        else:
            work_type = WorkOrderType.CORRECTIVE
        
        # Create work order
        title = f"Auto: {action_enum.value.replace('_', ' ').title()} - {component_id}"
        
        work_order = self.work_order_manager.create_work_order(
            component_id=component_id,
            work_type=work_type,
            priority=priority,
            title=title,
            description=f"Automatic maintenance triggered by: {trigger_reason}",
            auto_generated=True,
            trigger_id=f"event_{event.timestamp}"
        )
        
        # Add maintenance action
        estimated_duration = self.maintenance_catalog.estimate_duration(action_enum)
        work_order.add_action(
            action_type=action_enum.value,
            description=f"Perform {action_enum.value.replace('_', ' ')} on {component_id}",
            estimated_duration=estimated_duration
        )
        
        # Set component metadata
        work_order.component_type = component_status['class_name']
        work_order.created_date = event.timestamp
        
        # Schedule based on priority
        work_order.planned_start_date = self._calculate_start_time(event.timestamp, priority)
        work_order.status = WorkOrderStatus.SCHEDULED
        
        self.work_orders_created += 1
        return work_order
    
    def _calculate_start_time(self, current_time: float, priority: Priority) -> float:
        """Calculate when work order should start based on priority"""
        if priority == Priority.EMERGENCY:
            return current_time + self.emergency_delay_hours
        elif priority == Priority.CRITICAL:
            return current_time + self.high_priority_delay_hours * 0.5
        elif priority == Priority.HIGH:
            return current_time + self.high_priority_delay_hours
        elif priority == Priority.MEDIUM:
            return current_time + self.medium_priority_delay_hours
        else:  # LOW
            return current_time + self.low_priority_delay_hours
    
    def _execute_scheduled_work_orders(self, current_time: float) -> List[WorkOrder]:
        """Execute work orders that are scheduled for current time"""
        executed_orders = []
        
        scheduled_orders = self.work_order_manager.get_work_orders_by_status(WorkOrderStatus.SCHEDULED)
        
        for work_order in scheduled_orders:
            if (work_order.planned_start_date and 
                current_time >= work_order.planned_start_date):
                
                # Check if component is available for maintenance
                if self._can_perform_maintenance(work_order.component_id, work_order):
                    success = self._execute_work_order(work_order, current_time)
                    if success:
                        executed_orders.append(work_order)
                else:
                    # Reschedule for later
                    work_order.planned_start_date = current_time + 1.0  # Try again in 1 hour
                    print(f"AUTO MAINTENANCE: Rescheduled {work_order.work_order_id} - component not available")
        
        return executed_orders
    
    def _can_perform_maintenance(self, component_id: str, work_order: WorkOrder) -> bool:
        """Check if maintenance can be performed on component"""
        # Get component
        component_status = self.event_bus.get_component_status(component_id)
        if not component_status:
            return False
        
        # For now, assume maintenance can always be performed
        # This could be enhanced to check component status, running state, etc.
        return True
    
    def _execute_work_order(self, work_order: WorkOrder, current_time: float) -> bool:
        """Execute a work order on the target component"""
        
        # Get component from event bus
        component = self.event_bus.components.get(work_order.component_id)
        if not component:
            print(f"AUTO MAINTENANCE: Component {work_order.component_id} not found")
            return False
        
        # Start work order
        work_order.start_work(current_time, "AUTO_OPERATOR")
        
        success = True
        total_duration = 0.0
        work_performed = []
        
        # Execute each maintenance action
        for action in work_order.maintenance_actions:
            try:
                result = self._perform_maintenance_action(component, action.action_type)
                
                # Update action with results
                action.actual_duration = result.duration_hours
                action.success = result.success
                action.findings = result.findings
                action.recommendations = result.recommendations
                
                total_duration += result.duration_hours
                work_performed.append(result.work_performed)
                
                if not result.success:
                    success = False
                
                self.maintenance_actions_performed += 1
                
            except Exception as e:
                print(f"AUTO MAINTENANCE: Error executing {action.action_type} on {work_order.component_id}: {e}")
                action.success = False
                action.findings = f"Error: {str(e)}"
                success = False
        
        # Complete work order
        work_summary = "; ".join(work_performed) if work_performed else "Maintenance completed"
        self.work_order_manager.complete_work_order(
            work_order.work_order_id,
            current_time + total_duration,
            success,
            work_summary
        )
        
        if success:
            print(f"AUTO MAINTENANCE: Successfully executed {work_order.work_order_id} on {work_order.component_id}")
        else:
            print(f"AUTO MAINTENANCE: Failed to execute {work_order.work_order_id} on {work_order.component_id}")
        
        self.work_orders_executed += 1
        return success
    
    def _perform_maintenance_action(self, component: Any, action_type: str) -> MaintenanceResult:
        """Perform maintenance action on component"""
        
        # Check if component has perform_maintenance method
        if hasattr(component, 'perform_maintenance'):
            try:
                # Call component's maintenance method
                result = component.perform_maintenance(maintenance_type=action_type)
                
                # Convert result to MaintenanceResult if needed
                if isinstance(result, dict):
                    return MaintenanceResult(
                        success=result.get('success', True),
                        duration_hours=result.get('duration_hours', 1.0),
                        work_performed=result.get('work_performed', f"Performed {action_type}"),
                        findings=result.get('findings'),
                        recommendations=result.get('recommendations', []),
                        effectiveness_score=result.get('effectiveness_score', 1.0)
                    )
                elif isinstance(result, MaintenanceResult):
                    return result
                else:
                    # Assume success if method returns anything else
                    return MaintenanceResult(
                        success=True,
                        duration_hours=1.0,
                        work_performed=f"Performed {action_type} on {component.__class__.__name__}"
                    )
                    
            except Exception as e:
                return MaintenanceResult(
                    success=False,
                    duration_hours=0.5,
                    work_performed=f"Failed to perform {action_type}",
                    error_message=str(e)
                )
        else:
            # Component doesn't support maintenance
            return MaintenanceResult(
                success=False,
                duration_hours=0.0,
                work_performed=f"Component does not support maintenance",
                error_message=f"Component {component.__class__.__name__} does not have perform_maintenance method"
            )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current status of the automatic maintenance system"""
        event_stats = self.event_bus.get_statistics()
        work_order_stats = self.work_order_manager.get_statistics()
        
        return {
            'auto_execute_enabled': self.auto_execute_maintenance,
            'check_interval_hours': self.check_interval_hours,
            'last_check_time': self.last_check_time,
            'work_orders_created': self.work_orders_created,
            'work_orders_executed': self.work_orders_executed,
            'maintenance_actions_performed': self.maintenance_actions_performed,
            'event_bus_stats': event_stats,
            'work_order_stats': work_order_stats
        }
    
    def get_component_summary(self) -> Dict[str, Any]:
        """Get summary of all registered components"""
        return self.event_bus.get_all_component_status()
    
    def get_recent_work_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent work orders"""
        recent_orders = []
        
        # Get active work orders
        for work_order in list(self.work_order_manager.work_orders.values())[-limit:]:
            recent_orders.append(work_order.to_dict())
        
        # Get recent completed work orders
        for work_order in self.work_order_manager.completed_work_orders[-limit:]:
            recent_orders.append(work_order.to_dict())
        
        # Sort by creation date
        recent_orders.sort(key=lambda x: x['created_date'], reverse=True)
        
        return recent_orders[:limit]
    
    def enable_auto_execution(self):
        """Enable automatic work order execution"""
        self.auto_execute_maintenance = True
        print("AUTO MAINTENANCE: Automatic execution enabled")
    
    def disable_auto_execution(self):
        """Disable automatic work order execution"""
        self.auto_execute_maintenance = False
        print("AUTO MAINTENANCE: Automatic execution disabled")
    
    def set_check_interval(self, hours: float):
        """Set how often to check for maintenance needs"""
        self.check_interval_hours = max(0.1, hours)  # Minimum 6 minutes
        print(f"AUTO MAINTENANCE: Check interval set to {self.check_interval_hours} hours")
    
    def reset(self):
        """Reset the automatic maintenance system"""
        self.event_bus.reset()
        self.work_order_manager.reset()
        self.work_orders_created = 0
        self.work_orders_executed = 0
        self.maintenance_actions_performed = 0
        self.last_check_time = 0.0
        print("AUTO MAINTENANCE: System reset")


# Convenience function for easy setup
def create_auto_maintenance_system() -> AutoMaintenanceSystem:
    """Create and return a new automatic maintenance system"""
    return AutoMaintenanceSystem()
