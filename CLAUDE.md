# Nuclear Simulator RL Project - Quick Start for Claude

**Last Updated**: December 2024

## What Is This Project?

This repository contains **two nuclear reactor simulators** for reinforcement learning research:

1. **Shep Sandbox** (`shep-sandbox` branch) - Python-based standalone simulator (~7,300 lines)
2. **GSE GPWR Integration** (`master` branch) - Interface to commercial nuclear training simulator ⭐

**You're probably interested in #2** - the GSE GPWR integration for real high-fidelity RL training.

---

## Architecture Overview

### The Two-Machine Setup

```
┌─────────────────────────────────────────────────────────┐
│  LINUX MACHINE (Your Development Box)                   │
│  Location: /home/brad/Projects/nuclear-sim/            │
│                                                          │
│  What runs here:                                         │
│  ✓ Python RL agent (PyTorch, TensorFlow, JAX)          │
│  ✓ Training scripts                                      │
│  ✓ GSE Python library (gse/)                            │
│  ✓ Data collection & analysis                           │
│  ✓ GPU-accelerated model training                       │
│                                                          │
└───────────────────────┬──────────────────────────────────┘
                        │
                        │ Network: TCP/IP
                        │ Protocol: ONC RPC
                        │ Port: 9800
                        │ Latency: ~10-50ms
                        │
┌───────────────────────▼──────────────────────────────────┐
│  WINDOWS VM (Simulator Host)                            │
│  IP: 10.1.0.123                                         │
│  Location: D:\GPWR\                                     │
│                                                          │
│  What runs here:                                         │
│  ✓ GSE GPWR Simulator (mst.exe + mstG.dll)             │
│  ✓ GDA Server (gdaserver.exe) - Port 9800              │
│  ✓ 23 MB compiled physics model (PWR plant)             │
│  ✓ ~10,000 simulation variables                         │
│  ✓ Real-time thermodynamic simulation                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Why This Architecture?

- **Simulator must run on Windows** - GSE GPWR is Windows-only (.exe/.dll files)
- **RL training runs on Linux** - Better for ML frameworks, GPUs, containers
- **Clean separation** - Simulator is a "physics engine service" over the network
- **Standard pattern** - This is how industrial simulators work (SCADA-like)

---

## Quick Start

### 1. Start the Simulator (Windows VM)

```bash
# SSH to Windows VM
ssh brad@10.1.0.123

# Start simulator
cd D:\GPWR\Plant
call UploadGPWR_EnglishUnit_ALL.cmd

# Wait ~30 seconds for startup
# You should see GDA Server running on port 9800
```

### 2. Install Python Library (Linux)

```bash
# Clone repo (if not already)
cd ~/Projects/nuclear-sim

# Install GSE library
pip install -e gse/

# Verify installation
python3 verify_library.py
```

### 3. Test Connection

```python
from gse import GDAClient

# Connect to simulator
with GDAClient(host='10.1.0.123', port=9800) as client:
    # Read reactor power
    power = client.read_variable('RCS01POWER')
    print(f"Reactor Power: {power} MW")

    # Write control rod position
    client.write_variable('RTC01DEMAND', 50.0)
    print("Control rods set to 50%")

    # Reset to 100% power initial condition
    client.reset_to_ic(100)
    print("Reset to 100% power IC")
```

### 4. Run RL Training

```python
from gse import GPWREnvironment

# Create RL environment
env = GPWREnvironment(
    host='10.1.0.123',
    port=9800
)

# Standard RL loop
with env:
    obs = env.reset(ic=100)  # Start at 100% power

    for step in range(1000):
        # Your RL agent picks action
        action = {'rod_demand': 0.0, 'fw_flow_demand': 100.0}

        # Take step in environment
        obs, reward, done, info = env.step(action)

        if done:
            break
```

---

## What Can You Do?

### Read Variables (Observations)
```python
# ~10,000 variables available
client.read_variable('RCS01POWER')    # Reactor power (MW)
client.read_variable('RCS01TAVE')     # Average temperature (°F)
client.read_variable('PRS01PRESS')    # Pressurizer pressure (psia)
client.read_variable('SGN01LEVEL')    # Steam generator level (%)
client.read_variable('TUR01SPEED')    # Turbine speed (RPM)
```

### Write Variables (Actions)
```python
# Control any controllable variable
client.write_variable('RTC01DEMAND', 50.0)   # Control rods (%)
client.write_variable('CFW01DEMAND', 100.0)  # Feedwater flow (%)
client.write_variable('TUR01GOVERNOR', 95.0) # Turbine governor (%)
```

### Reset Environment (Initial Conditions)
```python
client.reset_to_ic(100)  # 100% power operation
client.reset_to_ic(50)   # 50% power operation
client.reset_to_ic(0)    # Cold shutdown
```

### Insert Malfunctions (Disturbances)
```python
# Simulate pump failure
client.insert_malfunction(
    variable='RCS01PUMP1SPD',  # Reactor coolant pump 1
    final_value=0.0,           # Fail to 0%
    ramp_time=10               # Over 10 seconds
)
```

---

## Repository Structure

```
nuclear-sim/
├── CLAUDE.md                       ← You are here
├── GSE_ENGINEERING_OVERVIEW.md     ← Detailed technical overview
├── GSE_GPWR_API_Reference.md       ← Complete API documentation
├── QUICK_START.md                  ← Quick reference guide
│
├── gse/                            ← Main Python library
│   ├── __init__.py                 ← Package exports
│   ├── rpc_client.py               ← ONC RPC client
│   ├── xdr.py                      ← XDR serialization
│   ├── gda_client.py               ← GDA Server interface
│   ├── types.py                    ← Data structures
│   ├── env.py                      ← Gym environment
│   ├── exceptions.py               ← Custom exceptions
│   ├── README.md                   ← Library documentation
│   ├── tests/                      ← Unit tests (40 tests)
│   └── examples/                   ← Usage examples
│
├── setup.py                        ← Installation script
└── verify_library.py               ← Verification script
```

---

## Key Concepts

### 1. Variables
- **~10,000 simulation variables** organized by system (RCS, PRS, SGN, TUR, etc.)
- **Read any variable** for observations
- **Write controllable variables** for actions
- **Variable naming**: `<SYSTEM><UNIT><COMPONENT><PARAMETER>`
  - Example: `RCS01TAVE` = Reactor Coolant System, Loop 01, Average Temperature

### 2. Initial Conditions (ICs)
- **Saved plant states** (snapshots of all 10k variables)
- **Use for reset**: `client.reset_to_ic(100)` loads "100% power" state
- **Reset time**: 2-5 seconds
- **Common ICs**: 0 (cold shutdown), 50 (50% power), 100 (100% power)

### 3. RPC Protocol
- **ONC RPC** (Open Network Computing Remote Procedure Call)
- **Binary protocol** (like gRPC, not REST/JSON)
- **XDR serialization** (eXternal Data Representation)
- **Procedure calls**: Read (CALLget #85), Write (CALLpost #86), Reset (CALLresetIC #7)

### 4. Plant Systems
- **RCS**: Reactor Coolant System (core, pumps, loops)
- **PRS**: Pressurizer (pressure control)
- **SGN**: Steam Generators (heat exchangers)
- **TUR**: Turbine (power generation)
- **CFW**: Condensate/Feedwater (water supply)
- **RTC**: Rod Control (reactivity control)
- **SIS**: Safety Injection (emergency cooling)

---

## Performance Characteristics

### Speed
- **Read latency**: ~10ms (single variable), ~20ms (batch of 10)
- **Write latency**: ~10ms
- **Reset latency**: 2-5 seconds
- **Throughput**: ~50-100 observations/sec

### Comparison
| Aspect | MuJoCo/Gym | GSE GPWR |
|--------|------------|----------|
| Step time | <1ms | 10-50ms |
| Reset time | Instant | 2-5 sec |
| Parallel envs | Easy | Hard (need multiple VMs) |
| Physics | Simplified | Industrial high-fidelity |

### Best Practices
- ✅ Use **batch reads/writes** for efficiency
- ✅ Use **sample-efficient RL** (PPO, SAC, TD3)
- ✅ **Cache observations** if reading same variables repeatedly
- ✅ Use **vectorization across time** instead of parallel envs
- ❌ Avoid naive DQN with large replay buffers (too slow)

---

## Example RL Tasks

### 1. Power Tracking (Easy)
**Goal**: Keep reactor power at setpoint (e.g., 95 MW)
**Obs**: Power, temperature, pressure (~10 variables)
**Action**: Rod position, feedwater flow (~3 variables)
**Reward**: `-abs(power - setpoint)`

### 2. Load Following (Medium)
**Goal**: Track time-varying power demand
**Obs**: Power, temps, pressures + setpoint trajectory
**Action**: Rods, feedwater, turbine governor
**Reward**: Tracking error + smoothness penalty

### 3. Emergency Response (Hard)
**Goal**: Respond to equipment failures, avoid reactor trip
**Obs**: Full state (~50-100 variables)
**Action**: Multiple actuators (~10 variables)
**Reward**: Sparse (+100 for avoiding trip, 0 otherwise)
**Disturbances**: Random pump/valve failures

---

## Common Commands

### Start Simulator (Windows)
```cmd
cd D:\GPWR\Plant
call UploadGPWR_EnglishUnit_ALL.cmd
```

### Install Library (Linux)
```bash
cd ~/Projects/nuclear-sim
pip install -e gse/
```

### Run Tests
```bash
python3 -m pytest gse/tests/ -v
```

### Run Examples
```bash
python3 gse/examples/basic_usage.py
```

### Verify Installation
```bash
python3 verify_library.py
```

---

## Troubleshooting

### Can't connect to simulator
```bash
# Check if GDA server is running on Windows VM
ssh brad@10.1.0.123 "netstat -an | findstr 9800"

# Should see: TCP 0.0.0.0:9800 LISTENING
```

### Simulator not starting
```bash
# Check if processes are running
ssh brad@10.1.0.123 "tasklist | findstr mst"
ssh brad@10.1.0.123 "tasklist | findstr gdaserver"
```

### Import errors
```bash
# Reinstall library
cd ~/Projects/nuclear-sim
pip install -e gse/ --force-reinstall
```

### Network latency too high
- Ensure both machines on same local network
- Check firewall isn't blocking port 9800
- Use batch operations instead of individual calls

---

## Important Files to Read

### For Getting Started
1. **This file** (`CLAUDE.md`) - Overview and quick start
2. **QUICK_START.md** - Quick reference guide
3. **gse/README.md** - Library documentation
4. **gse/examples/basic_usage.py** - Working code examples

### For Deep Understanding
1. **GSE_ENGINEERING_OVERVIEW.md** - Detailed architecture and capabilities
2. **GSE_GPWR_API_Reference.md** - Complete API documentation (1,500+ lines)

### For Development
1. **gse/rpc_client.py** - RPC protocol implementation
2. **gse/xdr.py** - Serialization/deserialization
3. **gse/gda_client.py** - High-level client interface
4. **gse/env.py** - RL environment wrapper

---

## Git Branches

### `master` (current)
- GSE GPWR integration
- Python RPC library
- RL environment
- Documentation
- **Use this for RL training**

### `shep-sandbox`
- Standalone Python nuclear simulator
- ~7,300 lines of Python code
- Graph-based simulation framework
- **Different project, not related to GSE GPWR**

---

## Next Steps

### If you're training RL agents:
1. ✅ Simulator running? (Windows VM)
2. ✅ Library installed? (`pip install -e gse/`)
3. ✅ Connection tested? (Run verify_library.py)
4. 🚀 **Start training!** Use `GPWREnvironment` class

### If you're developing the library:
1. Read `GSE_GPWR_API_Reference.md` for API details
2. Look at `gse/tests/` for examples
3. Add new features to `gse/gda_client.py`
4. Write tests in `gse/tests/`

### If you're debugging:
1. Check Windows VM: SSH to 10.1.0.123
2. Verify simulator running: `tasklist | findstr mst`
3. Verify GDA server: `netstat -an | findstr 9800`
4. Test connection: `python3 verify_library.py`

---

## Contact & Support

**Windows VM**: 10.1.0.123 (SSH access configured)
**Simulator Location**: D:\GPWR\
**Python Library**: ~/Projects/nuclear-sim/gse/
**Git Repo**: git@github.com:NuclearnAI/nuclear-sim.git

**Key Documentation on Windows VM**:
- `D:\GPWR\Documentation\Software Manuals\SimExec_User_Guide.pdf`
- `D:\GPWR\Documentation\Software Manuals\jstation.pdf`

---

## Summary (TL;DR)

**What**: Interface to GSE GPWR nuclear training simulator for RL
**Where**: Simulator on Windows VM (10.1.0.123), your code on Linux
**How**: Network connection via ONC RPC on port 9800
**Library**: `gse/` Python package with Gym-like interface
**Variables**: ~10,000 available (sensors + controls)
**Performance**: ~50 steps/sec, 2-5 sec reset time
**Status**: ✅ Complete, tested, documented, ready for RL training

**Get started in 3 commands**:
```bash
pip install -e gse/
python3 verify_library.py
python3 gse/examples/basic_usage.py
```

🚀 **You're ready to train RL agents on a real nuclear power plant simulator!**
