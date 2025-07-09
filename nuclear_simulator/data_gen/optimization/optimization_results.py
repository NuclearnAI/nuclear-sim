"""
Optimization results data structures.

This module defines the data structures used for storing and analyzing
initial conditions optimization results.
"""

import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime


@dataclass
class OptimizationResult:
    """Results from initial conditions optimization"""
    # Test identification
    action: str
    scenario_profile: str
    optimization_goal: str
    optimization_timestamp: str
    
    # File paths
    baseline_config_path: Optional[str]
    optimized_config_path: Optional[str]
    optimization_report_path: Optional[str]
    
    # Initial conditions
    baseline_ics: Dict[str, Any]
    optimized_ics: Dict[str, Any]
    
    # Optimization metrics
    optimization_iterations: int
    optimization_time_seconds: float
    improvement_achieved: bool
    
    # Performance comparison
    baseline_performance: Dict[str, float]
    optimized_performance: Dict[str, float]
    improvement_metrics: Dict[str, float]
    
    # Issues and diagnostics
    optimization_issues: List[str]
    optimization_warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def get_summary(self) -> str:
        """Get human-readable summary of optimization result"""
        status = "✅ IMPROVED" if self.improvement_achieved else "❌ NO IMPROVEMENT"
        goal = self.optimization_goal
        iterations = self.optimization_iterations
        time_taken = self.optimization_time_seconds
        
        summary = f"{status} {self.action} ({goal}): {iterations} iterations in {time_taken:.1f}s"
        
        if self.optimization_issues:
            summary += f", {len(self.optimization_issues)} issues"
        
        return summary


@dataclass
class TimingOptimizationResult(OptimizationResult):
    """Specialized results for target timing optimization"""
    # Timing-specific metrics
    target_trigger_hours: float
    tolerance_hours: float
    achieved_trigger_hours: Optional[float]
    timing_accuracy_hours: Optional[float]
    within_tolerance: bool
    
    # Timing optimization details
    timing_search_iterations: int
    timing_convergence_achieved: bool
    final_timing_error: float
    
    def get_timing_summary(self) -> str:
        """Get timing-specific summary"""
        if self.achieved_trigger_hours is not None:
            accuracy = abs(self.achieved_trigger_hours - self.target_trigger_hours)
            status = "✅ ON TARGET" if self.within_tolerance else "⚠️ OFF TARGET"
            
            return (f"{status} {self.action}: target {self.target_trigger_hours:.2f}h, "
                   f"achieved {self.achieved_trigger_hours:.2f}h "
                   f"(±{accuracy:.3f}h)")
        else:
            return f"❌ FAILED {self.action}: no trigger detected"


@dataclass
class BatchOptimizationResult:
    """Results from batch optimization of multiple actions"""
    batch_timestamp: str
    optimization_goal: str
    total_actions: int
    successful_optimizations: int
    failed_optimizations: int
    total_optimization_time_seconds: float
    
    # Individual results
    individual_results: List[OptimizationResult]
    
    # Batch metrics
    average_improvement: float
    best_performing_action: Optional[str]
    worst_performing_action: Optional[str]
    
    # Batch issues
    batch_issues: List[str]
    batch_warnings: List[str]
    
    def get_success_rate(self) -> float:
        """Get batch optimization success rate"""
        if self.total_actions == 0:
            return 0.0
        return self.successful_optimizations / self.total_actions
    
    def get_batch_summary(self) -> str:
        """Get batch optimization summary"""
        success_rate = self.get_success_rate() * 100
        avg_time = self.total_optimization_time_seconds / self.total_actions if self.total_actions > 0 else 0
        
        return (f"Batch optimization: {self.successful_optimizations}/{self.total_actions} successful "
               f"({success_rate:.1f}%), avg {avg_time:.1f}s per action")
    
    def get_results_by_action(self, action: str) -> List[OptimizationResult]:
        """Get all results for a specific action"""
        return [r for r in self.individual_results if r.action == action]
    
    def get_successful_results(self) -> List[OptimizationResult]:
        """Get all successful optimization results"""
        return [r for r in self.individual_results if r.improvement_achieved]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class OptimizationResultsCollection:
    """Collection of optimization results with analysis capabilities"""
    
    def __init__(self):
        self.results: List[OptimizationResult] = []
        self.created_time = time.time()
    
    def add_result(self, result: OptimizationResult):
        """Add an optimization result to the collection"""
        self.results.append(result)
    
    def get_results_by_action(self, action: str) -> List[OptimizationResult]:
        """Get all results for a specific action"""
        return [r for r in self.results if r.action == action]
    
    def get_results_by_goal(self, goal: str) -> List[OptimizationResult]:
        """Get all results for a specific optimization goal"""
        return [r for r in self.results if r.optimization_goal == goal]
    
    def get_success_rate(self) -> float:
        """Get overall optimization success rate"""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.improvement_achieved) / len(self.results)
    
    def get_average_improvement(self) -> float:
        """Get average improvement across all optimizations"""
        successful_results = [r for r in self.results if r.improvement_achieved]
        if not successful_results:
            return 0.0
        
        # Calculate average improvement based on optimization goal
        improvements = []
        for result in successful_results:
            if 'timing_accuracy' in result.improvement_metrics:
                improvements.append(result.improvement_metrics['timing_accuracy'])
            elif 'performance_improvement' in result.improvement_metrics:
                improvements.append(result.improvement_metrics['performance_improvement'])
        
        return sum(improvements) / len(improvements) if improvements else 0.0
    
    def get_timing_results(self) -> List[TimingOptimizationResult]:
        """Get all timing optimization results"""
        return [r for r in self.results if isinstance(r, TimingOptimizationResult)]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the collection"""
        timing_results = self.get_timing_results()
        
        return {
            'total_optimizations': len(self.results),
            'success_rate': self.get_success_rate(),
            'average_improvement': self.get_average_improvement(),
            'timing_optimizations': len(timing_results),
            'actions_optimized': len(set(r.action for r in self.results)),
            'optimization_goals': len(set(r.optimization_goal for r in self.results)),
            'total_optimization_time': sum(r.optimization_time_seconds for r in self.results),
            'average_iterations': sum(r.optimization_iterations for r in self.results) / len(self.results) if self.results else 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary for JSON serialization"""
        return {
            'created_time': self.created_time,
            'summary_stats': self.get_summary_stats(),
            'results': [r.to_dict() for r in self.results]
        }


def create_timing_optimization_result(action: str, scenario_profile: str,
                                    target_trigger_hours: float, tolerance_hours: float,
                                    achieved_trigger_hours: Optional[float],
                                    baseline_ics: Dict[str, Any], optimized_ics: Dict[str, Any],
                                    optimization_iterations: int, optimization_time_seconds: float,
                                    baseline_config_path: str = None, optimized_config_path: str = None,
                                    optimization_report_path: str = None) -> TimingOptimizationResult:
    """Factory function to create timing optimization results"""
    
    # Calculate timing metrics
    timing_accuracy_hours = None
    within_tolerance = False
    final_timing_error = float('inf')
    
    if achieved_trigger_hours is not None:
        timing_accuracy_hours = abs(achieved_trigger_hours - target_trigger_hours)
        within_tolerance = timing_accuracy_hours <= tolerance_hours
        final_timing_error = timing_accuracy_hours
    
    # Calculate improvement metrics
    improvement_achieved = within_tolerance
    improvement_metrics = {
        'timing_accuracy': timing_accuracy_hours if timing_accuracy_hours else 0.0,
        'within_tolerance': within_tolerance,
        'timing_improvement': 1.0 - (final_timing_error / target_trigger_hours) if target_trigger_hours > 0 else 0.0
    }
    
    # Performance comparison
    baseline_performance = {'trigger_time_hours': target_trigger_hours}  # Expected baseline
    optimized_performance = {'trigger_time_hours': achieved_trigger_hours if achieved_trigger_hours else 0.0}
    
    return TimingOptimizationResult(
        action=action,
        scenario_profile=scenario_profile,
        optimization_goal="target_timing",
        optimization_timestamp=datetime.now().isoformat(),
        baseline_config_path=baseline_config_path,
        optimized_config_path=optimized_config_path,
        optimization_report_path=optimization_report_path,
        baseline_ics=baseline_ics,
        optimized_ics=optimized_ics,
        optimization_iterations=optimization_iterations,
        optimization_time_seconds=optimization_time_seconds,
        improvement_achieved=improvement_achieved,
        baseline_performance=baseline_performance,
        optimized_performance=optimized_performance,
        improvement_metrics=improvement_metrics,
        optimization_issues=[],
        optimization_warnings=[],
        target_trigger_hours=target_trigger_hours,
        tolerance_hours=tolerance_hours,
        achieved_trigger_hours=achieved_trigger_hours,
        timing_accuracy_hours=timing_accuracy_hours,
        within_tolerance=within_tolerance,
        timing_search_iterations=optimization_iterations,
        timing_convergence_achieved=within_tolerance,
        final_timing_error=final_timing_error
    )
