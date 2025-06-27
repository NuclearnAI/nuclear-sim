# Data Generation Library

This library provides a comprehensive framework for generating and validating nuclear plant maintenance scenarios with intelligent initial conditions and realistic physics-based simulation.

## Architecture Overview

The data_gen library is organized into several key modules:

### Core Framework (`core/`)
- **`maintenance_tuning_framework.py`** - Main framework for maintenance scenario generation and validation
- **`validation_results.py`** - Validation result data structures and analysis

### Configuration Engine (`config_engine/`)
- **`composers/comprehensive_composer.py`** - Generates comprehensive plant configurations with targeted initial conditions
- **`templates/`** - Base configuration templates for different plant types
- **`generated_configs/`** - Generated configuration files

### Runners (`runners/`)
- **`maintenance_scenario_runner.py`** - Custom simulation runner for maintenance scenarios
- **`scenario_runner.py`** - Unified scenario interface for both maintenance and operational scenarios

### Optimization (`optimization/`)
- **`ic_optimizer.py`** - Initial conditions optimizer for target trigger timing
- **`timing_optimizer.py`** - Binary search optimization for precise timing control
- **`optimization_results.py`** - Optimization result handling and analysis

### Examples (`examples/`)
- **`quick_start.py`** - Quick start example demonstrating basic usage
- **`batch_validation_example.py`** - Batch validation across multiple actions
- **`timing_optimization_example.py`** - Timing optimization examples

## Quick Start

```python
from data_gen.core import MaintenanceTuningFramework

# Initialize the framework
framework = MaintenanceTuningFramework(verbose=True)

# Validate a maintenance action
result = framework.validate_action_scenario("oil_top_off", "demo_fast")
print(result.get_summary())

# Generate and save results
framework.save_results()
framework.generate_report()
```

## Key Features

### 1. Intelligent Initial Conditions
- Automatically generates initial conditions that position component parameters near maintenance thresholds
- Uses realistic degradation models for natural maintenance triggering
- Supports timing optimization for precise trigger control

### 2. Comprehensive Configuration Generation
- Creates complete plant configurations with all subsystems
- Embeds targeted initial conditions directly in configurations
- Supports multiple scenario profiles (demo_fast, training_realistic, validation_thorough)

### 3. Validation Framework
- Validates maintenance scenarios across different profiles
- Tracks work order creation and execution
- Provides detailed performance metrics and timing analysis

### 4. Optimization Capabilities
- Binary search optimization for target trigger timing
- Batch optimization across multiple actions
- Performance analysis and reporting

## Scenario Profiles

### demo_fast (15 minutes)
- Quick demonstrations with fast maintenance triggers
- Expected trigger time: ~6 minutes
- Execution limit: 30 seconds

### training_realistic (4 hours)
- Realistic training scenarios with industry-standard timing
- Expected trigger time: ~1 hour
- Execution limit: 2 minutes

### validation_thorough (24 hours)
- Comprehensive validation with extended simulation time
- Expected trigger time: ~4 hours
- Execution limit: 5 minutes

## Available Maintenance Actions

The framework supports maintenance actions across all major secondary system components:

### Steam Generator
- `tsp_chemical_cleaning` - TSP fouling removal
- `scale_removal` - Tube scale cleaning
- `moisture_separator_maintenance` - Steam quality improvement

### Turbine
- `bearing_maintenance` - Bearing temperature/vibration issues
- `vibration_analysis` - Rotor dynamics analysis
- `turbine_oil_top_off` - Oil level maintenance
- `efficiency_analysis` - Performance optimization

### Feedwater
- `oil_top_off` - Pump oil level maintenance
- `oil_change` - Oil contamination removal
- `bearing_inspection` - Pump bearing maintenance
- `pump_overhaul` - Efficiency restoration

### Condenser
- `condenser_tube_cleaning` - Fouling removal
- `condenser_cleaning` - General cleaning
- `vacuum_system_maintenance` - Vacuum performance

## Output Structure

```
data_gen/outputs/
├── baseline_configs/     # Baseline configurations
├── optimized_configs/    # Timing-optimized configurations
├── optimization_reports/ # Optimization analysis reports
├── configs/             # General configuration outputs
├── data/               # Simulation data exports
├── reports/            # Validation reports
└── results/            # Validation results
```

## Legacy Code

Historical and deprecated code has been moved to `legacy/` directory:
- `legacy/frameworks/` - Older framework implementations
- `legacy/initial_conditions/` - Deprecated IC generation classes
- `legacy/docs/` - Outdated documentation

## Dependencies

- Nuclear plant simulator (`simulator/`)
- Secondary system physics (`systems/secondary/`)
- Maintenance system (`systems/maintenance/`)
- State management (`simulator/state/`)

## Usage Examples

See the `examples/` directory for comprehensive usage examples covering:
- Basic validation workflows
- Batch processing multiple actions
- Timing optimization
- Custom scenario profiles
- Result analysis and reporting
