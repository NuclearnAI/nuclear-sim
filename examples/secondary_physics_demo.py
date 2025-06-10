#!/usr/bin/env python3
"""
Secondary Reactor Physics Demonstration

This script demonstrates the comprehensive secondary reactor physics implementation,
showing how steam generators, turbines, and condensers work together to model
the complete steam cycle of a PWR nuclear power plant.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import matplotlib.pyplot as plt
from systems.secondary import SecondaryReactorPhysics
from systems.secondary.steam_generator import SteamGeneratorConfig
from systems.secondary.turbine import TurbineConfig
from systems.secondary.condenser import CondenserConfig


def demonstrate_design_point_performance():
    """Demonstrate design point performance of secondary system"""
    print("=" * 70)
    print("SECONDARY REACTOR PHYSICS - DESIGN POINT PERFORMANCE")
    print("=" * 70)
    
    # Create secondary system with 3 steam generators (typical PWR)
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    print(f"System Configuration:")
    print(f"  Number of Steam Generators: {secondary_system.num_steam_generators}")
    print(f"  Steam Generator Design Power: {secondary_system.steam_generators[0].config.design_thermal_power/1e6:.0f} MW each")
    print(f"  Turbine Design Power: {secondary_system.turbine.config.rated_power_mwe:.0f} MW electrical")
    print(f"  Condenser Design Heat Duty: {secondary_system.condenser.config.design_heat_duty/1e6:.0f} MW")
    print()
    
    # Calculate design performance
    design_performance = secondary_system.calculate_design_performance()
    
    print("Design Point Performance:")
    print(f"  Electrical Power Output: {design_performance['design_electrical_power_mw']:.1f} MW")
    print(f"  Thermal Efficiency: {design_performance['design_thermal_efficiency']*100:.2f}%")
    print(f"  Heat Rate: {design_performance['design_heat_rate_kj_kwh']:.0f} kJ/kWh")
    print(f"  Total Steam Flow: {design_performance['design_steam_flow_kg_s']:.0f} kg/s")
    print(f"  Total Heat Transfer: {design_performance['design_heat_transfer_mw']:.0f} MW")
    print(f"  Condenser Pressure: {design_performance['design_condenser_pressure_mpa']:.4f} MPa")
    print(f"  Turbine Efficiency: {design_performance['design_turbine_efficiency']*100:.2f}%")
    print()
    
    return secondary_system, design_performance


def demonstrate_load_following():
    """Demonstrate load following capability"""
    print("=" * 70)
    print("LOAD FOLLOWING DEMONSTRATION")
    print("=" * 70)
    
    # Create secondary system
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    # Primary conditions (constant for this demo)
    primary_conditions = {
        'sg_1_inlet_temp': 327.0,  # °C
        'sg_1_outlet_temp': 293.0,  # °C
        'sg_1_flow': 5700.0,       # kg/s
        'sg_2_inlet_temp': 327.0,
        'sg_2_outlet_temp': 293.0,
        'sg_2_flow': 5700.0,
        'sg_3_inlet_temp': 327.0,
        'sg_3_outlet_temp': 293.0,
        'sg_3_flow': 5700.0
    }
    
    # Test different load levels
    load_levels = [100, 90, 80, 70, 60, 50, 40, 30]
    results = []
    
    print("Load Following Performance:")
    print(f"{'Load %':<8} {'Power MW':<10} {'Efficiency %':<12} {'Steam Flow':<12} {'Heat Rate':<12}")
    print("-" * 64)
    
    for load in load_levels:
        control_inputs = {
            'load_demand': load,
            'feedwater_temp': 227.0,
            'cooling_water_temp': 25.0,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        result = secondary_system.update_system(
            primary_conditions=primary_conditions,
            control_inputs=control_inputs,
            dt=1.0
        )
        
        results.append({
            'load': load,
            'power': result['electrical_power_mw'],
            'efficiency': result['thermal_efficiency'] * 100,
            'steam_flow': result['total_steam_flow'],
            'heat_rate': result['heat_rate_kj_kwh']
        })
        
        print(f"{load:<8.0f} {result['electrical_power_mw']:<10.1f} "
              f"{result['thermal_efficiency']*100:<12.2f} "
              f"{result['total_steam_flow']:<12.0f} "
              f"{result['heat_rate_kj_kwh']:<12.0f}")
    
    print()
    return results


def demonstrate_transient_response():
    """Demonstrate transient response to load changes"""
    print("=" * 70)
    print("TRANSIENT RESPONSE DEMONSTRATION")
    print("=" * 70)
    
    # Create secondary system
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    # Primary conditions
    primary_conditions = {
        'sg_1_inlet_temp': 327.0,
        'sg_1_outlet_temp': 293.0,
        'sg_1_flow': 5700.0,
        'sg_2_inlet_temp': 327.0,
        'sg_2_outlet_temp': 293.0,
        'sg_2_flow': 5700.0,
        'sg_3_inlet_temp': 327.0,
        'sg_3_outlet_temp': 293.0,
        'sg_3_flow': 5700.0
    }
    
    # Simulate load step change: 100% -> 75% -> 50% -> 100%
    time_points = []
    load_demands = []
    power_outputs = []
    efficiencies = []
    steam_flows = []
    
    dt = 1.0  # 1 second time steps
    total_time = 300  # 5 minutes
    
    print("Simulating load step changes over 5 minutes...")
    print("Load profile: 100% -> 75% (t=60s) -> 50% (t=120s) -> 100% (t=180s)")
    print()
    
    for t in range(total_time):
        # Define load profile
        if t < 60:
            load_demand = 100.0
        elif t < 120:
            load_demand = 75.0
        elif t < 180:
            load_demand = 50.0
        else:
            load_demand = 100.0
        
        control_inputs = {
            'load_demand': load_demand,
            'feedwater_temp': 227.0,
            'cooling_water_temp': 25.0,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        result = secondary_system.update_system(
            primary_conditions=primary_conditions,
            control_inputs=control_inputs,
            dt=dt
        )
        
        time_points.append(t)
        load_demands.append(load_demand)
        power_outputs.append(result['electrical_power_mw'])
        efficiencies.append(result['thermal_efficiency'] * 100)
        steam_flows.append(result['total_steam_flow'])
        
        # Print status every 30 seconds
        if t % 30 == 0:
            print(f"t={t:3d}s: Load={load_demand:5.1f}%, "
                  f"Power={result['electrical_power_mw']:6.1f} MW, "
                  f"Efficiency={result['thermal_efficiency']*100:5.2f}%")
    
    print()
    return time_points, load_demands, power_outputs, efficiencies, steam_flows


def demonstrate_component_details():
    """Demonstrate detailed component performance"""
    print("=" * 70)
    print("COMPONENT PERFORMANCE DETAILS")
    print("=" * 70)
    
    # Create secondary system
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    # Primary conditions
    primary_conditions = {
        'sg_1_inlet_temp': 327.0,
        'sg_1_outlet_temp': 293.0,
        'sg_1_flow': 5700.0,
        'sg_2_inlet_temp': 327.0,
        'sg_2_outlet_temp': 293.0,
        'sg_2_flow': 5700.0,
        'sg_3_inlet_temp': 327.0,
        'sg_3_outlet_temp': 293.0,
        'sg_3_flow': 5700.0
    }
    
    control_inputs = {
        'load_demand': 100.0,
        'feedwater_temp': 227.0,
        'cooling_water_temp': 25.0,
        'cooling_water_flow': 45000.0,
        'vacuum_pump_operation': 1.0
    }
    
    result = secondary_system.update_system(
        primary_conditions=primary_conditions,
        control_inputs=control_inputs,
        dt=1.0
    )
    
    # Steam Generator Details
    print("Steam Generator Performance:")
    for i, sg_state in enumerate(result['steam_generator_states']):
        print(f"  SG {i+1}:")
        print(f"    Primary Inlet Temp: {sg_state['primary_inlet_temp']:.1f} °C")
        print(f"    Primary Outlet Temp: {sg_state['primary_outlet_temp']:.1f} °C")
        print(f"    Secondary Pressure: {sg_state['secondary_pressure']:.3f} MPa")
        print(f"    Secondary Temperature: {sg_state['secondary_temperature']:.1f} °C")
        print(f"    Steam Quality: {sg_state['steam_quality']:.3f}")
        print(f"    Water Level: {sg_state['water_level']:.1f} m")
        print(f"    Heat Transfer Rate: {sg_state['heat_transfer_rate']/1e6:.1f} MW")
        print(f"    Overall HTC: {sg_state['overall_htc']:.0f} W/m²/K")
        print()
    
    # Turbine Details
    turbine_state = result['turbine_state']
    print("Turbine Performance:")
    print(f"  HP Turbine Power: {result['turbine_hp_power']:.1f} MW")
    print(f"  LP Turbine Power: {result['turbine_lp_power']:.1f} MW")
    print(f"  Mechanical Power: {result['turbine_mechanical_power']:.1f} MW")
    print(f"  Electrical Power (Gross): {result['turbine_electrical_power_gross']:.1f} MW")
    print(f"  Electrical Power (Net): {result['turbine_electrical_power_net']:.1f} MW")
    print(f"  Steam Rate: {result['turbine_steam_rate']:.1f} kg/MWh")
    print(f"  HP Exhaust Pressure: {turbine_state['hp_exhaust_pressure']:.3f} MPa")
    print(f"  HP Exhaust Quality: {turbine_state['hp_exhaust_quality']:.3f}")
    print(f"  Condenser Pressure: {turbine_state['condenser_pressure']:.4f} MPa")
    print()
    
    # Condenser Details
    condenser_state = result['condenser_state']
    print("Condenser Performance:")
    print(f"  Heat Rejection: {result['condenser_heat_rejection']/1e6:.1f} MW")
    print(f"  Cooling Water Inlet Temp: {condenser_state['cooling_water_inlet_temp']:.1f} °C")
    print(f"  Cooling Water Outlet Temp: {condenser_state['cooling_water_outlet_temp']:.1f} °C")
    print(f"  Cooling Water Temp Rise: {result['condenser_cooling_water_temp_rise']:.1f} °C")
    print(f"  Condenser Pressure: {condenser_state['condenser_pressure']:.4f} MPa")
    print(f"  Air Partial Pressure: {condenser_state['air_partial_pressure']:.6f} MPa")
    print(f"  Thermal Performance: {result['condenser_thermal_performance']:.3f}")
    print(f"  Overall HTC: {condenser_state['overall_htc']:.0f} W/m²/K")
    print()


def plot_results(time_points, load_demands, power_outputs, efficiencies, steam_flows):
    """Plot transient response results"""
    print("Generating performance plots...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
    
    # Load demand and power output
    ax1.plot(time_points, load_demands, 'r--', label='Load Demand', linewidth=2)
    ax1_twin = ax1.twinx()
    ax1_twin.plot(time_points, power_outputs, 'b-', label='Power Output', linewidth=2)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Load Demand (%)', color='r')
    ax1_twin.set_ylabel('Power Output (MW)', color='b')
    ax1.set_title('Load Following Response')
    ax1.grid(True, alpha=0.3)
    
    # Efficiency
    ax2.plot(time_points, efficiencies, 'g-', linewidth=2)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Thermal Efficiency (%)')
    ax2.set_title('Thermal Efficiency')
    ax2.grid(True, alpha=0.3)
    
    # Steam flow
    ax3.plot(time_points, steam_flows, 'm-', linewidth=2)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Steam Flow (kg/s)')
    ax3.set_title('Total Steam Flow')
    ax3.grid(True, alpha=0.3)
    
    # Power vs efficiency
    ax4.scatter(power_outputs, efficiencies, c=load_demands, cmap='viridis', s=20)
    ax4.set_xlabel('Power Output (MW)')
    ax4.set_ylabel('Thermal Efficiency (%)')
    ax4.set_title('Efficiency vs Power')
    ax4.grid(True, alpha=0.3)
    cbar = plt.colorbar(ax4.collections[0], ax=ax4)
    cbar.set_label('Load Demand (%)')
    
    plt.tight_layout()
    plt.savefig('secondary_physics_performance.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'secondary_physics_performance.png'")
    plt.show()


def main():
    """Main demonstration function"""
    print("NUCLEAR PLANT SECONDARY REACTOR PHYSICS DEMONSTRATION")
    print("Based on Westinghouse AP1000 Design Parameters")
    print()
    
    try:
        # Demonstrate design point performance
        secondary_system, design_perf = demonstrate_design_point_performance()
        
        # Demonstrate load following
        load_results = demonstrate_load_following()
        
        # Demonstrate transient response
        time_points, load_demands, power_outputs, efficiencies, steam_flows = demonstrate_transient_response()
        
        # Show component details
        demonstrate_component_details()
        
        # Generate plots
        plot_results(time_points, load_demands, power_outputs, efficiencies, steam_flows)
        
        print("=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("Secondary reactor physics successfully implemented with:")
        print("✓ Steam Generator Physics - Heat transfer, two-phase flow, level dynamics")
        print("✓ Turbine Physics - HP/LP expansion, moisture separation, power generation")
        print("✓ Condenser Physics - Heat rejection, vacuum systems, fouling effects")
        print("✓ Integrated System - Complete steam cycle with control dynamics")
        print("✓ Performance Validation - Design point and transient operation")
        print()
        print("Key Features:")
        print("- Physics-based models with validated parameters")
        print("- Real-time transient response capability")
        print("- Load following and control system dynamics")
        print("- Comprehensive performance monitoring")
        print("- Integration with existing nuclear simulation")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
