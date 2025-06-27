"""
Validation results and scenario profile definitions.

This module defines the data structures used for validation results
and scenario profile configurations.
"""

import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum


class ScenarioType(Enum):
    """Types of maintenance scenarios"""
    DEMO_FAST = "demo_fast"
    TRAINING_REALISTIC = "training_realistic"
    VALIDATION_THOROUGH = "validation_thorough"
    CUSTOM = "custom"


@dataclass
class ScenarioProfile:
    """Configuration profile for different scenario types"""
    name: str
    description: str
    target_duration_hours: float
    expected_trigger_time_hours: float  # When we expect maintenance to trigger
    max_execution_time_seconds: float  # Max execution time
    scenario_type: ScenarioType = ScenarioType.CUSTOM
    
    def __post_init__(self):
        """Validate profile parameters"""
        if self.expected_trigger_time_hours >= self.target_duration_hours:
            raise ValueError("Expected trigger time must be less than duration")
        if self.max_execution_time_seconds <= 0:
            raise ValueError("Max execution time must be positive")


@dataclass
class ValidationResult:
    """Results from a single validation test"""
    # Test identification
    action: str
    subsystem: str
    scenario_profile: str
    simulation_duration_hours: float
    
    # Core results
    success: bool
    work_orders_created: int
    maintenance_events: int
    execution_time_seconds: float
    trigger_time_hours: Optional[float]  # When first maintenance was triggered
    
    # Performance metrics
    trigger_rate: float  # work_orders / hour
    timing_score: float  # how well it met timing expectations
    reliability_score: float  # consistency of triggering
    
    # Validation checks
    initial_conditions_applied: bool
    degradation_detected: bool
    threshold_crossed: bool
    maintenance_effective: bool
    
    # Issues and diagnostics
    issues: List[str]
    warnings: List[str]
    
    # Additional data
    final_power_level: float = 0.0
    work_orders_executed: int = 0
    maintenance_effectiveness: float = 0.0
    csv_export_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def is_successful(self) -> bool:
        """Check if validation was successful with no critical issues"""
        return self.success and not any("CRITICAL" in issue for issue in self.issues)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the validation result"""
        status = "✅ PASSED" if self.is_successful() else "❌ FAILED"
        trigger_info = f"triggered at {self.trigger_time_hours:.2f}h" if self.trigger_time_hours else "no trigger"
        
        summary = f"{status} {self.action} ({self.scenario_profile}): {self.work_orders_created} work orders, {trigger_info}"
        
        if self.issues:
            summary += f", {len(self.issues)} issues"
        
        return summary


# Predefined scenario profiles
DEMO_FAST = ScenarioProfile(
    name="demo_fast",
    description="15-minute demos with quick maintenance triggers",
    target_duration_hours=0.25,  # 15 minutes
    expected_trigger_time_hours=0.1,  # Expect trigger within 6 minutes
    max_execution_time_seconds=30.0,  # 30 second execution limit
    scenario_type=ScenarioType.DEMO_FAST
)

TRAINING_REALISTIC = ScenarioProfile(
    name="training_realistic",
    description="4-hour training with realistic maintenance timing",
    target_duration_hours=4.0,
    expected_trigger_time_hours=1.0,  # Expect trigger within 1 hour
    max_execution_time_seconds=120.0,  # 2 minute execution limit
    scenario_type=ScenarioType.TRAINING_REALISTIC
)

VALIDATION_THOROUGH = ScenarioProfile(
    name="validation_thorough",
    description="24-hour validation with comprehensive testing",
    target_duration_hours=24.0,
    expected_trigger_time_hours=4.0,  # Expect trigger within 4 hours
    max_execution_time_seconds=300.0,  # 5 minute execution limit
    scenario_type=ScenarioType.VALIDATION_THOROUGH
)

# Profile registry
SCENARIO_PROFILES = {
    "demo_fast": DEMO_FAST,
    "training_realistic": TRAINING_REALISTIC,
    "validation_thorough": VALIDATION_THOROUGH
}


def get_scenario_profile(name: str) -> ScenarioProfile:
    """Get a predefined scenario profile by name"""
    if name not in SCENARIO_PROFILES:
        raise ValueError(f"Unknown scenario profile: {name}. Available: {list(SCENARIO_PROFILES.keys())}")
    return SCENARIO_PROFILES[name]


def create_custom_profile(name: str, duration_hours: float, expected_trigger_hours: float,
                         max_execution_seconds: float = 120.0, description: str = None) -> ScenarioProfile:
    """Create a custom scenario profile"""
    if description is None:
        description = f"Custom {duration_hours}h scenario expecting trigger within {expected_trigger_hours}h"
    
    return ScenarioProfile(
        name=name,
        description=description,
        target_duration_hours=duration_hours,
        expected_trigger_time_hours=expected_trigger_hours,
        max_execution_time_seconds=max_execution_seconds,
        scenario_type=ScenarioType.CUSTOM
    )


class ValidationResultsCollection:
    """Collection of validation results with analysis capabilities"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.created_time = time.time()
    
    def add_result(self, result: ValidationResult):
        """Add a validation result to the collection"""
        self.results.append(result)
    
    def get_results_by_action(self, action: str) -> List[ValidationResult]:
        """Get all results for a specific action"""
        return [r for r in self.results if r.action == action]
    
    def get_results_by_profile(self, profile: str) -> List[ValidationResult]:
        """Get all results for a specific scenario profile"""
        return [r for r in self.results if r.scenario_profile == profile]
    
    def get_success_rate(self) -> float:
        """Get overall success rate"""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.is_successful()) / len(self.results)
    
    def get_trigger_rate(self) -> float:
        """Get overall trigger rate (scenarios that triggered maintenance)"""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.work_orders_created > 0) / len(self.results)
    
    def get_average_trigger_time(self) -> Optional[float]:
        """Get average trigger time for successful scenarios"""
        trigger_times = [r.trigger_time_hours for r in self.results 
                        if r.trigger_time_hours is not None]
        if not trigger_times:
            return None
        return sum(trigger_times) / len(trigger_times)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the collection"""
        return {
            'total_results': len(self.results),
            'success_rate': self.get_success_rate(),
            'trigger_rate': self.get_trigger_rate(),
            'average_trigger_time_hours': self.get_average_trigger_time(),
            'total_work_orders': sum(r.work_orders_created for r in self.results),
            'total_execution_time': sum(r.execution_time_seconds for r in self.results),
            'actions_tested': len(set(r.action for r in self.results)),
            'profiles_tested': len(set(r.scenario_profile for r in self.results))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary for JSON serialization"""
        return {
            'created_time': self.created_time,
            'summary_stats': self.get_summary_stats(),
            'results': [r.to_dict() for r in self.results]
        }
