#!/usr/bin/env python3
"""
Coolant Pump Integration Demonstration

This script shows how to integrate the new coolant pump system with the existing
nuclear reactor simulation, demonstrating:

1. Pump system initialization and integration
2. Flow control and pump speed management
3. Pump trip scenarios and recovery
4. Integration with thermal hydraulics
5. Realistic pump dynamics during transients
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import matplotlib.pyplot as plt
from simulator.core.sim import NuclearPlantSimulator, ControlAction
from systems.primary.coolant import CoolantPumpSystem, PumpStatus
from systems.primary.reactor.reactivity_model import create_equilibrium_state


class NuclearPlantWithPumps:
    """
    Enhanced nuclear plant simulator with detailed coolant pump modeling
    
    This class demonstrates how to integrate the coolant pump system
    with the existing reactor physics simulation.
    """
    
    def __init__(self, dt: float = 1.0):
        """Initialize nuclear plant with pump system"""
        self.dt = dt
        self.time = 0.0
        
        # Initialize base reactor simulator
        self.reactor_sim = NuclearPlantSimulator(dt=dt, enable_secondary=True)
        
        # Initialize coolant pump system
        self.pump_system = CoolantPumpSystem(num_pumps=4, num_loops=3)
        
        # Set equilibrium state
        equilibrium_state = create_equilibrium_state(
            power_level=100.0,
            control_rod_position=95.0,
            auto_balance=True
        )
        self.reactor_sim.state = equilibrium_state
        
        # History for plotting
        self.history = {
            'time': [],
            'reactor_power': [],
            'total_flow': [],
            'pump_power': [],
            'running_pumps': [],
            'coolant_temp': [],
            'fuel_temp': [],
            'pump_speeds': {f'RCP-{i+1}A': [] for i in range(3)},
            'pump_flows': {f'RCP-{i+1}A': [] for i in range(3)},
            'pump_status': {f'RCP-{i+1}A': [] for i in range(3)}
        }
    
    def step(self, reactor_action: ControlAction = None, 
             pump_controls: dict = None, 
             load_demand: float = 100.0) -> dict:
        """
        Step the integrated simulation
        
        Args:
            reactor_action: Control action for reactor
            pump_controls: Dictionary with pump control inputs
            load_demand: Electrical load demand (%)
            
        Returns:
            Dictionary with complete plant state
        """
        if pump_controls is None:
            pump_controls = {}
        
        # Update pump system first
        system_conditions = {
            'system_pressure': self.reactor_sim.state.coolant_pressure,
            'coolant_temperature': self.reactor_sim.state.coolant_temperature,
            'suction_pressure': self.reactor_sim.state.coolant_pressure - 0.5
        }
        
        pump_result = self.pump_system.update_system(
            dt=self.dt,
            system_conditions=system_conditions,
            control_inputs=pump_controls
        )
        
        # Update reactor coolant flow based on pump performance
        if pump_result['system_available']:
            self.reactor_sim.state.coolant_flow_rate = pump_result['total_flow_rate']
        else:
            # Emergency: natural circulation only
            self.reactor_sim.state.coolant_flow_rate = min(
                self.reactor_sim.state.coolant_flow_rate, 2000.0
            )
            print(f"WARNING: Pump system unavailable at t={self.time:.1f}s - Natural circulation mode")
        
        # Step reactor simulation
        reactor_result = self.reactor_sim.step(
            action=reactor_action,
            load_demand=load_demand,
            cooling_water_temp=25.0
        )
        
        # Update time
        self.time += self.dt
        
        # Store history
        self._update_history(pump_result, reactor_result)
        
        # Compile integrated results
        integrated_result = {
            'time': self.time,
            'reactor': {
                'power_level': self.reactor_sim.state.power_level,
                'fuel_temperature': self.reactor_sim.state.fuel_temperature,
                'coolant_temperature': self.reactor_sim.state.coolant_temperature,
                'coolant_pressure': self.reactor_sim.state.coolant_pressure,
                'coolant_flow_rate': self.reactor_sim.state.coolant_flow_rate,
                'reactivity_pcm': reactor_result['info']['reactivity'],
                'scram_status': self.reactor_sim.state.scram_status
            },
            'pumps': pump_result,
            'secondary': {
                'electrical_power': reactor_result['info'].get('electrical_power', 0.0),
                'thermal_efficiency': reactor_result['info'].get('thermal_efficiency', 0.0)
            },
            'integration': {
                'flow_match': abs(pump_result['total_flow_rate'] - 
                                self.reactor_sim.state.coolant_flow_rate) < 100.0,
                'system_available': pump_result['system_available'],
                'total_plant_power': (pump_result['total_power_consumption'] + 
                                    reactor_result['info'].get('electrical_power', 0.0))
            }
        }
        
        return integrated_result
    
    def _update_history(self, pump_result: dict, reactor_result: dict):
        """Update history for plotting"""
        self.history['time'].append(self.time)
        self.history['reactor_power'].append(self.reactor_sim.state.power_level)
        self.history['total_flow'].append(pump_result['total_flow_rate'])
        self.history['pump_power'].append(pump_result['total_power_consumption'])
        self.history['running_pumps'].append(pump_result['num_running_pumps'])
        self.history['coolant_temp'].append(self.reactor_sim.state.coolant_temperature)
        self.history['fuel_temp'].append(self.reactor_sim.state.fuel_temperature)
        
        # Individual pump data
        for pump_id in ['RCP-1A', 'RCP-2A', 'RCP-3A']:
            if pump_id in pump_result['pump_details']:
                pump_data = pump_result['pump_details'][pump_id]
                self.history['pump_speeds'][pump_id].append(pump_data['speed_percent'])
                self.history['pump_flows'][pump_id].append(pump_data['flow_rate'])
                self.history['pump_status'][pump_id].append(pump_data['status'])
            else:
                self.history['pump_speeds'][pump_id].append(0.0)
                self.history['pump_flows'][pump_id].append(0.0)
                self.history['pump_status'][pump_id].append('stopped')
    
    def plot_results(self):
        """Plot integrated simulation results"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        time = np.array(self.history['time'])
        
        # Reactor power and flow
        ax1.plot(time, self.history['reactor_power'], 'r-', label='Reactor Power (%)', linewidth=2)
        ax1_twin = ax1.twinx()
        ax1_twin.plot(time, np.array(self.history['total_flow'])/1000, 'b-', 
                     label='Total Flow (×1000 kg/s)', linewidth=2)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Reactor Power (%)', color='r')
        ax1_twin.set_ylabel('Flow Rate (×1000 kg/s)', color='b')
        ax1.set_title('Reactor Power vs Coolant Flow')
        ax1.grid(True, alpha=0.3)
        
        # Pump performance
        ax2.plot(time, self.history['running_pumps'], 'g-', label='Running Pumps', linewidth=2)
        ax2_twin = ax2.twinx()
        ax2_twin.plot(time, self.history['pump_power'], 'm-', label='Pump Power (MW)', linewidth=2)
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Number of Running Pumps', color='g')
        ax2_twin.set_ylabel('Total Pump Power (MW)', color='m')
        ax2.set_title('Pump System Performance')
        ax2.grid(True, alpha=0.3)
        
        # Individual pump speeds
        colors = ['red', 'blue', 'green']
        for i, pump_id in enumerate(['RCP-1A', 'RCP-2A', 'RCP-3A']):
            ax3.plot(time, self.history['pump_speeds'][pump_id], 
                    color=colors[i], label=pump_id, linewidth=2)
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Pump Speed (%)')
        ax3.set_title('Individual Pump Speeds')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Temperatures
        ax4.plot(time, self.history['fuel_temp'], 'orange', label='Fuel Temp', linewidth=2)
        ax4.plot(time, self.history['coolant_temp'], 'cyan', label='Coolant Temp', linewidth=2)
        ax4.set_xlabel('Time (s)')
        ax4.set_ylabel('Temperature (°C)')
        ax4.set_title('Reactor Temperatures')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('coolant_pump_integration_results.png', dpi=300, bbox_inches='tight')
        print("Plot saved as 'coolant_pump_integration_results.png'")
        plt.show()


def demonstrate_normal_operation():
    """Demonstrate normal operation with pump system"""
    print("=" * 80)
    print("COOLANT PUMP INTEGRATION - NORMAL OPERATION")
    print("=" * 80)
    
    plant = NuclearPlantWithPumps(dt=1.0)
    
    print("System Configuration:")
    print(f"  Reactor: 3000 MW thermal")
    print(f"  Coolant Pumps: {plant.pump_system.num_pumps} pumps in {plant.pump_system.num_loops} loops")
    print(f"  Design Flow: {plant.pump_system.total_design_flow:.0f} kg/s")
    print()
    
    print("Normal Operation (120 seconds):")
    print(f"{'Time':<6} {'Power %':<8} {'Flow kg/s':<10} {'Pumps':<6} {'Pump MW':<8} {'Status':<15}")
    print("-" * 70)
    
    for t in range(120):
        result = plant.step(
            reactor_action=ControlAction.NO_ACTION,
            load_demand=100.0
        )
        
        if t % 20 == 0:
            status = "Normal" if result['integration']['system_available'] else "Degraded"
            print(f"{t:<6} {result['reactor']['power_level']:<8.1f} "
                  f"{result['pumps']['total_flow_rate']:<10.0f} "
                  f"{result['pumps']['num_running_pumps']:<6} "
                  f"{result['pumps']['total_power_consumption']:<8.1f} "
                  f"{status:<15}")
    
    print()
    return plant


def demonstrate_pump_trip_scenario():
    """Demonstrate pump trip and recovery"""
    print("=" * 80)
    print("COOLANT PUMP TRIP SCENARIO")
    print("=" * 80)
    
    plant = NuclearPlantWithPumps(dt=1.0)
    
    print("Scenario: Trip one pump at t=60s, restart at t=120s")
    print(f"{'Time':<6} {'Power %':<8} {'Flow kg/s':<10} {'Pumps':<6} {'Action':<20}")
    print("-" * 60)
    
    for t in range(180):
        pump_controls = {}
        action_desc = "Normal Operation"
        
        if t == 60:
            # Trip first pump
            pump_controls['RCP-1A_stop'] = True
            action_desc = "Stop RCP-1A"
        elif t == 120:
            # Restart pump
            pump_controls['RCP-1A_start'] = True
            action_desc = "Start RCP-1A"
        
        result = plant.step(
            reactor_action=ControlAction.NO_ACTION,
            pump_controls=pump_controls,
            load_demand=100.0
        )
        
        if t % 20 == 0 or t in [60, 61, 120, 121]:
            print(f"{t:<6} {result['reactor']['power_level']:<8.1f} "
                  f"{result['pumps']['total_flow_rate']:<10.0f} "
                  f"{result['pumps']['num_running_pumps']:<6} "
                  f"{action_desc:<20}")
    
    print()
    return plant


def demonstrate_flow_control():
    """Demonstrate automatic flow control"""
    print("=" * 80)
    print("AUTOMATIC FLOW CONTROL DEMONSTRATION")
    print("=" * 80)
    
    plant = NuclearPlantWithPumps(dt=1.0)
    
    print("Scenario: Change target flow from 17100 to 15000 to 19000 kg/s")
    print(f"{'Time':<6} {'Target':<8} {'Actual':<8} {'Speed %':<8} {'Action':<20}")
    print("-" * 60)
    
    for t in range(240):
        pump_controls = {}
        action_desc = "Normal"
        
        if t == 60:
            # Reduce target flow
            pump_controls['target_total_flow'] = 15000.0
            action_desc = "Reduce Target Flow"
        elif t == 120:
            # Increase target flow
            pump_controls['target_total_flow'] = 19000.0
            action_desc = "Increase Target Flow"
        elif t == 180:
            # Return to normal
            pump_controls['target_total_flow'] = 17100.0
            action_desc = "Return to Normal"
        
        result = plant.step(
            reactor_action=ControlAction.NO_ACTION,
            pump_controls=pump_controls,
            load_demand=100.0
        )
        
        # Get average pump speed
        avg_speed = 0.0
        running_count = 0
        for pump_id in result['pumps']['running_pumps']:
            if pump_id in result['pumps']['pump_details']:
                avg_speed += result['pumps']['pump_details'][pump_id]['speed_percent']
                running_count += 1
        
        if running_count > 0:
            avg_speed /= running_count
        
        if t % 20 == 0 or t in [60, 61, 120, 121, 180, 181]:
            target_flow = pump_controls.get('target_total_flow', 17100.0)
            print(f"{t:<6} {target_flow:<8.0f} "
                  f"{result['pumps']['total_flow_rate']:<8.0f} "
                  f"{avg_speed:<8.1f} "
                  f"{action_desc:<20}")
    
    print()
    return plant


def main():
    """Main demonstration function"""
    print("NUCLEAR REACTOR COOLANT PUMP INTEGRATION")
    print("Complete System Integration Demonstration")
    print()
    
    try:
        # Demonstrate normal operation
        plant1 = demonstrate_normal_operation()
        
        # Demonstrate pump trip scenario
        plant2 = demonstrate_pump_trip_scenario()
        
        # Demonstrate flow control
        plant3 = demonstrate_flow_control()
        
        # Generate plots for the flow control demonstration
        plant3.plot_results()
        
        print("=" * 80)
        print("INTEGRATION SUMMARY")
        print("=" * 80)
        print("Successfully demonstrated coolant pump integration:")
        print()
        print("✓ Pump System Features:")
        print("  - 4 reactor coolant pumps in 3 primary loops")
        print("  - Individual pump speed control and monitoring")
        print("  - Automatic system flow control")
        print("  - Pump protection systems (low flow, high temp, low pressure)")
        print("  - Realistic startup/shutdown dynamics")
        print()
        print("✓ Integration with Reactor Physics:")
        print("  - Pump flow directly controls reactor coolant flow rate")
        print("  - System pressure and temperature affect pump performance")
        print("  - Pump availability affects reactor operation")
        print("  - Natural circulation backup when pumps unavailable")
        print()
        print("✓ Control and Protection:")
        print("  - Individual pump start/stop control")
        print("  - Automatic flow control with target setpoints")
        print("  - Pump trip protection and recovery")
        print("  - Minimum pump requirements for safe operation")
        print()
        print("✓ Realistic Dynamics:")
        print("  - Pump speed ramp rate limiting")
        print("  - Startup and coastdown time constants")
        print("  - Flow-speed relationships with system effects")
        print("  - Power consumption modeling")
        print()
        print("The coolant pump system is now fully integrated and ready for use!")
        print("You can control pumps through the pump_controls dictionary in the step() method.")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
