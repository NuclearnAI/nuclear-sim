# Dataclass-Based Configuration Engine

The Dataclass-Based Configuration Engine provides a type-safe, physics-aware system for generating nuclear plant configurations that reliably trigger specific maintenance actions for testing purposes.

## Overview

This system leverages the sophisticated dataclass configurations from `systems/secondary` to generate comprehensive YAML configurations for action-targeted test scenarios. Unlike template-based approaches, this system uses actual dataclass factories and type validation to ensure consistency and reliability.

## Architecture

```
data_gen/config_engine/
├── __init__.py                    # Package exports
├── README.md                      # This documentation
├── composers/                     # Dataclass-based composers
│   ├── __init__.py               # Composer exports
│   └── comprehensive_composer.py # Main action-targeted composer
└── generated_configs/            # Output directory for generated configs
```

## Key Features

### 1. **Type-Safe Configuration Generation**
- **Dataclass Integration**: Uses actual secondary system dataclass configurations
- **Type Validation**: Full type checking throughout the configuration process
- **Consistency**: Same configs used by the secondary system itself
- **No Template Drift**: Direct dataclass usage eliminates template synchronization issues

### 2. **Action-Targeted Test Scenarios**
- **Reliable Triggering**: Physics-based targeting ensures maintenance actions trigger
- **Aggressive Mode**: Target subsystem configured for rapid action triggering
- **Quiet Mode**: Other subsystems configured to avoid interference
- **60+ Actions**: Supports all maintenance actions across all subsystems

### 3. **Comprehensive Output**
- **Complete Configurations**: 14+ sections covering entire plant operation
- **Physics Models**: TSP fouling, rotor dynamics, chemistry tracking
- **Maintenance Integration**: Seamless AutoMaintenanceSystem integration
- **Verification Ready**: Generates configs optimized for CSV verification workflow

## Quick Start

### Basic Usage
```python
from data_gen.config_engine import ComprehensiveComposer

# Initialize composer
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

### Convenience Functions
```python
from data_gen.config_engine import save_action_test_config

# One-step config generation and saving
config_file = save_action_test_config(
    target_action="oil_top_off", 
    duration_hours=1.0
)
```

### List Available Actions
```python
composer = ComprehensiveComposer()

# List all 60+ available actions
all_actions = composer.list_available_actions()
print(f"Total actions: {len(all_actions)}")

# List by subsystem
sg_actions = composer.get_actions_by_subsystem("steam_generator")
turbine_actions = composer.get_actions_by_subsystem("turbine")
feedwater_actions = composer.get_actions_by_subsystem("feedwater")
condenser_actions = composer.get_actions_by_subsystem("condenser")
```

## Supported Maintenance Actions

### **Steam Generator Actions (10)**
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

### **Turbine Actions (23)**
- `turbine_bearing_inspection` - Inspect turbine bearings
- `turbine_bearing_replacement` - Replace worn bearings
- `bearing_clearance_check` - Check bearing clearances
- `bearing_alignment` - Align bearing assemblies
- `thrust_bearing_adjustment` - Adjust thrust bearings
- `turbine_oil_change` - Change turbine oil
- `turbine_oil_top_off` - Top off turbine oil
- `oil_filter_replacement` - Replace oil filters
- `oil_cooler_cleaning` - Clean oil cooling system
- `lubrication_system_test` - Test lubrication system
- `rotor_inspection` - Inspect turbine rotor
- `thermal_bow_correction` - Correct thermal bow
- `critical_speed_test` - Test critical speeds
- `overspeed_test` - Test overspeed protection
- `vibration_monitoring_calibration` - Calibrate vibration monitoring
- `dynamic_balancing` - Balance rotor assembly
- `turbine_performance_test` - Performance testing
- `turbine_protection_test` - Test protection systems
- `thermal_stress_analysis` - Analyze thermal stresses
- `turbine_system_optimization` - System optimization
- `vibration_analysis` - Vibration analysis
- `efficiency_analysis` - Efficiency analysis

### **Feedwater Actions (21)**
- `oil_top_off` - Add oil to restore level
- `oil_change` - Change pump oil
- `pump_inspection` - Comprehensive pump inspection
- `impeller_inspection` - Inspect pump impeller
- `impeller_replacement` - Replace worn impeller
- `bearing_replacement` - Replace worn bearings
- `seal_replacement` - Replace mechanical seals
- `bearing_inspection` - Inspect pump bearings
- `seal_inspection` - Inspect mechanical seals
- `coupling_alignment` - Align pump coupling
- `pump_alignment_check` - Check pump alignment
- `npsh_analysis` - Net positive suction head analysis
- `cavitation_analysis` - Cavitation analysis
- `suction_system_check` - Check suction system
- `discharge_system_inspection` - Inspect discharge system
- `flow_system_inspection` - Inspect flow system
- `flow_control_inspection` - Inspect flow control
- `lubrication_system_check` - Check lubrication system
- `cooling_system_check` - Check cooling system
- `component_overhaul` - Complete component overhaul

### **Condenser Actions (18)**
- `condenser_tube_cleaning` - Clean condenser tubes
- `condenser_tube_plugging` - Plug leaking tubes
- `condenser_tube_inspection` - Inspect condenser tubes
- `condenser_biofouling_removal` - Remove biological fouling
- `condenser_scale_removal` - Remove mineral scale
- `condenser_chemical_cleaning` - Chemical cleaning
- `condenser_mechanical_cleaning` - Mechanical cleaning
- `condenser_hydroblast_cleaning` - High-pressure cleaning
- `condenser_water_treatment` - Water treatment
- `condenser_performance_test` - Performance testing
- `vacuum_ejector_cleaning` - Clean vacuum ejectors
- `vacuum_ejector_nozzle_replacement` - Replace ejector nozzles
- `vacuum_ejector_inspection` - Inspect vacuum ejectors
- `vacuum_system_test` - Test vacuum system
- `vacuum_leak_detection` - Detect and repair air leaks
- `intercondenser_cleaning` - Clean intercondenser
- `aftercondenser_cleaning` - Clean aftercondenser
- `motive_steam_system_check` - Check motive steam system
- `vacuum_system_check` - Check vacuum system

## Technical Implementation

### Dataclass Integration
The system directly imports and uses dataclass configurations:

```python
from systems.secondary.config import SecondarySystemConfig
from systems.secondary.steam_generator.config import SteamGeneratorConfig
from systems.secondary.turbine.config import TurbineConfig
from systems.secondary.feedwater.config import FeedwaterConfig
from systems.secondary.condenser.config import CondenserConfig
```

### Action-Targeted Configuration
For each target action, the system:

1. **Identifies target subsystem** from action-subsystem mapping
2. **Creates aggressive config** for target subsystem to trigger action quickly
3. **Creates quiet configs** for other subsystems to avoid interference
4. **Applies physics-based thresholds** based on action requirements
5. **Sets frequent check intervals** for reliable triggering

### Example: TSP Chemical Cleaning
```python
# Aggressive steam generator config
sg_config.tsp_fouling.base_fouling_rate = 0.1  # 100x faster fouling
sg_config.tsp_fouling.temperature_coefficient = 0.5  # More temperature sensitive
sg_config.maintenance.tsp_fouling_threshold = 0.5  # Lower threshold (mm)
sg_config.maintenance.individual_sg_check_interval_hours = 0.1  # Check every 6 minutes

# Quiet turbine config (won't trigger maintenance)
turbine_config.maintenance.efficiency_threshold = 0.1  # Very low
turbine_config.maintenance.performance_test_interval_hours = 9999.0  # Never check
```

## Configuration Structure

Generated configurations include 14+ comprehensive sections:

### **Core Sections**
- `plant_name`, `plant_id` - Plant identification
- `simulation_config` - Duration, time step, noise settings
- `load_profiles` - Power operation profiles
- `secondary_system` - Complete secondary system configuration

### **Subsystem Sections**
- `steam_generator` - Steam generator configuration
- `turbine` - Turbine system configuration  
- `feedwater` - Feedwater system configuration
- `condenser` - Condenser system configuration

### **Integration Sections**
- `maintenance_system` - Maintenance thresholds and scheduling
- `water_chemistry` - Primary and secondary chemistry control
- `performance_monitoring` - Efficiency tracking and alarms
- `environmental` - Site conditions and cooling water

### **Metadata Section**
- `metadata` - Configuration metadata including target action, creation date, validation status

## Verification Workflow

The generated configurations enable clear verification through CSV outputs:

### 1. **State History CSV**
Shows complete system evolution:
```csv
time,SG-001.tsp_fouling_fraction,SG-001.tube_wall_temp,...
0.5,0.03,285.0,...                    # Normal operation
1.0,0.06,290.0,...                    # TSP fouling crosses threshold
1.5,0.01,285.0,...                    # After maintenance - restored
```

### 2. **Work Orders CSV**
Shows maintenance actions executed:
```csv
work_order_id,component_id,action_type,status,created_time,completed_time,success
WO-001,SG-001,tsp_chemical_cleaning,COMPLETED,1.0,1.5,True
```

### 3. **Verification Pattern**
1. **Generate config** for target action
2. **Run simulation** with generated config
3. **Check state CSV** for parameter threshold crossing
4. **Check work orders CSV** for action execution
5. **Verify restoration** in state CSV

## Testing

### Run Test Suite
```bash
cd data_gen
python test_action_composer.py
```

### Test Coverage
- Basic functionality testing
- Steam generator scenarios
- Feedwater scenarios
- Convenience functions
- Comprehensive structure compliance

### Example Test Output
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

## API Reference

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

## Benefits

### **Type Safety**
- Full dataclass validation with type hints
- Compile-time error detection
- IDE support with autocomplete and type checking

### **Reliability**
- Physics-based targeting ensures reliable action triggering
- No template synchronization issues
- Consistent with secondary system implementation

### **Maintainability**
- Single source of truth for configurations
- Direct dataclass usage eliminates duplication
- Clear separation of concerns

### **Comprehensive Coverage**
- 60+ maintenance actions supported
- Complete plant configuration coverage
- Seamless simulation system integration

This dataclass-based approach provides a robust, type-safe foundation for generating action-targeted test scenarios that reliably demonstrate maintenance system functionality.
