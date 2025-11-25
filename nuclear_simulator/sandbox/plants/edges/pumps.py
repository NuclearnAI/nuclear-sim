
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional

# Import libraries
import math
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.edges.base import TransferEdge



# Create class for pumps
class Pump(TransferEdge):
    """
    Flows fluid between two nodes at a controllable mass flow rate.
    Attributes:
        deltaP:             [Pa]    Pressure increase provided by the pump
        m_dot:              [kg/s]  Mass flow rate
        D:                  [m]     Effective diameter of the pump
        L:                  [m]     Effective length of the pump
        f:                  [-]     Effective friction factor
        K_minor:            [-]     Effective minor loss coefficient
        monodirectional:    [-]     Whether the pump only allows flow in one direction
    """
    deltaP: float | None = None
    m_dot: float | None = None
    D: float
    L: float
    f: float
    K_minor: float = 0.0
    monodirectional: bool = True

    def __init__(self, **data) -> None:
        """Initialize pump edge."""
        # Call super init
        super().__init__(**data)

        # Initialize m_dot
        if (self.m_dot is None) and (self.deltaP is None):
            raise ValueError("Pump requires m_dot or deltaP to be specified.")
        elif self.m_dot is None:
            fluid_src: Gas | Liquid = self.get_contents_source()
            fluid_tgt: Gas | Liquid = self.get_contents_target()
            rho = (fluid_src.rho + fluid_tgt.rho) / 2
            sign = 1.0 if self.m_dot > 0 else -1.0
            A = math.pi * (self.D**2) / 4.0 
            K_t = self.f * self.L / self.D + self.K_minor
            K_t = max(K_t, 1e-6)  # Prevent division by zero
            C = A * math.sqrt(2.0 / K_t)
            m_dot = sign * C * math.sqrt(abs(self.deltaP) * rho)
            self.m_dot = m_dot
        elif self.deltaP is None:
            fluid_src: Gas | Liquid = self.get_contents_source()
            fluid_tgt: Gas | Liquid = self.get_contents_target()
            rho = (fluid_src.rho + fluid_tgt.rho) / 2
            sign = 1.0 if self.m_dot > 0 else -1.0
            A = math.pi * (self.D**2) / 4.0 
            K_t = self.f * self.L / self.D + self.K_minor
            K_t = max(K_t, 1e-6)  # Prevent division by zero
            C = A * math.sqrt(2.0 / K_t)
            deltaP = sign * (self.m_dot / C)**2 / rho
            self.deltaP = deltaP
        else:
            raise ValueError("Either m_dot or deltaP must be None for pump initialization.")

        # Done
        return

    def calculate_material_flow(self, dt: float) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update.
        Returns:
            flow:  Material flow rates (kg/s, J/s) keyed by field name
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

        # Calculate constants
        rho = (fluid_src.rho + fluid_tgt.rho) / 2
        A = math.pi * (self.D**2) / 4.0 
        K_t = self.f * self.L / self.D + self.K_minor
        K_t = max(K_t, 1e-6)  # Prevent division by zero
        C = A * math.sqrt(2.0 / K_t)
        tau = 2 * A * self.L / K_t

        # Calculate flow rate from pressure difference
        dP = P_src - P_tgt + self.deltaP
        sign = 1.0 if dP > 0 else -1.0
        m_dot = sign * C * math.sqrt(abs(dP) * rho)

        # Add inertia
        m_dot_prev = self.m_dot or m_dot
        alpha = min(dt / tau, 1.0)
        m_dot = alpha * m_dot + (1.0 - alpha) * m_dot_prev

        # Enforce mono-directional flow if specified
        if self.monodirectional:
            m_dot = max(m_dot, 0.0)

        # Calculate energy flow rate based on mass flow and energy density
        if m_dot > 0:
            U_dot = m_dot * (fluid_src.U / fluid_src.m)
        else:
            U_dot = m_dot * (fluid_tgt.U / fluid_tgt.m)

        # Create fluid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)  # Nodes handle volume
        else:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Store state
        self.m_dot = m_dot

        # Return output
        return fluid_flow
    

# Class for liquid pumps
class LiquidPump(Pump):
    """
    Pumps liquid between two nodes at a controllable mass flow rate.
    """
    D: float = 0.90
    L: float = 15.0
    f: float = 0.015
    K_minor: float = 2.0

# Class for gas pumps
class GasPump(Pump):
    """
    Pumps gas between two nodes at a controllable mass flow rate.
    """
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
    pipe = LiquidPump(
        node_source=node1, 
        node_target=node2, 
        m_dot=100.0,
    )
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
