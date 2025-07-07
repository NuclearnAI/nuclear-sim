#!/usr/bin/env python
"""
Custom Maintenance Scenario Runner

This module provides a streamlined simulation runner specifically designed
to work with the ComprehensiveComposer output and test maintenance actions.
It avoids the complexity of the existing WorkOrderTrackingSimulation and
provides focused functionality for maintenance scenario testing.
"""

import sys
import time
import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import core simulator
from simulator.core.sim import NuclearPlantSimulator, ControlAction
from systems.primary.reactor.heat_sources import ConstantHeatSource

# Import secondary system components (use SecondaryReactorPhysics instead of individual components)
try:
    from systems.secondary.config import PWRConfigManager
except ImportError:
    PWRConfigManager = None

# Simple enums for work orders (no longer import from maintenance system)
from enum import Enum

class WorkOrderType(Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MaintenanceScenarioRunner:
    """
    Custom simulation runner for maintenance scenarios
    
    This runner is specifically designed to work with ComprehensiveComposer
    configurations and test maintenance action triggering.
    """
    
    def __init__(self, config: Union[Dict[str, Any], str, Path], verbose: bool = True):
        """
        Initialize the maintenance scenario runner
        
        Args:
            config: Configuration dictionary from ComprehensiveComposer OR path to YAML file
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.simulator = None
        self.maintenance_system = None
        
        # Data collection
        self.simulation_data = []
        self.maintenance_events = []
        self.work_order_events = []
        self.component_health_data = []
        
        # No longer use maintenance catalog - rely on conditions files only
        self.maintenance_catalog = None
        
        # PHASE 1: Load configuration from dictionary or YAML file
        self.config = self._load_config(config)
        
        # CRITICAL FIX: Enhanced target action processing with validation
        self.target_action = self.config['metadata']['target_action']
        self.target_subsystem = self.config['metadata']['target_subsystem']
        self.subsystem_modes = self.config['metadata'].get('subsystem_modes', {})
        self.duration_hours = self.config['simulation_config']['duration_hours']
        
        # CRITICAL FIX: Validate target action consistency
        print(f"SCENARIO RUNNER: 🎯 Target action from config: {self.target_action}")
        print(f"SCENARIO RUNNER: 🏭 Target subsystem from config: {self.target_subsystem}")
        print(f"SCENARIO RUNNER: 🔧 Subsystem modes: {self.subsystem_modes}")
        
        # Initialize simulator
        self._initialize_simulator()
        
        if self.verbose:
            print(f"🔧 MaintenanceScenarioRunner initialized")
            print(f"   Target action: {self.target_action}")
            print(f"   Target subsystem: {self.target_subsystem}")
            print(f"   Duration: {self.duration_hours} hours")
            print(f"   Config validation: ✅ Target action preserved")
    
    def _load_config(self, config: Union[Dict[str, Any], str, Path]) -> Dict[str, Any]:
        """
        PHASE 1: Load configuration from dictionary or YAML file
        
        Args:
            config: Configuration dictionary OR path to YAML file
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML file is malformed
            ValueError: If configuration is invalid
        """
        if isinstance(config, dict):
            # Already a dictionary - validate and return
            if self.verbose:
                print(f"📄 Using provided configuration dictionary")
            self._validate_config(config)
            return config
        
        # Convert to Path object for easier handling
        yaml_path = Path(config)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML configuration file not found: {yaml_path}")
        
        if not yaml_path.suffix.lower() in ['.yaml', '.yml']:
            raise ValueError(f"File must have .yaml or .yml extension: {yaml_path}")
        
        if self.verbose:
            print(f"📄 Loading YAML configuration from: {yaml_path}")
        
        try:
            with open(yaml_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
            
            if self.verbose:
                print(f"   ✅ Successfully loaded YAML configuration")
                print(f"   📊 Configuration sections: {len(loaded_config)}")
            
            # Validate the loaded configuration
            self._validate_config(loaded_config)
            
            return loaded_config
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {yaml_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration from {yaml_path}: {e}")
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        PHASE 1: Validate configuration has required sections
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValueError: If required sections are missing
        """
        required_sections = [
            'metadata',
            'simulation_config', 
            'secondary_system',
            'maintenance_system'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            raise ValueError(f"Configuration missing required sections: {missing_sections}")
        
        # Validate metadata section has required fields
        metadata = config['metadata']
        required_metadata = ['target_action', 'target_subsystem']
        missing_metadata = []
        for field in required_metadata:
            if field not in metadata:
                missing_metadata.append(field)
        
        if missing_metadata:
            raise ValueError(f"Metadata section missing required fields: {missing_metadata}")
        
        # Validate simulation_config has duration
        sim_config = config['simulation_config']
        if 'duration_hours' not in sim_config:
            raise ValueError("simulation_config section missing 'duration_hours' field")
        
        if self.verbose:
            print(f"   ✅ Configuration validation passed")
            print(f"   🎯 Target action: {metadata['target_action']}")
            print(f"   🏭 Target subsystem: {metadata['target_subsystem']}")
            print(f"   ⏱️ Duration: {sim_config['duration_hours']} hours")
    
    def _initialize_simulator(self):
        """Initialize the nuclear plant simulator with maintenance system"""
        try:
            # Extract simulation parameters
            sim_config = self.config['simulation_config']
            time_step_minutes = sim_config.get('time_step_minutes', 1.0)
            
            # Create heat source
            thermal_power_mw = self.config.get('thermal_power_mw', 3000.0)
            heat_source = ConstantHeatSource(
                rated_power_mw=thermal_power_mw,
                noise_enabled=True,
                noise_std_percent=5.0,
                noise_seed=42
            )
            
            # For now, let the simulator use its default PWR configuration
            # The ComprehensiveComposer generates dataclass configs that need special handling
            # We'll enable secondary system and let it use the default PWR3000 config
            # Create simulator with real secondary system using comprehensive config
            # CORRECTED: dt is actually in minutes, not seconds (comment in sim.py was wrong)
            # CRITICAL FIX: Extract secondary_system section from comprehensive config
            self.simulator = NuclearPlantSimulator(
                heat_source=heat_source,
                dt=time_step_minutes,  # Use minutes directly
                enable_secondary=True,  # Always enable secondary system
                enable_state_management=True,
                secondary_config=self.config  # Use secondary_system section from comprehensive config
            )
            
            # Initialize maintenance monitoring
            self._initialize_maintenance_monitoring()
            
            # Reset to steady state
            # self.simulator.reset(start_at_steady_state=True)
            
            # Note: Initial degradation is now applied directly in component initial_conditions
            # by the ComprehensiveComposer, so no post-initialization degradation needed
            
            if self.verbose:
                print(f"   ✅ Simulator initialized")
                print(f"   🔥 Heat source: {thermal_power_mw} MW")
                print(f"   ⏱️ Time step: {time_step_minutes} minutes")
                print(f"   🔧 Maintenance system: {'Enabled' if self.maintenance_system else 'Disabled'}")
        
        except Exception as e:
            print(f"   ❌ Error initializing simulator: {e}")
            raise
    
    def _initialize_secondary_systems(self):
        """Initialize secondary systems from configuration"""
        try:
            # Get secondary system configuration
            secondary_config = self.config.get('secondary_system', {})
            
            # For now, we'll create a simplified secondary system
            # This can be expanded later to use the full dataclass configurations
            
            # Create basic secondary system components
            self.secondary_systems = {
                'steam_generator': None,
                'turbine': None,
                'feedwater': None,
                'condenser': None
            }
            
            if self.verbose:
                print(f"   🏭 Secondary systems initialized (simplified)")
        
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Secondary systems initialization skipped: {e}")
    
    def _initialize_maintenance_monitoring(self):
        """Initialize maintenance monitoring using the new state manager integration"""
        try:
            # Check if secondary system is available
            if hasattr(self.simulator, 'secondary_physics') and self.simulator.secondary_physics:
                self.secondary_system = self.simulator.secondary_physics
                
                # Get the auto maintenance system from the simulator
                if hasattr(self.simulator, 'maintenance_system') and self.simulator.maintenance_system:
                    self.auto_maintenance_system = self.simulator.maintenance_system
                    
                    # NEW: Use the improved state manager integration
                    if self.verbose:
                        print(f"   🔧 Using new state manager integration for maintenance monitoring")
                    
                    # Use the new setup method that leverages state manager as single source of truth
                    if hasattr(self.simulator, 'state_manager'):
                        # CRITICAL FIX: Pass the config to state manager so it can load maintenance_system section
                        self.simulator.state_manager.config = self.config
                        
                        self.auto_maintenance_system.setup_monitoring_from_state_manager(
                            self.simulator.state_manager, 
                            aggressive_mode=True  # Use aggressive mode for better triggering
                        )
                        
                        # The maintenance_system config from template is now properly loaded
                        # State manager will use the realistic thresholds from the template
                        
                        self.maintenance_system = True
                        
                        if self.verbose:
                            print(f"   ✅ Auto maintenance system configured via state manager")
                            
                            # Get auto maintenance status
                            status = self.auto_maintenance_system.get_system_status()
                            print(f"   📊 Auto maintenance check interval: {status['check_interval_hours']} hours")
                            print(f"   🚀 Auto execution enabled: {status['auto_execute_enabled']}")
                            print(f"   📋 Work orders created: {status['work_orders_created']}")
                            print(f"   🔧 Work orders executed: {status['work_orders_executed']}")
                            
                            # Show state manager integration status
                            if 'state_manager_stats' in status:
                                sm_stats = status['state_manager_stats']
                                print(f"   🏭 Components registered: {sm_stats.get('registered_components', 0)}")
                                print(f"   🎯 Maintenance thresholds: {sm_stats.get('maintenance_thresholds', 0)}")
                                print(f"   🚨 Current violations: {sm_stats.get('threshold_violations', 0)}")
                    else:
                        self.maintenance_system = None
                        if self.verbose:
                            print(f"   ⚠️ State manager not available")
                else:
                    self.maintenance_system = None
                    if self.verbose:
                        print(f"   ⚠️ Auto maintenance system not available")
            else:
                self.maintenance_system = None
                if self.verbose:
                    print(f"   ⚠️ Secondary system not available")
        
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Maintenance monitoring initialization failed: {e}")
                import traceback
                traceback.print_exc()
            self.maintenance_system = None
    
    def run_scenario(self) -> Dict[str, Any]:
        """
        Run the maintenance scenario
        
        Returns:
            Dictionary containing simulation results
        """
        if self.verbose:
            print(f"\n🚀 Running maintenance scenario: {self.target_action}")
            print(f"{'Time (min)':<10} {'Power (%)':<10} {'Maintenance Events':<18} {'Work Orders':<12}")
            print("-" * 60)
        
        # PHASE 1 FIX: Calculate simulation parameters using actual dt
        duration_minutes = int(self.duration_hours * 60)
        dt_minutes = self.simulator.dt  # Get actual dt from simulator
        num_steps = int(duration_minutes / dt_minutes)  # Calculate correct number of steps
        
        if self.verbose:
            print(f"📊 Simulation parameters:")
            print(f"   Duration: {self.duration_hours} hours ({duration_minutes} minutes)")
            print(f"   Time step (dt): {dt_minutes} minutes")
            print(f"   Number of steps: {num_steps}")
            print(f"   Total simulation time: {num_steps * dt_minutes} minutes")
        
        # Generate power profile for correct number of steps
        power_profile = self._generate_power_profile(num_steps)
        
        # Track maintenance triggering
        maintenance_triggered = False
        work_orders_created = 0
        
        # Run simulation
        start_time = time.time()
        
        for step in range(num_steps):
            # Calculate current simulation time
            current_time_minutes = step * dt_minutes
            
            # Set target power
            target_power = power_profile[step]
            self._set_target_power(target_power)
            
            # Step simulator
            result = self.simulator.step(action=ControlAction.NO_ACTION)
            
            # Simulate component degradation to trigger maintenance
            self._simulate_component_degradation(current_time_minutes)
            
            # Check for maintenance triggers
            maintenance_events = self._check_maintenance_triggers(current_time_minutes)
            if maintenance_events:
                maintenance_triggered = True
                work_orders_created += len(maintenance_events)
                self.maintenance_events.extend(maintenance_events)
            
            # Collect data
            self._collect_simulation_data(current_time_minutes, result, target_power, maintenance_events)
            
            # PHASE 3 FIX: Print status at appropriate intervals based on simulation time
            print_interval = max(1, int(10.0 / dt_minutes))  # Print every ~10 minutes of sim time
            if step % print_interval == 0 and self.verbose:
                print(f"{current_time_minutes:<10.0f} {self.simulator.state.power_level:<10.1f} "
                      f"{len(maintenance_events):<18} {work_orders_created:<12}")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # FIX: Get actual work order count from AutoMaintenanceSystem
        actual_work_orders_created = 0
        actual_work_orders_executed = 0
        
        if self.maintenance_system and hasattr(self, 'auto_maintenance_system'):
            auto_status = self.auto_maintenance_system.get_system_status()
            actual_work_orders_created = auto_status['work_orders_created']
            actual_work_orders_executed = auto_status['work_orders_executed']
            
            if self.verbose:
                print(f"\n🔧 Work Order Count Verification:")
                print(f"   📊 Scenario runner tracked: {work_orders_created}")
                print(f"   🎯 Auto maintenance actual: {actual_work_orders_created}")
                print(f"   ✅ Auto maintenance executed: {actual_work_orders_executed}")
        
        # Generate results using actual counts from AutoMaintenanceSystem
        results = {
            'success': maintenance_triggered or actual_work_orders_created > 0,  # Success if either tracking method shows work orders
            'target_action': self.target_action,
            'target_subsystem': self.target_subsystem,
            'duration_hours': self.duration_hours,
            'execution_time_seconds': execution_time,
            'work_orders_created': actual_work_orders_created,  # Use actual count from AutoMaintenanceSystem
            'work_orders_executed': actual_work_orders_executed,  # Add executed count
            'scenario_tracked_work_orders': work_orders_created,  # Keep original for debugging
            'maintenance_events': len(self.maintenance_events),
            'simulation_data_points': len(self.simulation_data),
            'final_power_level': self.simulator.state.power_level
        }
        
        if self.verbose:
            print(f"\n📋 Scenario Results:")
            print(f"   ✅ Success: {results['success']}")
            print(f"   🔧 Work orders created: {actual_work_orders_created}")
            print(f"   ⚡ Work orders executed: {actual_work_orders_executed}")
            print(f"   📊 Maintenance events: {len(self.maintenance_events)}")
            print(f"   ⏱️ Execution time: {execution_time:.1f}s")
            
            # Show discrepancy if any
            if work_orders_created != actual_work_orders_created:
                print(f"   ⚠️ Count discrepancy: scenario tracked {work_orders_created}, actual {actual_work_orders_created}")
        
        # NEW: Add maintenance effectiveness verification if available
        if self.maintenance_system and hasattr(self, 'auto_maintenance_system') and actual_work_orders_executed > 0:
            effectiveness_data = self._verify_maintenance_effectiveness()
            results['maintenance_effectiveness'] = effectiveness_data
            
            if self.verbose and effectiveness_data:
                print(f"   📊 Maintenance effectiveness: {effectiveness_data.get('average_effectiveness', 0):.1%}")
        
        return results
    
    def _verify_maintenance_effectiveness(self) -> Dict[str, Any]:
        """Verify maintenance effectiveness using state manager capabilities"""
        effectiveness_data = {
            'verifications_performed': 0,
            'successful_verifications': 0,
            'average_effectiveness': 0.0,
            'verification_details': []
        }
        
        try:
            if hasattr(self.simulator, 'state_manager') and self.simulator.state_manager:
                state_manager = self.simulator.state_manager
                
                # Get maintenance history
                maintenance_history = state_manager.get_maintenance_history()
                
                for maintenance_record in maintenance_history:
                    if maintenance_record.get('success', False):
                        component_id = maintenance_record.get('component_id')
                        action_type = maintenance_record.get('action_type')
                        
                        # Define expected changes for common maintenance actions
                        expected_changes = self._get_expected_maintenance_changes(action_type)
                        
                        if expected_changes and component_id:
                            # Use state manager's verification method
                            is_effective = state_manager.verify_maintenance_action(
                                component_id=component_id,
                                action_type=action_type,
                                expected_changes=expected_changes,
                                tolerance=0.1
                            )
                            
                            effectiveness_data['verifications_performed'] += 1
                            if is_effective:
                                effectiveness_data['successful_verifications'] += 1
                            
                            effectiveness_data['verification_details'].append({
                                'component_id': component_id,
                                'action_type': action_type,
                                'effective': is_effective,
                                'expected_changes': expected_changes
                            })
                
                # Calculate average effectiveness
                if effectiveness_data['verifications_performed'] > 0:
                    effectiveness_data['average_effectiveness'] = (
                        effectiveness_data['successful_verifications'] / 
                        effectiveness_data['verifications_performed']
                    )
                
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Maintenance effectiveness verification failed: {e}")
        
        return effectiveness_data
    
    def _get_expected_maintenance_changes(self, action_type: str) -> Dict[str, float]:
        """Get expected parameter changes for maintenance actions"""
        # Define expected changes for common maintenance actions
        expected_changes_map = {
            'oil_top_off': {
                'oil_level': 20.0  # Expect oil level to increase by ~20%
            },
            'oil_change': {
                'oil_contamination': -10.0  # Expect contamination to decrease by ~10 ppm
            },
            'bearing_inspection': {
                'bearing_temperature': -5.0  # Expect temperature to decrease by ~5°C
            },
            'vibration_analysis': {
                'vibration_level': -2.0  # Expect vibration to decrease by ~2 mm/s
            },
            'tsp_chemical_cleaning': {
                'tsp_fouling_fraction': -0.03  # Expect fouling to decrease by ~3%
            },
            'condenser_tube_cleaning': {
                'fouling_resistance': -0.0005  # Expect fouling resistance to decrease
            },
            'turbine_oil_top_off': {
                'oil_level': 25.0  # Expect oil level to increase by ~25%
            },
            'efficiency_analysis': {
                'efficiency': 0.02  # Expect efficiency to improve by ~2%
            }
        }
        
        return expected_changes_map.get(action_type, {})
    
    def _generate_power_profile(self, num_steps: int) -> np.ndarray:
        """Generate power profile for the scenario"""
        # Get load profile configuration
        load_profiles = self.config.get('load_profiles', {})
        scenario = self.config['simulation_config'].get('scenario', 'steady_with_noise')
        
        if 'profiles' in load_profiles and scenario in load_profiles['profiles']:
            profile_config = load_profiles['profiles'][scenario]
            base_power = profile_config.get('base_power_percent', 90.0)
            noise_std = profile_config.get('noise_std_percent', 2.0)
        else:
            # Default steady state with noise
            base_power = 90.0
            noise_std = 2.0
        
        # PHASE 4 FIX: Generate profile for correct number of steps
        time_points = np.arange(num_steps)
        noise = noise_std * np.random.normal(0, 1, num_steps)
        power_profile = base_power + noise
        
        # Clip to reasonable bounds
        power_profile = np.clip(power_profile, 20.0, 105.0)
        
        return power_profile
    
    def _set_target_power(self, target_power: float):
        """Set target power using heat source"""
        if hasattr(self.simulator.primary_physics.heat_source, 'set_power_setpoint'):
            self.simulator.primary_physics.heat_source.set_power_setpoint(target_power)
    
    def _simulate_component_degradation(self, time_step: int):
        """Monitor real component degradation - no artificial degradation needed"""
        # The secondary system components already have built-in degradation models:
        # - Steam generators have TSP fouling that accumulates over time
        # - Turbines have bearing wear and efficiency degradation
        # - Feedwater pumps have oil degradation and bearing wear
        # - Condensers have fouling accumulation
        # 
        # We just need to monitor these existing parameters, not add artificial degradation
        pass
    
    def _update_component_parameter(self, component_id: str, parameter: str, value: float):
        """Update a component parameter for maintenance monitoring"""
        # This would normally be handled by the actual component models
        # For testing, we'll store the values and check thresholds manually
        if not hasattr(self, '_component_parameters'):
            self._component_parameters = {}
        
        if component_id not in self._component_parameters:
            self._component_parameters[component_id] = {}
        
        self._component_parameters[component_id][parameter] = value
    
    def _check_maintenance_triggers(self, time_step: int) -> List[Dict[str, Any]]:
        """Extract actual maintenance actions being performed and track work orders"""
        events = []
        
        if not self.maintenance_system or not hasattr(self, 'auto_maintenance_system'):
            return events
        
        time_minutes = time_step  # time_step is already in minutes
        time_hours = time_minutes / 60.0  # Derived for compatibility
        
        try:
            # CRITICAL FIX: Check for new work orders created FIRST, before they get executed
            self._check_work_order_creation(time_minutes, time_hours)
            
            # CRITICAL FIX: Also check for work orders that were just created in this update cycle
            # These might not show up in get_recent_work_orders() if they were immediately executed
            if hasattr(self.auto_maintenance_system, 'current_update_work_orders'):
                for new_work_order in self.auto_maintenance_system.current_update_work_orders:
                    # Create work order creation event for newly created work orders
                    if not hasattr(self, '_processed_work_order_creations'):
                        self._processed_work_order_creations = set()
                    
                    work_order_id = new_work_order.work_order_id
                    if work_order_id not in self._processed_work_order_creations:
                        creation_event = {
                            'time_hours': new_work_order.created_date / 60.0,
                            'work_order_id': work_order_id,
                            'component_id': new_work_order.component_id,
                            'work_order_type': new_work_order.work_order_type.value,
                            'priority': new_work_order.priority.value,
                            'status': new_work_order.status.value,
                            'title': new_work_order.title,  # CRITICAL FIX: Get title directly from work order object
                            'description': new_work_order.description,  # CRITICAL FIX: Get description directly from work order object
                            'created_date': new_work_order.created_date,
                            'planned_start_date': new_work_order.planned_start_date,
                            'planned_duration': new_work_order.planned_duration,
                            'auto_generated': new_work_order.auto_generated,
                            'trigger_id': new_work_order.trigger_id,
                            'event_type': 'work_order_created'
                        }
                        
                        self.work_order_events.append(creation_event)
                        self._processed_work_order_creations.add(work_order_id)
                        
                        if self.verbose:
                            print(f"   📋 WORK ORDER CREATED: {work_order_id} for {new_work_order.component_id} at {creation_event['time_hours']:.2f}h")
                            print(f"       Title: '{new_work_order.title}'")
            
            # Get recently completed work orders from auto maintenance system
            recent_work_orders = self.auto_maintenance_system.get_recent_work_orders(limit=10)
            
            for work_order_dict in recent_work_orders:
                # Track work order status changes
                self._track_work_order_status_change(work_order_dict, time_hours)
                
                # Check if this work order was just completed
                if (work_order_dict.get('status') == 'completed' and 
                    work_order_dict.get('actual_completion_date')):
                    
                    completion_time_hours = work_order_dict['actual_completion_date'] / 60.0
                    
                    # CRITICAL FIX: Only log if completed in the last check interval AND not already processed
                    time_since_completion = time_hours - completion_time_hours
                    
                    # Only process if completed very recently (within check interval) and in the past
                    if (0 <= time_since_completion <= self.auto_maintenance_system.check_interval_hours):
                        
                        # DUPLICATE PREVENTION: Check if we already processed this work order completion
                        if not hasattr(self, '_processed_work_order_completions'):
                            self._processed_work_order_completions = set()
                        
                        completion_key = f"{work_order_dict['work_order_id']}_{completion_time_hours}"
                        if completion_key in self._processed_work_order_completions:
                            continue  # Skip already processed completion
                        
                        # Mark as processed
                        self._processed_work_order_completions.add(completion_key)
                        
                        # Extract each maintenance action from the work order
                        maintenance_actions = work_order_dict.get('maintenance_actions', [])
                        if not maintenance_actions:
                            # CRITICAL FIX: Infer action type from work order title
                            action_type = self._infer_action_type_from_work_order(work_order_dict)
                            maintenance_actions = [{'action_type': action_type, 'success': True}]
                        
                        for action in maintenance_actions:
                            # CRITICAL FIX: Get proper action type and name
                            action_type = action.get('action_type', 'unknown')
                            if action_type == 'unknown' or action_type == 'maintenance_action':
                                # Try to infer from work order details
                                action_type = self._infer_action_type_from_work_order(work_order_dict)
                            
                            event = {
                                'time_hours': completion_time_hours,
                                'component_id': work_order_dict['component_id'],
                                'action_type': action_type,
                                'action_name': self._get_action_display_name(action_type),
                                'work_order_id': work_order_dict['work_order_id'],
                                'success': action.get('success', True),  # Default to True if not specified
                                'duration_hours': action.get('actual_duration', 0.5),  # Default duration
                                'effectiveness_score': action.get('effectiveness_score', 1.0),  # Default effectiveness
                                'findings': action.get('findings', ''),
                                'triggered': True,
                                'trigger_reason': f'Maintenance action completed: {action_type}'
                            }
                            events.append(event)
                            
                            if self.verbose:
                                print(f"   🔧 MAINTENANCE ACTION: {event['action_name']} on {event['component_id']} at {completion_time_hours:.2f}h")
                
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Warning: Maintenance action check failed: {e}")
                import traceback
                traceback.print_exc()
        
        return events
    
    def _check_work_order_creation(self, time_minutes: float, time_hours: float):
        """Check for new work orders being created"""
        try:
            # Get current work order count
            current_status = self.auto_maintenance_system.get_system_status()
            current_work_orders = current_status['work_orders_created']
            
            # Check if new work orders were created since last check
            if not hasattr(self, '_last_work_order_count'):
                self._last_work_order_count = 0
            
            new_work_orders = current_work_orders - self._last_work_order_count
            
            if new_work_orders > 0:
                # CRITICAL FIX: Track work orders we've already processed to avoid duplicates
                if not hasattr(self, '_processed_work_order_creations'):
                    self._processed_work_order_creations = set()
                
                # Get recent work orders to find the newly created ones
                recent_work_orders = self.auto_maintenance_system.get_recent_work_orders(limit=current_work_orders + 5)
                
                # CRITICAL FIX: Process all work orders, not just the last N
                for work_order_dict in recent_work_orders:
                    work_order_id = work_order_dict['work_order_id']
                    
                    # Skip if we've already processed this work order creation
                    if work_order_id in self._processed_work_order_creations:
                        continue
                    
                    # CRITICAL FIX: Only process work orders created recently
                    created_time_minutes = work_order_dict.get('created_date', 0)  # Already in minutes
                    created_time_hours = created_time_minutes / 60.0
                    time_since_creation = time_hours - created_time_hours
                    
                    # Only process if created very recently (within check interval)
                    if 0 <= time_since_creation <= self.auto_maintenance_system.check_interval_hours:
                        # Create work order event
                        work_order_event = {
                            'time_minutes': created_time_minutes,  # Primary time field
                            'time_hours': created_time_hours,  # Derived for compatibility
                            'work_order_id': work_order_id,
                            'component_id': work_order_dict['component_id'],
                            'work_order_type': work_order_dict.get('work_order_type', 'corrective'),
                            'priority': work_order_dict.get('priority', 'MEDIUM'),
                            'status': work_order_dict.get('status', 'planned'),
                            'title': work_order_dict.get('title', ''),
                            'description': work_order_dict.get('description', ''),
                            'created_date': created_time_minutes,  # Already in minutes
                            'planned_start_date': work_order_dict.get('planned_start_date'),
                            'planned_duration': work_order_dict.get('planned_duration', 0.0),
                            'auto_generated': work_order_dict.get('auto_generated', True),
                            'trigger_id': work_order_dict.get('trigger_id', ''),
                            'event_type': 'work_order_created'
                        }
                        
                        self.work_order_events.append(work_order_event)
                        self._processed_work_order_creations.add(work_order_id)
                        
                        if self.verbose:
                            print(f"   📋 WORK ORDER CREATED: {work_order_id} for {work_order_dict['component_id']} at {created_time_hours:.2f}h")
                
                # Update the work order count
                self._last_work_order_count = current_work_orders
                
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Warning: Work order creation check failed: {e}")
    
    def _track_work_order_status_change(self, work_order_dict: dict, time_hours: float):
        """Track work order status changes"""
        work_order_id = work_order_dict['work_order_id']
        current_status = work_order_dict.get('status', 'unknown')
        
        # Track status changes
        if not hasattr(self, '_work_order_status_tracker'):
            self._work_order_status_tracker = {}
        
        if work_order_id not in self._work_order_status_tracker:
            self._work_order_status_tracker[work_order_id] = current_status
        elif self._work_order_status_tracker[work_order_id] != current_status:
            # FIXED: Use actual completion time if available, otherwise current time
            event_time_minutes = None
            event_time_hours = time_hours
            
            if current_status == 'completed' and work_order_dict.get('actual_completion_date'):
                # Use actual completion time for completed work orders
                event_time_minutes = work_order_dict['actual_completion_date']
                event_time_hours = event_time_minutes / 60.0
            elif current_status == 'in_progress' and work_order_dict.get('actual_start_date'):
                # Use actual start time for in-progress work orders
                event_time_minutes = work_order_dict['actual_start_date']
                event_time_hours = event_time_minutes / 60.0
            else:
                # Use current simulation time
                event_time_minutes = time_hours * 60.0
                event_time_hours = time_hours
            
            # Status changed - log the event
            status_change_event = {
                'time_minutes': event_time_minutes,  # Primary time field
                'time_hours': event_time_hours,      # Derived for compatibility
                'work_order_id': work_order_id,
                'component_id': work_order_dict['component_id'],
                'old_status': self._work_order_status_tracker[work_order_id],
                'new_status': current_status,
                'actual_start_date': work_order_dict.get('actual_start_date'),
                'actual_completion_date': work_order_dict.get('actual_completion_date'),
                'actual_duration': work_order_dict.get('actual_duration'),
                'event_type': 'work_order_status_change'
            }
            
            self.work_order_events.append(status_change_event)
            self._work_order_status_tracker[work_order_id] = current_status
            
            if self.verbose:
                print(f"   📋 WORK ORDER STATUS: {work_order_id} {status_change_event['old_status']} → {current_status} at {event_time_hours:.2f}h")
    
    def _get_parameter_threshold(self, component_id: str, parameter: str) -> Optional[float]:
        """Get threshold for a component parameter"""
        # Simplified threshold lookup
        thresholds = {
            'oil_level': 80.0,
            'fouling_level': 0.5,
            'vibration_level': 5.0,
            'fouling_resistance': 0.001
        }
        return thresholds.get(parameter)
    
    def _collect_simulation_data(self, time_step: int, result: Dict, target_power: float, maintenance_events: List):
        """Enhanced data collection using state manager capabilities"""
        data_point = {
            'time_minutes': time_step,
            'time_hours': time_step / 60.0,
            'target_power': target_power,
            'actual_power': self.simulator.state.power_level,
            'fuel_temperature': self.simulator.state.fuel_temperature,
            'coolant_temperature': self.simulator.state.coolant_temperature,
            'control_rod_position': self.simulator.state.control_rod_position,
            'maintenance_events': len(maintenance_events),
            'maintenance_triggered': len(maintenance_events) > 0,
            'feedwater_flow': self.simulator.secondary_physics.total_feedwater_flow
        }
        
        # NEW: Add state manager maintenance data
        if hasattr(self.simulator, 'state_manager') and self.simulator.state_manager:
            state_manager = self.simulator.state_manager
            
            # Add threshold violation data
            current_violations = state_manager.get_current_threshold_violations()
            data_point['threshold_violations_count'] = len(current_violations)
            
            # Add maintenance history data
            maintenance_history = state_manager.get_maintenance_history()
            data_point['maintenance_history_count'] = len(maintenance_history)
            
            # Add component health snapshots for key components
            key_components = ['FW-001', 'TB-001', 'SG-001', 'CD-001']
            for component_id in key_components:
                try:
                    snapshot = state_manager.get_component_state_snapshot(component_id)
                    for param, value in snapshot.items():
                        if isinstance(value, (int, float)):
                            data_point[f"{component_id}_{param}"] = value
                except:
                    # Component might not exist or have data yet
                    pass
        
        # Add component parameters if available (legacy support)
        if hasattr(self, '_component_parameters'):
            for comp_id, params in self._component_parameters.items():
                for param_name, value in params.items():
                    data_point[f"{comp_id}_{param_name}"] = value
        
        self.simulation_data.append(data_point)
    
    def create_plots(self, save_plots: bool = True) -> None:
        """Create visualization plots"""
        if not self.simulation_data:
            print("No simulation data available for plotting")
            return
        
        df = pd.DataFrame(self.simulation_data)
        
        # Create plots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Power level
        axes[0, 0].plot(df['time_hours'], df['target_power'], 'b--', label='Target', alpha=0.7)
        axes[0, 0].plot(df['time_hours'], df['actual_power'], 'b-', label='Actual', linewidth=2)
        axes[0, 0].set_ylabel('Power Level (%)')
        axes[0, 0].set_title('Power Level')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Temperatures
        axes[0, 1].plot(df['time_hours'], df['fuel_temperature'], 'r-', label='Fuel')
        axes[0, 1].plot(df['time_hours'], df['coolant_temperature'], 'b-', label='Coolant')
        axes[0, 1].set_ylabel('Temperature (°C)')
        axes[0, 1].set_title('System Temperatures')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Maintenance events
        axes[1, 0].plot(df['time_hours'], df['maintenance_events'], 'g-', linewidth=2)
        axes[1, 0].set_ylabel('Maintenance Events')
        axes[1, 0].set_title('Maintenance Triggering')
        axes[1, 0].grid(True, alpha=0.3)
        
        '''
        # Component parameters (if available)
        param_cols = [col for col in df.columns if '_' in col and col not in ['time_minutes', 'time_hours']]
        if param_cols:
            for i, col in enumerate(param_cols[:3]):  # Show first 3 parameters
                axes[1, 1].plot(df['time_hours'], df[col], label=col.split('_')[-1])
            axes[1, 1].set_ylabel('Parameter Value')
            axes[1, 1].set_title('Component Parameters')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        else:
            axes[1, 1].plot(df['time_hours'], df['control_rod_position'], 'purple', linewidth=2)
            axes[1, 1].set_ylabel('Rod Position (%)')
            axes[1, 1].set_title('Control Rod Position')
            axes[1, 1].grid(True, alpha=0.3)
        '''

        axes[1, 1].plot(df['time_hours'], df['feedwater_flow'])
        axes[1, 1].set_ylabel('Feedwater Flow kg/s')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].set_title('Feedwater Monitoring')

        # Set x-axis labels
        for ax in axes[1, :]:
            ax.set_xlabel('Time (hours)')
        
        plt.suptitle(f'Maintenance Scenario: {self.target_action}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_plots:
            filename = f'maintenance_scenario_{self.target_action}.png'
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            if self.verbose:
                print(f"📊 Plots saved to {filename}")
        
        plt.show()
    
    def export_data(self, filename_prefix: str = None) -> List[str]:
        """Export simulation data and maintenance actions to CSV files"""
        if filename_prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"{self.target_action}_{timestamp}"
        
        exported_files = []
        
        # Export simulation data using state manager
        filename = f"{filename_prefix}_simulation_data"
        self.simulator.state_manager.export_by_category('secondary',  f"{filename}.csv")
        self.simulator.state_manager.export_by_subcategory('secondary', 'feedwater_FWP-1', f"{filename}_fwp_1_data.csv")
        exported_files.append(filename)
        if self.verbose:
            print(f"📄 Simulation data exported to {filename}")
        
        # Export maintenance actions (new)
        maintenance_file = self.export_maintenance_actions_csv(filename_prefix)
        if maintenance_file:
            exported_files.append(maintenance_file)
            if self.verbose:
                print(f"📄 Maintenance actions exported to {maintenance_file}")
        
        # Export work orders (new)
        work_orders_file = self.export_work_orders_csv(filename_prefix)
        if work_orders_file:
            exported_files.append(work_orders_file)
            if self.verbose:
                print(f"📄 Work orders exported to {work_orders_file}")
        
        return exported_files
    
    def export_maintenance_actions_csv(self, filename_prefix: str) -> str:
        """Export detailed maintenance actions to CSV"""
        if not self.maintenance_events:
            return None
        
        maintenance_data = []
        
        for event in self.maintenance_events:
            row = {
                # Timing
                'timestamp_hours': event['time_hours'],
                'timestamp_minutes': event['time_hours'] * 60,
                'simulation_time_formatted': self._format_simulation_time(event['time_hours'] * 60),
                
                # Component & Action (simplified - only action_name)
                'component_id': event['component_id'],
                'action_name': event.get('action_name', event['action_type'].replace('_', ' ').title()),
                'work_order_id': event.get('work_order_id', ''),
                
                # Results
                'success': event.get('success', False),
                'duration_hours': event.get('duration_hours', 0.0),
                'effectiveness_score': event.get('effectiveness_score', 0.0),
                'findings': event.get('findings', ''),
                
                # Context
                'trigger_reason': event.get('trigger_reason', 'Auto maintenance trigger')
            }
            maintenance_data.append(row)
        
        # Export to CSV
        filename = f"{filename_prefix}_maintenance_actions.csv"
        df = pd.DataFrame(maintenance_data)
        df.to_csv(filename, index=False)
        
        return filename

    def export_work_orders_csv(self, filename_prefix: str) -> str:
        """Export detailed work orders to CSV"""
        if not self.work_order_events:
            return None
        
        work_order_data = []
        
        for event in self.work_order_events:
            # FIXED: Use consistent time fields - minutes as primary, hours as derived
            time_minutes = event.get('time_minutes', event.get('time_hours', 0) * 60)
            time_hours = time_minutes / 60.0
            
            row = {
                # FIXED: Timing - minutes as primary, hours as derived
                'timestamp_minutes': time_minutes,
                'timestamp_hours': time_hours,
                'simulation_time_formatted': self._format_simulation_time(time_minutes),
                
                # Work Order Details
                'work_order_id': event['work_order_id'],
                'component_id': event['component_id'],
                'work_order_type': event.get('work_order_type', 'corrective'),
                'priority': event.get('priority', 'MEDIUM'),
                'status': event.get('status', 'planned'),
                'title': event.get('title', ''),
                'description': event.get('description', ''),
                
                # Event Type
                'event_type': event.get('event_type', 'unknown'),
                'old_status': event.get('old_status', ''),
                'new_status': event.get('new_status', ''),
                
                # Scheduling (all times in minutes)
                'created_date': event.get('created_date'),
                'planned_start_date': event.get('planned_start_date'),
                'planned_duration': event.get('planned_duration', 0.0),
                'actual_start_date': event.get('actual_start_date'),
                'actual_completion_date': event.get('actual_completion_date'),
                'actual_duration': event.get('actual_duration'),
                
                # Metadata
                'auto_generated': event.get('auto_generated', True),
                'trigger_id': event.get('trigger_id', '')
            }
            work_order_data.append(row)
        
        # Export to CSV
        filename = f"{filename_prefix}_work_orders.csv"
        df = pd.DataFrame(work_order_data)
        df.to_csv(filename, index=False)
        
        return filename

    def smart_parse_action_type(self, work_order_title: str) -> str:
        """
        Smart parsing to extract action type from work order titles
        
        Examples:
        "Auto: Oil Change - FWP-1" → "oil_change"
        "Auto: Bearing Replacement - FWP-2" → "bearing_replacement" 
        "Auto: Lubrication System Check - FWP-3" → "lubrication_system_check"
        "Auto: Seal Replacement - FWP-1" → "seal_replacement"
        """
        import re
        
        if not work_order_title:
            return "maintenance_action"
        
        # Step 1: Clean the title
        # Remove "Auto: " prefix and component suffix
        cleaned = work_order_title.lower()
        cleaned = re.sub(r'^auto:\s*', '', cleaned)  # Remove "Auto: "
        cleaned = re.sub(r'\s*-\s*\w+-\d+$', '', cleaned)  # Remove " - FWP-1"
        
        # Step 2: Transform to action_type format
        # Replace spaces with underscores
        action_type = cleaned.replace(' ', '_')
        
        # Step 3: Handle common variations
        # "lubrication_system_check" stays as is
        # "oil_change" stays as is
        # etc.
        
        return action_type.strip()
    
    def _infer_action_type_from_work_order(self, work_order_dict: dict) -> str:
        """Get action type from work order using smart parsing"""
        
        # BEST: Direct access to stored action type (most reliable)
        maintenance_actions = work_order_dict.get('maintenance_actions', [])
        if maintenance_actions:
            action = maintenance_actions[0]
            if isinstance(action, dict) and 'action_type' in action:
                return action['action_type']
        
        # SMART PARSING: Extract from work order title
        title = work_order_dict.get('title', '')
        if title:
            action_type = self.smart_parse_action_type(title)
            if action_type and action_type != "maintenance_action":
                return action_type
        
        # Final fallback - generic action, NOT scenario name
        return "maintenance_action"

    def _get_action_display_name(self, action_type: str) -> str:
        """Get human-readable name for maintenance action - simplified without maintenance system"""
        return action_type.replace('_', ' ').title()

    def _format_simulation_time(self, time_minutes: Optional[float]) -> Optional[str]:
        """Format simulation time in minutes to HH:MM:SS format"""
        if time_minutes is None:
            return None
        
        total_seconds = int(time_minutes * 60)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # ===== COMPONENT MONITORING METHODS =====
    
    def _check_steam_generator_triggers(self, time_hours: float) -> List[Dict[str, Any]]:
        """Check steam generator health for maintenance triggers"""
        events = []
        thresholds = self.maintenance_config['thresholds']['steam_generator']
        
        if not hasattr(self.steam_generators, 'steam_generators'):
            return events
        
        try:
            for i, sg in enumerate(self.steam_generators.steam_generators):
                sg_id = f"SG_{i+1}"
                
                # Check TSP fouling
                if hasattr(sg, 'tsp_fouling') and hasattr(sg.tsp_fouling, 'fouling_fraction'):
                    fouling_fraction = sg.tsp_fouling.fouling_fraction
                    if fouling_fraction > thresholds['heat_transfer_degradation']:
                        events.append({
                            'time_hours': time_hours,
                            'component_id': sg_id,
                            'parameter': 'tsp_fouling_fraction',
                            'value': fouling_fraction,
                            'threshold': thresholds['heat_transfer_degradation'],
                            'action': 'tsp_chemical_cleaning',
                            'triggered': True
                        })
                
                # Check tube wall temperature
                if hasattr(sg, 'tube_wall_temp'):
                    tube_temp = sg.tube_wall_temp
                    if tube_temp > thresholds['tube_wall_temperature']:
                        events.append({
                            'time_hours': time_hours,
                            'component_id': sg_id,
                            'parameter': 'tube_wall_temperature',
                            'value': tube_temp,
                            'threshold': thresholds['tube_wall_temperature'],
                            'action': 'scale_removal',
                            'triggered': True
                        })
                
                # Check steam quality
                if hasattr(sg, 'steam_quality'):
                    steam_quality = sg.steam_quality
                    if steam_quality < thresholds['steam_quality']:
                        events.append({
                            'time_hours': time_hours,
                            'component_id': sg_id,
                            'parameter': 'steam_quality',
                            'value': steam_quality,
                            'threshold': thresholds['steam_quality'],
                            'action': 'moisture_separator_maintenance',
                            'triggered': True
                        })
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Steam generator monitoring error: {e}")
        
        return events
    
    def _check_turbine_triggers(self, time_hours: float) -> List[Dict[str, Any]]:
        """Check turbine health for maintenance triggers"""
        events = []
        thresholds = self.maintenance_config['thresholds']['turbine']
        
        try:
            # Check bearing temperatures
            if hasattr(self.turbine, 'bearing_system') and hasattr(self.turbine.bearing_system, 'bearings'):
                for bearing_id, bearing in self.turbine.bearing_system.bearings.items():
                    if hasattr(bearing, 'temperature'):
                        temp = bearing.temperature
                        if temp > thresholds['bearing_temperature']:
                            events.append({
                                'time_hours': time_hours,
                                'component_id': f"TURBINE_BEARING_{bearing_id}",
                                'parameter': 'bearing_temperature',
                                'value': temp,
                                'threshold': thresholds['bearing_temperature'],
                                'action': 'bearing_maintenance',
                                'triggered': True
                            })
            
            # Check vibration levels
            if hasattr(self.turbine, 'rotor_dynamics') and hasattr(self.turbine.rotor_dynamics, 'vibration_monitor'):
                monitor = self.turbine.rotor_dynamics.vibration_monitor
                if hasattr(monitor, 'displacement_amplitude'):
                    vibration = monitor.displacement_amplitude
                    if vibration > thresholds['vibration_level']:
                        events.append({
                            'time_hours': time_hours,
                            'component_id': "TURBINE_ROTOR",
                            'parameter': 'vibration_level',
                            'value': vibration,
                            'threshold': thresholds['vibration_level'],
                            'action': 'vibration_analysis',
                            'triggered': True
                        })
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Turbine monitoring error: {e}")
        
        return events
    
    def _check_feedwater_triggers(self, time_hours: float) -> List[Dict[str, Any]]:
        """Check feedwater system health for maintenance triggers"""
        events = []
        thresholds = self.maintenance_config['thresholds']['feedwater']
        
        try:
            if hasattr(self.feedwater_system, 'pump_system') and hasattr(self.feedwater_system.pump_system, 'pumps'):
                for pump_id, pump in self.feedwater_system.pump_system.pumps.items():
                    # Check bearing temperature
                    if hasattr(pump.state, 'bearing_temperature'):
                        temp = pump.state.bearing_temperature
                        if temp > thresholds['bearing_temperature']:
                            events.append({
                                'time_hours': time_hours,
                                'component_id': f"FW_PUMP_{pump_id}",
                                'parameter': 'bearing_temperature',
                                'value': temp,
                                'threshold': thresholds['bearing_temperature'],
                                'action': 'pump_bearing_maintenance',
                                'triggered': True
                            })
                    
                    # Check efficiency degradation
                    if hasattr(pump.state, 'efficiency_degradation_factor'):
                        degradation = 1.0 - pump.state.efficiency_degradation_factor
                        if degradation > thresholds['pump_efficiency_degradation']:
                            events.append({
                                'time_hours': time_hours,
                                'component_id': f"FW_PUMP_{pump_id}",
                                'parameter': 'efficiency_degradation',
                                'value': degradation,
                                'threshold': thresholds['pump_efficiency_degradation'],
                                'action': 'pump_overhaul',
                                'triggered': True
                            })
                    
                    # Check seal leakage
                    if hasattr(pump.state, 'seal_leakage'):
                        leakage = pump.state.seal_leakage
                        if leakage > thresholds['seal_leakage']:
                            events.append({
                                'time_hours': time_hours,
                                'component_id': f"FW_PUMP_{pump_id}",
                                'parameter': 'seal_leakage',
                                'value': leakage,
                                'threshold': thresholds['seal_leakage'],
                                'action': 'seal_replacement',
                                'triggered': True
                            })
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Feedwater monitoring error: {e}")
        
        return events
    
    def _check_condenser_triggers(self, time_hours: float) -> List[Dict[str, Any]]:
        """Check condenser health for maintenance triggers"""
        events = []
        thresholds = self.maintenance_config['thresholds']['condenser']
        
        try:
            # Check fouling resistance
            if hasattr(self.condenser, 'fouling_system') and hasattr(self.condenser.fouling_system, 'total_fouling_resistance'):
                fouling = self.condenser.fouling_system.total_fouling_resistance
                if fouling > thresholds['fouling_resistance']:
                    events.append({
                        'time_hours': time_hours,
                        'component_id': "CONDENSER",
                        'parameter': 'fouling_resistance',
                        'value': fouling,
                        'threshold': thresholds['fouling_resistance'],
                        'action': 'condenser_cleaning',
                        'triggered': True
                    })
            
            # Check thermal performance
            if hasattr(self.condenser, 'thermal_performance_factor'):
                performance = self.condenser.thermal_performance_factor
                degradation = 1.0 - performance
                if degradation > thresholds['thermal_performance_degradation']:
                    events.append({
                        'time_hours': time_hours,
                        'component_id': "CONDENSER",
                        'parameter': 'thermal_performance_degradation',
                        'value': degradation,
                        'threshold': thresholds['thermal_performance_degradation'],
                        'action': 'condenser_tube_cleaning',
                        'triggered': True
                    })
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Condenser monitoring error: {e}")
        
        return events
    
    # Note: All initial degradation methods removed since degradation is now applied
    # directly in component initial_conditions by the ComprehensiveComposer
