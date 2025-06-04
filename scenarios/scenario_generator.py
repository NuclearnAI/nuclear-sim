"""
Nuclear Plant Scenario Generator

This module generates various operational scenarios for training and testing
the nuclear plant simulator, including normal operations, transients, and emergency scenarios.
"""

import random
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from simulator.core.sim import ControlAction, NuclearPlantSimulator, ReactorState

warnings.filterwarnings('ignore')


class ScenarioType(Enum):
    """Types of scenarios that can be generated"""
    NORMAL_OPERATION = "normal_operation"
    POWER_RAMP_UP = "power_ramp_up"
    POWER_RAMP_DOWN = "power_ramp_down"
    LOAD_FOLLOWING = "load_following"
    STEAM_LINE_BREAK = "steam_line_break"
    LOSS_OF_COOLANT = "loss_of_coolant"
    CONTROL_ROD_MALFUNCTION = "control_rod_malfunction"
    FEEDWATER_TRANSIENT = "feedwater_transient"
    TURBINE_TRIP = "turbine_trip"
    REACTOR_SCRAM = "reactor_scram"


@dataclass
class ScenarioAction:
    """Represents a single action in a scenario"""
    time: float
    action: ControlAction
    magnitude: float = 1.0
    description: str = ""


@dataclass
class Scenario:
    """Complete scenario definition"""
    name: str
    scenario_type: ScenarioType
    duration: float  # seconds
    initial_state: Optional[ReactorState] = None
    actions: Optional[List[ScenarioAction]] = None
    description: str = ""
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []


class ScenarioGenerator:
    """Generates various nuclear plant operational scenarios"""
    
    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
    
    def generate_normal_operation(self, duration: float = 3600) -> Scenario:
        """Generate a normal operation scenario with minor adjustments"""
        actions = []
        
        # Use default initial state which is already in equilibrium
        initial_state = None  # Use simulator's default equilibrium state
        
        # Add some minor control adjustments throughout operation
        num_adjustments = random.randint(3, 8)
        for i in range(num_adjustments):
            time = random.uniform(60, duration - 60)
            action_type = random.choice([
                ControlAction.CONTROL_ROD_WITHDRAW,
                ControlAction.CONTROL_ROD_INSERT,
                ControlAction.OPEN_STEAM_VALVE,
                ControlAction.CLOSE_STEAM_VALVE,
                ControlAction.INCREASE_FEEDWATER,
                ControlAction.DECREASE_FEEDWATER
            ])
            magnitude = random.uniform(0.1, 0.5)  # Small adjustments
            
            actions.append(ScenarioAction(
                time=time,
                action=action_type,
                magnitude=magnitude,
                description=f"Minor {action_type.name.lower()} adjustment"
            ))
        
        # Sort actions by time
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Normal Operation",
            scenario_type=ScenarioType.NORMAL_OPERATION,
            duration=duration,
            initial_state=initial_state,
            actions=actions,
            description="Normal plant operation with minor control adjustments"
        )
    
    def generate_power_ramp_up(self, target_power: float = 110, duration: float = 1800) -> Scenario:
        """Generate a power ramp-up scenario"""
        actions = []
        
        # Initial state at lower power
        initial_state = ReactorState()
        initial_state.power_level = 80.0
        initial_state.control_rod_position = 40.0  # More inserted for lower power
        initial_state.fuel_temperature = 550.0  # Lower temperature for stable operation
        initial_state.neutron_flux = 8e11  # Lower flux for 80% power
        
        # Gradual rod withdrawal to increase power
        ramp_steps = 6
        for i in range(ramp_steps):
            time = (i + 1) * (duration / ramp_steps)
            actions.append(ScenarioAction(
                time=time,
                action=ControlAction.CONTROL_ROD_WITHDRAW,
                magnitude=0.8,
                description=f"Rod withdrawal step {i+1} for power increase"
            ))
        
        # Adjust steam valve to match power increase
        for i in range(3):
            time = duration * 0.3 * (i + 1)
            actions.append(ScenarioAction(
                time=time,
                action=ControlAction.OPEN_STEAM_VALVE,
                magnitude=0.6,
                description="Steam valve adjustment for power ramp"
            ))
        
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Power Ramp Up",
            scenario_type=ScenarioType.POWER_RAMP_UP,
            duration=duration,
            initial_state=initial_state,
            actions=actions,
            description=f"Controlled power ramp from 80% to {target_power}%"
        )
    
    def generate_power_ramp_down(self, target_power: float = 70, duration: float = 1800) -> Scenario:
        """Generate a power ramp-down scenario"""
        actions = []
        
        # Initial state at higher power
        initial_state = ReactorState()
        initial_state.power_level = 100.0
        initial_state.control_rod_position = 60.0
        initial_state.fuel_temperature = 550.0  # Stable temperature
        initial_state.neutron_flux = 1e12  # Normal flux for 100% power
        
        # Gradual rod insertion to decrease power
        ramp_steps = 5
        for i in range(ramp_steps):
            time = (i + 1) * (duration / ramp_steps)
            actions.append(ScenarioAction(
                time=time,
                action=ControlAction.CONTROL_ROD_INSERT,
                magnitude=0.7,
                description=f"Rod insertion step {i+1} for power decrease"
            ))
        
        # Adjust steam valve to match power decrease
        actions.append(ScenarioAction(
            time=duration * 0.4,
            action=ControlAction.CLOSE_STEAM_VALVE,
            magnitude=0.5,
            description="Steam valve closure for power ramp down"
        ))
        
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Power Ramp Down",
            scenario_type=ScenarioType.POWER_RAMP_DOWN,
            duration=duration,
            initial_state=initial_state,
            actions=actions,
            description=f"Controlled power ramp from 100% to {target_power}%"
        )
    
    def generate_load_following(self, duration: float = 7200) -> Scenario:
        """Generate a load following scenario with varying power demands"""
        actions = []
        
        # Initial state for stable operation
        initial_state = ReactorState()
        initial_state.fuel_temperature = 550.0  # Stable temperature
        initial_state.neutron_flux = 1e12  # Normal flux for 100% power
        initial_state.power_level = 100.0
        
        # Create a sinusoidal load pattern
        num_cycles = 3
        steps_per_cycle = 8
        total_steps = num_cycles * steps_per_cycle
        
        for i in range(total_steps):
            time = (i + 1) * (duration / total_steps)
            
            # Sinusoidal pattern for power demand
            cycle_position = (i % steps_per_cycle) / steps_per_cycle * 2 * np.pi
            power_factor = 0.5 + 0.3 * np.sin(cycle_position)  # Between 0.2 and 0.8
            
            if power_factor > 0.5:
                action = ControlAction.CONTROL_ROD_WITHDRAW
                magnitude = (power_factor - 0.5) * 2  # Scale to 0-1
            else:
                action = ControlAction.CONTROL_ROD_INSERT
                magnitude = (0.5 - power_factor) * 2  # Scale to 0-1
            
            actions.append(ScenarioAction(
                time=time,
                action=action,
                magnitude=magnitude,
                description=f"Load following adjustment {i+1}"
            ))
        
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Load Following",
            scenario_type=ScenarioType.LOAD_FOLLOWING,
            duration=duration,
            initial_state=initial_state,
            actions=actions,
            description="Variable power output following electrical grid demand"
        )
    
    def generate_steam_line_break(self, duration: float = 600) -> Scenario:
        """Generate a steam line break accident scenario"""
        actions = []
        
        # Initial state for stable operation
        initial_state = ReactorState()
        initial_state.fuel_temperature = 550.0  # Stable temperature
        initial_state.neutron_flux = 1e12  # Normal flux for 100% power
        initial_state.power_level = 100.0
        
        # Steam line break occurs early in scenario
        break_time = 30.0
        actions.append(ScenarioAction(
            time=break_time,
            action=ControlAction.OPEN_STEAM_VALVE,
            magnitude=2.0,  # Excessive opening to simulate break
            description="Steam line break - rapid steam loss"
        ))
        
        # Operator response: emergency feedwater increase
        actions.append(ScenarioAction(
            time=break_time + 15,
            action=ControlAction.INCREASE_FEEDWATER,
            magnitude=1.5,
            description="Emergency feedwater increase response"
        ))
        
        # Control rod insertion for power reduction
        actions.append(ScenarioAction(
            time=break_time + 30,
            action=ControlAction.CONTROL_ROD_INSERT,
            magnitude=1.0,
            description="Control rod insertion for power reduction"
        ))
        
        # Additional coolant flow increase
        actions.append(ScenarioAction(
            time=break_time + 45,
            action=ControlAction.INCREASE_COOLANT_FLOW,
            magnitude=1.2,
            description="Increase coolant flow for heat removal"
        ))
        
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Steam Line Break",
            scenario_type=ScenarioType.STEAM_LINE_BREAK,
            duration=duration,
            initial_state=initial_state,
            actions=actions,
            description="Steam line break accident with operator response"
        )
    
    def generate_loss_of_coolant(self, duration: float = 900) -> Scenario:
        """Generate a loss of coolant accident (LOCA) scenario"""
        actions = []
        
        # LOCA occurs early
        loca_time = 45.0
        actions.append(ScenarioAction(
            time=loca_time,
            action=ControlAction.DECREASE_COOLANT_FLOW,
            magnitude=1.5,  # Significant coolant loss
            description="Loss of coolant accident initiation"
        ))
        
        # Immediate scram response
        actions.append(ScenarioAction(
            time=loca_time + 5,
            action=ControlAction.CONTROL_ROD_INSERT,
            magnitude=2.0,  # Full insertion
            description="Emergency reactor scram"
        ))
        
        # Emergency core cooling activation
        actions.append(ScenarioAction(
            time=loca_time + 20,
            action=ControlAction.INCREASE_FEEDWATER,
            magnitude=2.0,
            description="Emergency core cooling system activation"
        ))
        
        # Continued cooling efforts
        actions.append(ScenarioAction(
            time=loca_time + 60,
            action=ControlAction.INCREASE_FEEDWATER,
            magnitude=1.5,
            description="Continued emergency cooling"
        ))
        
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Loss of Coolant Accident",
            scenario_type=ScenarioType.LOSS_OF_COOLANT,
            duration=duration,
            actions=actions,
            description="Loss of coolant accident with emergency response"
        )
    
    def generate_turbine_trip(self, duration: float = 1200) -> Scenario:
        """Generate a turbine trip scenario"""
        actions = []
        
        # Turbine trip - sudden steam valve closure
        trip_time = 60.0
        actions.append(ScenarioAction(
            time=trip_time,
            action=ControlAction.CLOSE_STEAM_VALVE,
            magnitude=2.0,  # Rapid closure
            description="Turbine trip - steam valve closure"
        ))
        
        # Reactor power reduction
        actions.append(ScenarioAction(
            time=trip_time + 10,
            action=ControlAction.CONTROL_ROD_INSERT,
            magnitude=1.2,
            description="Power reduction following turbine trip"
        ))
        
        # Pressure relief
        actions.append(ScenarioAction(
            time=trip_time + 30,
            action=ControlAction.OPEN_STEAM_VALVE,
            magnitude=0.3,
            description="Pressure relief valve operation"
        ))
        
        # Gradual power recovery
        recovery_start = trip_time + 300
        for i in range(4):
            actions.append(ScenarioAction(
                time=recovery_start + i * 120,
                action=ControlAction.CONTROL_ROD_WITHDRAW,
                magnitude=0.4,
                description=f"Power recovery step {i+1}"
            ))
        
        actions.sort(key=lambda x: x.time)
        
        return Scenario(
            name="Turbine Trip",
            scenario_type=ScenarioType.TURBINE_TRIP,
            duration=duration,
            actions=actions,
            description="Turbine trip event with power reduction and recovery"
        )
    
    def generate_random_scenario(self, duration: float = 1800) -> Scenario:
        """Generate a random scenario combining multiple events"""
        scenario_types = [
            self.generate_normal_operation,
            self.generate_power_ramp_up,
            self.generate_power_ramp_down,
            self.generate_load_following
        ]
        
        # Randomly select and generate a scenario
        selected_generator = random.choice(scenario_types)
        return selected_generator(duration)
    
    def generate_scenario_batch(self, 
                              scenario_types: List[ScenarioType], 
                              count_per_type: int = 5) -> List[Scenario]:
        """Generate a batch of scenarios for training"""
        scenarios = []
        
        for scenario_type in scenario_types:
            for _ in range(count_per_type):
                if scenario_type == ScenarioType.NORMAL_OPERATION:
                    scenario = self.generate_normal_operation(
                        duration=random.uniform(1800, 7200)
                    )
                elif scenario_type == ScenarioType.POWER_RAMP_UP:
                    scenario = self.generate_power_ramp_up(
                        target_power=random.uniform(105, 115),
                        duration=random.uniform(1200, 2400)
                    )
                elif scenario_type == ScenarioType.POWER_RAMP_DOWN:
                    scenario = self.generate_power_ramp_down(
                        target_power=random.uniform(60, 80),
                        duration=random.uniform(1200, 2400)
                    )
                elif scenario_type == ScenarioType.LOAD_FOLLOWING:
                    scenario = self.generate_load_following(
                        duration=random.uniform(3600, 10800)
                    )
                elif scenario_type == ScenarioType.STEAM_LINE_BREAK:
                    scenario = self.generate_steam_line_break(
                        duration=random.uniform(600, 1200)
                    )
                elif scenario_type == ScenarioType.LOSS_OF_COOLANT:
                    scenario = self.generate_loss_of_coolant(
                        duration=random.uniform(900, 1800)
                    )
                elif scenario_type == ScenarioType.TURBINE_TRIP:
                    scenario = self.generate_turbine_trip(
                        duration=random.uniform(1200, 2400)
                    )
                else:
                    scenario = self.generate_random_scenario()
                
                scenarios.append(scenario)
        
        return scenarios


def run_scenario(scenario: Scenario, simulator: Optional[NuclearPlantSimulator] = None) -> Dict[str, Any]:
    """Run a specific scenario and return results"""
    if simulator is None:
        simulator = NuclearPlantSimulator(dt=1.0)
    
    # Set initial state if provided
    if scenario.initial_state is not None:
        # Reset first to initialize properly, then override with custom state
        simulator.reset()
        # Copy the initial state values to the simulator state
        simulator.state.fuel_temperature = scenario.initial_state.fuel_temperature
        simulator.state.neutron_flux = scenario.initial_state.neutron_flux
        simulator.state.power_level = scenario.initial_state.power_level
        simulator.state.control_rod_position = scenario.initial_state.control_rod_position
        # Copy other important state variables
        simulator.state.coolant_temperature = scenario.initial_state.coolant_temperature
        simulator.state.coolant_pressure = scenario.initial_state.coolant_pressure
        simulator.state.coolant_flow_rate = scenario.initial_state.coolant_flow_rate
        simulator.state.steam_temperature = scenario.initial_state.steam_temperature
        simulator.state.steam_pressure = scenario.initial_state.steam_pressure
        simulator.state.steam_flow_rate = scenario.initial_state.steam_flow_rate
        simulator.state.feedwater_flow_rate = scenario.initial_state.feedwater_flow_rate
        simulator.state.steam_valve_position = scenario.initial_state.steam_valve_position
        simulator.state.reactivity = scenario.initial_state.reactivity
        simulator.state.scram_status = scenario.initial_state.scram_status
        if scenario.initial_state.delayed_neutron_precursors is not None:
            simulator.state.delayed_neutron_precursors = scenario.initial_state.delayed_neutron_precursors.copy()
    else:
        simulator.reset()
    
    print(f"Running scenario: {scenario.name}")
    print(f"Description: {scenario.description}")
    print(f"Duration: {scenario.duration:.0f} seconds")
    print("-" * 50)
    
    # Create action schedule - round times to nearest second for integer timesteps
    action_schedule = {}
    if scenario.actions:
        for action in scenario.actions:
            rounded_time = round(action.time)
            action_schedule[rounded_time] = action
    
    results = []
    current_time = 0.0
    
    while current_time < scenario.duration:
        # Check if there's an action at this time (using integer time)
        action_to_apply = None
        magnitude = 1.0
        
        time_key = int(current_time)
        if time_key in action_schedule:
            scenario_action = action_schedule[time_key]
            action_to_apply = scenario_action.action
            magnitude = scenario_action.magnitude
            print(f"Time {current_time:6.0f}s: {scenario_action.description}")
        
        # Step the simulation
        result = simulator.step(action_to_apply, magnitude)
        results.append({
            'time': current_time,
            'observation': result['observation'].copy(),
            'reward': result['reward'],
            'done': result['done'],
            'info': result['info'].copy()
        })
        
        # Print status every 60 seconds
        if int(current_time) % 60 == 0:
            print(f"Time: {current_time:6.0f}s | Power: {simulator.state.power_level:6.1f}% | "
                  f"Fuel Temp: {simulator.state.fuel_temperature:6.0f}°C | "
                  f"Rod Pos: {simulator.state.control_rod_position:5.1f}%")
        
        # Check for early termination
        if result['done']:
            print(f"Scenario terminated early at {current_time:.0f}s due to safety system activation")
            break
        
        current_time += simulator.dt
    
    print(f"Scenario completed. Final power level: {simulator.state.power_level:.1f}%")
    
    return {
        'scenario': scenario,
        'simulator': simulator,
        'results': results,
        'success': not results[-1]['done'] if results else False
    }


def demonstrate_scenarios():
    """Demonstrate various scenario types"""
    generator = ScenarioGenerator(random_seed=42)
    
    # Generate different types of scenarios
    scenarios = [
        generator.generate_normal_operation(duration=600),
        generator.generate_power_ramp_up(duration=900),
        generator.generate_steam_line_break(duration=300),
        generator.generate_load_following(duration=1200)
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*60}")
        result = run_scenario(scenario)
        
        # Plot results if simulation has history
        if hasattr(result['simulator'], 'plot_parameters'):
            result['simulator'].plot_parameters([
                'power_level', 'fuel_temperature', 'coolant_temperature', 
                'control_rod_position'
            ])


if __name__ == "__main__":
    demonstrate_scenarios()
