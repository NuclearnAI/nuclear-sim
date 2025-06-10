import warnings
import sys
import os
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

# Add the project root to the path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new primary physics system
from systems.primary import PrimaryReactorPhysics, ReactorState, ControlAction
# Import from the secondary physics system
from systems.secondary import SecondaryReactorPhysics
from systems.primary.reactor.reactivity_model import create_equilibrium_state

warnings.filterwarnings("ignore")


class NuclearPlantSimulator:
    """Physics-based nuclear power plant simulator with integrated primary and secondary systems"""

    def __init__(self, dt: float = 1.0, heat_source=None, enable_secondary: bool = True):
        self.dt = dt  # Time step in seconds
        self.time = 0.0
        self.history = {
            'time': [],
            'primary': {
                'neutron_flux': [],
                'fuel_temperature': [],
                'coolant_temperature': [],
                'coolant_pressure': [],
                'coolant_flow_rate': [],
                'steam_temperature': [],
                'steam_pressure': [],
                'steam_flow_rate': [],
                'control_rod_position': [],
                'steam_valve_position': [],
                'power_level': [],
                'scram_status': [],
                'reactivity': [],
                'boron_concentration': [],
                'thermal_power': []
            },
            'secondary': {
                'electrical_power': [],
                'thermal_efficiency': [],
                'total_steam_flow': [],
                'sg_avg_pressure': [],
                'sg_avg_temperature': [],
                'condenser_pressure': [],
                'condenser_temperature': [],
                'turbine_power': [],
                'generator_power': [],
                'feedwater_flow': [],
                'feedwater_temperature': [],
                'cooling_water_temperature': [],
                'cooling_water_flow': [],
                'load_demand': [],
                'vacuum_pump_operation': []
            },
            'integration': {
                'primary_hot_leg_temp': [],
                'primary_cold_leg_temp': [],
                'heat_removal_rate': [],
                'overall_plant_efficiency': [],
                'coupling_factor': []
            }
        }
        self.enable_secondary = enable_secondary
        
        # Initialize primary reactor physics system
        self.primary_physics = PrimaryReactorPhysics(
            rated_power_mw=3000.0,
            heat_source=heat_source
        )
        
        # Initialize secondary reactor physics system (3 steam generators for typical PWR)
        if self.enable_secondary:
            self.secondary_physics = SecondaryReactorPhysics(num_steam_generators=3)
        else:
            self.secondary_physics = None
        
        # Integration parameters for primary-secondary coupling
        self.primary_loops = 3  # Number of primary loops
        self.thermal_power_split = [1/3, 1/3, 1/3]  # Equal split between loops
        
        # Control parameters for secondary system
        self.load_demand = 100.0  # % rated electrical load
        self.cooling_water_temp = 25.0  # °C
        
        # Expose state for backward compatibility
        self.state = self.primary_physics.state

    def step(
        self, action: Optional[ControlAction] = None, magnitude: float = 1.0,
        load_demand: float = None, cooling_water_temp: float = None
    ) -> Dict:
        """Advance simulation by one time step with integrated primary-secondary physics"""
        # Update control parameters if provided
        if load_demand is not None:
            self.load_demand = load_demand
        if cooling_water_temp is not None:
            self.cooling_water_temp = cooling_water_temp
        
        # Convert single action to control inputs format for primary physics
        control_inputs = self._convert_action_to_control_inputs(action, magnitude)
        
        # Update primary physics system
        primary_result = self.primary_physics.update_system(
            control_inputs=control_inputs,
            dt=self.dt
        )
        
        # Initialize secondary result for backward compatibility
        secondary_result = None
        
        # Update secondary physics system if enabled
        if self.enable_secondary and self.secondary_physics is not None:
            # Calculate primary-to-secondary coupling
            primary_conditions = self._calculate_primary_to_secondary_coupling()
            
            # Prepare secondary control inputs
            secondary_control_inputs = {
                'load_demand': self.load_demand,
                'feedwater_temp': 227.0,  # Typical feedwater temperature
                'cooling_water_temp': self.cooling_water_temp,
                'cooling_water_flow': 45000.0,  # Design cooling water flow
                'vacuum_pump_operation': 1.0
            }
            
            # Update secondary system
            secondary_result = self.secondary_physics.update_system(
                primary_conditions=primary_conditions,
                control_inputs=secondary_control_inputs,
                dt=self.dt
            )
            
            # Apply secondary-to-primary feedback (simplified)
            self._apply_secondary_to_primary_feedback(secondary_result)
        
        # Update time
        self.time += self.dt
        
        # Store history
        observation = self.get_observation()
        self.history['time'].append(self.time)
        
        # Primary system measurements
        self.history['primary']['neutron_flux'].append(self.state.neutron_flux)
        self.history['primary']['fuel_temperature'].append(self.state.fuel_temperature)
        self.history['primary']['coolant_temperature'].append(self.state.coolant_temperature)
        self.history['primary']['coolant_pressure'].append(self.state.coolant_pressure)
        self.history['primary']['coolant_flow_rate'].append(self.state.coolant_flow_rate)
        self.history['primary']['steam_temperature'].append(self.state.steam_temperature)
        self.history['primary']['steam_pressure'].append(self.state.steam_pressure)
        self.history['primary']['steam_flow_rate'].append(self.state.steam_flow_rate)
        self.history['primary']['control_rod_position'].append(self.state.control_rod_position)
        self.history['primary']['steam_valve_position'].append(self.state.steam_valve_position)
        self.history['primary']['power_level'].append(self.state.power_level)
        self.history['primary']['scram_status'].append(float(self.state.scram_status))
        self.history['primary']['reactivity'].append(primary_result['total_reactivity_pcm'])
        self.history['primary']['boron_concentration'].append(getattr(self.state, 'boron_concentration', 0.0))
        self.history['primary']['thermal_power'].append(primary_result['thermal_power_mw'])
        
        # Secondary system measurements
        if secondary_result is not None:
            self.history['secondary']['electrical_power'].append(secondary_result['electrical_power_mw'])
            self.history['secondary']['thermal_efficiency'].append(secondary_result['thermal_efficiency'])
            self.history['secondary']['total_steam_flow'].append(secondary_result['total_steam_flow'])
            self.history['secondary']['sg_avg_pressure'].append(secondary_result['sg_avg_pressure'])
            self.history['secondary']['sg_avg_temperature'].append(secondary_result.get('sg_avg_temperature', 0.0))
            self.history['secondary']['condenser_pressure'].append(secondary_result['condenser_pressure'])
            self.history['secondary']['condenser_temperature'].append(secondary_result.get('condenser_temperature', 0.0))
            self.history['secondary']['turbine_power'].append(secondary_result.get('turbine_power_mw', 0.0))
            self.history['secondary']['generator_power'].append(secondary_result['electrical_power_mw'])
            self.history['secondary']['feedwater_flow'].append(secondary_result.get('feedwater_flow', 0.0))
            self.history['secondary']['feedwater_temperature'].append(227.0)  # From control inputs
            self.history['secondary']['cooling_water_temperature'].append(self.cooling_water_temp)
            self.history['secondary']['cooling_water_flow'].append(45000.0)  # From control inputs
            self.history['secondary']['load_demand'].append(self.load_demand)
            self.history['secondary']['vacuum_pump_operation'].append(1.0)  # From control inputs
            
            # Integration measurements
            primary_conditions = self._calculate_primary_to_secondary_coupling()
            self.history['integration']['primary_hot_leg_temp'].append(primary_conditions['sg_1_inlet_temp'])
            self.history['integration']['primary_cold_leg_temp'].append(primary_conditions['sg_1_outlet_temp'])
            self.history['integration']['heat_removal_rate'].append(primary_result['thermal_power_mw'])
            self.history['integration']['overall_plant_efficiency'].append(secondary_result['thermal_efficiency'])
            self.history['integration']['coupling_factor'].append(getattr(self, '_last_heat_removal_factor', 1.0))
        else:
            # Add default values when secondary system is not enabled
            self.history['secondary']['electrical_power'].append(0.0)
            self.history['secondary']['thermal_efficiency'].append(0.0)
            self.history['secondary']['total_steam_flow'].append(0.0)
            self.history['secondary']['sg_avg_pressure'].append(0.0)
            self.history['secondary']['sg_avg_temperature'].append(0.0)
            self.history['secondary']['condenser_pressure'].append(0.0)
            self.history['secondary']['condenser_temperature'].append(0.0)
            self.history['secondary']['turbine_power'].append(0.0)
            self.history['secondary']['generator_power'].append(0.0)
            self.history['secondary']['feedwater_flow'].append(0.0)
            self.history['secondary']['feedwater_temperature'].append(0.0)
            self.history['secondary']['cooling_water_temperature'].append(self.cooling_water_temp)
            self.history['secondary']['cooling_water_flow'].append(0.0)
            self.history['secondary']['load_demand'].append(self.load_demand)
            self.history['secondary']['vacuum_pump_operation'].append(0.0)
            self.history['integration']['primary_hot_leg_temp'].append(self.state.coolant_temperature)
            self.history['integration']['primary_cold_leg_temp'].append(self.state.coolant_temperature)
            self.history['integration']['heat_removal_rate'].append(primary_result['thermal_power_mw'])
            self.history['integration']['overall_plant_efficiency'].append(0.0)
            self.history['integration']['coupling_factor'].append(1.0)

        # Prepare return information
        info = {
            "time": self.time,
            "thermal_power": primary_result['thermal_power_mw'],
            "scram_activated": primary_result['scram_activated'],
            "reactivity": primary_result['total_reactivity_pcm'],
            "reactivity_components": primary_result['reactivity_components'],
        }
        
        # Add secondary system information if available
        if secondary_result is not None:
            # Calculate realistic thermal efficiency with robust error handling
            thermal_power_mw = primary_result['thermal_power_mw']
            electrical_power_mw = secondary_result['electrical_power_mw']
            
            # Robust efficiency calculation with NaN/Inf checking
            if (thermal_power_mw > 10.0 and 
                np.isfinite(thermal_power_mw) and 
                np.isfinite(electrical_power_mw) and 
                electrical_power_mw >= 0):
                realistic_efficiency = electrical_power_mw / thermal_power_mw
                # Cap efficiency at reasonable values (max 40% for nuclear plants)
                realistic_efficiency = min(max(realistic_efficiency, 0.0), 0.40)
            else:
                realistic_efficiency = 0.0  # No efficiency when reactor is shut down or invalid values
            
            # Validate all secondary system values before using them
            electrical_power = secondary_result['electrical_power_mw'] if np.isfinite(secondary_result['electrical_power_mw']) else 0.0
            steam_flow = secondary_result['total_steam_flow'] if np.isfinite(secondary_result['total_steam_flow']) else 1665.0
            steam_pressure = secondary_result['sg_avg_pressure'] if np.isfinite(secondary_result['sg_avg_pressure']) else 6.895
            condenser_pressure = secondary_result['condenser_pressure'] if np.isfinite(secondary_result['condenser_pressure']) else 0.007
            
            info.update({
                "electrical_power": electrical_power,
                "thermal_efficiency": realistic_efficiency,
                "steam_flow": steam_flow,
                "steam_pressure": steam_pressure,
                "condenser_pressure": condenser_pressure,
                "secondary_system": secondary_result
            })

        # Return step information
        return {
            "observation": observation,
            "reward": self.calculate_reward(secondary_result),
            "done": primary_result['scram_activated'],
            "info": info,
        }
    
    def _convert_action_to_control_inputs(self, action: Optional[ControlAction], magnitude: float) -> dict:
        """Convert single action to control inputs format for primary physics"""
        control_inputs = {
            'control_rod_action': ControlAction.NO_ACTION,
            'control_rod_magnitude': 0.0,
            'coolant_flow_action': ControlAction.NO_ACTION,
            'coolant_flow_magnitude': 0.0,
            'boron_action': ControlAction.NO_ACTION,
            'boron_magnitude': 0.0,
            'steam_valve_action': ControlAction.NO_ACTION,
            'steam_valve_magnitude': 0.0,
            'primary_action': action if action is not None else ControlAction.NO_ACTION
        }
        
        if action is not None:
            if action in [ControlAction.CONTROL_ROD_INSERT, ControlAction.CONTROL_ROD_WITHDRAW]:
                control_inputs['control_rod_action'] = action
                control_inputs['control_rod_magnitude'] = magnitude
            elif action in [ControlAction.INCREASE_COOLANT_FLOW, ControlAction.DECREASE_COOLANT_FLOW]:
                control_inputs['coolant_flow_action'] = action
                control_inputs['coolant_flow_magnitude'] = magnitude
            elif action in [ControlAction.DILUTE_BORON, ControlAction.BORATE_COOLANT]:
                control_inputs['boron_action'] = action
                control_inputs['boron_magnitude'] = magnitude
            elif action in [ControlAction.OPEN_STEAM_VALVE, ControlAction.CLOSE_STEAM_VALVE]:
                control_inputs['steam_valve_action'] = action
                control_inputs['steam_valve_magnitude'] = magnitude
        
        return control_inputs

    def get_observation(self) -> np.ndarray:
        """Get current state as observation vector for RL"""
        # Base primary system observations
        primary_obs = [
            self.state.neutron_flux / 1e12,  # Normalized flux
            self.state.fuel_temperature / 1000,  # Normalized temperature
            self.state.coolant_temperature / 300,
            self.state.coolant_pressure / 20,
            self.state.coolant_flow_rate / 50000,
            self.state.steam_temperature / 300,
            self.state.steam_pressure / 10,
            self.state.steam_flow_rate / 3000,
            self.state.control_rod_position / 100,
            self.state.steam_valve_position / 100,
            self.state.power_level / 100,
            float(self.state.scram_status),
        ]
        
        # Add secondary system observations if available
        if self.enable_secondary and self.secondary_physics is not None:
            # Get secondary system state
            secondary_state = self.secondary_physics.get_system_state()
            
            secondary_obs = [
                secondary_state['electrical_power_output'] / 1100,  # Normalized electrical power
                secondary_state['thermal_efficiency'] / 0.35,  # Normalized efficiency
                secondary_state['total_steam_flow'] / 1665,  # Normalized steam flow
                secondary_state['load_demand'] / 100,  # Normalized load demand
                secondary_state['feedwater_temperature'] / 250,  # Normalized feedwater temp
                secondary_state['cooling_water_temperature'] / 35,  # Normalized cooling water temp
            ]
            
            return np.array(primary_obs + secondary_obs)
        
        return np.array(primary_obs)

    def _calculate_primary_to_secondary_coupling(self) -> dict:
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
        primary_thermal_power = self.state.power_level / 100.0 * 3000.0  # MW
        
        # Calculate primary coolant conditions based on reactor physics
        # Hot leg temperature should be based on fuel temperature and power level
        # Typical PWR: fuel temp ~600°C, coolant outlet (hot leg) ~327°C
        fuel_to_coolant_delta = 280.0  # Typical temperature difference between fuel and coolant
        primary_hot_leg_temp = max(self.state.fuel_temperature - fuel_to_coolant_delta, 280.0)
        
        # Ensure hot leg temperature is within realistic PWR operating range
        primary_hot_leg_temp = np.clip(primary_hot_leg_temp, 280.0, 340.0)
        
        # Heat removal in steam generators determines cold leg temperature
        # Q = m_dot * cp * (T_hot - T_cold)
        # Assuming total primary flow of 17,100 kg/s (typical PWR)
        total_primary_flow = 17100.0  # kg/s
        cp_primary = 5.2  # kJ/kg/K at PWR conditions
        
        # Calculate cold leg temperature based on heat removal
        heat_removed_mw = primary_thermal_power  # Assume all heat goes to steam generators
        if total_primary_flow > 0 and cp_primary > 0:
            delta_t_primary = heat_removed_mw * 1000.0 / (total_primary_flow * cp_primary)
        else:
            delta_t_primary = 34.0  # Default PWR temperature drop
        
        # Ensure reasonable temperature drop (typical PWR: 30-40°C)
        delta_t_primary = np.clip(delta_t_primary, 25.0, 50.0)
        
        primary_cold_leg_temp = primary_hot_leg_temp - delta_t_primary
        
        # Ensure cold leg temperature is within realistic PWR operating range
        primary_cold_leg_temp = np.clip(primary_cold_leg_temp, 260.0, 310.0)
        
        # Don't override the thermal hydraulics calculation - let it handle coolant temperature
        # The thermal hydraulics model already accounts for heat removal and thermal dynamics
        # Only use the calculated temperatures for secondary system interface
        pass
        
        # Calculate conditions for each steam generator loop
        primary_conditions = {}
        flow_per_loop = total_primary_flow / self.primary_loops
        
        for i in range(self.primary_loops):
            sg_key = f'sg_{i+1}'
            
            # Each steam generator sees the same inlet conditions
            primary_conditions[f'{sg_key}_inlet_temp'] = primary_hot_leg_temp
            primary_conditions[f'{sg_key}_outlet_temp'] = primary_cold_leg_temp
            primary_conditions[f'{sg_key}_flow'] = flow_per_loop
            
        return primary_conditions
    
    def _apply_secondary_to_primary_feedback(self, secondary_result: dict) -> None:
        """
        Apply feedback from secondary to primary systems
        
        This includes:
        1. Steam demand affecting primary heat removal
        2. Feedwater temperature affecting steam generator performance
        3. Load demand affecting overall plant operation
        
        Args:
            secondary_result: Results from secondary system update
        """
        # Steam demand affects primary heat removal rate
        steam_demand = secondary_result['total_steam_flow']  # kg/s
        
        # Higher steam demand -> more heat removal -> lower primary temperature
        # This is a simplified feedback model
        heat_removal_factor = steam_demand / 1665.0  # Normalize to design flow
        
        # Electrical load affects steam demand
        electrical_load = secondary_result['electrical_power_mw']
        load_factor = electrical_load / 1100.0  # Normalize to design power
        
        # Apply simplified feedback (in a real plant this would be more complex)
        # For now, we just store the feedback factors for potential future use
        self._last_heat_removal_factor = heat_removal_factor
        self._last_load_factor = load_factor

    def calculate_reward(self, secondary_result: dict = None) -> float:
        """Calculate reward for RL training with optional secondary system performance"""
        # Target power level around 100%
        power_error = abs(self.state.power_level - 100)
        power_reward = -power_error / 100

        # Temperature stability
        temp_penalty = 0
        if self.state.fuel_temperature > 800:
            temp_penalty = -(self.state.fuel_temperature - 800) / 100

        # Pressure stability
        pressure_penalty = 0
        if self.state.coolant_pressure > 16:
            pressure_penalty = -(self.state.coolant_pressure - 16)

        # Scram penalty
        scram_penalty = -100 if self.state.scram_status else 0

        base_reward = power_reward + temp_penalty + pressure_penalty + scram_penalty
        
        # Add secondary system performance if available
        if secondary_result is not None:
            # Efficiency reward - higher efficiency is better
            efficiency_reward = (secondary_result['thermal_efficiency'] - 0.30) * 10  # Normalize around 30% efficiency
            
            # Electrical power stability reward
            target_electrical_power = self.load_demand / 100.0 * 1100.0  # MW
            electrical_error = abs(secondary_result['electrical_power_mw'] - target_electrical_power)
            electrical_reward = -electrical_error / 100
            
            # Steam system stability
            steam_pressure_penalty = 0
            if secondary_result['sg_avg_pressure'] < 5.0 or secondary_result['sg_avg_pressure'] > 8.0:
                steam_pressure_penalty = -abs(secondary_result['sg_avg_pressure'] - 6.895) * 5
            
            # Condenser performance
            condenser_penalty = 0
            if secondary_result['condenser_pressure'] > 0.01:  # Poor vacuum
                condenser_penalty = -(secondary_result['condenser_pressure'] - 0.007) * 100
            
            secondary_reward = efficiency_reward + electrical_reward + steam_pressure_penalty + condenser_penalty
            return base_reward + secondary_reward * 0.5  # Weight secondary performance at 50%
        
        return base_reward

    def reset(self):
        """Reset simulation to initial conditions"""
        self.primary_physics.reset_system()
        if self.enable_secondary and self.secondary_physics is not None:
            self.secondary_physics.reset_system()
        
        self.state = self.primary_physics.state
        self.time = 0.0
        # Reset history by clearing all lists in the hierarchical structure
        self.history['time'] = []
        for category in ['primary', 'secondary', 'integration']:
            for key in self.history[category]:
                self.history[category][key] = []
        
        # Reset control parameters
        self.load_demand = 100.0
        self.cooling_water_temp = 25.0
        
        return self.get_observation()

    def plot_parameters(self, parameters: List[str] = None, time_window: int = None):
        """Plot selected parameters over time using hierarchical history structure"""
        if not self.history['time']:
            print("No simulation data to plot")
            return

        if parameters is None:
            parameters = [
                "primary.power_level",
                "primary.fuel_temperature", 
                "primary.coolant_temperature",
                "primary.coolant_pressure",
                "primary.control_rod_position",
            ]

        # Get time data
        time_data = np.array(self.history['time'])
        if time_window:
            time_data = time_data[-time_window:]

        fig, axes = plt.subplots(len(parameters), 1, figsize=(12, 3 * len(parameters)))
        if len(parameters) == 1:
            axes = [axes]

        for i, param in enumerate(parameters):
            # Parse hierarchical parameter name (e.g., "primary.power_level")
            if '.' in param:
                category, param_name = param.split('.', 1)
                if category in self.history and param_name in self.history[category]:
                    data = np.array(self.history[category][param_name])
                    if time_window:
                        data = data[-time_window:]
                    
                    # Create readable labels
                    ylabel = param_name.replace('_', ' ').title()
                    if 'temperature' in param_name.lower():
                        ylabel += " (°C)"
                    elif 'pressure' in param_name.lower():
                        ylabel += " (MPa)"
                    elif 'power' in param_name.lower() or 'level' in param_name.lower():
                        ylabel += " (%)" if 'level' in param_name.lower() else " (MW)"
                    elif 'position' in param_name.lower():
                        ylabel += " (%)"
                    elif 'flow' in param_name.lower():
                        ylabel += " (kg/s)"
                    elif 'efficiency' in param_name.lower():
                        ylabel += " (%)"
                        data = data * 100  # Convert to percentage
                    
                    axes[i].plot(time_data, data, linewidth=2)
                    axes[i].set_ylabel(ylabel)
                    axes[i].grid(True, alpha=0.3)
                    axes[i].set_title(f"{category.title()} - {ylabel}")
                else:
                    print(f"Parameter {param} not found in history")
            else:
                # Handle legacy parameter names for backward compatibility
                if param in self.history['primary']:
                    data = np.array(self.history['primary'][param])
                    if time_window:
                        data = data[-time_window:]
                    
                    ylabel = param.replace('_', ' ').title()
                    axes[i].plot(time_data, data, linewidth=2)
                    axes[i].set_ylabel(ylabel)
                    axes[i].grid(True, alpha=0.3)
                else:
                    print(f"Parameter {param} not found in primary history")

        axes[-1].set_xlabel("Time (s)")
        plt.tight_layout()
        plt.show()


# Example usage and testing
def run_simulation_example():
    """Example of running the integrated nuclear plant simulation"""
    print("Integrated Nuclear Power Plant Digital Twin Simulation")
    print("=" * 60)

    # Create simulator with integrated primary-secondary physics
    sim = NuclearPlantSimulator(dt=1.0, enable_secondary=True)
    sim.primary_physics.state = create_equilibrium_state()

    print("System Configuration:")
    print(f"  Primary Reactor: 3000 MW thermal")
    print(f"  Steam Generators: 3 units")
    print(f"  Secondary System: Enabled")
    print(f"  Observation Space: {len(sim.get_observation())} parameters")
    print()

    # Run simulation with some control actions and load changes
    print("Running integrated simulation with control actions and load changes...")
    print(f"{'Time':<6} {'Primary %':<10} {'Electrical MW':<12} {'Efficiency %':<12} {'Load %':<8} {'Action':<20}")
    print("-" * 78)

    for t in range(300):  # 5 minutes
        # Define control actions
        if t == 60:  # At 1 minute, withdraw control rods
            action = ControlAction.CONTROL_ROD_WITHDRAW
            action_name = "Rod Withdraw"
        elif t == 120:  # At 2 minutes, reduce load
            action = ControlAction.CONTROL_ROD_WITHDRAW
            action_name = "Rod Withdraw"
        elif t == 180:  # At 3 minutes, insert control rods
            action = ControlAction.NO_ACTION
            action_name = "Load Reduction"
        elif t == 240:  # At 4 minutes, increase coolant flow
            action = ControlAction.INCREASE_COOLANT_FLOW
            action_name = "Coolant Flow Up"
        else:
            action = ControlAction.NO_ACTION
            action_name = "No Action"

        # Define load demand profile
        if t < 60:
            load_demand = 100.0
        elif t < 120:
            load_demand = 100.0
        elif t < 180:
            load_demand = 100.  # Load reduction
        elif t < 240:
            load_demand = 100.0
        else:
            load_demand = 100.0  # Load increase

        # Step simulation with integrated physics
        result = sim.step(action, load_demand=load_demand, cooling_water_temp=25.0)

        # Print status every 30 seconds
        if t % 30 == 0:
            electrical_power = result['info'].get('electrical_power', 0.0)
            thermal_efficiency = result['info'].get('thermal_efficiency', 0.0) * 100
            
            print(f"{t:<6} {sim.state.power_level:<10.1f} "
                  f"{electrical_power:<12.1f} "
                  f"{thermal_efficiency:<12.2f} "
                  f"{load_demand:<8.0f} "
                  f"{action_name:<20}")

    print(f"\nSimulation completed. Final state:")
    print(f"  Primary Power Level: {sim.state.power_level:.1f}%")
    
    if 'electrical_power' in result['info']:
        print(f"  Electrical Power Output: {result['info']['electrical_power']:.1f} MW")
        print(f"  Thermal: Efficiency: {result['info']['thermal_efficiency']*100:.2f}%")
        print(f"  Steam Flow Rate: {result['info']['steam_flow']:.0f} kg/s")
        print(f"  Steam Pressure: {result['info']['steam_pressure']:.2f} MPa")
        print(f"  Condenser Pressure: {result['info']['condenser_pressure']:.4f} MPa")

    # Plot results
    sim.plot_parameters(
        [
            "power_level",
            "fuel_temperature",
            "coolant_temperature",
            "control_rod_position",
        ]
    )

    return sim


# RL Environment wrapper
class NuclearPlantEnv:
    """Gym-style environment wrapper for RL training"""

    def __init__(self, enable_secondary: bool = True):
        self.sim = NuclearPlantSimulator(enable_secondary=enable_secondary)
        self.action_space_size = len(ControlAction)
        # Dynamic observation space size based on secondary system
        self.observation_space_size = 18 if enable_secondary else 12

    def step(self, action_idx: int, load_demand: float = None, cooling_water_temp: float = None):
        action = ControlAction(action_idx)
        result = self.sim.step(action, load_demand=load_demand, cooling_water_temp=cooling_water_temp)
        return (result["observation"], result["reward"], result["done"], result["info"])

    def reset(self):
        return self.sim.reset()

    def render(self):
        info_str = (f"Time: {self.sim.time:6.1f}s | Power: {self.sim.state.power_level:6.1f}% | "
                   f"Fuel Temp: {self.sim.state.fuel_temperature:6.1f}°C")
        
        # Add secondary system info if available
        if self.sim.enable_secondary and hasattr(self.sim, '_last_load_factor'):
            info_str += f" | Load: {self.sim.load_demand:5.1f}%"
        
        print(info_str)


if __name__ == "__main__":
    # Run the example simulation
    simulator = run_simulation_example()
