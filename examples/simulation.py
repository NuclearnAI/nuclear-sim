#!/usr/bin/env python
# coding: utf-8

# # Nuclear Plant Simulation with Integrated Work Order Management
# This notebook demonstrates the comprehensive capabilities of our nuclear plant simulator
# with integrated automatic maintenance management. We implement the physics for:
# 
# - Reactors with realistic heat sources
# - Feedwater Pump Systems with maintenance monitoring
# - Steam Generation Systems with automatic work order generation
# - Turbine Systems with predictive maintenance
# - Condenser Systems with condition-based maintenance
# - Complete Work Order Management System

# ## Setup and Imports

# In[1]:


import sys
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict, Any
import time
from datetime import datetime

# Add project root to path
sys.path.append('..')
sys.path.append('../simulator')
sys.path.append('../systems')
sys.path.append('../core')

# Import nuclear simulator components
from simulator.core.sim import NuclearPlantSimulator, ControlAction
from systems.primary.reactor.heat_sources import ReactorHeatSource, ConstantHeatSource
from systems.primary.reactor.reactivity_model import create_equilibrium_state

# Import maintenance system components
from systems.maintenance import (
    AutoMaintenanceSystem, 
    WorkOrder, 
    WorkOrderStatus, 
    WorkOrderType, 
    Priority,
    MaintenanceActionType
)

# Import the physics-based PI formatter
sys.path.append('../data')
from data.physics_based_pi_formatter import PhysicsBasedPIFormatter, PhysicsValidationConfig
from data.pi_data_formatter import PIDataFormatter

# Configure matplotlib for better plots
plt.style.use('default')
plt.rcParams['figure.figsize'] = (15, 10)
plt.rcParams['font.size'] = 10

print("✅ All imports successful!")
print(f"📅 Simulation started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("🔧 Work Order Management System: ENABLED")


# ## Create Enhanced Simulator with Maintenance Management
# 
# Let's create a nuclear plant simulator with integrated automatic maintenance management.
# This demonstrates how modern nuclear plants operate with sophisticated maintenance systems.
# Note: dt=1.0 represents 1 minute simulation time steps.

# In[2]:


def create_enhanced_simulator():
    """Create nuclear plant simulator with integrated maintenance management"""
    
    # Create constant heat source with realistic noise
    heat_source = ConstantHeatSource(
        rated_power_mw=3000.0, 
        noise_enabled=True, 
        noise_std_percent=15.0, 
        noise_seed=42
    )
    
    # Create simulator with secondary systems enabled (dt=1.0 means 1 minute per step)
    simulator = NuclearPlantSimulator(
        heat_source=heat_source, 
        dt=1.0,  # 1 minute per simulation step
        enable_secondary=True
    )
    
    # Create automatic maintenance system
    maintenance_system = AutoMaintenanceSystem()
    
    # Configure maintenance system for minute-based simulation
    maintenance_system.check_interval_hours = 0.25  # Check every 15 minutes (15 simulation steps)
    maintenance_system.emergency_delay_hours = 0.0  # Execute immediately
    maintenance_system.high_priority_delay_hours = 1.0  # 1 hour delay (60 steps)
    maintenance_system.medium_priority_delay_hours = 4.0  # 4 hour delay (240 steps)
    maintenance_system.low_priority_delay_hours = 24.0  # 24 hour delay (1440 steps)
    
    print("🔥 Heat Source Configuration:")
    print(f"   Type: {heat_source.__class__.__name__}")
    print(f"   Rated Power: {heat_source.rated_power_mw:.0f} MW")
    print(f"   Current Power: {heat_source.get_power_percent():.1f}%")
    
    print("\n🏭 Simulator Configuration:")
    print(f"   Time Step: {simulator.dt:.1f} minutes")
    print(f"   Initial Power Level: {simulator.state.power_level:.1f}%")
    print(f"   Initial Fuel Temperature: {simulator.state.fuel_temperature:.1f}°C")
    print(f"   Initial Coolant Temperature: {simulator.state.coolant_temperature:.1f}°C")
    
    print("\n🔧 Maintenance System Configuration:")
    print(f"   Auto-execution: {maintenance_system.auto_execute_maintenance}")
    print(f"   Check interval: {maintenance_system.check_interval_hours} hours ({maintenance_system.check_interval_hours * 60:.0f} minutes)")
    print(f"   Work orders created: {maintenance_system.work_orders_created}")
    
    return simulator, heat_source, maintenance_system

# Create the enhanced simulator
simulator, heat_source, maintenance_system = create_enhanced_simulator()


# ## Register Components for Automatic Maintenance
# 
# Register key plant components with the maintenance system for automatic monitoring
# and work order generation based on realistic operating parameters.

# In[3]:


def register_components_for_maintenance(simulator, maintenance_system):
    """Register plant components with realistic maintenance monitoring"""
    
    print("🔧 Registering components for automatic maintenance...")
    
    # Register feedwater pumps with comprehensive monitoring
    if hasattr(simulator.secondary_physics, 'feedwater_system'):
        feedwater_system = simulator.secondary_physics.feedwater_system
        
        if hasattr(feedwater_system, 'pump_system') and hasattr(feedwater_system.pump_system, 'pumps'):
            for pump_id, pump in feedwater_system.pump_system.pumps.items():
                
                # Create realistic monitoring configuration for each pump
                monitoring_config = {
                    'oil_level': {
                        'attribute': 'state.oil_level',
                        'threshold': 35.0,  # Low oil level threshold
                        'comparison': 'less_than',
                        'action': 'oil_top_off',
                        'cooldown_hours': 2.0  # 2 hours = 120 minutes
                    },
                    'bearing_temperature': {
                        'attribute': 'state.bearing_temperature',
                        'threshold': 85.0,  # High bearing temperature
                        'comparison': 'greater_than',
                        'action': 'bearing_inspection',
                        'cooldown_hours': 8.0  # 8 hours = 480 minutes
                    },
                    'vibration_level': {
                        'attribute': 'state.vibration_level',
                        'threshold': 8.0,   # High vibration
                        'comparison': 'greater_than',
                        'action': 'vibration_analysis',
                        'cooldown_hours': 12.0  # 12 hours = 720 minutes
                    },
                    'impeller_wear': {
                        'attribute': 'state.impeller_wear',
                        'threshold': 15.0,  # Significant wear
                        'comparison': 'greater_than',
                        'action': 'impeller_inspection',
                        'cooldown_hours': 24.0  # 24 hours = 1440 minutes
                    }
                }
                
                maintenance_system.register_component(pump_id, pump, monitoring_config)
                print(f"   ✅ Registered {pump_id} for maintenance monitoring")
    
    # Register steam generators
    if hasattr(simulator.secondary_physics, 'steam_generators'):
        for sg_id, sg in simulator.secondary_physics.steam_generators.items():
            
            monitoring_config = {
                'tube_fouling': {
                    'attribute': 'state.tube_fouling_factor',
                    'threshold': 0.15,  # 15% fouling
                    'comparison': 'greater_than',
                    'action': 'tube_cleaning',
                    'cooldown_hours': 48.0  # 48 hours = 2880 minutes
                },
                'water_level': {
                    'attribute': 'state.water_level',
                    'threshold': 25.0,  # Low water level
                    'comparison': 'less_than',
                    'action': 'level_control_check',
                    'cooldown_hours': 4.0  # 4 hours = 240 minutes
                }
            }
            
            maintenance_system.register_component(sg_id, sg, monitoring_config)
            print(f"   ✅ Registered {sg_id} for maintenance monitoring")
    
    # Register turbines
    if hasattr(simulator.secondary_physics, 'turbine'):
        turbine = simulator.secondary_physics.turbine
        
        # Register individual turbine stages if available
        if hasattr(turbine, 'stages'):
            for stage_id, stage in turbine.stages.items():
                monitoring_config = {
                    'efficiency': {
                        'attribute': 'state.efficiency',
                        'threshold': 0.85,  # Low efficiency
                        'comparison': 'less_than',
                        'action': 'efficiency_analysis',
                        'cooldown_hours': 24.0  # 24 hours = 1440 minutes
                    },
                    'blade_wear': {
                        'attribute': 'state.blade_wear',
                        'threshold': 10.0,  # Blade wear percentage
                        'comparison': 'greater_than',
                        'action': 'blade_inspection',
                        'cooldown_hours': 72.0  # 72 hours = 4320 minutes
                    }
                }
                
                maintenance_system.register_component(stage_id, stage, monitoring_config)
                print(f"   ✅ Registered {stage_id} for maintenance monitoring")
    
    # Register condenser
    if hasattr(simulator.secondary_physics, 'condenser'):
        condenser = simulator.secondary_physics.condenser
        
        monitoring_config = {
            'vacuum_level': {
                'attribute': 'state.vacuum_level',
                'threshold': 90.0,  # Low vacuum
                'comparison': 'less_than',
                'action': 'vacuum_system_check',
                'cooldown_hours': 6.0  # 6 hours = 360 minutes
            },
            'tube_cleanliness': {
                'attribute': 'state.tube_cleanliness',
                'threshold': 0.80,  # Dirty tubes
                'comparison': 'less_than',
                'action': 'tube_cleaning',
                'cooldown_hours': 48.0  # 48 hours = 2880 minutes
            }
        }
        
        maintenance_system.register_component('CONDENSER', condenser, monitoring_config)
        print(f"   ✅ Registered CONDENSER for maintenance monitoring")
    
    print(f"\n🔧 Component registration complete!")
    print(f"   Total components registered: {len(maintenance_system.event_bus.components)}")

# Register components for maintenance
register_components_for_maintenance(simulator, maintenance_system)


# ## Enhanced Simulation with Maintenance Integration
# 
# Run a comprehensive simulation that demonstrates both nuclear plant operations
# and integrated maintenance management with automatic work order generation.
# Time units: Each step = 1 minute, so 300 steps = 5 hours of operation.

# In[4]:


def run_enhanced_simulation_with_maintenance(duration_minutes: int = 300) -> Dict[str, pd.DataFrame]:
    """
    Run enhanced simulation with integrated maintenance management
    
    Args:
        duration_minutes: Simulation duration in minutes (simulation steps)
        
    Returns:
        Dictionary containing simulation data and maintenance data
    """
    
    # Reset systems
    simulator.reset(True)
    maintenance_system.reset()
    
    # Re-register components after reset
    register_components_for_maintenance(simulator, maintenance_system)
    
    # Data collection
    simulation_data = []
    maintenance_data = []
    work_order_events = []
    
    print(f"🚀 Running enhanced simulation for {duration_minutes} minutes ({duration_minutes/60:.1f} hours)...")
    print(f"{'Time (min)':<10} {'Power (MW)':<12} {'Work Orders':<12} {'Maintenance':<15}")
    print("-" * 80)
    
    # Power level variation schedule for realistic operation
    power_levels = [77., 75., 78., 73., 75., 80., 77., 81., 83., 72., 77., 75., 78., 73., 75., 80., 77., 81., 83., 72.]
    power_level = simulator.state.power_level
    
    for t in range(duration_minutes):
        current_time = simulator.time  # This is in minutes
        
        # Update power level following realistic load-following pattern (every 2.5 hours = 150 minutes)
        if t % 150 == 0:
            previous_power_level = power_level
            target_power_level = power_levels[min(t // 150, len(power_levels) - 1)]
        
        power_level += (target_power_level - previous_power_level) / 150
        heat_source.set_power_setpoint(power_level)
        
        # Step nuclear plant simulation (dt=1.0 minute)
        result = simulator.step(ControlAction.NO_ACTION, 1.0, load_demand=power_level)
        
        # Update maintenance system (this monitors components and creates work orders)
        # Convert current_time from minutes to hours for maintenance system
        new_work_orders = maintenance_system.update(current_time / 60.0, 1.0 / 60.0)
        
        # Collect simulation data
        sim_data = {
            'time_minutes': current_time,
            'time_hours': current_time / 60.0,
            'power_level': simulator.state.power_level,
            'fuel_temperature': simulator.state.fuel_temperature,
            'coolant_temperature': simulator.state.coolant_temperature,
            'coolant_pressure': simulator.state.coolant_pressure,
            'control_rod_position': simulator.state.control_rod_position,
            'steam_flow_rate': simulator.state.steam_flow_rate,
            'steam_pressure': simulator.state.steam_pressure,
            'thermal_power_mw': result['info']['thermal_power'],
            'feedwater_flow_rate': simulator.secondary_physics.total_feedwater_flow,
            'heat_rejection_rate': simulator.secondary_physics.total_system_heat_rejection,
        }
        simulation_data.append(sim_data)
        
        # Collect maintenance system data
        maintenance_status = maintenance_system.get_system_status()
        maint_data = {
            'time_minutes': current_time,
            'time_hours': current_time / 60.0,
            'active_work_orders': maintenance_status['work_order_stats']['total_active'],
            'completed_work_orders': maintenance_status['work_order_stats']['total_completed'],
            'work_orders_created': maintenance_status['work_orders_created'],
            'work_orders_executed': maintenance_status['work_orders_executed'],
            'maintenance_actions_performed': maintenance_status['maintenance_actions_performed'],
            'components_monitored': len(maintenance_system.event_bus.components)
        }
        maintenance_data.append(maint_data)
        
        # Record work order events
        for work_order in new_work_orders:
            work_order_events.append({
                'time_minutes': current_time,
                'time_hours': current_time / 60.0,
                'work_order_id': work_order.work_order_id,
                'component_id': work_order.component_id,
                'work_type': work_order.work_order_type.value,
                'priority': work_order.priority.value,
                'status': work_order.status.value,
                'title': work_order.title,
                'auto_generated': work_order.auto_generated
            })
        
        # Print status every hour (60 minutes)
        if t % 60 == 0:
            active_orders = maintenance_status['work_order_stats']['total_active']
            completed_orders = maintenance_status['work_order_stats']['total_completed']
            actions_performed = maintenance_status['maintenance_actions_performed']
            
            print(f"{current_time:<10.0f} {simulator.primary_physics.thermal_power_mw:<12.1f} "
                  f"{active_orders:<4}/{completed_orders:<6} {actions_performed:<15}")
        
        # Check for early termination
        if result['done']:
            print(f"\n⚠️  Simulation terminated early at {current_time:.0f} minutes due to safety system activation")
            break
    
    print(f"\n✅ Enhanced simulation completed!")
    print(f"   Final time: {simulator.time:.0f} minutes ({simulator.time/60:.1f} hours)")
    print(f"   Final power: {simulator.state.power_level:.1f}%")
    print(f"   Total work orders created: {maintenance_system.work_orders_created}")
    print(f"   Total work orders executed: {maintenance_system.work_orders_executed}")
    print(f"   Total maintenance actions: {maintenance_system.maintenance_actions_performed}")
    
    return {
        'simulation': pd.DataFrame(simulation_data),
        'maintenance': pd.DataFrame(maintenance_data),
        'work_orders': pd.DataFrame(work_order_events)
    }

# Run the enhanced simulation (5 hours = 300 minutes)
enhanced_data = run_enhanced_simulation_with_maintenance(300)


# ## Comprehensive Results Analysis and Visualization
# 
# Analyze and visualize both the nuclear plant operation and maintenance management results.

# In[5]:


def plot_enhanced_simulation_results(data_dict: Dict[str, pd.DataFrame]):
    """
    Plot comprehensive results including plant operation and maintenance management
    """
    simulation_data = data_dict['simulation']
    maintenance_data = data_dict['maintenance']
    work_order_data = data_dict['work_orders']
    
    # Create comprehensive dashboard
    fig = plt.figure(figsize=(20, 16))
    
    # Define grid layout for subplots
    gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
    
    # Row 1: Plant Operation Parameters
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(simulation_data['time_hours'], simulation_data['power_level'], 'b-', linewidth=2, label='Power Level')
    ax1.axhline(y=100, color='g', linestyle='--', alpha=0.7, label='Rated Power')
    ax1.set_ylabel('Power Level (%)')
    ax1.set_xlabel('Time (hours)')
    ax1.set_title('Power Level')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(simulation_data['time_hours'], simulation_data['fuel_temperature'], 'r-', linewidth=2, label='Fuel')
    ax2.plot(simulation_data['time_hours'], simulation_data['coolant_temperature'], 'b-', linewidth=2, label='Coolant')
    ax2.set_ylabel('Temperature (°C)')
    ax2.set_xlabel('Time (hours)')
    ax2.set_title('Temperatures')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(simulation_data['time_hours'], simulation_data['thermal_power_mw'], 'red', linewidth=2)
    ax3.axhline(y=3000, color='g', linestyle='--', alpha=0.7, label='Rated Power')
    ax3.set_ylabel('Thermal Power (MW)')
    ax3.set_xlabel('Time (hours)')
    ax3.set_title('Thermal Power Output')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Row 2: Secondary System Parameters
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.plot(simulation_data['time_hours'], simulation_data['feedwater_flow_rate'], 'cyan', linewidth=2)
    ax4.set_ylabel('Feedwater Flow (kg/s)')
    ax4.set_xlabel('Time (hours)')
    ax4.set_title('Feedwater Flow Rate')
    ax4.grid(True, alpha=0.3)
    
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(simulation_data['time_hours'], simulation_data['steam_pressure'], 'orange', linewidth=2)
    ax5.set_ylabel('Steam Pressure (Pa)')
    ax5.set_xlabel('Time (hours)')
    ax5.set_title('Steam Pressure')
    ax5.grid(True, alpha=0.3)
    
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.plot(simulation_data['time_hours'], simulation_data['heat_rejection_rate'], 'green', linewidth=2)
    ax6.set_ylabel('Heat Rejection (MW)')
    ax6.set_xlabel('Time (hours)')
    ax6.set_title('Heat Rejection Rate')
    ax6.grid(True, alpha=0.3)
    
    # Row 3: Maintenance System Status
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.plot(maintenance_data['time_hours'], maintenance_data['active_work_orders'], 'purple', linewidth=2, label='Active')
    ax7.plot(maintenance_data['time_hours'], maintenance_data['completed_work_orders'], 'brown', linewidth=2, label='Completed')
    ax7.set_ylabel('Work Orders')
    ax7.set_xlabel('Time (hours)')
    ax7.set_title('Work Order Status')
    ax7.grid(True, alpha=0.3)
    ax7.legend()
    
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.plot(maintenance_data['time_hours'], maintenance_data['work_orders_created'], 'red', linewidth=2, label='Created')
    ax8.plot(maintenance_data['time_hours'], maintenance_data['work_orders_executed'], 'blue', linewidth=2, label='Executed')
    ax8.set_ylabel('Cumulative Count')
    ax8.set_xlabel('Time (hours)')
    ax8.set_title('Work Order Creation & Execution')
    ax8.grid(True, alpha=0.3)
    ax8.legend()
    
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.plot(maintenance_data['time_hours'], maintenance_data['maintenance_actions_performed'], 'darkgreen', linewidth=2)
    ax9.set_ylabel('Actions Performed')
    ax9.set_xlabel('Time (hours)')
    ax9.set_title('Maintenance Actions')
    ax9.grid(True, alpha=0.3)
    
    # Row 4: Work Order Analysis
    ax10 = fig.add_subplot(gs[3, 0])
    if len(work_order_data) > 0:
        # Work order types distribution
        work_type_counts = work_order_data['work_type'].value_counts()
        ax10.pie(work_type_counts.values, labels=work_type_counts.index, autopct='%1.1f%%')
        ax10.set_title('Work Order Types')
    else:
        ax10.text(0.5, 0.5, 'No Work Orders\nGenerated', ha='center', va='center', transform=ax10.transAxes)
        ax10.set_title('Work Order Types')
    
    ax11 = fig.add_subplot(gs[3, 1])
    if len(work_order_data) > 0:
        # Priority distribution
        priority_counts = work_order_data['priority'].value_counts()
        colors = ['red', 'orange', 'yellow', 'lightblue', 'lightgreen']
        ax11.bar(priority_counts.index, priority_counts.values, color=colors[:len(priority_counts)])
        ax11.set_ylabel('Count')
        ax11.set_title('Work Order Priorities')
        ax11.tick_params(axis='x', rotation=45)
    else:
        ax11.text(0.5, 0.5, 'No Work Orders\nGenerated', ha='center', va='center', transform=ax11.transAxes)
        ax11.set_title('Work Order Priorities')
    
    ax12 = fig.add_subplot(gs[3, 2])
    if len(work_order_data) > 0:
        # Component maintenance frequency
        component_counts = work_order_data['component_id'].value_counts().head(10)
        ax12.barh(range(len(component_counts)), component_counts.values)
        ax12.set_yticks(range(len(component_counts)))
        ax12.set_yticklabels(component_counts.index)
        ax12.set_xlabel('Work Orders')
        ax12.set_title('Component Maintenance Frequency')
    else:
        ax12.text(0.5, 0.5, 'No Work Orders\nGenerated', ha='center', va='center', transform=ax12.transAxes)
        ax12.set_title('Component Maintenance Frequency')
    
    # Add overall title
    fig.suptitle('Nuclear Plant Simulation with Integrated Maintenance Management', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    plt.show()

# Plot the enhanced results
plot_enhanced_simulation_results(enhanced_data)


# ## Maintenance System Analysis and Reporting
# 
# Generate comprehensive reports on maintenance system performance and component health.

# In[6]:


def generate_maintenance_reports(maintenance_system, work_order_data):
    """Generate comprehensive maintenance system reports"""
    
    print("📊 MAINTENANCE SYSTEM PERFORMANCE REPORT")
    print("=" * 60)
    
    # System status
    status = maintenance_system.get_system_status()
    
    print("🔧 SYSTEM STATUS:")
    print(f"   Auto-execution enabled: {status['auto_execute_enabled']}")
    print(f"   Check interval: {status['check_interval_hours']} hours ({status['check_interval_hours'] * 60:.0f} minutes)")
    print(f"   Work orders created: {status['work_orders_created']}")
    print(f"   Work orders executed: {status['work_orders_executed']}")
    print(f"   Maintenance actions performed: {status['maintenance_actions_performed']}")
    
    # Work order statistics
    wo_stats = status['work_order_stats']
    print(f"\n📋 WORK ORDER STATISTICS:")
    print(f"   Total active: {wo_stats['total_active']}")
    print(f"   Total completed: {wo_stats['total_completed']}")
    print(f"   Average effectiveness: {wo_stats['avg_effectiveness']:.2f}")
    
    print(f"\n   By Status:")
    for status_name, count in wo_stats['by_status'].items():
        if count > 0:
            print(f"     {status_name}: {count}")
    
    print(f"\n   By Priority:")
    for priority_name, count in wo_stats['by_priority'].items():
        if count > 0:
            print(f"     {priority_name}: {count}")
    
    print(f"\n   By Type:")
    for type_name, count in wo_stats['by_type'].items():
        if count > 0:
            print(f"     {type_name}: {count}")
    
    # Component status
    component_summary = maintenance_system.get_component_summary()
    print(f"\n🔩 COMPONENT MONITORING:")
    print(f"   Total components registered: {len(component_summary)}")
    
    for component_id, component_info in list(component_summary.items())[:5]:  # Show first 5
        print(f"   {component_id}:")
        print(f"     Class: {component_info['class_name']}")
        print(f"     Monitoring parameters: {component_info.get('num_monitors', 0)}")
        print(f"     Registered time: {component_info.get('registered_time', 0.0):.1f}")
    
    # Recent work orders
    recent_orders = maintenance_system.get_recent_work_orders(5)
    if recent_orders:
        print(f"\n📝 RECENT WORK ORDERS:")
        for order in recent_orders:
            print(f"   {order['work_order_id']}: {order['title']}")
            print(f"     Component: {order['component_id']}")
            print(f"     Priority: {order['priority']} | Status: {order['status']}")
            print(f"     Auto-generated: {order['auto_generated']}")
            print()
    
    # Work order events analysis
    if len(work_order_data) > 0:
        print(f"\n📈 WORK ORDER EVENTS ANALYSIS:")
        print(f"   Total work order events: {len(work_order_data)}")
        print(f"   Unique components affected: {work_order_data['component_id'].nunique()}")
        print(f"   Auto-generated work orders: {work_order_data['auto_generated'].sum()}")
        
        # Most active components
        component_activity = work_order_data['component_id'].value_counts().head(3)
        print(f"\n   Most active components:")
        for component, count in component_activity.items():
            print(f"     {component}: {count} work orders")
    
    return status

# Generate maintenance reports
maintenance_reports = generate_maintenance_reports(maintenance_system, enhanced_data['work_orders'])


# ## Export Enhanced Results
# 
# Export all simulation and maintenance data for further analysis and reporting.

# In[7]:


def export_enhanced_results(data_dict, maintenance_system):
    """Export comprehensive simulation and maintenance results"""
    
    print("💾 EXPORTING ENHANCED SIMULATION RESULTS")
    print("=" * 50)
    
    # Export simulation data
    simulation_file = "enhanced_simulation_results.csv"
    data_dict['simulation'].to_csv(simulation_file, index=False)
    print(f"✅ Simulation data exported to: {simulation_file}")
    
    # Export maintenance data
    maintenance_file = "maintenance_system_results.csv"
    data_dict['maintenance'].to_csv(maintenance_file, index=False)
    print(f"✅ Maintenance data exported to: {maintenance_file}")
    
    # Export work order events
    if len(data_dict['work_orders']) > 0:
        work_orders_file = "work_order_events.csv"
        data_dict['work_orders'].to_csv(work_orders_file, index=False)
        print(f"✅ Work order events exported to: {work_orders_file}")
    
    # Export component status
    component_summary = maintenance_system.get_component_summary()
    if component_summary:
        component_file = "component_maintenance_status.csv"
        component_df = pd.DataFrame([
            {
                'component_id': comp_id,
                'class_name': info['class_name'],
                'monitoring_parameters': info.get('num_monitors', 0),
                'registered_time': info.get('registered_time', 0.0),
                'current_values': str(info.get('current_values', {}))
            }
            for comp_id, info in component_summary.items()
        ])
        component_df.to_csv(component_file, index=False)
        print(f"✅ Component status exported to: {component_file}")
    
    # Export recent work orders
    recent_orders = maintenance_system.get_recent_work_orders(20)
    if recent_orders:
        recent_orders_file = "recent_work_orders.csv"
        recent_df = pd.DataFrame(recent_orders)
        recent_df.to_csv(recent_orders_file, index=False)
        print(f"✅ Recent work orders exported to: {recent_orders_file}")
    
    # Generate summary report
    summary_file = "enhanced_simulation_summary.md"
    with open(summary_file, 'w') as f:
        f.write("# Enhanced Nuclear Plant Simulation with Maintenance Management\n\n")
        f.write(f"**Simulation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Simulation Overview\n")
        f.write(f"- Duration: {data_dict['simulation']['time_minutes'].max():.0f} minutes ({data_dict['simulation']['time_hours'].max():.1f} hours)\n")
        f.write(f"- Final Power Level: {data_dict['simulation']['power_level'].iloc[-1]:.1f}%\n")
        f.write(f"- Average Thermal Power: {data_dict['simulation']['thermal_power_mw'].mean():.1f} MW\n\n")
        
        f.write("## Maintenance System Performance\n")
        status = maintenance_system.get_system_status()
        f.write(f"- Work Orders Created: {status['work_orders_created']}\n")
        f.write(f"- Work Orders Executed: {status['work_orders_executed']}\n")
        f.write(f"- Maintenance Actions Performed: {status['maintenance_actions_performed']}\n")
        f.write(f"- Components Monitored: {len(maintenance_system.event_bus.components)}\n\n")
        
        if len(data_dict['work_orders']) > 0:
            f.write("## Work Order Summary\n")
            f.write(f"- Total Work Order Events: {len(data_dict['work_orders'])}\n")
            f.write(f"- Auto-Generated Orders: {data_dict['work_orders']['auto_generated'].sum()}\n")
            f.write(f"- Components Affected: {data_dict['work_orders']['component_id'].nunique()}\n\n")
        
        f.write("## Key Features Demonstrated\n")
        f.write("- ✅ Automatic component monitoring\n")
        f.write("- ✅ Event-driven work order generation\n")
        f.write("- ✅ Priority-based maintenance scheduling\n")
        f.write("- ✅ Real-time maintenance execution\n")
        f.write("- ✅ Comprehensive maintenance reporting\n")
        f.write("- ✅ Integration with nuclear plant physics\n")
    
    print(f"✅ Summary report exported to: {summary_file}")
    
    print(f"\n🎯 EXPORT SUMMARY:")
    print("=" * 30)
    print("The enhanced simulation successfully demonstrates:")
    print("1. ✅ Nuclear plant operation with realistic load following")
    print("2. ✅ Automatic maintenance system integration")
    print("3. ✅ Work order generation and execution")
    print("4. ✅ Component health monitoring")
    print("5. ✅ Comprehensive data export and reporting")
    
    return {
        'simulation_file': simulation_file,
        'maintenance_file': maintenance_file,
        'work_orders_file': work_orders_file if len(data_dict['work_orders']) > 0 else None,
        'component_file': component_file if component_summary else None,
        'summary_file': summary_file
    }

# Export the enhanced results
exported_files = export_enhanced_results(enhanced_data, maintenance_system)


# ## Summary: Nuclear Plant Simulation with Work Order Management
# 
# This enhanced simulation demonstrates the integration of a sophisticated work order
# management system with nuclear plant operations. Key achievements include:
# 
# ### 🔧 **Maintenance System Integration**
# - **Automatic Component Monitoring**: Real-time monitoring of pumps, steam generators, turbines, and condensers
# - **Event-Driven Work Orders**: Automatic generation based on parameter thresholds
# - **Priority-Based Scheduling**: Emergency to low priority with appropriate delays
# - **Complete Lifecycle Management**: From creation to execution and completion
# 
# ### 📊 **Comprehensive Data Management**
# - **Time-Aware Operations**: Proper handling of minute-based simulation time steps
# - **Multi-System Tracking**: Both plant physics and maintenance operations
# - **Export Capabilities**: CSV files for further analysis and reporting
# - **Real-Time Reporting**: Live status updates during simulation
# 
# ### 🏭 **Realistic Plant Operations**
# - **Load Following**: Realistic power level variations over time
# - **Component Degradation**: Simulated wear and maintenance needs
# - **Maintenance Impact**: Effects of maintenance on plant operations
# - **Operational Continuity**: Plant continues operating during maintenance
# 
# ### 🎯 **Key Benefits**
# 1. **Proactive Maintenance**: Issues detected before failures occur
# 2. **Optimized Scheduling**: Priority-based work order execution
# 3. **Complete Audit Trail**: Full documentation of all maintenance activities
# 4. **Performance Metrics**: Effectiveness tracking and continuous improvement
# 5. **Regulatory Compliance**: Comprehensive maintenance records
# 
# This system represents a significant advancement in nuclear plant simulation,
# providing a realistic demonstration of how modern maintenance management systems
# integrate with plant operations to ensure safe, reliable, and efficient operation.

print("\n" + "="*80)
print("🎉 ENHANCED NUCLEAR PLANT SIMULATION WITH WORK ORDER MANAGEMENT COMPLETE!")
print("="*80)
print(f"📊 Simulation Duration: {enhanced_data['simulation']['time_hours'].max():.1f} hours")
print(f"🔧 Work Orders Created: {maintenance_system.work_orders_created}")
print(f"⚡ Maintenance Actions: {maintenance_system.maintenance_actions_performed}")
print(f"📁 Files Exported: {len([f for f in exported_files.values() if f is not None])}")
print("="*80)
