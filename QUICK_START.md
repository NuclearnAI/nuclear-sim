# GSE GPWR Library - Quick Start Guide

## Installation

No installation needed - the library is ready to use:

```bash
cd /home/brad/Projects/nuclear-sim
python3 -c "import gse; print('GSE library loaded successfully')"
```

## Quick Test

Test the library without connecting to the simulator:

```bash
# Run unit tests
python3 -m pytest gse/tests/ -v

# Should see: 40 passed, 2 skipped
```

## First Connection (When Simulator is Available)

```python
from gse import GDAClient

# Connect to simulator
with GDAClient(host='10.1.0.123', port=9800) as client:
    # Read reactor power
    power = client.read_variable('RCS01POWER')
    print(f"Reactor power: {power} MW")
```

## RL Training Example

```python
from gse import GPWREnvironment

# Create environment
env = GPWREnvironment(host='10.1.0.123')

with env:
    # Reset to 100% power initial condition
    obs = env.reset(ic=100)
    print(f"Initial power: {obs['reactor_power']:.2f} MW")

    # Training loop
    for episode in range(10):
        obs = env.reset(ic=100)
        done = False
        total_reward = 0

        while not done:
            # Your RL agent policy here
            action = {
                'rod_demand': 0.0,  # No rod motion
                'fw_flow_demand': 100.0,  # Full feedwater
            }

            obs, reward, done, info = env.step(action)
            total_reward += reward

        print(f"Episode {episode}: Total reward = {total_reward:.2f}")
```

## File Structure

```
gse/
├── __init__.py           # Package initialization
├── rpc_client.py         # Low-level RPC client
├── xdr.py                # XDR serialization
├── gda_client.py         # High-level GDA client
├── types.py              # Data structures
├── env.py                # RL environment
├── exceptions.py         # Custom exceptions
├── README.md             # Full documentation
├── examples/
│   └── basic_usage.py    # Usage examples
└── tests/
    ├── __init__.py
    ├── test_xdr.py       # XDR tests
    └── test_rpc.py       # RPC tests
```

## Common Operations

### Read/Write Variables

```python
from gse import GDAClient

with GDAClient(host='10.1.0.123') as client:
    # Single read
    power = client.read_variable('RCS01POWER')

    # Batch read
    values = client.read_variables([
        'RCS01POWER',
        'PRS01PRESS',
        'SGN01LEVEL'
    ])

    # Single write
    client.write_variable('RTC01DEMAND', 50.0)

    # Batch write
    client.write_variables({
        'RTC01DEMAND': 50.0,
        'CFW01DEMAND': 100.0,
    })
```

### Reset to Initial Condition

```python
with GDAClient(host='10.1.0.123') as client:
    # Reset to 100% power
    client.reset_to_ic(100)

    # Reset to cold shutdown
    client.reset_to_ic(0)
```

### Insert Malfunction

```python
with GDAClient(host='10.1.0.123') as client:
    # Insert pump speed malfunction
    malf_index = client.insert_malfunction(
        var_name='RCS01PUMP1SPD',
        final_value=50.0,  # Reduce to 50%
        ramp_time=10,      # Over 10 seconds
        delay=0,           # Start immediately
    )
    print(f"Malfunction inserted: {malf_index}")
```

## Common Variables

### Reactor System (RCS)
- `RCS01POWER` - Reactor power (MW)
- `RCS01TAVE` - Average temperature (°F)
- `RCS01THOT` - Hot leg temperature (°F)
- `RCS01TCOLD` - Cold leg temperature (°F)

### Pressurizer (PRS)
- `PRS01PRESS` - Pressure (psia)
- `PRS01LEVEL` - Water level (%)
- `PRS01SPRAY` - Spray valve position (%)
- `PRS01HEATERS` - Heater power (%)

### Steam Generators (SGN)
- `SGN01LEVEL` - SG 1 level (%)
- `SGN01PRESS` - SG 1 pressure (psia)
- `SGN02LEVEL` - SG 2 level (%)
- `SGN02PRESS` - SG 2 pressure (psia)

### Control Systems
- `RTC01DEMAND` - Rod control demand (%)
- `CFW01DEMAND` - Feedwater flow demand (%)
- `TUR01GOVERNOR` - Turbine governor (%)

## Next Steps

1. **Run Examples**: `python3 -m gse.examples.basic_usage`
2. **Read Full Docs**: `gse/README.md`
3. **API Reference**: `GSE_GPWR_API_Reference.md`
4. **Customize Environment**: Modify `GPWREnvironment` for your RL task

## Troubleshooting

### Import Error
```bash
# Make sure you're in the project directory
cd /home/brad/Projects/nuclear-sim
python3 -c "import gse"
```

### Connection Error
```python
# Verify simulator is running
import socket
sock = socket.socket()
sock.settimeout(2.0)
try:
    sock.connect(('10.1.0.123', 9800))
    print("Simulator is reachable")
except:
    print("Cannot reach simulator - check if it is running")
finally:
    sock.close()
```

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all operations will log details
from gse import GDAClient
client = GDAClient(host='10.1.0.123')
```

## Support

- **Full Documentation**: `gse/README.md`
- **API Reference**: `GSE_GPWR_API_Reference.md`
- **Examples**: `gse/examples/basic_usage.py`
- **Tests**: `gse/tests/`
