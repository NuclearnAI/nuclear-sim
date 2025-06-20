"""
Work Order Management

This module defines the core data structures for maintenance work orders,
providing a realistic work order system similar to those used in actual
nuclear power plants.

Key Features:
1. Comprehensive work order tracking from creation to completion
2. Priority-based scheduling and execution
3. Complete audit trail and documentation
4. Integration with maintenance actions and component registry
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class WorkOrderType(Enum):
    """Types of maintenance work orders"""
    PREVENTIVE = "preventive"       # Scheduled preventive maintenance
    CORRECTIVE = "corrective"       # Fix known problems
    EMERGENCY = "emergency"         # Immediate action required
    PREDICTIVE = "predictive"       # Based on condition monitoring
    MODIFICATION = "modification"   # Equipment modifications
    INSPECTION = "inspection"       # Routine inspections
    CALIBRATION = "calibration"     # Instrument calibration
    CLEANING = "cleaning"           # System cleaning and flushing


class Priority(Enum):
    """Work order priority levels"""
    LOW = 1                         # Can wait weeks/months
    MEDIUM = 2                      # Should be done within weeks  
    HIGH = 3                        # Should be done within days
    CRITICAL = 4                    # Should be done within hours
    EMERGENCY = 5                   # Immediate action required


class WorkOrderStatus(Enum):
    """Work order status tracking"""
    DRAFT = "draft"                 # Being created
    PLANNED = "planned"             # Ready for scheduling
    SCHEDULED = "scheduled"         # Scheduled for specific time
    IN_PROGRESS = "in_progress"     # Work is being performed
    ON_HOLD = "on_hold"            # Temporarily suspended
    COMPLETED = "completed"         # Work finished successfully
    CANCELLED = "cancelled"         # Work order cancelled
    FAILED = "failed"               # Work order failed


@dataclass
class WorkOrderAction:
    """Individual action within a work order"""
    action_type: str                # Type of maintenance action
    description: str                # Detailed description
    estimated_duration: float      # Estimated hours
    actual_duration: Optional[float] = None  # Actual hours taken
    success: Optional[bool] = None  # Whether action succeeded
    findings: Optional[str] = None  # What was found during work
    recommendations: List[str] = field(default_factory=list)  # Future recommendations


@dataclass
class WorkOrder:
    """
    Comprehensive work order for maintenance activities
    
    This represents a complete maintenance work order similar to those
    used in actual nuclear power plants, with full tracking and documentation.
    """
    
    # Core Identification
    work_order_id: str              # Unique work order ID (e.g., "WO-001234")
    work_order_type: WorkOrderType  # Type of maintenance work
    priority: Priority              # Priority level
    
    # Component Information
    component_id: str               # Target component ID
    component_type: Optional[str] = None  # Type of component
    system: Optional[str] = None    # System name
    subsystem: Optional[str] = None # Subsystem name
    
    # Work Description
    title: str = ""                 # Short title
    description: str = ""           # Detailed description
    maintenance_actions: List[WorkOrderAction] = field(default_factory=list)
    
    # Scheduling and Timing
    created_date: float = 0.0       # When work order was created (simulation time)
    planned_start_date: Optional[float] = None  # Planned start time
    planned_duration: float = 0.0   # Estimated total duration
    actual_start_date: Optional[float] = None   # Actual start time
    actual_completion_date: Optional[float] = None  # Actual completion time
    actual_duration: Optional[float] = None     # Actual total duration
    
    # Status and Assignment
    status: WorkOrderStatus = WorkOrderStatus.PLANNED
    assigned_to: Optional[str] = None  # Who is assigned to do the work
    
    # Prerequisites and Requirements
    prerequisites: List[str] = field(default_factory=list)  # Required conditions
    safety_requirements: List[str] = field(default_factory=list)  # Safety procedures
    required_parts: List[str] = field(default_factory=list)  # Parts/materials needed
    required_tools: List[str] = field(default_factory=list)  # Tools needed
    
    # Results and Documentation
    work_performed: Optional[str] = None  # Summary of work performed
    parts_used: List[str] = field(default_factory=list)  # Parts actually used
    findings: Optional[str] = None  # Overall findings
    recommendations: List[str] = field(default_factory=list)  # Future recommendations
    
    # Performance Metrics
    effectiveness_score: Optional[float] = None  # 0-1 scale effectiveness
    cost: Optional[float] = None    # Total cost
    downtime_hours: Optional[float] = None  # Equipment downtime caused
    
    # Automation and Integration
    auto_generated: bool = False    # Whether this was auto-generated
    trigger_id: Optional[str] = None  # ID of trigger that created this
    parent_work_order: Optional[str] = None  # Parent work order if this is a sub-task
    child_work_orders: List[str] = field(default_factory=list)  # Sub-tasks
    related_work_orders: List[str] = field(default_factory=list)  # Related work orders
    
    # Additional metadata
    created_by: str = "AUTO_SYSTEM"  # Who/what created this work order
    notes: List[str] = field(default_factory=list)  # Additional notes
    
    def add_action(self, action_type: str, description: str, estimated_duration: float = 1.0):
        """Add a maintenance action to this work order"""
        action = WorkOrderAction(
            action_type=action_type,
            description=description,
            estimated_duration=estimated_duration
        )
        self.maintenance_actions.append(action)
        self.planned_duration += estimated_duration
    
    def start_work(self, current_time: float, assigned_to: str = "AUTO_OPERATOR"):
        """Start executing this work order"""
        self.status = WorkOrderStatus.IN_PROGRESS
        self.actual_start_date = current_time
        self.assigned_to = assigned_to
    
    def complete_work(self, current_time: float, success: bool = True, 
                     work_summary: str = "", findings: str = ""):
        """Complete this work order"""
        self.status = WorkOrderStatus.COMPLETED if success else WorkOrderStatus.FAILED
        self.actual_completion_date = current_time
        
        if self.actual_start_date:
            self.actual_duration = current_time - self.actual_start_date
        
        if work_summary:
            self.work_performed = work_summary
        if findings:
            self.findings = findings
        
        # Calculate effectiveness score
        if success:
            # Base effectiveness on whether work was completed on time
            if self.actual_duration and self.planned_duration > 0:
                time_efficiency = min(1.0, self.planned_duration / self.actual_duration)
                self.effectiveness_score = time_efficiency
            else:
                self.effectiveness_score = 1.0
        else:
            self.effectiveness_score = 0.0
    
    def add_note(self, note: str):
        """Add a note to this work order"""
        self.notes.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}")
    
    def get_summary(self) -> str:
        """Get a summary string for this work order"""
        return (f"{self.work_order_id}: {self.title} "
                f"({self.component_id}, {self.priority.name}, {self.status.name})")
    
    def get_duration_summary(self) -> Dict[str, float]:
        """Get duration information"""
        return {
            'planned_duration': self.planned_duration,
            'actual_duration': self.actual_duration or 0.0,
            'variance': (self.actual_duration or 0.0) - self.planned_duration,
            'efficiency': (self.planned_duration / (self.actual_duration or 1.0)) if self.actual_duration else 1.0
        }
    
    def is_overdue(self, current_time: float) -> bool:
        """Check if this work order is overdue"""
        if self.status in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED, WorkOrderStatus.FAILED]:
            return False
        
        if self.planned_start_date and current_time > self.planned_start_date + self.planned_duration:
            return True
        
        return False
    
    def get_age_hours(self, current_time: float) -> float:
        """Get age of work order in hours"""
        return current_time - self.created_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert work order to dictionary for serialization"""
        return {
            'work_order_id': self.work_order_id,
            'work_order_type': self.work_order_type.value,
            'priority': self.priority.value,
            'component_id': self.component_id,
            'component_type': self.component_type,
            'system': self.system,
            'subsystem': self.subsystem,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'created_date': self.created_date,
            'planned_start_date': self.planned_start_date,
            'planned_duration': self.planned_duration,
            'actual_start_date': self.actual_start_date,
            'actual_completion_date': self.actual_completion_date,
            'actual_duration': self.actual_duration,
            'assigned_to': self.assigned_to,
            'work_performed': self.work_performed,
            'findings': self.findings,
            'effectiveness_score': self.effectiveness_score,
            'auto_generated': self.auto_generated,
            'trigger_id': self.trigger_id,
            'num_actions': len(self.maintenance_actions),
            'num_notes': len(self.notes)
        }


class WorkOrderManager:
    """Manager for work order operations and queries"""
    
    def __init__(self):
        self.work_orders: Dict[str, WorkOrder] = {}
        self.work_order_counter = 1
        self.completed_work_orders: List[WorkOrder] = []
    
    def create_work_order(self, component_id: str, work_type: WorkOrderType, 
                         priority: Priority, title: str, description: str = "",
                         auto_generated: bool = False, trigger_id: str = None) -> WorkOrder:
        """Create a new work order"""
        
        wo_id = f"WO-{self.work_order_counter:06d}"
        self.work_order_counter += 1
        
        work_order = WorkOrder(
            work_order_id=wo_id,
            work_order_type=work_type,
            priority=priority,
            component_id=component_id,
            title=title,
            description=description,
            auto_generated=auto_generated,
            trigger_id=trigger_id
        )
        
        self.work_orders[wo_id] = work_order
        return work_order
    
    def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]:
        """Get work order by ID"""
        return self.work_orders.get(work_order_id)
    
    def get_work_orders_by_component(self, component_id: str) -> List[WorkOrder]:
        """Get all work orders for a specific component"""
        return [wo for wo in self.work_orders.values() if wo.component_id == component_id]
    
    def get_work_orders_by_status(self, status: WorkOrderStatus) -> List[WorkOrder]:
        """Get all work orders with specific status"""
        return [wo for wo in self.work_orders.values() if wo.status == status]
    
    def get_work_orders_by_priority(self, priority: Priority) -> List[WorkOrder]:
        """Get all work orders with specific priority"""
        return [wo for wo in self.work_orders.values() if wo.priority == priority]
    
    def get_overdue_work_orders(self, current_time: float) -> List[WorkOrder]:
        """Get all overdue work orders"""
        return [wo for wo in self.work_orders.values() if wo.is_overdue(current_time)]
    
    def complete_work_order(self, work_order_id: str, current_time: float, 
                           success: bool = True, work_summary: str = "", findings: str = ""):
        """Complete a work order and move to history"""
        work_order = self.work_orders.get(work_order_id)
        if work_order:
            work_order.complete_work(current_time, success, work_summary, findings)
            
            # Move to completed list
            self.completed_work_orders.append(work_order)
            del self.work_orders[work_order_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get work order statistics"""
        active_orders = list(self.work_orders.values())
        completed_orders = self.completed_work_orders
        
        return {
            'total_active': len(active_orders),
            'total_completed': len(completed_orders),
            'by_status': {status.name: len([wo for wo in active_orders if wo.status == status]) 
                         for status in WorkOrderStatus},
            'by_priority': {priority.name: len([wo for wo in active_orders if wo.priority == priority]) 
                           for priority in Priority},
            'by_type': {wotype.name: len([wo for wo in active_orders if wo.work_order_type == wotype]) 
                       for wotype in WorkOrderType},
            'avg_effectiveness': sum(wo.effectiveness_score for wo in completed_orders 
                                   if wo.effectiveness_score is not None) / max(1, len(completed_orders))
        }
    
    def clear_completed_history(self):
        """Clear completed work order history"""
        self.completed_work_orders.clear()
    
    def reset(self):
        """Reset work order manager"""
        self.work_orders.clear()
        self.completed_work_orders.clear()
        self.work_order_counter = 1
