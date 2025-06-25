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
from pathlib import Path
from typing import Dict, List, Any, Optional
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

# Import maintenance system (simplified for now)
try:
    from systems.maintenance.work_orders import WorkOrderType, Priority
except ImportError:
    # Create simple enums if not available
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
    
    def __init__(self, config: Dict[str, Any], verbose: bool = True):
        """
        Initialize the maintenance scenario runner
        
        Args:
            config: Configuration dictionary from ComprehensiveComposer
            verbose: Enable verbose output
        """
        self.config = config
        self.verbose = verbose
        self.simulator = None
        self.maintenance_system = None
        
        # Data collection
        self.simulation_data = []
        self.maintenance_events = []
        self.component_health_data = []
        
        # Results tracking
        self.target_action = config['metadata']['target_action']
        self.target_subsystem = config['metadata']['target_subsystem']
        self.subsystem_modes = config['metadata'].get('subsystem_modes', {})
        self.duration_hours = config['simulation_config']['duration_hours']
        
        # Initialize simulator
        self._initialize_simulator()
        
        if self.verbose:
            print(f"🔧 MaintenanceScenarioRunner initialized")
            print(f"   Target action: {self.target_action}")
            print(f"   Target subsystem: {self.target_subsystem}")
            print(f"   Duration: {self.duration_hours} hours")
    
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
            secondary_config = self.config.get('secondary_system', {})
            self.simulator = NuclearPlantSimulator(
                heat_source=heat_source,
                dt=time_step_minutes,  # Use minutes directly
                enable_secondary=True,  # Always enable secondary system
                enable_state_management=True,
                secondary_config=secondary_config  # Use secondary_system section from comprehensive config
            )
            
            # Initialize maintenance monitoring
            self._initialize_maintenance_monitoring()
            
            # Reset to steady state
            self.simulator.reset(start_at_steady_state=True)
            
            # Apply initial degradation after simulator is initialized
            self._apply_initial_degradation()
            
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
        """Initialize maintenance monitoring using the existing auto maintenance system"""
        try:
            # Check if secondary system is available
            if hasattr(self.simulator, 'secondary_physics') and self.simulator.secondary_physics:
                self.secondary_system = self.simulator.secondary_physics
                
                # Get component references for degradation application
                self.steam_generators = getattr(self.secondary_system, 'steam_generator_system', None)
                self.turbine = getattr(self.secondary_system, 'turbine', None)
                self.feedwater_system = getattr(self.secondary_system, 'feedwater_system', None)
                self.condenser = getattr(self.secondary_system, 'condenser', None)
                
                # Get the auto maintenance system from the simulator
                if hasattr(self.simulator, 'maintenance_system') and self.simulator.maintenance_system:
                    self.auto_maintenance_system = self.simulator.maintenance_system
                    
                    # CRITICAL FIX: Apply explicit maintenance configuration instead of forcing re-discovery
                    # This ensures our subsystem-specific config is used directly
                    if self.verbose:
                        print(f"   🔧 Applying explicit subsystem-specific config to auto maintenance system")
                    
                    # Reset maintenance config state to ensure clean application
                    self.auto_maintenance_system.reset_maintenance_config()
                    
                    # Apply our subsystem-specific configuration explicitly
                    self.auto_maintenance_system.apply_explicit_maintenance_config(self.config)
                    
                    # Now discover components with the explicit config already set
                    if hasattr(self.simulator, 'state_manager'):
                        # Clear existing registrations cleanly
                        self.auto_maintenance_system.event_bus.reset()
                        
                        # Discover components using the explicitly set config
                        self.auto_maintenance_system.discover_components_from_state_manager(
                            self.simulator.state_manager, 
                            aggressive_mode=True  # Use aggressive mode for better triggering
                        )
                    
                    self.maintenance_system = True
                    
                    if self.verbose:
                        print(f"   ✅ Auto maintenance system configured with explicit subsystem-specific config")
                        
                        # Get auto maintenance status
                        status = self.auto_maintenance_system.get_system_status()
                        print(f"   📊 Auto maintenance check interval: {status['check_interval_hours']} hours")
                        print(f"   🚀 Auto execution enabled: {status['auto_execute_enabled']}")
                        print(f"   📋 Work orders created: {status['work_orders_created']}")
                        print(f"   🔧 Work orders executed: {status['work_orders_executed']}")
                        
                        # Get component summary
                        components = self.auto_maintenance_system.get_component_summary()
                        print(f"   🏭 Components monitored: {len(components)}")
                        
                        # Show subsystem-specific configuration status
                        maintenance_system_config = self.config.get('maintenance_system', {})
                        component_configs = maintenance_system_config.get('component_configs', {})
                        print(f"   🎯 Subsystem configs applied: {list(component_configs.keys())}")
                        for subsystem, config_data in component_configs.items():
                            mode = config_data.get('mode', 'unknown')
                            thresholds = len(config_data.get('thresholds', {}))
                            print(f"      {subsystem}: {mode} mode, {thresholds} thresholds")
                else:
                    self.maintenance_system = None
                    if self.verbose:
                        print(f"   ⚠️ Auto maintenance system not available")
                        print(f"   🏭 Components available: SG={self.steam_generators is not None}, "
                              f"Turbine={self.turbine is not None}, FW={self.feedwater_system is not None}, "
                              f"Condenser={self.condenser is not None}")
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
    
    def _get_aggressive_thresholds(self):
        """Get conservative thresholds for realistic maintenance triggering"""
        # These are realistic thresholds based on industry standards
        return {
            'steam_generator': {
                'tsp_fouling_thickness': 2.0,  # mm - realistic fouling thickness
                'tube_wall_temperature': 320.0,  # °C - closer to actual alarm point
                'steam_quality': 0.97,  # fraction - realistic degradation threshold
                'heat_transfer_degradation': 0.10  # fraction - 10% degradation
            },
            'turbine': {
                'bearing_temperature': 110.0,  # °C - industry standard alarm
                'vibration_level': 15.0,  # mils - typical alarm threshold
                'efficiency_degradation': 0.05,  # fraction - 5% degradation
                'oil_contamination': 15.0  # ppm - realistic contamination level
            },
            'feedwater': {
                'pump_efficiency_degradation': 0.08,  # fraction - 8% degradation
                'bearing_temperature': 110.0,  # °C - industry standard
                'vibration_level': 20.0,  # mils - pump vibration alarm
                'seal_leakage': 1.0  # L/min - realistic leakage threshold
            },
            'condenser': {
                'thermal_performance_degradation': 0.20,  # fraction - 20% degradation
                'fouling_resistance': 0.002,  # m²K/W - realistic fouling resistance
                'vacuum_efficiency_degradation': 0.25  # fraction - 25% degradation
            }
        }
    
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
        
        # Calculate simulation parameters
        duration_minutes = int(self.duration_hours * 60)
        
        # Generate power profile
        power_profile = self._generate_power_profile(duration_minutes)
        
        # Track maintenance triggering
        maintenance_triggered = False
        work_orders_created = 0
        
        # Run simulation
        start_time = time.time()
        
        for t in range(duration_minutes):
            # Set target power
            target_power = power_profile[t]
            self._set_target_power(target_power)
            
            # Step simulator
            result = self.simulator.step(action=ControlAction.NO_ACTION)
            
            # Simulate component degradation to trigger maintenance
            self._simulate_component_degradation(t)
            
            # Check for maintenance triggers
            maintenance_events = self._check_maintenance_triggers(t)
            if maintenance_events:
                maintenance_triggered = True
                work_orders_created += len(maintenance_events)
                self.maintenance_events.extend(maintenance_events)
            
            # Collect data
            self._collect_simulation_data(t, result, target_power, maintenance_events)
            
            # Print status every 10 minutes
            if t % 10 == 0 and self.verbose:
                print(f"{t:<10} {self.simulator.state.power_level:<10.1f} "
                      f"{len(maintenance_events):<18} {work_orders_created:<12}")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Generate results
        results = {
            'success': maintenance_triggered,
            'target_action': self.target_action,
            'target_subsystem': self.target_subsystem,
            'duration_hours': self.duration_hours,
            'execution_time_seconds': execution_time,
            'work_orders_created': work_orders_created,
            'maintenance_events': len(self.maintenance_events),
            'simulation_data_points': len(self.simulation_data),
            'final_power_level': self.simulator.state.power_level
        }
        
        if self.verbose:
            print(f"\n📋 Scenario Results:")
            print(f"   ✅ Success: {maintenance_triggered}")
            print(f"   🔧 Work orders created: {work_orders_created}")
            print(f"   📊 Maintenance events: {len(self.maintenance_events)}")
            print(f"   ⏱️ Execution time: {execution_time:.1f}s")
        
        return results
    
    def _generate_power_profile(self, duration_minutes: int) -> np.ndarray:
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
        
        # Generate profile
        time_points = np.arange(duration_minutes)
        noise = noise_std * np.random.normal(0, 1, duration_minutes)
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
        """Check if maintenance should be triggered using the auto maintenance system"""
        events = []
        
        if not self.maintenance_system or not hasattr(self, 'auto_maintenance_system'):
            return events
        
        time_hours = time_step / 60.0
        
        try:
            # Get work orders created by the auto maintenance system
            # The auto maintenance system runs its own update cycle during simulator.step()
            # We just need to check for new work orders
            
            # Get current work order count
            current_status = self.auto_maintenance_system.get_system_status()
            current_work_orders = current_status['work_orders_created']
            
            # Check if new work orders were created since last check
            if not hasattr(self, '_last_work_order_count'):
                self._last_work_order_count = 0
            
            new_work_orders = current_work_orders - self._last_work_order_count
            
            if new_work_orders > 0:
                # Get recent work orders from the auto maintenance system
                recent_orders = self.auto_maintenance_system.get_recent_work_orders(limit=new_work_orders)
                
                # Convert work orders to maintenance events
                for work_order in recent_orders[-new_work_orders:]:  # Get the newest ones
                    event = {
                        'time_hours': time_hours,
                        'component_id': work_order['component_id'],
                        'parameter': 'auto_maintenance_trigger',
                        'value': 1.0,
                        'threshold': 1.0,
                        'action': work_order['maintenance_actions'][0]['action_type'] if work_order['maintenance_actions'] else 'unknown',
                        'triggered': True,
                        'work_order_id': work_order['work_order_id'],
                        'priority': work_order['priority'],
                        'trigger_reason': work_order['description']
                    }
                    events.append(event)
                    
                    if self.verbose:
                        print(f"   🚨 AUTO MAINTENANCE: {work_order['work_order_id']} - {event['action']} on {event['component_id']}")
                
                # Update the work order count
                self._last_work_order_count = current_work_orders
                
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Warning: Auto maintenance check failed: {e}")
        
        return events
    
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
        """Collect simulation data"""
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
        
        # Add component parameters if available
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
        """Export simulation data to CSV files"""
        if filename_prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"{self.target_action}_{timestamp}"
        
        exported_files = []
        
        # Export simulation data
        if self.simulation_data:
            filename = f"{filename_prefix}_simulation_data.csv"
            exported_files.append(filename)
            self.simulator.state_manager.export_by_category('secondary', filename=filename)
            if self.verbose:
                print(f"📄 Simulation data exported to {filename}")
        
        # Export maintenance events
        if self.maintenance_events:
            events_df = pd.DataFrame(self.maintenance_events)
            filename = f"{filename_prefix}_maintenance_events.csv"
            events_df.to_csv(filename, index=False)
            exported_files.append(filename)
            if self.verbose:
                print(f"📄 Maintenance events exported to {filename}")
        
        return exported_files
    
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
    
    def _apply_initial_degradation(self):
        """Apply initial degradation from config to component states"""
        initial_degradation = self.config.get('initial_degradation', {})
        
        if not initial_degradation:
            if self.verbose:
                print(f"   📊 No initial degradation specified")
            return
        
        if self.verbose:
            print(f"   🎯 Applying initial degradation for {self.target_action}")
        
        degradation_applied = 0
        
        try:
            # CRITICAL FIX: Only apply degradation to the target subsystem
            # This prevents cross-contamination between subsystems
            
            # Apply feedwater pump degradation ONLY if targeting feedwater
            if (self.target_subsystem == "feedwater" and 
                self.feedwater_system and hasattr(self.feedwater_system, 'pump_system')):
                degradation_applied += self._apply_feedwater_degradation(initial_degradation)
            
            # Apply turbine degradation ONLY if targeting turbine
            if self.target_subsystem == "turbine" and self.turbine:
                degradation_applied += self._apply_turbine_degradation(initial_degradation)
            
            # Apply steam generator degradation ONLY if targeting steam_generator
            if self.target_subsystem == "steam_generator" and self.steam_generators:
                degradation_applied += self._apply_steam_generator_degradation(initial_degradation)
            
            # Apply condenser degradation ONLY if targeting condenser
            if self.target_subsystem == "condenser" and self.condenser:
                degradation_applied += self._apply_condenser_degradation(initial_degradation)
            
            if self.verbose:
                print(f"   ✅ Applied {degradation_applied} degradation parameters")
                
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Error applying initial degradation: {e}")
    
    def _apply_feedwater_degradation(self, degradation: Dict[str, Any]) -> int:
        """Apply feedwater-specific degradation"""
        applied = 0
        
        if hasattr(self.feedwater_system.pump_system, 'pumps'):
            for pump_id, pump in self.feedwater_system.pump_system.pumps.items():
                # Oil level degradation - apply to both pump and lubrication system
                if 'feedwater_pump_oil_level' in degradation:
                    # Apply to pump state
                    pump.state.oil_level = degradation['feedwater_pump_oil_level']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} oil level set to {pump.state.oil_level}%")
                    
                    # Also apply to lubrication system if it exists
                    if hasattr(pump, 'lubrication_system') and pump.lubrication_system:
                        # The lubrication system has a different structure - check what attributes it has
                        if hasattr(pump.lubrication_system, 'oil_level'):
                            pump.lubrication_system.oil_level = degradation['feedwater_pump_oil_level']
                            applied += 1
                            if self.verbose:
                                print(f"     🔧 {pump_id}-LUB oil level set to {pump.lubrication_system.oil_level}%")
                        elif hasattr(pump.lubrication_system, 'state') and hasattr(pump.lubrication_system.state, 'oil_level'):
                            pump.lubrication_system.state.oil_level = degradation['feedwater_pump_oil_level']
                            applied += 1
                            if self.verbose:
                                print(f"     🔧 {pump_id}-LUB oil level set to {pump.lubrication_system.state.oil_level}%")
                        else:
                            # Try to find the oil level attribute in the lubrication system
                            for attr_name in dir(pump.lubrication_system):
                                if 'oil_level' in attr_name.lower() and not attr_name.startswith('_'):
                                    try:
                                        setattr(pump.lubrication_system, attr_name, degradation['feedwater_pump_oil_level'])
                                        applied += 1
                                        if self.verbose:
                                            print(f"     🔧 {pump_id}-LUB {attr_name} set to {degradation['feedwater_pump_oil_level']}%")
                                        break
                                    except:
                                        continue
                
                # Bearing wear degradation
                if 'feedwater_pump_bearing_wear' in degradation:
                    pump.state.bearing_wear = degradation['feedwater_pump_bearing_wear']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} bearing wear set to {pump.state.bearing_wear}%")
                
                # Bearing temperature degradation
                if 'feedwater_pump_bearing_temperature' in degradation:
                    pump.state.bearing_temperature = degradation['feedwater_pump_bearing_temperature']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} bearing temperature set to {pump.state.bearing_temperature}°C")
                
                # Impeller wear degradation
                if 'feedwater_pump_impeller_wear' in degradation:
                    pump.state.impeller_wear = degradation['feedwater_pump_impeller_wear']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} impeller wear set to {pump.state.impeller_wear}%")
                
                # Seal wear degradation
                if 'feedwater_pump_seal_wear' in degradation:
                    pump.state.seal_wear = degradation['feedwater_pump_seal_wear']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} seal wear set to {pump.state.seal_wear}%")
                
                # Vibration level degradation
                if 'feedwater_pump_vibration_level' in degradation:
                    pump.state.vibration_level = degradation['feedwater_pump_vibration_level']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} vibration level set to {pump.state.vibration_level} mm/s")
                
                # Efficiency degradation
                if 'feedwater_pump_efficiency_degradation' in degradation:
                    pump.state.efficiency_degradation_factor = degradation['feedwater_pump_efficiency_degradation']
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 {pump_id} efficiency factor set to {pump.state.efficiency_degradation_factor}")
                
                # Apply degradation acceleration if specified
                if 'feedwater_degradation_acceleration' in degradation:
                    acceleration = degradation['feedwater_degradation_acceleration']
                    # Increase wear rates
                    pump.base_impeller_wear_rate *= acceleration
                    pump.base_bearing_wear_rate *= acceleration
                    pump.base_seal_wear_rate *= acceleration
                    applied += 1
                    if self.verbose:
                        print(f"     🚀 {pump_id} degradation acceleration: {acceleration}x")
        
        return applied
    
    def _apply_turbine_degradation(self, degradation: Dict[str, Any]) -> int:
        """Apply turbine-specific degradation"""
        applied = 0
        
        # Bearing temperature degradation
        if 'turbine_bearing_temperature' in degradation:
            # Apply to turbine bearing system if available
            if hasattr(self.turbine, 'bearing_system'):
                # Set a representative bearing temperature
                setattr(self.turbine, '_degraded_bearing_temperature', degradation['turbine_bearing_temperature'])
                applied += 1
                if self.verbose:
                    print(f"     🔧 Turbine bearing temperature set to {degradation['turbine_bearing_temperature']}°C")
        
        # Vibration level degradation
        if 'turbine_vibration_level' in degradation:
            setattr(self.turbine, '_degraded_vibration_level', degradation['turbine_vibration_level'])
            applied += 1
            if self.verbose:
                print(f"     🔧 Turbine vibration level set to {degradation['turbine_vibration_level']} mils")
        
        # Oil contamination degradation
        if 'turbine_oil_contamination' in degradation:
            setattr(self.turbine, '_degraded_oil_contamination', degradation['turbine_oil_contamination'])
            applied += 1
            if self.verbose:
                print(f"     🔧 Turbine oil contamination set to {degradation['turbine_oil_contamination']} ppm")
        
        # Oil level degradation
        if 'turbine_oil_level' in degradation:
            setattr(self.turbine, '_degraded_oil_level', degradation['turbine_oil_level'])
            applied += 1
            if self.verbose:
                print(f"     🔧 Turbine oil level set to {degradation['turbine_oil_level']}%")
        
        # Efficiency degradation
        if 'turbine_efficiency' in degradation:
            setattr(self.turbine, '_degraded_efficiency', degradation['turbine_efficiency'])
            applied += 1
            if self.verbose:
                print(f"     🔧 Turbine efficiency set to {degradation['turbine_efficiency']}")
        
        return applied
    
    def _apply_steam_generator_degradation(self, degradation: Dict[str, Any]) -> int:
        """Apply steam generator-specific degradation"""
        applied = 0
        
        # TSP fouling degradation
        if 'steam_generator_tsp_fouling_fraction' in degradation:
            if hasattr(self.steam_generators, 'steam_generators'):
                for sg in self.steam_generators.steam_generators:
                    if hasattr(sg, 'tsp_fouling'):
                        sg.tsp_fouling.fouling_fraction = degradation['steam_generator_tsp_fouling_fraction']
                        applied += 1
                        if self.verbose:
                            print(f"     🔧 SG TSP fouling set to {sg.tsp_fouling.fouling_fraction}")
        
        # Tube wall temperature degradation
        if 'steam_generator_tube_wall_temperature' in degradation:
            if hasattr(self.steam_generators, 'steam_generators'):
                for sg in self.steam_generators.steam_generators:
                    setattr(sg, '_degraded_tube_wall_temp', degradation['steam_generator_tube_wall_temperature'])
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 SG tube wall temperature set to {degradation['steam_generator_tube_wall_temperature']}°C")
        
        # Steam quality degradation
        if 'steam_generator_steam_quality' in degradation:
            if hasattr(self.steam_generators, 'steam_generators'):
                for sg in self.steam_generators.steam_generators:
                    setattr(sg, '_degraded_steam_quality', degradation['steam_generator_steam_quality'])
                    applied += 1
                    if self.verbose:
                        print(f"     🔧 SG steam quality set to {degradation['steam_generator_steam_quality']}")
        
        return applied
    
    def _apply_condenser_degradation(self, degradation: Dict[str, Any]) -> int:
        """Apply condenser-specific degradation"""
        applied = 0
        
        # Fouling resistance degradation
        if 'condenser_tube_fouling_resistance' in degradation:
            if hasattr(self.condenser, 'fouling_system'):
                setattr(self.condenser.fouling_system, '_degraded_fouling_resistance', 
                       degradation['condenser_tube_fouling_resistance'])
                applied += 1
                if self.verbose:
                    print(f"     🔧 Condenser fouling resistance set to {degradation['condenser_tube_fouling_resistance']}")
        
        # Thermal performance degradation
        if 'condenser_thermal_performance' in degradation:
            setattr(self.condenser, '_degraded_thermal_performance', degradation['condenser_thermal_performance'])
            applied += 1
            if self.verbose:
                print(f"     🔧 Condenser thermal performance set to {degradation['condenser_thermal_performance']}")
        
        # Vacuum efficiency degradation
        if 'condenser_vacuum_efficiency' in degradation:
            setattr(self.condenser, '_degraded_vacuum_efficiency', degradation['condenser_vacuum_efficiency'])
            applied += 1
            if self.verbose:
                print(f"     🔧 Condenser vacuum efficiency set to {degradation['condenser_vacuum_efficiency']}")
        
        return applied
