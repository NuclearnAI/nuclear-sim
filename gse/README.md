# GSE GPWR Python Library

A complete, production-ready Python library for interfacing with the GSE GPWR nuclear power plant training simulator via ONC RPC protocol.

## Features

- **Low-level RPC client** - Complete ONC RPC implementation with record marking
- **XDR serialization** - Full XDR encoding/decoding for all data types
- **High-level GDA client** - Convenient Python API for simulator operations
- **RL Gym environment** - Standard RL interface for training agents
- **Type-safe** - Comprehensive type hints throughout
- **Well-documented** - Google-style docstrings and examples
- **Production-ready** - Error handling, logging, and testing

## Installation

```bash
cd /home/brad/Projects/nuclear-sim
pip install -e .
```

Or install dependencies directly:

```bash
pip install numpy pytest
```

## Quick Start

### Basic Usage

```python
from gse import GDAClient

# Connect to simulator
with GDAClient(host='10.1.0.123', port=9800) as client:
    # Read a variable
    power = client.read_variable('RCS01POWER')
    print(f"Reactor power: {power} MW")

    # Write a variable
    client.write_variable('RTC01DEMAND', 50.0)

    # Reset to initial condition
    client.reset_to_ic(100)  # 100% power IC
```

### RL Environment

```python
from gse import GPWREnvironment

# Create environment
env = GPWREnvironment(host='10.1.0.123')
env.connect()

# Reset
obs = env.reset(ic=100)

# Take actions
action = {
    'rod_demand': 0.0,
    'fw_flow_demand': 100.0,
}
obs, reward, done, info = env.step(action)

env.close()
```

### Custom Reward Function

```python
def custom_reward(prev_obs, action, obs):
    """Custom reward for power tracking."""
    target = 95.0
    error = abs(obs['reactor_power'] - target)
    return -error * 1.0

env = GPWREnvironment(
    reward_function=custom_reward,
    step_delay=0.1,
    max_episode_steps=1000
)
```

## API Overview

### GDAClient

The high-level client for GDA Server operations:

```python
from gse import GDAClient

client = GDAClient(host='10.1.0.123', port=9800)
client.connect()

# Variable access
value = client.read_variable('RCS01POWER')
client.write_variable('RTC01DEMAND', 50.0)

# Batch operations
values = client.read_variables(['RCS01POWER', 'PRS01PRESS'])
client.write_variables({'RTC01DEMAND': 50.0, 'CFW01DEMAND': 100.0})

# Variable metadata
gdes = client.get_variable_info('RCS01POWER')
print(f"{gdes.name}: {gdes.value} {gdes.unit}")

# Initial conditions
client.reset_to_ic(100)  # Reset to IC 100

# Malfunctions
malf_index = client.insert_malfunction(
    var_name='RCS01PUMP1SPD',
    final_value=50.0,
    ramp_time=10
)

# Get all active instructor actions
active = client.get_all_active()
print(f"Active malfunctions: {active.nummalf}")

client.disconnect()
```

### GPWREnvironment

Gym-compatible RL environment:

```python
from gse import GPWREnvironment

env = GPWREnvironment(
    host='10.1.0.123',
    port=9800,
    observation_vars={
        'power': 'RCS01POWER',
        'pressure': 'PRS01PRESS',
    },
    action_vars={
        'rods': 'RTC01DEMAND',
    },
    reward_function=custom_reward,
    step_delay=0.1,
    max_episode_steps=1000
)

# Standard Gym interface
with env:
    obs = env.reset(ic=100)

    for _ in range(100):
        action = {'rods': 0.0}
        obs, reward, done, info = env.step(action)

        if done:
            break
```

### Data Types

Complete type definitions for all GDA structures:

```python
from gse.types import GDES, MALFS, OVERS, DataType, PointType

# Variable metadata
gdes = GDES(
    name='RCS01POWER',
    type=DataType.R4,
    unit='MW',
    value='100.0'
)

# Malfunction structure
malf = MALFS(
    vars='RCS01PUMP1SPD',
    final=50.0,
    ramp=10,
    type=1
)
```

## Architecture

```
┌─────────────────────────────────────┐
│  Your RL Agent / Application        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  gse.env.GPWREnvironment            │
│  - Standard Gym interface           │
│  - Configurable obs/action spaces   │
│  - Custom reward functions          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  gse.gda_client.GDAClient           │
│  - High-level API                   │
│  - Variable read/write              │
│  - Malfunctions & IC management     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  gse.rpc_client.RPCClient           │
│  - ONC RPC protocol                 │
│  - Record marking                   │
│  - XID tracking                     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  gse.xdr (XDREncoder/XDRDecoder)    │
│  - XDR serialization                │
│  - All data types                   │
└─────────────────────────────────────┘
               │ TCP Socket
┌──────────────▼──────────────────────┐
│  GSE GPWR Simulator (10.1.0.123)    │
│  - GDA Server (port 9800)           │
│  - Nuclear plant model              │
└─────────────────────────────────────┘
```

## Module Reference

### `gse.gda_client`

High-level GDA Server client with convenient methods:
- `read_variable()` - Read single variable
- `write_variable()` - Write single variable
- `read_variables()` - Batch read
- `write_variables()` - Batch write
- `get_variable_info()` - Get metadata (GDES)
- `reset_to_ic()` - Load initial condition
- `insert_malfunction()` - Insert malfunction
- `get_all_active()` - Get all active instructor actions

### `gse.rpc_client`

Low-level ONC RPC client:
- Complete RPC message formatting (call/reply)
- Record marking protocol for TCP
- XID tracking and verification
- Error handling for all RPC error codes
- Fragment reassembly

### `gse.xdr`

XDR encoding/decoding:
- `XDREncoder` - Serialize data to network format
- `XDRDecoder` - Deserialize data from network
- All basic types: int, uint, long, float, double, bool, string, bytes
- Arrays and structures

### `gse.env`

RL Gym environment:
- Standard Gym interface (reset, step, render)
- Configurable observation/action spaces
- Custom reward functions
- Safety limit checking
- Episode management

### `gse.types`

Data structures:
- `GDES` - Variable metadata
- `MALFS` - Malfunction structure
- `OVERS` - Override structure
- `REMS` - Remote function structure
- `GLCF` - Component failure structure
- `FPO` - Fixed parameter override
- `ANO` - Annunciator override
- `ALLACTIVE` - All active instructor actions
- Enums: `DataType`, `PointType`

## Examples

See `examples/basic_usage.py` for complete examples:

1. Basic connection and variable access
2. Context manager usage
3. Write operations
4. Initial conditions
5. Malfunction insertion
6. RL environment usage
7. Custom reward functions
8. Variable metadata queries

Run examples:

```bash
cd /home/brad/Projects/nuclear-sim
python -m gse.examples.basic_usage
```

## Testing

Run unit tests:

```bash
cd /home/brad/Projects/nuclear-sim
pytest gse/tests/ -v
```

Run specific test file:

```bash
pytest gse/tests/test_xdr.py -v
pytest gse/tests/test_rpc.py -v
```

Integration tests (require simulator):

```bash
# Edit test files to enable integration tests
pytest gse/tests/ -v -m integration
```

## Error Handling

The library provides custom exceptions:

```python
from gse.exceptions import (
    GSEError,              # Base exception
    RPCError,              # RPC protocol error
    ConnectionError,       # Connection failed
    TimeoutError,          # Operation timeout
    VariableNotFoundError, # Variable doesn't exist
    XDRError,              # Serialization error
    MalfunctionError,      # Malfunction operation failed
    InitialConditionError, # IC operation failed
)

try:
    client.read_variable('INVALID_VAR')
except VariableNotFoundError as e:
    print(f"Variable not found: {e.variable_name}")
except GSEError as e:
    print(f"GSE error: {e}")
```

## Logging

Enable logging for debugging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all GSE operations will log
client = GDAClient(host='10.1.0.123')
client.connect()  # Will log connection details
```

## Configuration

### Default Configuration

```python
# GDA Server
DEFAULT_HOST = '10.1.0.123'
DEFAULT_PORT = 9800
DEFAULT_TIMEOUT = 10.0

# RPC
DEFAULT_PROGRAM = 0x20000001
DEFAULT_VERSION = 1

# Environment
DEFAULT_STEP_DELAY = 0.1  # seconds
DEFAULT_MAX_STEPS = 1000
```

### Custom Configuration

```python
# Custom GDA client
client = GDAClient(
    host='192.168.1.100',
    port=9800,
    timeout=5.0,
    program=0x20000001,
    version=1
)

# Custom environment
env = GPWREnvironment(
    host='10.1.0.123',
    step_delay=0.05,  # Faster updates
    max_episode_steps=5000,
    observation_vars=custom_obs,
    action_vars=custom_actions,
    reward_function=custom_reward
)
```

## Common Variables

### Observation Variables

```python
obs_vars = {
    # Reactor
    'reactor_power': 'RCS01POWER',      # Reactor power (MW)
    'avg_temp': 'RCS01TAVE',            # Average temperature (°F)
    'hot_leg_temp': 'RCS01THOT',        # Hot leg temperature
    'cold_leg_temp': 'RCS01TCOLD',      # Cold leg temperature

    # Pressurizer
    'przr_pressure': 'PRS01PRESS',      # Pressure (psia)
    'przr_level': 'PRS01LEVEL',         # Level (%)

    # Steam Generators
    'sg1_level': 'SGN01LEVEL',          # SG1 level (%)
    'sg1_pressure': 'SGN01PRESS',       # SG1 pressure (psia)
    'sg2_level': 'SGN02LEVEL',          # SG2 level (%)
    'sg2_pressure': 'SGN02PRESS',       # SG2 pressure (psia)

    # Turbine
    'turbine_speed': 'TUR01SPEED',      # Turbine speed (RPM)
    'gen_power': 'GEN01POWER',          # Generator power (MW)
}
```

### Action Variables

```python
action_vars = {
    # Control rods
    'rod_demand': 'RTC01DEMAND',        # Rod position demand (%)

    # Pressurizer control
    'przr_spray': 'PRS01SPRAY',         # Spray valve position (%)
    'przr_heaters': 'PRS01HEATERS',     # Heater power (%)

    # Feedwater control
    'fw_flow_demand': 'CFW01DEMAND',    # FW flow demand (%)

    # Turbine control
    'turbine_governor': 'TUR01GOVERNOR', # Governor valve (%)
}
```

## Troubleshooting

### Connection Issues

```python
# Check if simulator is running
import socket
try:
    sock = socket.socket()
    sock.settimeout(2.0)
    sock.connect(('10.1.0.123', 9800))
    sock.close()
    print("Simulator is reachable")
except:
    print("Cannot reach simulator")
```

### Variable Not Found

```python
# Use get_variable_info to check if variable exists
try:
    gdes = client.get_variable_info('RCS01POWER')
    print(f"Variable exists: {gdes.name}")
except VariableNotFoundError:
    print("Variable does not exist")
```

### Timeout Issues

```python
# Increase timeout for slow operations
client = GDAClient(timeout=30.0)

# Or for specific operations
env = GPWREnvironment(step_delay=0.5)  # Wait longer for updates
```

## Performance Tips

1. **Batch operations** - Use `read_variables()` and `write_variables()` for multiple vars
2. **Connection reuse** - Keep client connected instead of reconnecting
3. **Step delay** - Adjust `step_delay` based on simulator update rate
4. **Logging** - Disable debug logging in production for better performance

## License

Internal use for nuclear simulation research.

## Support

For issues or questions:
- Check the API reference: `/home/brad/Projects/nuclear-sim/GSE_GPWR_API_Reference.md`
- Review examples: `gse/examples/basic_usage.py`
- Run tests: `pytest gse/tests/ -v`

## Version History

### 1.0.0 (2025-01-XX)
- Initial release
- Complete ONC RPC implementation
- XDR serialization/deserialization
- High-level GDA client
- RL Gym environment wrapper
- Comprehensive type definitions
- Unit tests and examples
