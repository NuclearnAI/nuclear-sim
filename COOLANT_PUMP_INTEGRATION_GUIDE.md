# Coolant Pump Integration Guide

This guide shows how to add coolant pumps to your nuclear simulation project and integrate them with your existing reactor physics.

## Overview

The coolant pump system provides:
- **4 reactor coolant pumps** in 3 primary loops (typical PWR configuration)
- **Individual pump control** (start/stop, speed control)
- **Automatic flow control** with target setpoints
- **Protection systems** (low flow, high temperature, low pressure trips)
- **Realistic dynamics** (startup/shutdown times, speed ramping)
- **Integration with thermal hydraulics** (flow affects reactor cooling)

## Quick Start

### 1. Basic Integration

```python
from simulator.core.sim import NuclearPlantSimulator, ControlAction
from systems.primary.coolant import CoolantPumpSystem

# Create reactor simulator
reactor_sim = NuclearPlantSimulator(dt=1.0, enable_secondary=True)

# Add coolant pump system
pump_system = CoolantPumpSystem(num_pumps=4, num_loops=3)

# In your simulation loop:
for t in range(simulation_time):
    # Update pump system
    system_conditions = {
        'system_pressure': reactor_sim.state.coolant_pressure,
        'coolant_temperature': reactor_sim.state.coolant_temperature,
        'suction_pressure': reactor_sim.state.coolant_pressure - 0.5
    }
    
    pump_result = pump_system.update_system(
        dt=1.0,
        system_conditions=system_conditions
    )
    
    # Update reactor flow based on pump performance
    reactor_sim.state.coolant_flow_rate = pump_result['total_flow_rate']
    
    # Step reactor simulation
    reactor_result = reactor_sim.step(action=ControlAction.NO_ACTION)
```

### 2. Pump Control

```python
# Control individual pumps
pump_controls = {
    'RCP-1A_start': True,           # Start pump RCP-1A
    'RCP-2A_stop': True,            # Stop pump RCP-2A
    'RCP-1A_speed_setpoint': 90.0,  # Set pump speed to 90%
    'target_total_flow': 15000.0    # Set system target flow
}

pump_result = pump_system.update_system(
    dt=1.0,
    system_conditions=system_conditions,
    control_inputs=pump_controls
)
```

### 3. Monitor Pump Status

```python
# Get system status
system_state = pump_system.get_system_state()

print(f"Total Flow: {system_state['total_flow_rate']:.0f} kg/s")
print(f"Running Pumps: {len(system_state['running_pumps'])}")
print(f"System Available: {system_state['system_available']}")

# Get individual pump details
for pump_id, pump_state in system_state['pump_states'].items():
    print(f"{pump_id}: {pump_state['status']} at {pump_state['speed_percent']:.1f}%")
```

## Pump System Configuration

### Default Configuration
- **4 pumps total**: RCP-1A, RCP-2A, RCP-3A, RCP-1B
- **3 primary loops**: Loop 1, Loop 2, Loop 3
- **Design flow**: 17,100 kg/s total (5,700 kg/s per pump)
- **Minimum pumps**: 2 pumps required for safe operation

### Pump Naming Convention
- `RCP-{loop}{pump}`: e.g., RCP-1A, RCP-2A, RCP-3A, RCP-1B
- Loop numbers: 1, 2, 3
- Pump letters: A, B, C, D...

## Control Options

### Individual Pump Control
```python
pump_controls = {
    'RCP-1A_start': True,           # Start specific pump
    'RCP-1A_stop': True,            # Stop specific pump
    'RCP-1A_speed_setpoint': 85.0   # Set pump speed (30-105%)
}
```

### System-Level Control
```python
pump_controls = {
    'target_total_flow': 16000.0,   # Target system flow (kg/s)
    'auto_control': True            # Enable automatic flow control
}
```

## Protection Systems

The pump system includes realistic protection features:

### Automatic Trips
- **Low Flow**: < 1,000 kg/s per pump
- **Low System Pressure**: < 10.0 MPa
- **High Coolant Temperature**: > 350°C

### Trip Recovery
```python
# Reset a tripped pump
pump_system.pumps['RCP-1A'].reset_trip()

# Then start the pump
pump_controls = {'RCP-1A_start': True}
```

## Integration with Existing Code

### Method 1: Modify Existing Simulator

Add pump system to your existing `NuclearPlantSimulator`:

```python
# In your simulator initialization
self.pump_system = CoolantPumpSystem(num_pumps=4, num_loops=3)

# In your step() method
def step(self, action, pump_controls=None):
    # Update pumps first
    pump_result = self.pump_system.update_system(
        dt=self.dt,
        system_conditions={
            'system_pressure': self.state.coolant_pressure,
            'coolant_temperature': self.state.coolant_temperature
        },
        control_inputs=pump_controls or {}
    )
    
    # Update reactor flow
    self.state.coolant_flow_rate = pump_result['total_flow_rate']
    
    # Continue with existing step logic...
```

### Method 2: Wrapper Class

Create a wrapper class (like in the demo):

```python
class EnhancedNuclearPlant:
    def __init__(self):
        self.reactor_sim = NuclearPlantSimulator()
        self.pump_system = CoolantPumpSystem()
    
    def step(self, reactor_action, pump_controls):
        # Update pumps
        pump_result = self.pump_system.update_system(...)
        
        # Update reactor
        self.reactor_sim.state.coolant_flow_rate = pump_result['total_flow_rate']
        reactor_result = self.reactor_sim.step(reactor_action)
        
        return {'reactor': reactor_result, 'pumps': pump_result}
```

## Realistic Scenarios

### Pump Trip Scenario
```python
# Normal operation
for t in range(60):
    result = plant.step()

# Trip a pump
pump_controls = {'RCP-1A_stop': True}
result = plant.step(pump_controls=pump_controls)

# System automatically adjusts flow with remaining pumps
# Flow reduces from ~17,100 to ~12,800 kg/s
```

### Load Following
```python
# Reduce power and flow together
reactor_action = ControlAction.CONTROL_ROD_INSERT
pump_controls = {'target_total_flow': 14000.0}

result = plant.step(
    reactor_action=reactor_action,
    pump_controls=pump_controls
)
```

### Emergency Scenarios
```python
# Multiple pump trips
pump_controls = {
    'RCP-1A_stop': True,
    'RCP-2A_stop': True
}

result = plant.step(pump_controls=pump_controls)

if not result['pumps']['system_available']:
    print("WARNING: Insufficient pumps - Natural circulation mode")
    # Reactor automatically limits flow to 2000 kg/s
```

## Performance Characteristics

### Flow-Speed Relationship
- Flow approximately proportional to pump speed
- System resistance effects included
- Temperature and pressure corrections applied

### Power Consumption
- Power ∝ Speed^2.5 (typical for centrifugal pumps)
- Rated power: 6.5 MW per pump at 100% speed
- Total system: ~26 MW at full power

### Dynamics
- **Speed ramp rate**: 10%/s maximum
- **Startup time**: 30 seconds to rated speed
- **Coastdown time**: 120 seconds from rated speed
- **Flow control deadband**: 200 kg/s

## Monitoring and Diagnostics

### Key Parameters to Monitor
```python
# System level
total_flow = pump_result['total_flow_rate']
running_pumps = pump_result['num_running_pumps']
system_available = pump_result['system_available']
total_power = pump_result['total_power_consumption']

# Individual pumps
for pump_id, details in pump_result['pump_details'].items():
    speed = details['speed_percent']
    flow = details['flow_rate']
    status = details['status']
    available = details['available']
    trip_active = details['trip_active']
```

### Status Values
- **running**: Pump operating normally
- **stopped**: Pump stopped
- **starting**: Pump in startup sequence
- **stopping**: Pump in shutdown sequence
- **tripped**: Pump tripped by protection system

## Advanced Features

### Custom Pump Configuration
```python
# Create system with different configuration
pump_system = CoolantPumpSystem(num_pumps=6, num_loops=4)

# Adjust system parameters
pump_system.total_design_flow = 20000.0  # Higher flow design
pump_system.minimum_pumps_required = 3   # Higher minimum
```

### Manual Flow Control
```python
# Disable automatic control
pump_system.auto_flow_control = False

# Manual speed control for each pump
pump_controls = {
    'RCP-1A_speed_setpoint': 90.0,
    'RCP-2A_speed_setpoint': 85.0,
    'RCP-3A_speed_setpoint': 95.0
}
```

## Integration with RL Training

The pump system can be integrated with reinforcement learning:

```python
# Add pump actions to RL action space
class ExtendedControlAction(Enum):
    # Existing actions...
    START_PUMP = 11
    STOP_PUMP = 12
    INCREASE_PUMP_SPEED = 13
    DECREASE_PUMP_SPEED = 14

# In RL environment step function
def step(self, action_idx):
    action = ExtendedControlAction(action_idx)
    
    # Convert to pump controls
    pump_controls = {}
    if action == ExtendedControlAction.START_PUMP:
        # Start first available stopped pump
        for pump_id, pump in self.pump_system.pumps.items():
            if pump.state.status.value == 'stopped':
                pump_controls[f'{pump_id}_start'] = True
                break
    
    # Step simulation
    result = self.plant.step(
        reactor_action=action,
        pump_controls=pump_controls
    )
    
    return result
```

## Troubleshooting

### Common Issues

1. **Pumps not starting**
   - Check if pump is available: `pump.state.available`
   - Reset trip if needed: `pump.reset_trip()`

2. **Flow not matching target**
   - Check if automatic control is enabled
   - Verify pump speeds are within limits
   - Check system resistance effects

3. **Unexpected pump trips**
   - Monitor system conditions (pressure, temperature)
   - Check protection setpoints
   - Review trip reasons in pump state

### Debug Information
```python
# Get detailed pump state
for pump_id, pump in pump_system.pumps.items():
    state = pump.get_pump_state()
    print(f"{pump_id}: {state}")
    
    if state['trip_active']:
        print(f"  Trip reason: {pump.state.trip_reason}")
```

## Summary

The coolant pump system provides a realistic and comprehensive model of PWR reactor coolant pumps that integrates seamlessly with your existing nuclear simulation. Key benefits:

- **Realistic operation**: Based on actual PWR pump characteristics
- **Easy integration**: Minimal changes to existing code
- **Comprehensive control**: Individual and system-level control options
- **Safety features**: Protection systems and trip logic
- **Performance modeling**: Accurate flow, power, and dynamic behavior

The system is ready to use and can be easily customized for different reactor designs or operational scenarios.
