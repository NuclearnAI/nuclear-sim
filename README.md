# Nuclear Plant Simulator

A comprehensive nuclear power plant simulator with hierarchical system architecture, supporting multiple heat source types and advanced simulation capabilities.

## Key Features

- **Unified CLI**: Single command-line interface for all operations.
- **Multiple Heat Sources**: Supports realistic reactor physics and simplified constant heat sources.
- **Hierarchical System Model**: Mirrors real nuclear plant systems.
- **Comprehensive Data Logging**: All 22+ plant parameters logged to CSV in real-time.
- **Automatic Plotting**: Generates standard plots for key parameters after each run.
- **Run Management**: Organizes simulation runs with metadata and artifacts.
- **Interactive Mode**: Step-by-step simulation with real-time dashboard.
- **Extensible Architecture**: Designed for adding new systems, heat sources, and scenarios.
- **Educational Focus**: Suitable for learning reactor physics, operations, and safety.

## 🚀 Quick Start & Installation

### Option 1: Run Locally (No Installation)
From the `nuclear-simulator` directory:
```bash
./nuclear-sim --help
./nuclear-sim run normal_operation --name "Test" --duration 300
```

### Option 2: Install Globally (Recommended)
1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd nuclear-simulator
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    # or if using uv
    uv sync
    ```
3.  Run the installation script (from the `nuclear-simulator` directory):
    ```bash
    ./install.sh
    ```
    This may require `sudo` privileges if `/usr/local/bin` is not writable by your user.
4.  Then use `nuclear-sim` from any directory:
    ```bash
    nuclear-sim --help
    nuclear-sim run normal_operation --name "Test" --duration 300
    ```

### Quick Test
To verify the simulator is working:
```bash
# If installed globally
nuclear-sim run normal_operation --name "Quick Test" --duration 120
# Or if running locally
./nuclear-sim run normal_operation --name "Quick Test" --duration 120
```
View results:
```bash
nuclear-sim list
nuclear-sim status
```

### Troubleshooting Setup
- **"Command not found"**: Use `./nuclear-sim` if not installed globally, or run `./install.sh`.
- **Permission denied for `./nuclear-sim`**: Run `chmod +x nuclear-sim`.
- **Permission denied for `install.sh`**: Run `chmod +x install.sh`, then `sudo ./install.sh`.
- **Python errors**: Ensure Python 3.8+ is installed. Install dependencies (`pip install numpy matplotlib seaborn rich` or from `requirements.txt`).

## 🏗️ Project Structure

The simulator is organized into a hierarchical structure:

```
nuclear-simulator/
├── simulator/                    # Core simulation engine
│   ├── core/                    # Main simulator logic
│   │   └── sim.py              # NuclearPlantSimulator class
│   ├── state/                   # Reactor state management (placeholder)
│   └── control/                 # Control actions and interfaces (placeholder)
├── systems/                     # Plant systems (hierarchical)
│   ├── primary/                 # Primary system
│   │   ├── reactor/            # Reactor core systems
│   │   │   ├── reactivity_model.py # Comprehensive reactivity model
│   │   │   ├── reactor_physics.py  # Unified reactor physics
│   │   │   └── heat_sources/   # Different heat source options
│   │   ├── coolant/            # Primary coolant system (placeholder)
│   │   └── steam_generator/    # Steam generators (placeholder)
│   ├── secondary/              # Secondary system (placeholders for steam, turbine, condenser)
│   └── safety/                 # Safety systems (placeholder)
├── scenarios/                   # Simulation scenarios
│   └── scenario_generator.py   # Scenario generation logic
├── data/                       # Data management utilities
│   ├── plant_data_logger.py   # Data logging to CSV
│   └── gen_training_data.py   # Training data generation
├── visualization/              # Plotting and visualization
│   └── plant_plotter.py       # Plotting utilities using logged data
├── management/                 # Run management
│   └── run_manager.py         # Simulation run management
├── examples/                   # Example scripts and notebooks (see examples/README.md)
├── tests/                      # Test files (see tests/README.md)
├── game/                       # Interactive operator training game (see game/README.md)
├── runs/                       # Simulation output data
├── nuclear_sim.py              # Main CLI Python script
└── nuclear-sim                 # Executable CLI wrapper script
```
*(Placeholders indicate planned modules/directories that are currently empty or minimally populated.)*

## Core Concepts & Architecture

### Main Components Overview
- **`simulator/`**: Contains the core simulation engine (`sim.py`) and placeholders for state and control logic.
- **`systems/`**: Models the physical plant systems.
    - **`systems/primary/reactor/`**: Holds the detailed reactor physics and heat source models.
    - Other subdirectories are placeholders for future system components.
- **`scenarios/`**: Defines and generates various operational and emergency scenarios.
- **`data/`**: Utilities for logging simulation data and generating training datasets.
- **`visualization/`**: Tools for plotting data from simulation runs.
- **`management/`**: Handles the creation, execution, and tracking of simulation runs.
- **`game/`**: A FastAPI-based interactive game built on top of the simulator. See `game/README.md`.
- **`examples/`**: Demonstrates various ways to use the simulator. See `examples/README.md`.
- **`tests/`**: Contains the test suite for the project. See `tests/README.md`.

### Heat Source Architecture
The simulator supports multiple heat source types via a pluggable interface (`systems.primary.reactor.heat_sources.heat_source_interface.HeatSource`).
- **`ReactorHeatSource`**: Full reactor physics simulation.
- **`ConstantHeatSource`**: Simplified, instant-response heat source, ideal for testing secondary systems or for educational purposes focusing on plant balance.

## Usage

### Command-Line Interface (CLI)
The primary way to interact with the simulator is through the `nuclear-sim` command.

**Basic Command Structure:**
```bash
# If installed globally
nuclear-sim <command> [options]
# Or if running locally from project root
./nuclear-sim <command> [options]
```

**Main Commands:**
- `run`: Execute a nuclear plant scenario.
- `list`: Show all simulation runs.
- `status`: Show system status and summary of runs.
- `plot`: (Planned/Future) Create plots from run data via CLI.
- `params`: (Planned/Future) List available parameters for a run via CLI.
- `interactive`: Launch the simulator in interactive step-by-step mode.

**Running Scenarios:**
```bash
# Run a normal operation scenario
./nuclear-sim run normal_operation --name "Baseline Test" --duration 600

# Run with constant heat source
./nuclear-sim run normal_operation --name "Constant Heat Test" --heat-source constant --duration 300

# Run an emergency scenario
./nuclear-sim run steam_line_break --name "MSLB Test" --duration 300 --tags "emergency,training"
```
**Available Scenarios:**
- Normal Operations: `normal_operation`, `power_ramp_up`, `power_ramp_down`, `load_following`
- Emergency Scenarios: `steam_line_break`, `loss_of_coolant`, `turbine_trip`

**CLI Options for `run` command:**
  `--name NAME`: Run name (required).
  `--description DESC`: Run description.
  `--duration SECONDS`: Duration in seconds (default: 600).
  `--tags TAG1,TAG2`: Comma-separated tags.
  `--heat-source TYPE`: Heat source type: `reactor` or `constant` (default: `reactor`).

**Viewing and Managing Runs:**
```bash
# List all runs
./nuclear-sim list

# Filter runs by scenario type or tags
./nuclear-sim list --scenario-type steam_line_break
./nuclear-sim list --tags emergency

# Show system status (summary of runs)
./nuclear-sim status
```

### Interactive Mode
Run the simulator step-by-step with a real-time dashboard.
```bash
python nuclear_sim.py interactive <scenario_type> --name "Interactive Run Name"
# Example:
python nuclear_sim.py interactive normal_operation --name "Interactive Test"
```
**Interactive Controls:**
- `ENTER`: Advance one simulation step.
- `s <number>`: Advance multiple steps.
- `a`: Enable auto-advance mode.
- `p`: Pause auto-advance mode.
- `q`: Quit and save the session.

The `examples/` directory contains several `interactive_*.sh` scripts that provide convenient one-click launchers for common interactive scenarios. See `examples/README.md` for details.

### Python API Usage
You can also use the simulator components directly in Python scripts.
```python
from simulator.core.sim import NuclearPlantSimulator
from systems.primary.reactor.heat_sources import ConstantHeatSource

# Create simulator with constant heat source
heat_source = ConstantHeatSource(rated_power_mw=3000.0)
simulator = NuclearPlantSimulator(dt=1.0, heat_source=heat_source)

# Run simulation
simulator.reset()
for t in range(300):
    result = simulator.step()
    if result['done']:
        break
print(f"Final power: {simulator.state.power_level:.1f}%")
```
See `examples/nuclear_plant_constant_heat_simulation.ipynb` for a Jupyter Notebook demonstration.

## Output and Data Management

### Automatic Data Export
Every simulation run automatically generates:
- **Complete CSV Data Export**: All 22+ plant parameters logged at every timestep to `data/timeseries.csv` within the run directory.
- **Format**: `timestamp,parameter_name,value,unit,quality`.

### Logged Parameters (Examples)
- Power: `power_level`, `thermal_power`, `neutron_flux`
- Temperatures: `fuel_temperature`, `coolant_temperature`, `steam_temperature`
- Control: `control_rod_position`, `steam_valve_position`
- Safety: `scram_status`, `reactivity`

### Automatic Plotting
After each run, standard plots are generated in the `plots/` subdirectory of the run:
- Overview Plot: Key plant parameters.
- Power Parameters Plot.
- Temperature Parameters Plot.
- Control Parameters Plot.

### Run Organization
Each simulation creates a structured data package in `runs/<run_id>/`:
```
runs/normal_operation_20250603_171635/
├── data/
│   └── timeseries.csv          # Complete parameter data
├── plots/
│   ├── overview.png
│   ├── power_parameters.png
│   └── ... (other standard plots)
├── config/
│   ├── run_config.json         # Run configuration
│   └── scenario.json           # Scenario definition
└── logs/
    └── execution.json          # Execution metadata
```

## Development

### Adding New Heat Sources
1. Create a class inheriting from `systems.primary.reactor.heat_sources.heat_source_interface.HeatSource`.
2. Implement the required methods (`update`, `get_thermal_power_mw`, etc.).
3. Pass an instance of your new heat source to the `NuclearPlantSimulator` constructor.

### Adding New Systems
1. Create a new directory under `systems/` (e.g., `systems/auxiliary/feedwater_system/`).
2. Implement system classes and logic.
3. Integrate the new system into the main `NuclearPlantSimulator` in `simulator/core/sim.py`.

### Testing
The project uses a custom test framework. See `tests/README.md` for details on running and adding tests.
```bash
# Run all tests
python tests/test_suite.py
# Or using pytest
python -m pytest tests/
```

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add tests for new functionality.
5. Submit a pull request.

## License
[Add your license information here]

## Support
- Check examples in `examples/README.md`.
- Review test files in `tests/README.md`.
- Open an issue on GitHub.

## Future Enhancements
- Advanced Control Systems (PID, MPC)
- Machine Learning Integration (RL agents)
- 3D Visualization
- Distributed Simulation
- Additional Heat Sources (MSR, Fusion)
- TimescaleDB/Grafana Integration

---
**Nuclear Plant Simulator** - A comprehensive, educational nuclear power plant simulation platform.
