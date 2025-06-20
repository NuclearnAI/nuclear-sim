"""
Neutronics Model

This module implements neutronics calculations for nuclear reactor simulation,
including control rod reactivity and neutron flux management.
"""

import numpy as np
from typing import Dict

class NeutronicsModel:
    """
    Neutronics model for nuclear reactor neutron physics calculations
    """

    def __init__(self):
        """Initialize neutronics model"""
        pass

    def calculate_control_rod_reactivity(self, position: float) -> float:
        """
        Calculate reactivity based on control rod position
        
        Args:
            position: Control rod position (% withdrawn, 0-100)
            
        Returns:
            Reactivity in delta-k/k
        """
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

    def calculate_neutron_flux_from_power(self, power_percent: float, rated_flux: float = 1e13) -> float:
        """
        Calculate neutron flux from power level
        
        Args:
            power_percent: Power level as percentage
            rated_flux: Rated neutron flux at 100% power
            
        Returns:
            Neutron flux in n/cm²/s
        """
        return rated_flux * (power_percent / 100.0)

    def calculate_power_from_neutron_flux(self, neutron_flux: float, rated_flux: float = 1e13) -> float:
        """
        Calculate power percentage from neutron flux
        
        Args:
            neutron_flux: Neutron flux in n/cm²/s
            rated_flux: Rated neutron flux at 100% power
            
        Returns:
            Power level as percentage
        """
        return (neutron_flux / rated_flux) * 100.0

    def validate_neutron_flux(self, neutron_flux: float) -> float:
        """
        Validate and clip neutron flux to safe operating range
        
        Args:
            neutron_flux: Input neutron flux
            
        Returns:
            Validated neutron flux
        """
        return np.clip(neutron_flux, 1e8, 1e14)

    def calculate_thermal_power_from_flux(self, neutron_flux: float, rated_power_mw: float = 3000.0) -> float:
        """
        Calculate thermal power from neutron flux
        
        Args:
            neutron_flux: Neutron flux in n/cm²/s
            rated_power_mw: Rated thermal power in MW
            
        Returns:
            Thermal power in MW
        """
        # Power from neutron flux (simplified conversion)
        # Limit thermal power to reasonable range
        thermal_power = np.clip(
            neutron_flux / 1e12 * rated_power_mw, 0, 4000
        )  # MW (max 4000 MW)
        
        return thermal_power

    def get_neutronics_status(self, reactor_state) -> Dict[str, float]:
        """
        Get current neutronics status
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Dictionary with neutronics parameters
        """
        return {
            "neutron_flux": reactor_state.neutron_flux,
            "power_level": reactor_state.power_level,
            "reactivity": reactor_state.reactivity,
            "control_rod_position": reactor_state.control_rod_position,
            "control_rod_reactivity": self.calculate_control_rod_reactivity(
                reactor_state.control_rod_position
            ),
        }
