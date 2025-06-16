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

# Import the new state management system
from simulator.state import StateManager, StateProvider, StateVariable, StateCategory

warnings.filterwarnings("ignore")


class NuclearPlantSimulator:
    """Physics-based nuclear power plant simulator with integrated primary and secondary systems"""

    def __init__(self, dt: float = 1.0, heat_source=None, enable_secondary: bool = True, 
                 enable_state_management: bool = True, max_state_rows: int = 100000):
        self.dt = dt  # Time step in seconds
        self.time = 0.0
        self.enable_state_management = enable_state_management
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
        
        # Initialize state management system
        if self.enable_state_management:
            self.state_manager = StateManager(max_rows=max_state_rows, auto_manage_memory=True)
            
            # Register physics systems as state providers
            self.state_manager.register_provider(self.primary_physics, "primary")
            if self.enable_secondary and self.secondary_physics is not None:
                self.state_manager.register_provider(self.secondary_physics, "secondary")
            
            print(f"State management initialized: {self.state_manager}")
        else:
            self.state_manager = None
        
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
        
        # TODO: This is awful code
        self.state = self.primary_physics.state
        
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
        
        # Collect states using the new state management system
        if self.enable_state_management and self.state_manager is not None:
            try:
                collected_states = self.state_manager.collect_states(self.time)
            except Exception as e:
                warnings.warn(f"State collection failed: {e}")
        
        # Get observation for RL
        observation = self.get_observation()

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
            # Use the realistic thermal efficiency calculated by the secondary system
            # This eliminates the dual calculation problem and ensures consistency
            
            # Validate all secondary system values before using them
            electrical_power = secondary_result['electrical_power_mw'] if np.isfinite(secondary_result['electrical_power_mw']) else 0.0
            thermal_efficiency = secondary_result['thermal_efficiency'] if np.isfinite(secondary_result['thermal_efficiency']) else 0.0
            steam_flow = secondary_result['total_steam_flow'] if np.isfinite(secondary_result['total_steam_flow']) else 1665.0
            steam_pressure = secondary_result['sg_avg_pressure'] if np.isfinite(secondary_result['sg_avg_pressure']) else 6.895
            condenser_pressure = secondary_result['condenser_pressure'] if np.isfinite(secondary_result['condenser_pressure']) else 0.007
            condenser_heat_rejection = secondary_result['condenser_heat_rejection'] if np.isfinite(secondary_result['condenser_heat_rejection']) else 0.0
            
            # Additional validation: ensure thermal efficiency is within realistic bounds
            thermal_efficiency = max(0.0, min(thermal_efficiency, 0.35))  # Cap at 35% for PWR
            
            info.update({
                "electrical_power": electrical_power,
                "thermal_efficiency": thermal_efficiency,
                "steam_flow": steam_flow,
                "steam_pressure": steam_pressure,
                "condenser_pressure": condenser_pressure,
                "condenser_heat_rejection": condenser_heat_rejection,  # Energy-balance-corrected value
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
            
            # Add feedwater pump observations
            feedwater_state = secondary_state.get('feedwater_state', {})
            feedwater_obs = [
                feedwater_state.get('feedwater_total_flow', 0.0) / 1665,  # Normalized feedwater flow
                feedwater_state.get('feedwater_total_power', 0.0) / 40,  # Normalized pump power (4 pumps * 10MW each)
                float(feedwater_state.get('feedwater_system_availability', False)),  # System availability (0 or 1)
                feedwater_state.get('feedwater_total_flow', 0.0) / 1665,  # Normalized target flow (using actual flow as proxy)
            ]
            
            return np.array(primary_obs + secondary_obs + feedwater_obs)
        
        return np.array(primary_obs)

    def _calculate_primary_to_secondary_coupling(self) -> dict:
        """
        Calculate the coupling between primary and secondary systems
        
        This is the key integration point where:
        1. Primary thermal power is transferred to secondary via steam generators
        2. Primary coolant temperatures are calculated based on heat removal
        3. Secondary steam conditions are determined by primary heat input
        4. Feedwater pump status affects heat transfer capability
        
        Returns:
            Dictionary with coupling parameters for each steam generator
        """
        # Get primary thermal power from reactor physics
        primary_thermal_power = self.state.power_level / 100.0 * 3000.0  # MW
        
        # FIXED: Calculate realistic PWR hot leg and cold leg temperatures
        # Based on power level and realistic PWR operating conditions
        power_fraction = self.state.power_level / 100.0
        
        # Realistic PWR temperatures based on power level
        # At 100% power: Hot leg = 327°C, Cold leg = 293°C
        # At 0% power: Both approach cold leg temperature
        primary_hot_leg_temp = 293.0 + (34.0 * power_fraction)  # 293°C to 327°C
        primary_cold_leg_temp = 293.0  # Cold leg stays relatively constant
        
        # NOTE: Feedwater pump effects on primary temperatures are now handled
        # through the physically accurate steam generator level mechanism.
        # The steam generator heat transfer area is reduced when water level drops
        # due to feedwater pump failures, which naturally leads to higher primary
        # temperatures through reduced heat removal capability.
        
        # Ensure temperatures are within realistic PWR operating range
        primary_hot_leg_temp = np.clip(primary_hot_leg_temp, 293.0, 350.0)
        primary_cold_leg_temp = np.clip(primary_cold_leg_temp, 280.0, 300.0)
        
        # Ensure hot leg is always hotter than cold leg
        if primary_hot_leg_temp <= primary_cold_leg_temp:
            primary_hot_leg_temp = primary_cold_leg_temp + 5.0  # Minimum 5°C difference
        
        # Calculate realistic primary flow based on power level
        # Typical PWR: 17,100 kg/s total flow at 100% power
        design_flow = 17100.0  # kg/s
        # Flow varies with power level (reactor coolant pumps may be load-following)
        flow_fraction = max(0.3, power_fraction)  # Minimum 30% flow even at low power
        total_primary_flow = design_flow * flow_fraction
        
        # NOTE: Primary flow is no longer directly affected by feedwater pump status.
        # The effect now occurs naturally through steam generator level changes
        # affecting heat transfer area and thus heat removal capability.
        
        # Validate heat balance: Q = m_dot * cp * delta_T
        cp_primary = 5.2  # kJ/kg/K at PWR conditions
        calculated_thermal_power = (total_primary_flow * cp_primary * 
                                   (primary_hot_leg_temp - primary_cold_leg_temp)) / 1000.0  # MW
        
        # Debug output for troubleshooting
        '''
        print(f"DEBUG: Primary-Secondary Coupling:")
        print(f"  Power Level: {self.state.power_level:.1f}%")
        print(f"  Hot Leg Temp: {primary_hot_leg_temp:.1f}°C")
        print(f"  Cold Leg Temp: {primary_cold_leg_temp:.1f}°C")
        print(f"  Temperature Delta: {primary_hot_leg_temp - primary_cold_leg_temp:.1f}°C")
        print(f"  Primary Flow: {total_primary_flow:.0f} kg/s")
        print(f"  Calculated Thermal Power: {calculated_thermal_power:.1f} MW")
        print(f"  Target Thermal Power: {primary_thermal_power:.1f} MW")
        print(f"  Feedwater System Available: {feedwater_system_available}")
        print(f"  Feedwater Pumps Running: {feedwater_num_pumps}")
        '''
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
        4. Feedwater pump status affecting steam generator level control
        5. Feedwater pump availability affecting plant operation
        
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
        
        # Feedwater pump feedback effects
        feedwater_system_available = secondary_result.get('feedwater_system_available', True)
        feedwater_flow_rate = secondary_result.get('feedwater_total_flow', 1665.0)
        feedwater_num_pumps = secondary_result.get('feedwater_num_running_pumps', 3)
        
        # Feedwater pump availability affects steam generator level control
        # If feedwater pumps are unavailable, this affects heat removal capability
        if not feedwater_system_available:
            # Reduce effective heat removal when feedwater system is unavailable
            heat_removal_factor *= 0.5  # 50% reduction in heat removal capability
            
        # Feedwater flow rate affects steam generator performance
        # Mismatch between feedwater flow and steam demand affects SG level
        feedwater_flow_factor = feedwater_flow_rate / 1665.0  # Normalize to design
        
        # Number of running pumps affects system reliability
        pump_reliability_factor = min(1.0, feedwater_num_pumps / 3.0)  # Normalize to 3 pumps
        
        # CRITICAL FIX: Update primary system steam flow rate with secondary system's calculated value
        # This ensures that simulator.state.steam_flow_rate reflects the actual steam demand
        self.state.steam_flow_rate = steam_demand
        
        # Update primary system state with feedwater pump feedback
        if hasattr(self.state, 'feedwater_pump_status'):
            self.state.feedwater_pump_status = feedwater_system_available
        if hasattr(self.state, 'feedwater_pump_speed'):
            # Estimate average pump speed from flow rate
            if feedwater_flow_rate > 0:
                estimated_speed = min(100.0, (feedwater_flow_rate / 1665.0) * 100.0)
                self.state.feedwater_pump_speed = estimated_speed
            else:
                self.state.feedwater_pump_speed = 0.0
        if hasattr(self.state, 'feedwater_system_available'):
            self.state.feedwater_system_available = feedwater_system_available
        if hasattr(self.state, 'feedwater_pump_power'):
            self.state.feedwater_pump_power = secondary_result.get('feedwater_total_power', 0.0)
        if hasattr(self.state, 'feedwater_num_running_pumps'):
            self.state.feedwater_num_running_pumps = feedwater_num_pumps
        
        # Apply simplified feedback (in a real plant this would be more complex)
        # Store feedback factors for potential future use
        self._last_heat_removal_factor = heat_removal_factor
        self._last_load_factor = load_factor
        self._last_feedwater_flow_factor = feedwater_flow_factor
        self._last_pump_reliability_factor = pump_reliability_factor

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
        
        # Reset state management system
        if self.enable_state_management and self.state_manager is not None:
            self.state_manager.clear_data()
        
        # Reset control parameters
        self.load_demand = 100.0
        self.cooling_water_temp = 25.0
        
        return self.get_observation()

    def plot_parameters(self, parameters: List[str] = None, time_window: int = None):
        """Plot selected parameters over time using state management data"""
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot plot parameters.")
            return
        
        if self.state_manager.data.empty:
            print("No simulation data to plot")
            return

        if parameters is None:
            # Default parameters to plot
            available_vars = self.get_available_state_variables()
            parameters = []
            
            # Try to find common parameters
            for var in available_vars:
                if any(param in var.lower() for param in ['power_level', 'fuel_temperature', 'coolant_temperature', 'control_rod']):
                    parameters.append(var)
                if len(parameters) >= 4:  # Limit to 4 plots
                    break
            
            if not parameters:
                parameters = available_vars[:4]  # Just take first 4 if no common ones found

        # Get time series data
        try:
            time_range = None
            if time_window:
                max_time = self.state_manager.data['time'].max()
                min_time = max_time - time_window
                time_range = (min_time, max_time)
            
            data = self.state_manager.get_time_series(['time'] + parameters, time_range)
            
            if data.empty:
                print("No data available for plotting")
                return
            
            # Create plots
            fig, axes = plt.subplots(len(parameters), 1, figsize=(12, 3 * len(parameters)))
            if len(parameters) == 1:
                axes = [axes]

            for i, param in enumerate(parameters):
                if param in data.columns:
                    # Create readable labels
                    ylabel = param.replace('_', ' ').replace('.', ' ').title()
                    if 'temperature' in param.lower():
                        ylabel += " (°C)"
                    elif 'pressure' in param.lower():
                        ylabel += " (MPa)"
                    elif 'power' in param.lower() or 'level' in param.lower():
                        ylabel += " (%)" if 'level' in param.lower() else " (MW)"
                    elif 'position' in param.lower():
                        ylabel += " (%)"
                    elif 'flow' in param.lower():
                        ylabel += " (kg/s)"
                    elif 'efficiency' in param.lower():
                        ylabel += " (%)"
                        data[param] = data[param] * 100  # Convert to percentage
                    
                    axes[i].plot(data['time'], data[param], linewidth=2)
                    axes[i].set_ylabel(ylabel)
                    axes[i].grid(True, alpha=0.3)
                    axes[i].set_title(ylabel)
                else:
                    print(f"Parameter {param} not found in data")

            axes[-1].set_xlabel("Time (s)")
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"Error plotting parameters: {e}")

    # State Management Methods
    def export_state_data(self, filename: str, time_range: Optional[Tuple[float, float]] = None,
                         variables: Optional[List[str]] = None) -> None:
        """
        Export state data to CSV using the new state management system.
        
        Args:
            filename: Output CSV filename
            time_range: Optional tuple of (start_time, end_time) to filter data
            variables: Optional list of variables to include (default: all)
        """
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot export state data.")
            return
        
        self.state_manager.export_to_csv(filename, time_range, variables)

    def export_state_data_by_category(self, category: str, filename: str,
                                    time_range: Optional[Tuple[float, float]] = None) -> None:
        """
        Export state data for a specific category (e.g., 'primary', 'secondary').
        
        Args:
            category: Category name
            filename: Output CSV filename
            time_range: Optional time range filter
        """
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot export state data.")
            return
        
        self.state_manager.export_by_category(category, filename, time_range)

    def export_state_data_by_subcategory(self, category: str, subcategory: str, filename: str,
                                       time_range: Optional[Tuple[float, float]] = None) -> None:
        """
        Export state data for a specific subcategory (e.g., 'primary.neutronics').
        
        Args:
            category: Category name
            subcategory: Subcategory name
            filename: Output CSV filename
            time_range: Optional time range filter
        """
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot export state data.")
            return
        
        self.state_manager.export_by_subcategory(category, subcategory, filename, time_range)

    def export_state_summary_statistics(self, filename: str) -> None:
        """
        Export statistical summary of all state variables.
        
        Args:
            filename: Output CSV filename for summary statistics
        """
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot export summary statistics.")
            return
        
        self.state_manager.export_summary_statistics(filename)

    def get_state_data_info(self) -> Dict[str, any]:
        """
        Get information about the collected state data.
        
        Returns:
            Dictionary with dataset information
        """
        if not self.enable_state_management or self.state_manager is None:
            return {
                'state_management_enabled': False,
                'message': 'State management is not enabled'
            }
        
        info = self.state_manager.get_data_info()
        info['state_management_enabled'] = True
        return info

    def get_available_state_variables(self) -> List[str]:
        """
        Get list of all available state variables.
        
        Returns:
            List of variable names
        """
        if not self.enable_state_management or self.state_manager is None:
            return []
        
        return self.state_manager.get_available_variables()

    def get_available_state_categories(self) -> List[str]:
        """
        Get list of all available state categories.
        
        Returns:
            List of category names
        """
        if not self.enable_state_management or self.state_manager is None:
            return []
        
        return self.state_manager.get_available_categories()

    def get_state_variable_history(self, variable_name: str,
                                 time_range: Optional[Tuple[float, float]] = None):
        """
        Get time series for a specific state variable.
        
        Args:
            variable_name: Name of the variable
            time_range: Optional tuple of (start_time, end_time) to filter data
            
        Returns:
            pandas Series with the variable's time series data
        """
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot retrieve variable history.")
            return None
        
        return self.state_manager.get_variable_history(variable_name, time_range)

    def get_state_time_series(self, variable_names: List[str],
                            time_range: Optional[Tuple[float, float]] = None):
        """
        Get time series DataFrame for multiple state variables.
        
        Args:
            variable_names: List of variable names to include
            time_range: Optional tuple of (start_time, end_time) to filter data
            
        Returns:
            pandas DataFrame with time and selected variables
        """
        if not self.enable_state_management or self.state_manager is None:
            print("State management is not enabled. Cannot retrieve time series.")
            return None
        
        return self.state_manager.get_time_series(variable_names, time_range)


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
            load_demand = 70.  # Load reduction
        elif t < 240:
            load_demand = 70.0
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
        print(f"  Thermal Efficiency: {result['info']['thermal_efficiency']*100:.2f}%")
        print(f"  Steam Flow Rate: {result['info']['steam_flow']:.0f} kg/s")
        print(f"  Steam Pressure: {result['info']['steam_pressure']:.2f} MPa")
        print(f"  Condenser Pressure: {result['info']['condenser_pressure']:.4f} MPa")

    # Demonstrate new state management capabilities
    if sim.enable_state_management:
        print(f"\nState Management System:")
        state_info = sim.get_state_data_info()
        print(f"  Total rows collected: {state_info['total_rows']}")
        print(f"  Total variables: {state_info['total_variables']}")
        print(f"  Available categories: {state_info['categories']}")
        print(f"  Memory usage: {state_info['memory_usage_mb']:.1f} MB")
        print(f"  Average collection time: {state_info['avg_collection_time_ms']:.2f} ms")
        
        # Export examples
        print(f"\nExporting state data...")
        sim.export_state_data("simulation_complete_data.csv")
        sim.export_state_data_by_category("primary", "simulation_primary_data.csv")
        sim.export_state_data_by_category("secondary", "simulation_secondary_data.csv")
        sim.export_state_summary_statistics("simulation_summary_stats.csv")
        
        print(f"  Available variables: {len(sim.get_available_state_variables())}")
        print(f"  Available categories: {sim.get_available_state_categories()}")

    # Plot results using state management data
    sim.plot_parameters()

    return sim


# RL Environment wrapper
class NuclearPlantEnv:
    """Gym-style environment wrapper for RL training"""

    def __init__(self, enable_secondary: bool = True):
        self.sim = NuclearPlantSimulator(enable_secondary=enable_secondary)
        self.action_space_size = len(ControlAction)
        # Dynamic observation space size based on secondary system
        # Primary: 12 observations
        # Secondary: 6 observations  
        # Feedwater pumps: 4 observations
        # Total: 12 + 6 + 4 = 22 observations when secondary is enabled
        self.observation_space_size = 22 if enable_secondary else 12

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
