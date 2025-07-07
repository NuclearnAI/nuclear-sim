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

from .work_orders import WorkOrder, WorkOrderManager, WorkOrderType, Priority, WorkOrderStatus
from .maintenance_actions import MaintenanceActionType, MaintenanceResult, get_maintenance_catalog
from .maintenance_templates import MaintenanceConfigFactory

# Simple event class for state manager integration (replaces MaintenanceEvent)
class StateManagerEvent:
    """Simple event class for state manager threshold violations"""
    def __init__(self, component_id: str, timestamp: float, data: dict):
        self.component_id = component_id
        self.timestamp = timestamp
        self.data = data


def map_equipment_type_to_subsystem(equipment_type: str) -> str:
    """
    Map equipment type to subsystem name for config lookup
    
    The maintenance config is organized by subsystem names (feedwater, turbine, etc.)
    but components are classified by equipment type (pump, turbine_stage, etc.).
    This function bridges that gap.
    
    Args:
        equipment_type: Equipment type from component metadata (e.g., "pump")
        
    Returns:
        Subsystem name for config lookup (e.g., "feedwater")
    """
    equipment_to_subsystem = {
        "pump": "feedwater",
        "turbine_stage": "turbine", 
        "steam_generator": "steam_generator",
        "condenser": "condenser",
        "lubrication_system": "feedwater",  # Lubrication systems are part of feedwater
        "control_system": None,  # Control systems don't have maintenance configs
        "protection_system": None,  # Protection systems don't have maintenance configs
        "unknown": None  # Handle unknown types gracefully
    }
    return equipment_to_subsystem.get(equipment_type, equipment_type)


class AutoMaintenanceSystem:
    """
    Automatic maintenance system that acts like virtual plant operators
    
    This system now uses the state manager as the single source of truth for
    all component monitoring and threshold detection.
    """
    
    def __init__(self):
        # Core components - NO MORE EVENT BUS!
        self.work_order_manager = WorkOrderManager()
        self.maintenance_catalog = get_maintenance_catalog()
        self.state_manager = None  # Will be set during setup
        
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
        self.work_order_cooldown_hours = 24.0  # Minimum time between same work orders (24 hours)
        
        # No more event subscriptions - state manager handles everything!
        print("AUTO MAINTENANCE: 🚀 PHASE 3: Event bus removed - using state manager only")
    
    def setup_monitoring_from_state_manager(self, state_manager, aggressive_mode: bool = False):
        """
        PHASE 2: Setup monitoring using state manager as single source of truth
        
        Args:
            state_manager: StateManager instance with registered components
            aggressive_mode: If True, use aggressive thresholds for demos
        """
        print(f"AUTO MAINTENANCE: 🚀 PHASE 2: Setting up monitoring via state manager")
        
        # Store reference to state manager
        self.state_manager = state_manager
        
        # Load maintenance configuration through state manager
        maintenance_config = state_manager.load_maintenance_config()
        
        # CRITICAL DEBUG: Show what's actually in the maintenance config
        print(f"AUTO MAINTENANCE: 🔍 Maintenance config structure:")
        print(f"  Mode: {maintenance_config.get('mode', 'unknown')}")
        print(f"  Component configs keys: {list(maintenance_config.get('component_configs', {}).keys())}")
        for config_key, config_data in maintenance_config.get('component_configs', {}).items():
            print(f"    {config_key}: {len(config_data.get('thresholds', {}))} thresholds")
        
        # Subscribe to state manager's threshold events
        state_manager.subscribe_to_threshold_events(self._handle_state_manager_threshold)
        
        # Apply maintenance thresholds to components registered in state manager
        components_configured = 0
        
        # Get all registered components from state manager
        registered_instances = state_manager.get_registered_instance_info()
        
        print(f"AUTO MAINTENANCE: 🔍 Found {len(registered_instances)} registered instances:")
        for instance_id, instance_info in registered_instances.items():
            print(f"  - {instance_id}: {instance_info['class_name']}")
        
        for instance_id, instance_info in registered_instances.items():
            try:
                # CRITICAL FIX: Filter out standalone subsystem instances
                if instance_id.endswith('-LUB') or 'lubrication' in instance_id.lower():
                    print(f"AUTO MAINTENANCE: 🚫 Skipping lubrication system instance {instance_id}")
                    continue
                
                if any(suffix in instance_id for suffix in ['-CTRL', '-PROT', '-DIAG', '-MON']):
                    print(f"AUTO MAINTENANCE: 🚫 Skipping subsystem instance {instance_id}")
                    continue
                
                # Get component metadata
                from simulator.state.component_metadata import ComponentRegistry
                component_metadata = ComponentRegistry.get_component(instance_id)
                if not component_metadata:
                    print(f"AUTO MAINTENANCE: No metadata found for {instance_id}, skipping")
                    continue
                
                equipment_type = component_metadata['metadata'].equipment_type.value
                
                # CRITICAL FIX: The state manager already mapped subsystem to equipment type
                # So we should look up by equipment_type directly, not by subsystem_name
                print(f"AUTO MAINTENANCE: 🔄 Looking up config for equipment type '{equipment_type}'")
                
                # Check if we have maintenance config for this equipment type
                if equipment_type in maintenance_config.get('component_configs', {}):
                    config_data = maintenance_config['component_configs'][equipment_type]
                    thresholds = config_data.get('thresholds', {})
                    
                    if thresholds:
                        # Apply thresholds to state manager
                        state_manager.apply_maintenance_thresholds(instance_id, thresholds)
                        components_configured += 1
                        
                        print(f"AUTO MAINTENANCE: ✅ Configured {instance_id} ({equipment_type}) with {len(thresholds)} thresholds")
                        
                        # Show specific oil_level threshold for debugging
                        if 'oil_level' in thresholds:
                            oil_threshold = thresholds['oil_level']
                            print(f"    🛢️ oil_level: {oil_threshold.get('threshold')}% {oil_threshold.get('comparison')} -> {oil_threshold.get('action')}")
                    else:
                        print(f"AUTO MAINTENANCE: ⚠️ No thresholds found for {instance_id} ({equipment_type})")
                else:
                    print(f"AUTO MAINTENANCE: ⚠️ No maintenance config for equipment type '{equipment_type}'")
                
            except Exception as e:
                print(f"AUTO MAINTENANCE: Failed to configure {instance_id}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"AUTO MAINTENANCE: ✅ PHASE 2 Complete - configured {components_configured} components via state manager")
        
        # Set execution delays based on mode
        if aggressive_mode:
            self.emergency_delay_hours = 0.0
            self.high_priority_delay_hours = 0.0
            self.medium_priority_delay_hours = 0.0
            self.low_priority_delay_hours = 0.0
            print("AUTO MAINTENANCE: Configured for aggressive mode (immediate execution)")
        else:
            self.emergency_delay_hours = 0.0      # Keep emergency immediate
            self.high_priority_delay_hours = 1.0  # 1 hour delay
            self.medium_priority_delay_hours = 4.0 # 4 hour delay  
            self.low_priority_delay_hours = 24.0   # 24 hour delay
            print("AUTO MAINTENANCE: Configured for realistic priority-based delays")

    def update(self, current_time_minutes: float, dt: float) -> List[WorkOrder]:
        """
        PHASE 3: Main update loop - now uses state manager only
        
        Args:
            current_time_minutes: Current simulation time in minutes
            dt: Time step
            
        Returns:
            List of work orders created or executed this update
        """
        # Only check periodically, not every simulation step
        # Convert check interval from hours to minutes for comparison
        check_interval_minutes = self.check_interval_hours * 60
        
        # Allow first check immediately when last_check_time is 0.0
        if self.last_check_time > 0.0 and current_time_minutes - self.last_check_time < check_interval_minutes:
            return []
        
        self.last_check_time = current_time_minutes
        new_work_orders = []
        
        # Clear the current update work orders list
        self.current_update_work_orders = []
        
        # PHASE 3: State manager handles all threshold checking automatically during state collection
        # No need to explicitly check components - state manager does this during collect_states()
        
        # Add newly created work orders from state manager threshold events
        new_work_orders.extend(self.current_update_work_orders)
        
        # Execute scheduled work orders
        if self.auto_execute_maintenance:
            executed_orders = self._execute_scheduled_work_orders(current_time_minutes)
            new_work_orders.extend(executed_orders)
        
        return new_work_orders
    
    # PHASE 3: Legacy event handlers removed - state manager handles all events now
    # These methods are kept for backward compatibility but are no longer used
    
    def _handle_state_manager_threshold(self, violation_data: dict):
        """
        PHASE 2: Handle threshold violation events from state manager
        
        Args:
            violation_data: Threshold violation data from state manager
        """
        component_id = violation_data.get('component_id')
        parameter = violation_data.get('parameter')
        value = violation_data.get('value')
        threshold = violation_data.get('threshold')
        comparison = violation_data.get('comparison')
        action = violation_data.get('action')
        priority = violation_data.get('priority', 'MEDIUM')
        timestamp = violation_data.get('timestamp')
        
        # PHASE 2 FIX: Check if we've already processed this exact violation recently
        violation_key = f"{component_id}:{parameter}:{action}:{timestamp}"
        if hasattr(self, '_processed_violations'):
            if violation_key in self._processed_violations:
                print(f"AUTO MAINTENANCE: 🔄 Skipping already processed violation: {component_id}.{parameter}")
                return
        else:
            self._processed_violations = set()
        
        # Mark this violation as processed
        self._processed_violations.add(violation_key)
        
        print(f"AUTO MAINTENANCE: 🚨 PHASE 2: State manager threshold violation: {component_id}.{parameter} = {value:.2f} {comparison} {threshold} -> {action}")
        
        if not action:
            print(f"AUTO MAINTENANCE: No action specified for {component_id} {parameter} threshold")
            return
        
        # Convert priority string to Priority enum
        priority_map = {
            'EMERGENCY': Priority.EMERGENCY,
            'CRITICAL': Priority.CRITICAL,
            'HIGH': Priority.HIGH,
            'MEDIUM': Priority.MEDIUM,
            'LOW': Priority.LOW
        }
        priority_enum = priority_map.get(priority.upper(), Priority.MEDIUM)
        
        # Create a MaintenanceEvent-like object for compatibility
        event_data = {
            'parameter': parameter,
            'value': value,
            'threshold': threshold,
            'comparison': comparison,
            'action': action
        }
        
        # Create a simple event object
        event = StateManagerEvent(component_id, timestamp, event_data)
        
        # Create work order using existing logic
        work_order = self._create_automatic_work_order(
            component_id=component_id,
            action_type=action,
            priority=priority_enum,
            trigger_reason=f"State manager threshold: {parameter} = {value:.2f} {comparison} {threshold}",
            event=event
        )
        
        if work_order:
            # Add the newly created work order to the current update list
            self.current_update_work_orders.append(work_order)
            formatted_time = work_order._format_simulation_time(work_order.created_date)
            print(f"AUTO MAINTENANCE: ✅ PHASE 2: Created work order {work_order.work_order_id} for {component_id} - {action} at {formatted_time}")
            
            # Record maintenance result back to state manager if available
            if hasattr(self, 'state_manager') and self.state_manager:
                # We'll record the result after execution, for now just log
                print(f"AUTO MAINTENANCE: 📝 Will report maintenance result back to state manager")
        else:
            print(f"AUTO MAINTENANCE: ❌ PHASE 2: Failed to create work order for {component_id} - {action}")
    
    def _create_automatic_work_order(self, component_id: str, action_type: str,
                                   priority: Priority, trigger_reason: str,
                                   event: StateManagerEvent) -> Optional[WorkOrder]:
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
        
        # PHASE 3: Get component information from state manager instead of event bus
        if not self.state_manager:
            print(f"AUTO MAINTENANCE: State manager not available")
            return None
        
        # Get component from state manager
        registered_instances = self.state_manager.get_registered_instance_info()
        if component_id not in registered_instances:
            print(f"AUTO MAINTENANCE: Component {component_id} not found in state manager")
            return None
        
        component_info = registered_instances[component_id]
        component_status = {
            'class_name': component_info['class_name']
        }
        
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
    
    def _calculate_start_time(self, current_time_minutes: float, priority: Priority) -> float:
        """Calculate when work order should start based on priority (all times in minutes)"""
        if priority == Priority.EMERGENCY:
            return current_time_minutes + (self.emergency_delay_hours * 60)
        elif priority == Priority.CRITICAL:
            return current_time_minutes + (self.high_priority_delay_hours * 0.5 * 60)
        elif priority == Priority.HIGH:
            return current_time_minutes + (self.high_priority_delay_hours * 60)
        elif priority == Priority.MEDIUM:
            return current_time_minutes + (self.medium_priority_delay_hours * 60)
        else:  # LOW
            return current_time_minutes + (self.low_priority_delay_hours * 60)
    
    def _execute_scheduled_work_orders(self, current_time_minutes: float) -> List[WorkOrder]:
        """Execute work orders that are scheduled for current time"""
        executed_orders = []
        
        scheduled_orders = self.work_order_manager.get_work_orders_by_status(WorkOrderStatus.SCHEDULED)
        
        for work_order in scheduled_orders:
            if (work_order.planned_start_date and 
                current_time_minutes >= work_order.planned_start_date):
                
                # Check if component is available for maintenance
                if self._can_perform_maintenance(work_order.component_id, work_order):
                    success = self._execute_work_order(work_order, current_time_minutes)
                    if success:
                        executed_orders.append(work_order)
                else:
                    # Reschedule for later (convert 1 hour to minutes)
                    work_order.planned_start_date = current_time_minutes + 60.0  # Try again in 1 hour (60 minutes)
                    print(f"AUTO MAINTENANCE: Rescheduled {work_order.work_order_id} - component not available")
        
        return executed_orders
    
    def _can_perform_maintenance(self, component_id: str, work_order: WorkOrder) -> bool:
        """PHASE 3: Check if maintenance can be performed on component using state manager"""
        if not self.state_manager:
            return False
            
        # Get component from state manager
        registered_instances = self.state_manager.get_registered_instance_info()
        if component_id not in registered_instances:
            return False
        
        # For now, assume maintenance can always be performed
        # This could be enhanced to check component status, running state, etc.
        return True
    
    def _execute_work_order(self, work_order: WorkOrder, current_time: float) -> bool:
        """PHASE 3: Execute a work order on the target component using state manager"""
        
        # Get component from state manager instead of event bus
        if not self.state_manager:
            print(f"AUTO MAINTENANCE: State manager not available")
            return False
            
        registered_instances = self.state_manager.get_registered_instance_info()
        if work_order.component_id not in registered_instances:
            print(f"AUTO MAINTENANCE: Component {work_order.component_id} not found in state manager")
            return False
        
        component = registered_instances[work_order.component_id]['instance']
        
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
        
        # Complete work order immediately (zero duration)
        work_summary = "; ".join(work_performed) if work_performed else "Maintenance completed"
        self.work_order_manager.complete_work_order(
            work_order.work_order_id,
            current_time,  # Complete at current time (zero duration)
            success,
            work_summary
        )
        
        # PHASE 3: Record maintenance result back to state manager
        if self.state_manager and work_order.maintenance_actions:
            for action in work_order.maintenance_actions:
                # Calculate effectiveness based on action success and duration
                effectiveness = 1.0 if action.success else 0.0
                
                # Record the maintenance result
                self.state_manager.record_maintenance_result(
                    component_id=work_order.component_id,
                    action_type=action.action_type,
                    success=action.success,
                    effectiveness=effectiveness
                )
                
                print(f"AUTO MAINTENANCE: 📝 Recorded maintenance result: {work_order.component_id} {action.action_type} {'✅' if action.success else '❌'}")
        
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
        """PHASE 3: Get current status of the automatic maintenance system using state manager"""
        work_order_stats = self.work_order_manager.get_statistics()
        
        # Get state manager stats if available
        state_manager_stats = {}
        if self.state_manager:
            state_manager_stats = {
                'registered_components': len(self.state_manager.get_registered_instance_info()),
                'maintenance_thresholds': len(self.state_manager.get_components_with_maintenance_thresholds()),
                'threshold_violations': len(self.state_manager.get_current_threshold_violations()),
                'maintenance_history': len(self.state_manager.get_maintenance_history())
            }
        
        return {
            'auto_execute_enabled': self.auto_execute_maintenance,
            'check_interval_hours': self.check_interval_hours,
            'last_check_time': self.last_check_time,
            'work_orders_created': self.work_orders_created,
            'work_orders_executed': self.work_orders_executed,
            'maintenance_actions_performed': self.maintenance_actions_performed,
            'state_manager_stats': state_manager_stats,
            'work_order_stats': work_order_stats
        }
    
    def get_component_summary(self) -> Dict[str, Any]:
        """PHASE 3: Get summary of all registered components from state manager"""
        if not self.state_manager:
            return {}
        
        return self.state_manager.get_registered_instance_info()
    
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
        """PHASE 3: Reset the automatic maintenance system completely - no more event bus!"""
        # Reset work order manager
        self.work_order_manager.reset()
        
        # Reset statistics
        self.work_orders_created = 0
        self.work_orders_executed = 0
        self.maintenance_actions_performed = 0
        self.last_check_time = 0.0
        
        # Reset all maintenance configuration state
        self.reset_maintenance_config()
        
        # Clear work order tracking
        self.current_update_work_orders = []
        self.recent_work_order_triggers = {}
        
        # PHASE 2 FIX: Clear processed violations tracking
        if hasattr(self, '_processed_violations'):
            self._processed_violations.clear()
        
        # Clear state manager reference
        self.state_manager = None
        
        print("AUTO MAINTENANCE: ✅ PHASE 3: Complete system reset - event bus removed")
    
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
            print(f"AUTO MAINTENANCE: ✅ Using explicit maintenance configuration")
            return self._explicit_maintenance_config
        
        # If config was already loaded, reuse it
        if hasattr(self, '_loaded_maintenance_config') and self._loaded_maintenance_config:
            print(f"AUTO MAINTENANCE: ✅ Using cached maintenance configuration")
            return self._loaded_maintenance_config
        
        # Load config from available sources with PRIORITY ORDER
        maintenance_config = None
        config_source = None
        config_source_name = "unknown"
        
        print(f"AUTO MAINTENANCE: 🔍 Searching for maintenance configuration...")
        
        # PRIORITY 1: Check for comprehensive config in state_manager.config (highest priority)
        if hasattr(state_manager, 'config') and state_manager.config:
            config_source = state_manager.config
            config_source_name = "state_manager.config"
            print(f"AUTO MAINTENANCE: 📋 Found config source: {config_source_name}")
        # PRIORITY 2: Check secondary_config passed from simulator
        elif hasattr(self, 'secondary_config') and self.secondary_config:
            config_source = self.secondary_config
            config_source_name = "secondary_config"
            print(f"AUTO MAINTENANCE: 📋 Found config source: {config_source_name}")
        # PRIORITY 3: Check simulator's secondary physics config
        elif hasattr(state_manager, 'simulator') and hasattr(state_manager.simulator, 'secondary_physics') and hasattr(state_manager.simulator.secondary_physics, 'config'):
            config_source = state_manager.simulator.secondary_physics.config
            config_source_name = "simulator.secondary_physics.config"
            print(f"AUTO MAINTENANCE: 📋 Found config source: {config_source_name}")
        
        if config_source:
            print(f"AUTO MAINTENANCE: 🔧 Processing config from {config_source_name}")
            
            # CRITICAL FIX: Check for maintenance_system.component_configs FIRST (comprehensive composer format)
            if isinstance(config_source, dict) and 'maintenance_system' in config_source:
                maintenance_system = config_source['maintenance_system']
                print(f"AUTO MAINTENANCE: 🎯 Found maintenance_system section with keys: {list(maintenance_system.keys())}")
                
                if 'component_configs' in maintenance_system:
                    print(f"AUTO MAINTENANCE: ✅ Found component_configs in maintenance_system - using comprehensive config!")
                    
                    # Create a temporary config object with the right structure for the YAML loader
                    temp_config = type('TempConfig', (), {})()
                    temp_config.maintenance_component_configs = maintenance_system['component_configs']
                    temp_config.maintenance_mode = maintenance_system.get('maintenance_mode', 'realistic')
                    temp_config.maintenance_threshold_multiplier = maintenance_system.get('maintenance_threshold_multiplier', 1.0)
                    temp_config.maintenance_cooldown_reduction_factor = maintenance_system.get('maintenance_cooldown_reduction_factor', 1.0)
                    temp_config.maintenance_check_interval_multiplier = maintenance_system.get('maintenance_check_interval_multiplier', 1.0)
                    temp_config.maintenance_work_order_cooldown_hours = maintenance_system.get('maintenance_work_order_cooldown_hours', 24.0)
                    
                    maintenance_config = self._create_maintenance_config_from_yaml(temp_config)
                    print(f"AUTO MAINTENANCE: ✅ Successfully loaded comprehensive maintenance config from {config_source_name}")
                    
                    # CRITICAL DEBUG: Show detailed threshold information
                    component_configs = maintenance_system['component_configs']
                    for subsystem, config_data in component_configs.items():
                        thresholds = config_data.get('thresholds', {})
                        print(f"  📊 {subsystem}: {len(thresholds)} thresholds, {config_data.get('check_interval_hours', 'unknown')}h interval")
                        
                        # Show specific oil_level threshold for debugging
                        if 'oil_level' in thresholds:
                            oil_threshold = thresholds['oil_level']
                            print(f"    🛢️ oil_level: {oil_threshold.get('threshold', 'unknown')}% {oil_threshold.get('comparison', 'unknown')} -> {oil_threshold.get('action', 'unknown')}")
                else:
                    print(f"AUTO MAINTENANCE: ⚠️ maintenance_system found but no component_configs")
            
            # FALLBACK: Check for maintenance.component_configs (alternative format)
            elif isinstance(config_source, dict) and 'maintenance' in config_source:
                maintenance_section = config_source['maintenance']
                print(f"AUTO MAINTENANCE: 🔍 Found maintenance section with keys: {list(maintenance_section.keys())}")
                
                if 'component_configs' in maintenance_section:
                    print(f"AUTO MAINTENANCE: ✅ Found component_configs in maintenance section")
                    
                    temp_config = type('TempConfig', (), {})()
                    temp_config.maintenance_component_configs = maintenance_section['component_configs']
                    temp_config.maintenance_mode = maintenance_section.get('maintenance_mode', 'realistic')
                    temp_config.maintenance_threshold_multiplier = maintenance_section.get('maintenance_threshold_multiplier', 1.0)
                    temp_config.maintenance_cooldown_reduction_factor = maintenance_section.get('maintenance_cooldown_reduction_factor', 1.0)
                    temp_config.maintenance_check_interval_multiplier = maintenance_section.get('maintenance_check_interval_multiplier', 1.0)
                    temp_config.maintenance_work_order_cooldown_hours = maintenance_section.get('maintenance_work_order_cooldown_hours', 24.0)
                    
                    maintenance_config = self._create_maintenance_config_from_yaml(temp_config)
                    print(f"AUTO MAINTENANCE: ✅ Loaded config from maintenance section")
                else:
                    print(f"AUTO MAINTENANCE: ⚠️ maintenance section found but no component_configs")
            
            # FALLBACK: Check for old format maintenance_component_configs
            elif hasattr(config_source, 'maintenance_component_configs') and config_source.maintenance_component_configs:
                print(f"AUTO MAINTENANCE: 🔍 Found old format maintenance_component_configs")
                maintenance_config = self._create_maintenance_config_from_yaml(config_source)
                print(f"AUTO MAINTENANCE: ✅ Loaded config from maintenance_component_configs (old format)")
            
            # FALLBACK: Check for aggressive mode indicators
            elif hasattr(config_source, 'maintenance_ultra_aggressive_mode') and config_source.maintenance_ultra_aggressive_mode:
                maintenance_config = MaintenanceConfigFactory.create_ultra_aggressive()
                print(f"AUTO MAINTENANCE: ✅ Loaded ultra-aggressive factory config")
            else:
                print(f"AUTO MAINTENANCE: ⚠️ Config source found but no recognized maintenance configuration format")
        else:
            print(f"AUTO MAINTENANCE: ⚠️ No config source found")
        
        # CRITICAL FIX: Fallback to factory defaults if no YAML config found
        if maintenance_config is None:
            print(f"AUTO MAINTENANCE: 🔄 No comprehensive config found, using factory defaults")
            if aggressive_mode:
                maintenance_config = MaintenanceConfigFactory.create_aggressive()
                print(f"AUTO MAINTENANCE: ⚠️ Using aggressive factory config (fallback)")
            else:
                maintenance_config = MaintenanceConfigFactory.create_conservative()
                print(f"AUTO MAINTENANCE: ⚠️ Using conservative factory config (fallback)")
        
        # Cache the loaded config for reuse
        self._loaded_maintenance_config = maintenance_config
        
        # CRITICAL DEBUG: Show final configuration summary
        print(f"AUTO MAINTENANCE: 📊 Final configuration summary:")
        print(f"  Mode: {maintenance_config.mode}")
        print(f"  Equipment types: {len(maintenance_config.component_types)}")
        for equipment_type, config in maintenance_config.component_types.items():
            print(f"    {equipment_type}: {len(config.thresholds)} thresholds, {config.check_interval_hours}h interval")
        
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
    
    def apply_explicit_config_override(self, config):
        """
        Apply explicit config AFTER auto discovery completes
        
        This method allows auto discovery to run normally, then overrides
        the monitoring configurations with our explicit subsystem-specific settings.
        
        Args:
            config: Configuration dict containing maintenance_system section
        """
        print(f"AUTO MAINTENANCE: 🔧 Applying post-discovery config override")
        
        # Create explicit maintenance config from the provided config
        if isinstance(config, dict):
            temp_config = type('TempConfig', (), {})()
            if 'maintenance_system' in config:
                temp_config.maintenance_component_configs = config['maintenance_system']['component_configs']
                temp_config.maintenance_mode = config['maintenance_system'].get('maintenance_mode', 'subsystem_specific')
            else:
                temp_config.maintenance_component_configs = config
                temp_config.maintenance_mode = 'subsystem_specific'
            
            explicit_config = self._create_maintenance_config_from_yaml(temp_config)
        else:
            explicit_config = config
        
        # Map subsystem names to equipment types
        subsystem_to_equipment_mapping = {
            'feedwater': 'pump',
            'turbine': 'turbine_stage', 
            'steam_generator': 'steam_generator',
            'condenser': 'condenser'
        }
        
        components_updated = 0
        
        # For each registered component, check if we should override its config
        for component_id, component_info in self.event_bus.components.items():
            try:
                # Get component metadata to determine equipment type
                from simulator.state.component_metadata import ComponentRegistry
                component_metadata = ComponentRegistry.get_component(component_id)
                
                if not component_metadata:
                    continue
                    
                equipment_type = component_metadata['metadata'].equipment_type.value
                
                # Check if we have explicit config for this equipment type
                if equipment_type in explicit_config.component_types:
                    explicit_component_config = explicit_config.component_types[equipment_type]
                    
                    # Get component's current state variables
                    component = component_info['component']
                    if hasattr(component, 'get_state_dict'):
                        state_variables = component.get_state_dict()
                        
                        # Generate new monitoring config using explicit thresholds
                        from .maintenance_templates import generate_monitoring_config
                        new_monitoring_config = generate_monitoring_config(
                            state_variables,
                            component_metadata['metadata'].equipment_type,
                            component_id,
                            explicit_config
                        )
                        
                        if new_monitoring_config:
                            # Update the component's monitoring configuration
                            self.event_bus.update_component_monitoring(component_id, new_monitoring_config)
                            components_updated += 1
                            
                            print(f"AUTO MAINTENANCE: ✅ Updated {component_id} ({equipment_type}) with {len(new_monitoring_config)} explicit thresholds")
                        else:
                            print(f"AUTO MAINTENANCE: ⚠️ No monitoring config generated for {component_id}")
                    else:
                        print(f"AUTO MAINTENANCE: ⚠️ Component {component_id} has no get_state_dict method")
                        
            except Exception as e:
                print(f"AUTO MAINTENANCE: ❌ Failed to update {component_id}: {e}")
                continue
        
        # Store the explicit config for future reference
        self._explicit_maintenance_config = explicit_config
        self._loaded_maintenance_config = explicit_config
        
        print(f"AUTO MAINTENANCE: ✅ Post-discovery override complete - updated {components_updated} components")
        
        # Show final configuration status
        for equipment_type, config in explicit_config.component_types.items():
            print(f"AUTO MAINTENANCE: 📋 {equipment_type}: {len(config.thresholds)} thresholds, {config.check_interval_hours}h interval")
        
        return explicit_config
    
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
        generated by the ComprehensiveComposer and maps subsystem names to equipment types.
        """
        from .config import MaintenanceConfig, MaintenanceMode, ComponentTypeConfig, ComponentThresholds
        
        print(f"AUTO MAINTENANCE: 🔧 Creating maintenance config from YAML")
        
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
            print(f"AUTO MAINTENANCE: 📋 Set maintenance mode to {maintenance_config.mode}")
        
        # CRITICAL FIX: Map subsystem names to equipment type names
        subsystem_to_equipment_mapping = {
            'feedwater': 'pump',  # feedwater subsystem contains pump equipment
            'turbine': 'turbine_stage',  # turbine subsystem contains turbine_stage equipment
            'steam_generator': 'steam_generator',  # direct mapping
            'condenser': 'condenser'  # direct mapping
        }
        
        # Load component-specific configurations from new subsystem-specific format
        if hasattr(yaml_config, 'maintenance_component_configs'):
            component_configs = yaml_config.maintenance_component_configs
            print(f"AUTO MAINTENANCE: 📊 Processing {len(component_configs)} subsystem configs")
            
            for subsystem_name, config_data in component_configs.items():
                print(f"AUTO MAINTENANCE: 🔍 Processing subsystem: {subsystem_name}")
                print(f"AUTO MAINTENANCE: 📋 Config data keys: {list(config_data.keys())}")
                
                # Map subsystem name to equipment type name
                equipment_type_name = subsystem_to_equipment_mapping.get(subsystem_name, subsystem_name)
                print(f"AUTO MAINTENANCE: 🔄 Mapping {subsystem_name} -> {equipment_type_name}")
                
                # Create component type configuration
                component_config = ComponentTypeConfig()
                
                # Set check interval directly from config (already calculated by ComprehensiveComposer)
                component_config.check_interval_hours = config_data.get('check_interval_hours', 4.0)
                print(f"AUTO MAINTENANCE: ⏰ Set check interval: {component_config.check_interval_hours}h")
                
                # CRITICAL FIX: Load thresholds directly (already calculated by ComprehensiveComposer)
                if 'thresholds' in config_data:
                    thresholds = config_data['thresholds']
                    print(f"AUTO MAINTENANCE: 🎯 {subsystem_name} has {len(thresholds)} thresholds in config_data")
                    
                    thresholds_added = 0
                    for param_name, threshold_data in thresholds.items():
                        print(f"AUTO MAINTENANCE: 🔧 Processing threshold {param_name}: {threshold_data}")
                        
                        # CRITICAL FIX: Validate threshold data structure
                        if not isinstance(threshold_data, dict):
                            print(f"AUTO MAINTENANCE: ❌ Invalid threshold data for {param_name}: {type(threshold_data)}")
                            continue
                            
                        # Skip thresholds without actions defined
                        if 'action' not in threshold_data:
                            print(f"AUTO MAINTENANCE: ⚠️ Skipping {param_name} - no action defined")
                            continue
                            
                        # CRITICAL FIX: Validate required threshold fields
                        if 'threshold' not in threshold_data:
                            print(f"AUTO MAINTENANCE: ❌ Skipping {param_name} - no threshold value defined")
                            continue
                            
                        # Use thresholds directly (no multiplier calculations needed)
                        try:
                            threshold_config = ComponentThresholds(
                                threshold=threshold_data['threshold'],
                                comparison=threshold_data.get('comparison', 'greater_than'),
                                action=threshold_data['action'],
                                cooldown_hours=threshold_data.get('cooldown_hours', 24.0),
                                priority=threshold_data.get('priority', 'MEDIUM')
                            )
                            
                            component_config.thresholds[param_name] = threshold_config
                            thresholds_added += 1
                            print(f"AUTO MAINTENANCE: ✅ Added threshold {param_name}: {threshold_config.threshold} {threshold_config.comparison} -> {threshold_config.action}")
                            
                        except Exception as e:
                            print(f"AUTO MAINTENANCE: ❌ Failed to create threshold {param_name}: {e}")
                            continue
                else:
                    print(f"AUTO MAINTENANCE: ⚠️ {subsystem_name} has no 'thresholds' key in config_data")
                
                # CRITICAL FIX: Only store component config if it has thresholds
                if len(component_config.thresholds) > 0:
                    # Store in maintenance config using equipment type name
                    maintenance_config.component_types[equipment_type_name] = component_config
                    print(f"AUTO MAINTENANCE: ✅ Stored {subsystem_name} -> {equipment_type_name} with {len(component_config.thresholds)} thresholds")
                else:
                    print(f"AUTO MAINTENANCE: ⚠️ Skipping {subsystem_name} -> {equipment_type_name} - no valid thresholds")
        else:
            print(f"AUTO MAINTENANCE: ❌ No maintenance_component_configs found in YAML config")
        
        print(f"AUTO MAINTENANCE: 📊 Final config has {len(maintenance_config.component_types)} equipment types")
        
        # CRITICAL FIX: Enhanced debug output for verification
        for equipment_type, config in maintenance_config.component_types.items():
            print(f"AUTO MAINTENANCE: 📋 {equipment_type}:")
            print(f"  ⏰ Check interval: {config.check_interval_hours}h")
            print(f"  🎯 Thresholds: {len(config.thresholds)}")
            
            # Show specific thresholds for debugging
            for param_name, threshold in config.thresholds.items():
                print(f"    - {param_name}: {threshold.threshold} ({threshold.comparison}) -> {threshold.action} (cooldown: {threshold.cooldown_hours}h, priority: {threshold.priority})")
        
        return maintenance_config


# Convenience function for easy setup
def create_auto_maintenance_system() -> AutoMaintenanceSystem:
    """Create and return a new automatic maintenance system"""
    return AutoMaintenanceSystem()
