# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.plants.thermograph import (
        ThermoNode, Edge
    )

# Import libraries
from nuclear_simulator.sandbox.plants.physics import (
    calc_pipe_mass_flow,
    calc_energy_from_temperature,
)


class Pipe(Edge):
    """
    Pipe edge: advects mass and internal energy from source → target.
    Flow is computed from pressure drop via Darcy–Weisbach (lumped).
    """

    # Geometry / hydraulics
    D: float = 0.7        # [m]     Inner diameter
    L: float = 12.0       # [m]     Length
    f: float = 0.02       # [-]     Darcy friction factor (lumped)
    K_minor: float = 1.0  # [-]     Lumped minor-loss coefficient

    # Which fluid on the node this pipe moves (prefix for fields)
    fluid_prefix: str = "coolant"

    def calculate_flows(
            self, 
            dt: float, 
            node_source: ThermoNode, 
            node_target: ThermoNode
        ) -> dict[str, float]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:          [s] Time step for the update. (unused)
            node_source: Source node (upstream)
            node_target: Target node (downstream)
        Returns:
            flows:       Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get fluid prefix
        pfx = self.fluid_prefix

        # Get variables
        P_up = getattr(node_source, f"{pfx}_P")
        P_dn = getattr(node_target, f"{pfx}_P")
        rho  = getattr(node_source, f"{pfx}_rho")

        # Mass flow rate from pressure drop
        m_dot = calc_pipe_mass_flow(
            P_up=P_up, 
            P_dn=P_dn, 
            rho=self.rho,
            D=self.D, 
            L=self.L, 
            f=self.f, 
            K_minor=self.K_minor,
        )

        # Advect internal energy with the upstream state
        if m_dot > 0:
            T  = getattr(node_source, f"{pfx}_T")
            cp = getattr(node_source, f"{pfx}_cp")
            U_dot  = calc_energy_from_temperature(m=m_dot, T=T, cv=cp)
        else:
            T  = getattr(node_target, f"{pfx}_T")
            cp = getattr(node_target, f"{pfx}_cp")
            U_dot  = calc_energy_from_temperature(m=m_dot, T=T, cv=cp)

        # Package flows
        flows = {
            f"{pfx}_m": m_dot,   # [kg/s]
            f"{pfx}_U": U_dot,   # [J/s]
        }

        # Return output
        return flows



class Pump(Edge):
    """
    Pump edge: imposes a commanded mass flow (no energy addition here).
    Controller sets m_dot_setpoint. Energy is simply advected with source state.
    """

    # Control / setpoint
    m_dot_setpoint: float = 5000.0  # [kg/s] default commanded flow

    # Fluid selection (prefix for fields)
    fluid_prefix: str = "coolant"

    def calculate_flows(self, dt: float, node_source: Node, node_target: Node) -> dict[str, float]:
        """
        Returns instantaneous rates (per second). Node integration will multiply by dt.
        """
        pfx  = self.fluid_prefix
        mdot = self.m_dot_setpoint

        # Advect internal energy with upstream properties
        T_src  = getattr(node_source, f"{pfx}_T")
        cp_src = getattr(node_source, f"{pfx}_cp")
        U_dot  = mdot * cp_src * T_src

        return {
            f"{pfx}_m": mdot,  # [kg/s]
            f"{pfx}_U": U_dot, # [J/s]
        }
    
