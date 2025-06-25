# Nuclear Plant Scenario Runner

A unified script to generate and run nuclear plant scenarios using your composer suite. This tool combines both maintenance-targeted scenarios (using the ComprehensiveComposer) and operational scenarios (using the ScenarioGenerator) into a single, easy-to-use interface.

## Features

- **Maintenance Scenarios**: Generate scenarios that target specific maintenance actions (oil changes, cleaning, inspections, etc.)
- **Operational Scenarios**: Generate reactor physics scenarios (power ramps, emergency scenarios, load following)
- **Batch Processing**: Run multiple scenarios automatically
- **Interactive Mode**: User-friendly menu-driven interface
- **Comprehensive Output**: Automatic data export, visualization generation, and results analysis

## Quick Start

### 1. Test the Installation

```bash
# Run basic functionality tests
python test_scenario_runner.py

# Run full test including simulation
python test_scenario_runner.py --full-test
```

### 2. List Available Options

```bash
# List all maintenance actions
python scenario_runner.py --list-actions

# List all operational scenarios
python scenario_runner.py --list-scenarios
```

### 3. Run Your First Scenario

```bash
# Run a maintenance scenario
python scenario_runner.py --action oil_top_off --duration 1.0

# Run an operational scenario
python scenario_runner.py --scenario normal_operation --duration 2.0
```

## Usage Examples

### Single Maintenance Scenario

```bash
# Target a specific maintenance action
python scenario_runner.py --action tsp_chemical_cleaning --duration 2.0

# Use conservative thresholds (less aggressive triggering)
python scenario_runner.py --action oil_top_off --duration 1.5 --conservative

# Specify custom output directory
python scenario_runner.py --action scale_removal --duration 1.0 --output-dir my_results
```

### Single Operational Scenario

```bash
# Normal operation
python scenario_runner.py --scenario normal_operation --duration 2.0

# Power ramp with custom target
python scenario_runner.py --scenario power_ramp_up --duration 1.5 --target-power 115

# Emergency scenario
python scenario_runner.py --scenario steam_line_break --duration 0.5
```

### Batch Processing

```bash
# Run multiple maintenance actions
python scenario_runner.py --batch-maintenance --actions "oil_top_off,tsp_chemical_cleaning,scale_removal" --count 2

# Run with custom duration and conservative mode
python scenario_runner.py --batch-maintenance --actions "bearing_inspection,pump_inspection" --duration 1.5 --count 3 --conservative
```

### Run All Actions

```bash
# Run ALL available maintenance actions
python scenario_runner.py --run-all-actions --duration 1.0

# Run all actions for a specific subsystem
python scenario_runner.py --run-all-actions --subsystem turbine --duration 1.5

# Run all actions except specific ones
python scenario_runner.py --run-all-actions --exclude-actions "oil_top_off,bearing_inspection" --duration 2.0

# Run all actions with multiple runs per action
python scenario_runner.py --run-all-actions --count 2 --duration 1.0
```

### Interactive Mode

```bash
# Launch interactive menu
python scenario_runner.py --interactive
```

The interactive mode provides a user-friendly menu where you can:
- Browse available actions and scenarios
- Select scenarios by number or name
- Set custom parameters
- View results in real-time

## Available Maintenance Actions

The scenario runner supports 60+ maintenance actions across four subsystems:

### Steam Generator (10 actions)
- `tsp_chemical_cleaning` - TSP fouling chemical cleaning
- `tsp_mechanical_cleaning` - TSP fouling mechanical cleaning
- `scale_removal` - Tube scale removal
- `moisture_separator_maintenance` - Moisture separator maintenance
- `secondary_side_cleaning` - General secondary side cleaning
- And more...

### Turbine (23 actions)
- `oil_top_off` - Lubrication oil top-off
- `oil_change` - Complete oil change
- `bearing_inspection` - Bearing inspection
- `vibration_analysis` - Vibration analysis
- `efficiency_analysis` - Performance efficiency analysis
- And more...

### Feedwater (21 actions)
- `pump_inspection` - Pump inspection
- `impeller_replacement` - Impeller replacement
- `seal_replacement` - Seal replacement
- `coupling_alignment` - Coupling alignment
- `cavitation_analysis` - Cavitation analysis
- And more...

### Condenser (19 actions)
- `condenser_tube_cleaning` - Condenser tube cleaning
- `vacuum_system_test` - Vacuum system testing
- `biofouling_removal` - Biofouling removal
- `chemical_cleaning` - Chemical cleaning
- And more...

## Available Operational Scenarios

- `normal_operation` - Normal plant operation with minor adjustments
- `power_ramp_up` - Controlled power increase
- `power_ramp_down` - Controlled power decrease
- `load_following` - Variable power following grid demand
- `steam_line_break` - Steam line break accident
- `loss_of_coolant` - Loss of coolant accident (LOCA)
- `turbine_trip` - Turbine trip event
- `control_rod_malfunction` - Control rod malfunction
- `feedwater_transient` - Feedwater system transient
- `reactor_scram` - Emergency reactor shutdown

## Output Structure

Each scenario run creates a timestamped directory with:

### Maintenance Scenarios
```
simulation_runs/
└── oil_top_off_20250624_133045/
    ├── config.yaml                    # Generated configuration
    ├── work_order_tracking_results.png # Performance plots
    ├── work_order_gantt_chart.png     # Work order timeline
    ├── simulation_data_*.csv          # Raw simulation data
    ├── work_order_history_*.csv       # Work order details
    ├── component_health_data_*.csv    # Component health metrics
    └── maintenance_statistics_*.csv    # Maintenance statistics
```

### Operational Scenarios
```
simulation_runs/
└── normal_operation_20250624_133045/
    ├── scenario.json                  # Scenario definition
    ├── results.json                   # Simulation results
    └── simulation_data.csv            # Time series data
```

## Configuration Options

### Maintenance Scenarios

- **Aggressive Mode** (default): Uses very sensitive thresholds to reliably trigger maintenance actions
- **Conservative Mode**: Uses normal thresholds, may not trigger actions in short simulations
- **Duration**: Simulation time in hours (0.1 to 24+ hours supported)
- **Plant Name**: Custom plant identification

### Operational Scenarios

- **Duration**: Simulation time in hours
- **Target Power**: For power ramp scenarios (default: 110% for ramp up, 70% for ramp down)
- **Random Seed**: For reproducible scenarios (set in ScenarioGenerator)

## Advanced Usage

### Custom Output Directory

```bash
python scenario_runner.py --action oil_top_off --output-dir /path/to/results
```

### Quiet Mode

```bash
python scenario_runner.py --action oil_top_off --quiet
```

### Parameter Sweeps (Manual)

```bash
# Run same action with different durations
for duration in 0.5 1.0 1.5 2.0; do
    python scenario_runner.py --action oil_top_off --duration $duration
done
```

## Integration with Existing Tools

The scenario runner integrates seamlessly with your existing infrastructure:

- **ComprehensiveComposer**: For maintenance-targeted configurations
- **ScenarioGenerator**: For operational scenarios
- **WorkOrderTrackingSimulation**: For maintenance scenario execution
- **NuclearPlantSimulator**: For operational scenario execution
- **Visualization Tools**: Automatic plot generation
- **Data Export**: CSV export for further analysis

## Troubleshooting

### Common Issues

1. **No maintenance actions triggered**
   - Try increasing duration (`--duration 2.0` or higher)
   - Ensure aggressive mode is enabled (default)
   - Check that the action name is correct (`--list-actions`)

2. **Import errors**
   - Ensure you're running from the project root directory
   - Check that all dependencies are installed
   - Verify Python path includes the project directory

3. **Simulation crashes**
   - Check the generated configuration files for errors
   - Try shorter durations first
   - Use `--verbose` for detailed error messages

### Getting Help

```bash
# Show all command line options
python scenario_runner.py --help

# List available actions and scenarios
python scenario_runner.py --list-actions
python scenario_runner.py --list-scenarios

# Use interactive mode for guided usage
python scenario_runner.py --interactive
```

## Performance Notes

- **Maintenance scenarios**: Typically take 10-60 seconds for 1-2 hour simulations
- **Operational scenarios**: Usually complete in 5-30 seconds
- **Batch processing**: Scales linearly with number of scenarios
- **Output files**: Range from a few MB to 100+ MB depending on duration and data collection

## Next Steps

1. **Start with testing**: Run `python test_scenario_runner.py` to verify everything works
2. **Explore interactively**: Use `python scenario_runner.py --interactive` to browse options
3. **Run single scenarios**: Try specific maintenance actions or operational scenarios
4. **Scale up**: Use batch processing for systematic testing
5. **Analyze results**: Use the generated CSV files and plots for analysis

## Examples for Common Use Cases

### Testing Maintenance System
```bash
# Quick test of oil maintenance
python scenario_runner.py --action oil_top_off --duration 0.5

# Comprehensive pump testing
python scenario_runner.py --batch-maintenance --actions "pump_inspection,bearing_inspection,seal_inspection" --count 2
```

### Training Data Generation
```bash
# Generate diverse operational scenarios
python scenario_runner.py --scenario normal_operation --duration 4.0
python scenario_runner.py --scenario load_following --duration 6.0
python scenario_runner.py --scenario power_ramp_up --duration 2.0
```

### Emergency Response Training
```bash
# Emergency scenarios
python scenario_runner.py --scenario steam_line_break --duration 1.0
python scenario_runner.py --scenario loss_of_coolant --duration 1.5
python scenario_runner.py --scenario turbine_trip --duration 2.0
```

This scenario runner provides a powerful, unified interface to your nuclear plant simulation capabilities, making it easy to generate training data, test maintenance systems, and explore operational scenarios.
