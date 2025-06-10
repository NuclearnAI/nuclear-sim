"""
Thermal Hydraulics Model

This module implements thermal hydraulic calculations for nuclear reactor simulation,
including heat transfer, temperature dynamics, and pressure calculations.
"""

import numpy as np
from typing import Dict


class ThermalHydraulicsModel:
    """
    Thermal hydraulics model for nuclear reactor heat transfer calculations
    """

    def __init__(self):
        """Initialize thermal hydraulics model with physical constants"""
        # Physical constants
        self.FUEL_HEAT_CAPACITY = 300.0  # J/kg/K
        self.COOLANT_HEAT_CAPACITY = 5200.0  # J/kg/K
        self.FUEL_MASS = 100000.0  # kg
        self.COOLANT_MASS = 300000.0  # kg

    def calculate_thermal_hydraulics(self, reactor_state, thermal_power: float) -> Dict[str, float]:
        """
        Calculate thermal hydraulic parameters from given thermal power
        
        Args:
            reactor_state: Current reactor state
            thermal_power: Thermal power in watts
            
        Returns:
            Dictionary with thermal hydraulic derivatives
        """
        # Fuel temperature dynamics
        heat_removal = self.calculate_heat_transfer_coefficient(reactor_state) * (
            reactor_state.fuel_temperature - reactor_state.coolant_temperature
        )
        fuel_temp_dot = (thermal_power - heat_removal) / (
            self.FUEL_MASS * self.FUEL_HEAT_CAPACITY
        )

        # For steady state, limit temperature changes very strictly
        if abs(reactor_state.power_level - 100.0) < 5.0:  # Near 100% power
            fuel_temp_dot = np.clip(
                fuel_temp_dot, -1.0, 1.0
            )  # Max 1°C/s change for steady state
        else:
            fuel_temp_dot = np.clip(
                fuel_temp_dot, -10, 10
            )  # Max 10°C/s change for transients

        # Coolant temperature dynamics - improved heat balance
        coolant_heat_gain = heat_removal
        
        # Heat loss to steam generators (more realistic calculation)
        # Use a reference temperature closer to actual cold leg temperature
        reference_temp = 293.0  # Typical PWR cold leg temperature
        coolant_heat_loss = (
            reactor_state.coolant_flow_rate
            * self.COOLANT_HEAT_CAPACITY
            * (reactor_state.coolant_temperature - reference_temp) / 1000.0  # Convert to MW
        )
        
        # Net heat change in coolant
        net_coolant_heat = coolant_heat_gain - coolant_heat_loss
        coolant_temp_dot = net_coolant_heat / (
            self.COOLANT_MASS * self.COOLANT_HEAT_CAPACITY
        )

        # For steady state, limit coolant temperature changes
        if abs(reactor_state.power_level - 100.0) < 5.0:  # Near 100% power
            coolant_temp_dot = np.clip(
                coolant_temp_dot, -0.5, 0.5
            )  # Max 0.5°C/s change for steady state
        else:
            coolant_temp_dot = np.clip(
                coolant_temp_dot, -5, 5
            )  # Max 5°C/s change for transients

        # Pressure dynamics (more stable)
        # Pressure should be relatively stable in normal operation
        target_pressure = 15.5  # MPa - typical PWR operating pressure
        
        # Small pressure variations based on temperature (thermal expansion)
        temp_pressure_effect = 0.002 * (reactor_state.coolant_temperature - 293.0)  # Reduced sensitivity
        
        # Pressure regulation (pressurizer control)
        pressure_error = reactor_state.coolant_pressure - (target_pressure + temp_pressure_effect)
        pressure_dot = -0.01 * pressure_error  # Proportional control to maintain target pressure
        
        # Limit pressure change rate for stability
        pressure_dot = np.clip(pressure_dot, -0.05, 0.05)  # Max 0.05 MPa/s change

        return {
            "fuel_temp_dot": fuel_temp_dot,
            "coolant_temp_dot": coolant_temp_dot,
            "pressure_dot": pressure_dot,
            "thermal_power": thermal_power,
        }

    def calculate_heat_transfer_coefficient(self, reactor_state) -> float:
        """
        Calculate heat transfer coefficient based on flow rate
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Heat transfer coefficient
        """
        # Simplified correlation
        return 50000 + 2.0 * reactor_state.coolant_flow_rate

    def update_thermal_state(self, reactor_state, thermal_params: Dict[str, float], dt: float) -> None:
        """
        Update thermal hydraulic state variables
        
        Args:
            reactor_state: Current reactor state
            thermal_params: Thermal parameter derivatives
            dt: Time step
        """
        # Update fuel temperature
        reactor_state.fuel_temperature += thermal_params["fuel_temp_dot"] * dt
        reactor_state.fuel_temperature = np.clip(reactor_state.fuel_temperature, 200, 2000)

        # Update coolant temperature
        reactor_state.coolant_temperature += thermal_params["coolant_temp_dot"] * dt
        reactor_state.coolant_temperature = np.clip(reactor_state.coolant_temperature, 200, 400)

        # Update coolant pressure
        reactor_state.coolant_pressure += thermal_params["pressure_dot"] * dt
        reactor_state.coolant_pressure = np.clip(reactor_state.coolant_pressure, 10, 20)

    def calculate_steam_cycle(self, reactor_state) -> Dict[str, float]:
        """
        Calculate steam cycle parameters
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Dictionary with steam cycle derivatives
        """
        # Steam generation rate based on heat transfer
        steam_generation = min(
            reactor_state.coolant_flow_rate * 0.05,
            reactor_state.steam_valve_position / 100 * 2000,
        )

        # Steam temperature and pressure dynamics
        steam_temp_dot = 0.1 * (
            reactor_state.coolant_temperature - reactor_state.steam_temperature
        )
        steam_pressure_dot = 0.05 * (steam_generation - reactor_state.steam_flow_rate)

        # Mass balance
        steam_flow_dot = reactor_state.steam_valve_position / 100 * 20 - 10
        feedwater_flow_dot = steam_generation - reactor_state.feedwater_flow_rate

        return {
            "steam_temp_dot": steam_temp_dot,
            "steam_pressure_dot": steam_pressure_dot,
            "steam_flow_dot": steam_flow_dot,
            "feedwater_flow_dot": feedwater_flow_dot,
        }

    def update_steam_state(self, reactor_state, steam_params: Dict[str, float], dt: float) -> None:
        """
        Update steam cycle state variables
        
        Args:
            reactor_state: Current reactor state
            steam_params: Steam parameter derivatives
            dt: Time step
        """
        # Update steam temperature
        reactor_state.steam_temperature += steam_params["steam_temp_dot"] * dt
        reactor_state.steam_temperature = np.clip(reactor_state.steam_temperature, 200, 400)

        # Update steam pressure
        reactor_state.steam_pressure += steam_params["steam_pressure_dot"] * dt
        reactor_state.steam_pressure = np.clip(reactor_state.steam_pressure, 1, 10)

        # Update steam flow rate
        reactor_state.steam_flow_rate += steam_params["steam_flow_dot"] * dt
        reactor_state.steam_flow_rate = np.clip(reactor_state.steam_flow_rate, 0, 3000)

        # Update feedwater flow rate
        reactor_state.feedwater_flow_rate += steam_params["feedwater_flow_dot"] * dt
        reactor_state.feedwater_flow_rate = np.clip(reactor_state.feedwater_flow_rate, 0, 3000)

    def check_for_nan_values(self, reactor_state) -> bool:
        """
        Check for NaN values and reset if necessary
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            True if NaN values were found and reset
        """
        if (
            np.isnan(reactor_state.fuel_temperature)
            or np.isnan(reactor_state.neutron_flux)
            or np.isnan(reactor_state.coolant_temperature)
            or np.isnan(reactor_state.coolant_pressure)
        ):
            print("Warning: NaN detected, resetting to safe values")
            reactor_state.neutron_flux = 1e12
            reactor_state.fuel_temperature = 600.0
            reactor_state.coolant_temperature = 280.0
            reactor_state.coolant_pressure = 15.5
            reactor_state.power_level = 100.0
            return True
        return False
