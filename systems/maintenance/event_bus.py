"""
Maintenance Event Bus

This module provides the event-driven communication system for maintenance
management, allowing components to publish maintenance events and the
maintenance system to respond automatically.

Key Features:
1. Publisher-subscriber pattern for loose coupling
2. Component registration and monitoring
3. Automatic parameter checking and threshold detection
4. Event routing and handling
5. No inheritance requirements for components
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import time


@dataclass
class MaintenanceEvent:
    """Represents a maintenance-related event"""
    event_type: str                             # Type of event
    component_id: str                          # Component that generated the event
    timestamp: float                           # When the event occurred
    data: Dict[str, Any]                       # Event data
    priority: str = "MEDIUM"                   # Event priority
    source: str = "SYSTEM"                     # Event source


@dataclass
class ParameterMonitor:
    """Configuration for monitoring a component parameter"""
    component_id: str                          # Component being monitored
    parameter_name: str                        # Name of parameter to monitor
    attribute_path: str                        # Path to attribute (e.g., "state.oil_level")
    threshold_value: Optional[float] = None    # Threshold for triggering
    comparison: str = "greater_than"           # Comparison type
    action: Optional[str] = None               # Suggested maintenance action
    enabled: bool = True                       # Whether monitoring is enabled
    cooldown_hours: float = 24.0              # Minimum time between triggers
    last_triggered: float = 0.0               # Last time this monitor triggered
    last_value: Optional[float] = None        # Last recorded value


class MaintenanceEventBus:
    """
    Central event bus for maintenance events using pure pub/sub pattern
    
    This system allows components to be monitored for maintenance needs
    without requiring any code changes to the components themselves.
    """
    
    def __init__(self):
        # Event subscribers
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Component registry
        self.components: Dict[str, Any] = {}
        self.component_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Parameter monitoring
        self.parameter_monitors: Dict[str, ParameterMonitor] = {}
        
        # Event history
        self.event_history: List[MaintenanceEvent] = []
        self.max_history_size = 1000
        
        # Statistics
        self.events_published = 0
        self.events_processed = 0
        
        # Current simulation time for event timestamps
        self.current_simulation_time = 0.0
        
    def subscribe(self, event_type: str, callback: Callable[[MaintenanceEvent], None]):
        """
        Subscribe to maintenance events
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from maintenance events"""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
    
    def publish(self, event_type: str, component_id: str, data: Dict[str, Any], 
               priority: str = "MEDIUM", source: str = "SYSTEM"):
        """
        Publish a maintenance event
        
        Args:
            event_type: Type of event
            component_id: Component that generated the event
            data: Event data
            priority: Event priority
            source: Event source
        """
        event = MaintenanceEvent(
            event_type=event_type,
            component_id=component_id,
            timestamp=self.current_simulation_time,  # Use simulation time instead of Unix time
            data=data,
            priority=priority,
            source=source
        )
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        self.events_published += 1
        
        # Notify subscribers
        for callback in self.subscribers[event_type]:
            try:
                callback(event)
                self.events_processed += 1
            except Exception as e:
                print(f"Error in event callback for {event_type}: {e}")
    
    def register_component(self, component_id: str, component: Any, 
                          monitoring_config: Dict[str, Dict[str, Any]]):
        """
        Register a component for maintenance monitoring with comprehensive duplicate detection
        
        Args:
            component_id: Unique component identifier
            component: Component instance
            monitoring_config: Configuration for parameter monitoring
        """
        # COMPREHENSIVE DUPLICATE DETECTION
        if component_id in self.components:
            print(f"DUPLICATE PREVENTION: Component {component_id} already registered in EventBus, skipping")
            return
        
        # Check if component is registered in the global ComponentRegistry
        try:
            from .component_registry import get_component_registry
            component_registry = get_component_registry()
            if component_id in component_registry.components:
                print(f"DUPLICATE PREVENTION: Component {component_id} already in ComponentRegistry")
                # Don't return here - we still want to register in EventBus even if it's in ComponentRegistry
        except ImportError:
            pass  # ComponentRegistry not available
        
        # Check for existing parameter monitors that would conflict
        existing_monitors = [mid for mid in self.parameter_monitors.keys() 
                           if mid.startswith(f"{component_id}.")]
        if existing_monitors:
            print(f"DUPLICATE PREVENTION: Component {component_id} has existing monitors: {existing_monitors}")
            print(f"DUPLICATE PREVENTION: Clearing existing monitors for clean re-registration")
            # Remove existing monitors for clean re-registration
            for monitor_id in existing_monitors:
                del self.parameter_monitors[monitor_id]
        
        # Register the component
        self.components[component_id] = component
        self.component_metadata[component_id] = {
            'class_name': component.__class__.__name__,
            'registered_time': time.time(),
            'monitoring_config': monitoring_config
        }
        
        # Create parameter monitors
        monitors_created = 0
        for param_name, param_config in monitoring_config.items():
            monitor_id = f"{component_id}.{param_name}"
            
            # Skip if monitor already exists (shouldn't happen after cleanup above)
            if monitor_id in self.parameter_monitors:
                print(f"DUPLICATE PREVENTION: Monitor {monitor_id} already exists, skipping")
                continue
            
            monitor = ParameterMonitor(
                component_id=component_id,
                parameter_name=param_name,
                attribute_path=param_config.get('attribute', param_name),
                threshold_value=param_config.get('threshold'),
                comparison=param_config.get('comparison', 'greater_than'),
                action=param_config.get('action'),
                enabled=param_config.get('enabled', True),
                cooldown_hours=param_config.get('cooldown_hours', 24.0)
            )
            
            self.parameter_monitors[monitor_id] = monitor
            monitors_created += 1
        
        print(f"EVENT BUS: ✅ Registered component {component_id} with {monitors_created} monitors")
        
        # Also register in ComponentRegistry if available
        try:
            from .component_registry import get_component_registry
            component_registry = get_component_registry()
            component_registry.register_component(component_id, component)
            print(f"EVENT BUS: ✅ Also registered {component_id} in ComponentRegistry")
        except ImportError:
            pass  # ComponentRegistry not available
    
    def unregister_component(self, component_id: str):
        """Unregister a component from monitoring"""
        if component_id in self.components:
            del self.components[component_id]
            del self.component_metadata[component_id]
            
            # Remove parameter monitors
            monitors_to_remove = [mid for mid in self.parameter_monitors.keys() 
                                if mid.startswith(f"{component_id}.")]
            for monitor_id in monitors_to_remove:
                del self.parameter_monitors[monitor_id]
    
    def check_all_components(self, current_time: float):
        """
        Check all registered components for maintenance needs
        
        Args:
            current_time: Current simulation time
        """
        # Update current simulation time for event timestamps
        self.current_simulation_time = current_time
        
        for monitor_id, monitor in self.parameter_monitors.items():
            if not monitor.enabled:
                continue
            
            # Check cooldown (allow first trigger when last_triggered is 0.0)
            if monitor.last_triggered > 0.0 and current_time - monitor.last_triggered < monitor.cooldown_hours:
                continue
            
            try:
                component = self.components.get(monitor.component_id)
                if not component:
                    continue
                
                # Get current parameter value
                current_value = self._get_parameter_value(component, monitor.attribute_path)
                if current_value is None:
                    continue
                
                # Check threshold condition
                if monitor.threshold_value is not None:
                    if self._check_threshold_condition(current_value, monitor.threshold_value, monitor.comparison):
                        # Threshold exceeded
                        self.publish('threshold_exceeded', monitor.component_id, {
                            'parameter': monitor.parameter_name,
                            'value': current_value,
                            'threshold': monitor.threshold_value,
                            'comparison': monitor.comparison,
                            'action': monitor.action
                        }, priority='HIGH')
                        
                        monitor.last_triggered = current_time
                
                # Check for significant parameter changes
                if monitor.last_value is not None:
                    change = abs(current_value - monitor.last_value)
                    if change > 0.1:  # Configurable threshold
                        self.publish('parameter_changed', monitor.component_id, {
                            'parameter': monitor.parameter_name,
                            'old_value': monitor.last_value,
                            'new_value': current_value,
                            'change': change
                        })
                
                monitor.last_value = current_value
                
            except Exception as e:
                print(f"Error checking monitor {monitor_id}: {e}")
    
    def _get_parameter_value(self, component: Any, attribute_path: str) -> Optional[float]:
        """
        Get parameter value from component using attribute path
        
        Args:
            component: Component instance
            attribute_path: Path to attribute (e.g., "state.oil_level" or "pumps.FWP-1.state.oil_level")
            
        Returns:
            Parameter value or None if not found
        """
        try:
            # Handle nested attribute paths with dictionary access
            obj = component
            for attr in attribute_path.split('.'):
                if hasattr(obj, attr):
                    # Standard attribute access
                    obj = getattr(obj, attr)
                elif hasattr(obj, '__getitem__'):
                    # Dictionary-like access
                    obj = obj[attr]
                else:
                    # Try both approaches
                    try:
                        obj = getattr(obj, attr)
                    except AttributeError:
                        obj = obj[attr]
            
            # Convert to float if possible
            if isinstance(obj, (int, float)):
                return float(obj)
            
        except (AttributeError, TypeError, ValueError, KeyError):
            pass
        
        return None
    
    def _check_threshold_condition(self, value: float, threshold: float, comparison: str) -> bool:
        """
        Check if threshold condition is met
        
        Args:
            value: Current value
            threshold: Threshold value
            comparison: Comparison type
            
        Returns:
            True if condition is met
        """
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
    
    def get_component_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a registered component"""
        if component_id not in self.components:
            return None
        
        component = self.components[component_id]
        metadata = self.component_metadata[component_id]
        
        # Get current parameter values
        current_values = {}
        for monitor_id, monitor in self.parameter_monitors.items():
            if monitor.component_id == component_id:
                value = self._get_parameter_value(component, monitor.attribute_path)
                current_values[monitor.parameter_name] = value
        
        return {
            'component_id': component_id,
            'class_name': metadata['class_name'],
            'registered_time': metadata['registered_time'],
            'current_values': current_values,
            'num_monitors': len([m for m in self.parameter_monitors.values() 
                               if m.component_id == component_id])
        }
    
    def get_all_component_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered components"""
        return {cid: self.get_component_status(cid) for cid in self.components.keys()}
    
    def get_recent_events(self, event_type: str = None, component_id: str = None, 
                         limit: int = 50) -> List[MaintenanceEvent]:
        """
        Get recent maintenance events
        
        Args:
            event_type: Filter by event type
            component_id: Filter by component ID
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        events = self.event_history
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if component_id:
            events = [e for e in events if e.component_id == component_id]
        
        # Return most recent events
        return events[-limit:] if len(events) > limit else events
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'registered_components': len(self.components),
            'active_monitors': len([m for m in self.parameter_monitors.values() if m.enabled]),
            'total_monitors': len(self.parameter_monitors),
            'events_published': self.events_published,
            'events_processed': self.events_processed,
            'event_history_size': len(self.event_history),
            'subscriber_count': sum(len(subs) for subs in self.subscribers.values()),
            'event_types': list(self.subscribers.keys())
        }
    
    def enable_monitor(self, component_id: str, parameter_name: str):
        """Enable monitoring for a specific parameter"""
        monitor_id = f"{component_id}.{parameter_name}"
        if monitor_id in self.parameter_monitors:
            self.parameter_monitors[monitor_id].enabled = True
    
    def disable_monitor(self, component_id: str, parameter_name: str):
        """Disable monitoring for a specific parameter"""
        monitor_id = f"{component_id}.{parameter_name}"
        if monitor_id in self.parameter_monitors:
            self.parameter_monitors[monitor_id].enabled = False
    
    def update_monitor_threshold(self, component_id: str, parameter_name: str, 
                               new_threshold: float):
        """Update threshold for a parameter monitor"""
        monitor_id = f"{component_id}.{parameter_name}"
        if monitor_id in self.parameter_monitors:
            self.parameter_monitors[monitor_id].threshold_value = new_threshold
    
    def clear_event_history(self):
        """Clear event history"""
        self.event_history.clear()
        self.events_published = 0
        self.events_processed = 0
    
    def reset(self):
        """Reset the event bus completely"""
        self.subscribers.clear()
        self.components.clear()
        self.component_metadata.clear()
        self.parameter_monitors.clear()
        self.clear_event_history()
