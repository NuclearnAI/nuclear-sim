"""
Reactor Heat Source Implementation

This module provides a reactor physics-based heat source that wraps
the existing reactor physics calculations.
"""

from typing import Any, Dict

import numpy as np

from .heat_source_interface import HeatSource


class ReactorHeatSource(HeatSource):
    """Heat source based on reactor physics calculations"""

    def __init__(self, rated_power_mw: float = 3000.0):
        """
        Initialize reactor heat source

        Args:
            rated_power_mw: Rated thermal power in MW
        """
        super().__init__(rated_power_mw)

        # Import reactivity model
        from ..reactivity_model import ReactivityModel

        self.reactivity_model = ReactivityModel()

        # Physics constants
        self.BETA = 0.0065  # Total delayed neutron fraction
        self.LAMBDA = np.array(
            [0.077, 0.311, 1.40, 3.87, 1.40, 0.195]
        )  # Decay constants
        self.LAMBDA_PROMPT = 1e-5  # Prompt neutron generation time

    def update(self, dt: float, **kwargs) -> Dict[str, Any]:
        """
        Update reactor physics and return heat source status

        Args:
            dt: Time step in seconds
            **kwargs: Additional parameters including reactor_state and control_action

        Returns:
            Dictionary with heat source status
        """
        reactor_state = kwargs.get("reactor_state")
        control_action = kwargs.get("control_action")

        if reactor_state is None:
            # Return default values if no state provided
            return {
                "thermal_power_mw": self.rated_power_mw,
                "power_percent": 100.0,
                "available": True,
                "reactivity_pcm": 0.0,
                "neutron_flux": 1e13,
            }

        # Update fission product concentrations
        fp_updates = self.reactivity_model.update_fission_products(
            reactor_state, reactor_state.neutron_flux, dt
        )
        reactor_state.xenon_concentration = fp_updates["xenon"]
        reactor_state.iodine_concentration = fp_updates["iodine"]
        reactor_state.samarium_concentration = fp_updates["samarium"]

        # Calculate total reactivity using comprehensive model
        total_reactivity, reactivity_components = (
            self.reactivity_model.calculate_total_reactivity(reactor_state)
        )

        # Convert from pcm to delta-k/k
        reactivity = total_reactivity / 100000.0  # pcm to delta-k/k

        if reactor_state.scram_status:
            reactivity = -0.5  # Large negative reactivity during scram

        # Solve point kinetics equations
        flux_dot, precursor_dot = self._point_kinetics(reactivity, reactor_state)

        # Update neutron flux
        reactor_state.neutron_flux += flux_dot * dt
        reactor_state.neutron_flux = np.clip(reactor_state.neutron_flux, 1e8, 1e14)

        # Update delayed neutron precursors
        if reactor_state.delayed_neutron_precursors is not None:
            reactor_state.delayed_neutron_precursors += precursor_dot * dt
            reactor_state.delayed_neutron_precursors = np.clip(
                reactor_state.delayed_neutron_precursors, 0, 1
            )

        # Calculate thermal power from neutron flux
        thermal_power_mw = np.clip(reactor_state.neutron_flux / 1e12 * 3000, 0, 4000)
        power_percent = (reactor_state.neutron_flux / 1e13) * 100
        power_percent = np.clip(power_percent, 0, 150)

        # Update reactor state power level
        reactor_state.power_level = power_percent
        reactor_state.reactivity = reactivity

        return {
            "thermal_power_mw": thermal_power_mw,
            "power_percent": power_percent,
            "available": not reactor_state.scram_status,
            "reactivity_pcm": total_reactivity,
            "neutron_flux": reactor_state.neutron_flux,
            "reactivity_components": reactivity_components,
        }

    def _point_kinetics(self, reactivity: float, reactor_state) -> tuple:
        """Solve point kinetics equations for neutron flux"""
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

    def get_thermal_power_mw(self) -> float:
        """Get current thermal power output"""
        return self.current_power_mw

    def get_power_percent(self) -> float:
        """Get current power as percentage of rated"""
        return (self.current_power_mw / self.rated_power_mw) * 100.0

    def set_power_setpoint(self, power_percent: float) -> None:
        """
        Set power setpoint (not directly applicable for reactor physics)

        Args:
            power_percent: Target power percentage
        """
        self.power_setpoint_percent = power_percent
        # Note: Reactor power is controlled by reactivity, not direct setpoint

    def get_state_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary for logging/monitoring"""
        return {
            "type": "reactor",
            "thermal_power_mw": self.current_power_mw,
            "power_percent": self.get_power_percent(),
            "rated_power_mw": self.rated_power_mw,
            "setpoint_percent": self.power_setpoint_percent,
            "available": True,
        }

    def reset(self) -> None:
        """Reset heat source to initial conditions"""
        self.current_power_mw = self.rated_power_mw
        self.power_setpoint_percent = 100.0

    def get_status(self) -> Dict[str, Any]:
        """
        Get current heat source status

        Returns:
            Dictionary with status information
        """
        return {
            "type": "reactor",
            "rated_power_mw": self.rated_power_mw,
            "controllable": False,  # Controlled via reactivity, not direct power
            "response_time": "Physics-based",
            "description": "Nuclear reactor with full physics simulation",
        }
