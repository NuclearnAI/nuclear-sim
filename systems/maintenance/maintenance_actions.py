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
    
    # === STEAM GENERATOR SPECIFIC ACTIONS ===
    TSP_CHEMICAL_CLEANING = "tsp_chemical_cleaning"     # TSP fouling chemical cleaning
    TSP_MECHANICAL_CLEANING = "tsp_mechanical_cleaning" # TSP fouling mechanical cleaning
    TUBE_BUNDLE_INSPECTION = "tube_bundle_inspection"   # Comprehensive tube bundle inspection
    EDDY_CURRENT_TESTING = "eddy_current_testing"       # Eddy current tube testing
    MOISTURE_SEPARATOR_MAINTENANCE = "moisture_separator_maintenance"  # Steam quality maintenance
    STEAM_DRYER_CLEANING = "steam_dryer_cleaning"       # Steam dryer maintenance
    WATER_CHEMISTRY_ADJUSTMENT = "water_chemistry_adjustment"  # Chemistry control
    SCALE_REMOVAL = "scale_removal"                     # Remove mineral scale
    TUBE_SHEET_INSPECTION = "tube_sheet_inspection"     # Inspect tube sheet
    SECONDARY_SIDE_CLEANING = "secondary_side_cleaning" # Clean secondary side
    
    # === TURBINE BEARING ACTIONS ===
    TURBINE_BEARING_INSPECTION = "turbine_bearing_inspection"       # Inspect turbine bearing condition
    TURBINE_BEARING_REPLACEMENT = "turbine_bearing_replacement"     # Replace worn turbine bearing
    BEARING_CLEARANCE_CHECK = "bearing_clearance_check"  # Check bearing clearances
    BEARING_ALIGNMENT = "bearing_alignment"         # Align bearing assembly
    THRUST_BEARING_ADJUSTMENT = "thrust_bearing_adjustment"  # Adjust thrust bearing
    
    # === TURBINE LUBRICATION ACTIONS ===
    TURBINE_OIL_CHANGE = "turbine_oil_change"       # Change turbine bearing oil
    TURBINE_OIL_TOP_OFF = "turbine_oil_top_off"     # Top off turbine oil
    OIL_FILTER_REPLACEMENT = "oil_filter_replacement"  # Replace oil filters
    OIL_COOLER_CLEANING = "oil_cooler_cleaning"     # Clean oil coolers
    LUBRICATION_SYSTEM_TEST = "lubrication_system_test"  # Test lubrication system
    
    # === TURBINE ROTOR ACTIONS ===
    ROTOR_INSPECTION = "rotor_inspection"           # Inspect rotor condition
    THERMAL_BOW_CORRECTION = "thermal_bow_correction"  # Correct thermal bow
    CRITICAL_SPEED_TEST = "critical_speed_test"     # Test critical speeds
    OVERSPEED_TEST = "overspeed_test"               # Test overspeed protection
    
    # === TURBINE VIBRATION ACTIONS ===
    VIBRATION_MONITORING_CALIBRATION = "vibration_monitoring_calibration"  # Calibrate vibration sensors
    DYNAMIC_BALANCING = "dynamic_balancing"         # Dynamic balancing at speed
    
    # === TURBINE SYSTEM ACTIONS ===
    TURBINE_PERFORMANCE_TEST = "turbine_performance_test"  # Performance testing
    TURBINE_PROTECTION_TEST = "turbine_protection_test"    # Test protection systems
    THERMAL_STRESS_ANALYSIS = "thermal_stress_analysis"    # Analyze thermal stress
    TURBINE_SYSTEM_OPTIMIZATION = "turbine_system_optimization"  # Optimize system performance
    
    # === CONDENSER SPECIFIC ACTIONS ===
    CONDENSER_TUBE_CLEANING = "condenser_tube_cleaning"           # Clean condenser tubes
    CONDENSER_TUBE_PLUGGING = "condenser_tube_plugging"           # Plug failed condenser tubes
    CONDENSER_TUBE_INSPECTION = "condenser_tube_inspection"       # Inspect condenser tubes
    CONDENSER_BIOFOULING_REMOVAL = "condenser_biofouling_removal" # Remove biological fouling
    CONDENSER_SCALE_REMOVAL = "condenser_scale_removal"           # Remove mineral scale
    CONDENSER_CHEMICAL_CLEANING = "condenser_chemical_cleaning"   # Chemical cleaning of condenser
    CONDENSER_MECHANICAL_CLEANING = "condenser_mechanical_cleaning" # Mechanical cleaning
    CONDENSER_HYDROBLAST_CLEANING = "condenser_hydroblast_cleaning" # High-pressure water cleaning
    CONDENSER_WATER_TREATMENT = "condenser_water_treatment"       # Cooling water treatment
    CONDENSER_PERFORMANCE_TEST = "condenser_performance_test"     # Performance testing
    
    # === VACUUM SYSTEM ACTIONS ===
    VACUUM_EJECTOR_CLEANING = "vacuum_ejector_cleaning"           # Clean steam ejector
    VACUUM_EJECTOR_NOZZLE_REPLACEMENT = "vacuum_ejector_nozzle_replacement" # Replace ejector nozzle
    VACUUM_EJECTOR_INSPECTION = "vacuum_ejector_inspection"       # Inspect ejector condition
    VACUUM_SYSTEM_TEST = "vacuum_system_test"                     # Test vacuum system performance
    VACUUM_LEAK_DETECTION = "vacuum_leak_detection"               # Detect and repair air leaks
    INTERCONDENSER_CLEANING = "intercondenser_cleaning"           # Clean inter-condenser
    AFTERCONDENSER_CLEANING = "aftercondenser_cleaning"           # Clean after-condenser
    MOTIVE_STEAM_SYSTEM_CHECK = "motive_steam_system_check"       # Check motive steam supply
    
    # === GENERIC ACTIONS ===
    COMPONENT_REPLACEMENT = "component_replacement"  # Replace entire component
    COMPONENT_OVERHAUL = "component_overhaul"        # Complete component overhaul
    ADJUSTMENT = "adjustment"                        # Adjust component settings
    REPAIR = "repair"                               # General repair work
    ROUTINE_MAINTENANCE = "routine_maintenance"     # Routine preventive maintenance
    
    # === MISSING ACTIONS FROM TEMPLATES ===
    LEVEL_CONTROL_CHECK = "level_control_check"     # Check level control systems
    COOLING_WATER_CHECK = "cooling_water_check"     # Check cooling water systems
    EFFICIENCY_ANALYSIS = "efficiency_analysis"     # Analyze component efficiency
    BLADE_INSPECTION = "blade_inspection"           # Inspect turbine blades
    BLADE_REPLACEMENT = "blade_replacement"         # Replace turbine blades
    VACUUM_SYSTEM_CHECK = "vacuum_system_check"     # Check vacuum system
    GOVERNOR_SYSTEM_CHECK = "governor_system_check" # Check turbine governor system
    
    # === POST-TRIP INVESTIGATION ACTIONS ===
    PUMP_INSPECTION = "pump_inspection"             # Comprehensive pump inspection
    NPSH_ANALYSIS = "npsh_analysis"                 # NPSH analysis and improvement
    SUCTION_SYSTEM_CHECK = "suction_system_check"   # Check pump suction system
    DISCHARGE_SYSTEM_INSPECTION = "discharge_system_inspection"  # Inspect discharge system
    FLOW_SYSTEM_INSPECTION = "flow_system_inspection"  # Inspect flow control system
    FLOW_CONTROL_INSPECTION = "flow_control_inspection"  # Inspect flow control valves
    PUMP_ALIGNMENT_CHECK = "pump_alignment_check"   # Check pump alignment
    LUBRICATION_SYSTEM_CHECK = "lubrication_system_check"  # Check lubrication system
    COOLING_SYSTEM_CHECK = "cooling_system_check"   # Check cooling system
    COMPREHENSIVE_SYSTEM_INSPECTION = "comprehensive_system_inspection"  # Full system inspection
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"     # Root cause analysis
    CAVITATION_ANALYSIS = "cavitation_analysis"     # Cavitation analysis
    NPSH_IMPROVEMENT = "npsh_improvement"           # NPSH improvement actions
    WEAR_ANALYSIS = "wear_analysis"                 # Wear analysis
    COMPONENT_REPLACEMENT_EVALUATION = "component_replacement_evaluation"  # Evaluate replacement needs
    POST_TRIP_INSPECTION = "post_trip_inspection"   # General post-trip inspection
    TRIP_ROOT_CAUSE_ANALYSIS = "trip_root_cause_analysis"  # Trip-specific root cause analysis
    PROTECTION_SYSTEM_TEST = "protection_system_test"  # Test protection systems
    PROTECTION_SYSTEM_CALIBRATION = "protection_system_calibration"  # Calibrate protection systems


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
        
        # Motor Inspection
        self.actions[MaintenanceActionType.MOTOR_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.MOTOR_INSPECTION,
            display_name="Motor Inspection",
            description="Inspect electric motor condition and performance",
            category="Electrical",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["motor", "pump"]
        )
        
        # Bearing Inspection
        self.actions[MaintenanceActionType.BEARING_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.BEARING_INSPECTION,
            display_name="Bearing Inspection",
            description="Inspect bearing condition and clearances",
            category="Mechanical",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,  # Can be done online with vibration/temperature monitoring
            typical_frequency_hours=4380.0,  # Semi-annual
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
        
        # === STEAM GENERATOR SPECIFIC ACTIONS ===
        
        # TSP Chemical Cleaning
        self.actions[MaintenanceActionType.TSP_CHEMICAL_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TSP_CHEMICAL_CLEANING,
            display_name="TSP Chemical Cleaning",
            description="Chemical cleaning to remove tube support plate fouling",
            category="Steam Generator",
            typical_duration_hours=12.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual or as needed
            applicable_component_types=["steam_generator"]
        )
        
        # TSP Mechanical Cleaning
        self.actions[MaintenanceActionType.TSP_MECHANICAL_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TSP_MECHANICAL_CLEANING,
            display_name="TSP Mechanical Cleaning",
            description="Mechanical cleaning to remove tube support plate fouling",
            category="Steam Generator",
            typical_duration_hours=16.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["steam_generator"]
        )
        
        # Tube Bundle Inspection
        self.actions[MaintenanceActionType.TUBE_BUNDLE_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TUBE_BUNDLE_INSPECTION,
            display_name="Tube Bundle Inspection",
            description="Comprehensive inspection of steam generator tube bundle",
            category="Steam Generator",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["steam_generator"]
        )
        
        # Eddy Current Testing
        self.actions[MaintenanceActionType.EDDY_CURRENT_TESTING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.EDDY_CURRENT_TESTING,
            display_name="Eddy Current Testing",
            description="Non-destructive testing of steam generator tubes",
            category="Steam Generator",
            typical_duration_hours=24.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["steam_generator"]
        )
        
        # Moisture Separator Maintenance
        self.actions[MaintenanceActionType.MOISTURE_SEPARATOR_MAINTENANCE] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.MOISTURE_SEPARATOR_MAINTENANCE,
            display_name="Moisture Separator Maintenance",
            description="Maintenance of steam moisture separation equipment",
            category="Steam Generator",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["steam_generator"]
        )
        
        # Steam Dryer Cleaning
        self.actions[MaintenanceActionType.STEAM_DRYER_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.STEAM_DRYER_CLEANING,
            display_name="Steam Dryer Cleaning",
            description="Cleaning of steam dryer components",
            category="Steam Generator",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["steam_generator"]
        )
        
        # Water Chemistry Adjustment
        self.actions[MaintenanceActionType.WATER_CHEMISTRY_ADJUSTMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.WATER_CHEMISTRY_ADJUSTMENT,
            display_name="Water Chemistry Adjustment",
            description="Adjust water chemistry parameters for optimal performance",
            category="Steam Generator",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=720.0,  # Monthly
            applicable_component_types=["steam_generator"]
        )
        
        # Scale Removal
        self.actions[MaintenanceActionType.SCALE_REMOVAL] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.SCALE_REMOVAL,
            display_name="Scale Removal",
            description="Remove mineral scale deposits from steam generator",
            category="Steam Generator",
            typical_duration_hours=10.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["steam_generator"]
        )
        
        # Tube Sheet Inspection
        self.actions[MaintenanceActionType.TUBE_SHEET_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TUBE_SHEET_INSPECTION,
            display_name="Tube Sheet Inspection",
            description="Inspection of steam generator tube sheet",
            category="Steam Generator",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["steam_generator"]
        )
        
        # Secondary Side Cleaning
        self.actions[MaintenanceActionType.SECONDARY_SIDE_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.SECONDARY_SIDE_CLEANING,
            display_name="Secondary Side Cleaning",
            description="General cleaning of steam generator secondary side",
            category="Steam Generator",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["steam_generator"]
        )
        
        # === TURBINE BEARING ACTIONS ===
        
        # Turbine Bearing Inspection
        self.actions[MaintenanceActionType.TURBINE_BEARING_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_BEARING_INSPECTION,
            display_name="Turbine Bearing Inspection",
            description="Inspect turbine bearing condition and clearances",
            category="Turbine Bearing",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["turbine_bearing"]
        )
        
        # Turbine Bearing Replacement
        self.actions[MaintenanceActionType.TURBINE_BEARING_REPLACEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_BEARING_REPLACEMENT,
            display_name="Turbine Bearing Replacement",
            description="Replace worn or damaged turbine bearing",
            category="Turbine Bearing",
            typical_duration_hours=12.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=35040.0,  # Every 4 years
            applicable_component_types=["turbine_bearing"]
        )
        
        # Bearing Clearance Check
        self.actions[MaintenanceActionType.BEARING_CLEARANCE_CHECK] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.BEARING_CLEARANCE_CHECK,
            display_name="Bearing Clearance Check",
            description="Check and measure bearing clearances",
            category="Turbine Bearing",
            typical_duration_hours=3.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_bearing"]
        )
        
        # Bearing Alignment
        self.actions[MaintenanceActionType.BEARING_ALIGNMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.BEARING_ALIGNMENT,
            display_name="Bearing Alignment",
            description="Align bearing assembly and check concentricity",
            category="Turbine Bearing",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["turbine_bearing"]
        )
        
        # Thrust Bearing Adjustment
        self.actions[MaintenanceActionType.THRUST_BEARING_ADJUSTMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.THRUST_BEARING_ADJUSTMENT,
            display_name="Thrust Bearing Adjustment",
            description="Adjust thrust bearing position and clearances",
            category="Turbine Bearing",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_bearing"]
        )
        
        # === TURBINE LUBRICATION ACTIONS ===
        
        # Turbine Oil Change
        self.actions[MaintenanceActionType.TURBINE_OIL_CHANGE] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_OIL_CHANGE,
            display_name="Turbine Oil Change",
            description="Complete replacement of turbine bearing oil",
            category="Turbine Lubrication",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_lubrication"]
        )
        
        # Turbine Oil Top-off
        self.actions[MaintenanceActionType.TURBINE_OIL_TOP_OFF] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_OIL_TOP_OFF,
            display_name="Turbine Oil Top-off",
            description="Add oil to restore proper turbine oil level",
            category="Turbine Lubrication",
            typical_duration_hours=1.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=720.0,  # Monthly
            applicable_component_types=["turbine_lubrication"]
        )
        
        # Oil Filter Replacement
        self.actions[MaintenanceActionType.OIL_FILTER_REPLACEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.OIL_FILTER_REPLACEMENT,
            display_name="Oil Filter Replacement",
            description="Replace turbine oil filtration elements",
            category="Turbine Lubrication",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["turbine_lubrication"]
        )
        
        # Oil Cooler Cleaning
        self.actions[MaintenanceActionType.OIL_COOLER_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.OIL_COOLER_CLEANING,
            display_name="Oil Cooler Cleaning",
            description="Clean turbine oil cooling system",
            category="Turbine Lubrication",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["turbine_lubrication"]
        )
        
        # Lubrication System Test
        self.actions[MaintenanceActionType.LUBRICATION_SYSTEM_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.LUBRICATION_SYSTEM_TEST,
            display_name="Lubrication System Test",
            description="Test turbine lubrication system performance",
            category="Turbine Lubrication",
            typical_duration_hours=3.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["turbine_lubrication"]
        )
        
        # === TURBINE ROTOR ACTIONS ===
        
        # Rotor Inspection
        self.actions[MaintenanceActionType.ROTOR_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.ROTOR_INSPECTION,
            display_name="Rotor Inspection",
            description="Comprehensive inspection of turbine rotor",
            category="Turbine Rotor",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_rotor"]
        )
        
        # Thermal Bow Correction
        self.actions[MaintenanceActionType.THERMAL_BOW_CORRECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.THERMAL_BOW_CORRECTION,
            display_name="Thermal Bow Correction",
            description="Correct thermal bow in turbine rotor",
            category="Turbine Rotor",
            typical_duration_hours=12.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["turbine_rotor"]
        )
        
        # Critical Speed Test
        self.actions[MaintenanceActionType.CRITICAL_SPEED_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CRITICAL_SPEED_TEST,
            display_name="Critical Speed Test",
            description="Test turbine critical speed characteristics",
            category="Turbine Rotor",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_rotor"]
        )
        
        # Overspeed Test
        self.actions[MaintenanceActionType.OVERSPEED_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.OVERSPEED_TEST,
            display_name="Overspeed Test",
            description="Test turbine overspeed protection system",
            category="Turbine Rotor",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["turbine_rotor"]
        )
        
        # === TURBINE VIBRATION ACTIONS ===
        
        # Vibration Monitoring Calibration
        self.actions[MaintenanceActionType.VIBRATION_MONITORING_CALIBRATION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VIBRATION_MONITORING_CALIBRATION,
            display_name="Vibration Monitoring Calibration",
            description="Calibrate turbine vibration monitoring sensors",
            category="Turbine Vibration",
            typical_duration_hours=3.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["turbine_vibration"]
        )
        
        # Dynamic Balancing
        self.actions[MaintenanceActionType.DYNAMIC_BALANCING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.DYNAMIC_BALANCING,
            display_name="Dynamic Balancing",
            description="Perform dynamic balancing of turbine rotor at speed",
            category="Turbine Vibration",
            typical_duration_hours=16.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["turbine_vibration"]
        )
        
        # === TURBINE SYSTEM ACTIONS ===
        
        # Turbine Performance Test
        self.actions[MaintenanceActionType.TURBINE_PERFORMANCE_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_PERFORMANCE_TEST,
            display_name="Turbine Performance Test",
            description="Comprehensive turbine performance testing",
            category="Turbine System",
            typical_duration_hours=8.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["turbine_system"]
        )
        
        # Turbine Protection Test
        self.actions[MaintenanceActionType.TURBINE_PROTECTION_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_PROTECTION_TEST,
            display_name="Turbine Protection Test",
            description="Test turbine protection systems and trip logic",
            category="Turbine System",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["turbine_system"]
        )
        
        # Thermal Stress Analysis
        self.actions[MaintenanceActionType.THERMAL_STRESS_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.THERMAL_STRESS_ANALYSIS,
            display_name="Thermal Stress Analysis",
            description="Analyze thermal stress in turbine components",
            category="Turbine System",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_system"]
        )
        
        # Turbine System Optimization
        self.actions[MaintenanceActionType.TURBINE_SYSTEM_OPTIMIZATION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TURBINE_SYSTEM_OPTIMIZATION,
            display_name="Turbine System Optimization",
            description="Optimize turbine system performance and efficiency",
            category="Turbine System",
            typical_duration_hours=12.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["turbine_system"]
        )
        
        # === CONDENSER SPECIFIC ACTIONS ===
        
        # Condenser Tube Cleaning
        self.actions[MaintenanceActionType.CONDENSER_TUBE_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_TUBE_CLEANING,
            display_name="Condenser Tube Cleaning",
            description="Clean condenser tubes to remove fouling and restore heat transfer",
            category="Condenser",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["condenser"]
        )
        
        # Condenser Tube Plugging
        self.actions[MaintenanceActionType.CONDENSER_TUBE_PLUGGING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_TUBE_PLUGGING,
            display_name="Condenser Tube Plugging",
            description="Plug failed or leaking condenser tubes",
            category="Condenser",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # As needed
            applicable_component_types=["condenser"]
        )
        
        # Condenser Tube Inspection
        self.actions[MaintenanceActionType.CONDENSER_TUBE_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_TUBE_INSPECTION,
            display_name="Condenser Tube Inspection",
            description="Inspect condenser tubes for damage, wear, and fouling",
            category="Condenser",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["condenser"]
        )
        
        # Condenser Biofouling Removal
        self.actions[MaintenanceActionType.CONDENSER_BIOFOULING_REMOVAL] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_BIOFOULING_REMOVAL,
            display_name="Condenser Biofouling Removal",
            description="Remove biological fouling from condenser tubes",
            category="Condenser",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["condenser"]
        )
        
        # Condenser Scale Removal
        self.actions[MaintenanceActionType.CONDENSER_SCALE_REMOVAL] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_SCALE_REMOVAL,
            display_name="Condenser Scale Removal",
            description="Remove mineral scale deposits from condenser tubes",
            category="Condenser",
            typical_duration_hours=10.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["condenser"]
        )
        
        # Condenser Chemical Cleaning
        self.actions[MaintenanceActionType.CONDENSER_CHEMICAL_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_CHEMICAL_CLEANING,
            display_name="Condenser Chemical Cleaning",
            description="Chemical cleaning of condenser tubes and surfaces",
            category="Condenser",
            typical_duration_hours=12.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["condenser"]
        )
        
        # Condenser Mechanical Cleaning
        self.actions[MaintenanceActionType.CONDENSER_MECHANICAL_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_MECHANICAL_CLEANING,
            display_name="Condenser Mechanical Cleaning",
            description="Mechanical cleaning of condenser tubes using brushes or scrapers",
            category="Condenser",
            typical_duration_hours=16.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["condenser"]
        )
        
        # Condenser Hydroblast Cleaning
        self.actions[MaintenanceActionType.CONDENSER_HYDROBLAST_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_HYDROBLAST_CLEANING,
            display_name="Condenser Hydroblast Cleaning",
            description="High-pressure water cleaning of condenser tubes",
            category="Condenser",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["condenser"]
        )
        
        # Condenser Water Treatment
        self.actions[MaintenanceActionType.CONDENSER_WATER_TREATMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_WATER_TREATMENT,
            display_name="Condenser Water Treatment",
            description="Optimize cooling water chemistry and treatment",
            category="Condenser",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=720.0,  # Monthly
            applicable_component_types=["condenser"]
        )
        
        # Condenser Performance Test
        self.actions[MaintenanceActionType.CONDENSER_PERFORMANCE_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CONDENSER_PERFORMANCE_TEST,
            display_name="Condenser Performance Test",
            description="Test condenser heat transfer performance and efficiency",
            category="Condenser",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["condenser"]
        )
        
        # === VACUUM SYSTEM ACTIONS ===
        
        # Vacuum Ejector Cleaning
        self.actions[MaintenanceActionType.VACUUM_EJECTOR_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VACUUM_EJECTOR_CLEANING,
            display_name="Vacuum Ejector Cleaning",
            description="Clean steam ejector nozzles and diffusers",
            category="Vacuum System",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["vacuum_ejector"]
        )
        
        # Vacuum Ejector Nozzle Replacement
        self.actions[MaintenanceActionType.VACUUM_EJECTOR_NOZZLE_REPLACEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VACUUM_EJECTOR_NOZZLE_REPLACEMENT,
            display_name="Vacuum Ejector Nozzle Replacement",
            description="Replace worn or eroded ejector nozzles",
            category="Vacuum System",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=17520.0,  # Every 2 years
            applicable_component_types=["vacuum_ejector"]
        )
        
        # Vacuum Ejector Inspection
        self.actions[MaintenanceActionType.VACUUM_EJECTOR_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VACUUM_EJECTOR_INSPECTION,
            display_name="Vacuum Ejector Inspection",
            description="Inspect ejector condition and performance",
            category="Vacuum System",
            typical_duration_hours=3.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=8760.0,  # Annual
            applicable_component_types=["vacuum_ejector"]
        )
        
        # Vacuum System Test
        self.actions[MaintenanceActionType.VACUUM_SYSTEM_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VACUUM_SYSTEM_TEST,
            display_name="Vacuum System Test",
            description="Test vacuum system performance and control logic",
            category="Vacuum System",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["vacuum_system"]
        )
        
        # Vacuum Leak Detection
        self.actions[MaintenanceActionType.VACUUM_LEAK_DETECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.VACUUM_LEAK_DETECTION,
            display_name="Vacuum Leak Detection",
            description="Detect and repair air leaks in vacuum system",
            category="Vacuum System",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["vacuum_system"]
        )
        
        # Intercondenser Cleaning
        self.actions[MaintenanceActionType.INTERCONDENSER_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.INTERCONDENSER_CLEANING,
            display_name="Intercondenser Cleaning",
            description="Clean ejector inter-condenser heat exchanger",
            category="Vacuum System",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["vacuum_ejector"]
        )
        
        # Aftercondenser Cleaning
        self.actions[MaintenanceActionType.AFTERCONDENSER_CLEANING] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.AFTERCONDENSER_CLEANING,
            display_name="Aftercondenser Cleaning",
            description="Clean ejector after-condenser heat exchanger",
            category="Vacuum System",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            typical_frequency_hours=4380.0,  # Semi-annual
            applicable_component_types=["vacuum_ejector"]
        )
        
        # Motive Steam System Check
        self.actions[MaintenanceActionType.MOTIVE_STEAM_SYSTEM_CHECK] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.MOTIVE_STEAM_SYSTEM_CHECK,
            display_name="Motive Steam System Check",
            description="Check motive steam supply pressure and quality",
            category="Vacuum System",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            typical_frequency_hours=2190.0,  # Quarterly
            applicable_component_types=["vacuum_system"]
        )
        
        # === POST-TRIP INVESTIGATION ACTIONS ===
        
        # Pump Inspection
        self.actions[MaintenanceActionType.PUMP_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.PUMP_INSPECTION,
            display_name="Pump Inspection",
            description="Comprehensive pump inspection following protection trip",
            category="Post-Trip Investigation",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "feedwater_system"]
        )
        
        # NPSH Analysis
        self.actions[MaintenanceActionType.NPSH_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.NPSH_ANALYSIS,
            display_name="NPSH Analysis",
            description="Analyze NPSH conditions and identify improvement opportunities",
            category="Post-Trip Investigation",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "feedwater_system"]
        )
        
        # Suction System Check
        self.actions[MaintenanceActionType.SUCTION_SYSTEM_CHECK] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.SUCTION_SYSTEM_CHECK,
            display_name="Suction System Check",
            description="Check pump suction system for restrictions and leaks",
            category="Post-Trip Investigation",
            typical_duration_hours=3.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "feedwater_system"]
        )
        
        # Discharge System Inspection
        self.actions[MaintenanceActionType.DISCHARGE_SYSTEM_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.DISCHARGE_SYSTEM_INSPECTION,
            display_name="Discharge System Inspection",
            description="Inspect pump discharge system and pressure relief components",
            category="Post-Trip Investigation",
            typical_duration_hours=3.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "feedwater_system"]
        )
        
        # Flow System Inspection
        self.actions[MaintenanceActionType.FLOW_SYSTEM_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.FLOW_SYSTEM_INSPECTION,
            display_name="Flow System Inspection",
            description="Inspect flow measurement and control systems",
            category="Post-Trip Investigation",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "feedwater_system"]
        )
        
        # Flow Control Inspection
        self.actions[MaintenanceActionType.FLOW_CONTROL_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.FLOW_CONTROL_INSPECTION,
            display_name="Flow Control Inspection",
            description="Inspect flow control valves and actuators",
            category="Post-Trip Investigation",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            applicable_component_types=["valve", "feedwater_system"]
        )
        
        # Pump Alignment Check
        self.actions[MaintenanceActionType.PUMP_ALIGNMENT_CHECK] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.PUMP_ALIGNMENT_CHECK,
            display_name="Pump Alignment Check",
            description="Check pump and motor alignment following vibration trip",
            category="Post-Trip Investigation",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "motor"]
        )
        
        # Lubrication System Check
        self.actions[MaintenanceActionType.LUBRICATION_SYSTEM_CHECK] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.LUBRICATION_SYSTEM_CHECK,
            display_name="Lubrication System Check",
            description="Check lubrication system following bearing temperature trip",
            category="Post-Trip Investigation",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "turbine", "lubrication_system"]
        )
        
        # Cooling System Check
        self.actions[MaintenanceActionType.COOLING_SYSTEM_CHECK] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.COOLING_SYSTEM_CHECK,
            display_name="Cooling System Check",
            description="Check cooling system following motor temperature trip",
            category="Post-Trip Investigation",
            typical_duration_hours=2.0,
            equipment_shutdown_required=False,
            applicable_component_types=["motor", "cooling_system"]
        )
        
        # Comprehensive System Inspection
        self.actions[MaintenanceActionType.COMPREHENSIVE_SYSTEM_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.COMPREHENSIVE_SYSTEM_INSPECTION,
            display_name="Comprehensive System Inspection",
            description="Complete system inspection following critical health trip",
            category="Post-Trip Investigation",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "turbine", "feedwater_system"]
        )
        
        # Root Cause Analysis
        self.actions[MaintenanceActionType.ROOT_CAUSE_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.ROOT_CAUSE_ANALYSIS,
            display_name="Root Cause Analysis",
            description="Detailed root cause analysis of system failure",
            category="Post-Trip Investigation",
            typical_duration_hours=12.0,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "turbine", "feedwater_system", "steam_generator"]
        )
        
        # Cavitation Analysis
        self.actions[MaintenanceActionType.CAVITATION_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.CAVITATION_ANALYSIS,
            display_name="Cavitation Analysis",
            description="Analyze cavitation conditions and damage assessment",
            category="Post-Trip Investigation",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump"]
        )
        
        # NPSH Improvement
        self.actions[MaintenanceActionType.NPSH_IMPROVEMENT] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.NPSH_IMPROVEMENT,
            display_name="NPSH Improvement",
            description="Implement NPSH improvement modifications",
            category="Post-Trip Investigation",
            typical_duration_hours=8.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "feedwater_system"]
        )
        
        # Wear Analysis
        self.actions[MaintenanceActionType.WEAR_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.WEAR_ANALYSIS,
            display_name="Wear Analysis",
            description="Analyze component wear patterns and remaining life",
            category="Post-Trip Investigation",
            typical_duration_hours=6.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "turbine", "motor"]
        )
        
        # Component Replacement Evaluation
        self.actions[MaintenanceActionType.COMPONENT_REPLACEMENT_EVALUATION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.COMPONENT_REPLACEMENT_EVALUATION,
            display_name="Component Replacement Evaluation",
            description="Evaluate need for component replacement",
            category="Post-Trip Investigation",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            applicable_component_types=["pump", "turbine", "motor", "valve"]
        )
        
        # Post-Trip Inspection
        self.actions[MaintenanceActionType.POST_TRIP_INSPECTION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.POST_TRIP_INSPECTION,
            display_name="Post-Trip Inspection",
            description="General post-trip inspection and assessment",
            category="Post-Trip Investigation",
            typical_duration_hours=4.0,
            equipment_shutdown_required=True,
            applicable_component_types=["pump", "turbine", "feedwater_system", "steam_generator"]
        )
        
        # Trip Root Cause Analysis
        self.actions[MaintenanceActionType.TRIP_ROOT_CAUSE_ANALYSIS] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.TRIP_ROOT_CAUSE_ANALYSIS,
            display_name="Trip Root Cause Analysis",
            description="Analyze root cause of protection system trip",
            category="Post-Trip Investigation",
            typical_duration_hours=6.0,
            equipment_shutdown_required=False,
            applicable_component_types=["protection_system", "pump", "turbine"]
        )
        
        # Protection System Test
        self.actions[MaintenanceActionType.PROTECTION_SYSTEM_TEST] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.PROTECTION_SYSTEM_TEST,
            display_name="Protection System Test",
            description="Test protection system functionality and calibration",
            category="Post-Trip Investigation",
            typical_duration_hours=3.0,
            equipment_shutdown_required=False,
            applicable_component_types=["protection_system"]
        )
        
        # Protection System Calibration
        self.actions[MaintenanceActionType.PROTECTION_SYSTEM_CALIBRATION] = MaintenanceActionMetadata(
            action_type=MaintenanceActionType.PROTECTION_SYSTEM_CALIBRATION,
            display_name="Protection System Calibration",
            description="Calibrate protection system setpoints and logic",
            category="Post-Trip Investigation",
            typical_duration_hours=4.0,
            equipment_shutdown_required=False,
            applicable_component_types=["protection_system"]
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
