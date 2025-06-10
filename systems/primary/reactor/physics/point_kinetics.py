"""
Point Kinetics Model

This module implements the point kinetics equations for nuclear reactor physics,
including delayed neutron precursor calculations.
"""

import numpy as np
from typing import Tuple


class PointKineticsModel:
    """
    Point kinetics model for nuclear reactor neutron flux calculations
    """

    def __init__(self):
        """Initialize point kinetics model with physical constants"""
        # Physical constants
        self.BETA = 0.0065  # Total delayed neutron fraction
        self.LAMBDA = np.array(
            [0.077, 0.311, 1.40, 3.87, 1.40, 0.195]
        )  # Decay constants
        self.LAMBDA_PROMPT = 1e-5  # Prompt neutron generation time

    def solve_point_kinetics(self, reactivity: float, reactor_state) -> Tuple[float, np.ndarray]:
        """
        Solve point kinetics equations for neutron flux
        
        Args:
            reactivity: Reactivity in delta-k/k
            reactor_state: Current reactor state
            
        Returns:
            Tuple of (flux_dot, precursor_dot)
        """
        # Limit reactivity to prevent numerical instability
        reactivity = np.clip(reactivity, -0.9, 0.1)

        # For steady state operation, use conservative integration
        if abs(reactivity) < 0.01:  # Near critical
            flux_dot = 0.0
            precursor_dot = np.zeros_like(reactor_state.delayed_neutron_precursors)
            return flux_dot, precursor_dot

        # For very small reactivity changes, use conservative approach
        if abs(reactivity) < 0.01:  # < 1000 pcm
            effective_reactivity = reactivity * 0.01  # Reduce sensitivity
        else:
            effective_reactivity = reactivity

        # Point kinetics with delayed neutrons
        flux_dot = (
            (effective_reactivity - self.BETA)
            / self.LAMBDA_PROMPT
            * reactor_state.neutron_flux
        )
        for i in range(6):
            flux_dot += self.LAMBDA[i] * reactor_state.delayed_neutron_precursors[i]

        # Conservative flux changes for stability
        if abs(reactivity) < 0.0001:  # Very near critical
            max_flux_change = reactor_state.neutron_flux * 0.0001
        elif abs(reactivity) < 0.001:  # Near critical
            max_flux_change = reactor_state.neutron_flux * 0.001
        elif abs(reactivity) < 0.01:  # Moderately near critical
            max_flux_change = reactor_state.neutron_flux * 0.01
        else:
            max_flux_change = reactor_state.neutron_flux * 0.1

        flux_dot = np.clip(flux_dot, -max_flux_change, max_flux_change)

        # Delayed neutron precursor equations
        precursor_dot = np.zeros_like(reactor_state.delayed_neutron_precursors)
        for i in range(6):
            beta_i = self.BETA / 6  # Assume equal fractions
            precursor_dot[i] = (
                beta_i / self.LAMBDA_PROMPT * reactor_state.neutron_flux
                - self.LAMBDA[i] * reactor_state.delayed_neutron_precursors[i]
            )

        return flux_dot, precursor_dot

    def update_neutron_flux(self, reactor_state, flux_dot: float, dt: float) -> None:
        """
        Update neutron flux based on point kinetics solution
        
        Args:
            reactor_state: Current reactor state
            flux_dot: Rate of change of neutron flux
            dt: Time step
        """
        reactor_state.neutron_flux += flux_dot * dt
        reactor_state.neutron_flux = np.clip(reactor_state.neutron_flux, 1e8, 1e14)

    def update_precursors(self, reactor_state, precursor_dot: np.ndarray, dt: float) -> None:
        """
        Update delayed neutron precursors
        
        Args:
            reactor_state: Current reactor state
            precursor_dot: Rate of change of precursor concentrations
            dt: Time step
        """
        if reactor_state.delayed_neutron_precursors is not None:
            reactor_state.delayed_neutron_precursors += precursor_dot * dt
            reactor_state.delayed_neutron_precursors = np.clip(
                reactor_state.delayed_neutron_precursors, 0, 1
            )

    def calculate_power_from_flux(self, neutron_flux: float, rated_power_mw: float = 3000.0) -> Tuple[float, float]:
        """
        Calculate thermal power and power percentage from neutron flux
        
        Args:
            neutron_flux: Neutron flux in n/cm²/s
            rated_power_mw: Rated thermal power in MW
            
        Returns:
            Tuple of (thermal_power_mw, power_percent)
        """
        # Power from neutron flux (simplified conversion)
        thermal_power_mw = np.clip(neutron_flux / 1e12 * rated_power_mw, 0, 4000)
        power_percent = (neutron_flux / 1e13) * 100
        power_percent = np.clip(power_percent, 0, 150)
        
        return thermal_power_mw, power_percent
