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

        # Import physics models
        from ..reactivity_model import ReactivityModel
        from ..physics.point_kinetics import PointKineticsModel
        from ..physics.thermal_hydraulics import ThermalHydraulicsModel
        from ..physics.neutronics import NeutronicsModel
        from ..safety.scram_logic import ScramSystem

        self.reactivity_model = ReactivityModel()
        self.point_kinetics = PointKineticsModel()
        self.thermal_hydraulics = ThermalHydraulicsModel()
        self.neutronics = NeutronicsModel()
        self.scram_system = ScramSystem()

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

        # Solve point kinetics equations using the physics model
        flux_dot, precursor_dot = self.point_kinetics.solve_point_kinetics(reactivity, reactor_state)

        # Update neutron flux using the physics model
        self.point_kinetics.update_neutron_flux(reactor_state, flux_dot, dt)

        # Update delayed neutron precursors using the physics model
        self.point_kinetics.update_precursors(reactor_state, precursor_dot, dt)

        # Calculate thermal power from neutron flux using the physics model
        thermal_power_mw, power_percent = self.point_kinetics.calculate_power_from_flux(
            reactor_state.neutron_flux, self.rated_power_mw
        )

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
