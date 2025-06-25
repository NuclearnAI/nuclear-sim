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
from .maintenance_templates import generate_monitoring_config, get_default_check_interval, get_supported_equipment_types, MaintenanceConfigFactory


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
        
        # FIX: Track work orders created during current update cycle
        self.current_update_work_orders = []
        
        # DUPLICATE PREVENTION: Track recent work order creation to prevent duplicates
        self.recent_work_order_triggers = {}  # component_id + action -> timestamp
        self.work_order_cooldown_hours = 0.1  # Minimum time between same work orders (6 minutes for ultra-aggressive)
        
        # Subscribe to maintenance events
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Set up event subscriptions for automatic maintenance responses"""
        self.event_bus.subscribe('threshold_exceeded', self._handle_threshold_exceeded)
        self.event_bus.subscribe('component_failure', self._handle_component_failure)
        self.event_bus.subscribe('parameter_changed', self._handle_parameter_changed)
        self.event_bus.subscribe('protection_trip_occurred', self._handle_protection_trip)
    
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
    
    def discover_components_from_state_manager(self, state_manager, aggressive_mode: bool = False):
        """
        Automatically discover and register components from the state manager
        
        Args:
            state_manager: StateManager instance with registered components
            aggressive_mode: If True, use aggressive thresholds for demos
        """
        from simulator.state.component_metadata import ComponentRegistry
        
        # Get all registered components from the state manager
        registered_instances = state_manager.get_registered_instance_info()
        
        components_registered = 0
        
        for instance_id, instance_info in registered_instances.items():
            try:
                component = instance_info['instance']
                category = instance_info['category']
                subcategory = instance_info['subcategory']
                
                # Get component metadata from ComponentRegistry
                component_metadata = ComponentRegistry.get_component(instance_id)
                if not component_metadata:
                    print(f"AUTO MAINTENANCE: No metadata found for {instance_id}, skipping")
                    continue
                
                equipment_type = component_metadata['metadata'].equipment_type
                
                # Check if this equipment type is supported
                if equipment_type not in get_supported_equipment_types():
                    print(f"AUTO MAINTENANCE: Equipment type {equipment_type.value} not supported for {instance_id}, skipping")
                    continue
                
                # Get component's state variables
                if hasattr(component, 'get_state_dict'):
                    state_variables = component.get_state_dict()
                else:
                    print(f"AUTO MAINTENANCE: Component {instance_id} has no get_state_dict method, skipping")
                    continue
                
                # Use explicitly set maintenance config or discover from sources
                maintenance_config = self._get_or_load_maintenance_config(state_manager, aggressive_mode)
                
                # Generate monitoring configuration using new config system
                monitoring_config = generate_monitoring_config(
                    state_variables, 
                    equipment_type, 
                    instance_id,  # Pass component ID for overrides
                    maintenance_config
                )
                
                if not monitoring_config:
                    print(f"AUTO MAINTENANCE: No monitoring configuration generated for {instance_id}, skipping")
                    continue
                
                # Register component with generated configuration
                self.event_bus.register_component(instance_id, component, monitoring_config)
                components_registered += 1
                
                # Set appropriate check interval based on equipment type
                equipment_check_interval = get_default_check_interval(equipment_type, aggressive_mode)
                if equipment_check_interval < self.check_interval_hours:
                    self.check_interval_hours = equipment_check_interval
                
                print(f"AUTO MAINTENANCE: Auto-registered {instance_id} ({equipment_type.value}) with {len(monitoring_config)} monitors")
                
            except Exception as e:
                print(f"AUTO MAINTENANCE: Failed to register {instance_id}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"AUTO MAINTENANCE: Component discovery complete - registered {components_registered} components")
        
        # Set execution delays based on mode
        if aggressive_mode:
            self.emergency_delay_hours = 0.0
            self.high_priority_delay_hours = 0.0
            self.medium_priority_delay_hours = 0.0
            self.low_priority_delay_hours = 0.0
            print("AUTO MAINTENANCE: Configured for aggressive mode (immediate execution)")
        else:
            self.emergency_delay_hours = 0.0
            self.high_priority_delay_hours = 1.0
            self.medium_priority_delay_hours = 4.0
            self.low_priority_delay_hours = 24.0
            print("AUTO MAINTENANCE: Configured for conservative mode (realistic delays)")

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
        # Allow first check immediately when last_check_time is 0.0
        if self.last_check_time > 0.0 and current_time - self.last_check_time < self.check_interval_hours:
            return []
        
        self.last_check_time = current_time
        new_work_orders = []
        
        # FIX: Clear the current update work orders list
        self.current_update_work_orders = []
        
        # 1. Check all components for maintenance needs
        self.event_bus.check_all_components(current_time)
        
        # FIX: Add newly created work orders from threshold events
        new_work_orders.extend(self.current_update_work_orders)
        
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
            # Add the newly created work order to the current update list
            self.current_update_work_orders.append(work_order)
            # Format the creation time for display
            formatted_time = work_order._format_simulation_time(work_order.created_date)
            print(f"AUTO MAINTENANCE: Created {work_order.work_order_id} for {component_id} - {action} at {formatted_time}")
        else:
            print(f"AUTO MAINTENANCE: Failed to create work order for {component_id} - {action}")
    
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
            # FIX: Add the newly created work order to the current update list
            self.current_update_work_orders.append(work_order)
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
    
    def _handle_protection_trip(self, event: MaintenanceEvent):
        """Handle protection system trip events by creating post-trip work orders"""
        component_id = event.component_id
        data = event.data
        
        # Extract trip information
        trip_type = data.get('trip_type', 'unknown')
        trip_value = data.get('trip_value', 0.0)
        trip_setpoint = data.get('trip_setpoint', 0.0)
        severity = data.get('severity', 'HIGH')
        recommended_actions = data.get('recommended_actions', [])
        system_type = data.get('system_type', 'protection')
        
        print(f"AUTO MAINTENANCE: Protection trip detected - {trip_type} on {component_id} ({severity})")
        
        # Determine priority based on severity
        priority_map = {
            'CRITICAL': Priority.CRITICAL,
            'HIGH': Priority.HIGH,
            'MEDIUM': Priority.MEDIUM,
            'LOW': Priority.LOW
        }
        priority = priority_map.get(severity, Priority.HIGH)
        
        # Create work orders for each recommended action
        work_orders_created = 0
        for action in recommended_actions:
            work_order = self._create_automatic_work_order(
                component_id=component_id,
                action_type=action,
                priority=priority,
                trigger_reason=f"Post-trip investigation: {trip_type} trip (value: {trip_value:.2f}, setpoint: {trip_setpoint:.2f})",
                event=event
            )
            
            if work_order:
                self.current_update_work_orders.append(work_order)
                work_orders_created += 1
                formatted_time = work_order._format_simulation_time(work_order.created_date)
                print(f"AUTO MAINTENANCE: Created post-trip work order {work_order.work_order_id} for {component_id} - {action} at {formatted_time}")
        
        if work_orders_created > 0:
            print(f"AUTO MAINTENANCE: Created {work_orders_created} post-trip work orders for {component_id} {trip_type} trip")
        else:
            print(f"AUTO MAINTENANCE: No work orders created for {component_id} {trip_type} trip")
    
    def _create_automatic_work_order(self, component_id: str, action_type: str,
                                   priority: Priority, trigger_reason: str,
                                   event: MaintenanceEvent) -> Optional[WorkOrder]:
        """Create an automatic work order with duplicate prevention"""
        
        # Convert action string to MaintenanceActionType if needed
        if isinstance(action_type, str):
            try:
                action_enum = MaintenanceActionType(action_type)
            except ValueError:
                print(f"AUTO MAINTENANCE: Unknown action type '{action_type}' for {component_id}")
                return None
        else:
            action_enum = action_type
        
        # DUPLICATE PREVENTION: Check if we recently created a similar work order
        trigger_key = f"{component_id}:{action_type}"
        current_time = event.timestamp
        
        if trigger_key in self.recent_work_order_triggers:
            last_trigger_time = self.recent_work_order_triggers[trigger_key]
            time_since_last = current_time - last_trigger_time
            
            if time_since_last < self.work_order_cooldown_hours:
                print(f"AUTO MAINTENANCE: Skipping duplicate work order for {component_id} - {action_type} "
                      f"(last created {time_since_last:.2f} hours ago, cooldown: {self.work_order_cooldown_hours} hours)")
                return None
        
        # Check for existing active work orders for the same component and action
        existing_orders = self.work_order_manager.get_work_orders_by_component(component_id)
        for existing_order in existing_orders:
            if existing_order.status in [WorkOrderStatus.PLANNED, WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS]:
                # Check if any action in the existing work order matches our action
                for existing_action in existing_order.maintenance_actions:
                    if existing_action.action_type == action_type:
                        print(f"AUTO MAINTENANCE: Skipping duplicate work order - {existing_order.work_order_id} "
                              f"already has {action_type} for {component_id}")
                        return None
        
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
        
        # Only increment counter if work order was actually created and stored
        if work_order.work_order_id in self.work_order_manager.work_orders:
            self.work_orders_created += 1
            
            # Record this trigger to prevent duplicates
            self.recent_work_order_triggers[trigger_key] = current_time
            
            print(f"AUTO MAINTENANCE: Successfully created work order {work_order.work_order_id} for {component_id} - {action_type}")
        else:
            print(f"AUTO MAINTENANCE: ERROR - Work order {work_order.work_order_id} was not stored in manager!")
            return None
        
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
                # Determine how to call the maintenance method based on component type
                component_class_name = component.__class__.__name__
                print(f"AUTO MAINTENANCE: Attempting {action_type} on {component_class_name}")
                
                if component_class_name == "FeedwaterPumpSystem":
                    # For pump systems, we need to determine which pump to maintain
                    # For now, let the system decide (pump_id=None means system-wide maintenance)
                    result = component.perform_maintenance(pump_id=None, maintenance_type=action_type)
                    
                elif hasattr(component, 'config') and hasattr(component.config, 'pump_id'):
                    # For individual pumps with pump_id in config
                    pump_id = component.config.pump_id
                    result = component.perform_maintenance(pump_id=pump_id, maintenance_type=action_type)
                    
                elif hasattr(component, 'config') and hasattr(component.config, 'system_id'):
                    # For lubrication systems or other systems with system_id
                    print(f"AUTO MAINTENANCE: Calling perform_maintenance on {component.config.system_id}")
                    result = component.perform_maintenance(maintenance_type=action_type)
                    
                else:
                    # Standard maintenance method call
                    result = component.perform_maintenance(maintenance_type=action_type)
                
                print(f"AUTO MAINTENANCE: Maintenance result type: {type(result)}, content: {result}")
                
                # Convert result to MaintenanceResult if needed
                if isinstance(result, dict):
                    maintenance_result = MaintenanceResult(
                        success=result.get('success', True),
                        duration_hours=result.get('duration_hours', 1.0),
                        work_performed=result.get('work_performed', f"Performed {action_type}"),
                        findings=result.get('findings'),
                        recommendations=result.get('recommendations', []),
                        effectiveness_score=result.get('effectiveness_score', 1.0)
                    )
                    print(f"AUTO MAINTENANCE: Converted to MaintenanceResult: success={maintenance_result.success}")
                    return maintenance_result
                elif isinstance(result, MaintenanceResult):
                    print(f"AUTO MAINTENANCE: Already MaintenanceResult: success={result.success}")
                    return result
                else:
                    # Assume success if method returns anything else
                    maintenance_result = MaintenanceResult(
                        success=True,
                        duration_hours=1.0,
                        work_performed=f"Performed {action_type} on {component.__class__.__name__}"
                    )
                    print(f"AUTO MAINTENANCE: Created default MaintenanceResult: success={maintenance_result.success}")
                    return maintenance_result
                    
            except Exception as e:
                print(f"AUTO MAINTENANCE: Exception during maintenance on {component.__class__.__name__}: {e}")
                import traceback
                traceback.print_exc()
                return MaintenanceResult(
                    success=False,
                    duration_hours=0.5,
                    work_performed=f"Failed to perform {action_type}",
                    error_message=str(e)
                )
        else:
            # Component doesn't support maintenance
            print(f"AUTO MAINTENANCE: Component {component.__class__.__name__} does not have perform_maintenance method")
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
        """Reset the automatic maintenance system completely"""
        self.event_bus.reset()
        self.work_order_manager.reset()
        self.work_orders_created = 0
        self.work_orders_executed = 0
        self.maintenance_actions_performed = 0
        self.last_check_time = 0.0
        
        # Reset all maintenance configuration state
        self.reset_maintenance_config()
        
        # Clear work order tracking
        self.current_update_work_orders = []
        self.recent_work_order_triggers = {}
        
        # Re-subscribe to maintenance events after reset
        self._setup_event_subscriptions()
        
        print("AUTO MAINTENANCE: ✅ Complete system reset")
    
    def _get_or_load_maintenance_config(self, state_manager, aggressive_mode: bool = False):
        """
        Get or load maintenance configuration with proper singleton pattern
        
        Args:
            state_manager: StateManager instance
            aggressive_mode: If True, use aggressive thresholds for demos
            
        Returns:
            Maintenance configuration object
        """
        # If we have an explicitly set config, use it
        if hasattr(self, '_explicit_maintenance_config'):
            return self._explicit_maintenance_config
        
        # If config was already loaded, reuse it
        if hasattr(self, '_loaded_maintenance_config') and self._loaded_maintenance_config:
            return self._loaded_maintenance_config
        
        # Load config from available sources
        maintenance_config = None
        config_source = None
        
        # Check multiple sources for configuration
        if hasattr(self, 'secondary_config') and self.secondary_config:
            # Use config passed from simulator
            config_source = self.secondary_config
        elif hasattr(state_manager, 'config'):
            config_source = state_manager.config
        elif hasattr(state_manager, 'simulator') and hasattr(state_manager.simulator, 'secondary_physics') and hasattr(state_manager.simulator.secondary_physics, 'config'):
            config_source = state_manager.simulator.secondary_physics.config
        
        if config_source:
            # Check for maintenance_system.component_configs (comprehensive composer format)
            if isinstance(config_source, dict) and 'maintenance_system' in config_source:
                maintenance_system = config_source['maintenance_system']
                if 'component_configs' in maintenance_system:
                    # Create a temporary config object with the right structure for the YAML loader
                    temp_config = type('TempConfig', (), {})()
                    temp_config.maintenance_component_configs = maintenance_system['component_configs']
                    temp_config.maintenance_mode = maintenance_system.get('maintenance_mode', 'conservative')
                    temp_config.maintenance_threshold_multiplier = maintenance_system.get('maintenance_threshold_multiplier', 1.0)
                    temp_config.maintenance_cooldown_reduction_factor = maintenance_system.get('maintenance_cooldown_reduction_factor', 1.0)
                    temp_config.maintenance_check_interval_multiplier = maintenance_system.get('maintenance_check_interval_multiplier', 1.0)
                    temp_config.maintenance_work_order_cooldown_hours = maintenance_system.get('maintenance_work_order_cooldown_hours', 24.0)
                    maintenance_config = self._create_maintenance_config_from_yaml(temp_config)
                    print(f"AUTO MAINTENANCE: ✅ Loaded subsystem-specific config from maintenance_system")
            # Check for maintenance_component_configs (old format)
            elif hasattr(config_source, 'maintenance_component_configs') and config_source.maintenance_component_configs:
                maintenance_config = self._create_maintenance_config_from_yaml(config_source)
                print(f"AUTO MAINTENANCE: ✅ Loaded config from maintenance_component_configs")
            # Check for maintenance.component_configs (alternative format)
            elif isinstance(config_source, dict) and 'maintenance' in config_source:
                maintenance_system = config_source['maintenance']
                if 'component_configs' in maintenance_system:
                    # Create a temporary config object with the right structure for the YAML loader
                    temp_config = type('TempConfig', (), {})()
                    temp_config.maintenance_component_configs = maintenance_system['component_configs']
                    temp_config.maintenance_mode = maintenance_system.get('maintenance_mode', 'conservative')
                    temp_config.maintenance_threshold_multiplier = maintenance_system.get('maintenance_threshold_multiplier', 1.0)
                    temp_config.maintenance_cooldown_reduction_factor = maintenance_system.get('maintenance_cooldown_reduction_factor', 1.0)
                    temp_config.maintenance_check_interval_multiplier = maintenance_system.get('maintenance_check_interval_multiplier', 1.0)
                    temp_config.maintenance_work_order_cooldown_hours = maintenance_system.get('maintenance_work_order_cooldown_hours', 24.0)
                    maintenance_config = self._create_maintenance_config_from_yaml(temp_config)
                    print(f"AUTO MAINTENANCE: ✅ Loaded config from maintenance section")
            # Check for other aggressive mode indicators
            elif hasattr(config_source, 'maintenance_ultra_aggressive_mode') and config_source.maintenance_ultra_aggressive_mode:
                maintenance_config = MaintenanceConfigFactory.create_ultra_aggressive()
                print(f"AUTO MAINTENANCE: ✅ Loaded ultra-aggressive factory config")
        
        # Fallback to factory defaults if no YAML config found
        if maintenance_config is None:
            if aggressive_mode:
                maintenance_config = MaintenanceConfigFactory.create_aggressive()
                print(f"AUTO MAINTENANCE: ✅ Using aggressive factory config (fallback)")
            else:
                maintenance_config = MaintenanceConfigFactory.create_conservative()
                print(f"AUTO MAINTENANCE: ✅ Using conservative factory config (fallback)")
        
        # Cache the loaded config for reuse
        self._loaded_maintenance_config = maintenance_config
        return maintenance_config
    
    def apply_explicit_maintenance_config(self, maintenance_config):
        """
        Apply an explicitly provided maintenance configuration
        
        This bypasses all config discovery and uses the provided config directly.
        Used by MaintenanceScenarioRunner to ensure subsystem-specific configs are used.
        
        Args:
            maintenance_config: Pre-configured maintenance config object or dict
        """
        if isinstance(maintenance_config, dict):
            # Convert dict config to proper maintenance config object
            temp_config = type('TempConfig', (), {})()
            if 'maintenance_system' in maintenance_config:
                temp_config.maintenance_component_configs = maintenance_config['maintenance_system']['component_configs']
                temp_config.maintenance_mode = maintenance_config['maintenance_system'].get('maintenance_mode', 'subsystem_specific')
            else:
                temp_config.maintenance_component_configs = maintenance_config
                temp_config.maintenance_mode = 'subsystem_specific'
            
            self._explicit_maintenance_config = self._create_maintenance_config_from_yaml(temp_config)
        else:
            self._explicit_maintenance_config = maintenance_config
        
        print(f"AUTO MAINTENANCE: ✅ Applied explicit maintenance configuration")
        return self._explicit_maintenance_config
    
    def reset_maintenance_config(self):
        """
        Reset all maintenance configuration state
        
        This clears cached configs and forces fresh loading on next discovery.
        """
        if hasattr(self, '_loaded_maintenance_config'):
            delattr(self, '_loaded_maintenance_config')
        if hasattr(self, '_explicit_maintenance_config'):
            delattr(self, '_explicit_maintenance_config')
        if hasattr(self, '_subsystem_config_loaded'):
            delattr(self, '_subsystem_config_loaded')
        
        print(f"AUTO MAINTENANCE: ✅ Reset maintenance configuration state")
    
    def _create_maintenance_config_from_yaml(self, yaml_config):
        """
        Create maintenance configuration from subsystem-specific YAML config
        
        This method loads the new subsystem-specific maintenance configuration
        generated by the ComprehensiveComposer.
        """
        from .config import MaintenanceConfig, MaintenanceMode, ComponentTypeConfig, ComponentThresholds
        
        # Create base maintenance config
        maintenance_config = MaintenanceConfig()
        
        # Set mode from YAML if available
        if hasattr(yaml_config, 'maintenance_mode'):
            mode_str = yaml_config.maintenance_mode.lower()
            if mode_str == 'subsystem_specific':
                maintenance_config.mode = MaintenanceMode.CUSTOM
            elif mode_str == 'aggressive':
                maintenance_config.mode = MaintenanceMode.AGGRESSIVE
            elif mode_str == 'ultra_aggressive':
                maintenance_config.mode = MaintenanceMode.ULTRA_AGGRESSIVE
            elif mode_str == 'conservative':
                maintenance_config.mode = MaintenanceMode.CONSERVATIVE
            else:
                maintenance_config.mode = MaintenanceMode.CUSTOM
        
        # Load component-specific configurations from new subsystem-specific format
        if hasattr(yaml_config, 'maintenance_component_configs'):
            component_configs = yaml_config.maintenance_component_configs
            
            for component_type, config_data in component_configs.items():
                # Create component type configuration
                component_config = ComponentTypeConfig()
                
                # Set check interval directly from config (already calculated by ComprehensiveComposer)
                component_config.check_interval_hours = config_data.get('check_interval_hours', 4.0)
                
                # Load thresholds directly (already calculated by ComprehensiveComposer)
                if 'thresholds' in config_data:
                    thresholds = config_data['thresholds']
                    
                    for param_name, threshold_data in thresholds.items():
                        # Skip thresholds without actions defined
                        if 'action' not in threshold_data:
                            continue
                            
                        # Use thresholds directly (no multiplier calculations needed)
                        threshold_config = ComponentThresholds(
                            threshold=threshold_data['threshold'],
                            comparison=threshold_data.get('comparison', 'greater_than'),
                            action=threshold_data['action'],
                            cooldown_hours=threshold_data.get('cooldown_hours', 24.0),
                            priority=threshold_data.get('priority', 'MEDIUM')
                        )
                        
                        component_config.thresholds[param_name] = threshold_config
                
                # Store in maintenance config
                maintenance_config.component_types[component_type] = component_config
        
        print(f"AUTO MAINTENANCE: Loaded subsystem-specific config with {len(maintenance_config.component_types)} component types")
        
        # Debug: Show configuration for each subsystem
        for subsystem, config in maintenance_config.component_types.items():
            mode = "unknown"
            if hasattr(yaml_config, 'maintenance_component_configs'):
                subsystem_config = yaml_config.maintenance_component_configs.get(subsystem, {})
                mode = subsystem_config.get('mode', 'unknown')
            
            print(f"AUTO MAINTENANCE: {subsystem} - mode: {mode}, check_interval: {config.check_interval_hours}h, thresholds: {len(config.thresholds)}")
            
            # Show specific thresholds for debugging
            for param_name, threshold in config.thresholds.items():
                print(f"  - {param_name}: {threshold.threshold} ({threshold.comparison}) -> {threshold.action} (cooldown: {threshold.cooldown_hours}h)")
        
        return maintenance_config


# Convenience function for easy setup
def create_auto_maintenance_system() -> AutoMaintenanceSystem:
    """Create and return a new automatic maintenance system"""
    return AutoMaintenanceSystem()
