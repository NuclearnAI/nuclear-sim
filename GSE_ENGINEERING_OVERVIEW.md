# GSE GPWR Simulator - Engineering Overview for RL

## Connection Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR CODE (Linux/Mac/wherever)                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Python RL Agent                                     │    │
│  │  └─ from gse import GPWREnvironment                  │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Network: TCP Socket
                       │ Protocol: ONC RPC (binary, like gRPC)
                       │ Address: 10.1.0.123:9800
                       │ Latency: ~10-50ms per call
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  WINDOWS VM (10.1.0.123)                                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  GDA Server (gdaserver.exe)                        │     │
│  │  - Port 9800 TCP listener                          │     │
│  │  - RPC request handler                             │     │
│  │  - Variable read/write interface                   │     │
│  └──────────────────┬─────────────────────────────────┘     │
│                     │ Shared Memory IPC                     │
│  ┌──────────────────▼─────────────────────────────────┐     │
│  │  MST (mst.exe) - Simulation Executive              │     │
│  │  - Loads mstG.dll (23MB plant physics model)       │     │
│  │  - Executes real-time simulation loop              │     │
│  │  - ~10,000 variables in memory                     │     │
│  │  - Configurable timestep (0.01-0.1 sec typical)    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## How It Works (Technical)

### 1. **Connection Protocol: ONC RPC**
- **Not HTTP/REST** - It's ONC RPC (Open Network Computing Remote Procedure Call)
- **Binary protocol** - Like gRPC/Protobuf, not JSON
- **Client-server model** - You make RPC calls, get responses
- **Transport**: TCP sockets with XDR (eXternal Data Representation) serialization
- **Authentication**: None required (trusted network)

### 2. **Message Flow**
```
Your Code                         GDA Server
   │                                  │
   ├─── TCP Connect ──────────────────>
   │                                  │
   ├─── RPC Call: read("RCS01POWER")─>
   │                                  │
   │                        [Reads from shared memory]
   │                                  │
   <──── RPC Reply: "98.5" ───────────┤
   │                                  │
   ├─── RPC Call: write("RTC01DEMAND", 50.0)─>
   │                                  │
   │                        [Writes to shared memory]
   │                                  │
   <──── RPC Reply: "OK" ─────────────┤
   │                                  │
```

### 3. **What's Actually Running**
- **mst.exe**: Main simulation executive - runs the plant model in real-time
- **mstG.dll**: The actual PWR physics model (thermodynamics, neutronics, etc.)
- **gdaserver.exe**: Your API gateway - handles RPC requests
- **dbaserver.exe**: Database server - variable metadata lookups
- **dirserver.exe**: Directory service - configuration info

## Core RL Capabilities

### 1. **Observation Space** - Read Variables
```python
# Read any of ~10,000 simulation variables
obs = client.read_variable('RCS01POWER')    # Reactor power
temp = client.read_variable('RCS01TAVE')    # Coolant temperature
press = client.read_variable('PRS01PRESS')  # Pressurizer pressure
level = client.read_variable('SGN01LEVEL')  # Steam generator level

# Batch reads for efficiency (one RPC call)
obs = client.read_variables([
    'RCS01POWER', 'RCS01TAVE', 'PRS01PRESS',
    'SGN01LEVEL', 'TUR01SPEED', 'GEN01POWER'
])
```

**RPC Call**: `CALLget` (procedure #85)
**Latency**: ~10ms for single read, ~20ms for batch of 10

### 2. **Action Space** - Write Controls
```python
# Write any controllable variable
client.write_variable('RTC01DEMAND', 50.0)    # Control rod position (%)
client.write_variable('CFW01DEMAND', 100.0)   # Feedwater flow (%)
client.write_variable('TUR01GOVERNOR', 95.0)  # Turbine governor (%)

# Batch writes
client.write_variables({
    'RTC01DEMAND': 50.0,
    'CFW01DEMAND': 100.0,
    'PRS01SPRAY': 0.0
})
```

**RPC Call**: `CALLpost` (procedure #86)
**Latency**: ~10ms

### 3. **Environment Reset** - Initial Conditions
```python
# Reset to saved plant state (like gym.reset())
client.reset_to_ic(100)  # 100% power operation
client.reset_to_ic(50)   # 50% power
client.reset_to_ic(0)    # Cold shutdown

# Each IC = snapshot of all 10k variables at a stable operating point
```

**RPC Call**: `CALLresetIC` (procedure #7)
**Latency**: ~2-5 seconds (full reset)

### 4. **Disturbances** - Malfunction Insertion
```python
# Inject equipment failures for robustness training
client.insert_malfunction(
    variable='RCS01PUMP1SPD',  # Reactor coolant pump 1
    final_value=0.0,           # Fail to 0% (pump stops)
    ramp_time=10,              # Gradual failure over 10 seconds
    delay=0                    # Start immediately
)

# Other malfunction types:
# - Step change (instant)
# - Ramp (gradual)
# - Bias (offset)
# - Drift (slow change)
```

**RPC Call**: `CALLsetMF` (procedure #23)

**Use Cases**:
- Train on rare events (pump trips, valve failures)
- Curriculum learning (add failures gradually)
- Robustness testing

### 5. **Overrides** - Force Variable Values
```python
# Lock a variable at specific value (useful for debugging/testing)
client.set_override('SGN01LEVEL', value=50.0)  # Force SG level to 50%
client.delete_override('SGN01LEVEL')           # Release it

# Use cases:
# - Simplify problem (freeze some variables)
# - Test isolated subsystems
# - Controlled experiments
```

**RPC Call**: `CALLsetOR` (procedure #11)

## Variable Space

### Systems Available (~10,000 variables total)

| System Code | Description | Key Variables |
|-------------|-------------|---------------|
| **RCS** | Reactor Coolant System | Power, Tavg, Thot, Tcold, Flow |
| **PRS** | Pressurizer | Pressure, Level, Heaters, Spray |
| **SGN** | Steam Generators (x2-4) | Level, Pressure, Steam Flow |
| **TUR** | Turbine | Speed, Load, Governor |
| **GEN** | Generator | Power Output, Frequency |
| **CFW** | Condensate/Feedwater | Flow, Temp, Pump Speed |
| **MSS** | Main Steam System | Pressure, Flow, Valve Position |
| **RTC** | Rod Control | Rod Position, Demand |
| **SIS** | Safety Injection | Flow, Pressure, Valve States |
| **RHR** | Residual Heat Removal | Flow, Temp, Valve States |

### Variable Naming Convention
```
<SYSTEM><LOOP/UNIT><COMPONENT><PARAMETER>

Examples:
RCS01TAVE    = RCS / Loop 01 / Average Temperature
PRS01PRESS   = PRS / Unit 01 / Pressure
SGN02LEVEL   = SGN / Unit 02 / Level
TUR01SPEED   = TUR / Unit 01 / Speed
```

### Data Types
```c
R4  = float  (4 bytes) - Most analog values
R8  = double (8 bytes) - High precision
I4  = int    (4 bytes) - Discrete values, counts
L4  = bool   (4 bytes) - On/off, open/closed
```

## Performance Characteristics

### Latency (on local network)
```
Single read:           ~10ms
Batch read (10 vars):  ~20ms
Single write:          ~10ms
Batch write (5 vars):  ~15ms
Reset to IC:           ~2-5 seconds
Malfunction insert:    ~10ms
```

### Throughput
```
Observations/sec:  ~50-100 Hz (with batching)
Actions/sec:       ~50-100 Hz
Episodes/hour:     ~100-200 (depends on episode length & reset time)
```

### Simulation Speed
```
Real-time:    1x (1 sim second = 1 real second)
Fast-time:    2-10x configurable
Slow-time:    0.1-0.5x for debugging
```

## Python Library Usage

### Simple Gym-like Interface
```python
from gse import GPWREnvironment

# Create environment
env = GPWREnvironment(
    host='10.1.0.123',
    port=9800,
    obs_vars=['RCS01POWER', 'RCS01TAVE', 'PRS01PRESS', ...],
    action_vars=['RTC01DEMAND', 'CFW01DEMAND', ...],
    reward_function=my_custom_reward,
    safety_limits={'PRS01PRESS': (1800, 2500), ...}
)

# Standard RL loop
with env:
    obs = env.reset(ic=100)  # Load 100% power IC

    for step in range(1000):
        action = agent.get_action(obs)
        obs, reward, done, info = env.step(action)

        if done:  # Trip or episode complete
            break
```

### Low-level RPC Interface
```python
from gse import GDAClient

# Direct RPC access (more control)
with GDAClient(host='10.1.0.123', port=9800) as client:
    # Read
    power = client.read_variable('RCS01POWER')

    # Write
    client.write_variable('RTC01DEMAND', 50.0)

    # Reset
    client.reset_to_ic(100)

    # Malfunction
    client.insert_malfunction(
        variable='RCS01PUMP1SPD',
        final_value=0.0,
        ramp_time=10
    )

    # Get metadata
    info = client.get_variable_info('RCS01POWER')
    # Returns: type, units, limits, description
```

## Key Differences vs Standard RL Environments

| Aspect | MuJoCo/Atari | GSE GPWR |
|--------|--------------|----------|
| **Speed** | <1ms/step | 10-50ms/step |
| **Reset** | Instant | 2-5 seconds |
| **Parallelization** | Easy (vectorized) | Hard (1 VM = 1 env) |
| **State dim** | 10-100 | 10,000 (choose subset) |
| **Physics** | Simplified | High-fidelity industrial |
| **Real-world** | Benchmark | Actual operator training simulator |

## Practical Considerations

### ✅ **Advantages**
- **High fidelity**: Real industrial physics model
- **Rich dynamics**: Complex interactions, long time horizons
- **Safety critical**: Learn robust policies with hard constraints
- **Variable access**: Choose what matters for your task
- **Network isolated**: Your code runs anywhere (Linux preferred)

### ⚠️ **Limitations**
- **Slow compared to MuJoCo**: ~20 steps/sec vs 1000+ steps/sec
- **Single environment**: Can't easily run 100 parallel envs
- **Reset time**: 2-5 seconds (sample efficiency matters more)
- **Windows dependency**: Simulator must run on Windows VM
- **Network latency**: ~10ms minimum (local network)

### 🎯 **Best For**
- **Sample-efficient RL**: DDPG, SAC, TD3, PPO (not DQN with replay buffer)
- **Continuous control**: Most variables are continuous
- **Long-horizon tasks**: Startup/shutdown sequences, load following
- **Safe RL**: Learn policies that respect constraints
- **Transfer learning**: Train in sim, deploy to real plant

## Example RL Tasks

### 1. **Power Tracking** (Easy)
- **Goal**: Maintain reactor power at setpoint (e.g., 95 MW)
- **Obs**: Power, temperature, pressure (~10 vars)
- **Action**: Rod demand, feedwater flow (~3 vars)
- **Reward**: `-abs(power - setpoint)`
- **Episode**: 1000 steps (~100 sec sim time)

### 2. **Load Following** (Medium)
- **Goal**: Track time-varying power setpoint
- **Obs**: Same as above + setpoint trajectory
- **Action**: Same as above
- **Reward**: Tracking error + control smoothness penalty
- **Episode**: 5000 steps (~500 sec)

### 3. **Emergency Response** (Hard)
- **Goal**: Respond to equipment failure, avoid trip
- **Obs**: Full state (~50-100 vars)
- **Action**: Multiple actuators (~10 vars)
- **Reward**: Sparse (avoid trip = +100, else 0)
- **Episode**: Until trip or recovery
- **Disturbances**: Random malfunction injection

## Getting Started Checklist

```bash
# 1. Ensure simulator is running on Windows VM
ssh brad@10.1.0.123
cd D:\GPWR\Plant
call UploadGPWR_EnglishUnit_ALL.cmd

# 2. Install library on your Linux machine
cd ~/Projects/nuclear-sim
pip install -e gse/

# 3. Test connection
python -c "from gse import GDAClient; \
           c = GDAClient('10.1.0.123'); \
           c.connect(); \
           print(f'Power: {c.read_variable(\"RCS01POWER\")}'); \
           c.disconnect()"

# 4. Run example
python gse/examples/basic_usage.py

# 5. Start RL training
python train_agent.py
```

## Summary

**You have**: Network-accessible nuclear plant simulator with full programmatic control

**You can**:
- ✅ Read any sensor (10k variables available)
- ✅ Write any control (rods, feedwater, turbine, etc.)
- ✅ Reset to known states (100+ ICs available)
- ✅ Inject failures for robustness training
- ✅ Run from Linux/anywhere over network

**Key numbers**:
- Latency: ~10-50ms per call
- Throughput: ~50 obs/sec
- Reset time: 2-5 seconds
- Variables: ~10,000 total

**Your Python library**:
- RPC client implemented
- Gym-like interface ready
- Cross-platform (Linux/Mac/Windows)
- 40 unit tests passing
- Examples and docs included

**Ready to train RL agents!** 🚀
