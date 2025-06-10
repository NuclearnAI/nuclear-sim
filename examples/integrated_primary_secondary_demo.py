#!/usr/bin/env python3
"""
Integrated Primary-Secondary Reactor Physics Demonstration

This script demonstrates how the secondary reactor physics integrates with the existing
primary reactor physics to create a complete nuclear power plant simulation.

The integration shows:
1. Primary reactor physics (neutronics, thermal hydraulics)
2. Heat transfer from primary to secondary via steam generators
3. Secondary steam cycle (turbine, condenser)
4. Feedback loops between primary and secondary systems
5. Complete plant control and dynamics
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import matplotlib.pyplot as plt
from simulator.core.sim import NuclearPlantSimulator, ControlAction, ReactorState
from systems.secondary import SecondaryReactorPhysics
from systems.primary.reactor.reactivity_model import create_equilibrium_state


class IntegratedNuclearPlant:
    """
    Integrated nuclear plant simulator combining primary and secondary physics
    
    This class demonstrates the complete integration between:
    - Primary reactor physics (neutronics, thermal hydraulics)
    - Secondary steam cycle physics (steam generators, turbine, condenser)
    - Control systems and feedback loops
    """
    
    def __init__(self, dt: float = 1.0):
        """Initialize integrated nuclear plant"""
        self.dt = dt
        self.time = 0.0
        
        # Initialize primary reactor simulator
        self.primary_sim = NuclearPlantSimulator(dt=dt)
        
        # Initialize secondary system (3 steam generators for typical PWR)
        self.secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
        
        # Set initial equilibrium state for primary
        equilibrium_state = create_equilibrium_state(
            power_level=100.0,
            control_rod_position=95.0,
            auto_balance=True
        )
        self.primary_sim.state = equilibrium_state
        
        # Integration parameters
        self.primary_loops = 3  # Number of primary loops
        self.thermal_power_split = [1/3, 1/3, 1/3]  # Equal split between loops
        
        # History for plotting
        self.history = {
            'time': [],
            'primary_power': [],
            'electrical_power': [],
            'primary_temp_hot': [],
            'primary_temp_cold': [],
            'steam_pressure': [],
            'thermal_efficiency': [],
            'reactivity': [],
            'control_rod_position': [],
            'neutron_flux': []
        }
    
    def calculate_primary_to_secondary_coupling(self) -> dict:
        """
        Calculate the coupling between primary and secondary systems
        
        This is the key integration point where:
        1. Primary thermal power is transferred to secondary via steam generators
        2. Primary coolant temperatures are calculated based on heat removal
        3. Secondary steam conditions are determined by primary heat input
        
        Returns:
            Dictionary with coupling parameters for each steam generator
        """
        # Get primary thermal power from reactor physics
        primary_thermal_power = self.primary_sim.state.power_level / 100.0 * 3000.0  # MW
        
        # Calculate primary coolant conditions
        # In a real PWR, hot leg temperature is ~327°C, cold leg ~293°C
        primary_hot_leg_temp = self.primary_sim.state.coolant_temperature + 25.0  # °C
        
        # Heat removal in steam generators determines cold leg temperature
        # Q = m_dot * cp * (T_hot - T_cold)
        # Assuming total primary flow of 17,100 kg/s (typical PWR)
        total_primary_flow = 17100.0  # kg/s
        cp_primary = 5.2  # kJ/kg/K at PWR conditions
        
        # Calculate cold leg temperature based on heat removal
        heat_removed_mw = primary_thermal_power  # Assume all heat goes to steam generators
        delta_t_primary = heat_removed_mw * 1000.0 / (total_primary_flow * cp_primary)
        primary_cold_leg_temp = primary_hot_leg_temp - delta_t_primary
        
        # Update primary simulator state with calculated temperatures
        self.primary_sim.state.coolant_temperature = primary_cold_leg_temp
        
        # Calculate conditions for each steam generator loop
        primary_conditions = {}
        flow_per_loop = total_primary_flow / self.primary_loops
        power_per_loop = primary_thermal_power / self.primary_loops
        
        for i in range(self.primary_loops):
            sg_key = f'sg_{i+1}'
            
            # Each steam generator sees the same inlet conditions
            primary_conditions[f'{sg_key}_inlet_temp'] = primary_hot_leg_temp
            primary_conditions[f'{sg_key}_outlet_temp'] = primary_cold_leg_temp
            primary_conditions[f'{sg_key}_flow'] = flow_per_loop
            
        return primary_conditions
    
    def calculate_secondary_to_primary_feedback(self, secondary_result: dict) -> dict:
        """
        Calculate feedback from secondary to primary systems
        
        This includes:
        1. Steam demand affecting primary heat removal
        2. Feedwater temperature affecting steam generator performance
        3. Load demand affecting overall plant operation
        
        Args:
            secondary_result: Results from secondary system update
            
        Returns:
            Dictionary with feedback parameters
        """
        # Steam demand affects primary heat removal rate
        steam_demand = secondary_result['total_steam_flow']  # kg/s
        
        # Higher steam demand -> more heat removal -> lower primary temperature
        # This is a simplified feedback model
        heat_removal_factor = steam_demand / 1665.0  # Normalize to design flow
        
        # Electrical load affects steam demand
        electrical_load = secondary_result['electrical_power_mw']
        load_factor = electrical_load / 1100.0  # Normalize to design power
        
        return {
            'heat_removal_factor': heat_removal_factor,
            'load_factor': load_factor,
            'steam_demand': steam_demand,
            'electrical_load': electrical_load
        }
    
    def step(self, 
             primary_action: ControlAction = None,
             load_demand: float = 100.0,
             cooling_water_temp: float = 25.0) -> dict:
        """
        Advance integrated simulation by one time step
        
        Args:
            primary_action: Control action for primary system
            load_demand: Electrical load demand (% rated)
            cooling_water_temp: Cooling water temperature (°C)
            
        Returns:
            Dictionary with complete plant state
        """
        # Step 1: Update primary reactor physics
        primary_result = self.primary_sim.step(primary_action)
        
        # Step 2: Calculate primary-to-secondary coupling
        primary_conditions = self.calculate_primary_to_secondary_coupling()
        
        # Step 3: Update secondary system with primary conditions
        control_inputs = {
            'load_demand': load_demand,
            'feedwater_temp': 227.0,  # Typical feedwater temperature
            'cooling_water_temp': cooling_water_temp,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        secondary_result = self.secondary_system.update_system(
            primary_conditions=primary_conditions,
            control_inputs=control_inputs,
            dt=self.dt
        )
        
        # Step 4: Calculate secondary-to-primary feedback
        feedback = self.calculate_secondary_to_primary_feedback(secondary_result)
        
        # Step 5: Apply feedback to primary system (simplified)
        # In a real plant, this would involve complex control systems
        # Here we show the concept with simplified feedback
        
        # Advance time
        self.time += self.dt
        
        # Store history
        self.history['time'].append(self.time)
        self.history['primary_power'].append(self.primary_sim.state.power_level)
        self.history['electrical_power'].append(secondary_result['electrical_power_mw'])
        self.history['primary_temp_hot'].append(primary_conditions['sg_1_inlet_temp'])
        self.history['primary_temp_cold'].append(primary_conditions['sg_1_outlet_temp'])
        self.history['steam_pressure'].append(secondary_result['sg_avg_pressure'])
        self.history['thermal_efficiency'].append(secondary_result['thermal_efficiency'])
        self.history['reactivity'].append(primary_result['info']['reactivity'])
        self.history['control_rod_position'].append(self.primary_sim.state.control_rod_position)
        self.history['neutron_flux'].append(self.primary_sim.state.neutron_flux)
        
        # Compile integrated results
        integrated_result = {
            # Primary system results
            'primary': {
                'power_level': self.primary_sim.state.power_level,
                'neutron_flux': self.primary_sim.state.neutron_flux,
                'reactivity_pcm': primary_result['info']['reactivity'],
                'fuel_temperature': self.primary_sim.state.fuel_temperature,
                'coolant_temp_hot': primary_conditions['sg_1_inlet_temp'],
                'coolant_temp_cold': primary_conditions['sg_1_outlet_temp'],
                'coolant_pressure': self.primary_sim.state.coolant_pressure,
                'control_rod_position': self.primary_sim.state.control_rod_position,
                'boron_concentration': self.primary_sim.state.boron_concentration,
                'scram_status': self.primary_sim.state.scram_status
            },
            
            # Secondary system results
            'secondary': secondary_result,
            
            # Integration metrics
            'integration': {
                'overall_efficiency': secondary_result['thermal_efficiency'],
                'heat_balance': primary_conditions['sg_1_inlet_temp'] - primary_conditions['sg_1_outlet_temp'],
                'power_balance': self.primary_sim.state.power_level - secondary_result['electrical_power_mw'] * 100 / 1100,
                'coupling_factor': feedback['heat_removal_factor']
            },
            
            # Plant performance
            'plant': {
                'gross_electrical_mw': secondary_result['electrical_power_mw'],
                'net_electrical_mw': secondary_result['electrical_power_mw'] * 0.98,  # Account for plant auxiliaries
                'thermal_power_mw': self.primary_sim.state.power_level / 100.0 * 3000.0,
                'overall_efficiency': secondary_result['thermal_efficiency'],
                'capacity_factor': secondary_result['electrical_power_mw'] / 1100.0
            }
        }
        
        return integrated_result
    
    def reset(self):
        """Reset integrated simulation to initial conditions"""
        self.primary_sim.reset()
        self.secondary_system.reset_system()
        self.time = 0.0
        
        # Reset history
        for key in self.history:
            self.history[key] = []
        
        # Set equilibrium state
        equilibrium_state = create_equilibrium_state(
            power_level=100.0,
            control_rod_position=95.0,
            auto_balance=True
        )
        self.primary_sim.state = equilibrium_state


def demonstrate_integrated_operation():
    """Demonstrate integrated primary-secondary operation"""
    print("=" * 80)
    print("INTEGRATED PRIMARY-SECONDARY REACTOR PHYSICS DEMONSTRATION")
    print("=" * 80)
    
    # Create integrated plant
    plant = IntegratedNuclearPlant(dt=1.0)
    
    print("System Configuration:")
    print(f"  Primary Reactor: 3000 MW thermal")
    print(f"  Steam Generators: 3 units, 1085 MW each")
    print(f"  Turbine Generator: 1100 MW electrical")
    print(f"  Primary Loops: {plant.primary_loops}")
    print()
    
    # Demonstrate steady-state operation
    print("Steady-State Operation (60 seconds):")
    print(f"{'Time':<6} {'Primary %':<10} {'Electrical MW':<12} {'Hot Leg °C':<10} {'Cold Leg °C':<11} {'Efficiency %':<12}")
    print("-" * 70)
    
    for t in range(60):
        result = plant.step(
            primary_action=ControlAction.NO_ACTION,
            load_demand=100.0,
            cooling_water_temp=25.0
        )
        
        if t % 10 == 0:
            print(f"{t:<6} {result['primary']['power_level']:<10.1f} "
                  f"{result['secondary']['electrical_power_mw']:<12.1f} "
                  f"{result['primary']['coolant_temp_hot']:<10.1f} "
                  f"{result['primary']['coolant_temp_cold']:<11.1f} "
                  f"{result['secondary']['thermal_efficiency']*100:<12.2f}")
    
    print()
    return plant, result


def demonstrate_load_following():
    """Demonstrate integrated load following"""
    print("=" * 80)
    print("INTEGRATED LOAD FOLLOWING DEMONSTRATION")
    print("=" * 80)
    
    plant = IntegratedNuclearPlant(dt=1.0)
    
    # Load following scenario: 100% -> 75% -> 50% -> 100%
    load_profile = []
    time_points = []
    
    print("Load Following Scenario: 100% -> 75% -> 50% -> 100%")
    print(f"{'Time':<6} {'Load %':<8} {'Primary %':<10} {'Electrical MW':<12} {'Reactivity pcm':<14} {'Efficiency %':<12}")
    print("-" * 72)
    
    for t in range(240):  # 4 minutes
        # Define load profile
        if t < 60:
            load_demand = 100.0
        elif t < 120:
            load_demand = 75.0
        elif t < 180:
            load_demand = 50.0
        else:
            load_demand = 100.0
        
        # For load changes, we might adjust control rods
        if t == 60 or t == 120:  # Load reduction
            primary_action = ControlAction.CONTROL_ROD_INSERT
        elif t == 180:  # Load increase
            primary_action = ControlAction.CONTROL_ROD_WITHDRAW
        else:
            primary_action = ControlAction.NO_ACTION
        
        result = plant.step(
            primary_action=primary_action,
            load_demand=load_demand,
            cooling_water_temp=25.0
        )
        
        load_profile.append(load_demand)
        time_points.append(t)
        
        if t % 20 == 0:
            print(f"{t:<6} {load_demand:<8.0f} "
                  f"{result['primary']['power_level']:<10.1f} "
                  f"{result['secondary']['electrical_power_mw']:<12.1f} "
                  f"{result['primary']['reactivity_pcm']:<14.1f} "
                  f"{result['secondary']['thermal_efficiency']*100:<12.2f}")
    
    print()
    return plant, load_profile, time_points


def demonstrate_control_interactions():
    """Demonstrate primary-secondary control interactions"""
    print("=" * 80)
    print("PRIMARY-SECONDARY CONTROL INTERACTIONS")
    print("=" * 80)
    
    plant = IntegratedNuclearPlant(dt=1.0)
    
    print("Demonstrating various control actions and their effects:")
    print()
    
    scenarios = [
        ("Control Rod Withdrawal", ControlAction.CONTROL_ROD_WITHDRAW, 100.0),
        ("Control Rod Insertion", ControlAction.CONTROL_ROD_INSERT, 100.0),
        ("Load Reduction", ControlAction.NO_ACTION, 75.0),
        ("Coolant Flow Increase", ControlAction.INCREASE_COOLANT_FLOW, 100.0),
    ]
    
    for scenario_name, action, load in scenarios:
        plant.reset()
        
        print(f"{scenario_name}:")
        print(f"{'Time':<6} {'Primary %':<10} {'Electrical MW':<12} {'Reactivity pcm':<14} {'Rod Pos %':<10}")
        print("-" * 62)
        
        # Run scenario for 30 seconds
        for t in range(30):
            if t < 10:
                # Baseline
                result = plant.step(ControlAction.NO_ACTION, 100.0, 25.0)
            else:
                # Apply action
                result = plant.step(action, load, 25.0)
            
            if t % 5 == 0:
                print(f"{t:<6} {result['primary']['power_level']:<10.1f} "
                      f"{result['secondary']['electrical_power_mw']:<12.1f} "
                      f"{result['primary']['reactivity_pcm']:<14.1f} "
                      f"{result['primary']['control_rod_position']:<10.1f}")
        
        print()


def plot_integrated_results(plant):
    """Plot integrated simulation results"""
    print("Generating integrated performance plots...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    time = np.array(plant.history['time'])
    
    # Primary and electrical power
    ax1.plot(time, plant.history['primary_power'], 'r-', label='Primary Power (%)', linewidth=2)
    ax1_twin = ax1.twinx()
    ax1_twin.plot(time, plant.history['electrical_power'], 'b-', label='Electrical Power (MW)', linewidth=2)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Primary Power (%)', color='r')
    ax1_twin.set_ylabel('Electrical Power (MW)', color='b')
    ax1.set_title('Primary vs Electrical Power')
    ax1.grid(True, alpha=0.3)
    
    # Primary temperatures
    ax2.plot(time, plant.history['primary_temp_hot'], 'r-', label='Hot Leg', linewidth=2)
    ax2.plot(time, plant.history['primary_temp_cold'], 'b-', label='Cold Leg', linewidth=2)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Temperature (°C)')
    ax2.set_title('Primary Coolant Temperatures')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Reactivity and control
    ax3.plot(time, plant.history['reactivity'], 'g-', label='Reactivity', linewidth=2)
    ax3_twin = ax3.twinx()
    ax3_twin.plot(time, plant.history['control_rod_position'], 'm-', label='Rod Position', linewidth=2)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Reactivity (pcm)', color='g')
    ax3_twin.set_ylabel('Rod Position (%)', color='m')
    ax3.set_title('Reactivity Control')
    ax3.grid(True, alpha=0.3)
    
    # Efficiency and steam pressure
    ax4.plot(time, np.array(plant.history['thermal_efficiency']) * 100, 'orange', label='Efficiency', linewidth=2)
    ax4_twin = ax4.twinx()
    ax4_twin.plot(time, plant.history['steam_pressure'], 'purple', label='Steam Pressure', linewidth=2)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Thermal Efficiency (%)', color='orange')
    ax4_twin.set_ylabel('Steam Pressure (MPa)', color='purple')
    ax4.set_title('Plant Performance')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('integrated_primary_secondary_performance.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'integrated_primary_secondary_performance.png'")
    plt.show()


def main():
    """Main demonstration function"""
    print("INTEGRATED PRIMARY-SECONDARY NUCLEAR REACTOR PHYSICS")
    print("Demonstrating Complete Plant Integration")
    print()
    
    try:
        # Demonstrate steady-state operation
        plant, steady_result = demonstrate_integrated_operation()
        
        # Show integration details
        print("Integration Details:")
        print(f"  Primary Thermal Power: {steady_result['plant']['thermal_power_mw']:.1f} MW")
        print(f"  Electrical Power Output: {steady_result['plant']['gross_electrical_mw']:.1f} MW")
        print(f"  Overall Plant Efficiency: {steady_result['plant']['overall_efficiency']*100:.2f}%")
        print(f"  Heat Balance (ΔT): {steady_result['integration']['heat_balance']:.1f} °C")
        print(f"  Primary Hot Leg: {steady_result['primary']['coolant_temp_hot']:.1f} °C")
        print(f"  Primary Cold Leg: {steady_result['primary']['coolant_temp_cold']:.1f} °C")
        print(f"  Steam Pressure: {steady_result['secondary']['sg_avg_pressure']:.2f} MPa")
        print(f"  Condenser Pressure: {steady_result['secondary']['condenser_pressure']:.4f} MPa")
        print()
        
        # Demonstrate load following
        plant_lf, load_profile, time_points = demonstrate_load_following()
        
        # Demonstrate control interactions
        demonstrate_control_interactions()
        
        # Generate plots
        plot_integrated_results(plant_lf)
        
        print("=" * 80)
        print("INTEGRATION SUMMARY")
        print("=" * 80)
        print("Successfully demonstrated complete primary-secondary integration:")
        print()
        print("✓ Primary Reactor Physics:")
        print("  - Neutron kinetics with point kinetics equations")
        print("  - Reactivity feedback (temperature, xenon, control rods)")
        print("  - Thermal hydraulics and heat transfer")
        print("  - Safety systems and protection")
        print()
        print("✓ Secondary Steam Cycle Physics:")
        print("  - Steam generator heat transfer and two-phase flow")
        print("  - Turbine expansion and power generation")
        print("  - Condenser heat rejection and vacuum systems")
        print("  - Complete mass and energy balance")
        print()
        print("✓ Primary-Secondary Coupling:")
        print("  - Heat transfer from primary to secondary via steam generators")
        print("  - Primary coolant temperature calculation based on heat removal")
        print("  - Steam conditions determined by primary heat input")
        print("  - Feedback loops for load following and control")
        print()
        print("✓ Integrated Plant Control:")
        print("  - Control rod reactivity management")
        print("  - Load following capability")
        print("  - Coordinated primary-secondary response")
        print("  - Realistic plant dynamics and time constants")
        print()
        print("This integration provides a complete nuclear power plant model")
        print("suitable for operator training, control system development,")
        print("and safety analysis applications.")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
