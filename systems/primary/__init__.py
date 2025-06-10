"""
Primary Reactor Physics System

This module provides the integrated primary reactor physics system for PWR plants,
combining neutronics, thermal hydraulics, and safety systems into a complete primary side model.
"""

from .reactor.physics.neutronics import NeutronicsModel
from .reactor.physics.thermal_hydraulics import ThermalHydraulicsModel
from .reactor.safety.scram_logic import ScramSystem
from .reactor.heat_sources import ReactorHeatSource

# Import reactor state and control actions from sim.py for now
# These will be moved here eventually
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np

warnings.filterwarnings("ignore")


class ControlAction(Enum):
    """Available control actions for the RL agent"""

    CONTROL_ROD_INSERT = 0
    CONTROL_ROD_WITHDRAW = 1
    INCREASE_COOLANT_FLOW = 2
    DECREASE_COOLANT_FLOW = 3
    OPEN_STEAM_VALVE = 4
    CLOSE_STEAM_VALVE = 5
    INCREASE_FEEDWATER = 6
    DECREASE_FEEDWATER = 7
    NO_ACTION = 8
    DILUTE_BORON = 9  # Reduce boron concentration (add reactivity)
    BORATE_COOLANT = 10  # Add boron concentration (reduce reactivity)


@dataclass
class ReactorState:
    """Current state of the reactor system"""

    # Neutronics
    neutron_flux: float = 1e13  # neutrons/cm²/s (100% power)
    reactivity: float = 0.0  # delta-k/k (critical)
    delayed_neutron_precursors: Optional[np.ndarray] = None

    # Thermal hydraulics
    fuel_temperature: float = 575.0  # °C (realistic steady-state average)
    coolant_temperature: float = 280.0  # °C
    coolant_pressure: float = 15.5  # MPa
    coolant_flow_rate: float = 20000.0  # kg/s
    coolant_void_fraction: float = 0.0  # Steam void fraction (0-1)

    # Steam cycle
    steam_temperature: float = 285.0  # °C
    steam_pressure: float = 7.0  # MPa
    steam_flow_rate: float = 1000.0  # kg/s
    feedwater_flow_rate: float = 1000.0  # kg/s

    # Control systems
    control_rod_position: float = (
        95.0  # % withdrawn (PWR normal operation - rods mostly out)
    )
    steam_valve_position: float = 50.0  # % open    
    boron_concentration: float = 12000.0  # ppm

    # Fission product poisons - start deeply subcritical
    xenon_concentration: float = 2.8e15  # atoms/cm³
    iodine_concentration: float = 1.5e16  # atoms/cm³
    samarium_concentration: float = 1.0e15  # atoms/cm³

    # Burnable poisons and fuel depletion
    burnable_poison_worth: float = 0.0  # pcm
    fuel_burnup: float = 15000.0  # MWd/MTU

    # Safety parameters
    power_level: float = 100.0  # % rated power
    scram_status: bool = False

    def __post_init__(self):
        if self.delayed_neutron_precursors is None:
            # 6 delayed neutron precursor groups
            self.delayed_neutron_precursors = np.array(
                [0.0002, 0.0011, 0.0010, 0.0030, 0.0096, 0.0003]
            )


__all__ = [
    'NeutronicsModel',
    'ThermalHydraulicsModel',
    'ScramSystem',
    'ReactorHeatSource',
    'PrimaryReactorPhysics',
    'ReactorState',
    'ControlAction'
]


class PrimaryReactorPhysics:
    """
    Integrated primary reactor physics system
    
    This class combines neutronics, thermal hydraulics, and safety systems to model
    the complete primary side of a PWR nuclear power plant.
    
    The system models:
    1. Neutron kinetics and reactivity feedback mechanisms
    2. Heat generation and thermal hydraulic behavior
    3. Control rod dynamics and boron chemistry effects
    4. Safety system monitoring and automatic scram logic
    5. Primary coolant system thermal hydraulics
    """
    
    def __init__(self, 
                 rated_power_mw: float = 3000.0,
                 heat_source=None,
                 neutronics_config=None,
                 thermal_hydraulics_config=None,
                 safety_config=None):
        """
        Initialize integrated primary reactor physics
        
        Args:
            rated_power_mw: Rated thermal power in MW
            heat_source: Heat source model (defaults to ReactorHeatSource)
            neutronics_config: Neutronics model configuration
            thermal_hydraulics_config: Thermal hydraulics configuration
            safety_config: Safety system configuration
        """
        self.rated_power_mw = rated_power_mw
        
        # Initialize component physics models
        if heat_source is not None:
            self.heat_source = heat_source
        else:
            self.heat_source = ReactorHeatSource(rated_power_mw=rated_power_mw)
        
        self.neutronics = NeutronicsModel()
        self.thermal_hydraulics = ThermalHydraulicsModel()
        self.scram_system = ScramSystem()
        
        # System state variables
        self.state = ReactorState()
        self.thermal_power_mw = 0.0
        self.total_reactivity_pcm = 0.0
        self.scram_activated = False
        
        # Control parameters
        self.max_control_rod_speed = 5.0  # %/s
        self.max_valve_speed = 10.0  # %/s
        self.max_flow_change_rate = 1000.0  # kg/s/s
        
    def update_system(self,
                     control_inputs: dict,
                     dt: float) -> dict:
        """
        Update the complete primary system for one time step
        
        Args:
            control_inputs: Dictionary with control system inputs
                - 'control_rod_action': Control rod action (ControlAction enum)
                - 'control_rod_magnitude': Control rod action magnitude (0-1)
                - 'coolant_flow_action': Coolant flow action (ControlAction enum)
                - 'coolant_flow_magnitude': Coolant flow action magnitude (0-1)
                - 'boron_action': Boron concentration action (ControlAction enum)
                - 'boron_magnitude': Boron action magnitude (0-1)
                - 'steam_valve_action': Steam valve action (ControlAction enum)
                - 'steam_valve_magnitude': Steam valve action magnitude (0-1)
            dt: Time step (s)
            
        Returns:
            Dictionary with complete primary system state and performance
        """
        # Extract control inputs and apply actions
        self._apply_control_actions(control_inputs, dt)
        
        # Update heat source (handles neutronics and heat generation)
        heat_result = self.heat_source.update(
            dt=dt, 
            reactor_state=self.state, 
            control_action=control_inputs.get('primary_action', ControlAction.NO_ACTION)
        )
        
        # Extract heat source results
        self.thermal_power_mw = heat_result['thermal_power_mw']
        self.state.power_level = heat_result['power_percent']
        
        # Update neutron flux if provided
        if 'neutron_flux' in heat_result:
            self.state.neutron_flux = heat_result['neutron_flux']
        
        # Update reactivity if provided
        if 'reactivity_pcm' in heat_result:
            self.total_reactivity_pcm = heat_result['reactivity_pcm']
            self.state.reactivity = self.total_reactivity_pcm / 100000.0  # Convert to delta-k/k
        else:
            self.total_reactivity_pcm = 0.0
        
        # Get reactivity components if available
        reactivity_components = heat_result.get('reactivity_components', {})

        # Calculate thermal hydraulics based on heat source output
        thermal_power = self.thermal_power_mw * 1e6  # Convert to watts
        thermal_params = self.thermal_hydraulics.calculate_thermal_hydraulics(self.state, thermal_power)
        steam_params = self.thermal_hydraulics.calculate_steam_cycle(self.state)

        # Update thermal hydraulic state variables
        self.thermal_hydraulics.update_thermal_state(self.state, thermal_params, dt)

        # Update steam cycle parameters
        self.thermal_hydraulics.update_steam_state(self.state, steam_params, dt)

        # Check for NaN values and reset if necessary
        self.thermal_hydraulics.check_for_nan_values(self.state)

        # Check safety systems
        self.scram_activated = self.scram_system.check_safety_systems(self.state)
        
        # Compile complete system results
        system_result = {
            # Overall system performance
            'thermal_power_mw': self.thermal_power_mw,
            'power_level_percent': self.state.power_level,
            'total_reactivity_pcm': self.total_reactivity_pcm,
            'reactivity_components': reactivity_components,
            
            # Neutronics performance
            'neutron_flux': self.state.neutron_flux,
            'delayed_neutron_precursors': self.state.delayed_neutron_precursors.copy(),
            'xenon_concentration': self.state.xenon_concentration,
            'iodine_concentration': self.state.iodine_concentration,
            'samarium_concentration': self.state.samarium_concentration,
            
            # Thermal hydraulics performance
            'fuel_temperature': self.state.fuel_temperature,
            'coolant_temperature': self.state.coolant_temperature,
            'coolant_pressure': self.state.coolant_pressure,
            'coolant_flow_rate': self.state.coolant_flow_rate,
            'coolant_void_fraction': self.state.coolant_void_fraction,
            
            # Steam cycle interface
            'steam_temperature': self.state.steam_temperature,
            'steam_pressure': self.state.steam_pressure,
            'steam_flow_rate': self.state.steam_flow_rate,
            'feedwater_flow_rate': self.state.feedwater_flow_rate,
            
            # Control and operating conditions
            'control_rod_position': self.state.control_rod_position,
            'steam_valve_position': self.state.steam_valve_position,
            'boron_concentration': self.state.boron_concentration,
            
            # Safety parameters
            'scram_status': self.state.scram_status,
            'scram_activated': self.scram_activated,
            
            # Detailed component states
            'heat_source_state': getattr(self.heat_source, 'get_state', lambda: {})(),
            'neutronics_state': getattr(self.neutronics, 'get_state_dict', lambda: {})(),
            'thermal_hydraulics_state': getattr(self.thermal_hydraulics, 'get_state_dict', lambda: {})(),
            'safety_state': getattr(self.scram_system, 'get_state_dict', lambda: {})()
        }
        
        return system_result
    
    def _apply_control_actions(self, control_inputs: dict, dt: float):
        """Apply control actions to the primary system"""
        # Control rod actions
        rod_action = control_inputs.get('control_rod_action', ControlAction.NO_ACTION)
        rod_magnitude = control_inputs.get('control_rod_magnitude', 1.0)
        
        if rod_action == ControlAction.CONTROL_ROD_INSERT:
            self.state.control_rod_position = max(
                0,
                self.state.control_rod_position
                - self.max_control_rod_speed * dt * rod_magnitude,
            )
        elif rod_action == ControlAction.CONTROL_ROD_WITHDRAW:
            self.state.control_rod_position = min(
                100,
                self.state.control_rod_position
                + self.max_control_rod_speed * dt * rod_magnitude,
            )
        
        # Coolant flow actions
        flow_action = control_inputs.get('coolant_flow_action', ControlAction.NO_ACTION)
        flow_magnitude = control_inputs.get('coolant_flow_magnitude', 1.0)
        
        if flow_action == ControlAction.INCREASE_COOLANT_FLOW:
            self.state.coolant_flow_rate = min(
                50000,
                self.state.coolant_flow_rate
                + self.max_flow_change_rate * dt * flow_magnitude,
            )
        elif flow_action == ControlAction.DECREASE_COOLANT_FLOW:
            self.state.coolant_flow_rate = max(
                5000,
                self.state.coolant_flow_rate
                - self.max_flow_change_rate * dt * flow_magnitude,
            )
        
        # Boron concentration actions
        boron_action = control_inputs.get('boron_action', ControlAction.NO_ACTION)
        boron_magnitude = control_inputs.get('boron_magnitude', 1.0)
        
        if boron_action == ControlAction.DILUTE_BORON:
            max_dilution_rate = 50.0  # ppm/s
            self.state.boron_concentration = max(
                0,
                self.state.boron_concentration
                - max_dilution_rate * dt * boron_magnitude,
            )
        elif boron_action == ControlAction.BORATE_COOLANT:
            max_boration_rate = 50.0  # ppm/s
            self.state.boron_concentration = min(
                3000,
                self.state.boron_concentration
                + max_boration_rate * dt * boron_magnitude,
            )
        
        # Steam valve actions
        valve_action = control_inputs.get('steam_valve_action', ControlAction.NO_ACTION)
        valve_magnitude = control_inputs.get('steam_valve_magnitude', 1.0)
        
        if valve_action == ControlAction.OPEN_STEAM_VALVE:
            self.state.steam_valve_position = min(
                100,
                self.state.steam_valve_position
                + self.max_valve_speed * dt * valve_magnitude,
            )
        elif valve_action == ControlAction.CLOSE_STEAM_VALVE:
            self.state.steam_valve_position = max(
                0,
                self.state.steam_valve_position
                - self.max_valve_speed * dt * valve_magnitude,
            )
    
    def get_system_state(self) -> dict:
        """Get complete primary system state for monitoring and logging"""
        return {
            'rated_power_mw': self.rated_power_mw,
            'thermal_power_mw': self.thermal_power_mw,
            'total_reactivity_pcm': self.total_reactivity_pcm,
            'scram_activated': self.scram_activated,
            'reactor_state': {
                'neutron_flux': self.state.neutron_flux,
                'reactivity': self.state.reactivity,
                'fuel_temperature': self.state.fuel_temperature,
                'coolant_temperature': self.state.coolant_temperature,
                'coolant_pressure': self.state.coolant_pressure,
                'coolant_flow_rate': self.state.coolant_flow_rate,
                'power_level': self.state.power_level,
                'control_rod_position': self.state.control_rod_position,
                'boron_concentration': self.state.boron_concentration,
                'scram_status': self.state.scram_status
            },
            'component_states': {
                'heat_source': getattr(self.heat_source, 'get_state', lambda: {})(),
                'neutronics': getattr(self.neutronics, 'get_state_dict', lambda: {})(),
                'thermal_hydraulics': getattr(self.thermal_hydraulics, 'get_state_dict', lambda: {})(),
                'safety': getattr(self.scram_system, 'get_state_dict', lambda: {})()
            }
        }
    
    def reset_system(self) -> None:
        """Reset all components to initial steady-state conditions"""
        # Reset heat source if it has a reset method
        if hasattr(self.heat_source, 'reset'):
            self.heat_source.reset()
        
        # Reset component models if they have reset methods
        if hasattr(self.neutronics, 'reset'):
            self.neutronics.reset()
        if hasattr(self.thermal_hydraulics, 'reset'):
            self.thermal_hydraulics.reset()
        if hasattr(self.scram_system, 'reset'):
            self.scram_system.reset()
        
        # Reset system state
        self.state = ReactorState()
        self.thermal_power_mw = 0.0
        self.total_reactivity_pcm = 0.0
        self.scram_activated = False


# Example usage and testing
if __name__ == "__main__":
    print("Primary Reactor Physics System - Integration Test")
    print("=" * 60)
    
    # Create integrated primary system
    primary_system = PrimaryReactorPhysics(rated_power_mw=3000.0)
    
    print(f"Initialized system with {primary_system.rated_power_mw:.0f} MW rated power")
    print()
    
    # Test transient operation
    print("Transient Operation Test (Control Rod Movement):")
    
    # Test control rod withdrawal
    for step in range(5):
        control_inputs = {
            'control_rod_action': ControlAction.CONTROL_ROD_WITHDRAW,
            'control_rod_magnitude': 0.5,
            'coolant_flow_action': ControlAction.NO_ACTION,
            'coolant_flow_magnitude': 0.0,
            'boron_action': ControlAction.NO_ACTION,
            'boron_magnitude': 0.0,
            'steam_valve_action': ControlAction.NO_ACTION,
            'steam_valve_magnitude': 0.0
        }
        
        result = primary_system.update_system(
            control_inputs=control_inputs,
            dt=1.0
        )
        
        print(f"  Step {step:2d}: Power {result['power_level_percent']:6.1f}%, "
              f"Fuel Temp {result['fuel_temperature']:6.1f}°C, "
              f"Rod Pos {result['control_rod_position']:5.1f}%")
    
    print()
    print("Primary reactor physics implementation complete!")
    print("Components: Neutronics, Thermal Hydraulics, Safety Systems, Heat Sources")
    print("Features: Control rod dynamics, boron chemistry, reactivity feedback, scram logic")
