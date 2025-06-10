"""
Heat Transfer Model

This module implements heat transfer calculations for nuclear reactor simulation,
including heat transfer coefficients and thermal coupling between components.
"""

import numpy as np
from typing import Dict


class HeatTransferModel:
    """
    Heat transfer model for nuclear reactor thermal calculations
    """

    def __init__(self):
        """Initialize heat transfer model with physical constants"""
        # Heat transfer constants
        self.base_heat_transfer_coeff = 50000.0  # Base heat transfer coefficient
        self.flow_coefficient = 2.0  # Flow rate dependency coefficient

    def calculate_heat_transfer_coefficient(self, coolant_flow_rate: float) -> float:
        """
        Calculate heat transfer coefficient based on flow rate
        
        Args:
            coolant_flow_rate: Coolant flow rate in kg/s
            
        Returns:
            Heat transfer coefficient in W/K
        """
        # Simplified correlation: h = h_base + k * flow_rate
        return self.base_heat_transfer_coeff + self.flow_coefficient * coolant_flow_rate

    def calculate_heat_removal(self, reactor_state) -> float:
        """
        Calculate heat removal from fuel to coolant
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Heat removal rate in watts
        """
        heat_transfer_coeff = self.calculate_heat_transfer_coefficient(
            reactor_state.coolant_flow_rate
        )
        
        temperature_difference = (
            reactor_state.fuel_temperature - reactor_state.coolant_temperature
        )
        
        return heat_transfer_coeff * temperature_difference

    def calculate_fuel_to_coolant_heat_transfer(
        self, 
        fuel_temp: float, 
        coolant_temp: float, 
        coolant_flow_rate: float
    ) -> float:
        """
        Calculate heat transfer from fuel to coolant
        
        Args:
            fuel_temp: Fuel temperature in °C
            coolant_temp: Coolant temperature in °C
            coolant_flow_rate: Coolant flow rate in kg/s
            
        Returns:
            Heat transfer rate in watts
        """
        heat_transfer_coeff = self.calculate_heat_transfer_coefficient(coolant_flow_rate)
        temperature_difference = fuel_temp - coolant_temp
        
        return heat_transfer_coeff * temperature_difference

    def calculate_coolant_heat_loss(self, reactor_state) -> float:
        """
        Calculate heat loss from coolant to environment/steam generator
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Heat loss rate in watts
        """
        # Simplified model: heat loss proportional to flow rate and temperature difference
        coolant_heat_capacity = 5200.0  # J/kg/K
        reference_temp = 260.0  # °C (inlet temperature)
        
        heat_loss = (
            reactor_state.coolant_flow_rate
            * coolant_heat_capacity
            * (reactor_state.coolant_temperature - reference_temp)
        )
        
        return heat_loss

    def get_heat_transfer_status(self, reactor_state) -> Dict[str, float]:
        """
        Get current heat transfer status
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Dictionary with heat transfer parameters
        """
        heat_transfer_coeff = self.calculate_heat_transfer_coefficient(
            reactor_state.coolant_flow_rate
        )
        heat_removal = self.calculate_heat_removal(reactor_state)
        heat_loss = self.calculate_coolant_heat_loss(reactor_state)
        
        return {
            "heat_transfer_coefficient": heat_transfer_coeff,
            "heat_removal_rate": heat_removal,
            "coolant_heat_loss": heat_loss,
            "fuel_coolant_temp_diff": reactor_state.fuel_temperature - reactor_state.coolant_temperature,
            "coolant_flow_rate": reactor_state.coolant_flow_rate,
        }

    def validate_heat_transfer_parameters(self, reactor_state) -> bool:
        """
        Validate heat transfer parameters are within reasonable ranges
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            True if parameters are valid, False otherwise
        """
        # Check for reasonable temperature ranges
        if reactor_state.fuel_temperature < 200 or reactor_state.fuel_temperature > 2000:
            return False
        
        if reactor_state.coolant_temperature < 200 or reactor_state.coolant_temperature > 400:
            return False
        
        # Check for positive flow rate
        if reactor_state.coolant_flow_rate <= 0:
            return False
        
        # Check for reasonable temperature difference
        temp_diff = reactor_state.fuel_temperature - reactor_state.coolant_temperature
        if temp_diff < 0 or temp_diff > 1000:
            return False
        
        return True
