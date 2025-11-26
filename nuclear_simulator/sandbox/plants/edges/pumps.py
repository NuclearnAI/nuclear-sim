
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
import math
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.edges.base import TransferEdge


# Class for pumps
class Pump(TransferEdge):
    """
    Flows fluid between two nodes based on pressure difference and inertia.
    
    Attributes:
        m_dot:              [kg/s]       Previous mass flow rate for first-order response
        K:                  [kg/(s·√Pa)] Flow conductance coefficient
        tau:                [s]          Response time constant
        dP_added:           [Pa]         Additional pressure added by pump
    """
    m_dot: float | None = None
    K: float
    tau: float
    dP_added: float | None = None

    def __init__(self, **data: Any) -> None:
        """
        Initialize pump and set pressure difference based on mass flow rate if provided.
        Args:
            m_dot:  [kg/s] Initial mass flow rate through the pump
        """

        # Call super init
        super().__init__(**data)

        # Set initial velocity if mass flow rate provided
        if (self.m_dot is None) and (self.dP_added is None):
            raise ValueError("Either initial m_dot or dP_added must be provided for Pump.")
        elif self.m_dot is not None:
            # Set dP_added based on initial m_dot: m_dot = K * sqrt(dP) =>  dP = (m_dot / K)^2
            self.dP_added = (self.m_dot / self.K)**2

        # Done
        return

    def calculate_material_flow(self, dt: float) -> Any:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update.
        Returns:
            Material flow object with mass and energy flow rates
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
            raise TypeError(f"{self.__class__.__name__} material must be Gas or Liquid.")
        fluid_class = type(fluid_src)

        # Calculate steady-state mass flow rate using conductance model
        dP = P_src - P_tgt + self.dP_added
        sign = 1 if dP >= 0 else -1
        m_dot = sign * self.K * math.sqrt(abs(dP))

        # Apply first-order response
        alpha = min(dt / self.tau, 1.0)  # Clamp to prevent instability
        m_dot_prev = self.m_dot if (self.m_dot is not None) else m_dot
        m_dot = alpha * m_dot + (1.0 - alpha) * m_dot_prev

        # Calculate energy flow rate based on mass flow and energy density
        if m_dot > 0:
            U_dot = m_dot * (fluid_src.U / fluid_src.m)
        else:
            U_dot = m_dot * (fluid_tgt.U / fluid_tgt.m)

        # Create fluid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Store current flow rate for next timestep
        self.m_dot = m_dot

        # Return output
        return fluid_flow


# Class for liquid pumps
class LiquidPump(Pump):
    """A Pump for liquids with typical conductance parameters."""
    K: float = 50.0
    tau: float = 3.0


# Class for gas pumps
class GasPump(Pump):
    """A Pump for gases with typical conductance parameters."""
    K: float = 0.001
    tau: float = 1.0



# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Import libraries
    from nuclear_simulator.sandbox.graphs import Graph
    from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel
    from nuclear_simulator.sandbox.plants.materials import PWRSecondaryWater
    # Define graph
    graph = Graph()
    # Create nodes and edge
    node1 = graph.add_node(
        PressurizedLiquidVessel,
        name="Node1",
        P=7e6,
        contents=PWRSecondaryWater.from_temperature(m=1000.0, T=550.0),
    )
    node2 = graph.add_node(
        PressurizedLiquidVessel,
        name="Node2",
        P=8e6,
        contents=PWRSecondaryWater.from_temperature(m=100.0, T=550.0),
    )
    graph.add_edge(
        Pump,
        node_source=node1,
        node_target=node2,
        name="Pump",
    )
    # Simulate
    dt = 1.0
    for t in range(10000):
        graph.update(dt)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

