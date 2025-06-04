"""
Nuclear Plant Plotting System

This module provides flexible plotting capabilities for nuclear plant data,
allowing visualization of any parameters from CSV data files.
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Add parent directory to path so we can import from core
sys.path.append(str(Path(__file__).parent.parent))

from data.plant_data_logger import CSVDataReader


class PlantPlotter:
    """
    Flexible plotting system for nuclear plant data.
    Can plot any combination of parameters from CSV data files.
    """
    
    def __init__(self, figsize: Tuple[int, int] = (15, 10)):
        """
        Initialize the plant plotter
        
        Args:
            figsize: Default figure size for plots
        """
        self.figsize = figsize
        
        # Set up plotting style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Parameter groupings for standard plant plots
        self.parameter_groups = {
            'power': ['power_level', 'thermal_power', 'neutron_flux'],
            'temperatures': ['fuel_temperature', 'coolant_temperature', 'steam_temperature'],
            'pressures': ['coolant_pressure', 'steam_pressure'],
            'flows': ['coolant_flow_rate', 'steam_flow_rate', 'feedwater_flow_rate'],
            'control': ['control_rod_position', 'steam_valve_position'],
            'safety': ['scram_status', 'reactivity'],
            'neutronics': ['neutron_flux', 'reactivity'] + [f'delayed_neutron_precursors_group_{i}' for i in range(1, 7)]
        }
        
        # Parameter display names and units
        self.parameter_info = {
            'neutron_flux': ('Neutron Flux', 'neutrons/cm²/s'),
            'reactivity': ('Reactivity', 'Δk/k'),
            'fuel_temperature': ('Fuel Temperature', '°C'),
            'coolant_temperature': ('Coolant Temperature', '°C'),
            'coolant_pressure': ('Coolant Pressure', 'MPa'),
            'coolant_flow_rate': ('Coolant Flow Rate', 'kg/s'),
            'steam_temperature': ('Steam Temperature', '°C'),
            'steam_pressure': ('Steam Pressure', 'MPa'),
            'steam_flow_rate': ('Steam Flow Rate', 'kg/s'),
            'feedwater_flow_rate': ('Feedwater Flow Rate', 'kg/s'),
            'control_rod_position': ('Control Rod Position', '% withdrawn'),
            'steam_valve_position': ('Steam Valve Position', '% open'),
            'power_level': ('Power Level', '% rated'),
            'thermal_power': ('Thermal Power', 'MW'),
            'scram_status': ('SCRAM Status', 'boolean'),
            'simulation_time': ('Simulation Time', 's'),
        }
        
        # Add delayed neutron precursor groups
        for i in range(1, 7):
            param_name = f'delayed_neutron_precursors_group_{i}'
            self.parameter_info[param_name] = (f'Delayed Neutron Group {i}', 'relative')
    
    def plot_parameters(self, 
                       csv_path: str, 
                       parameters: List[str],
                       title: Optional[str] = None,
                       time_range: Optional[Tuple[float, float]] = None,
                       save_path: Optional[str] = None,
                       show_plot: bool = True) -> matplotlib.figure.Figure:
        """
        Plot specified parameters from CSV data
        
        Args:
            csv_path: Path to the CSV data file
            parameters: List of parameter names to plot
            title: Plot title (auto-generated if None)
            time_range: Tuple of (start_time, end_time) in seconds
            save_path: Path to save the plot (optional)
            show_plot: Whether to display the plot
            
        Returns:
            matplotlib Figure object
        """
        # Read data
        reader = CSVDataReader(csv_path)
        data = reader.read_multiple_parameters(parameters)
        
        # Convert timestamps to simulation time for x-axis
        sim_times = {}
        for param in parameters:
            if data[param][0]:  # If we have data for this parameter
                # Read simulation_time parameter to get proper x-axis
                sim_time_data = reader.read_parameter('simulation_time')
                if sim_time_data[1]:
                    # Use simulation time as x-axis
                    sim_times[param] = sim_time_data[1][:len(data[param][1])]
                else:
                    # Fallback to index-based time
                    sim_times[param] = list(range(len(data[param][1])))
        
        # Create subplots
        n_params = len(parameters)
        if n_params == 1:
            fig, ax = plt.subplots(1, 1, figsize=self.figsize)
            axes = [ax]
        else:
            # Calculate subplot layout
            cols = min(2, n_params)
            rows = (n_params + cols - 1) // cols
            fig, axes = plt.subplots(rows, cols, figsize=self.figsize)
            if rows == 1:
                axes = [axes] if cols == 1 else list(axes)
            else:
                axes = axes.flatten()
        
        # Plot each parameter
        for i, param in enumerate(parameters):
            ax = axes[i]
            
            if not data[param][1]:  # No data for this parameter
                ax.text(0.5, 0.5, f'No data for {param}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'{param} (No Data)')
                continue
            
            times = sim_times.get(param, list(range(len(data[param][1]))))
            values = data[param][1]
            
            # Apply time range filter if specified
            if time_range:
                start_time, end_time = time_range
                filtered_data = [(t, v) for t, v in zip(times, values) 
                               if start_time <= t <= end_time]
                if filtered_data:
                    times, values = zip(*filtered_data)
                else:
                    times, values = [], []
            
            if not times:
                ax.text(0.5, 0.5, f'No data in time range', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'{param} (No Data in Range)')
                continue
            
            # Special handling for boolean parameters
            if param == 'scram_status':
                ax.step(times, values, where='post', linewidth=2, color='red')
                ax.fill_between(times, values, alpha=0.3, color='red', step='post')
                ax.set_ylim(-0.1, 1.1)
                ax.set_yticks([0, 1])
                ax.set_yticklabels(['Normal', 'SCRAM'])
            else:
                ax.plot(times, values, linewidth=2)
            
            # Set labels and title
            param_display, unit = self.parameter_info.get(param, (param, 'unknown'))
            ax.set_title(f'{param_display}')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(f'{param_display} ({unit})')
            ax.grid(True, alpha=0.3)
            
            # Add reference lines for certain parameters
            if param == 'power_level':
                ax.axhline(y=100, color='green', linestyle='--', alpha=0.7, label='100% Power')
                ax.axhline(y=110, color='orange', linestyle='--', alpha=0.5, label='110% Power')
                ax.legend()
            elif param == 'control_rod_position':
                ax.axhline(y=50, color='green', linestyle='--', alpha=0.7, label='50% Withdrawn')
                ax.legend()
        
        # Hide unused subplots
        for i in range(n_params, len(axes)):
            axes[i].set_visible(False)
        
        # Set overall title
        if title is None:
            title = f"Nuclear Plant Parameters: {', '.join(parameters)}"
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot if requested
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        # Show plot if requested
        if show_plot:
            plt.show()
        
        return fig
    
    def plot_parameter_group(self,
                           csv_path: str,
                           group_name: str,
                           title: Optional[str] = None,
                           time_range: Optional[Tuple[float, float]] = None,
                           save_path: Optional[str] = None,
                                show_plot: bool = True) -> matplotlib.figure.Figure:
        """
        Plot a predefined group of related parameters
        
        Args:
            csv_path: Path to the CSV data file
            group_name: Name of parameter group ('power', 'temperatures', etc.)
            title: Plot title (auto-generated if None)
            time_range: Tuple of (start_time, end_time) in seconds
            save_path: Path to save the plot (optional)
            show_plot: Whether to display the plot
            
        Returns:
            matplotlib Figure object
        """
        if group_name not in self.parameter_groups:
            raise ValueError(f"Unknown parameter group: {group_name}. "
                           f"Available groups: {list(self.parameter_groups.keys())}")
        
        parameters = self.parameter_groups[group_name]
        
        if title is None:
            title = f"Nuclear Plant {group_name.title()} Parameters"
        
        return self.plot_parameters(csv_path, parameters, title, time_range, save_path, show_plot)
    
    def plot_overview(self,
                     csv_path: str,
                     title: Optional[str] = None,
                     time_range: Optional[Tuple[float, float]] = None,
                     save_path: Optional[str] = None,
                     show_plot: bool = True) -> matplotlib.figure.Figure:
        """
        Create a comprehensive overview plot with key plant parameters
        
        Args:
            csv_path: Path to the CSV data file
            title: Plot title (auto-generated if None)
            time_range: Tuple of (start_time, end_time) in seconds
            save_path: Path to save the plot (optional)
            show_plot: Whether to display the plot
            
        Returns:
            matplotlib Figure object
        """
        # Key parameters for overview
        key_parameters = [
            'power_level',
            'fuel_temperature',
            'coolant_temperature',
            'coolant_pressure',
            'control_rod_position',
            'scram_status'
        ]
        
        if title is None:
            title = "Nuclear Plant Overview"
        
        return self.plot_parameters(csv_path, key_parameters, title, time_range, save_path, show_plot)
    
    def compare_runs(self,
                    csv_paths: List[str],
                    run_names: List[str],
                    parameters: List[str],
                    title: Optional[str] = None,
                    time_range: Optional[Tuple[float, float]] = None,
                    save_path: Optional[str] = None,
                    show_plot: bool = True) -> matplotlib.figure.Figure:
        """
        Compare the same parameters across multiple runs
        
        Args:
            csv_paths: List of paths to CSV data files
            run_names: List of names for each run
            parameters: List of parameter names to compare
            title: Plot title (auto-generated if None)
            time_range: Tuple of (start_time, end_time) in seconds
            save_path: Path to save the plot (optional)
            show_plot: Whether to display the plot
            
        Returns:
            matplotlib Figure object
        """
        if len(csv_paths) != len(run_names):
            raise ValueError("Number of CSV paths must match number of run names")
        
        # Create subplots
        n_params = len(parameters)
        if n_params == 1:
            fig, ax = plt.subplots(1, 1, figsize=self.figsize)
            axes = [ax]
        else:
            cols = min(2, n_params)
            rows = (n_params + cols - 1) // cols
            fig, axes = plt.subplots(rows, cols, figsize=self.figsize)
            if rows == 1:
                axes = [axes] if cols == 1 else list(axes)
            else:
                axes = axes.flatten()
        
        # Color cycle for different runs
        colors = plt.cm.get_cmap('tab10')(np.linspace(0, 1, len(csv_paths)))
        
        # Plot each parameter
        for i, param in enumerate(parameters):
            ax = axes[i]
            
            for j, (csv_path, run_name) in enumerate(zip(csv_paths, run_names)):
                try:
                    reader = CSVDataReader(csv_path)
                    
                    # Get simulation time and parameter data
                    sim_time_data = reader.read_parameter('simulation_time')
                    param_data = reader.read_parameter(param)
                    
                    if sim_time_data[1] and param_data[1]:
                        times = sim_time_data[1][:len(param_data[1])]
                        values = param_data[1]
                        
                        # Apply time range filter if specified
                        if time_range:
                            start_time, end_time = time_range
                            filtered_data = [(t, v) for t, v in zip(times, values) 
                                           if start_time <= t <= end_time]
                            if filtered_data:
                                times, values = zip(*filtered_data)
                            else:
                                continue
                        
                        # Plot the data
                        if param == 'scram_status':
                            ax.step(times, values, where='post', linewidth=2, 
                                   color=colors[j], label=run_name)
                        else:
                            ax.plot(times, values, linewidth=2, 
                                   color=colors[j], label=run_name)
                
                except Exception as e:
                    print(f"Warning: Could not read {param} from {csv_path}: {e}")
                    continue
            
            # Set labels and title
            param_display, unit = self.parameter_info.get(param, (param, 'unknown'))
            ax.set_title(f'{param_display}')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(f'{param_display} ({unit})')
            ax.grid(True, alpha=0.3)
            ax.legend()
        
        # Hide unused subplots
        for i in range(n_params, len(axes)):
            axes[i].set_visible(False)
        
        # Set overall title
        if title is None:
            title = f"Run Comparison: {', '.join(parameters)}"
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot if requested
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparison plot saved to: {save_path}")
        
        # Show plot if requested
        if show_plot:
            plt.show()
        
        return fig
    
    def get_available_parameters(self, csv_path: str) -> List[str]:
        """Get list of all parameters available in a CSV file"""
        reader = CSVDataReader(csv_path)
        return reader.get_available_parameters()
    
    def get_parameter_groups(self) -> Dict[str, List[str]]:
        """Get dictionary of available parameter groups"""
        return self.parameter_groups.copy()


def demonstrate_plant_plotter():
    """Demonstrate the plant plotting capabilities"""
    print("Nuclear Plant Plotting System Demonstration")
    print("=" * 50)
    
    # Use the test data we created earlier
    csv_path = "runs/test_data_logger_demo/data/timeseries.csv"
    
    if not os.path.exists(csv_path):
        print(f"Test data not found at {csv_path}")
        print("Please run the plant data logger demo first.")
        return
    
    # Create plotter
    plotter = PlantPlotter()
    
    print(f"Reading data from: {csv_path}")
    
    # Get available parameters
    available_params = plotter.get_available_parameters(csv_path)
    print(f"Available parameters: {len(available_params)}")
    print(f"Parameters: {', '.join(available_params[:10])}...")  # Show first 10
    print()
    
    # 1. Plot overview
    print("1. Creating overview plot...")
    plotter.plot_overview(csv_path, 
                         title="Nuclear Plant Overview - Test Data",
                         save_path="runs/test_data_logger_demo/plots/overview.png")
    
    # 2. Plot power parameters
    print("2. Creating power parameters plot...")
    plotter.plot_parameter_group(csv_path, 'power',
                                title="Power Parameters - Test Data",
                                save_path="runs/test_data_logger_demo/plots/power_params.png")
    
    # 3. Plot temperatures
    print("3. Creating temperature parameters plot...")
    plotter.plot_parameter_group(csv_path, 'temperatures',
                                title="Temperature Parameters - Test Data",
                                save_path="runs/test_data_logger_demo/plots/temperature_params.png")
    
    # 4. Plot custom parameter selection
    print("4. Creating custom parameter plot...")
    custom_params = ['power_level', 'fuel_temperature', 'control_rod_position']
    plotter.plot_parameters(csv_path, custom_params,
                           title="Custom Parameter Selection - Test Data",
                           save_path="runs/test_data_logger_demo/plots/custom_params.png")
    
    print("\nPlotting demonstration completed!")
    print("Generated plots:")
    print("  - overview.png: Key plant parameters")
    print("  - power_params.png: Power-related parameters")
    print("  - temperature_params.png: Temperature parameters")
    print("  - custom_params.png: Custom parameter selection")
    
    return plotter


if __name__ == "__main__":
    plotter = demonstrate_plant_plotter()
