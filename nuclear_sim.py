#!/usr/bin/env python3
"""
Nuclear Plant Simulator - Unified CLI

This is the unified command-line interface for the nuclear plant simulator system.
It provides a single entry point for all nuclear plant simulation operations.

Updated to use the new hierarchical structure.
"""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from data.plant_data_logger import PlantDataLogger
from management.run_manager import RunManager
from scenarios.scenario_generator import ScenarioGenerator, run_scenario
from simulator.core.sim import ControlAction, NuclearPlantSimulator
from visualization.plant_plotter import PlantPlotter


class NuclearSimulatorCLI:
    """Unified CLI for nuclear plant simulator operations"""
    
    def __init__(self):
        """Initialize the CLI"""
        self.run_manager = RunManager()
        self.plotter = PlantPlotter()
        self.scenario_generator = ScenarioGenerator()
    
    def run_scenario_with_logging(self, 
                                 scenario_type: str,
                                 duration: float,
                                 run_name: str,
                                 description: str = "",
                                 tags: Optional[List[str]] = None,
                                 heat_source_type: str = 'reactor') -> str:
        """
        Run a scenario with complete data logging and plotting
        
        Args:
            scenario_type: Type of scenario to run
            duration: Duration in seconds
            run_name: Name for the run
            description: Description of the run
            tags: Tags for categorizing the run
            heat_source_type: Type of heat source ('reactor' or 'constant')
            
        Returns:
            run_id: Unique identifier for the run
        """
        print(f"Nuclear Plant Simulator - Running {scenario_type}")
        print("=" * 60)
        
        # Create run
        run_id = self.run_manager.create_run(
            run_name=run_name,
            description=description,
            scenario_type=scenario_type,
            duration=duration,
            tags=tags or []
        )
        
        run_dir = Path("runs") / run_id
        
        # Initialize plant data logger
        logger = PlantDataLogger(str(run_dir))
        
        print(f"Created run: {run_id}")
        print(f"Data logging: {logger.get_logged_parameter_count()} parameters")
        print(f"CSV file: {logger.get_csv_path()}")
        print()
        
        # Generate scenario
        print("Generating scenario...")
        scenario = self._generate_scenario(scenario_type, duration)
        
        # Create simulator with heat source type
        if heat_source_type == 'constant':
            # Import and use constant heat source
            from systems.primary.reactor.heat_sources import ConstantHeatSource
            heat_source = ConstantHeatSource(rated_power_mw=3000.0)
            simulator = NuclearPlantSimulator(dt=1.0, heat_source=heat_source)
        else:
            # Use default reactor physics
            simulator = NuclearPlantSimulator(dt=1.0)
        
        # Set initial state if provided by scenario
        if scenario.initial_state is not None:
            simulator.reset()
            # Copy initial state values
            simulator.state.fuel_temperature = scenario.initial_state.fuel_temperature
            simulator.state.neutron_flux = scenario.initial_state.neutron_flux
            simulator.state.power_level = scenario.initial_state.power_level
            simulator.state.control_rod_position = scenario.initial_state.control_rod_position
        else:
            simulator.reset()
        
        print(f"Running scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Duration: {scenario.duration:.0f} seconds")
        print("-" * 50)
        
        # Create action schedule
        action_schedule = {}
        if scenario.actions:
            for action in scenario.actions:
                rounded_time = round(action.time)
                action_schedule[rounded_time] = action
        
        # Run simulation with real-time logging
        current_time = 0.0
        step_count = 0
        
        print("Starting simulation...")
        print(f"{'Time (s)':<8} {'Power (%)':<10} {'Fuel T (°C)':<12} {'Rod Pos (%)':<12} {'Status':<15}")
        print("-" * 65)
        
        while current_time < scenario.duration:
            # Check for scheduled actions
            action_to_apply = None
            magnitude = 1.0
            
            time_key = int(current_time)
            if time_key in action_schedule:
                scenario_action = action_schedule[time_key]
                action_to_apply = scenario_action.action
                magnitude = scenario_action.magnitude
                print(f"Action: {scenario_action.description}")
            
            # Step the simulation
            result = simulator.step(action_to_apply, magnitude)
            
            # Log all parameters to CSV in real-time
            logger.log_timestep(simulator)
            
            # Print status every 30 seconds
            if step_count % 30 == 0:
                status = "SCRAM" if simulator.state.scram_status else "Normal"
                print(f"{current_time:<8.0f} {simulator.state.power_level:<10.1f} "
                      f"{simulator.state.fuel_temperature:<12.0f} "
                      f"{simulator.state.control_rod_position:<12.1f} {status:<15}")
            
            # Check for early termination
            if result['done']:
                print(f"\nScenario terminated early at {current_time:.0f}s due to safety system activation")
                break
            
            current_time += simulator.dt
            step_count += 1
        
        print(f"\nSimulation completed!")
        print(f"Final power level: {simulator.state.power_level:.1f}%")
        print(f"Total timesteps: {step_count}")
        print(f"Data logged to: {logger.get_csv_path()}")
        
        # Generate automatic plots
        print("\nGenerating plots...")
        csv_path = logger.get_csv_path()
        
        # Overview plot
        self.plotter.plot_overview(
            csv_path,
            title=f"Nuclear Plant Overview - {run_name}",
            save_path=str(run_dir / "plots" / "overview.png"),
            show_plot=False
        )
        
        # Power parameters
        self.plotter.plot_parameter_group(
            csv_path, 'power',
            title=f"Power Parameters - {run_name}",
            save_path=str(run_dir / "plots" / "power_parameters.png"),
            show_plot=False
        )
        
        # Temperature parameters
        self.plotter.plot_parameter_group(
            csv_path, 'temperatures',
            title=f"Temperature Parameters - {run_name}",
            save_path=str(run_dir / "plots" / "temperature_parameters.png"),
            show_plot=False
        )
        
        # Control parameters
        self.plotter.plot_parameter_group(
            csv_path, 'control',
            title=f"Control Parameters - {run_name}",
            save_path=str(run_dir / "plots" / "control_parameters.png"),
            show_plot=False
        )
        
        print("Generated plots:")
        print("  - overview.png: Key plant parameters")
        print("  - power_parameters.png: Power-related parameters")
        print("  - temperature_parameters.png: Temperature parameters")
        print("  - control_parameters.png: Control system parameters")
        
        # Update run metadata
        metadata = self.run_manager.get_run(run_id)
        if metadata:
            metadata.success = not simulator.state.scram_status
            metadata.total_timesteps = step_count
            metadata.final_power_level = simulator.state.power_level
            metadata.artifacts_generated = [
                "data/timeseries.csv",
                "plots/overview.png",
                "plots/power_parameters.png", 
                "plots/temperature_parameters.png",
                "plots/control_parameters.png"
            ]
            self.run_manager.runs_index[run_id] = metadata
            self.run_manager._save_runs_index()
        
        print(f"\n✅ Run {run_id} completed successfully!")
        print(f"All data and plots saved to: runs/{run_id}/")
        
        return run_id
    
    def _generate_scenario(self, scenario_type: str, duration: float):
        """Generate a scenario based on type"""
        if scenario_type == "normal_operation":
            return self.scenario_generator.generate_normal_operation(duration)
        elif scenario_type == "power_ramp_up":
            return self.scenario_generator.generate_power_ramp_up(duration=duration)
        elif scenario_type == "power_ramp_down":
            return self.scenario_generator.generate_power_ramp_down(duration=duration)
        elif scenario_type == "load_following":
            return self.scenario_generator.generate_load_following(duration)
        elif scenario_type == "steam_line_break":
            return self.scenario_generator.generate_steam_line_break(duration)
        elif scenario_type == "loss_of_coolant":
            return self.scenario_generator.generate_loss_of_coolant(duration)
        elif scenario_type == "turbine_trip":
            return self.scenario_generator.generate_turbine_trip(duration)
        else:
            return self.scenario_generator.generate_normal_operation(duration)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Nuclear Plant Simulator - Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a normal operation scenario
  python nuclear_sim.py run normal_operation --name "Baseline Test" --duration 600
  
  # Run with constant heat source
  python nuclear_sim.py run normal_operation --name "Constant Heat Test" --heat-source constant
  
  # List all runs
  python nuclear_sim.py list
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a nuclear plant scenario')
    run_parser.add_argument('scenario_type', 
                           choices=['normal_operation', 'power_ramp_up', 'power_ramp_down',
                                   'load_following', 'steam_line_break', 'loss_of_coolant', 'turbine_trip'],
                           help='Type of scenario to run')
    run_parser.add_argument('--name', required=True, help='Name for the run')
    run_parser.add_argument('--description', default='', help='Description of the run')
    run_parser.add_argument('--duration', type=float, default=600, help='Duration in seconds (default: 600)')
    run_parser.add_argument('--tags', help='Comma-separated tags')
    run_parser.add_argument('--heat-source', choices=['reactor', 'constant'], default='reactor',
                           help='Type of heat source to use (default: reactor)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all runs')
    list_parser.add_argument('--tags', help='Filter by comma-separated tags')
    list_parser.add_argument('--scenario-type', help='Filter by scenario type')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = NuclearSimulatorCLI()
    
    try:
        if args.command == 'run':
            tags = args.tags.split(',') if args.tags else None
            run_id = cli.run_scenario_with_logging(
                scenario_type=args.scenario_type,
                duration=args.duration,
                run_name=args.name,
                description=args.description,
                tags=tags,
                heat_source_type=getattr(args, 'heat_source', 'reactor')
            )
            print(f"\nRun ID: {run_id}")
        
        elif args.command == 'list':
            runs = cli.run_manager.list_runs(
                tags=args.tags.split(',') if args.tags else None,
                scenario_type=args.scenario_type
            )
            
            if not runs:
                print("No runs found")
                return
            
            print(f"{'Run ID':<35} {'Name':<25} {'Scenario':<20} {'Status':<8} {'Created':<20}")
            print("-" * 115)
            
            for run in runs:
                status = "✓ Success" if run.success else "✗ Failed"
                created = run.created_at[:19].replace('T', ' ')
                print(f"{run.run_id:<35} {run.run_name[:24]:<25} {run.scenario_type:<20} {status:<8} {created:<20}")
            
            print(f"\nTotal runs: {len(runs)}")
        
        elif args.command == 'status':
            runs = cli.run_manager.list_runs()
            total_runs = len(runs)
            successful_runs = sum(1 for run in runs if run.success)
            
            print("Nuclear Plant Simulator Status")
            print("=" * 40)
            print(f"Total Runs: {total_runs}")
            print(f"Successful: {successful_runs}")
            print(f"Failed: {total_runs - successful_runs}")
            print(f"Success Rate: {(successful_runs/total_runs*100):.1f}%" if total_runs > 0 else "N/A")
            
            if runs:
                recent_runs = sorted(runs, key=lambda x: x.created_at, reverse=True)[:5]
                print(f"\nRecent Runs:")
                for run in recent_runs:
                    status = "✓" if run.success else "✗"
                    created = run.created_at[:19].replace('T', ' ')
                    print(f"  {status} {run.run_id} ({run.scenario_type}) - {created}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
