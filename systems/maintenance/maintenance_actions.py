"""
Maintenance Actions

This module defines the types of maintenance actions that can be performed
on nuclear plant components, along with simplified result structures.

Key Features:
1. Comprehensive catalog of maintenance action types
2. Standardized maintenance result reporting
3. Simple action metadata for planning
4. Integration with component-specific maintenance methods
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class MaintenanceActionType(Enum):
    """
    Comprehensive catalog of maintenance actions for nuclear plant components
    """
    
    # === LUBRICATION ACTIONS ===
    OIL_CHANGE = "oil_change"                   # Complete oil replacement
    OIL_TOP_OFF = "oil_top_off"                # Add oil to restore level
    OIL_ANALYSIS = "oil_analysis"              # Oil quality testing
    FILTER_CHANGE = "filter_change"            # Replace oil filters
    LUBRICATION_INSPECTION = "lubrication_inspection"  # Inspect lubrication system
    OIL_SYSTEM_FLUSH = "oil_system_flush"      # Flush oil system
    
    # === MECHANICAL ACTIONS ===
    BEARING_REPLACEMENT = "bearing_replacement"  # Replace bearings
    BEARING_INSPECTION = "bearing_inspection"    # Inspect bearing condition
    SEAL_REPLACEMENT = "seal_replacement"        # Replace mechanical seals
    SEAL_INSPECTION = "seal_inspection"          # Inspect seal condition
    IMPELLER_REPLACEMENT = "impeller_replacement"  # Replace pump impeller
    IMPELLER_INSPECTION = "impeller_inspection"   # Inspect impeller condition
    COUPLING_ALIGNMENT = "coupling_alignment"     # Align pump/motor coupling
    COUPLING_REPLACEMENT = "coupling_replacement" # Replace coupling
    ROTOR_BALANCING = "rotor_balancing"          # Balance rotating equipment
    
    # === VIBRATION AND ALIGNMENT ===
    VIBRATION_ANALYSIS = "vibration_analysis"   # Vibration monitoring and analysis
    ALIGNMENT_CHECK = "alignment_check"         # Check equipment alignment
    
    # === ELECTRICAL ACTIONS ===
    MOTOR_INSPECTION = "motor_inspection"       # Inspect electric motor
    MOTOR_REPLACEMENT = "motor_replacement"     # Replace electric motor
    ELECTRICAL_TESTING = "electrical_testing"  # Electrical system testing
    INSULATION_TESTING = "insulation_testing"  # Motor insulation testing
    
    # === INSTRUMENTATION ACTIONS ===
    CALIBRATION = "calibration"                 # Instrument calibration
    SENSOR_REPLACEMENT = "sensor_replacement"   # Replace sensors
    CONTROL_SYSTEM_TEST = "control_system_test" # Test control systems
    
    # === CLEANING ACTIONS ===
    CHEMICAL_CLEANING = "chemical_cleaning"     # Chemical cleaning of systems
    MECHANICAL_CLEANING = "mechanical_cleaning" # Mechanical cleaning
    SYSTEM_FLUSH = "system_flush"              # Flush system with clean fluid
    DESCALING = "descaling"                    # Remove scale deposits
    
    # === INSPECTION ACTIONS ===
    VISUAL_INSPECTION = "visual_inspection"     # Visual inspection
    NDT_INSPECTION = "ndt_inspection"          # Non-destructive testing
    PERFORMANCE_TEST = "performance_test"       # Component performance testing
    LEAK_TEST = "leak_test"                    # Leak testing
    
    # === VALVE ACTIONS ===
    VALVE_INSPECTION = "valve_inspection"       # Valve inspection
    VALVE_REPLACEMENT = "valve_replacement"     # Replace valve
    VALVE_PACKING_REPLACEMENT = "valve_packing_replacement"  # Replace valve packing
    
    # === HEAT EXCHANGER ACTIONS ===
    TUBE_CLEANING = "tube_cleaning"            # Clean heat exchanger tubes
    TUBE_INSPECTION = "tube_inspection"        # Inspect heat exchanger tubes
    TUBE_PLUGGING = "tube_plugging"           # Plug defective tubes
    
    # === GENERIC ACTIONS ===
    COMPONENT_REPLACEMENT = "component_replacement"  # Replace entire component
    COMPONENT_OVERHAUL = "component_overhaul"        # Complete component overhaul
    ADJUSTMENT = "adjustment"                        # Adjust component settings
    REPAIR = "repair"                               # General repair work
    ROUTINE_MAINTENANCE = "routine_maintenance"     # Routine preventive maintenance


@dataclass
class MaintenanceResult:
    """
    Result of a maintenance action execution
    """
    
    # Core Results
    success: bool                               # Whether action succeeded
    duration_hours: float                       # Actual time taken
    work_performed: str                         # Description of work done
    
    # Optional Results
    findings: Optional[str] = None              # What was found during work
    recommendations: List[str] = field(default_factory=list)  # Future recommendations
    performance_improvement: Optional[float] = None  # % performance improvement
    parts_used: List[str] = field(default_factory=list)  # Parts/materials used
    cost: Optional[float] = None                # Total cost
    effectiveness_score: Optional[float] = None # Effectiveness of maintenance (0-1)
    next_maintenance_due: Optional[float] = None  # When next maintenance is due (hours)
    
    # Error Information (if failed)
    error_message: Optional[str] = None         # Error description if failed
    
    def add_recommendation(self, recommendation: str):
        """Add a maintenance recommendation"""
        self.recommendations.append(recommendation)
    
    def set_next_maintenance(self, hours_from_now: float):
        """Set when next maintenance is due"""
        self.next_maintenance_due = hours_from_now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'success': self.success,
            'duration_hours': self.duration_hours,
            'work_performed': self.work_performed,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'performance_improvement': self.performance_improvement,
            'parts_used': self.parts_used,
            'cost': self.cost,
            'effectiveness_score': self.effectiveness_score,
            'next_maintenance_due': self.next_maintenance_due,
            'error_message': self.error_message
        }


@dataclass
class MaintenanceActionMetadata:
    """
    Simple metadata for maintenance actions
    """
    
    action_type: MaintenanceActionType          # Type of action
    display_name: str                          # Human-readable name
    description: str                           # Detailed description
    category: str                              # Action category
    typical_duration_hours: float              # Typical duration
    equipment_shutdown_required: bool          # Must equipment be shut down
    typical_frequency_hours: Optional[float] = None  # How often performed
    applicable_component_types: List[str] = field(default_factory=list)  # Component types


class MaintenanceActionCatalog:
    """
    Catalog of maintenance actions with basic metadata
    """
    
    def __init__(self):
        self.actions: Dict[MaintenanceActionType, MaintenanceActionMetadata] = {}
        self._initialize_catalog()
    
    def _initialize_catalog(self):
        """Initialize the maintenance action catalog with standard actions"""
        
        # Oil Change
        self.actions[MaintenanceActionType.OIL_CHANGE] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.OIL_CHANGE,
            display_name="Oil Change",
            description="Complete replacement of lubrication oil",
            category="Lubrication",
            typical_duration_hours=2.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["pump", "turbine", "compressor"]
        )
        
        # Oil Top-off
        self.actions[MaintenanceActionType.OIL_TOP_OFF] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.OIL_TOP_OFF,
            display_name="Oil Top-off",
            description="Add oil to restore proper level",
            category="Lubrication",
            typical_duration_hours=0.5,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "turbine", "compressor"]
        )
        
        # Impeller Inspection
        self.actions[MaintenanceActionType.IMPELLER_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.IMPELLER_INSPECTION,
            display_name="Impeller Inspection",
            description="Visual and dimensional inspection of pump impeller",
            category="Mechanical",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["pump"]
        )
        
        # Impeller Replacement
        self.actions[MaintenanceActionType.IMPELLER_REPLACEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.IMPELLER_REPLACEMENT,
            display_name="Impeller Replacement",
            description="Replace worn or damaged pump impeller",
            category="Mechanical",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["pump"]
        )
        
        # Bearing Replacement
        self.actions[MaintenanceActionType.BEARING_REPLACEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.BEARING_REPLACEMENT,
            display_name="Bearing Replacement",
            description="Replace worn or damaged bearings",
            category="Mechanical",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["pump", "motor", "turbine"]
        )
        
        # Seal Replacement
        self.actions[MaintenanceActionType.SEAL_REPLACEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.SEAL_REPLACEMENT,
            display_name="Seal Replacement",
            description="Replace mechanical seals",
            category="Mechanical",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["pump"]
        )
        
        # Vibration Analysis
        self.actions[MaintenanceActionType.VIBRATION_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VIBRATION_ANALYSIS,
            display_name="Vibration Analysis",
            description="Comprehensive vibration monitoring and analysis",
            category="Condition Monitoring",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "motor", "turbine", "compressor"]
        )
        
        # Component Overhaul
        self.actions[MaintenanceActionType.COMPONENT_OVERHAUL] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.COMPONENT_OVERHAUL,
            display_name="Component Overhaul",
            description="Complete overhaul of component",
            category="Major Maintenance",
            typical_duration_hours=24.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=35040.0,  # Every 4 years
            applicable_component_types=["pump", "turbine", "compressor", "motor"]
        )
        
        # Routine Maintenance
        self.actions[MaintenanceActionType.ROUTINE_MAINTENANCE] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.ROUTINE_MAINTENANCE,
            display_name="Routine Maintenance",
            description="Standard routine maintenance activities",
            category="Preventive",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["pump", "turbine", "compressor", "motor", "valve"]
        )
    
    def get_action_metadata(self, action_type: MaintenanceActionType) -> Optional[MaintenanceActionMetadata]:
        """Get metadata for a specific action type"""
        return self.actions.get(action_type)
    
    def get_actions_by_category(self, category: str) -> List[MaintenanceActionMetadata]:
        """Get all actions in a specific category"""
        return [action for action in self.actions.values() if action.category == category]
    
    def get_actions_for_component_type(self, component_type: str) -> List[MaintenanceActionMetadata]:
        """Get all applicable actions for a component type"""
        return [action for action in self.actions.values() 
                if component_type in action.applicable_component_types]
    
    def get_all_categories(self) -> List[str]:
        """Get all action categories"""
        return list(set(action.category for action in self.actions.values()))
    
    def estimate_duration(self, action_type: MaintenanceActionType) -> float:
        """Get estimated duration for an action"""
        metadata = self.get_action_metadata(action_type)
        return metadata.typical_duration_hours if metadata else 1.0
    
    def requires_shutdown(self, action_type: MaintenanceActionType) -> bool:
        """Check if action requires equipment shutdown"""
        metadata = self.get_action_metadata(action_type)
        return metadata.equipment_shutdown_required if metadata else True


# Global catalog instance
MAINTENANCE_CATALOG = MaintenanceActionCatalog()


def get_maintenance_catalog() -> MaintenanceActionCatalog:
    """Get the global maintenance action catalog"""
    return MAINTENANCE_CATALOG


def create_maintenance_result(success: bool, duration: float, work_description: str,
                            findings: str = None, **kwargs) -> MaintenanceResult:
    """
    Convenience function to create a maintenance result
    
    Args:
        success: Whether the maintenance was successful
        duration: Duration in hours
        work_description: Description of work performed
        findings: Optional findings
        **kwargs: Additional result parameters
        
    Returns:
        MaintenanceResult instance
    """
    return MaintenanceResult(
        success=success,
        duration_hours=duration,
        work_performed=work_description,
        findings=findings,
        **kwargs
    )
