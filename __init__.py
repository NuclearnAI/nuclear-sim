"""
Nuclear Simulator - A comprehensive nuclear power plant simulator

This package provides a hierarchical system architecture for simulating
nuclear power plant operations, including reactor physics, system dynamics,
data generation, and testing capabilities.

Main submodules:
- simulator: Core simulation engine
- systems: Plant systems (primary, secondary, safety, maintenance)
- data_gen: Data generation and configuration tools
- data: Data utilities and formatters
- tests: Testing framework
"""

__version__ = "0.1.0"

# Import all major submodules for easy access
from . import simulator
from . import systems
from . import data_gen
from . import data
from . import tests

# Make submodules available at package level
__all__ = [
    "simulator",
    "systems", 
    "data_gen",
    "data",
    "tests"
]
