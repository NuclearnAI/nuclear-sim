# Nuclear Plant Action-Targeted Configuration Generator

This directory contains a **type-safe, dataclass-based** configuration generation system that leverages the sophisticated dataclass configurations from `systems/secondary` to generate comprehensive YAML configurations for action-targeted test scenarios.

## 🚀 Key Features

### Core Capabilities
1. **Dataclass Integration**: Uses secondary system's dataclass configs directly
2. **Action-Targeted Generation**: Creates scenarios that reliably trigger specific maintenance actions
3. **Type Safety**: Full type validation throughout the configuration process
4. **Maintenance Integration**: Seamless integration with the AutoMaintenanceSystem
5. **Comprehensive Output**: Generates complete configs matching the comprehensive nuclear plant schema

### Clean Architecture
```
data_gen/
├── config_engine/
│   ├── composers/                      # Dataclass-based composers
│   │   ├── comprehensive_composer.py   # Main action-targeted composer
│   │   └── __init__.py
│   ├── generated_configs/              # Output directory
│   └── README.md                       # Detailed technical documentation
├── test_action_composer.py            # Test suite for the system
└── README_refactored.md               # This overview document
```

## 🎯 Action-Targeted Test Scenarios

The system creates **action-targeted test scenarios** that:

1. **Target specific maintenance actions** (e.g., "tsp_chemical_cleaning")
2. **Configure physics aggressively** to trigger the action quickly
3. **Silence other subsystems** to avoid interference
4. **Generate comprehensive YAML** that works with the simulation system

### Example: TSP Chemical Cleaning Test
```python
from data_gen.config_engine import ComprehensiveComposer

composer = ComprehensiveComposer()

# Generate action-targeted test scenario
config = composer.compose_action_test_scenario(
    target_action="tsp_chemical_cleaning",
    duration_hours=1.5,
    aggressive_mode=True
)

# Save configuration
config_file = composer.save_config(config, "tsp_test")
```

This generates a comprehensive YAML config where:
- **Steam generator TSP fouling rate** is 100x faster
- **TSP fouling threshold** is lowered to 0.5mm
- **Check interval** is every 6 minutes
- **Other subsystems** have permissive thresholds (won't trigger)

## 📊 Verification Workflow

The generated configs enable clear verification in CSV outputs:

### 1. Complete State History CSV
Shows the full system state evolution including:
- Target parameter crossing threshold
- Parameter restoration after maintenance
- All other system parameters for context

### 2. Completed Work Orders CSV
Shows maintenance actions that were triggered and executed:
- Work order creation time
- Action type and component
- Execution success and duration

### Example Verification Pattern
```csv
# State History CSV
time,SG-001.tsp_fouling_fraction,SG-001.tube_wall_temp,...
0.5,0.03,285.0,...                    # Normal operation
1.0,0.06,290.0,...                    # TSP fouling crosses 0.05 threshold
1.5,0.01,285.0,...                    # After maintenance - restored

# Work Orders CSV
work_order_id,component_id,action_type,status,created_time,completed_time,success
WO-001,SG-001,tsp_chemical_cleaning,COMPLETED,1.0,1.5,True
```

## 🔧 Available Maintenance Actions

The system supports **60+ maintenance actions** across all subsystems:

### Steam Generator Actions (10)
- `tsp_chemical_cleaning` - Chemical cleaning of TSP fouling
- `tsp_mechanical_cleaning` - Mechanical cleaning of TSP fouling
- `scale_removal` - Remove mineral scale deposits
- `moisture_separator_maintenance` - Steam quality maintenance
- `secondary_side_cleaning` - General secondary side cleaning
- `steam_dryer_cleaning` - Steam dryer maintenance
- `water_chemistry_adjustment` - Chemistry optimization
- `tube_bundle_inspection` - Comprehensive tube inspection
- `eddy_current_testing` - Non-destructive tube testing
- `tube_sheet_inspection` - Tube sheet examination

### Turbine Actions (23)
- `turbine_bearing_inspection` - Inspect turbine bearings
- `turbine_bearing_replacement` - Replace worn bearings
- `vibration_analysis` - Vibration monitoring and analysis
- `efficiency_analysis` - Turbine efficiency analysis
- `turbine_oil_top_off` - Top off turbine oil
- `turbine_oil_change` - Change turbine oil
- `overspeed_test` - Test overspeed protection
- `dynamic_balancing` - Balance rotor assembly
- `rotor_inspection` - Inspect turbine rotor
- `thermal_stress_analysis` - Analyze thermal stresses
- And 13 more...

### Feedwater Actions (21)
- `oil_top_off` - Add oil to restore level
- `oil_change` - Change pump oil
- `pump_inspection` - Comprehensive pump inspection
- `impeller_inspection` - Inspect pump impeller
- `impeller_replacement` - Replace worn impeller
- `bearing_replacement` - Replace worn bearings
- `seal_replacement` - Replace mechanical seals
- `coupling_alignment` - Align pump coupling
- `npsh_analysis` - Net positive suction head analysis
- `cavitation_analysis` - Cavitation analysis
- And 11 more...

### Condenser Actions (18)
- `condenser_tube_cleaning` - Clean condenser tubes
- `condenser_tube_inspection` - Inspect condenser tubes
- `condenser_biofouling_removal` - Remove biological fouling
- `condenser_scale_removal` - Remove mineral scale
- `vacuum_system_test` - Test vacuum system
- `vacuum_leak_detection` - Detect and repair air leaks
- `vacuum_ejector_cleaning` - Clean vacuum ejectors
- `condenser_performance_test` - Performance testing
- `condenser_chemical_cleaning` - Chemical cleaning
- `condenser_mechanical_cleaning` - Mechanical cleaning
- And 8 more...

## 🚀 Quick Start Guide

### 1. Basic Usage
```python
from data_gen.config_engine import (
    ComprehensiveComposer,
    save_action_test_config
)

# Simple: Create and save config in one step
config_file = save_action_test_config("tsp_chemical_cleaning", duration_hours=1.5)

# Advanced: Full control
composer = ComprehensiveComposer()
config = composer.compose_action_test_scenario(
    target_action="scale_removal",
    duration_hours=2.0,
    plant_name="Scale Removal Test Plant",
    aggressive_mode=True
)
config_file = composer.save_config(config, "scale_test")
```

### 2. List Available Actions
```python
composer = ComprehensiveComposer()

# List all actions
all_actions = composer.list_available_actions()
print(f"Total actions: {len(all_actions)}")

# List by subsystem
sg_actions = composer.get_actions_by_subsystem("steam_generator")
turbine_actions = composer.get_actions_by_subsystem("turbine")
feedwater_actions = composer.get_actions_by_subsystem("feedwater")
condenser_actions = composer.get_actions_by_subsystem("condenser")
```

### 3. Run Test Suite
```bash
cd data_gen
python test_action_composer.py
```

## 🏗️ Technical Architecture

### Dataclass Integration
The system leverages the secondary system's sophisticated dataclass architecture:

```python
# Uses actual dataclass factories
sg_config = create_standard_sg_config()
turbine_config = create_standard_turbine_config()

# Applies action-specific modifications
if target_action == "tsp_chemical_cleaning":
    sg_config.tsp_fouling.base_fouling_rate = 0.1  # 100x faster
    sg_config.maintenance.tsp_fouling_threshold = 0.5  # Lower threshold

# Composes into secondary system config
secondary_config = SecondarySystemConfig(
    steam_generator=sg_config,
    turbine=turbine_config,
    # ... other subsystems
)

# Serializes to comprehensive YAML
comprehensive_config = {
    'secondary_system': secondary_config.to_dict(),
    'steam_generator': sg_config.to_dict(),
    # ... other sections
}
```

### Action-Subsystem Mapping
The composer maintains a comprehensive mapping of maintenance actions to target subsystems:

```python
action_subsystem_map = {
    "tsp_chemical_cleaning": "steam_generator",
    "vibration_analysis": "turbine", 
    "oil_top_off": "feedwater",
    "condenser_tube_cleaning": "condenser",
    # ... 60+ total mappings
}
```

### Aggressive vs Quiet Configuration
- **Target subsystem**: Gets aggressive configuration to trigger the action
- **Other subsystems**: Get quiet configuration to avoid interference

```python
# Aggressive steam generator for TSP cleaning
sg_config.tsp_fouling.base_fouling_rate = 0.1  # Fast fouling
sg_config.maintenance.tsp_fouling_threshold = 0.5  # Low threshold

# Quiet turbine (won't trigger maintenance)
turbine_config.maintenance.efficiency_threshold = 0.1  # Very low
turbine_config.maintenance.performance_test_interval_hours = 9999.0  # Never check
```

## 📈 System Benefits

### 1. Type Safety
- **Full dataclass validation** with type hints
- **Compile-time error detection**
- **IDE support** with autocomplete and type checking

### 2. Maintenance Integration
- **Uses actual maintenance catalog** and component physics
- **Physics-based targeting** ensures reliable action triggering
- **Seamless AutoMaintenanceSystem integration**

### 3. Consistency
- **Uses same dataclass configs** as secondary system
- **Single source of truth** for configurations
- **No template drift** or synchronization issues

### 4. Reliability
- **Physics-based targeting** ensures reliable action triggering
- **Comprehensive verification workflow** through CSV outputs
- **Proven action-targeting methodology**

### 5. Comprehensive Output
- **Complete comprehensive configs** matching target schema
- **14+ configuration sections** covering entire plant operation
- **Ready for simulation** with no additional setup required

## 🧪 Testing and Validation

### Test Suite
Run the comprehensive test suite:
```bash
python data_gen/test_action_composer.py
```

Tests include:
- Basic functionality
- Steam generator scenarios
- Feedwater scenarios  
- Convenience functions
- Comprehensive structure compliance

### Manual Testing
1. **Generate config** for target action
2. **Run simulation** with generated config
3. **Check state CSV** for parameter threshold crossing
4. **Check work orders CSV** for action execution
5. **Verify restoration** in state CSV

### Example Test Results
```
🧪 Testing Action-Targeted Configuration Composer
============================================================

📋 Available Actions by Subsystem:

STEAM_GENERATOR (10 actions):
  • tsp_chemical_cleaning
  • tsp_mechanical_cleaning
  • scale_removal
  • moisture_separator_maintenance
  • secondary_side_cleaning

🔧 Testing Steam Generator Action Scenarios
--------------------------------------------------

1. TSP Chemical Cleaning Test:
   ✅ Generated config with 14 sections
   💾 Saved to: data_gen/generated_configs/tsp_cleaning_test_20250624_130604.yaml
   🎯 TSP fouling rate: 0.1
   🎯 TSP threshold: 0.5 mm
   🎯 Check interval: 0.1 hours
```

## 📚 API Reference

### ComprehensiveComposer

#### `compose_action_test_scenario(target_action, duration_hours=2.0, plant_name=None, aggressive_mode=True)`
Creates a comprehensive configuration targeting a specific maintenance action.

**Parameters:**
- `target_action` (str): Maintenance action to target
- `duration_hours` (float): Simulation duration
- `plant_name` (str, optional): Plant name override
- `aggressive_mode` (bool): Use aggressive thresholds for reliable triggering

**Returns:**
- `Dict[str, Any]`: Complete comprehensive configuration

#### `save_config(config, filename, output_dir=None)`
Saves configuration to YAML file.

#### `list_available_actions()`
Returns list of all available maintenance actions.

#### `get_actions_by_subsystem(subsystem)`
Returns list of actions for specific subsystem.

### Convenience Functions

#### `create_action_test_config(target_action, duration_hours=2.0)`
Creates action test configuration in one step.

#### `save_action_test_config(target_action, duration_hours=2.0, output_dir=None)`
Creates and saves action test configuration in one step.

## 🎯 Next Steps

1. **Run test suite** to verify functionality
2. **Generate test configs** for your target actions
3. **Run simulations** with generated configs
4. **Analyze CSV outputs** to verify action triggering
5. **Iterate on thresholds** if needed for reliable triggering

## 📖 Additional Documentation

For detailed technical documentation, see:
- **[config_engine/README.md](config_engine/README.md)** - Complete technical documentation
- **[test_action_composer.py](test_action_composer.py)** - Test suite and examples

The dataclass-based system provides a robust, type-safe foundation for generating action-targeted test scenarios that reliably demonstrate maintenance system functionality.
