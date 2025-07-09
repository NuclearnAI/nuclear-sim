"""
Main maintenance tuning framework.

This module provides the central framework for generating and validating
maintenance scenarios with intelligent initial conditions using the existing
simulator infrastructure.
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simulator.core.sim import NuclearPlantSimulator
from .validation_results import (
    ValidationResult, ScenarioProfile, ValidationResultsCollection,
    get_scenario_profile, SCENARIO_PROFILES
)
from ..optimization import ICOptimizer, TimingOptimizationResult
from ..config_engine.composers.comprehensive_composer import ComprehensiveComposer


class MaintenanceTuningFramework:
    """
    Main framework for maintenance scenario generation and validation
    
    This framework orchestrates the entire process of:
    1. Analyzing simulator thresholds
    2. Generating targeted initial conditions
    3. Creating configured simulators
    4. Running validation scenarios
    5. Collecting and analyzing results
    """
    
    def __init__(self, base_simulator: Optional[NuclearPlantSimulator] = None,
                 output_dir: Optional[str] = None, verbose: bool = True):
        """
        Initialize the maintenance tuning framework
        
        Args:
            base_simulator: Optional base simulator for analysis (will create one if None)
            output_dir: Output directory for results (default: data_gen/outputs)
            verbose: Enable verbose output
        """
        self.verbose = verbose
        
        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "outputs"
        
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "configs").mkdir(exist_ok=True)
        (self.output_dir / "results").mkdir(exist_ok=True)
        (self.output_dir / "data").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
        
        # Initialize components
        self.composer = ComprehensiveComposer()
        self.ic_optimizer = ICOptimizer(output_dir=str(self.output_dir), verbose=verbose)
        self.results_collection = ValidationResultsCollection()
        
        if self.verbose:
            print(f"🔧 MaintenanceTuningFramework initialized")
            print(f"   📁 Output directory: {self.output_dir}")
            print(f"   🎯 Available actions: {len(self.get_available_actions())}")
            print(f"    Scenario profiles: {list(SCENARIO_PROFILES.keys())}")
    
    def _create_base_simulator(self) -> NuclearPlantSimulator:
        """Create a base simulator for threshold analysis"""
        if self.verbose:
            print(f"   🔧 Creating base simulator with comprehensive configuration...")
        
        # Generate a base configuration using ComprehensiveComposer
        base_config = self.composer.compose_action_test_scenario(
            target_action="oil_top_off",  # Use a common action for base config
            duration_hours=1.0  # Short duration for analysis
        )
        
        # Create simulator with the comprehensive configuration
        simulator = NuclearPlantSimulator(
            enable_state_management=True,
            enable_secondary=True,
            secondary_config=base_config,  # Pass the whole config
            dt=1.0 # 1 minute time step
        )
        
        # Reset to steady state for consistent analysis
        # simulator.reset(start_at_steady_state=True)
        
        if self.verbose:
            print(f"   ✅ Base simulator created with comprehensive configuration")
        
        return simulator
    
    def get_available_actions(self) -> List[str]:
        """Get all available maintenance actions"""
        return self.ic_optimizer.get_available_actions()
    
    def get_available_profiles(self) -> List[str]:
        """Get all available scenario profiles"""
        return list(SCENARIO_PROFILES.keys())
    
    def optimize_for_timing(self, target_action: str, target_trigger_hours: float,
                          tolerance_hours: float = 0.1, scenario_profile: str = "training_realistic",
                          max_iterations: int = 10) -> TimingOptimizationResult:
        """
        Optimize initial conditions for target trigger timing
        
        Args:
            target_action: Maintenance action to optimize
            target_trigger_hours: Target trigger time in hours
            tolerance_hours: Acceptable timing tolerance
            scenario_profile: Scenario profile for optimization
            max_iterations: Maximum optimization iterations
            
        Returns:
            TimingOptimizationResult with optimization details
        """
        return self.ic_optimizer.optimize_for_target_timing(
            target_action=target_action,
            target_trigger_hours=target_trigger_hours,
            tolerance_hours=tolerance_hours,
            scenario_profile=scenario_profile,
            max_iterations=max_iterations
        )
    
    def batch_optimize_timing(self, timing_targets: Dict[str, float],
                            tolerance_hours: float = 0.1, scenario_profile: str = "training_realistic",
                            max_iterations: int = 10) -> List[TimingOptimizationResult]:
        """
        Batch optimize multiple actions for target timing
        
        Args:
            timing_targets: Dictionary mapping action names to target trigger hours
            tolerance_hours: Timing tolerance for all actions
            scenario_profile: Scenario profile for optimization
            max_iterations: Maximum optimization iterations per action
            
        Returns:
            List of TimingOptimizationResult objects
        """
        return self.ic_optimizer.batch_optimize_timing(
            timing_targets=timing_targets,
            tolerance_hours=tolerance_hours,
            scenario_profile=scenario_profile,
            max_iterations=max_iterations
        )
    
    def create_targeted_simulator(self, target_action: str, 
                                scenario_profile: str = "training_realistic") -> NuclearPlantSimulator:
        """
        Create a simulator configured for a specific maintenance action using ComprehensiveComposer
        
        Args:
            target_action: Maintenance action to target
            scenario_profile: Scenario profile to use
            
        Returns:
            Configured simulator instance
        """
        profile = get_scenario_profile(scenario_profile)
        
        if self.verbose:
            print(f"🎯 Creating targeted simulator for {target_action} ({scenario_profile})")
        
        # Generate configuration using ComprehensiveComposer (handles ICs automatically)
        config = self.composer.compose_action_test_scenario(
            target_action=target_action,
            duration_hours=profile.target_duration_hours
        )
        
        # Create simulator with comprehensive configuration
        simulator = NuclearPlantSimulator(
            enable_state_management=True,
            enable_secondary=True,
            secondary_config=config,
            dt=1.0  # 1 minute time step
        )
        
        # Reset to apply initial conditions
        # simulator.reset(start_at_steady_state=True)
        
        if self.verbose:
            print(f"   ✅ Created simulator with ComprehensiveComposer configuration")
        
        return simulator
    
    def validate_action_scenario(self, target_action: str, 
                               scenario_profile: str = "training_realistic") -> ValidationResult:
        """
        Validate a maintenance action scenario
        
        Args:
            target_action: Maintenance action to validate
            scenario_profile: Scenario profile to use
            
        Returns:
            Validation result
        """
        profile = get_scenario_profile(scenario_profile)
        
        if self.verbose:
            print(f"\n🎯 Validating {target_action} for {scenario_profile} profile")
            print(f"   Duration: {profile.target_duration_hours}h")
            print(f"   Expected trigger: {profile.expected_trigger_time_hours}h")
        
        # Determine subsystem from ComprehensiveComposer
        subsystem = self.composer.action_subsystem_map.get(target_action, "unknown")
        
        # Create targeted simulator
        start_time = time.time()
        simulator = self.create_targeted_simulator(target_action, scenario_profile)
        
        # Run simulation
        duration_minutes = int(profile.target_duration_hours * 60)
        
        if self.verbose:
            print(f"   🚀 Running simulation for {duration_minutes} minutes...")
        
        for minute in range(duration_minutes):
            simulator.step()
            
            # Print progress every 10 minutes for long simulations
            if self.verbose and duration_minutes > 30 and minute % 10 == 0:
                print(f"   ⏱️ Progress: {minute}/{duration_minutes} minutes")
        
        execution_time = time.time() - start_time
        
        # Analyze results
        results = self._analyze_simulation_results(
            simulator, target_action, subsystem, profile, execution_time
        )
        
        # Export data
        csv_path = self._export_simulation_data(simulator, target_action, scenario_profile)
        results.csv_export_path = str(csv_path)
        
        # Add to results collection
        self.results_collection.add_result(results)
        
        if self.verbose:
            print(f"   📋 {results.get_summary()}")
        
        return results
    
    def _analyze_simulation_results(self, simulator: NuclearPlantSimulator, 
                                  target_action: str, subsystem: str,
                                  profile: ScenarioProfile, execution_time: float) -> ValidationResult:
        """Analyze simulation results and create ValidationResult"""
        
        # Get maintenance history from state manager
        maintenance_history = simulator.state_manager.get_maintenance_history()
        work_orders_created = len(maintenance_history)
        
        # Find first trigger time
        trigger_time_hours = None
        if maintenance_history:
            trigger_times = [record['timestamp'] / 3600.0 for record in maintenance_history]
            trigger_time_hours = min(trigger_times)
        
        # Calculate performance metrics
        trigger_rate = work_orders_created / profile.target_duration_hours
        
        # Timing score: how well it met timing expectations
        if trigger_time_hours and trigger_time_hours <= profile.expected_trigger_time_hours:
            timing_score = 1.0 - (trigger_time_hours / profile.expected_trigger_time_hours)
        else:
            timing_score = 0.0
        
        # Reliability score: basic success indicator
        reliability_score = 1.0 if work_orders_created > 0 and trigger_time_hours else 0.0
        
        # Validation checks
        initial_conditions_applied = True  # Assume true if simulator was created successfully
        degradation_detected = trigger_time_hours is not None
        threshold_crossed = work_orders_created > 0
        
        # Check maintenance effectiveness
        maintenance_effective = False
        if maintenance_history:
            effective_actions = sum(1 for record in maintenance_history if record.get('success', False))
            maintenance_effective = effective_actions > 0
        
        # Detect issues
        issues = []
        warnings = []
        
        if execution_time > profile.max_execution_time_seconds:
            issues.append(f"Execution time ({execution_time:.1f}s) exceeded limit ({profile.max_execution_time_seconds}s)")
        
        if not threshold_crossed:
            issues.append("No maintenance was triggered during simulation")
        elif trigger_time_hours and trigger_time_hours > profile.expected_trigger_time_hours:
            warnings.append(f"First trigger ({trigger_time_hours:.2f}h) later than expected ({profile.expected_trigger_time_hours}h)")
        
        if work_orders_created == 0:
            issues.append("No work orders were created")
        
        # Get final power level
        final_power_level = simulator.state.power_level
        
        # Count work orders executed
        work_orders_executed = sum(1 for record in maintenance_history if record.get('success', False))
        
        # Calculate maintenance effectiveness
        maintenance_effectiveness = work_orders_executed / work_orders_created if work_orders_created > 0 else 0.0
        
        return ValidationResult(
            action=target_action,
            subsystem=subsystem or "unknown",
            scenario_profile=profile.name,
            simulation_duration_hours=profile.target_duration_hours,
            success=threshold_crossed,
            work_orders_created=work_orders_created,
            maintenance_events=len(maintenance_history),
            execution_time_seconds=execution_time,
            trigger_time_hours=trigger_time_hours,
            trigger_rate=trigger_rate,
            timing_score=timing_score,
            reliability_score=reliability_score,
            initial_conditions_applied=initial_conditions_applied,
            degradation_detected=degradation_detected,
            threshold_crossed=threshold_crossed,
            maintenance_effective=maintenance_effective,
            issues=issues,
            warnings=warnings,
            final_power_level=final_power_level,
            work_orders_executed=work_orders_executed,
            maintenance_effectiveness=maintenance_effectiveness
        )
    
    def _export_simulation_data(self, simulator: NuclearPlantSimulator, 
                              target_action: str, scenario_profile: str) -> Path:
        """Export simulation data to CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_action}_{scenario_profile}_{timestamp}.csv"
        csv_path = self.output_dir / "data" / filename
        
        simulator.export_state_data(str(csv_path))
        
        return csv_path
    
    def validate_multiple_actions(self, actions: List[str], 
                                scenario_profile: str = "training_realistic") -> Dict[str, ValidationResult]:
        """
        Validate multiple maintenance actions
        
        Args:
            actions: List of maintenance actions to validate
            scenario_profile: Scenario profile to use
            
        Returns:
            Dictionary mapping action names to validation results
        """
        if self.verbose:
            print(f"\n🎯 Validating {len(actions)} actions for {scenario_profile} profile")
        
        results = {}
        
        for i, action in enumerate(actions):
            if self.verbose:
                print(f"\n--- Action {i+1}/{len(actions)}: {action} ---")
            
            try:
                result = self.validate_action_scenario(action, scenario_profile)
                results[action] = result
            except Exception as e:
                if self.verbose:
                    print(f"   ❌ Failed: {e}")
                # Create failed result
                results[action] = ValidationResult(
                    action=action,
                    subsystem="unknown",
                    scenario_profile=scenario_profile,
                    simulation_duration_hours=0.0,
                    success=False,
                    work_orders_created=0,
                    maintenance_events=0,
                    execution_time_seconds=0.0,
                    trigger_time_hours=None,
                    trigger_rate=0.0,
                    timing_score=0.0,
                    reliability_score=0.0,
                    initial_conditions_applied=False,
                    degradation_detected=False,
                    threshold_crossed=False,
                    maintenance_effective=False,
                    issues=[f"Validation failed: {str(e)}"],
                    warnings=[]
                )
        
        if self.verbose:
            self._print_batch_summary(results)
        
        return results
    
    def validate_action_across_profiles(self, target_action: str) -> Dict[str, ValidationResult]:
        """
        Validate an action across all scenario profiles
        
        Args:
            target_action: Maintenance action to validate
            
        Returns:
            Dictionary mapping profile names to validation results
        """
        if self.verbose:
            print(f"\n🎯 Validating {target_action} across all profiles")
        
        results = {}
        
        for profile_name in SCENARIO_PROFILES.keys():
            if self.verbose:
                print(f"\n--- Profile: {profile_name} ---")
            
            try:
                result = self.validate_action_scenario(target_action, profile_name)
                results[profile_name] = result
            except Exception as e:
                if self.verbose:
                    print(f"   ❌ Failed: {e}")
                continue
        
        return results
    
    def validate_all_actions(self, scenario_profile: str = "training_realistic") -> Dict[str, ValidationResult]:
        """
        Validate all available maintenance actions
        
        Args:
            scenario_profile: Scenario profile to use
            
        Returns:
            Dictionary mapping action names to validation results
        """
        all_actions = self.get_available_actions()
        
        if self.verbose:
            print(f"\n🚀 Validating ALL {len(all_actions)} available actions")
            print(f"   Profile: {scenario_profile}")
            print(f"   Estimated time: {len(all_actions) * 2} minutes")
        
        return self.validate_multiple_actions(all_actions, scenario_profile)
    
    def _print_batch_summary(self, results: Dict[str, ValidationResult]):
        """Print summary of batch validation results"""
        if not results:
            return
        
        successful = sum(1 for r in results.values() if r.success and not r.issues)
        successful_with_issues = sum(1 for r in results.values() if r.success and r.issues)
        failed = sum(1 for r in results.values() if not r.success)
        
        print(f"\n📊 Batch Validation Summary:")
        print(f"   ✅ Passed: {successful}")
        print(f"   ⚠️ Passed with issues: {successful_with_issues}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success rate: {(successful + successful_with_issues) / len(results) * 100:.1f}%")
        
        # Show top performers
        if successful > 0:
            top_performers = sorted(
                [r for r in results.values() if r.success],
                key=lambda x: x.work_orders_created,
                reverse=True
            )[:3]
            
            print(f"\n🏆 Top Performers:")
            for result in top_performers:
                print(f"   {result.action}: {result.work_orders_created} work orders, "
                      f"triggered at {result.trigger_time_hours:.2f}h")
    
    def save_results(self, filename: Optional[str] = None) -> Path:
        """
        Save validation results to file
        
        Args:
            filename: Optional filename (will generate if None)
            
        Returns:
            Path to saved results file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_results_{timestamp}.json"
        
        results_path = self.output_dir / "results" / filename
        
        with open(results_path, 'w') as f:
            json.dump(self.results_collection.to_dict(), f, indent=2)
        
        if self.verbose:
            print(f"💾 Results saved to {results_path}")
        
        return results_path
    
    def generate_report(self, filename: Optional[str] = None) -> Path:
        """
        Generate a comprehensive validation report
        
        Args:
            filename: Optional filename (will generate if None)
            
        Returns:
            Path to generated report file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_report_{timestamp}.md"
        
        report_path = self.output_dir / "reports" / filename
        
        # Generate report content
        report_lines = [
            "# Maintenance Tuning Framework - Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Total validations: {len(self.results_collection.results)}",
            f"- Success rate: {self.results_collection.get_success_rate():.1%}",
            f"- Trigger rate: {self.results_collection.get_trigger_rate():.1%}",
            f"- Average trigger time: {self.results_collection.get_average_trigger_time():.2f}h" if self.results_collection.get_average_trigger_time() else "- Average trigger time: N/A",
            "",
            "## Results by Action"
        ]
        
        # Group results by action
        actions = set(r.action for r in self.results_collection.results)
        for action in sorted(actions):
            action_results = self.results_collection.get_results_by_action(action)
            successful = sum(1 for r in action_results if r.is_successful())
            
            report_lines.extend([
                f"### {action}",
                f"- Tests: {len(action_results)}",
                f"- Success rate: {successful / len(action_results):.1%}",
                ""
            ])
            
            for result in action_results:
                report_lines.append(f"- {result.get_summary()}")
            
            report_lines.append("")
        
        # Write report
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        if self.verbose:
            print(f"📄 Report saved to {report_path}")
        
        return report_path
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for all validation results"""
        return self.results_collection.get_summary_stats()
