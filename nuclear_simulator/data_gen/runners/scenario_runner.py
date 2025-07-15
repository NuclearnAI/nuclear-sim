#!/usr/bin/env python
"""
Unified Scenario Generator and Runner

This script provides a unified interface to generate and run nuclear plant scenarios
using both the maintenance-targeted ComprehensiveComposer and operational ScenarioGenerator.

Features:
- Generate maintenance-targeted scenarios for specific actions
- Generate operational scenarios (power ramps, emergency scenarios, etc.)
- Run single scenarios or batch processing
- Export results and generate visualizations
- CLI interface with interactive and batch modes
"""

import argparse
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent  # Go up two levels to get to data_gen/
sys.path.insert(0, str(project_root))

# Import composer and scenario generation
from config_engine.composers.comprehensive_composer import (
    ComprehensiveComposer,
    create_action_test_config,
    save_action_test_config
)
# Note: scenarios module removed - operational scenarios functionality disabled

# Import simulation infrastructure
from runners.maintenance_scenario_runner import MaintenanceScenarioRunner
from simulator.core.sim import NuclearPlantSimulator

# No longer import maintenance actions - use conditions files only


class ScenarioRunner:
    """
    Unified scenario generation and execution system
    """
    
    def __init__(self, output_dir: Optional[str] = None, verbose: bool = True, enable_plotting: bool = True):
        """
        Initialize the scenario runner
        
        Args:
            output_dir: Directory for output files (default: simulation_runs)
            verbose: Enable verbose output
            enable_plotting: Enable plot creation and display
        """
        self.verbose = verbose
        self.enable_plotting = enable_plotting
        self.output_dir = Path(output_dir) if output_dir else Path("simulation_runs")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize composers
        self.maintenance_composer = ComprehensiveComposer()
        # Note: scenario_generator removed - operational scenarios functionality disabled
        
        # Track results
        self.results = []
        
        if self.verbose:
            print("🚀 Scenario Runner Initialized")
            print(f"   📁 Output directory: {self.output_dir}")
            print(f"   🔧 Maintenance actions available: {len(self.maintenance_composer.list_available_actions())}")
    
    def generate_maintenance_scenario(
        self,
        action: str,
        duration_hours: float = 2.0,
        aggressive_mode: bool = True,
        plant_name: Optional[str] = None,
        randomize: bool = False,
        randomization_seed: Optional[int] = None,
        randomization_factor: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate a maintenance-targeted scenario configuration
        
        Args:
            action: Maintenance action to target (e.g., "oil_top_off")
            duration_hours: Simulation duration in hours
            aggressive_mode: Use aggressive thresholds for reliable triggering
            plant_name: Optional plant name override
            
        Returns:
            Complete configuration dictionary
        """
        if self.verbose:
            print(f"🔧 Generating maintenance scenario for: {action}")
        
        try:
            # Determine target subsystem for the action
            target_subsystem = self.maintenance_composer.action_subsystem_map.get(action)
            if not target_subsystem:
                raise ValueError(f"Unknown action: {action}")
            
            # Use the simplified API (no subsystem modes needed)
            config = self.maintenance_composer.compose_action_test_scenario(
                target_action=action,
                duration_hours=duration_hours,
                plant_name=plant_name,
                randomize=randomize,
                randomization_seed=randomization_seed,
                randomization_factor=randomization_factor
            )
            
            if self.verbose:
                print(f"   ✅ Generated config with {len(config)} sections")
                print(f"   🎯 Target subsystem: {config['metadata']['target_subsystem']}")
            
            return config
            
        except Exception as e:
            print(f"   ❌ Error generating maintenance scenario: {e}")
            raise
    
    def generate_combined_maintenance_scenario(
        self,
        actions: List[str],
        duration_hours: float = 2.0,
        aggressive_mode: bool = True,
        plant_name: Optional[str] = None,
        randomize: bool = False,
        randomization_seed: Optional[int] = None,
        randomization_factor: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate a combined maintenance scenario from multiple actions
        
        Args:
            actions: List of maintenance actions to combine
            duration_hours: Simulation duration in hours
            aggressive_mode: Use aggressive thresholds for reliable triggering
            plant_name: Optional plant name override
            randomize: Enable randomization of initial conditions
            randomization_seed: Base random seed (different seeds used for each action)
            randomization_factor: Randomization factor for parameter variation
            
        Returns:
            Complete configuration dictionary with averaged initial conditions
        """
        if self.verbose:
            print(f"🔧 Generating combined maintenance scenario for: {actions}")
        
        try:
            # 1. Get initial conditions for each action with different seeds
            individual_conditions = []
            for i, action in enumerate(actions):
                action_seed = randomization_seed + i if randomization_seed else None
                conditions = self._get_action_initial_conditions(
                    action, randomize, action_seed, randomization_factor
                )
                individual_conditions.append(conditions)
                
                if self.verbose:
                    print(f"   📋 Action {i+1}/{len(actions)} ({action}): {len(conditions)} parameters")
            
            # 2. Average overlapping parameters
            averaged_conditions = self._average_initial_conditions(individual_conditions)
            
            if self.verbose:
                print(f"   🔀 Averaged conditions: {len(averaged_conditions)} parameters")
            
            # 3. Create combined configuration using averaged conditions
            combined_config = self._create_combined_config(
                actions, averaged_conditions, duration_hours, plant_name
            )
            
            if self.verbose:
                print(f"   ✅ Generated combined config with {len(combined_config)} sections")
                print(f"   🎯 Target actions: {actions}")
            
            return combined_config
            
        except Exception as e:
            print(f"   ❌ Error generating combined maintenance scenario: {e}")
            raise
    
    def _get_action_initial_conditions(
        self,
        action: str,
        randomize: bool,
        seed: Optional[int],
        factor: float
    ) -> Dict[str, Any]:
        """
        Get initial conditions for a specific action
        
        Args:
            action: Maintenance action name
            randomize: Whether to apply randomization
            seed: Random seed for reproducibility
            factor: Randomization factor
            
        Returns:
            Dictionary of initial conditions for this action
        """
        target_subsystem = self.maintenance_composer.action_subsystem_map.get(action)
        if not target_subsystem:
            raise ValueError(f"Unknown action: {action}")
        
        if randomize:
            # Get randomized conditions directly from the randomization functions
            if target_subsystem == "feedwater":
                from config_engine.initial_conditions.feedwater_conditions import get_randomized_feedwater_conditions
                conditions = get_randomized_feedwater_conditions(action, seed, factor)
            elif target_subsystem == "turbine":
                from config_engine.initial_conditions.turbine_conditions import get_randomized_turbine_conditions
                conditions = get_randomized_turbine_conditions(action, seed, factor)
            elif target_subsystem == "steam_generator":
                from config_engine.initial_conditions.steam_generator_conditions import get_randomized_sg_conditions
                conditions = get_randomized_sg_conditions(action, seed, factor)
            else:
                # Fallback to base conditions if randomization not supported
                conditions = self.maintenance_composer.initial_conditions_catalog.get_conditions(target_subsystem, action)
        else:
            # Get base conditions directly from catalog
            conditions = self.maintenance_composer.initial_conditions_catalog.get_conditions(target_subsystem, action)
        
        if not conditions:
            raise ValueError(f"No conditions found for {target_subsystem}.{action}")
        
        # Filter out metadata fields, keep only actual IC parameters
        ic_params = {k: v for k, v in conditions.items() 
                     if k not in ['description', 'expected_action', 'target_pump', 'physics_calculation', 'physics_notes']}
        
        return ic_params
    
    def _average_initial_conditions(self, conditions_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Average overlapping initial condition parameters from multiple actions
        
        Args:
            conditions_list: List of initial condition dictionaries from different actions
            
        Returns:
            Dictionary with averaged overlapping parameters and unique parameters
        """
        averaged = {}
        
        # Get all unique parameter names across all actions
        all_params = set()
        for conditions in conditions_list:
            all_params.update(conditions.keys())
        
        # For each parameter, check if multiple actions set it
        for param in all_params:
            values = [cond[param] for cond in conditions_list if param in cond]
            
            if len(values) == 1:
                # Only one action sets this parameter - use it directly
                averaged[param] = values[0]
            else:
                # Multiple actions set this parameter - average them
                averaged[param] = self._average_parameter_values(values)
        
        return averaged
    
    def _average_parameter_values(self, values: List[Any]) -> Any:
        """
        Average parameter values based on their type
        
        Args:
            values: List of parameter values to average
            
        Returns:
            Averaged value
        """
        if all(isinstance(v, (int, float)) for v in values):
            # Numeric values - arithmetic mean
            return sum(values) / len(values)
        elif all(isinstance(v, list) for v in values):
            # Array values - element-wise averaging
            return self._average_arrays(values)
        elif all(isinstance(v, bool) for v in values):
            # Boolean values - logical OR (if any action needs it true)
            return any(values)
        else:
            # Fallback - use first value
            return values[0]
    
    def _average_arrays(self, arrays: List[List]) -> List:
        """
        Element-wise averaging for array parameters
        
        Args:
            arrays: List of arrays to average
            
        Returns:
            Array with averaged elements
        """
        if not arrays or not arrays[0]:
            return []
        
        max_length = max(len(arr) for arr in arrays)
        averaged = []
        
        for i in range(max_length):
            element_values = [arr[i] for arr in arrays if i < len(arr)]
            if all(isinstance(v, (int, float)) for v in element_values):
                averaged.append(sum(element_values) / len(element_values))
            else:
                averaged.append(element_values[0])  # Fallback to first value
        
        return averaged
    
    def _create_combined_config(
        self,
        actions: List[str],
        averaged_conditions: Dict[str, Any],
        duration_hours: float,
        plant_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        Create a combined configuration using averaged initial conditions
        
        Args:
            actions: List of actions being combined
            averaged_conditions: Averaged initial conditions
            duration_hours: Simulation duration
            plant_name: Optional plant name
            
        Returns:
            Complete configuration dictionary
        """
        # Start with the base template
        import copy
        config = copy.deepcopy(self.maintenance_composer.base_config)
        
        # Update plant identification
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        primary_action = actions[0]
        
        if plant_name is None:
            plant_name = f"Multi-Action Test Plant ({len(actions)} actions)"
        
        plant_id = f"MULTI-ACTION-{len(actions)}-{timestamp}"
        
        config['plant_name'] = plant_name
        config['plant_id'] = plant_id
        config['description'] = f"Combined maintenance test scenario for actions: {', '.join(actions)}"
        
        # Update simulation configuration
        config['simulation_config']['duration_hours'] = duration_hours
        config['simulation_config']['scenario'] = f"multi_action_{len(actions)}_test"
        
        # Add load profile for the combined scenario
        if 'load_profiles' not in config:
            config['load_profiles'] = {'profiles': {}}
        
        config['load_profiles']['profiles'][f"multi_action_{len(actions)}_test"] = {
            'type': 'steady_with_noise',
            'base_power_percent': 90.0,
            'noise_std_percent': 2.0,
            'description': f"Steady operation for multi-action testing: {', '.join(actions)}"
        }
        
        # Apply averaged initial conditions to the appropriate subsystem
        # For now, assume all actions are from the same subsystem (feedwater)
        # This can be enhanced later to handle cross-subsystem scenarios
        primary_subsystem = self.maintenance_composer.action_subsystem_map.get(primary_action)
        if primary_subsystem and primary_subsystem in config.get('secondary_system', {}):
            subsystem_config = config['secondary_system'][primary_subsystem]
            if 'initial_conditions' in subsystem_config:
                initial_conditions = subsystem_config['initial_conditions']
                
                # Apply averaged conditions
                applied_count = 0
                for param, value in averaged_conditions.items():
                    if param in initial_conditions:
                        initial_conditions[param] = value
                        applied_count += 1
                
                if self.verbose:
                    print(f"   ✅ Applied {applied_count} averaged parameters to {primary_subsystem}")
        
        # Update metadata
        config['metadata'] = {
            'created_date': datetime.now().strftime("%Y-%m-%d"),
            'created_by': "Multi-Action Maintenance Composer",
            'configuration_type': "multi_action_maintenance_test",
            'target_action': primary_action,  # Required by MaintenanceScenarioRunner
            'target_actions': actions,  # Additional field for multi-action info
            'primary_target_action': primary_action,
            'target_subsystem': primary_subsystem,
            'validation_status': "generated",
            'last_modified': datetime.now().strftime("%Y-%m-%d"),
            'version_notes': f"Generated for testing {len(actions)} combined actions with averaged initial conditions",
            'base_template': "nuclear_plant_comprehensive_config.yaml",
            'state_manager_integration': True,
            'maintenance_monitoring_enabled': True,
            'threshold_verification_enabled': True
        }
        
        return config
    
    def generate_operational_scenario(
        self,
        scenario_type: Union[str, Any],
        duration_hours: float = 2.0,
        **kwargs
    ) -> Any:
        """
        Generate an operational scenario - DISABLED
        
        Args:
            scenario_type: Type of scenario to generate
            duration_hours: Simulation duration in hours
            **kwargs: Additional parameters for scenario generation
            
        Returns:
            None - functionality disabled
        """
        raise NotImplementedError("Operational scenario generation is disabled - scenarios module not available")
    
    def run_maintenance_scenario(
        self,
        actions: Union[str, List[str]],
        duration_hours: float = 2.0,
        aggressive_mode: bool = True,
        save_config: bool = True,
        tracking_start_hours: float = 0.0,
        randomize: bool = False,
        randomization_seed: Optional[int] = None,
        randomization_factor: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate and run a maintenance-targeted scenario
        
        Args:
            actions: Maintenance action(s) to target - single string or list of strings
            duration_hours: Simulation duration in hours
            aggressive_mode: Use aggressive thresholds
            save_config: Save the generated configuration
            tracking_start_hours: Start time for CSV data tracking (hours). Data before this time will not be saved to CSVs.
            randomize: Enable randomization of initial conditions
            randomization_seed: Random seed for reproducibility (different seeds used for each action)
            randomization_factor: Randomization factor for parameter variation
            
        Returns:
            Simulation results
        """
        # Convert single action to list for uniform processing (backward compatibility)
        if isinstance(actions, str):
            actions = [actions]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        primary_action = actions[0]  # Use first action for naming
        if len(actions) == 1:
            run_name = f"{primary_action}_{timestamp}"
        else:
            run_name = f"multi_action_{len(actions)}_{timestamp}"
        
        if self.verbose:
            if len(actions) == 1:
                print(f"\n🎯 Running Maintenance Scenario: {primary_action}")
            else:
                print(f"\n🎯 Running Multi-Action Maintenance Scenario: {actions}")
            print("=" * 60)
        
        # Generate configuration (single or combined)
        if len(actions) == 1:
            # Single action - use existing method
            config = self.generate_maintenance_scenario(
                action=primary_action,
                duration_hours=duration_hours,
                aggressive_mode=aggressive_mode,
                randomize=randomize,
                randomization_seed=randomization_seed,
                randomization_factor=randomization_factor
            )
        else:
            # Multiple actions - use new combined method
            config = self.generate_combined_maintenance_scenario(
                actions=actions,
                duration_hours=duration_hours,
                aggressive_mode=aggressive_mode,
                randomize=randomize,
                randomization_seed=randomization_seed,
                randomization_factor=randomization_factor
            )
        
        # Save configuration if requested
        config_file = None
        if save_config:
            config_file = self.output_dir / f"{run_name}_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
            if self.verbose:
                print(f"   💾 Saved config: {config_file}")
        
        # Create run directory
        run_dir = self.output_dir / run_name
        run_dir.mkdir(exist_ok=True)
        
        # Run simulation using our custom MaintenanceScenarioRunner
        try:
            # Change to run directory for simulation
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(run_dir)
                
                # Create our custom simulation runner
                simulation = MaintenanceScenarioRunner(config, verbose=self.verbose, enable_plotting=self.enable_plotting)
                
                # Set tracking start time for CSV filtering
                simulation.tracking_start_hours = tracking_start_hours
                
                # Run simulation
                start_time = time.time()
                sim_results = simulation.run_scenario()
                end_time = time.time()
                
                # Generate outputs
                simulation.create_plots(save_plots=True)
                simulation.export_data(filename_prefix=run_name)
                
                # Collect results
                results = {
                    'run_name': run_name,
                    'actions': actions,  # List of actions
                    'primary_action': primary_action,  # First action for backward compatibility
                    'action': primary_action,  # Backward compatibility
                    'duration_hours': duration_hours,
                    'aggressive_mode': aggressive_mode,
                    'execution_time_seconds': end_time - start_time,
                    'config_file': str(config_file) if config_file else None,
                    'run_directory': str(run_dir),
                    'success': sim_results['success'],
                    'work_orders_created': sim_results['work_orders_created'],
                    'maintenance_events': sim_results['maintenance_events'],
                    'simulation_data_points': sim_results['simulation_data_points'],
                    'final_power_level': sim_results['final_power_level']
                }
                
                # Add work order details for compatibility
                results['work_orders'] = {
                    'completed': sim_results['work_orders_created'],
                    'active': 0,
                    'total_created': sim_results['work_orders_created']
                }
                
                self.results.append(results)
                
                if self.verbose:
                    self._print_maintenance_results(results, simulation)
                
                return results, run_name
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            print(f"   ❌ Error running simulation: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def run_operational_scenario(
        self,
        scenario_type: Union[str, Any],
        duration_hours: float = 2.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate and run an operational scenario - DISABLED
        
        Args:
            scenario_type: Type of scenario to generate
            duration_hours: Simulation duration in hours
            **kwargs: Additional parameters for scenario generation
            
        Returns:
            Simulation results
        """
        raise NotImplementedError("Operational scenario execution is disabled - scenarios module not available")
    
    def run_batch_maintenance(
        self,
        actions: List[str],
        duration_hours: float = 2.0,
        count_per_action: int = 1,
        aggressive_mode: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Run multiple maintenance scenarios in batch
        
        Args:
            actions: List of maintenance actions to test
            duration_hours: Simulation duration for each run
            count_per_action: Number of runs per action
            aggressive_mode: Use aggressive thresholds
            
        Returns:
            List of results for all runs
        """
        if self.verbose:
            print(f"\n🔄 Running Batch Maintenance Scenarios")
            print("=" * 60)
            print(f"   Actions: {len(actions)}")
            print(f"   Runs per action: {count_per_action}")
            print(f"   Total runs: {len(actions) * count_per_action}")
        
        batch_results = []
        total_runs = len(actions) * count_per_action
        current_run = 0
        
        for action in actions:
            for run_idx in range(count_per_action):
                current_run += 1
                if self.verbose:
                    print(f"\n[{current_run}/{total_runs}] Running {action} (run {run_idx + 1})")
                
                try:
                    result = self.run_maintenance_scenario(
                        action=action,
                        duration_hours=duration_hours,
                        aggressive_mode=aggressive_mode
                    )
                    batch_results.append(result)
                    
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
                    # Continue with next run
                    continue
        
        if self.verbose:
            self._print_batch_summary(batch_results)
        
        return batch_results
    
    def run_from_yaml_file(
        self,
        yaml_path: Union[str, Path],
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        PHASE 2: Run scenario from YAML configuration file
        
        Args:
            yaml_path: Path to YAML configuration file
            save_results: Save results and plots
            
        Returns:
            Simulation results dictionary
        """
        yaml_path = Path(yaml_path)
        
        if self.verbose:
            print(f"\n📄 Running scenario from YAML file: {yaml_path}")
            print("=" * 60)
        
        try:
            # Create MaintenanceScenarioRunner with YAML file
            simulation = MaintenanceScenarioRunner(yaml_path, verbose=self.verbose)
            
            # Extract metadata for result tracking
            target_action = simulation.target_action
            target_subsystem = simulation.target_subsystem
            duration_hours = simulation.duration_hours
            
            # Create run directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"{target_action}_yaml_{timestamp}"
            run_dir = self.output_dir / run_name
            run_dir.mkdir(exist_ok=True)
            
            # Change to run directory for simulation
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(run_dir)
                
                # Run simulation
                start_time = time.time()
                sim_results = simulation.run_scenario()
                end_time = time.time()
                
                if save_results:
                    # Generate outputs
                    simulation.create_plots(save_plots=True)
                    simulation.export_data(filename_prefix=run_name)
                
                # Collect results
                results = {
                    'run_name': run_name,
                    'yaml_file': str(yaml_path),
                    'target_action': target_action,
                    'target_subsystem': target_subsystem,
                    'duration_hours': duration_hours,
                    'execution_time_seconds': end_time - start_time,
                    'run_directory': str(run_dir),
                    'success': sim_results['success'],
                    'work_orders_created': sim_results['work_orders_created'],
                    'work_orders_executed': sim_results['work_orders_executed'],
                    'maintenance_events': sim_results['maintenance_events'],
                    'simulation_data_points': sim_results['simulation_data_points'],
                    'final_power_level': sim_results['final_power_level']
                }
                
                # Add work order details for compatibility
                results['work_orders'] = {
                    'completed': sim_results['work_orders_executed'],
                    'active': 0,
                    'total_created': sim_results['work_orders_created']
                }
                
                self.results.append(results)
                
                if self.verbose:
                    self._print_yaml_results(results, simulation)
                
                return results
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            print(f"   ❌ Error running YAML scenario: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def run_batch_from_yaml_directory(
        self,
        yaml_dir: Union[str, Path],
        pattern: str = "*.yaml",
        save_results: bool = True
    ) -> List[Dict[str, Any]]:
        """
        PHASE 2: Run multiple scenarios from YAML files in a directory
        
        Args:
            yaml_dir: Directory containing YAML files
            pattern: File pattern to match (default: "*.yaml")
            save_results: Save results and plots for each scenario
            
        Returns:
            List of results for all scenarios
        """
        yaml_dir = Path(yaml_dir)
        
        if not yaml_dir.exists():
            raise FileNotFoundError(f"YAML directory not found: {yaml_dir}")
        
        # Find YAML files
        yaml_files = list(yaml_dir.glob(pattern))
        if not yaml_files:
            print(f"⚠️ No YAML files found in {yaml_dir} matching pattern '{pattern}'")
            return []
        
        if self.verbose:
            print(f"\n📁 Running batch scenarios from YAML directory: {yaml_dir}")
            print("=" * 70)
            print(f"   Pattern: {pattern}")
            print(f"   Files found: {len(yaml_files)}")
            print(f"   Save results: {save_results}")
        
        batch_results = []
        
        for i, yaml_file in enumerate(yaml_files, 1):
            if self.verbose:
                print(f"\n[{i}/{len(yaml_files)}] Processing: {yaml_file.name}")
            
            try:
                result = self.run_from_yaml_file(yaml_file, save_results=save_results)
                batch_results.append(result)
                
            except Exception as e:
                print(f"   ❌ Failed to process {yaml_file.name}: {e}")
                # Continue with next file
                continue
        
        if self.verbose:
            self._print_yaml_batch_summary(batch_results, yaml_dir)
        
        return batch_results
    
    def validate_yaml_config(self, yaml_path: Union[str, Path]) -> bool:
        """
        PHASE 2: Validate YAML configuration without running simulation
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            True if valid, False otherwise
        """
        yaml_path = Path(yaml_path)
        
        if self.verbose:
            print(f"\n🔍 Validating YAML configuration: {yaml_path}")
        
        try:
            # Try to create MaintenanceScenarioRunner (validation happens in constructor)
            simulation = MaintenanceScenarioRunner(yaml_path, verbose=False)
            
            if self.verbose:
                print(f"   ✅ YAML configuration is valid")
                print(f"   🎯 Target action: {simulation.target_action}")
                print(f"   🏭 Target subsystem: {simulation.target_subsystem}")
                print(f"   ⏱️ Duration: {simulation.duration_hours} hours")
            
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"   ❌ YAML configuration is invalid: {e}")
            return False
    
    def _print_yaml_results(self, results: Dict[str, Any], simulation: MaintenanceScenarioRunner):
        """Print YAML scenario results"""
        print(f"\n📋 YAML Scenario Results")
        print("-" * 40)
        print(f"   📄 YAML file: {Path(results['yaml_file']).name}")
        print(f"   ⏱️ Execution time: {results['execution_time_seconds']:.1f}s")
        print(f"   📁 Output directory: {results['run_directory']}")
        print(f"   ✅ Success: {results['success']}")
        print(f"   🔧 Work orders created: {results['work_orders']['total_created']}")
        print(f"   ✅ Work orders completed: {results['work_orders']['completed']}")
        print(f"   📊 Data points: {results['simulation_data_points']}")
        print(f"   📊 Maintenance events: {results['maintenance_events']}")
        print(f"   ⚡ Final power: {results['final_power_level']:.1f}%")
    
    def _print_yaml_batch_summary(self, batch_results: List[Dict[str, Any]], yaml_dir: Path):
        """Print YAML batch execution summary"""
        print(f"\n📊 YAML Batch Summary")
        print("=" * 50)
        print(f"   📁 Directory: {yaml_dir}")
        print(f"   📄 Total YAML files processed: {len(batch_results)}")
        
        if batch_results:
            successful_runs = sum(1 for r in batch_results if r.get('success', False))
            print(f"   ✅ Successful runs: {successful_runs}/{len(batch_results)} ({successful_runs/len(batch_results):.1%})")
            
            total_work_orders = sum(r.get('work_orders', {}).get('total_created', 0) for r in batch_results)
            print(f"   🔧 Total work orders: {total_work_orders}")
            
            avg_execution_time = sum(r['execution_time_seconds'] for r in batch_results) / len(batch_results)
            print(f"   ⏱️ Average execution time: {avg_execution_time:.1f}s")
            
            # Show top performing scenarios
            print(f"\n🏆 Top Performing Scenarios:")
            sorted_results = sorted(batch_results, key=lambda r: r.get('work_orders', {}).get('total_created', 0), reverse=True)
            for i, result in enumerate(sorted_results[:3]):
                wo_count = result.get('work_orders', {}).get('total_created', 0)
                yaml_name = Path(result['yaml_file']).name
                print(f"   {i+1}. {yaml_name}: {wo_count} work orders")
    
    def run_all_actions(
        self,
        duration_hours: float = 2.0,
        count_per_action: int = 1,
        aggressive_mode: bool = True,
        subsystem_filter: Optional[str] = None,
        exclude_actions: Optional[List[str]] = None,
        parallel: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run ALL available maintenance actions
        
        Args:
            duration_hours: Simulation duration for each run
            count_per_action: Number of runs per action
            aggressive_mode: Use aggressive thresholds
            subsystem_filter: Only run actions for specific subsystem
            exclude_actions: List of actions to skip
            parallel: Run actions in parallel (future enhancement)
            
        Returns:
            List of results for all runs
        """
        # Get all available actions
        all_actions = self.list_available_actions()
        
        # Apply subsystem filter if specified
        if subsystem_filter:
            all_actions = self.get_actions_by_subsystem(subsystem_filter)
            if not all_actions:
                print(f"❌ No actions found for subsystem: {subsystem_filter}")
                return []
        
        # Apply exclusions if specified
        if exclude_actions:
            all_actions = [action for action in all_actions if action not in exclude_actions]
        
        if self.verbose:
            print(f"\n🚀 Running ALL Available Maintenance Actions")
            print("=" * 70)
            print(f"   Total actions available: {len(self.list_available_actions())}")
            if subsystem_filter:
                print(f"   Filtered to subsystem: {subsystem_filter}")
            if exclude_actions:
                print(f"   Excluded actions: {len(exclude_actions)}")
            print(f"   Actions to run: {len(all_actions)}")
            print(f"   Runs per action: {count_per_action}")
            print(f"   Total runs: {len(all_actions) * count_per_action}")
            print(f"   Estimated duration: {len(all_actions) * count_per_action * duration_hours:.1f} simulation hours")
            
            # Show actions by subsystem
            print(f"\n📋 Actions by Subsystem:")
            for subsystem in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
                subsystem_actions = [a for a in all_actions if a in self.get_actions_by_subsystem(subsystem)]
                if subsystem_actions:
                    print(f"   {subsystem.upper()}: {len(subsystem_actions)} actions")
        
        # Confirm with user for large runs
        if len(all_actions) * count_per_action > 20 and self.verbose:
            print(f"\n⚠️  This will run {len(all_actions) * count_per_action} total scenarios.")
            print("   This may take a significant amount of time.")
            response = input("   Continue? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("   Cancelled by user.")
                return []
        
        # Run all actions using batch processing
        start_time = time.time()
        results = self.run_batch_maintenance(
            actions=all_actions,
            duration_hours=duration_hours,
            count_per_action=count_per_action,
            aggressive_mode=aggressive_mode
        )
        end_time = time.time()
        
        # Generate comprehensive summary
        if self.verbose:
            self._print_all_actions_summary(results, all_actions, end_time - start_time)
        
        # Save comprehensive results
        self._save_all_actions_results(results, subsystem_filter, exclude_actions)
        
        return results
    
    def _print_all_actions_summary(self, results: List[Dict[str, Any]], 
                                 all_actions: List[str], total_time: float):
        """Print comprehensive summary for run-all-actions"""
        print(f"\n🎉 ALL ACTIONS COMPLETE")
        print("=" * 70)
        print(f"   Total execution time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        print(f"   Actions attempted: {len(all_actions)}")
        print(f"   Scenarios completed: {len(results)}")
        
        if results:
            # Success rate analysis
            successful_runs = sum(1 for r in results if r.get('success', False))
            triggered_runs = sum(1 for r in results if r.get('work_orders', {}).get('total_created', 0) > 0)
            
            print(f"   Success rate: {successful_runs}/{len(results)} ({successful_runs/len(results):.1%})")
            print(f"   Trigger rate: {triggered_runs}/{len(results)} ({triggered_runs/len(results):.1%})")
            
            # Work order statistics
            total_work_orders = sum(r.get('work_orders', {}).get('total_created', 0) for r in results)
            print(f"   Total work orders created: {total_work_orders}")
            
            # Performance statistics
            avg_execution_time = sum(r.get('execution_time_seconds', 0) for r in results) / len(results)
            print(f"   Average execution time per scenario: {avg_execution_time:.1f}s")
            
            # Subsystem breakdown
            print(f"\n📊 Results by Subsystem:")
            for subsystem in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
                subsystem_results = [r for r in results if r.get('action') in self.get_actions_by_subsystem(subsystem)]
                if subsystem_results:
                    subsystem_triggered = sum(1 for r in subsystem_results if r.get('work_orders', {}).get('total_created', 0) > 0)
                    subsystem_work_orders = sum(r.get('work_orders', {}).get('total_created', 0) for r in subsystem_results)
                    print(f"   {subsystem.upper()}: {len(subsystem_results)} runs, {subsystem_triggered} triggered, {subsystem_work_orders} work orders")
            
            # Top performing actions
            print(f"\n🏆 Top Performing Actions (Most Work Orders):")
            sorted_results = sorted(results, key=lambda r: r.get('work_orders', {}).get('total_created', 0), reverse=True)
            for i, result in enumerate(sorted_results[:5]):
                wo_count = result.get('work_orders', {}).get('total_created', 0)
                print(f"   {i+1}. {result.get('action', 'Unknown')}: {wo_count} work orders")
            
            # Failed actions
            failed_results = [r for r in results if not r.get('success', False)]
            if failed_results:
                print(f"\n⚠️  Failed Actions ({len(failed_results)}):")
                for result in failed_results[:5]:  # Show first 5
                    print(f"   • {result.get('action', 'Unknown')}")
                if len(failed_results) > 5:
                    print(f"   ... and {len(failed_results) - 5} more")
    
    def _save_all_actions_results(self, results: List[Dict[str, Any]], 
                                subsystem_filter: Optional[str], 
                                exclude_actions: Optional[List[str]]):
        """Save comprehensive results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create results directory
        results_dir = self.output_dir / f"all_actions_run_{timestamp}"
        results_dir.mkdir(exist_ok=True)
        
        # Save detailed results as JSON
        results_file = results_dir / "all_actions_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'metadata': {
                    'timestamp': timestamp,
                    'total_actions': len(results),
                    'subsystem_filter': subsystem_filter,
                    'excluded_actions': exclude_actions or [],
                    'generated_by': 'ScenarioRunner.run_all_actions'
                },
                'results': results
            }, f, indent=2)
        
        # Save summary CSV
        summary_file = results_dir / "all_actions_summary.csv"
        with open(summary_file, 'w') as f:
            f.write("action,subsystem,success,work_orders_created,execution_time_seconds,final_power_level\n")
            for result in results:
                action = result.get('action', '')
                # Determine subsystem
                subsystem = 'unknown'
                for sub in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
                    if action in self.get_actions_by_subsystem(sub):
                        subsystem = sub
                        break
                
                success = result.get('success', False)
                work_orders = result.get('work_orders', {}).get('total_created', 0)
                exec_time = result.get('execution_time_seconds', 0)
                final_power = result.get('final_power_level', 0)
                
                f.write(f"{action},{subsystem},{success},{work_orders},{exec_time:.1f},{final_power:.1f}\n")
        
        if self.verbose:
            print(f"\n💾 Comprehensive results saved:")
            print(f"   📄 Detailed results: {results_file}")
            print(f"   📊 Summary CSV: {summary_file}")
            print(f"   📁 Results directory: {results_dir}")
    
    def validate_action(self, action: str) -> bool:
        """Validate action against conditions files"""
        return action in self.maintenance_composer.list_available_actions()
    
    def suggest_similar_actions(self, invalid_action: str) -> List[str]:
        """Suggest similar valid actions for typos using fuzzy matching"""
        import difflib
        
        # Get all valid actions from conditions files
        valid_actions = self.maintenance_composer.list_available_actions()
        
        # Use difflib to find close matches
        suggestions = difflib.get_close_matches(
            invalid_action, 
            valid_actions, 
            n=3,  # Return up to 3 suggestions
            cutoff=0.6  # Minimum similarity threshold
        )
        
        return suggestions
    
    def list_available_actions(self) -> List[str]:
        """List all available maintenance actions from conditions files"""
        return self.maintenance_composer.list_available_actions()
    
    def list_available_scenarios(self) -> List[str]:
        """List all available operational scenario types - DISABLED"""
        return []  # Operational scenarios disabled - scenarios module not available
    
    def get_actions_by_subsystem(self, subsystem: str) -> List[str]:
        """Get maintenance actions for a specific subsystem from conditions files"""
        return self.maintenance_composer.get_actions_by_subsystem(subsystem)
    
    # Operational scenario helper methods disabled - scenarios module not available
    
    def _print_maintenance_results(self, results: Dict[str, Any], simulation: MaintenanceScenarioRunner):
        """Enhanced maintenance scenario results with state manager integration"""
        print(f"\n📋 Results Summary")
        print("-" * 40)
        print(f"   ⏱️ Execution time: {results['execution_time_seconds']:.1f}s")
        print(f"   📁 Output directory: {results['run_directory']}")
        print(f"   ✅ Success: {results['success']}")
        
        if 'work_orders' in results:
            wo = results['work_orders']
            print(f"   🔧 Work orders created: {wo['total_created']}")
            print(f"   ✅ Work orders completed: {wo['completed']}")
            print(f"   🔄 Work orders active: {wo['active']}")
        
        # NEW: Enhanced reporting with state manager data
        if hasattr(simulation, 'simulator') and hasattr(simulation.simulator, 'state_manager'):
            state_manager = simulation.simulator.state_manager
            
            # Show threshold violations
            violations = state_manager.get_current_threshold_violations()
            if violations:
                print(f"   🚨 Active threshold violations: {len(violations)}")
                for component_id, component_violations in violations.items():
                    for param, violation in component_violations.items():
                        print(f"      {component_id}.{param}: {violation.get('value', 'N/A'):.2f} {violation.get('comparison', '')} {violation.get('threshold', 'N/A')}")
            
            # Show maintenance history
            maintenance_history = state_manager.get_maintenance_history()
            if maintenance_history:
                print(f"   📝 Maintenance actions performed: {len(maintenance_history)}")
                for record in maintenance_history[-3:]:  # Show last 3
                    success_icon = "✅" if record.get('success', False) else "❌"
                    print(f"      {success_icon} {record.get('component_id', 'Unknown')}: {record.get('action_type', 'Unknown')}")
        
        # Show maintenance effectiveness if available
        if 'maintenance_effectiveness' in results:
            effectiveness = results['maintenance_effectiveness']
            if effectiveness.get('verifications_performed', 0) > 0:
                avg_eff = effectiveness.get('average_effectiveness', 0)
                print(f"   📊 Maintenance effectiveness: {avg_eff:.1%} ({effectiveness['successful_verifications']}/{effectiveness['verifications_performed']} verified)")
        
        print(f"   📊 Data points: {results['simulation_data_points']}")
        print(f"   📊 Maintenance events: {results['maintenance_events']}")
        print(f"   ⚡ Final power: {results['final_power_level']:.1f}%")
    
    def _print_operational_results(self, results: Dict[str, Any], simulation_result: Dict[str, Any]):
        """Print operational scenario results"""
        print(f"\n📋 Results Summary")
        print("-" * 40)
        print(f"   ⏱️ Execution time: {results['execution_time_seconds']:.1f}s")
        print(f"   📁 Output directory: {results['run_directory']}")
        print(f"   ✅ Success: {results['success']}")
        print(f"   📊 Data points: {results['data_points']}")
        print(f"   ⚡ Final power: {results['final_power_level']:.1f}%")
    
    def _print_batch_summary(self, batch_results: List[Dict[str, Any]]):
        """Print batch execution summary"""
        print(f"\n📊 Batch Summary")
        print("=" * 40)
        print(f"   Total runs: {len(batch_results)}")
        
        if batch_results:
            successful_runs = sum(1 for r in batch_results if r.get('work_orders', {}).get('total_created', 0) > 0)
            print(f"   Successful triggers: {successful_runs}/{len(batch_results)} ({successful_runs/len(batch_results):.1%})")
            
            total_work_orders = sum(r.get('work_orders', {}).get('total_created', 0) for r in batch_results)
            print(f"   Total work orders: {total_work_orders}")
            
            avg_execution_time = sum(r['execution_time_seconds'] for r in batch_results) / len(batch_results)
            print(f"   Average execution time: {avg_execution_time:.1f}s")


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Nuclear Plant Scenario Generator and Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single maintenance scenario
  python scenario_runner.py --action oil_top_off --duration 2.0
  
  # Run with randomization
  python scenario_runner.py --action oil_change --randomize --seed 42 --randomization-factor 0.1
  
  # Generate multiple randomized variants
  python scenario_runner.py --action oil_change --randomize --num-variants 5 --seed 42
  
  # MULTI-ACTION EXAMPLES (NEW):
  # Run multiple actions combined (parameter averaging)
  python scenario_runner.py --actions oil_change,pump_bearing_replacement --duration 2.0
  
  # Multi-action with randomization (different seeds per action)
  python scenario_runner.py --actions oil_change,seal_replacement --randomize --seed 42
  
  # Multi-action with multiple variants
  python scenario_runner.py --actions oil_change,motor_bearing_replacement --randomize --num-variants 3 --seed 42
  
  # Run an operational scenario
  python scenario_runner.py --scenario power_ramp_up --duration 1.5
  
  # Batch run multiple maintenance actions
  python scenario_runner.py --batch-maintenance --actions oil_top_off,tsp_chemical_cleaning --count 3
  
  # Run ALL available maintenance actions
  python scenario_runner.py --run-all-actions --duration 1.0
  
  # Run all actions for a specific subsystem
  python scenario_runner.py --run-all-actions --subsystem turbine --duration 1.5
  
  # Run all actions except specific ones
  python scenario_runner.py --run-all-actions --exclude-actions "oil_top_off,bearing_inspection"
  
  # Disable plotting for faster batch runs
  python scenario_runner.py --run-all-actions --no-plots --duration 1.0
  
  # YAML-FIRST EXAMPLES:
  # Run scenario from YAML file
  python scenario_runner.py --yaml-file my_scenario.yaml
  
  # Run all YAML files in directory
  python scenario_runner.py --yaml-dir ./scenarios/
  
  # Validate YAML without running
  python scenario_runner.py --validate-yaml my_scenario.yaml
  
  # List available actions
  python scenario_runner.py --list-actions
  
  # Interactive mode
  python scenario_runner.py --interactive
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--action', type=str, help='Run maintenance scenario for specific action')
    mode_group.add_argument('--actions', type=str, help='Run multi-action maintenance scenario (comma-separated list)')
    mode_group.add_argument('--scenario', type=str, help='Run operational scenario')
    mode_group.add_argument('--batch-maintenance', action='store_true', help='Run batch maintenance scenarios')
    mode_group.add_argument('--run-all-actions', action='store_true', help='Run ALL available maintenance actions')
    mode_group.add_argument('--yaml-file', type=str, help='PHASE 3: Run scenario from YAML configuration file')
    mode_group.add_argument('--yaml-dir', type=str, help='PHASE 3: Run all YAML files in directory')
    mode_group.add_argument('--validate-yaml', type=str, help='PHASE 3: Validate YAML configuration without running')
    mode_group.add_argument('--list-actions', action='store_true', help='List available maintenance actions')
    mode_group.add_argument('--list-scenarios', action='store_true', help='List available operational scenarios')
    mode_group.add_argument('--interactive', action='store_true', help='Interactive mode')
    
    # Common parameters
    parser.add_argument('--duration', type=float, default=2.0, help='Simulation duration in hours (default: 2.0)')
    parser.add_argument('--output-dir', type=str, help='Output directory (default: simulation_runs)')
    parser.add_argument('--verbose', action='store_true', default=True, help='Enable verbose output')
    parser.add_argument('--quiet', action='store_true', help='Disable verbose output')
    parser.add_argument('--no-plots', action='store_true', help='Disable plot creation and display')
    
    # Maintenance-specific parameters
    parser.add_argument('--count', type=int, default=1, help='Number of runs per action in batch mode')
    parser.add_argument('--aggressive', action='store_true', help='Use aggressive thresholds (default: conservative)')
    parser.add_argument('--tracking-start', type=float, default=0.0, help='Start time for CSV data tracking in hours. Data before this time will not be saved to CSVs (default: 0.0)')
    
    # Randomization parameters
    parser.add_argument('--randomize', action='store_true', help='Enable randomization of initial conditions')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--randomization-factor', type=float, default=0.1, help='Randomization factor (default: 0.1 = ±10%)')
    parser.add_argument('--num-variants', type=int, default=1, help='Number of randomized variants to generate (default: 1)')
    
    # Run-all-actions specific parameters
    parser.add_argument('--subsystem', type=str, choices=['steam_generator', 'turbine', 'feedwater', 'condenser'], 
                       help='Filter to specific subsystem for --run-all-actions')
    parser.add_argument('--exclude-actions', type=str, help='Comma-separated list of actions to exclude from --run-all-actions')
    
    # Operational scenario parameters
    parser.add_argument('--target-power', type=float, help='Target power for power ramp scenarios')
    
    return parser


def interactive_mode(runner: ScenarioRunner):
    """Run in interactive mode"""
    print("\n🎮 Interactive Scenario Runner")
    print("=" * 50)
    
    while True:
        print("\nSelect scenario type:")
        print("1. Maintenance scenario")
        print("2. Operational scenario")
        print("3. List available actions")
        print("4. List available scenarios")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            # Maintenance scenario
            actions = runner.list_available_actions()
            print(f"\nAvailable maintenance actions ({len(actions)}):")
            for i, action in enumerate(actions[:20], 1):  # Show first 20
                print(f"  {i:2d}. {action}")
            if len(actions) > 20:
                print(f"  ... and {len(actions) - 20} more")
            
            action_input = input("\nEnter action name or number: ").strip()
            
            # Handle numeric input
            if action_input.isdigit():
                action_idx = int(action_input) - 1
                if 0 <= action_idx < len(actions):
                    action = actions[action_idx]
                else:
                    print("Invalid action number")
                    continue
            else:
                action = action_input
                if action not in actions:
                    print("Invalid action name")
                    continue
            
            duration = float(input("Duration in hours (default 2.0): ") or "2.0")
            
            try:
                runner.run_maintenance_scenario(action, duration)
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '2':
            # Operational scenario
            scenarios = runner.list_available_scenarios()
            print(f"\nAvailable operational scenarios:")
            for i, scenario in enumerate(scenarios, 1):
                print(f"  {i:2d}. {scenario}")
            
            scenario_input = input("\nEnter scenario name or number: ").strip()
            
            # Handle numeric input
            if scenario_input.isdigit():
                scenario_idx = int(scenario_input) - 1
                if 0 <= scenario_idx < len(scenarios):
                    scenario = scenarios[scenario_idx]
                else:
                    print("Invalid scenario number")
                    continue
            else:
                scenario = scenario_input
                if scenario not in scenarios:
                    print("Invalid scenario name")
                    continue
            
            duration = float(input("Duration in hours (default 2.0): ") or "2.0")
            
            try:
                runner.run_operational_scenario(scenario, duration)
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '3':
            # List actions
            actions = runner.list_available_actions()
            print(f"\nAvailable maintenance actions ({len(actions)}):")
            
            # Group by subsystem
            for subsystem in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
                subsystem_actions = runner.get_actions_by_subsystem(subsystem)
                if subsystem_actions:
                    print(f"\n{subsystem.upper()}:")
                    for action in subsystem_actions:
                        print(f"  • {action}")
        
        elif choice == '4':
            # List scenarios
            scenarios = runner.list_available_scenarios()
            print(f"\nAvailable operational scenarios ({len(scenarios)}):")
            for scenario in scenarios:
                print(f"  • {scenario}")
        
        elif choice == '5':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice")


def main():
    """Main entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Handle verbose/quiet
    verbose = args.verbose and not args.quiet
    
    # Handle plotting flag
    enable_plotting = not args.no_plots
    
    # Initialize runner
    runner = ScenarioRunner(output_dir=args.output_dir, verbose=verbose, enable_plotting=enable_plotting)
    
    try:
        if args.list_actions:
            # List available maintenance actions
            actions = runner.list_available_actions()
            print(f"Available maintenance actions ({len(actions)}):")
            
            # Group by subsystem
            for subsystem in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
                subsystem_actions = runner.get_actions_by_subsystem(subsystem)
                if subsystem_actions:
                    print(f"\n{subsystem.upper()} ({len(subsystem_actions)} actions):")
                    for action in subsystem_actions:
                        print(f"  • {action}")
        
        elif args.list_scenarios:
            # List available operational scenarios
            scenarios = runner.list_available_scenarios()
            print(f"Available operational scenarios ({len(scenarios)}):")
            for scenario in scenarios:
                print(f"  • {scenario}")
        
        elif args.interactive:
            # Interactive mode
            interactive_mode(runner)
        
        elif args.action:
            # Single maintenance scenario with validation
            action = args.action
            
            # Validate action against enum
            if not runner.validate_action(action):
                print(f"❌ Invalid action: '{action}'")
                
                # Suggest similar actions
                suggestions = runner.suggest_similar_actions(action)
                if suggestions:
                    print(f"💡 Did you mean one of these?")
                    for suggestion in suggestions:
                        print(f"   • {suggestion}")
                else:
                    print(f"💡 Available actions:")
                    actions = runner.list_available_actions()
                    for i, valid_action in enumerate(actions[:10], 1):  # Show first 10
                        print(f"   {i:2d}. {valid_action}")
                    if len(actions) > 10:
                        print(f"   ... and {len(actions) - 10} more (use --list-actions to see all)")
                
                return 1
            
            aggressive_mode = args.aggressive
            
            # Handle multiple variants
            if args.num_variants > 1:
                print(f"🎲 Generating {args.num_variants} randomized variants")
                for i in range(args.num_variants):
                    variant_seed = args.seed + i if args.seed else None
                    print(f"\n[{i+1}/{args.num_variants}] Running variant {i+1}")
                    runner.run_maintenance_scenario(
                        actions=action,
                        duration_hours=args.duration,
                        aggressive_mode=aggressive_mode,
                        tracking_start_hours=args.tracking_start,
                        randomize=args.randomize,
                        randomization_seed=variant_seed,
                        randomization_factor=args.randomization_factor
                    )
                    # Small delay between variants for unique timestamps
                    time.sleep(1)
            else:
                runner.run_maintenance_scenario(
                    actions=action,
                    duration_hours=args.duration,
                    aggressive_mode=aggressive_mode,
                    tracking_start_hours=args.tracking_start,
                    randomize=args.randomize,
                    randomization_seed=args.seed,
                    randomization_factor=args.randomization_factor
                )
        
        elif args.actions:
            # Multi-action maintenance scenario with validation
            actions_list = [action.strip() for action in args.actions.split(',')]
            
            # Validate all actions
            invalid_actions = []
            for action in actions_list:
                if not runner.validate_action(action):
                    invalid_actions.append(action)
            
            if invalid_actions:
                print(f"❌ Invalid actions: {invalid_actions}")
                
                # Suggest similar actions for each invalid one
                for invalid_action in invalid_actions:
                    suggestions = runner.suggest_similar_actions(invalid_action)
                    if suggestions:
                        print(f"💡 For '{invalid_action}', did you mean: {', '.join(suggestions)}")
                
                return 1
            
            aggressive_mode = args.aggressive
            
            # Handle multiple variants
            if args.num_variants > 1:
                print(f"🎲 Generating {args.num_variants} randomized variants")
                for i in range(args.num_variants):
                    variant_seed = args.seed + i if args.seed else None
                    print(f"\n[{i+1}/{args.num_variants}] Running variant {i+1}")
                    runner.run_maintenance_scenario(
                        actions=actions_list,
                        duration_hours=args.duration,
                        aggressive_mode=aggressive_mode,
                        tracking_start_hours=args.tracking_start,
                        randomize=args.randomize,
                        randomization_seed=variant_seed,
                        randomization_factor=args.randomization_factor
                    )
                    # Small delay between variants for unique timestamps
                    time.sleep(1)
            else:
                runner.run_maintenance_scenario(
                    actions=actions_list,
                    duration_hours=args.duration,
                    aggressive_mode=aggressive_mode,
                    tracking_start_hours=args.tracking_start,
                    randomize=args.randomize,
                    randomization_seed=args.seed,
                    randomization_factor=args.randomization_factor
                )
        
        elif args.scenario:
            # Single operational scenario
            kwargs = {}
            if args.target_power:
                kwargs['target_power'] = args.target_power
            
            runner.run_operational_scenario(
                scenario_type=args.scenario,
                duration_hours=args.duration,
                **kwargs
            )
        
        elif args.batch_maintenance:
            # Batch maintenance scenarios
            if not args.actions:
                print("Error: --actions required for batch mode")
                return 1
            
            actions = [action.strip() for action in args.actions.split(',')]
            aggressive_mode = args.aggressive
            
            runner.run_batch_maintenance(
                actions=actions,
                duration_hours=args.duration,
                count_per_action=args.count,
                aggressive_mode=aggressive_mode
            )
        
        elif args.run_all_actions:
            # Run all available maintenance actions
            aggressive_mode = args.aggressive
            exclude_actions = None
            if args.exclude_actions:
                exclude_actions = [action.strip() for action in args.exclude_actions.split(',')]
            
            runner.run_all_actions(
                duration_hours=args.duration,
                count_per_action=args.count,
                aggressive_mode=aggressive_mode,
                subsystem_filter=args.subsystem,
                exclude_actions=exclude_actions
            )
        
        elif args.yaml_file:
            # PHASE 3: Run scenario from YAML file
            runner.run_from_yaml_file(
                yaml_path=args.yaml_file,
                save_results=True
            )
        
        elif args.yaml_dir:
            # PHASE 3: Run batch scenarios from YAML directory
            runner.run_batch_from_yaml_directory(
                yaml_dir=args.yaml_dir,
                pattern="*.yaml",
                save_results=True
            )
        
        elif args.validate_yaml:
            # PHASE 3: Validate YAML configuration
            is_valid = runner.validate_yaml_config(args.validate_yaml)
            return 0 if is_valid else 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
