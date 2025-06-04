"""
Nuclear Plant Data Logger

This module provides comprehensive data logging capabilities for nuclear plant simulations,
capturing all parameters in real-time like a real plant DCS (Distributed Control System).
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add parent directory to path so we can import from core
sys.path.append(str(Path(__file__).parent.parent))

from simulator.core.sim import NuclearPlantSimulator, ReactorState


class PlantDataLogger:
    """
    Real-time data logger for nuclear plant simulations.
    Captures all parameters at every timestep like a real plant DCS.
    """
    
    def __init__(self, run_directory: str):
        """
        Initialize the plant data logger
        
        Args:
            run_directory: Directory where this run's data will be stored
        """
        self.run_directory = Path(run_directory)
        self.csv_path = self.run_directory / "data" / "timeseries.csv"
        
        # Ensure data directory exists
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize CSV file with headers
        self._initialize_csv()
        
        # Parameter definitions with units
        self.parameter_definitions = {
            # Neutronics
            'neutron_flux': ('neutrons/cm²/s', 'Neutron flux density'),
            'reactivity': ('Δk/k', 'Reactivity'),
            'delayed_neutron_precursors_group_1': ('relative', 'Delayed neutron precursor group 1'),
            'delayed_neutron_precursors_group_2': ('relative', 'Delayed neutron precursor group 2'),
            'delayed_neutron_precursors_group_3': ('relative', 'Delayed neutron precursor group 3'),
            'delayed_neutron_precursors_group_4': ('relative', 'Delayed neutron precursor group 4'),
            'delayed_neutron_precursors_group_5': ('relative', 'Delayed neutron precursor group 5'),
            'delayed_neutron_precursors_group_6': ('relative', 'Delayed neutron precursor group 6'),
            
            # Thermal Hydraulics
            'fuel_temperature': ('°C', 'Average fuel temperature'),
            'coolant_temperature': ('°C', 'Reactor coolant temperature'),
            'coolant_pressure': ('MPa', 'Reactor coolant system pressure'),
            'coolant_flow_rate': ('kg/s', 'Reactor coolant flow rate'),
            
            # Steam Cycle
            'steam_temperature': ('°C', 'Steam generator outlet temperature'),
            'steam_pressure': ('MPa', 'Steam generator pressure'),
            'steam_flow_rate': ('kg/s', 'Main steam flow rate'),
            'feedwater_flow_rate': ('kg/s', 'Feedwater flow rate'),
            
            # Control Systems
            'control_rod_position': ('%', 'Control rod position (% withdrawn)'),
            'steam_valve_position': ('%', 'Steam valve position (% open)'),
            
            # Power and Safety
            'power_level': ('%', 'Reactor power level (% rated)'),
            'thermal_power': ('MW', 'Reactor thermal power'),
            'scram_status': ('boolean', 'Reactor SCRAM status'),
            
            # Simulation Meta
            'simulation_time': ('s', 'Simulation time'),
        }
    
    def _initialize_csv(self):
        """Initialize the CSV file with headers"""
        with open(self.csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'parameter_name', 'value', 'unit', 'quality'])
    
    def extract_all_parameters(self, simulator: NuclearPlantSimulator) -> List[Tuple[str, Any, str]]:
        """
        Extract all parameters from the simulator state
        
        Args:
            simulator: The nuclear plant simulator instance
            
        Returns:
            List of tuples (parameter_name, value, unit)
        """
        state = simulator.state
        parameters = []
        
        # Neutronics parameters
        parameters.append(('neutron_flux', float(state.neutron_flux), 'neutrons/cm²/s'))
        parameters.append(('reactivity', float(state.reactivity), 'Δk/k'))
        
        # Delayed neutron precursors (6 groups)
        if state.delayed_neutron_precursors is not None:
            for i, precursor in enumerate(state.delayed_neutron_precursors):
                parameters.append((f'delayed_neutron_precursors_group_{i+1}', float(precursor), 'relative'))
        
        # Thermal hydraulics
        parameters.append(('fuel_temperature', float(state.fuel_temperature), '°C'))
        parameters.append(('coolant_temperature', float(state.coolant_temperature), '°C'))
        parameters.append(('coolant_pressure', float(state.coolant_pressure), 'MPa'))
        parameters.append(('coolant_flow_rate', float(state.coolant_flow_rate), 'kg/s'))
        
        # Steam cycle
        parameters.append(('steam_temperature', float(state.steam_temperature), '°C'))
        parameters.append(('steam_pressure', float(state.steam_pressure), 'MPa'))
        parameters.append(('steam_flow_rate', float(state.steam_flow_rate), 'kg/s'))
        parameters.append(('feedwater_flow_rate', float(state.feedwater_flow_rate), 'kg/s'))
        
        # Control systems
        parameters.append(('control_rod_position', float(state.control_rod_position), '%'))
        parameters.append(('steam_valve_position', float(state.steam_valve_position), '%'))
        
        # Power and safety
        parameters.append(('power_level', float(state.power_level), '%'))
        parameters.append(('scram_status', int(state.scram_status), 'boolean'))
        
        # Calculate thermal power from neutron flux
        thermal_power = state.neutron_flux / 1e12 * 3000  # MW
        parameters.append(('thermal_power', float(thermal_power), 'MW'))
        
        # Simulation time
        parameters.append(('simulation_time', float(simulator.time), 's'))
        
        return parameters
    
    def log_timestep(self, simulator: NuclearPlantSimulator, quality: str = 'GOOD'):
        """
        Log all parameters for the current timestep
        
        Args:
            simulator: The nuclear plant simulator instance
            quality: Data quality flag ('GOOD', 'BAD', 'UNCERTAIN')
        """
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        # Extract all parameters
        parameters = self.extract_all_parameters(simulator)
        
        # Write to CSV
        with open(self.csv_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for param_name, value, unit in parameters:
                writer.writerow([timestamp, param_name, value, unit, quality])
    
    def get_parameter_list(self) -> List[str]:
        """Get list of all logged parameters"""
        return list(self.parameter_definitions.keys())
    
    def get_parameter_info(self, parameter_name: str) -> Optional[Tuple[str, str]]:
        """
        Get unit and description for a parameter
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            Tuple of (unit, description) or None if parameter not found
        """
        return self.parameter_definitions.get(parameter_name)
    
    def get_csv_path(self) -> str:
        """Get the path to the CSV file"""
        return str(self.csv_path)
    
    def get_logged_parameter_count(self) -> int:
        """Get the number of parameters being logged"""
        return len(self.parameter_definitions)


class CSVDataReader:
    """
    Reader for plant data CSV files
    """
    
    def __init__(self, csv_path: str):
        """
        Initialize the CSV reader
        
        Args:
            csv_path: Path to the CSV file
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    def read_parameter(self, parameter_name: str) -> Tuple[List[str], List[float]]:
        """
        Read time series data for a specific parameter
        
        Args:
            parameter_name: Name of the parameter to read
            
        Returns:
            Tuple of (timestamps, values)
        """
        timestamps = []
        values = []
        
        with open(self.csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['parameter_name'] == parameter_name:
                    timestamps.append(row['timestamp'])
                    values.append(float(row['value']))
        
        return timestamps, values
    
    def read_multiple_parameters(self, parameter_names: List[str]) -> Dict[str, Tuple[List[str], List[float]]]:
        """
        Read time series data for multiple parameters
        
        Args:
            parameter_names: List of parameter names to read
            
        Returns:
            Dictionary mapping parameter names to (timestamps, values) tuples
        """
        data = {param: ([], []) for param in parameter_names}
        
        with open(self.csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                param_name = row['parameter_name']
                if param_name in parameter_names:
                    data[param_name][0].append(row['timestamp'])
                    data[param_name][1].append(float(row['value']))
        
        return data
    
    def get_available_parameters(self) -> List[str]:
        """Get list of all parameters available in the CSV"""
        parameters = set()
        
        with open(self.csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                parameters.add(row['parameter_name'])
        
        return sorted(list(parameters))
    
    def get_time_range(self) -> Tuple[str, str]:
        """Get the time range of the data"""
        timestamps = []
        
        with open(self.csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                timestamps.append(row['timestamp'])
        
        if timestamps:
            return timestamps[0], timestamps[-1]
        else:
            return "", ""


def demonstrate_plant_data_logger():
    """Demonstrate the plant data logger functionality"""
    print("Nuclear Plant Data Logger Demonstration")
    print("=" * 50)
    
    # Create a test run directory
    test_run_dir = "runs/test_data_logger_demo"
    
    # Create logger
    logger = PlantDataLogger(test_run_dir)
    
    print(f"Created data logger for run: {test_run_dir}")
    print(f"CSV file: {logger.get_csv_path()}")
    print(f"Logging {logger.get_logged_parameter_count()} parameters")
    print()
    
    # Create simulator
    from simulator.core.sim import NuclearPlantSimulator
    sim = NuclearPlantSimulator(dt=1.0)
    
    print("Running short simulation with data logging...")
    
    # Run simulation with logging
    for step in range(10):
        result = sim.step()
        logger.log_timestep(sim)
        
        if step % 5 == 0:
            print(f"Step {step}: Power={sim.state.power_level:.1f}%, "
                  f"Fuel Temp={sim.state.fuel_temperature:.1f}°C")
    
    print(f"\nData logged to: {logger.get_csv_path()}")
    
    # Demonstrate reading the data
    print("\nReading logged data...")
    reader = CSVDataReader(logger.get_csv_path())
    
    available_params = reader.get_available_parameters()
    print(f"Available parameters: {len(available_params)}")
    
    # Read power level data
    timestamps, power_values = reader.read_parameter('power_level')
    print(f"Power level data points: {len(power_values)}")
    print(f"Power range: {min(power_values):.1f}% - {max(power_values):.1f}%")
    
    return logger, reader


if __name__ == "__main__":
    logger, reader = demonstrate_plant_data_logger()
