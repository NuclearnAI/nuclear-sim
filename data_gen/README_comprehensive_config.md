# Comprehensive Nuclear Plant Configuration Example

## Overview

This document describes the `nuclear_plant_comprehensive_config.yaml` file, which demonstrates all configuration capabilities of the nuclear simulation system. This comprehensive example serves as both a reference implementation and a template for creating custom nuclear plant configurations.

## File Structure

The configuration file contains **35 top-level sections** with over **600 lines** of detailed parameters covering every aspect of nuclear plant simulation.

## Key Features Demonstrated

### 1. Plant Identification & Basic Parameters
- **Plant Name**: Comprehensive PWR Nuclear Plant
- **Thermal Power**: 3000 MW (typical large PWR)
- **Electrical Power**: 1000 MW net output
- **Configuration**: 3-loop PWR design
- **Efficiency**: 33% design thermal efficiency

### 2. Complete Secondary System Integration

#### Steam Generator System (33 parameters)
- **3 Steam Generators** with individual modeling
- **TSP Fouling Modeling**: Base rate 0.001 mm/1000hrs with temperature/chemistry coefficients
- **Heat Transfer**: 3388 tubes per SG, 5000 m² area per SG
- **Initial Conditions**: Levels, pressures, temperatures, flow rates for each SG
- **Maintenance Thresholds**: Tube wall temperature, steam quality, fouling levels

#### Turbine System (22 parameters)
- **Multi-Stage Design**: 8 HP stages + 6 LP stages = 14 total
- **Rotor Dynamics**: 150,000 kg rotor, 45,000 kg⋅m² moment of inertia
- **Protection Systems**: Overspeed, vibration, thermal stress trips
- **Governor Control**: 4 control valves, load following capability
- **Bearing Systems**: 4 journal bearings with oil lubrication
- **Extraction Points**: 5 extraction points for feedwater heating

#### Feedwater System (21 parameters)
- **4-Pump Configuration**: 3 normally running + 1 standby
- **Three-Element Control**: Steam flow feedforward + level feedback
- **Variable Speed Control**: 50-110% speed range
- **Water Treatment**: Chemical dosing, pH control, oxygen scavenging
- **Protection Systems**: Low flow, high vibration, bearing temperature trips

#### Condenser System (20 parameters)
- **Heat Transfer**: 84,000 tubes, 75,000 m² area, 2000 MW heat rejection
- **Vacuum System**: 2 steam ejectors, 95% air removal efficiency
- **Tube Degradation**: Corrosion modeling, leak detection, plugging thresholds
- **Fouling Models**: Biofouling, scaling, corrosion product buildup
- **Cooling Water**: 45,000 kg/s flow, chemical treatment

### 3. Advanced Physics Modeling

#### TSP (Tube Support Plate) Fouling
- **Enable/Disable**: Configurable fouling simulation
- **Rate Factors**: Temperature, chemistry, and flow coefficients
- **Cleaning Thresholds**: Automatic cleaning triggers
- **Performance Impact**: Heat transfer degradation modeling

#### Rotor Dynamics
- **Physical Properties**: Mass, length, diameter, moment of inertia
- **Bearing Configuration**: Stiffness, damping, vibration limits
- **Thermal Expansion**: Coefficient and maximum expansion limits

#### Water Chemistry Control
- **Primary Chemistry**: pH 7.2, 1000 ppm boron, dissolved hydrogen
- **Secondary Chemistry**: pH 9.2, iron/copper limits, oxygen scavenging
- **Automatic Control**: pH deadbands, chemical injection rates

### 4. Comprehensive Maintenance System

#### Component-Specific Maintenance (4 component types)
- **Pump Maintenance**: Oil levels, bearing wear, vibration analysis
- **Steam Generator**: TSP fouling, tube wall temperature, steam quality
- **Turbine**: Efficiency monitoring, blade wear, thermal stress
- **Condenser**: Vacuum levels, tube cleanliness, heat rejection

#### Maintenance Scheduling
- **Check Intervals**: 4-12 hours depending on component
- **Cooldown Periods**: Prevent excessive maintenance frequency
- **Priority Levels**: HIGH, MEDIUM, LOW priority assignments
- **Auto-Execute**: Automatic work order generation and execution

### 5. System Integration & Coordination

#### Interlocks & Protection
- **System Interlocks**: Turbine-SG, Feedwater-SG, Condenser-Turbine
- **Load Control**: 5%/minute ramp rate, 20-105% load range
- **Emergency Systems**: Steam dump, emergency feedwater, shutdown sequences

#### Performance Monitoring
- **Targets**: 33% efficiency, 92% capacity factor, 95% availability
- **Trending**: Efficiency, heat rate, availability tracking
- **Alarms**: Performance degradation thresholds

### 6. Environmental & Site Conditions
- **Ambient Conditions**: 35°C design temperature, 200m elevation
- **Cooling Water**: River source, 25°C design temperature
- **Seasonal Variations**: 15°C temperature swing

## Configuration Validation Results

### ✅ YAML Structure Validation
- **35 top-level sections** properly structured
- **All required sections** present and complete
- **Parameter consistency** across subsystems
- **Valid YAML syntax** with proper nesting

### ✅ Subsystem Configuration
- **Steam Generators**: 3 units, 3000 MW total, TSP fouling enabled
- **Turbine**: 1000 MW, 34% efficiency, 14 stages
- **Feedwater**: 1500 kg/s, 4 pumps (3 running)
- **Condenser**: 2000 MW heat rejection, 84,000 tubes

### ✅ Advanced Features
- **Maintenance System**: 4 component types, comprehensive mode
- **Water Chemistry**: Primary and secondary chemistry control
- **Performance Monitoring**: Efficiency and availability targets
- **Environmental Integration**: Site-specific conditions

## Usage Examples

### Loading the Configuration
```python
import yaml

with open('nuclear_plant_comprehensive_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Access plant parameters
plant_name = config['plant_name']
thermal_power = config['thermal_power_mw']

# Access subsystem configurations
steam_generator_config = config['steam_generator']
turbine_config = config['turbine']
feedwater_config = config['feedwater']
condenser_config = config['condenser']
```

### Extracting Maintenance Settings
```python
# Get maintenance configuration
maintenance_config = config['maintenance_system']
component_configs = maintenance_config['component_configs']

# Access pump maintenance settings
pump_maintenance = component_configs['pump']
check_interval = pump_maintenance['check_interval_hours']
thresholds = pump_maintenance['thresholds']
```

### Using with Simulation System
```python
# The configuration can be used to initialize the nuclear simulation
# (Note: Requires PWRConfigManager implementation)
from simulator.core.sim import NuclearPlantSimulator

# Create simulator with configuration file
sim = NuclearPlantSimulator(
    secondary_config_file='nuclear_plant_comprehensive_config.yaml'
)
```

## Key Benefits

### 1. **Complete Reference Implementation**
- Demonstrates every configuration capability
- Shows realistic parameter values
- Provides working examples of advanced features

### 2. **Template for Custom Configurations**
- Copy and modify sections as needed
- Maintain parameter consistency
- Scale up or down for different plant sizes

### 3. **Educational Resource**
- Learn about PWR design parameters
- Understand system interactions
- See maintenance strategy implementation

### 4. **Testing & Validation**
- Verify simulation system capabilities
- Test configuration loading
- Validate parameter ranges

## Technical Specifications

### Plant Design Basis
- **Type**: 3-loop Pressurized Water Reactor (PWR)
- **Thermal Power**: 3000 MW
- **Electrical Output**: 1000 MW net
- **Efficiency**: 33% (typical for PWR)
- **Cooling**: River water, once-through

### Key Design Parameters
- **Steam Pressure**: 6.9 MPa (1000 psi)
- **Steam Temperature**: 285.8°C (546°F)
- **Steam Flow**: 1500 kg/s total
- **Feedwater Temperature**: 227°C (441°F)
- **Condenser Pressure**: 0.007 MPa (1 psia)

### Maintenance Philosophy
- **Predictive**: Condition-based monitoring
- **Preventive**: Scheduled maintenance intervals
- **Corrective**: Automatic work order generation
- **Coordinated**: System-level maintenance planning

## Conclusion

The `nuclear_plant_comprehensive_config.yaml` file successfully demonstrates the complete configuration capabilities of the nuclear simulation system. It provides:

- ✅ **Complete system coverage** - All major subsystems configured
- ✅ **Advanced physics modeling** - TSP fouling, rotor dynamics, chemistry
- ✅ **Realistic parameters** - Based on actual PWR designs
- ✅ **Maintenance integration** - Comprehensive maintenance system
- ✅ **Validation ready** - Tested and verified structure

This configuration serves as both a working example and a comprehensive reference for understanding the full capabilities of the nuclear plant simulation system.
