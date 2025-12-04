# GSE GPWR Simulator - API Documentation for RL Integration

**VM**: gpwr (10.1.0.123)
**Location**: `D:\GPWR\`
**Version**: GPWR 6.2, JADE 5.1.1, SimExec 5.0.0
**Type**: Full-scope PWR (Pressurized Water Reactor) simulator

---

## Executive Summary

The GSE GPWR simulator is a commercial nuclear power plant training simulator with programmatic API access for reinforcement learning integration. It provides real-time simulation of a PWR plant with multiple network interfaces for reading sensor data and sending control commands.

---

## Architecture Overview

### Core Components

1. **SimExec** - Real-time simulation executive (C/C++/Fortran)
   - `mst.exe` - Main Simulation Task (runs plant model DLL)
   - `mstG.dll` - GPWR plant model (23 MB, compiled C code)
   - Real-time execution loop with configurable timestep

2. **JADE** - Control room graphics/HMI system (Java-based)
   - `JStation` - Main operator stations
   - `JOS` - Operator interface system
   - Displays/panels for all plant systems

3. **API Servers** - Network-accessible data interfaces
   - **GDA Server** (`gdaserver.exe`) - Generic Data Acquisition (**PRIMARY API**)
   - **DBA Server** (`dbaserver.exe`) - Database server
   - **Dir Server** (`dirserver.exe`) - Directory service
   - **OPC DA Server** (`WTOPCsvr.dll`) - Industrial standard protocol

4. **IFE** - Instructor Facility Equipment
   - Malfunction insertion
   - IC (Initial Condition) management
   - Plant state control

---

## Programmatic Interfaces

### 1. GDA Server (Recommended for RL)

**Port**: 9800 (TCP)
**Protocol**: ONC RPC (Remote Procedure Call)
**Host**: `localhost` or `10.1.0.123`

**Configuration** (from `setenv.cmd`):
```batch
set GDADC_HOST=localhost
set GDADC_SERVICE=9800
set GDA_COMPATIBILITY=SEIS
```

**Purpose**: Primary API for reading simulation variables and writing control commands in real-time.

**Capabilities**:
- Read any simulation variable by name
- Write values to controllable variables
- Subscribe to variable updates
- Batch read/write operations
- High-frequency sampling (suitable for RL observation space)

**Library**: `gdadll.dll` (client library available)

### 2. OPC DA Server

**Protocol**: OPC DA (OLE for Process Control - Data Access)
**Library**: `WTOPCsvr.dll`

**Purpose**: Industry-standard protocol for SCADA/DCS integration.

**Capabilities**:
- Standard OPC DA 2.0/3.0 interface
- Tag-based data access
- Subscription model
- Suitable for integration with industrial control systems

### 3. ONC RPC (Low-level)

**Libraries**:
- `oncrpc.dll` - ONC RPC runtime
- Header files in `D:\GPWR\GSES\SimExec\include\RPC\`

**Purpose**: Direct low-level RPC calls to simulation services.

### 4. Remote Functions (JADE)

**Interface**: GUI-based remote functions
**Purpose**: Manual/scripted control through JADE interface
**Files**: `*Remote*.bat` scripts in `D:\GPWR\GSES\JADE\bat\`

---

## Plant Systems Simulated

The GPWR model includes full systems:

### Primary Systems
- **RCS** - Reactor Coolant System
- **PRS** - Pressurizer System
- **RTC** - Reactor Control (rod control)
- **SIS** - Safety Injection System
- **RHR** - Residual Heat Removal
- **CVC** - Chemical & Volume Control

### Secondary Systems
- **SGN** - Steam Generators (multiple)
- **MSS** - Main Steam System
- **CFW** - Condensate & Feedwater
- **TUR** - Turbine System
- **CND** - Condenser
- **GEN** - Generator

### Support Systems
- **CCW** - Component Cooling Water
- **SWS** - Service Water System
- **CWS** - Circulating Water System
- **EPS** - Electrical Power System
- **CNS** - Containment System
- **HVA** - HVAC
- **AIR** - Compressed Air

---

## Simulation Variables

### Variable Database

**Location**: `D:\GPWR\Plant\load\`
**Format**: Binary database with variable definitions

**Variable Types**:
- **Analog** - Continuous values (temperatures, pressures, flows, levels)
- **Digital** - Boolean states (pump status, valve positions)
- **Integer** - Discrete values (rod positions, counts)

**Variable Naming Convention**:
```
<SYSTEM><SUBSYSTEM><COMPONENT><PARAMETER>
```

Examples:
- `RCS01TAVE` - RCS Loop 1 Average Temperature
- `PRS01PZRLVL` - Pressurizer Level
- `SGN01LEVL` - Steam Generator 1 Level
- `TUR01SPEED` - Turbine Speed

### Accessing Variables

Variables are accessed through GDA Server using:
1. **Variable Name** (string identifier)
2. **Variable Index** (integer ID)
3. **Tag Path** (hierarchical path)

---

## Starting the Simulator

### Method 1: GUI Start (for testing)

From Windows Start Menu → GSES → GPWR:
- `1 Start Trainer EnglishUnit All` - Starts everything
- `2 Dashboard` - Opens monitoring dashboard
- `3 Stop Trainer` - Stops all processes

### Method 2: Command Line (for automation)

```cmd
cd D:\GPWR\Plant
call UploadGPWR_EnglishUnit_ALL.cmd
```

**Startup Sequence**:
1. Sets environment (`setenv.cmd`)
2. Starts MST (Main Simulation Task) with plant model
3. Loads initial conditions
4. Starts API servers (GDA, DBA, Dir)
5. Starts alarm server
6. Starts JADE (GUI - optional for headless)

**Startup Time**: ~30 seconds

### Method 3: Headless Start (for RL)

Modify startup script to skip GUI components:
```cmd
@echo off
cd /D D:\GPWR\Plant
call setenv.cmd
cd load
start /B mst.exe -f c.trnnio_EnglishUnit
timeout /t 10
call isd rtexall < loadset_EnglishUnit
cd ..\..\GSES\SimExec\bin\ia32
start /B gdaserver.exe
start /B dbaserver.exe
start /B dirserver.exe
```

---

## RL Integration Strategy

### Observation Space

**Read from GDA Server** (Port 9800):

**Example Variables for Observation**:
```python
observations = {
    # Core Parameters
    'reactor_power': 'RCS01POWER',
    'tavg': 'RCS01TAVE',
    'tcore_out': 'RCS01THOT',
    'tcore_in': 'RCS01TCOLD',

    # Pressurizer
    'pressurizer_pressure': 'PRS01PRESS',
    'pressurizer_level': 'PRS01LEVEL',

    # Steam Generators (x2 or x4)
    'sg1_level': 'SGN01LEVEL',
    'sg1_pressure': 'SGN01PRESS',
    'sg2_level': 'SGN02LEVEL',

    # Turbine
    'turbine_speed': 'TUR01SPEED',
    'generator_power': 'GEN01POWER',

    # Safety Systems
    'si_flow': 'SIS01FLOW',
    'containment_pressure': 'CNS01PRESS',
}
```

### Action Space

**Write to GDA Server**:

**Example Control Actions**:
```python
actions = {
    # Rod Control
    'rod_position_demand': 'RTC01DEMAND',  # Control rods

    # Pressurizer Control
    'pressurizer_heaters': 'PRS01HEATERS',
    'pressurizer_spray': 'PRS01SPRAY',

    # Feedwater Control
    'fw_flow_demand': 'CFW01DEMAND',

    # Turbine Control
    'turbine_throttle': 'TUR01THROTTLE',
    'turbine_governor': 'TUR01GOVERNOR',

    # Pump Controls
    'rcp_speed_1': 'RCS01PUMP1SPD',  # Reactor coolant pump
}
```

### Python Integration Example

```python
import socket
import struct

class GPWRInterface:
    def __init__(self, host='10.1.0.123', port=9800):
        self.host = host
        self.port = port
        self.connected = False

    def connect(self):
        """Connect to GDA server via RPC"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.connected = True

    def read_variable(self, var_name):
        """Read a simulation variable by name"""
        # RPC call to GDA server
        # Implementation requires RPC protocol handling
        pass

    def write_variable(self, var_name, value):
        """Write a value to a simulation variable"""
        # RPC call to GDA server
        pass

    def step(self, dt=1.0):
        """Advance simulation by dt seconds"""
        # Command sim to step forward
        pass

    def reset(self, ic_name='100_percent_power'):
        """Reset to initial condition"""
        # Load specified IC
        pass

# RL Environment Wrapper
class GPWREnv(gym.Env):
    def __init__(self):
        self.sim = GPWRInterface()
        self.sim.connect()

    def reset(self):
        self.sim.reset()
        return self._get_obs()

    def step(self, action):
        self._set_actions(action)
        self.sim.step(dt=1.0)
        obs = self._get_obs()
        reward = self._calculate_reward(obs)
        done = self._check_done(obs)
        return obs, reward, done, {}

    def _get_obs(self):
        return {
            'power': self.sim.read_variable('RCS01POWER'),
            'tavg': self.sim.read_variable('RCS01TAVE'),
            # ... more observations
        }
```

### Required Development

1. **RPC Client Library**
   - Implement ONC RPC protocol in Python
   - Or use existing Python RPC library (rpcgen, sunrpc)
   - Wrap GDA server calls

2. **Variable Mapping**
   - Create comprehensive variable dictionary
   - Map simulation variables to RL obs/action space
   - Handle unit conversions

3. **Synchronization**
   - Handle simulation timestep
   - Synchronize RL agent step with sim step
   - Real-time vs. faster-than-real-time execution

4. **Safety Wrapper**
   - Prevent unsafe actions (e.g., pulling all rods instantly)
   - Add action limits and rate limits
   - Emergency trip conditions

---

## Next Steps

### Immediate Tasks

1. **Start the simulator** and verify GDA server is accessible on port 9800
2. **Capture variable list** from running simulation
3. **Test RPC connection** with simple read/write operations
4. **Build Python RPC client** for GDA protocol
5. **Create RL environment wrapper** with Gym interface

### Tools Needed

- **rpcgen** - RPC stub generator (or Python equivalent)
- **Wireshark** - To capture RPC protocol if needed
- **GDA client example** - If available in GSES documentation

### Documentation to Review

Located on VM at:
- `D:\GPWR\Documentation\Software Manuals\SimExec_User_Guide.pdf`
- `D:\GPWR\Documentation\Software Manuals\jstation.pdf`
- `D:\GPWR\GSES\SimExec\bin\JDBUserGuide\` (HTML docs)

---

## Connection Info

**SSH Access**:
```bash
ssh brad@10.1.0.123
# Password: [your password]
# SSH keys configured
```

**RDP Access** (if GUI needed):
```
xfreerdp /v:10.1.0.123 /u:brad
```

**GDA Server** (when running):
```
Host: 10.1.0.123
Port: 9800
Protocol: TCP/RPC
```

---

## Summary

The GSE GPWR simulator provides enterprise-grade nuclear plant simulation with multiple programmatic interfaces. The **GDA Server on port 9800** is the primary API for RL integration, offering real-time variable read/write capabilities. With proper RPC client implementation, this simulator can serve as a high-fidelity environment for training RL agents on nuclear plant control tasks.

**Status**: Simulator installed, SSH configured, ready for API development and testing.
