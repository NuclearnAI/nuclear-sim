
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional

# Import libraries
import math
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.transfer.base import TransferEdge
from nuclear_simulator.sandbox.physics import (
    calc_incompressible_mass_flow,
    calc_compressible_mass_flow,
    calc_energy_from_temperature,
)


# Class for pipes
class Pipe(TransferEdge):
    """
    Flows fluid between two nodes based on pressure difference using Darcy-Weisbach.
    Attributes:
        m_dot:              [kg/s]  Last-calculated mass flow rate
        D:                  [m]     Inner diameter
        L:                  [m]     Length
        f:                  [-]     Darcy friction factor (lumped)
        K_minor:            [-]     Lumped minor-loss coefficient
        monodirectional:    [-]     If True, flow is only allowed from source to target.
        MAX_FLOW_FRACTION:  [-]     Maximum fraction of node mass that can flow per time step.
    """
    m_dot: float | None = None
    D: float
    L: float
    f: float
    K_minor: float
    monodirectional: bool = False
    max_flow_fraction: float = 0.1

    def calculate_material_flow(self, dt: float) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update.
        Returns:
            flows:  Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        fluid_src: Gas | Liquid = self.get_contents_source()
        fluid_tgt: Gas | Liquid = self.get_contents_target()
        P_src = self.get_field_source("P")
        P_tgt = self.get_field_target("P")

        # Get fluid properties
        if isinstance(fluid_src, Gas):
            fluid_type = Gas
        elif isinstance(fluid_src, Liquid):
            fluid_type = Liquid
        else:
            raise TypeError("Pipe material must be Gas or Liquid.")
        fluid_class = type(fluid_src)

        # Get edge parameters
        D = self.D
        L = self.L
        f = self.f
        K_minor = self.K_minor

        # Calculate constants
        A = math.pi * (D**2) / 4.0
        K_t = f * (L / D) + K_minor
        K_t = max(K_t, 1e-6)  # Prevent div by zero
        tau = 2 * A * L / K_t
        alpha = min(dt / tau, 1.0)

        # Calculate mass flow rate from pressure drop
        if fluid_type is Gas:
            m_dot = calc_compressible_mass_flow(
                P1=P_src,
                P2=P_tgt,
                T1=fluid_src.T,
                T2=fluid_tgt.T,
                MW=fluid_src.MW, 
                D=D, 
                L=L, 
                f=f, 
                K_minor=K_minor,
            )
        elif fluid_type is Liquid:
            rho = (fluid_src.rho + fluid_tgt.rho) / 2
            m_dot = calc_incompressible_mass_flow(
                P1=P_src,
                P2=P_tgt,
                rho=rho,
                D=D, 
                L=L, 
                f=f, 
                K_minor=K_minor,
            )

        # Add inertia
        m_dot_prev = self.m_dot or m_dot  # Use current if None
        m_dot = alpha * m_dot + (1.0 - alpha) * m_dot_prev

        # Enforce mono-directional flow if specified
        if self.monodirectional:
            m_dot = max(m_dot, 0.0)

        # Calculate energy flow rate based on mass flow and energy density
        if m_dot > 0:
            m_dot = min(m_dot, self.max_flow_fraction * fluid_src.m / dt)
            U_dot = m_dot * (fluid_src.U / fluid_src.m)
        else:
            m_dot = max(m_dot, -self.max_flow_fraction * fluid_tgt.m / dt)
            U_dot = m_dot * (fluid_tgt.U / fluid_tgt.m)

        # Create liquid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Store state
        self.m_dot = m_dot

        # Return output
        return fluid_flow


# Class for liquid pipes
class LiquidPipe(Pipe):
    """A Pipe for liquids."""
    D: float = 0.90
    L: float = 15.0
    f: float = 0.015
    K_minor: float = 2.0

# Class for gas pipes
class GasPipe(Pipe):
    """A Pipe for gases."""
    D: float = 0.45
    L: float = 15.0
    f: float = 0.015
    K_minor: float = 2.0

    

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel
    from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater
    # Create nodes and pipe
    node1 = PressurizedLiquidVessel(contents=PWRPrimaryWater(m=1000.0, U=1e6), P=2e7)
    node2 = PressurizedLiquidVessel(contents=PWRPrimaryWater(m=1000.0, U=1e6), P=1e7)
    pipe = LiquidPipe(node_source=node1, node_target=node2)
    # Update graph
    dt = 0.1
    pipe.update(dt)
    node1.update(dt)
    node2.update(dt)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
