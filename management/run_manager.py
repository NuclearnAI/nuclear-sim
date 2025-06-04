"""
Nuclear Simulator Run Management System

This module provides a comprehensive run-based system for managing nuclear plant simulations,
organizing all artifacts, results, and metadata in a structured way.
"""

import json
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

# Add parent directory to path so we can import from core and data_generation
sys.path.append(str(Path(__file__).parent.parent))

from data.gen_training_data import TrainingDataGenerator, TrainingExample
from data.plant_data_logger import PlantDataLogger
from scenarios.scenario_generator import Scenario, ScenarioGenerator, run_scenario
from simulator.core.sim import NuclearPlantSimulator
from visualization.plant_plotter import PlantPlotter


@dataclass
class RunMetadata:
    """Metadata for a simulation run"""
    run_id: str
    run_name: str
    description: str
    created_at: str
    duration_seconds: float
    scenario_type: str
    scenario_name: str
    success: bool
    total_timesteps: int
    safety_events: int
    final_power_level: float
    max_fuel_temperature: float
    min_fuel_temperature: float
    average_power_level: float
    control_actions_count: int
    artifacts_generated: List[str]
    tags: List[str]
    parameters: Dict[str, Any]


@dataclass
class RunArtifacts:
    """Container for all run artifacts"""
    timeseries_data: List[Dict[str, Any]]
    scenario_definition: Dict[str, Any]
    simulator_state: Dict[str, Any]
    plots: List[str]  # Plot file paths
    training_data: Optional[TrainingExample]
    logs: List[str]
    statistics: Dict[str, Any]


class RunManager:
    """Manages simulation runs and their artifacts"""
    
    def __init__(self, base_runs_dir: str = "runs"):
        """
        Initialize the run manager
        
        Args:
            base_runs_dir: Base directory for storing all runs
        """
        self.base_runs_dir = Path(base_runs_dir)
        self.base_runs_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.runs_index_file = self.base_runs_dir / "runs_index.json"
        self.templates_dir = self.base_runs_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Load existing runs index
        self.runs_index = self._load_runs_index()
        
        # Initialize components
        self.scenario_generator = ScenarioGenerator()
        self.training_generator = TrainingDataGenerator()
    
    def _load_runs_index(self) -> Dict[str, RunMetadata]:
        """Load the runs index from disk"""
        if self.runs_index_file.exists():
            try:
                with open(self.runs_index_file, 'r') as f:
                    data = json.load(f)
                    return {
                        run_id: RunMetadata(**metadata) 
                        for run_id, metadata in data.items()
                    }
            except Exception as e:
                print(f"Warning: Could not load runs index: {e}")
        return {}
    
    def _save_runs_index(self):
        """Save the runs index to disk"""
        try:
            data = {
                run_id: asdict(metadata) 
                for run_id, metadata in self.runs_index.items()
            }
            with open(self.runs_index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save runs index: {e}")
    
    def create_run(self, 
                   run_name: str,
                   description: str = "",
                   scenario_type: str = "normal_operation",
                   duration: float = 600.0,
                   tags: Optional[List[str]] = None,
                   parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new simulation run
        
        Args:
            run_name: Human-readable name for the run
            description: Description of the run purpose
            scenario_type: Type of scenario to run
            duration: Duration in seconds
            tags: Tags for categorizing the run
            parameters: Additional parameters for the run
            
        Returns:
            run_id: Unique identifier for the run
        """
        # Generate unique run ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{scenario_type}_{timestamp}"
        
        # Create run directory structure
        run_dir = self.base_runs_dir / run_id
        run_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (run_dir / "data").mkdir(exist_ok=True)
        (run_dir / "plots").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        (run_dir / "config").mkdir(exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        
        # Initialize metadata
        metadata = RunMetadata(
            run_id=run_id,
            run_name=run_name,
            description=description,
            created_at=datetime.now().isoformat(),
            duration_seconds=duration,
            scenario_type=scenario_type,
            scenario_name="",
            success=False,
            total_timesteps=0,
            safety_events=0,
            final_power_level=0.0,
            max_fuel_temperature=0.0,
            min_fuel_temperature=float('inf'),
            average_power_level=0.0,
            control_actions_count=0,
            artifacts_generated=[],
            tags=tags or [],
            parameters=parameters or {}
        )
        
        # Save initial metadata
        self.runs_index[run_id] = metadata
        self._save_runs_index()
        
        # Save run configuration
        config = {
            "run_id": run_id,
            "run_name": run_name,
            "description": description,
            "scenario_type": scenario_type,
            "duration": duration,
            "tags": tags or [],
            "parameters": parameters or {},
            "created_at": metadata.created_at
        }
        
        with open(run_dir / "config" / "run_config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Created new run: {run_id}")
        print(f"Run directory: {run_dir}")
        
        return run_id
    
    def execute_run(self, run_id: str) -> bool:
        """
        Execute a simulation run
        
        Args:
            run_id: ID of the run to execute
            
        Returns:
            success: Whether the run completed successfully
        """
        if run_id not in self.runs_index:
            print(f"Run {run_id} not found")
            return False
        
        metadata = self.runs_index[run_id]
        run_dir = self.base_runs_dir / run_id
        
        print(f"Executing run: {run_id}")
        print(f"Scenario: {metadata.scenario_type}")
        print(f"Duration: {metadata.duration_seconds} seconds")
        print("=" * 50)
        
        try:
            # Generate scenario
            scenario = self._generate_scenario(metadata.scenario_type, metadata.duration_seconds)
            metadata.scenario_name = scenario.name
            
            # Save scenario definition
            scenario_dict = {
                "name": scenario.name,
                "scenario_type": scenario.scenario_type.value if hasattr(scenario.scenario_type, 'value') else str(scenario.scenario_type),
                "duration": scenario.duration,
                "description": scenario.description,
                "actions": [
                    {
                        "time": action.time,
                        "action": action.action.value if hasattr(action.action, 'value') else str(action.action),
                        "magnitude": action.magnitude,
                        "description": action.description
                    }
                    for action in (scenario.actions or [])
                ]
            }
            
            with open(run_dir / "config" / "scenario.json", 'w') as f:
                json.dump(scenario_dict, f, indent=2)
            
            # Execute scenario
            start_time = time.time()
            result = run_scenario(scenario)
            execution_time = time.time() - start_time
            
            # Update metadata with results
            metadata.success = result['success']
            metadata.total_timesteps = len(result['results'])
            metadata.safety_events = sum(1 for r in result['results'] if r['done'])
            metadata.final_power_level = result['simulator'].state.power_level
            metadata.control_actions_count = len(scenario.actions or [])
            
            # Calculate statistics
            power_levels = [r['observation'][10] * 100 for r in result['results']]  # Power level is index 10
            fuel_temps = [r['observation'][1] * 1000 for r in result['results']]   # Fuel temp is index 1
            
            metadata.average_power_level = float(np.mean(power_levels))
            metadata.max_fuel_temperature = float(np.max(fuel_temps))
            metadata.min_fuel_temperature = float(np.min(fuel_temps))
            
            # Save artifacts
            artifacts = self._save_run_artifacts(run_id, result, scenario)
            metadata.artifacts_generated = artifacts
            
            # Generate plots
            plot_files = self._generate_run_plots(run_id, result)
            metadata.artifacts_generated.extend(plot_files)
            
            # Generate training data if applicable
            if metadata.scenario_type in ['control_rod_malfunction', 'steam_generator_tube_leak', 'feedwater_pump_failure']:
                training_data = self._generate_training_data(run_id, result)
                if training_data:
                    metadata.artifacts_generated.append("training_data.json")
            
            # Save execution log
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "execution_time_seconds": execution_time,
                "success": result['success'],
                "final_state": {
                    "power_level": result['simulator'].state.power_level,
                    "fuel_temperature": result['simulator'].state.fuel_temperature,
                    "coolant_temperature": result['simulator'].state.coolant_temperature,
                    "scram_status": result['simulator'].state.scram_status
                }
            }
            
            with open(run_dir / "logs" / "execution.json", 'w') as f:
                json.dump(log_entry, f, indent=2)
            
            # Update and save metadata
            self.runs_index[run_id] = metadata
            self._save_runs_index()
            
            print(f"Run {run_id} completed successfully!")
            print(f"Execution time: {execution_time:.2f} seconds")
            print(f"Artifacts generated: {len(metadata.artifacts_generated)}")
            
            return True
            
        except Exception as e:
            print(f"Error executing run {run_id}: {e}")
            
            # Save error log
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            }
            
            with open(run_dir / "logs" / "error.json", 'w') as f:
                json.dump(error_log, f, indent=2)
            
            return False
    
    def _generate_scenario(self, scenario_type: str, duration: float) -> Scenario:
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
    
    def _save_run_artifacts(self, run_id: str, result: Dict, scenario: Scenario) -> List[str]:
        """Save all run artifacts"""
        run_dir = self.base_runs_dir / run_id
        artifacts = []
        
        # Save timeseries data
        timeseries_file = run_dir / "data" / "timeseries.json"
        timeseries_data = []
        
        for r in result['results']:
            # Convert numpy arrays to lists for JSON serialization
            observation = r['observation'].tolist() if isinstance(r['observation'], np.ndarray) else r['observation']
            
            timeseries_data.append({
                "time": r['time'],
                "observation": observation,
                "reward": r['reward'],
                "done": r['done'],
                "info": r['info']
            })
        
        with open(timeseries_file, 'w') as f:
            json.dump(timeseries_data, f, indent=2)
        artifacts.append("data/timeseries.json")
        
        # Save simulator final state
        state_file = run_dir / "data" / "final_state.json"
        final_state = {
            "neutron_flux": result['simulator'].state.neutron_flux,
            "fuel_temperature": result['simulator'].state.fuel_temperature,
            "coolant_temperature": result['simulator'].state.coolant_temperature,
            "coolant_pressure": result['simulator'].state.coolant_pressure,
            "coolant_flow_rate": result['simulator'].state.coolant_flow_rate,
            "steam_temperature": result['simulator'].state.steam_temperature,
            "steam_pressure": result['simulator'].state.steam_pressure,
            "steam_flow_rate": result['simulator'].state.steam_flow_rate,
            "control_rod_position": result['simulator'].state.control_rod_position,
            "steam_valve_position": result['simulator'].state.steam_valve_position,
            "power_level": result['simulator'].state.power_level,
            "scram_status": result['simulator'].state.scram_status,
            "reactivity": result['simulator'].state.reactivity
        }
        
        with open(state_file, 'w') as f:
            json.dump(final_state, f, indent=2)
        artifacts.append("data/final_state.json")
        
        # Save statistics
        stats_file = run_dir / "data" / "statistics.json"
        power_levels = [r['observation'][10] * 100 for r in result['results']]
        fuel_temps = [r['observation'][1] * 1000 for r in result['results']]
        
        statistics = {
            "total_timesteps": len(result['results']),
            "duration_seconds": result['results'][-1]['time'] if result['results'] else 0,
            "power_statistics": {
                "mean": float(np.mean(power_levels)),
                "std": float(np.std(power_levels)),
                "min": float(np.min(power_levels)),
                "max": float(np.max(power_levels))
            },
            "fuel_temperature_statistics": {
                "mean": float(np.mean(fuel_temps)),
                "std": float(np.std(fuel_temps)),
                "min": float(np.min(fuel_temps)),
                "max": float(np.max(fuel_temps))
            },
            "safety_events": sum(1 for r in result['results'] if r['done']),
            "control_actions": len(scenario.actions or [])
        }
        
        with open(stats_file, 'w') as f:
            json.dump(statistics, f, indent=2)
        artifacts.append("data/statistics.json")
        
        return artifacts
    
    def _generate_run_plots(self, run_id: str, result: Dict) -> List[str]:
        """Generate plots for the run"""
        run_dir = self.base_runs_dir / run_id
        plot_files = []
        
        try:
            # Extract data for plotting
            times = [r['time'] for r in result['results']]
            observations = np.array([r['observation'] for r in result['results']])
            
            # Create basic time series plot
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f"Run {run_id} - Time Series Analysis", fontsize=16, fontweight='bold')
            
            # Power level
            axes[0, 0].plot(times, observations[:, 10] * 100, 'b-', linewidth=2)
            axes[0, 0].set_title('Power Level')
            axes[0, 0].set_ylabel('Power (%)')
            axes[0, 0].grid(True)
            
            # Fuel temperature
            axes[0, 1].plot(times, observations[:, 1] * 1000, 'r-', linewidth=2)
            axes[0, 1].set_title('Fuel Temperature')
            axes[0, 1].set_ylabel('Temperature (°C)')
            axes[0, 1].grid(True)
            
            # Control rod position
            axes[1, 0].plot(times, observations[:, 8] * 100, 'g-', linewidth=2)
            axes[1, 0].set_title('Control Rod Position')
            axes[1, 0].set_ylabel('Position (% withdrawn)')
            axes[1, 0].set_xlabel('Time (s)')
            axes[1, 0].grid(True)
            
            # Coolant temperature
            axes[1, 1].plot(times, observations[:, 2] * 300, 'purple', linewidth=2)
            axes[1, 1].set_title('Coolant Temperature')
            axes[1, 1].set_ylabel('Temperature (°C)')
            axes[1, 1].set_xlabel('Time (s)')
            axes[1, 1].grid(True)
            
            plt.tight_layout()
            
            # Save plot
            plot_file = run_dir / "plots" / "timeseries.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            plot_files.append("plots/timeseries.png")
            
        except Exception as e:
            print(f"Warning: Could not generate plots for run {run_id}: {e}")
        
        return plot_files
    
    def _generate_training_data(self, run_id: str, result: Dict) -> Optional[str]:
        """Generate training data from the run"""
        try:
            run_dir = self.base_runs_dir / run_id
            metadata = self.runs_index[run_id]
            
            # Convert run result to training example format
            timeseries_data = []
            timestamps = []
            
            for r in result['results']:
                observation = r['observation'].tolist() if isinstance(r['observation'], np.ndarray) else r['observation']
                timeseries_data.append(observation)
                timestamps.append(r['time'])
            
            # Create training example
            training_example = TrainingExample(
                scenario_type=metadata.scenario_type,
                timeseries_data=timeseries_data,
                timestamps=timestamps,
                parameter_names=[
                    "neutron_flux_norm", "fuel_temp_norm", "coolant_temp_norm",
                    "coolant_pressure_norm", "coolant_flow_norm", "steam_temp_norm",
                    "steam_pressure_norm", "steam_flow_norm", "control_rod_position_norm",
                    "steam_valve_position_norm", "power_level_norm", "scram_status"
                ],
                descriptions=[f"Run {run_id} at time {t}" for t in timestamps[::60]],  # Every minute
                summary=f"Simulation run {run_id}: {metadata.description}",
                equipment_status={"all_systems": "normal" if metadata.success else "degraded"},
                severity="normal" if metadata.success else "major",
                recommended_actions=[]
            )
            
            # Save training data
            training_file = run_dir / "artifacts" / "training_data.json"
            with open(training_file, 'w') as f:
                json.dump(asdict(training_example), f, indent=2)
            
            return "artifacts/training_data.json"
            
        except Exception as e:
            print(f"Warning: Could not generate training data for run {run_id}: {e}")
            return None
    
    def list_runs(self, tags: Optional[List[str]] = None, scenario_type: Optional[str] = None) -> List[RunMetadata]:
        """List all runs, optionally filtered by tags or scenario type"""
        runs = list(self.runs_index.values())
        
        if tags:
            runs = [run for run in runs if any(tag in run.tags for tag in tags)]
        
        if scenario_type:
            runs = [run for run in runs if run.scenario_type == scenario_type]
        
        return sorted(runs, key=lambda x: x.created_at, reverse=True)
    
    def get_run(self, run_id: str) -> Optional[RunMetadata]:
        """Get metadata for a specific run"""
        return self.runs_index.get(run_id)
    
    def get_run_artifacts(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load all artifacts for a run"""
        if run_id not in self.runs_index:
            return None
        
        run_dir = self.base_runs_dir / run_id
        artifacts = {}
        
        try:
            # Load timeseries data
            timeseries_file = run_dir / "data" / "timeseries.json"
            if timeseries_file.exists():
                with open(timeseries_file, 'r') as f:
                    artifacts['timeseries'] = json.load(f)
            
            # Load final state
            state_file = run_dir / "data" / "final_state.json"
            if state_file.exists():
                with open(state_file, 'r') as f:
                    artifacts['final_state'] = json.load(f)
            
            # Load statistics
            stats_file = run_dir / "data" / "statistics.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    artifacts['statistics'] = json.load(f)
            
            # Load scenario
            scenario_file = run_dir / "config" / "scenario.json"
            if scenario_file.exists():
                with open(scenario_file, 'r') as f:
                    artifacts['scenario'] = json.load(f)
            
            # Load training data if available
            training_file = run_dir / "artifacts" / "training_data.json"
            if training_file.exists():
                with open(training_file, 'r') as f:
                    artifacts['training_data'] = json.load(f)
            
            return artifacts
            
        except Exception as e:
            print(f"Error loading artifacts for run {run_id}: {e}")
            return None
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all its artifacts"""
        if run_id not in self.runs_index:
            print(f"Run {run_id} not found")
            return False
        
        try:
            # Remove run directory
            run_dir = self.base_runs_dir / run_id
            if run_dir.exists():
                shutil.rmtree(run_dir)
            
            # Remove from index
            del self.runs_index[run_id]
            self._save_runs_index()
            
            print(f"Deleted run {run_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting run {run_id}: {e}")
            return False
    
    def export_run(self, run_id: str, export_path: str) -> bool:
        """Export a run to a specified path"""
        if run_id not in self.runs_index:
            print(f"Run {run_id} not found")
            return False
        
        try:
            run_dir = self.base_runs_dir / run_id
            export_dir = Path(export_path)
            
            # Copy entire run directory
            shutil.copytree(run_dir, export_dir / run_id)
            
            print(f"Exported run {run_id} to {export_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting run {run_id}: {e}")
            return False
    
    def generate_run_report(self, run_id: str) -> Optional[str]:
        """Generate a comprehensive report for a run"""
        if run_id not in self.runs_index:
            return None
        
        metadata = self.runs_index[run_id]
        artifacts = self.get_run_artifacts(run_id)
        
        if not artifacts:
            return None
        
        report = f"""
# Nuclear Simulator Run Report

## Run Information
- **Run ID**: {metadata.run_id}
- **Name**: {metadata.run_name}
- **Description**: {metadata.description}
- **Created**: {metadata.created_at}
- **Scenario Type**: {metadata.scenario_type}
- **Duration**: {metadata.duration_seconds:.1f} seconds
- **Success**: {metadata.success}

## Results Summary
- **Total Timesteps**: {metadata.total_timesteps}
- **Safety Events**: {metadata.safety_events}
- **Final Power Level**: {metadata.final_power_level:.1f}%
- **Average Power Level**: {metadata.average_power_level:.1f}%
- **Fuel Temperature Range**: {metadata.min_fuel_temperature:.1f}°C - {metadata.max_fuel_temperature:.1f}°C
- **Control Actions**: {metadata.control_actions_count}

## Artifacts Generated
"""
        
        for artifact in metadata.artifacts_generated:
            report += f"- {artifact}\n"
        
        if 'statistics' in artifacts:
            stats = artifacts['statistics']
            report += f"""
## Detailed Statistics
- **Power Statistics**:
  - Mean: {stats['power_statistics']['mean']:.1f}%
  - Std Dev: {stats['power_statistics']['std']:.1f}%
  - Range: {stats['power_statistics']['min']:.1f}% - {stats['power_statistics']['max']:.1f}%

- **Fuel Temperature Statistics**:
  - Mean: {stats['fuel_temperature_statistics']['mean']:.1f}°C
  - Std Dev: {stats['fuel_temperature_statistics']['std']:.1f}°C
  - Range: {stats['fuel_temperature_statistics']['min']:.1f}°C - {stats['fuel_temperature_statistics']['max']:.1f}°C
"""
        
        # Save report
        run_dir = self.base_runs_dir / run_id
        report_file = run_dir / "artifacts" / "run_report.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        return report


def demonstrate_run_manager():
    """Demonstrate the run management system"""
    print("Nuclear Simulator Run Management System Demo")
    print("=" * 60)
    
    # Create run manager
    manager = RunManager()
    
    # Create and execute several runs
    scenarios = [
        ("normal_operation", "Normal plant operation baseline", 300),
        ("power_ramp_up", "Power increase scenario", 600),
        ("steam_line_break", "Emergency scenario testing", 300),
    ]
    
    run_ids = []
    
    for scenario_type, description, duration in scenarios:
        print(f"\nCreating run: {scenario_type}")
        run_id = manager.create_run(
            run_name=f"Demo {scenario_type.replace('_', ' ').title()}",
            description=description,
            scenario_type=scenario_type,
            duration=duration,
            tags=["demo", "test", scenario_type]
        )
        
        print(f"Executing run: {run_id}")
        success = manager.execute_run(run_id)
        
        if success:
            run_ids.append(run_id)
            print(f"✓ Run {run_id} completed successfully")
        else:
            print(f"✗ Run {run_id} failed")
    
    # List all runs
    print(f"\n{'='*60}")
    print("All Runs:")
    runs = manager.list_runs()
    for run in runs:
        print(f"  {run.run_id}: {run.run_name} ({run.scenario_type}) - {'✓' if run.success else '✗'}")
    
    # Generate reports
    if run_ids:
        print(f"\nGenerating report for run: {run_ids[0]}")
        report = manager.generate_run_report(run_ids[0])
        if report:
            print("Report generated successfully")
    
    print(f"\nRun management demo completed!")
    print(f"Runs directory: {manager.base_runs_dir}")
    
    return manager, run_ids


if __name__ == "__main__":
    manager, run_ids = demonstrate_run_manager()
