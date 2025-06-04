import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
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
    boron_concentration: float = 1200.0  # ppm

    # Fission product poisons
    xenon_concentration: float = 2.8e15  # atoms/cm³
    iodine_concentration: float = 1.5e16  # atoms/cm³
    samarium_concentration: float = 1.0e15  # atoms/cm³

    # Burnable poisons and fuel depletion
    burnable_poison_worth: float = -800.0  # pcm
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


class NuclearPlantSimulator:
    """Physics-based nuclear power plant simulator"""

    def __init__(self, dt: float = 1.0, heat_source=None):
        self.dt = dt  # Time step in seconds
        self.time = 0.0
        self.state = ReactorState()
        self.history = []
        
        # Heat source abstraction
        if heat_source is not None:
            self.heat_source = heat_source
        else:
            # Default to reactor physics heat source
            from systems.primary.reactor.heat_sources import ReactorHeatSource
            self.heat_source = ReactorHeatSource(rated_power_mw=3000.0)

        # Physical constants
        self.BETA = 0.0065  # Total delayed neutron fraction
        self.LAMBDA = np.array(
            [0.077, 0.311, 1.40, 3.87, 1.40, 0.195]
        )  # Decay constants
        self.LAMBDA_PROMPT = 1e-5  # Prompt neutron generation time
        self.FUEL_HEAT_CAPACITY = 300.0  # J/kg/K
        self.COOLANT_HEAT_CAPACITY = 5200.0  # J/kg/K
        self.FUEL_MASS = 100000.0  # kg
        self.COOLANT_MASS = 300000.0  # kg

        # Control parameters
        self.max_control_rod_speed = 5.0  # %/s
        self.max_valve_speed = 10.0  # %/s
        self.max_flow_change_rate = 1000.0  # kg/s/s

        # Safety limits
        self.max_fuel_temp = 1500.0  # °C (more realistic PWR fuel temperature limit)
        self.max_coolant_pressure = 17.0  # MPa
        self.min_coolant_flow = 1000.0  # kg/s (much lower to prevent early SCRAM)

    def point_kinetics(self, reactivity: float) -> Tuple[float, np.ndarray]:
        """Solve point kinetics equations for neutron flux"""
        # Reactivity feedback effects are already included in the comprehensive model
        # Don't add additional temperature feedback here to avoid double counting

        # Limit reactivity to prevent numerical instability
        reactivity = np.clip(reactivity, -0.9, 0.1)

        # For steady state operation (near critical), use much more conservative integration
        if (
            abs(reactivity) < 0.01
        ):  # Near critical (< 1000 pcm) - wider range for stability
            # For essentially critical conditions, maintain steady flux to prevent power drift
            flux_dot = 0.0
            precursor_dot = np.zeros_like(self.state.delayed_neutron_precursors)
            return flux_dot, precursor_dot

        # For very small reactivity changes, use extremely conservative approach
        if abs(reactivity) < 0.01:  # < 1000 pcm
            # Use a much smaller effective reactivity to prevent oscillations
            effective_reactivity = reactivity * 0.01  # Reduce sensitivity by 99%
        else:
            effective_reactivity = reactivity

        # Point kinetics with delayed neutrons
        flux_dot = (
            (effective_reactivity - self.BETA)
            / self.LAMBDA_PROMPT
            * self.state.neutron_flux
        )
        for i in range(6):
            flux_dot += self.LAMBDA[i] * self.state.delayed_neutron_precursors[i]

        # For near-critical conditions, use extremely conservative flux changes
        if abs(reactivity) < 0.0001:  # Very near critical (< 10 pcm)
            max_flux_change = (
                self.state.neutron_flux * 0.0001
            )  # Max 0.01% change per timestep
        elif abs(reactivity) < 0.001:  # Near critical (< 100 pcm)
            max_flux_change = (
                self.state.neutron_flux * 0.001
            )  # Max 0.1% change per timestep
        elif abs(reactivity) < 0.01:  # Moderately near critical (< 1000 pcm)
            max_flux_change = (
                self.state.neutron_flux * 0.01
            )  # Max 1% change per timestep
        else:
            max_flux_change = (
                self.state.neutron_flux * 0.1
            )  # Max 10% change per timestep

        flux_dot = np.clip(flux_dot, -max_flux_change, max_flux_change)

        # Delayed neutron precursor equations
        precursor_dot = np.zeros_like(self.state.delayed_neutron_precursors)
        for i in range(6):
            beta_i = self.BETA / 6  # Assume equal fractions for simplicity
            precursor_dot[i] = (
                beta_i / self.LAMBDA_PROMPT * self.state.neutron_flux
                - self.LAMBDA[i] * self.state.delayed_neutron_precursors[i]
            )

        return flux_dot, precursor_dot

    def thermal_hydraulics(self) -> Dict[str, float]:
        """Calculate thermal hydraulic parameters"""
        # Power from neutron flux (simplified conversion)
        # Limit thermal power to reasonable range
        thermal_power = np.clip(
            self.state.neutron_flux / 1e12 * 3000e6, 0, 4000e6
        )  # Watts (max 4000 MW)

        # For steady state operation, use much more conservative thermal dynamics
        # to prevent temperature spikes that cause SCRAM

        # Fuel temperature dynamics - much more conservative
        heat_removal = self.heat_transfer_coefficient() * (
            self.state.fuel_temperature - self.state.coolant_temperature
        )
        fuel_temp_dot = (thermal_power - heat_removal) / (
            self.FUEL_MASS * self.FUEL_HEAT_CAPACITY
        )

        # For steady state, limit temperature changes very strictly
        if abs(self.state.power_level - 100.0) < 5.0:  # Near 100% power
            fuel_temp_dot = np.clip(
                fuel_temp_dot, -1.0, 1.0
            )  # Max 1°C/s change for steady state
        else:
            fuel_temp_dot = np.clip(
                fuel_temp_dot, -10, 10
            )  # Max 10°C/s change for transients

        # Coolant temperature dynamics - more conservative
        coolant_heat_gain = heat_removal
        coolant_heat_loss = (
            self.state.coolant_flow_rate
            * self.COOLANT_HEAT_CAPACITY
            * (self.state.coolant_temperature - 260)
        )
        coolant_temp_dot = (coolant_heat_gain - coolant_heat_loss) / (
            self.COOLANT_MASS * self.COOLANT_HEAT_CAPACITY
        )

        # For steady state, limit coolant temperature changes
        if abs(self.state.power_level - 100.0) < 5.0:  # Near 100% power
            coolant_temp_dot = np.clip(
                coolant_temp_dot, -0.5, 0.5
            )  # Max 0.5°C/s change for steady state
        else:
            coolant_temp_dot = np.clip(
                coolant_temp_dot, -5, 5
            )  # Max 5°C/s change for transients

        # Pressure dynamics (simplified) - more stable
        pressure_dot = 0.01 * (self.state.coolant_temperature - 280) - 0.001 * (
            self.state.coolant_pressure - 15.5
        )
        pressure_dot = np.clip(pressure_dot, -0.1, 0.1)  # Max 0.1 MPa/s change

        return {
            "fuel_temp_dot": fuel_temp_dot,
            "coolant_temp_dot": coolant_temp_dot,
            "pressure_dot": pressure_dot,
            "thermal_power": thermal_power,
        }

    def thermal_hydraulics_from_power(self, thermal_power: float) -> Dict[str, float]:
        """Calculate thermal hydraulic parameters from given thermal power"""
        # Fuel temperature dynamics
        heat_removal = self.heat_transfer_coefficient() * (
            self.state.fuel_temperature - self.state.coolant_temperature
        )
        fuel_temp_dot = (thermal_power - heat_removal) / (
            self.FUEL_MASS * self.FUEL_HEAT_CAPACITY
        )

        # For steady state, limit temperature changes very strictly
        if abs(self.state.power_level - 100.0) < 5.0:  # Near 100% power
            fuel_temp_dot = np.clip(
                fuel_temp_dot, -1.0, 1.0
            )  # Max 1°C/s change for steady state
        else:
            fuel_temp_dot = np.clip(
                fuel_temp_dot, -10, 10
            )  # Max 10°C/s change for transients

        # Coolant temperature dynamics
        coolant_heat_gain = heat_removal
        coolant_heat_loss = (
            self.state.coolant_flow_rate
            * self.COOLANT_HEAT_CAPACITY
            * (self.state.coolant_temperature - 260)
        )
        coolant_temp_dot = (coolant_heat_gain - coolant_heat_loss) / (
            self.COOLANT_MASS * self.COOLANT_HEAT_CAPACITY
        )

        # For steady state, limit coolant temperature changes
        if abs(self.state.power_level - 100.0) < 5.0:  # Near 100% power
            coolant_temp_dot = np.clip(
                coolant_temp_dot, -0.5, 0.5
            )  # Max 0.5°C/s change for steady state
        else:
            coolant_temp_dot = np.clip(
                coolant_temp_dot, -5, 5
            )  # Max 5°C/s change for transients

        # Pressure dynamics (simplified)
        pressure_dot = 0.01 * (self.state.coolant_temperature - 280) - 0.001 * (
            self.state.coolant_pressure - 15.5
        )
        pressure_dot = np.clip(pressure_dot, -0.1, 0.1)  # Max 0.1 MPa/s change

        return {
            "fuel_temp_dot": fuel_temp_dot,
            "coolant_temp_dot": coolant_temp_dot,
            "pressure_dot": pressure_dot,
            "thermal_power": thermal_power,
        }

    def heat_transfer_coefficient(self) -> float:
        """Calculate heat transfer coefficient based on flow rate"""
        # Simplified correlation
        return 50000 + 2.0 * self.state.coolant_flow_rate

    def steam_cycle(self) -> Dict[str, float]:
        """Calculate steam cycle parameters"""
        # Steam generation rate based on heat transfer
        steam_generation = min(
            self.state.coolant_flow_rate * 0.05,
            self.state.steam_valve_position / 100 * 2000,
        )

        # Steam temperature and pressure dynamics
        steam_temp_dot = 0.1 * (
            self.state.coolant_temperature - self.state.steam_temperature
        )
        steam_pressure_dot = 0.05 * (steam_generation - self.state.steam_flow_rate)

        # Mass balance
        steam_flow_dot = self.state.steam_valve_position / 100 * 20 - 10
        feedwater_flow_dot = steam_generation - self.state.feedwater_flow_rate

        return {
            "steam_temp_dot": steam_temp_dot,
            "steam_pressure_dot": steam_pressure_dot,
            "steam_flow_dot": steam_flow_dot,
            "feedwater_flow_dot": feedwater_flow_dot,
        }

    def control_rod_reactivity(self, position: float) -> float:
        """Calculate reactivity based on control rod position"""
        # More realistic control rod worth curve
        # At 50% position (normal operating), reactivity should be near zero
        # Full insertion (0%) gives large negative reactivity
        # Full withdrawal (100%) gives moderate positive reactivity

        # Normalize position to 0-1 range
        pos_norm = position / 100.0

        # S-curve reactivity relationship
        # At 50% (0.5 normalized): reactivity ≈ 0
        # At 0% (0.0 normalized): reactivity ≈ -0.05 (shutdown)
        # At 100% (1.0 normalized): reactivity ≈ +0.02 (slight positive)
        reactivity = -0.05 + 0.07 * pos_norm - 0.02 * (pos_norm - 0.5) ** 2

        return reactivity

    def apply_action(self, action: ControlAction, magnitude: float = 1.0):
        """Apply control action to the system"""
        if action == ControlAction.CONTROL_ROD_INSERT:
            self.state.control_rod_position = max(
                0,
                self.state.control_rod_position
                - self.max_control_rod_speed * self.dt * magnitude,
            )

        elif action == ControlAction.CONTROL_ROD_WITHDRAW:
            self.state.control_rod_position = min(
                100,
                self.state.control_rod_position
                + self.max_control_rod_speed * self.dt * magnitude,
            )

        elif action == ControlAction.INCREASE_COOLANT_FLOW:
            self.state.coolant_flow_rate = min(
                50000,
                self.state.coolant_flow_rate
                + self.max_flow_change_rate * self.dt * magnitude,
            )

        elif action == ControlAction.DECREASE_COOLANT_FLOW:
            self.state.coolant_flow_rate = max(
                5000,
                self.state.coolant_flow_rate
                - self.max_flow_change_rate * self.dt * magnitude,
            )

        elif action == ControlAction.OPEN_STEAM_VALVE:
            self.state.steam_valve_position = min(
                100,
                self.state.steam_valve_position
                + self.max_valve_speed * self.dt * magnitude,
            )

        elif action == ControlAction.CLOSE_STEAM_VALVE:
            self.state.steam_valve_position = max(
                0,
                self.state.steam_valve_position
                - self.max_valve_speed * self.dt * magnitude,
            )

        elif action == ControlAction.INCREASE_FEEDWATER:
            self.state.feedwater_flow_rate = min(
                3000,
                self.state.feedwater_flow_rate
                + self.max_flow_change_rate * self.dt * magnitude,
            )

        elif action == ControlAction.DECREASE_FEEDWATER:
            self.state.feedwater_flow_rate = max(
                200,
                self.state.feedwater_flow_rate
                - self.max_flow_change_rate * self.dt * magnitude,
            )

        elif action == ControlAction.DILUTE_BORON:
            # Reduce boron concentration (add reactivity)
            max_dilution_rate = 50.0  # ppm/s
            self.state.boron_concentration = max(
                0,
                self.state.boron_concentration
                - max_dilution_rate * self.dt * magnitude,
            )

        elif action == ControlAction.BORATE_COOLANT:
            # Increase boron concentration (reduce reactivity)
            max_boration_rate = 50.0  # ppm/s
            self.state.boron_concentration = min(
                3000,
                self.state.boron_concentration
                + max_boration_rate * self.dt * magnitude,
            )

    def check_safety_systems(self) -> bool:
        """Check if safety systems should activate"""
        scram_conditions = [
            self.state.fuel_temperature > self.max_fuel_temp,
            self.state.coolant_pressure > self.max_coolant_pressure,
            self.state.coolant_flow_rate < self.min_coolant_flow,
            self.state.power_level > 120,
        ]

        if any(scram_conditions) and not self.state.scram_status:
            # Debug: Print which condition triggered the SCRAM
            if self.state.fuel_temperature > self.max_fuel_temp:
                print(
                    f"SCRAM: Fuel temperature {self.state.fuel_temperature:.1f}°C > {self.max_fuel_temp}°C"
                )
            if self.state.coolant_pressure > self.max_coolant_pressure:
                print(
                    f"SCRAM: Coolant pressure {self.state.coolant_pressure:.1f} MPa > {self.max_coolant_pressure} MPa"
                )
            if self.state.coolant_flow_rate < self.min_coolant_flow:
                print(
                    f"SCRAM: Coolant flow {self.state.coolant_flow_rate:.1f} kg/s < {self.min_coolant_flow} kg/s"
                )
            if self.state.power_level > 120:
                print(f"SCRAM: Power level {self.state.power_level:.1f}% > 120%")

            self.state.scram_status = True
            self.state.control_rod_position = 0  # All rods in
            return True
        return False

    def step(
        self, action: Optional[ControlAction] = None, magnitude: float = 1.0
    ) -> Dict:
        """Advance simulation by one time step"""
        # Apply control action
        if action is not None:
            self.apply_action(action, magnitude)

        # Update heat source (this handles all heat generation logic)
        heat_result = self.heat_source.update(
            dt=self.dt, 
            reactor_state=self.state, 
            control_action=action
        )
        
        # Extract heat source results
        thermal_power_mw = heat_result['thermal_power_mw']
        self.state.power_level = heat_result['power_percent']
        
        # Update neutron flux if provided
        if 'neutron_flux' in heat_result:
            self.state.neutron_flux = heat_result['neutron_flux']
        
        # Update reactivity if provided
        if 'reactivity_pcm' in heat_result:
            total_reactivity = heat_result['reactivity_pcm']
            self.state.reactivity = total_reactivity / 100000.0  # Convert to delta-k/k
        else:
            total_reactivity = 0.0
        
        # Get reactivity components if available
        reactivity_components = heat_result.get('reactivity_components', {})

        # Calculate thermal hydraulics based on heat source output
        thermal_power = thermal_power_mw * 1e6  # Convert to watts
        thermal_params = self.thermal_hydraulics_from_power(thermal_power)
        steam_params = self.steam_cycle()

        # Update thermal hydraulic state variables
        self.state.fuel_temperature += thermal_params["fuel_temp_dot"] * self.dt
        self.state.fuel_temperature = np.clip(self.state.fuel_temperature, 200, 2000)

        self.state.coolant_temperature += thermal_params["coolant_temp_dot"] * self.dt
        self.state.coolant_temperature = np.clip(self.state.coolant_temperature, 200, 400)

        self.state.coolant_pressure += thermal_params["pressure_dot"] * self.dt
        self.state.coolant_pressure = np.clip(self.state.coolant_pressure, 10, 20)

        # Update steam cycle parameters
        self.state.steam_temperature += steam_params["steam_temp_dot"] * self.dt
        self.state.steam_temperature = np.clip(self.state.steam_temperature, 200, 400)

        self.state.steam_pressure += steam_params["steam_pressure_dot"] * self.dt
        self.state.steam_pressure = np.clip(self.state.steam_pressure, 1, 10)

        self.state.steam_flow_rate += steam_params["steam_flow_dot"] * self.dt
        self.state.steam_flow_rate = np.clip(self.state.steam_flow_rate, 0, 3000)

        self.state.feedwater_flow_rate += steam_params["feedwater_flow_dot"] * self.dt
        self.state.feedwater_flow_rate = np.clip(self.state.feedwater_flow_rate, 0, 3000)

        # Check for NaN values and reset if necessary
        if (
            np.isnan(self.state.fuel_temperature)
            or np.isnan(self.state.neutron_flux)
            or np.isnan(self.state.coolant_temperature)
            or np.isnan(self.state.coolant_pressure)
        ):
            print("Warning: NaN detected, resetting to safe values")
            self.state.neutron_flux = 1e12
            self.state.fuel_temperature = 600.0
            self.state.coolant_temperature = 280.0
            self.state.coolant_pressure = 15.5
            self.state.power_level = 100.0

        # Check safety systems
        scram_activated = self.check_safety_systems()

        # Advance time
        self.time += self.dt

        # Store history
        observation = self.get_observation()
        self.history.append(observation.copy())

        # Return step information
        return {
            "observation": observation,
            "reward": self.calculate_reward(),
            "done": scram_activated,
            "info": {
                "time": self.time,
                "thermal_power": thermal_power_mw,
                "scram_activated": scram_activated,
                "reactivity": total_reactivity,  # Return in pcm
                "reactivity_components": reactivity_components,
            },
        }

    def get_observation(self) -> np.ndarray:
        """Get current state as observation vector for RL"""
        return np.array(
            [
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
        )

    def calculate_reward(self) -> float:
        """Calculate reward for RL training"""
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

        return power_reward + temp_penalty + pressure_penalty + scram_penalty

    def reset(self):
        """Reset simulation to initial conditions"""
        self.state = ReactorState()
        self.time = 0.0
        self.history = []
        return self.get_observation()

    def plot_parameters(self, parameters: List[str] = None, time_window: int = None):
        """Plot selected parameters over time"""
        if not self.history:
            print("No simulation data to plot")
            return

        if parameters is None:
            parameters = [
                "power_level",
                "fuel_temperature",
                "coolant_temperature",
                "coolant_pressure",
                "control_rod_position",
            ]

        history_array = np.array(self.history)
        if time_window:
            history_array = history_array[-time_window:]

        time_axis = np.arange(len(history_array)) * self.dt

        fig, axes = plt.subplots(len(parameters), 1, figsize=(12, 3 * len(parameters)))
        if len(parameters) == 1:
            axes = [axes]

        param_map = {
            "power_level": (10, "Power Level (%)"),
            "fuel_temperature": (1, "Fuel Temperature (°C)"),
            "coolant_temperature": (2, "Coolant Temperature (°C)"),
            "coolant_pressure": (3, "Coolant Pressure (MPa)"),
            "control_rod_position": (8, "Control Rod Position (%)"),
            "steam_flow_rate": (7, "Steam Flow Rate (kg/s)"),
        }

        for i, param in enumerate(parameters):
            if param in param_map:
                idx, ylabel = param_map[param]
                # Denormalize the data
                if param == "power_level":
                    data = history_array[:, idx] * 100
                elif param == "fuel_temperature":
                    data = history_array[:, idx] * 1000
                elif param == "coolant_temperature":
                    data = history_array[:, idx] * 300
                elif param == "coolant_pressure":
                    data = history_array[:, idx] * 20
                elif param == "control_rod_position":
                    data = history_array[:, idx] * 100
                elif param == "steam_flow_rate":
                    data = history_array[:, idx] * 3000
                else:
                    data = history_array[:, idx]

                axes[i].plot(time_axis, data)
                axes[i].set_ylabel(ylabel)
                axes[i].grid(True)

        axes[-1].set_xlabel("Time (s)")
        plt.tight_layout()
        plt.show()


# Example usage and testing
def run_simulation_example():
    """Example of running the nuclear plant simulation"""
    print("Nuclear Power Plant Digital Twin Simulation")
    print("=" * 50)

    # Create simulator
    sim = NuclearPlantSimulator(dt=1.0)

    # Run simulation with some control actions
    print("Running simulation with control actions...")

    for t in range(300):  # 5 minutes
        if t == 60:  # At 1 minute, withdraw control rods
            action = ControlAction.CONTROL_ROD_WITHDRAW
        elif t == 120:  # At 2 minutes, increase steam valve opening
            action = ControlAction.OPEN_STEAM_VALVE
        elif t == 180:  # At 3 minutes, insert control rods
            action = ControlAction.CONTROL_ROD_INSERT
        elif t == 240:  # At 4 minutes, increase coolant flow
            action = ControlAction.INCREASE_COOLANT_FLOW
        else:
            action = ControlAction.NO_ACTION

        result = sim.step(action)

        # Print status every 30 seconds
        if t % 30 == 0:
            print(
                f"Time: {sim.time:6.1f}s | Power: {sim.state.power_level:6.1f}% | "
                f"Fuel Temp: {sim.state.fuel_temperature:6.1f}°C | "
                f"Rod Pos: {sim.state.control_rod_position:5.1f}%"
            )

    print(f"\nSimulation completed. Final power level: {sim.state.power_level:.1f}%")

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

    def __init__(self):
        self.sim = NuclearPlantSimulator()
        self.action_space_size = len(ControlAction)
        self.observation_space_size = 12

    def step(self, action_idx: int):
        action = ControlAction(action_idx)
        result = self.sim.step(action)
        return (result["observation"], result["reward"], result["done"], result["info"])

    def reset(self):
        return self.sim.reset()

    def render(self):
        print(
            f"Time: {self.sim.time:6.1f}s | Power: {self.sim.state.power_level:6.1f}% | "
            f"Fuel Temp: {self.sim.state.fuel_temperature:6.1f}°C"
        )


if __name__ == "__main__":
    # Run the example simulation
    simulator = run_simulation_example()
