#!/usr/bin/env python
"""
Simplified Maintenance Tuning Framework

This module provides a streamlined framework for testing maintenance scenarios
using realistic thresholds and targeted initial conditions. Replaces the complex
threshold calibration system with a simpler approach based on natural degradation.

Key Features:
1. Scenario profile management (demo_fast, training_realistic, validation_thorough)
2. Initial conditions validation and optimization
3. Batch testing capabilities for multiple actions
4. Performance metrics and timing validation
5. Simple integration with realistic threshold system
"""

import sys
import time
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_gen.config_engine.composers.comprehensive_composer import ComprehensiveComposer
from data_gen.maintenance_scenario_runner import MaintenanceScenarioRunner


@dataclass
class ValidationResult:
    """Results from a single validation test"""
    action: str
    subsystem: str
    scenario_profile: str
    simulation_duration_hours: float
    
    # Results
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
    issues: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioProfile:
    """Configuration profile for different scenario types"""
    name: str
    description: str
    target_duration_hours: float
    expected_trigger_time_hours: float  # When we expect maintenance to trigger
    max_execution_time_seconds: float  # Max execution time
    
    def __post_init__(self):
        """Validate profile parameters"""
        if self.expected_trigger_time_hours >= self.target_duration_hours:
            raise ValueError("Expected trigger time must be less than duration")


class SimplifiedTuningFramework:
    """
    Simplified framework for validating maintenance scenarios with realistic thresholds
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the simplified tuning framework"""
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent / "tuning_results"
        self.output_dir.mkdir(exist_ok=True)
        
        self.composer = ComprehensiveComposer()
        self.validation_results = []
        
        # Define scenario profiles (simplified - no threshold tuning needed)
        self.scenario_profiles = {
            "demo_fast": ScenarioProfile(
                name="demo_fast",
                description="15-minute demos with quick maintenance triggers",
                target_duration_hours=0.25,  # 15 minutes
                expected_trigger_time_hours=0.1,  # Expect trigger within 6 minutes
                max_execution_time_seconds=30.0  # 30 second execution limit
            ),
            "training_realistic": ScenarioProfile(
                name="training_realistic",
                description="4-hour training with realistic maintenance timing",
                target_duration_hours=4.0,
                expected_trigger_time_hours=1.0,  # Expect trigger within 1 hour
                max_execution_time_seconds=120.0  # 2 minute execution limit
            ),
            "validation_thorough": ScenarioProfile(
                name="validation_thorough", 
                description="24-hour validation with comprehensive testing",
                target_duration_hours=24.0,
                expected_trigger_time_hours=4.0,  # Expect trigger within 4 hours
                max_execution_time_seconds=300.0  # 5 minute execution limit
            )
        }
        
        print(f"🔧 Simplified Tuning Framework Initialized")
        print(f"   Output directory: {self.output_dir}")
        print(f"   Scenario profiles: {list(self.scenario_profiles.keys())}")
        print(f"   Available actions: {len(self.composer.list_available_actions())}")
        print(f"   Approach: Realistic thresholds + targeted initial conditions + natural degradation")
    
    def validate_action(self, action: str, profile_name: str) -> ValidationResult:
        """
        Validate that a maintenance action works correctly with realistic thresholds
        
        Args:
            action: Maintenance action to validate (e.g., "oil_top_off")
            profile_name: Scenario profile to use
            
        Returns:
            Validation result
        """
        if profile_name not in self.scenario_profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        profile = self.scenario_profiles[profile_name]
        subsystem = self.composer.action_subsystem_map.get(action)
        
        if not subsystem:
            raise ValueError(f"Unknown action: {action}")
        
        print(f"\n🎯 Validating {action} for {profile_name} profile")
        print(f"   Target subsystem: {subsystem}")
        print(f"   Duration: {profile.target_duration_hours}h")
        print(f"   Expected trigger time: {profile.expected_trigger_time_hours}h")
        
        # Generate configuration using simplified composer
        config = self.composer.compose_action_test_scenario(
            target_action=action,
            duration_hours=profile.target_duration_hours
        )
        
        print(f"   ✅ Generated configuration with realistic thresholds")
        
        # Run the validation test
        start_time = time.time()
        
        try:
            # Suppress warnings during validation
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                runner = MaintenanceScenarioRunner(config, verbose=False)
                results = runner.run_scenario()
            
            execution_time = time.time() - start_time
            
            # Calculate performance metrics
            trigger_rate = results['work_orders_created'] / profile.target_duration_hours
            
            # Timing score: how well it met timing expectations
            trigger_time = None
            if hasattr(runner, 'maintenance_events') and runner.maintenance_events:
                trigger_time = runner.maintenance_events[0]['time_hours']
            
            if trigger_time and trigger_time <= profile.expected_trigger_time_hours:
                timing_score = 1.0 - (trigger_time / profile.expected_trigger_time_hours)
            else:
                timing_score = 0.0
            
            # Reliability score: basic success indicator
            reliability_score = 1.0 if results['success'] and trigger_time else 0.0
            
            # Validation checks
            initial_conditions_applied = self._check_initial_conditions_applied(config, action)
            degradation_detected = trigger_time is not None  # If maintenance triggered, degradation occurred
            threshold_crossed = results['work_orders_created'] > 0  # Work orders mean thresholds were crossed
            
            # Detect issues
            issues = []
            if execution_time > profile.max_execution_time_seconds:
                issues.append(f"Execution time ({execution_time:.1f}s) exceeded limit ({profile.max_execution_time_seconds}s)")
            if not results['success']:
                issues.append("Simulation failed to complete successfully")
            if trigger_time is None:
                issues.append("No maintenance was triggered during simulation")
            elif trigger_time > profile.expected_trigger_time_hours:
                issues.append(f"First trigger ({trigger_time:.2f}h) later than expected ({profile.expected_trigger_time_hours}h)")
            if not initial_conditions_applied:
                issues.append("Initial conditions may not have been applied correctly")
            
            result = ValidationResult(
                action=action,
                subsystem=subsystem,
                scenario_profile=profile_name,
                simulation_duration_hours=profile.target_duration_hours,
                success=results['success'],
                work_orders_created=results['work_orders_created'],
                maintenance_events=results['maintenance_events'],
                execution_time_seconds=execution_time,
                trigger_time_hours=trigger_time,
                trigger_rate=trigger_rate,
                timing_score=timing_score,
                reliability_score=reliability_score,
                initial_conditions_applied=initial_conditions_applied,
                degradation_detected=degradation_detected,
                threshold_crossed=threshold_crossed,
                issues=issues
            )
            
            # Print results
            if result.success and not result.issues:
                print(f"   ✅ PASSED: Triggered at {trigger_time:.2f}h, {result.work_orders_created} work orders")
            elif result.success:
                print(f"   ⚠️ PASSED with issues: {len(result.issues)} issues detected")
            else:
                print(f"   ❌ FAILED: {len(result.issues)} issues detected")
            
            for issue in result.issues:
                print(f"      - {issue}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"   ❌ FAILED: Exception during validation - {e}")
            
            return ValidationResult(
                action=action,
                subsystem=subsystem,
                scenario_profile=profile_name,
                simulation_duration_hours=profile.target_duration_hours,
                success=False,
                work_orders_created=0,
                maintenance_events=0,
                execution_time_seconds=execution_time,
                trigger_time_hours=None,
                trigger_rate=0.0,
                timing_score=0.0,
                reliability_score=0.0,
                initial_conditions_applied=False,
                degradation_detected=False,
                threshold_crossed=False,
                issues=[f"Validation failed: {str(e)}"]
            )
    
    def _check_initial_conditions_applied(self, config: Dict[str, Any], action: str) -> bool:
        """Check if initial conditions were properly applied for the action"""
        subsystem = self.composer.action_subsystem_map.get(action)
        if not subsystem:
            return False
        
        # Check if the subsystem has initial conditions in the config
        subsystem_config = config.get('secondary_system', {}).get(subsystem, {})
        initial_conditions = subsystem_config.get('initial_conditions', {})
        
        # Basic check: if there are any initial conditions, assume they were applied
        # More sophisticated checks could validate specific parameter values
        return len(initial_conditions) > 0
    
    def validate_multiple_actions(self, actions: List[str], profile_name: str,
                                 parallel: bool = True) -> Dict[str, ValidationResult]:
        """Validate multiple actions for a given profile"""
        
        print(f"\n🎯 Validating {len(actions)} actions for {profile_name} profile")
        
        results = {}
        
        if parallel and len(actions) > 1:
            # Run validations in parallel
            with ThreadPoolExecutor(max_workers=min(4, len(actions))) as executor:
                future_to_action = {
                    executor.submit(self.validate_action, action, profile_name): action
                    for action in actions
                }
                
                for future in as_completed(future_to_action):
                    action = future_to_action[future]
                    try:
                        result = future.result()
                        results[action] = result
                        status = "✅ PASSED" if result.success and not result.issues else "⚠️ ISSUES" if result.success else "❌ FAILED"
                        print(f"   {status} {action}: {result.work_orders_created} work orders")
                    except Exception as e:
                        print(f"   ❌ FAILED {action}: {e}")
        else:
            # Run validations sequentially
            for i, action in enumerate(actions):
                print(f"\n--- Action {i+1}/{len(actions)}: {action} ---")
                
                try:
                    result = self.validate_action(action, profile_name)
                    results[action] = result
                except Exception as e:
                    print(f"❌ {action}: Validation failed - {e}")
        
        # Summary
        passed = sum(1 for r in results.values() if r.success and not r.issues)
        passed_with_issues = sum(1 for r in results.values() if r.success and r.issues)
        failed = sum(1 for r in results.values() if not r.success)
        
        print(f"\n📊 Validation Summary for {profile_name}:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️ Passed with issues: {passed_with_issues}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success rate: {(passed + passed_with_issues) / len(actions) * 100:.1f}%")
        
        self.validation_results.extend(results.values())
        return results
    
    def validate_all_profiles(self, actions: List[str]) -> Dict[str, Dict[str, ValidationResult]]:
        """Validate actions across all scenario profiles"""
        
        print(f"\n🚀 Validating {len(actions)} actions across all profiles")
        print(f"   Actions: {actions}")
        print(f"   Profiles: {list(self.scenario_profiles.keys())}")
        
        all_results = {}
        
        for profile_name in self.scenario_profiles.keys():
            print(f"\n=== Validating {profile_name} Profile ===")
            
            profile_results = self.validate_multiple_actions(actions, profile_name)
            all_results[profile_name] = profile_results
        
        # Overall summary
        total_tests = sum(len(profile_results) for profile_results in all_results.values())
        total_passed = sum(1 for profile_results in all_results.values() 
                          for result in profile_results.values() 
                          if result.success and not result.issues)
        total_passed_with_issues = sum(1 for profile_results in all_results.values() 
                                     for result in profile_results.values() 
                                     if result.success and result.issues)
        total_failed = sum(1 for profile_results in all_results.values() 
                          for result in profile_results.values() 
                          if not result.success)
        
        print(f"\n🎯 Overall Validation Summary:")
        print(f"   Total tests: {total_tests}")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ⚠️ Passed with issues: {total_passed_with_issues}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   📈 Overall success rate: {(total_passed + total_passed_with_issues) / total_tests * 100:.1f}%")
        
        return all_results
    
    def save_results(self, filename: Optional[str] = None) -> Path:
        """Save validation results to file"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simplified_validation_results_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        # Prepare data for saving
        data = {
            'timestamp': datetime.now().isoformat(),
            'approach': 'realistic_thresholds_with_targeted_initial_conditions',
            'scenario_profiles': {name: asdict(profile) for name, profile in self.scenario_profiles.items()},
            'validation_results': [result.to_dict() for result in self.validation_results],
            'summary': {
                'total_tests': len(self.validation_results),
                'successful_tests': sum(1 for r in self.validation_results if r.success),
                'passed_tests': sum(1 for r in self.validation_results if r.success and not r.issues),
                'actions_tested': len(set(r.action for r in self.validation_results)),
                'profiles_tested': len(set(r.scenario_profile for r in self.validation_results))
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Results saved to {filepath}")
        return filepath
    
    def create_validation_report(self, actions: List[str]) -> str:
        """Create a comprehensive validation report"""
        
        # Run validation across all profiles
        all_results = self.validate_all_profiles(actions)
        
        # Create report
        report_lines = [
            "# Simplified Maintenance Tuning Framework - Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Approach",
            "This validation uses the simplified approach:",
            "- **Realistic industry-standard thresholds** (fixed in template)",
            "- **Targeted initial conditions** (set parameters near thresholds)",
            "- **Natural physics degradation** (parameters naturally cross thresholds)",
            "",
            "## Summary",
            f"- Actions validated: {len(actions)}",
            f"- Scenario profiles: {len(self.scenario_profiles)}",
            f"- Total tests run: {len(self.validation_results)}",
            ""
        ]
        
        # Add profile summaries
        for profile_name, profile_results in all_results.items():
            profile = self.scenario_profiles[profile_name]
            passed = sum(1 for r in profile_results.values() if r.success and not r.issues)
            passed_with_issues = sum(1 for r in profile_results.values() if r.success and r.issues)
            failed = sum(1 for r in profile_results.values() if not r.success)
            
            report_lines.extend([
                f"## {profile_name.title().replace('_', ' ')} Profile",
                f"**Description:** {profile.description}",
                f"**Duration:** {profile.target_duration_hours} hours",
                f"**Expected trigger time:** {profile.expected_trigger_time_hours} hours",
                f"**Results:** {passed} passed, {passed_with_issues} passed with issues, {failed} failed",
                ""
            ])
            
            # Add action details
            for action, result in profile_results.items():
                status = "✅ PASSED" if result.success and not result.issues else "⚠️ ISSUES" if result.success else "❌ FAILED"
                trigger_info = f"triggered at {result.trigger_time_hours:.2f}h" if result.trigger_time_hours else "no trigger"
                
                report_lines.extend([
                    f"### {action} - {status}",
                    f"- Work orders: {result.work_orders_created}",
                    f"- Trigger timing: {trigger_info}",
                    f"- Execution time: {result.execution_time_seconds:.1f}s",
                    f"- Issues: {len(result.issues)}",
                ])
                
                for issue in result.issues:
                    report_lines.append(f"  - {issue}")
                
                report_lines.append("")
        
        report_text = "\n".join(report_lines)
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"simplified_validation_report_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write(report_text)
        
        print(f"📄 Report saved to {report_path}")
        
        return report_text


# Convenience functions for easy usage
def quick_validation(actions: List[str], profile: str = "training_realistic") -> Dict[str, ValidationResult]:
    """Quick validation for a list of actions"""
    framework = SimplifiedTuningFramework()
    return framework.validate_multiple_actions(actions, profile)


def full_validation_suite(actions: Optional[List[str]] = None) -> str:
    """Run full validation suite for all actions and profiles"""
    framework = SimplifiedTuningFramework()
    
    if actions is None:
        # Use a representative sample of actions
        actions = [
            "oil_top_off",
            "oil_change", 
            "tsp_chemical_cleaning",
            "vibration_analysis",
            "condenser_tube_cleaning"
        ]
    
    report = framework.create_validation_report(actions)
    framework.save_results()
    
    return report


if __name__ == "__main__":
    print("🔧 Simplified Maintenance Tuning Framework")
    print("=" * 60)
    
    # Run a quick demonstration
    test_actions = ["oil_top_off", "tsp_chemical_cleaning"]
    
    print(f"Running demonstration with actions: {test_actions}")
    print("Approach: Realistic thresholds + targeted initial conditions + natural degradation")
    
    try:
        framework = SimplifiedTuningFramework()
        
        # Test one action quickly
        result = framework.validate_action("oil_top_off", "demo_fast")
        
        if result.success:
            print(f"\n✅ Demonstration completed successfully!")
            print(f"   Action: {result.action}")
            print(f"   Triggered at: {result.trigger_time_hours:.2f}h")
            print(f"   Work orders: {result.work_orders_created}")
            print(f"   Issues: {len(result.issues)}")
            
            # Save results
            framework.save_results("demo_results.json")
        else:
            print(f"\n⚠️ Demonstration had issues:")
            for issue in result.issues:
                print(f"   - {issue}")
            
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
