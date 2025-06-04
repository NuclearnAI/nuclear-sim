"""
Unified Reactor Physics Module

This module provides a comprehensive reactor physics implementation that consolidates
all reactor physics calculations including neutron kinetics, thermal dynamics, and
reactivity feedback effects.
"""

import os
import sys
import warnings
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

# Import the reactivity model from the same directory
from .reactivity_model import ReactivityModel, ReactorConfig

warnings.filterwarnings('ignore')


@dataclass
class ReactorState:
    """Unified reactor state containing all reactor parameters"""
    
    # Neutronics
    neutron_flux: float = 1e13  # neutrons/cm²/s (100% power)
    reactivity: float = 0.0     # delta-k/k (critical)
    delayed_neutron_precursors: Optional[np.ndarray] = None
    
    # Thermal hydraulics
    fuel_temperature: float = 575.0    # °C (realistic steady-state average)
    coolant_temperature: float = 280.0  # °C
    coolant_pressure: float = 15.5     # MPa
    coolant_flow_rate: float = 20000.0 # kg/s
    coolant_void_fraction: float = 0.0 # Steam void fraction (0-1)
    
    # Steam cycle
    steam_temperature: float = 285.0   # °C
    steam_pressure: float = 7.0        # MPa
    steam_flow_rate: float = 1000.0    # kg/s
    feedwater_flow_rate: float = 1000.0 # kg/s
    
    # Control systems
    control_rod_position: float = 95.0  # % withdrawn (PWR normal operation)
    steam_valve_position: float = 50.0  # % open
    boron_concentration: float = 1200.0 # ppm
    
    # Fission product poisons
    xenon_concentration: float = 2.8e15  # atoms/cm³
    iodine_concentration: float = 1.5e16 # atoms/cm³
    samarium_concentration: float = 1.0e15 # atoms/cm³
    
    # Burnable poisons and fuel depletion
    burnable_poison_worth: float = -800.0 # pcm
    fuel_burnup: float = 15000.0 # MWd/MTU
    
    # Safety parameters
    power_level: float = 100.0         # % rated power
    scram_status: bool = False
    
    def __post_init__(self):
        if self.delayed_neutron_precursors is None:
            # 6 delayed neutron precursor groups
            self.delayed_neutron_precursors = np.array([0.0002, 0.0011, 0.0010, 0.0030, 0.0096, 0.0003])


class ReactorPhysics:
    """
    Unified reactor physics engine that handles all reactor physics calculations
    """
    
    def __init__(self, rated_power_mw: float = 3000.0, config: Optional[ReactorConfig] = None):
        """
        Initialize reactor physics
        
        Args:
            rated_power_mw: Rated thermal power in MW
            config: Reactor configuration parameters
        """
        self.rated_power_mw = rated_power_mw
        self.state = ReactorState()
        
        # Initialize reactivity model
        self.reactivity_model = ReactivityModel(config)
        
        # Physical constants for neutron kinetics
        self.BETA = 0.0065  # Total delayed neutron fraction
        self.LAMBDA = np.array([0.077, 0.311, 1.40, 3.87, 1.40, 0.195])  # Decay constants
        self.LAMBDA_PROMPT = 1e-5  # Prompt neutron generation time
        
        # Thermal constants
        self.FUEL_HEAT_CAPACITY = 300.0  # J/kg/K
        self.COOLANT_HEAT_CAPACITY = 5200.0  # J/kg/K
        self.FUEL_MASS = 100000.0  # kg
        self.COOLANT_MASS = 300000.0  # kg
        
        # Safety limits
        self.max_fuel_temp = 1500.0  # °C
        self.max_coolant_pressure = 17.0  # MPa
        self.min_coolant_flow = 1000.0  # kg/s
        
    def point_kinetics(self, reactivity: float, dt: float) -> Tuple[float, np.ndarray]:
        """
        Solve point kinetics equations for neutron flux
        
        Args:
            reactivity: Total reactivity in delta-k/k
            dt: Time step in seconds
            
        Returns:
            Tuple of (flux_change, precursor_changes)
        """
        # Limit reactivity to prevent numerical instability
        reactivity = np.clip(reactivity, -0.9, 0.1)
        
        # For steady state operation (near critical), use conservative integration
        if abs(reactivity) < 0.01:  # Near critical (< 1000 pcm)
            # For essentially critical conditions, maintain steady flux
            flux_dot = 0.0
            if self.state.delayed_neutron_precursors is not None:
                precursor_dot = np.zeros_like(self.state.delayed_neutron_precursors)
            else:
                precursor_dot = np.zeros(6)
            return flux_dot * dt, precursor_dot * dt
        
        # Point kinetics with delayed neutrons
        flux_dot = (reactivity - self.BETA) / self.LAMBDA_PROMPT * self.state.neutron_flux
        if self.state.delayed_neutron_precursors is not None:
            for i in range(6):
                flux_dot += self.LAMBDA[i] * self.state.delayed_neutron_precursors[i]
        
        # Conservative flux changes for stability
        if abs(reactivity) < 0.0001:  # Very near critical (< 10 pcm)
            max_flux_change = self.state.neutron_flux * 0.0001  # Max 0.01% change per timestep
        elif abs(reactivity) < 0.001:  # Near critical (< 100 pcm)
            max_flux_change = self.state.neutron_flux * 0.001  # Max 0.1% change per timestep
        elif abs(reactivity) < 0.01:  # Moderately near critical (< 1000 pcm)
            max_flux_change = self.state.neutron_flux * 0.01  # Max 1% change per timestep
        else:
            max_flux_change = self.state.neutron_flux * 0.1  # Max 10% change per timestep
        
        flux_dot = np.clip(flux_dot, -max_flux_change, max_flux_change)
        
        # Delayed neutron precursor equations
        if self.state.delayed_neutron_precursors is not None:
            precursor_dot = np.zeros_like(self.state.delayed_neutron_precursors)
            for i in range(6):
                beta_i = self.BETA / 6  # Assume equal fractions for simplicity
                precursor_dot[i] = (beta_i / self.LAMBDA_PROMPT * self.state.neutron_flux - 
                                   self.LAMBDA[i] * self.state.delayed_neutron_precursors[i])
        else:
            precursor_dot = np.zeros(6)
        
        return flux_dot * dt, precursor_dot * dt
    
    def calculate_thermal_power(self) -> float:
        """
        Calculate thermal power from neutron flux
        
        Returns:
            Thermal power in MW
        """
        # Convert neutron flux to thermal power
        power_mw = np.clip(self.state.neutron_flux / 1e13 * self.rated_power_mw, 0, self.rated_power_mw * 1.2)
        return power_mw
    
    def update_fuel_temperature(self, thermal_power_mw: float, dt: float) -> float:
        """
        Update fuel temperature based on power and cooling
        
        Args:
            thermal_power_mw: Thermal power in MW
            dt: Time step in seconds
            
        Returns:
            Change in fuel temperature
        """
        # Heat generation from fission
        thermal_power_w = thermal_power_mw * 1e6  # Convert MW to W
        
        # Heat removal by coolant (simplified heat transfer)
        heat_transfer_coeff = 50000 + 2.0 * self.state.coolant_flow_rate
        heat_removal = heat_transfer_coeff * (self.state.fuel_temperature - self.state.coolant_temperature)
        
        # Fuel temperature dynamics
        fuel_temp_dot = (thermal_power_w - heat_removal) / (self.FUEL_MASS * self.FUEL_HEAT_CAPACITY)
        
        # Conservative temperature changes for steady state
        if abs(self.state.power_level - 100.0) < 5.0:  # Near 100% power
            fuel_temp_dot = np.clip(fuel_temp_dot, -1.0, 1.0)  # Max 1°C/s change
        else:
            fuel_temp_dot = np.clip(fuel_temp_dot, -10, 10)  # Max 10°C/s change
        
        return fuel_temp_dot * dt
    
    def update_coolant_temperature(self, thermal_power_mw: float, dt: float) -> float:
        """
        Update coolant temperature based on heat transfer
        
        Args:
            thermal_power_mw: Thermal power in MW
            dt: Time step in seconds
            
        Returns:
            Change in coolant temperature
        """
        # Heat transfer from fuel
        heat_transfer_coeff = 50000 + 2.0 * self.state.coolant_flow_rate
        heat_gain = heat_transfer_coeff * (self.state.fuel_temperature - self.state.coolant_temperature)
        
        # Heat removal by coolant flow
        heat_loss = (self.state.coolant_flow_rate * self.COOLANT_HEAT_CAPACITY * 
                    (self.state.coolant_temperature - 260))  # Assume 260°C inlet
        
        # Coolant temperature dynamics
        coolant_temp_dot = (heat_gain - heat_loss) / (self.COOLANT_MASS * self.COOLANT_HEAT_CAPACITY)
        
        # Conservative temperature changes for steady state
        if abs(self.state.power_level - 100.0) < 5.0:  # Near 100% power
            coolant_temp_dot = np.clip(coolant_temp_dot, -0.5, 0.5)  # Max 0.5°C/s change
        else:
            coolant_temp_dot = np.clip(coolant_temp_dot, -5, 5)  # Max 5°C/s change
        
        return coolant_temp_dot * dt
    
    def update_pressure(self, dt: float) -> float:
        """
        Update coolant pressure based on temperature
        
        Args:
            dt: Time step in seconds
            
        Returns:
            Change in pressure
        """
        # Simplified pressure dynamics based on temperature
        pressure_dot = 0.01 * (self.state.coolant_temperature - 280) - 0.001 * (
            self.state.coolant_pressure - 15.5
        )
        pressure_dot = np.clip(pressure_dot, -0.1, 0.1)  # Max 0.1 MPa/s change
        
        return pressure_dot * dt
    
    def check_safety_limits(self) -> Tuple[bool, str]:
        """
        Check if reactor core is within safety limits
        
        Returns:
            Tuple of (scram_required, reason)
        """
        if self.state.fuel_temperature > self.max_fuel_temp:
            return True, f"Fuel temperature {self.state.fuel_temperature:.1f}°C > {self.max_fuel_temp}°C"
        
        if self.state.coolant_pressure > self.max_coolant_pressure:
            return True, f"Coolant pressure {self.state.coolant_pressure:.1f} MPa > {self.max_coolant_pressure} MPa"
        
        if self.state.coolant_flow_rate < self.min_coolant_flow:
            return True, f"Coolant flow {self.state.coolant_flow_rate:.1f} kg/s < {self.min_coolant_flow} kg/s"
        
        if self.state.power_level > 120:
            return True, f"Power level {self.state.power_level:.1f}% > 120%"
        
        return False, ""
    
    def apply_scram(self) -> None:
        """Apply reactor scram (emergency shutdown)"""
        self.state.scram_status = True
        self.state.control_rod_position = 0  # All rods in
    
    def update(self, dt: float) -> Dict[str, Any]:
        """
        Update reactor physics for one time step
        
        Args:
            dt: Time step in seconds
            
        Returns:
            Dictionary with reactor status and parameters
        """
        # Update fission product concentrations
        fp_updates = self.reactivity_model.update_fission_products(
            self.state, self.state.neutron_flux, dt
        )
        self.state.xenon_concentration = fp_updates['xenon']
        self.state.iodine_concentration = fp_updates['iodine']
        self.state.samarium_concentration = fp_updates['samarium']
        
        # Calculate total reactivity
        total_reactivity, reactivity_components = self.reactivity_model.calculate_total_reactivity(
            self.state
        )
        
        # Convert from pcm to delta-k/k
        reactivity = total_reactivity / 100000.0
        
        if self.state.scram_status:
            reactivity = -0.5  # Large negative reactivity during scram
        
        # Solve neutron kinetics
        flux_change, precursor_change = self.point_kinetics(reactivity, dt)
        
        # Update neutron flux
        self.state.neutron_flux += flux_change
        self.state.neutron_flux = np.clip(self.state.neutron_flux, 1e8, 1e14)
        
        # Update delayed neutron precursors
        if self.state.delayed_neutron_precursors is not None:
            self.state.delayed_neutron_precursors += precursor_change
            self.state.delayed_neutron_precursors = np.clip(self.state.delayed_neutron_precursors, 0, 1)
        
        # Calculate thermal power
        thermal_power_mw = self.calculate_thermal_power()
        
        # Update thermal hydraulics
        fuel_temp_change = self.update_fuel_temperature(thermal_power_mw, dt)
        self.state.fuel_temperature += fuel_temp_change
        self.state.fuel_temperature = np.clip(self.state.fuel_temperature, 200, 2000)
        
        coolant_temp_change = self.update_coolant_temperature(thermal_power_mw, dt)
        self.state.coolant_temperature += coolant_temp_change
        self.state.coolant_temperature = np.clip(self.state.coolant_temperature, 200, 400)
        
        pressure_change = self.update_pressure(dt)
        self.state.coolant_pressure += pressure_change
        self.state.coolant_pressure = np.clip(self.state.coolant_pressure, 10, 20)
        
        # Update power level
        self.state.power_level = np.clip((self.state.neutron_flux / 1e13) * 100, 0, 150)
        
        # Store current reactivity
        self.state.reactivity = reactivity
        
        # Check safety limits
        scram_required, scram_reason = self.check_safety_limits()
        if scram_required and not self.state.scram_status:
            print(f"REACTOR SCRAM: {scram_reason}")
            self.apply_scram()
        
        # Check for NaN values and reset if necessary
        if (np.isnan(self.state.fuel_temperature) or np.isnan(self.state.neutron_flux)):
            print("Warning: NaN detected in reactor physics, resetting to safe values")
            self.state.neutron_flux = 1e12
            self.state.fuel_temperature = 600.0
            self.state.power_level = 100.0
        
        return {
            'thermal_power_mw': thermal_power_mw,
            'power_percent': self.state.power_level,
            'fuel_temperature': self.state.fuel_temperature,
            'coolant_temperature': self.state.coolant_temperature,
            'coolant_pressure': self.state.coolant_pressure,
            'neutron_flux': self.state.neutron_flux,
            'reactivity_pcm': total_reactivity,
            'reactivity_components': reactivity_components,
            'scram_status': self.state.scram_status,
            'control_rod_position': self.state.control_rod_position,
            'boron_concentration': self.state.boron_concentration
        }
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Get current reactor state as dictionary"""
        return {
            'neutron_flux': self.state.neutron_flux,
            'reactivity': self.state.reactivity,
            'fuel_temperature': self.state.fuel_temperature,
            'coolant_temperature': self.state.coolant_temperature,
            'coolant_pressure': self.state.coolant_pressure,
            'coolant_flow_rate': self.state.coolant_flow_rate,
            'power_level': self.state.power_level,
            'control_rod_position': self.state.control_rod_position,
            'steam_valve_position': self.state.steam_valve_position,
            'boron_concentration': self.state.boron_concentration,
            'xenon_concentration': self.state.xenon_concentration,
            'iodine_concentration': self.state.iodine_concentration,
            'samarium_concentration': self.state.samarium_concentration,
            'scram_status': self.state.scram_status,
            'fuel_burnup': self.state.fuel_burnup,
            'burnable_poison_worth': self.state.burnable_poison_worth
        }
    
    def reset(self) -> None:
        """Reset reactor to initial conditions"""
        self.state = ReactorState()
    
    def apply_control_action(self, action_type: str, magnitude: float = 1.0, dt: float = 1.0) -> None:
        """
        Apply control action to reactor state
        
        Args:
            action_type: Type of control action
            magnitude: Magnitude of action (0-1)
            dt: Time step for rate-limited actions
        """
        max_control_rod_speed = 5.0  # %/s
        max_flow_change_rate = 1000.0  # kg/s/s
        max_valve_speed = 10.0  # %/s
        max_boration_rate = 50.0  # ppm/s
        
        if action_type == "CONTROL_ROD_INSERT":
            self.state.control_rod_position = max(
                0, self.state.control_rod_position - max_control_rod_speed * dt * magnitude
            )
        elif action_type == "CONTROL_ROD_WITHDRAW":
            self.state.control_rod_position = min(
                100, self.state.control_rod_position + max_control_rod_speed * dt * magnitude
            )
        elif action_type == "INCREASE_COOLANT_FLOW":
            self.state.coolant_flow_rate = min(
                50000, self.state.coolant_flow_rate + max_flow_change_rate * dt * magnitude
            )
        elif action_type == "DECREASE_COOLANT_FLOW":
            self.state.coolant_flow_rate = max(
                5000, self.state.coolant_flow_rate - max_flow_change_rate * dt * magnitude
            )
        elif action_type == "OPEN_STEAM_VALVE":
            self.state.steam_valve_position = min(
                100, self.state.steam_valve_position + max_valve_speed * dt * magnitude
            )
        elif action_type == "CLOSE_STEAM_VALVE":
            self.state.steam_valve_position = max(
                0, self.state.steam_valve_position - max_valve_speed * dt * magnitude
            )
        elif action_type == "DILUTE_BORON":
            self.state.boron_concentration = max(
                0, self.state.boron_concentration - max_boration_rate * dt * magnitude
            )
        elif action_type == "BORATE_COOLANT":
            self.state.boron_concentration = min(
                3000, self.state.boron_concentration + max_boration_rate * dt * magnitude
            )
