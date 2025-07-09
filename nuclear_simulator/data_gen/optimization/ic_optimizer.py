"""
Initial conditions optimizer.

This module provides the main IC optimization engine that coordinates
timing optimization, config generation, and result analysis.
"""

import sys
import time
import copy
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .timing_optimizer import TimingOptimizer
from .optimization_results import (
    OptimizationResult, TimingOptimizationResult, 
    create_timing_optimization_result
)
from ..config_engine.composers.comprehensive_composer import ComprehensiveComposer


class ICOptimizer:
    """
    Main initial conditions optimization engine
    
    Coordinates timing optimization, config generation, and result analysis
    to produce optimized configurations for maintenance scenarios.
    """
    
    def __init__(self, output_dir: Optional[str] = None, verbose: bool = True):
        """
        Initialize IC optimizer
        
        Args:
            output_dir: Output directory for results (default: data_gen/outputs)
            verbose: Enable verbose output
        """
        self.verbose = verbose
        
        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "outputs"
        
        # Ensure output directories exist
        (self.output_dir / "optimized_configs").mkdir(exist_ok=True)
        (self.output_dir / "baseline_configs").mkdir(exist_ok=True)
        (self.output_dir / "optimization_reports").mkdir(exist_ok=True)
        
        # Initialize components
        self.composer = ComprehensiveComposer()
        self.timing_optimizer = TimingOptimizer(verbose=verbose)
        
        if self.verbose:
            print(f"🔧 ICOptimizer initialized")
            print(f"   📁 Output directory: {self.output_dir}")
    
    def optimize_for_target_timing(self, target_action: str, target_trigger_hours: float,
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
        if self.verbose:
            print(f"\n🎯 Optimizing {target_action} for target timing")
            print(f"   Target: {target_trigger_hours:.2f}h ±{tolerance_hours:.2f}h")
            print(f"   Profile: {scenario_profile}")
        
        start_time = time.time()
        
        # Generate base configuration using ComprehensiveComposer
        if self.verbose:
            print(f"   🔧 Generating base configuration...")
        
        base_config = self.composer.compose_action_test_scenario(
            target_action=target_action,
            duration_hours=target_trigger_hours * 3  # Allow extra time for optimization
        )
        
        # Save baseline configuration
        baseline_config_path = self._save_baseline_config(base_config, target_action, scenario_profile)
        
        # Extract baseline initial conditions
        baseline_ics = self._extract_initial_conditions(base_config, target_action)
        
        if self.verbose:
            print(f"   📊 Baseline ICs: {len(baseline_ics)} parameters")
            for param, value in list(baseline_ics.items())[:3]:  # Show first 3
                print(f"      {param}: {value}")
            if len(baseline_ics) > 3:
                print(f"      ... and {len(baseline_ics) - 3} more")
        
        # Run timing optimization
        if self.verbose:
            print(f"   🚀 Running timing optimization...")
        
        optimized_config, achieved_trigger_hours, iterations_used = self.timing_optimizer.optimize_for_target_timing(
            base_config=base_config,
            target_action=target_action,
            target_trigger_hours=target_trigger_hours,
            tolerance_hours=tolerance_hours,
            max_iterations=max_iterations
        )
        
        optimization_time = time.time() - start_time
        
        # Extract optimized initial conditions
        optimized_ics = self._extract_initial_conditions(optimized_config, target_action)
        
        # Save optimized configuration
        optimized_config_path = self._save_optimized_config(
            optimized_config, target_action, scenario_profile, target_trigger_hours
        )
        
        # Generate optimization report
        optimization_report_path = self._save_optimization_report(
            target_action, scenario_profile, target_trigger_hours, tolerance_hours,
            achieved_trigger_hours, baseline_ics, optimized_ics, iterations_used, optimization_time
        )
        
        # Create result
        result = create_timing_optimization_result(
            action=target_action,
            scenario_profile=scenario_profile,
            target_trigger_hours=target_trigger_hours,
            tolerance_hours=tolerance_hours,
            achieved_trigger_hours=achieved_trigger_hours,
            baseline_ics=baseline_ics,
            optimized_ics=optimized_ics,
            optimization_iterations=iterations_used,
            optimization_time_seconds=optimization_time,
            baseline_config_path=str(baseline_config_path),
            optimized_config_path=str(optimized_config_path),
            optimization_report_path=str(optimization_report_path)
        )
        
        if self.verbose:
            print(f"   📋 {result.get_timing_summary()}")
            print(f"   💾 Optimized config: {optimized_config_path.name}")
            print(f"   📄 Report: {optimization_report_path.name}")
        
        return result
    
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
        if self.verbose:
            print(f"\n🚀 Batch timing optimization for {len(timing_targets)} actions")
            print(f"   Profile: {scenario_profile}")
            print(f"   Tolerance: ±{tolerance_hours:.2f}h")
        
        results = []
        
        for i, (action, target_hours) in enumerate(timing_targets.items(), 1):
            if self.verbose:
                print(f"\n--- Action {i}/{len(timing_targets)}: {action} ---")
            
            try:
                result = self.optimize_for_target_timing(
                    target_action=action,
                    target_trigger_hours=target_hours,
                    tolerance_hours=tolerance_hours,
                    scenario_profile=scenario_profile,
                    max_iterations=max_iterations
                )
                results.append(result)
                
            except Exception as e:
                if self.verbose:
                    print(f"   ❌ Optimization failed: {e}")
                continue
        
        # Print batch summary
        if self.verbose:
            self._print_batch_summary(results)
        
        return results
    
    def get_available_actions(self) -> List[str]:
        """Get available actions from ComprehensiveComposer"""
        return list(self.composer.action_subsystem_map.keys())
    
    def _save_baseline_config(self, config: Dict[str, Any], action: str, profile: str) -> Path:
        """Save baseline configuration for comparison"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{action}_baseline_{profile}_{timestamp}.yaml"
        path = self.output_dir / "baseline_configs" / filename
        
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        return path
    
    def _save_optimized_config(self, config: Dict[str, Any], action: str, profile: str, 
                             target_hours: float) -> Path:
        """Save optimized configuration with metadata"""
        # Add optimization metadata
        optimized_config = copy.deepcopy(config)
        optimized_config['optimization_metadata'] = {
            'optimized': True,
            'optimization_timestamp': datetime.now().isoformat(),
            'optimization_tool': 'MaintenanceTuningFramework',
            'optimization_goal': 'target_timing',
            'target_action': action,
            'scenario_profile': profile,
            'target_trigger_hours': target_hours,
            'optimized_by': 'ICOptimizer'
        }
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{action}_target_{target_hours:.1f}h_{profile}_{timestamp}.yaml"
        path = self.output_dir / "optimized_configs" / filename
        
        with open(path, 'w') as f:
            yaml.dump(optimized_config, f, default_flow_style=False, sort_keys=False)
        
        return path
    
    def _save_optimization_report(self, action: str, profile: str, target_hours: float,
                                tolerance_hours: float, achieved_hours: Optional[float],
                                baseline_ics: Dict[str, Any], optimized_ics: Dict[str, Any],
                                iterations: int, optimization_time: float) -> Path:
        """Save detailed optimization report"""
        
        # Calculate metrics
        timing_accuracy = None
        within_tolerance = False
        improvement = "No trigger detected"
        
        if achieved_hours is not None:
            timing_accuracy = abs(achieved_hours - target_hours)
            within_tolerance = timing_accuracy <= tolerance_hours
            improvement = f"Achieved {achieved_hours:.3f}h (±{timing_accuracy:.3f}h)"
        
        # Create report
        report = {
            'optimization_summary': {
                'action': action,
                'scenario_profile': profile,
                'optimization_goal': 'target_timing',
                'optimization_timestamp': datetime.now().isoformat(),
                'optimization_time_seconds': optimization_time,
                'iterations_used': iterations
            },
            'timing_optimization': {
                'target_trigger_hours': target_hours,
                'tolerance_hours': tolerance_hours,
                'achieved_trigger_hours': achieved_hours,
                'timing_accuracy_hours': timing_accuracy,
                'within_tolerance': within_tolerance,
                'improvement_description': improvement
            },
            'initial_conditions': {
                'baseline_ics': baseline_ics,
                'optimized_ics': optimized_ics,
                'parameters_optimized': len(optimized_ics),
                'ic_changes': self._calculate_ic_changes(baseline_ics, optimized_ics)
            },
            'performance_metrics': {
                'optimization_successful': within_tolerance,
                'timing_improvement': timing_accuracy if timing_accuracy else 0.0,
                'convergence_achieved': within_tolerance,
                'optimization_efficiency': iterations / 10.0  # Normalize to max iterations
            }
        }
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{action}_optimization_report_{timestamp}.json"
        path = self.output_dir / "optimization_reports" / filename
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return path
    
    def _extract_initial_conditions(self, config: Dict[str, Any], target_action: str) -> Dict[str, Any]:
        """Extract initial conditions from configuration"""
        return self.timing_optimizer._extract_initial_conditions(config, target_action)
    
    def _calculate_ic_changes(self, baseline_ics: Dict[str, Any], 
                            optimized_ics: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Calculate changes between baseline and optimized ICs"""
        changes = {}
        
        for param in set(baseline_ics.keys()) | set(optimized_ics.keys()):
            baseline_val = baseline_ics.get(param, 0.0)
            optimized_val = optimized_ics.get(param, 0.0)
            
            if baseline_val != 0:
                percent_change = ((optimized_val - baseline_val) / baseline_val) * 100
            else:
                percent_change = 0.0
            
            changes[param] = {
                'baseline': baseline_val,
                'optimized': optimized_val,
                'absolute_change': optimized_val - baseline_val,
                'percent_change': percent_change
            }
        
        return changes
    
    def _print_batch_summary(self, results: List[TimingOptimizationResult]):
        """Print summary of batch optimization results"""
        if not results:
            return
        
        successful = sum(1 for r in results if r.within_tolerance)
        failed = len(results) - successful
        
        print(f"\n📊 Batch Optimization Summary:")
        print(f"   ✅ Successful: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
        print(f"   ❌ Failed: {failed}")
        
        if successful > 0:
            # Show successful optimizations
            print(f"\n🏆 Successful Optimizations:")
            for result in results:
                if result.within_tolerance:
                    print(f"   {result.get_timing_summary()}")
        
        if failed > 0:
            # Show failed optimizations
            print(f"\n⚠️ Failed Optimizations:")
            for result in results:
                if not result.within_tolerance:
                    print(f"   {result.get_timing_summary()}")
        
        # Calculate average metrics
        avg_iterations = sum(r.optimization_iterations for r in results) / len(results)
        avg_time = sum(r.optimization_time_seconds for r in results) / len(results)
        
        print(f"\n📈 Performance Metrics:")
        print(f"   Average iterations: {avg_iterations:.1f}")
        print(f"   Average time: {avg_time:.1f}s")
        print(f"   Total optimization time: {sum(r.optimization_time_seconds for r in results):.1f}s")
