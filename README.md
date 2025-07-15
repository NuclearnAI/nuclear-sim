# Nuclear Plant Simulator

A comprehensive nuclear power plant simulation platform with advanced maintenance scenario generation, intelligent initial conditions optimization, and sophisticated secondary system modeling. Built for training data generation, operational scenario analysis, and maintenance planning.

## 🚀 Key Features

### Primary Interface: Scenario Runner
- **Unified CLI & API**: Single interface for all simulation operations via `scenario_runner.py`
- **Maintenance Scenario Generation**: Intelligent targeting of specific maintenance actions with optimized initial conditions
- **Batch Processing**: Run multiple scenarios, all available actions, or subsystem-specific operations
- **YAML Configuration Support**: Define and run scenarios from configuration files
- **Interactive Mode**: Step-by-step scenario exploration and execution

### Advanced Simulation Capabilities
- **Comprehensive Secondary Systems**: Fully implemented steam generators, turbines, feedwater systems, and condensers with realistic physics
- **Intelligent Maintenance System**: Automatic work order generation, maintenance orchestration, and component monitoring
- **Data Generation Framework**: Sophisticated training data generation with timing optimization and validation
- **State Management**: Advanced component registration and threshold monitoring
- **Configuration Engine**: Template-based plant configuration with targeted initial conditions

### Modern Architecture
- **Hierarchical System Design**: Mirrors real nuclear plant organization
- **Extensible Framework**: Easy addition of new systems, components, and scenarios
- **Modern Python Packaging**: Uses pyproject.toml and modern dependency management
- **Comprehensive Logging**: Detailed simulation data export and visualization

## 🎯 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/cjb873/nuclear-sim.git
cd nuclear-sim

# Install dependencies (using uv - recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### Basic Usage - Scenario Runner (Main Interface)

```bash
# Run a maintenance scenario (most common use case)
python nuclear_simulator/data_gen/runners/scenario_runner.py --action oil_top_off --duration 2.0

# List all available maintenance actions
python nuclear_simulator/data_gen/runners/scenario_runner.py --list-actions

# Run all actions for a specific subsystem
python nuclear_simulator/data_gen/runners/scenario_runner.py --run-all-actions --subsystem feedwater --duration 1.5

# Batch run multiple specific actions
python nuclear_simulator/data_gen/runners/scenario_runner.py --batch-maintenance --actions "oil_top_off,bearing_inspection,tsp_chemical_cleaning" --count 2

# Interactive mode for exploration
python nuclear_simulator/data_gen/runners/scenario_runner.py --interactive

# Run from YAML configuration
python nuclear_simulator/data_gen/runners/scenario_runner.py --yaml-file my_scenario.yaml
```

### Quick Test
```bash
# Verify installation with a fast maintenance scenario
python nuclear_simulator/data_gen/runners/scenario_runner.py --action oil_top_off --duration 1.0 --no-plots
```

## 🏗️ Architecture Overview

The simulator is organized into a sophisticated, hierarchical structure:

```
nuclear_simulator/
├── data_gen/                           # 🎯 MAIN INTERFACE & DATA GENERATION
│   ├── runners/
│   │   ├── scenario_runner.py          # 🚀 PRIMARY CLI & API INTERFACE
│   │   └── maintenance_scenario_runner.py  # Maintenance-specific execution
│   ├── config_engine/                  # Configuration generation system
│   │   ├── composers/                  # Intelligent config composition
│   │   ├── templates/                  # Base plant configurations
│   │   └── initial_conditions/        # Targeted initial condition generation
│   ├── core/                          # Data generation framework
│   ├── optimization/                  # Timing and parameter optimization
│   └── validation/                    # Scenario validation framework
├── simulator/                         # Core simulation engine
│   ├── core/sim.py                   # Main NuclearPlantSimulator class
│   └── state/                        # Advanced state management
├── systems/                          # Plant systems (fully implemented)
│   ├── primary/                      # Primary reactor systems
│   │   └── reactor/                  # Reactor physics and heat sources
│   ├── secondary/                    # 🔥 COMPREHENSIVE SECONDARY SYSTEMS
│   │   ├── steam_generator/          # Steam generators with fouling models
│   │   ├── turbine/                  # Turbine with rotor dynamics
│   │   ├── feedwater/                # Feedwater system with pump models
│   │   ├── condenser/                # Condenser with vacuum systems
│   │   ├── water_chemistry.py        # Water chemistry modeling
│   │   └── ph_control_system.py      # pH control systems
│   └── maintenance/                  # 🔧 ADVANCED MAINTENANCE SYSTEM
│       ├── auto_maintenance.py       # Automatic maintenance scheduling
│       ├── work_orders.py           # Work order management
│       ├── maintenance_orchestrator.py  # Intelligent maintenance decisions
│       └── component_registry.py    # Component monitoring and tracking
├── tests/                           # Comprehensive test suite
└── data/                           # Legacy data utilities
```

## 🎯 Scenario Runner - Main Interface

The `scenario_runner.py` is the primary interface for all simulation operations:

### Core Commands

```bash
# MAINTENANCE SCENARIOS (Primary Use Case)
--action ACTION              # Run specific maintenance action
--batch-maintenance          # Run multiple maintenance actions
--run-all-actions           # Run ALL available maintenance actions
--subsystem SUBSYSTEM       # Filter to specific subsystem
--exclude-actions ACTIONS   # Exclude specific actions

# CONFIGURATION & VALIDATION
--yaml-file FILE            # Run from YAML configuration
--yaml-dir DIRECTORY        # Run all YAML files in directory
--validate-yaml FILE        # Validate YAML without running

# INFORMATION & EXPLORATION
--list-actions              # List all available maintenance actions
--interactive               # Interactive exploration mode

# EXECUTION CONTROL
--duration HOURS            # Simulation duration (default: 2.0)
--count N                   # Runs per action in batch mode
--aggressive                # Use aggressive maintenance thresholds
--no-plots                  # Disable plotting for faster execution
--output-dir DIR            # Custom output directory
```

### Available Maintenance Actions

The simulator supports comprehensive maintenance actions across all major secondary systems:

#### Steam Generator (4 actions)
- `tsp_chemical_cleaning` - TSP fouling removal
- `scale_removal` - Tube scale cleaning  
- `moisture_separator_maintenance` - Steam quality improvement
- `tube_interior_fouling` - Interior fouling maintenance

#### Turbine (5 actions)
- `bearing_maintenance` - Bearing temperature/vibration issues
- `vibration_analysis` - Rotor dynamics analysis
- `turbine_oil_top_off` - Oil level maintenance
- `efficiency_analysis` - Performance optimization
- `rotor_balancing` - Dynamic balancing

#### Feedwater (4 actions)
- `oil_top_off` - Pump oil level maintenance
- `oil_change` - Oil contamination removal
- `bearing_inspection` - Pump bearing maintenance
- `pump_overhaul` - Efficiency restoration

#### Condenser (3 actions)
- `condenser_tube_cleaning` - Fouling removal
- `condenser_cleaning` - General cleaning
- `vacuum_system_maintenance` - Vacuum performance

### Example Workflows

```bash
# Development workflow - test specific action
python nuclear_simulator/data_gen/runners/scenario_runner.py --action oil_top_off --duration 1.0

# Training data generation - comprehensive batch
python nuclear_simulator/data_gen/runners/scenario_runner.py --run-all-actions --duration 2.0 --count 3

# Subsystem analysis - focus on turbine
python nuclear_simulator/data_gen/runners/scenario_runner.py --run-all-actions --subsystem turbine --duration 1.5

# Production scenario - from YAML configuration
python nuclear_simulator/data_gen/runners/scenario_runner.py --yaml-file production_scenario.yaml
```

## 🔧 Core Systems

### Secondary Systems (Fully Implemented)
The secondary systems are comprehensively modeled with realistic physics:

- **Steam Generators**: TSP fouling models, tube scaling, moisture separation
- **Turbine Systems**: Multi-stage modeling, rotor dynamics, bearing lubrication
- **Feedwater Systems**: Pump performance, lubrication systems, level control
- **Condenser Systems**: Vacuum control, tube fouling, heat transfer
- **Water Chemistry**: pH control, chemical species tracking, corrosion modeling

### Maintenance System
Advanced maintenance framework with:

- **Automatic Monitoring**: Component threshold monitoring and violation detection
- **Work Order Management**: Automatic work order creation, scheduling, and execution
- **Maintenance Orchestration**: Intelligent decision-making for maintenance actions
- **Component Registry**: Comprehensive component tracking and maintenance history

### Data Generation Framework
Sophisticated system for generating training data:

- **Intelligent Initial Conditions**: Automatically positions components near maintenance thresholds
- **Timing Optimization**: Binary search optimization for precise maintenance trigger timing
- **Scenario Validation**: Comprehensive validation across multiple scenario profiles
- **Configuration Engine**: Template-based generation of complete plant configurations

## 📊 Output and Data Management

### Automatic Data Export
Every simulation run generates:
- **Complete CSV Data**: All plant parameters logged at every timestep
- **Configuration Files**: YAML configurations for reproducibility
- **Plots and Visualizations**: Standard plots for key parameters
- **Maintenance Reports**: Work order summaries and maintenance effectiveness

### Run Organization
```
simulation_runs/
├── oil_top_off_20250711_104500/
│   ├── data/
│   │   └── timeseries.csv              # Complete parameter data
│   ├── plots/
│   │   ├── overview.png
│   │   ├── maintenance_timeline.png
│   │   └── component_parameters.png
│   ├── config/
│   │   └── oil_top_off_20250711_104500_config.yaml
│   └── results/
│       └── maintenance_summary.json
```

## 🛠️ Configuration Management

### YAML-Based Configuration
The simulator uses comprehensive YAML configurations:

```yaml
metadata:
  scenario_name: "Feedwater Oil Top-off Scenario"
  target_action: "oil_top_off"
  target_subsystem: "feedwater"
  duration_hours: 2.0

plant_config:
  # Complete plant configuration with targeted initial conditions
  secondary_systems:
    feedwater:
      pumps:
        oil_level: 0.25  # Positioned near maintenance threshold
        # ... detailed configuration
```

### Configuration Templates
- **Comprehensive Templates**: Complete plant configurations for different scenarios
- **Targeted Initial Conditions**: Automatically generated conditions that trigger specific maintenance
- **Scenario Profiles**: Different timing profiles (demo_fast, training_realistic, validation_thorough)

## 🚀 Development and Extension

### Adding New Maintenance Actions
1. Create initial conditions in `config_engine/initial_conditions/`
2. Add action mapping in `comprehensive_composer.py`
3. Test with scenario runner: `--action your_new_action`

### Adding New Systems
1. Create system directory under `systems/`
2. Implement physics models and maintenance interfaces
3. Register with state manager and maintenance system
4. Add configuration templates

### Python API Usage
```python
from nuclear_simulator.data_gen.runners.scenario_runner import ScenarioRunner

# Initialize runner
runner = ScenarioRunner(output_dir="my_runs", verbose=True)

# Run maintenance scenario
result = runner.run_maintenance_scenario(
    action="oil_top_off",
    duration_hours=2.0,
    aggressive_mode=True
)

# Batch processing
results = runner.run_batch_maintenance(
    actions=["oil_top_off", "bearing_inspection"],
    duration_hours=1.5,
    count_per_action=3
)
```

## 📋 Use Cases

### Training Data Generation
```bash
# Generate comprehensive training dataset
python nuclear_simulator/data_gen/runners/scenario_runner.py --run-all-actions --duration 4.0 --count 5
```

### Maintenance Planning
```bash
# Analyze specific subsystem maintenance needs
python nuclear_simulator/data_gen/runners/scenario_runner.py --run-all-actions --subsystem turbine --duration 2.0
```

### Scenario Development
```bash
# Interactive development and testing
python nuclear_simulator/data_gen/runners/scenario_runner.py --interactive
```

### Production Simulation
```bash
# Run from validated YAML configuration
python nuclear_simulator/data_gen/runners/scenario_runner.py --yaml-file production_scenario.yaml
```

## 🧪 Testing

```bash
# Run test suite
python tests/test_suite.py

# Test specific functionality
python -m pytest tests/test_maintenance_scenarios.py
```

## 📦 Dependencies

- **Core**: numpy, matplotlib, pandas, seaborn
- **Web Interface**: fastapi, uvicorn, websockets
- **Configuration**: dataclass-wizard, pyyaml
- **Development**: jupyter, rich (for enhanced CLI output)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Test with scenario runner: `--action test_action`
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

- **Quick Help**: `python nuclear_simulator/data_gen/runners/scenario_runner.py --help`
- **List Actions**: `python nuclear_simulator/data_gen/runners/scenario_runner.py --list-actions`
- **Interactive Mode**: `python nuclear_simulator/data_gen/runners/scenario_runner.py --interactive`
- **GitHub Issues**: Open an issue for bugs or feature requests

## 🔮 Future Enhancements

- **Advanced Control Systems**: Model predictive control and advanced process control
- **Machine Learning Integration**: Reinforcement learning agents for plant operation
- **Real-time Visualization**: 3D plant visualization and real-time dashboards
- **Distributed Simulation**: Multi-node simulation for large-scale scenarios
- **Additional Reactor Types**: Molten salt reactors, small modular reactors
- **Cloud Integration**: Cloud-based simulation and data storage

---

**Nuclear Plant Simulator** - A comprehensive nuclear power plant simulation platform for training, analysis, and research.

*Primary Interface: `nuclear_simulator/data_gen/runners/scenario_runner.py`*
