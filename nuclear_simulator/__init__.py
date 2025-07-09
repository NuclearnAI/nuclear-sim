"""
Nuclear Simulator - A comprehensive nuclear power plant simulator

This package provides a hierarchical system architecture for simulating
nuclear power plant operations, including reactor physics, system dynamics,
data generation, and testing capabilities.

Usage:
    import nuclear_simulator
    
    # Create a simulator
    heat_source = nuclear_simulator.ConstantHeatSource(rated_power_mw=3000.0)
    simulator = nuclear_simulator.NuclearPlantSimulator(heat_source=heat_source)
    
    # Run scenarios
    runner = nuclear_simulator.ScenarioRunner()
"""

__version__ = "0.1.0"

# Simple direct imports - no path manipulation needed
# setuptools will handle making all modules available
from simulator.core.sim import NuclearPlantSimulator
from systems.primary.reactor.heat_sources.constant_heat_source import ConstantHeatSource
from systems.primary.reactor.heat_sources.reactor_heat_source import ReactorHeatSource
from data_gen.runners.scenario_runner import ScenarioRunner
from data_gen.runners.maintenance_scenario_runner import MaintenanceScenarioRunner
from data_gen.config_engine.composers.comprehensive_composer import ComprehensiveComposer

# Make submodules available for advanced users
import simulator
import systems
import data_gen
import data
import tests

# Make everything available at top level
__all__ = [
    # Core simulator classes
    "NuclearPlantSimulator",
    "ConstantHeatSource", 
    "ReactorHeatSource",
    
    # Data generation and scenario tools
    "ScenarioRunner",
    "MaintenanceScenarioRunner",
    "ComprehensiveComposer",
    
    # Submodules (for advanced users)
    "simulator",
    "systems", 
    "data_gen",
    "data",
    "tests"
]
