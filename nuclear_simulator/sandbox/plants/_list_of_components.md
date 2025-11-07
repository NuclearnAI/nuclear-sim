# Physical Reactor Components for Graph-Based Simulation

This document lists all physical reactor components identified from the old codebase that need to be translated to the new graph-like simulation engine.

**Analysis Date:** 2025-10-28  
**Source Directory:** `nuclear_simulator/systems/`  
**Purpose:** Identify physical hardware components (excluding abstract classes, control logic, and physics models)

---

## Primary System Components

### Reactor Coolant Pumps
**File:** [`nuclear_simulator/systems/primary/coolant/pump_models.py`](../../../systems/primary/coolant/pump_models.py)

1. **BasePump**
   - Base class providing common pump functionality for all nuclear plant pumps
   - Implements speed control, protection systems, standard pump dynamics
   - Foundation for consistent pump behavior across primary and secondary systems

2. **ReactorCoolantPump** 
   - Individual reactor coolant pump for PWR primary loops
   - Features: Flow rate control, startup/shutdown dynamics, protection systems
   - Rated flow: 5,700 kg/s per pump, Rated power: 6.5 MW

3. **CoolantPumpSystem**
   - Complete coolant pump system managing multiple RCPs (typically 4 pumps for PWR)
   - Features: Total system flow control, pump sequencing, N-1 redundancy
   - Design flow: 17,100 kg/s total, Minimum pumps required: 2

---

## Secondary System Components

### A. Condenser System

**File:** [`nuclear_simulator/systems/secondary/condenser/vacuum_pump.py`](../../../systems/secondary/condenser/vacuum_pump.py)

4. **SteamJetEjector**
   - Steam jet ejector for condenser vacuum service
   - Uses high-pressure motive steam to create vacuum
   - Features: Two-stage compression, nozzle/diffuser fouling tracking, erosion modeling
   - Design capacity: 25 kg/s air removal per ejector

**File:** [`nuclear_simulator/systems/secondary/condenser/vacuum_system.py`](../../../systems/secondary/condenser/vacuum_system.py)

5. **VacuumSystem**
   - Complete vacuum system coordinating multiple steam jet ejectors
   - Features: Air mass balance, automatic ejector start/stop, lead/lag rotation
   - Maintains condenser vacuum at ~0.007 MPa (7 kPa absolute)

**File:** [`nuclear_simulator/systems/secondary/condenser/physics.py`](../../../systems/secondary/condenser/physics.py)

6. **EnhancedCondenserPhysics**
   - Main condenser heat exchanger with tube bundle
   - Features: Heat transfer, tube degradation tracking, fouling models, cooling water chemistry effects
   - Design: ~27,000 tubes, 6,000+ m² heat transfer area
   - Heat rejection: ~2,000 MW thermal

### B. Feedwater System

**File:** [`nuclear_simulator/systems/secondary/feedwater/pump_system.py`](../../../systems/secondary/feedwater/pump_system.py)

7. **FeedwaterPump**
   - Individual feedwater pump for steam generator injection
   - Features: High head operation (1,200m), variable speed control, NPSH protection, cavitation modeling
   - Rated flow: 555 kg/s per pump, Rated power: 10 MW

8. **FeedwaterPumpSystem**
   - Complete feedwater pump system (typically 3-4 pumps for 3 SGs + 1 spare)
   - Features: Multi-pump coordination, load distribution, automatic sequencing
   - Total design flow: 1,665 kg/s (for 3 steam generators)

**File:** [`nuclear_simulator/systems/secondary/feedwater/pump_lubrication.py`](../../../systems/secondary/feedwater/pump_lubrication.py)

9. **FeedwaterPumpLubricationSystem**
   - Comprehensive lubrication system for feedwater pump components
   - Manages: Motor bearings, pump bearings, thrust bearings, mechanical seals, coupling
   - Features: Oil quality tracking, wear modeling, seal leakage monitoring
   - Oil reservoir: 150 liters per pump

**File:** [`nuclear_simulator/systems/secondary/feedwater/physics.py`](../../../systems/secondary/feedwater/physics.py)

10. **EnhancedFeedwaterPhysics**
    - Complete enhanced feedwater system orchestrator
    - Integrates: Pump system, level control, water chemistry, diagnostics, protection
    - Manages overall feedwater system operation and coordination

### C. Steam Generator System

**File:** [`nuclear_simulator/systems/secondary/steam_generator/steam_generator.py`](../../../systems/secondary/steam_generator/steam_generator.py)

11. **SteamGenerator**
    - Individual U-tube steam generator for PWR
    - Features: Primary-to-secondary heat transfer, two-phase flow, water level dynamics, TSP fouling tracking
    - Design: 5,100 m² heat transfer area, 10,000+ tubes per SG
    - Thermal power: ~1,085 MW per SG
    - Steam production: 555 kg/s per SG at 6.895 MPa

**File:** [`nuclear_simulator/systems/secondary/steam_generator/enhanced_physics.py`](../../../systems/secondary/steam_generator/enhanced_physics.py)

12. **EnhancedSteamGeneratorPhysics**
    - Enhanced SG system orchestrating multiple steam generators (typically 3 SGs)
    - Features: Load balancing, performance optimization, system coordination
    - Total thermal power: ~3,255 MW, Total steam flow: 1,665 kg/s

### D. Turbine System

**File:** [`nuclear_simulator/systems/secondary/turbine/stage_system.py`](../../../systems/secondary/turbine/stage_system.py)

13. **TurbineStage**
    - Individual turbine stage (impulse or reaction type)
    - Features: Steam expansion, blade performance, extraction flows, efficiency tracking
    - Typical PWR has 8 HP stages + 6 LP stages = 14 total stages

14. **TurbineStageSystem**
    - Multi-stage turbine system coordinating all stages
    - Features: Stage-by-stage expansion, extraction management, performance optimization
    - Total stages: 14 (8 HP + 6 LP), Multiple extraction points for feedwater heating

**File:** [`nuclear_simulator/systems/secondary/turbine/governor_system.py`](../../../systems/secondary/turbine/governor_system.py)

15. **TurbineGovernorSystem**
    - Complete turbine governor with control valves and hydraulics
    - Features: PID speed/load control, valve positioning, protection systems
    - Includes integrated lubrication system for governor components

16. **GovernorValveModel**
    - Governor control valve (steam admission valve)
    - Features: Hydraulic actuator dynamics, steam flow control, wear tracking
    - Valve characteristics: Response time, deadband, hysteresis

17. **GovernorLubricationSystem**
    - Lubrication system for governor components
    - Manages: Valve actuators, speed sensors, control linkages, servo valves, pilot valves
    - Hydraulic system pressure: 3.5 MPa

**File:** [`nuclear_simulator/systems/secondary/turbine/rotor_dynamics.py`](../../../systems/secondary/turbine/rotor_dynamics.py)

18. **RotorDynamicsModel**
    - Turbine rotor and shaft assembly
    - Features: Speed dynamics, thermal expansion, thermal bow, rotational mechanics
    - Rotor mass: 15,000 kg, Operating speed: 3,600 RPM

19. **BearingModel**
    - Individual turbine bearing (journal or thrust type)
    - Features: Load calculations, temperature monitoring, oil film analysis, wear tracking
    - Types: HP journal, LP journal, thrust bearings
    - Typical system has 4 bearings total

**File:** [`nuclear_simulator/systems/secondary/turbine/turbine_bearing_lubrication.py`](../../../systems/secondary/turbine/turbine_bearing_lubrication.py)

20. **TurbineBearingLubricationSystem**
    - Comprehensive lubrication for all turbine bearings
    - Manages: HP journal bearing, LP journal bearing, thrust bearing, seal oil system, oil coolers
    - Oil reservoir: 800 liters, High-temperature operation (45-95°C)

**File:** [`nuclear_simulator/systems/secondary/turbine/enhanced_physics.py`](../../../systems/secondary/turbine/enhanced_physics.py)

21. **EnhancedTurbinePhysics**
    - Complete enhanced turbine system orchestrator
    - Integrates: Stage system, rotor dynamics, governor, bearings, lubrication, protection
    - Rated power: ~1,100 MW electrical, Overall efficiency: ~34%

---

## Safety System Components

**Note:** The `nuclear_simulator/systems/safety/` directory is currently empty. No physical safety components were found in the analyzed files. Safety logic exists in [`scram_logic.py`](../../../systems/primary/reactor/safety/scram_logic.py) but is control logic, not physical hardware.

---

## Maintenance System Components

**Note:** The maintenance system (in [`nuclear_simulator/systems/maintenance/`](../../../systems/maintenance/)) contains control and orchestration logic rather than physical components. It manages maintenance of the physical components listed above but does not itself represent physical hardware.

---

## Component Summary

### By System:
- **Primary System:** 3 physical components
- **Secondary - Condenser:** 3 physical components  
- **Secondary - Feedwater:** 4 physical components
- **Secondary - Steam Generator:** 2 physical components
- **Secondary - Turbine:** 9 physical components
- **Safety System:** 0 physical components (directory empty)
- **Maintenance:** 0 physical components (orchestration only)

### Total Physical Components Identified: **21**

### Component Categories:
1. **Pumps and Pump Systems:** 6 components
   - Reactor coolant pumps (3)
   - Feedwater pumps and system (2)
   - Steam jet ejectors (1)

2. **Heat Exchangers:** 3 components
   - Condenser (1)
   - Steam generators (2)

3. **Turbine and Mechanical:** 6 components
   - Turbine stages and system (2)
   - Rotor assembly (1)
   - Bearings (1)
   - Governor and valves (2)

4. **Support Systems:** 6 components
   - Lubrication systems (4)
   - Vacuum system (1)
   - Enhanced system orchestrators (1)

---

## Component Details and Relationships

### Key Physical Component Hierarchies:

#### 1. Pump Hierarchy
```
BasePump (base class)
├── ReactorCoolantPump (primary coolant circulation)
└── FeedwaterPump (feedwater injection)
```

#### 2. Turbine Hierarchy
```
EnhancedTurbinePhysics (system orchestrator)
├── TurbineStageSystem
│   └── TurbineStage (×14 stages: 8 HP + 6 LP)
├── RotorDynamicsModel
│   └── BearingModel (×4 bearings)
├── TurbineGovernorSystem
│   ├── GovernorValveModel
│   └── GovernorLubricationSystem
└── TurbineBearingLubricationSystem
```

#### 3. Steam Generator Hierarchy
```
EnhancedSteamGeneratorPhysics (system orchestrator)
└── SteamGenerator (×3 units in typical PWR)
```

#### 4. Condenser Hierarchy
```
EnhancedCondenserPhysics (main condenser)
└── VacuumSystem
    └── SteamJetEjector (×2 typical, lead/lag operation)
```

#### 5. Feedwater Hierarchy
```
EnhancedFeedwaterPhysics (system orchestrator)
├── FeedwaterPumpSystem
│   ├── FeedwaterPump (×4: 3 operating + 1 spare)
│   └── FeedwaterPumpLubricationSystem (per pump)
└── ThreeElementControl (control logic - not physical)
```

---

## Critical Physical Interactions

### Primary-to-Secondary Heat Transfer:
- **ReactorCoolantPump** → circulates hot primary coolant
- **SteamGenerator** → transfers heat from primary to secondary
- Tube bundle is the physical interface

### Secondary Side Flow Path:
- **FeedwaterPump** → pressurizes feedwater
- **SteamGenerator** → converts feedwater to steam  
- **TurbineStage** (×14) → expands steam, extracts work
- **Condenser** → condenses exhaust steam
- **VacuumSystem** → maintains vacuum
- Back to feedwater pump (cycle complete)

### Support Systems:
- **Lubrication Systems** (3 types) → support all rotating equipment
- **Governor** → controls turbine steam admission
- **Bearings** → support rotating shafts
- **Vacuum System** → enables efficient turbine operation

---

## Translation Priority for New Engine

### High Priority (Core Power Cycle):
1. SteamGenerator - Primary heat transfer component
2. TurbineStage - Primary work extraction component
3. Condenser - Heat rejection component
4. FeedwaterPump - Circulation component
5. ReactorCoolantPump - Primary circulation component

### Medium Priority (Control & Efficiency):
6. TurbineGovernorSystem - Steam flow control
7. VacuumSystem - Condenser performance
8. FeedwaterPumpSystem - System coordination
9. TurbineStageSystem - Multi-stage coordination

### Lower Priority (Detailed Modeling):
10. Bearing systems - Mechanical support
11. Lubrication systems - Equipment protection
12. Rotor dynamics - Detailed mechanical behavior
13. Protection systems - Safety logic (not physical hardware)

---

## Notes for Graph Engine Translation

### Component Node Types:
- **Heat Exchangers:** Condenser, SteamGenerator
- **Work Devices:** TurbineStage, Pumps (all types)
- **Flow Control:** GovernorValve, control valves
- **Support Equipment:** Bearings, Lubrication systems, VacuumSystem
- **System Orchestrators:** Enhanced physics classes (may become graph controllers)

### Physical Connections:
- Fluid connections: Steam, water, condensate flows
- Mechanical connections: Shaft couplings, bearing supports
- Thermal connections: Heat transfer interfaces
- Control connections: Sensor feedback, actuator commands

### State Variables to Track:
- **Thermodynamic:** Pressure, temperature, flow rate, enthalpy, quality
- **Mechanical:** Speed, torque, vibration, wear, alignment
- **Performance:** Efficiency, power, degradation factors
- **Operational:** Status (running/stopped), trip conditions, availability

---

## Files NOT Containing Physical Components

The following files were examined but contain only abstract models, control logic, or helper classes:

- [`scram_logic.py`](../../../systems/primary/reactor/safety/scram_logic.py) - SCRAM control logic (not physical)
- [`component_descriptions.py`](../../../systems/primary/component_descriptions.py) - Metadata only
- [`level_control.py`](../../../systems/secondary/feedwater/level_control.py) - Control algorithms
- [`protection_system.py`](../../../systems/secondary/feedwater/protection_system.py) - Protection logic
- [`performance_monitoring.py`](../../../systems/secondary/feedwater/performance_monitoring.py) - Diagnostics (not examined in detail)
- Physics model files (neutronics, thermal hydraulics, etc.) - Mathematical models, not hardware

---

## Summary

**Total Physical Components Identified: 21**

These components represent the actual physical hardware in a PWR nuclear power plant that must be modeled in the new graph-based simulation engine. Each component has well-defined physical characteristics, operating parameters, and interactions with other components that can be represented as nodes and edges in a graph structure.

The analysis excluded:
- Abstract base classes used only for code organization
- Control logic and protection systems (software, not hardware)
- Physics models and calculation engines
- Data structures and interfaces
- Helper classes and utilities

## List of Nodes

- BasePump
- ReactorCoolantPump
- CoolantPumpSystem
- SteamJetEjector
- VacuumSystem
- EnhancedCondenserPhysics
- FeedwaterPump
- FeedwaterPumpSystem
- FeedwaterPumpLubricationSystem
- EnhancedFeedwaterPhysics
- SteamGenerator
- EnhancedSteamGeneratorPhysics
- TurbineStage
- TurbineStageSystem
- TurbineGovernorSystem
- GovernorValveModel
- GovernorLubricationSystem
- RotorDynamicsModel
- BearingModel
- TurbineBearingLubricationSystem
- EnhancedTurbinePhysics
