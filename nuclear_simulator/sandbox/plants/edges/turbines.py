
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
import math
from nuclear_simulator.sandbox.materials.base import Energy
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.edges.pipes import TransferEdge


# Class for turbine edge
class TurbineEdge(TransferEdge):
    """
    Flows fluid between two nodes based on pressure difference and inertia, extracting energy.
    Attributes:
        m_dot:              [kg/s]       Previous mass flow rate for first-order response
        K:                  [kg/(s·√Pa)] Flow conductance coefficient
        tau:                [s]          Response time constant
        eta:                [-]          Efficiency of energy extraction
        power_output:       [W]          Last calculated power output
    """
    monodirectional: bool = True  # Turbines only flow one way
    m_dot: float | None = None
    K: float
    tau: float
    eta: float = 0.9
    power_output: float | None = None  # [W] Store last power output

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
        dP = P_src - P_tgt
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
            m_dot = 0.0  # No reverse flow in turbine
            U_dot = 0.0

        # Calculate extracted energy based on enthalpy difference
        h_src = (fluid_src.U + P_src * fluid_src.V) / fluid_src.m
        h_tgt = (fluid_tgt.U + P_tgt * fluid_tgt.V) / fluid_tgt.m
        power_output = self.eta * m_dot * (h_src - h_tgt)
        power_output = max(power_output, 0.0)  # Prevent negative extraction

        # Create fluid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)  # V handled by Gas class
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Store states for next timestep
        self.m_dot = m_dot
        self.power_output = power_output

        # Return output
        return fluid_flow

    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Calculates material exchange between node_source and node_target.
        Removes energy from fluid to simulate turbine work extraction.
        Args:
            dt:  [s]  Time step
        Returns:
            flows: Dict with flows keyed by tag_material
        """

        # Get flow from parent class
        flow: Material = super().calculate_flows(dt)[self.tag_material]

        # Calculate power extracted
        self.power_output = min(self.power_output, flow.U / dt)  # Limit to available energy
        power_flow = Energy(U=self.power_output)

        # Adjust flow to account for non-conservation of energy
        flows = {
            '_source': {self.tag_material: flow},
            '_target': {self.tag_material: flow - power_flow},
        }

        # Done
        return flows
        


# Class for liquid turbines
class LiquidTurbine(TurbineEdge):
    """A Turbine for liquids with typical conductance parameters."""
    K: float = 50.0
    tau: float = 3.0


# Class for gas turbines
class GasTurbine(TurbineEdge):
    """A Turbine for gases with typical conductance parameters."""
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
        P=8e6,
        contents=PWRSecondaryWater.from_temperature(m=1000.0, T=550.0),
    )
    node2 = graph.add_node(
        PressurizedLiquidVessel,
        name="Node2",
        P=7e6,
        contents=PWRSecondaryWater.from_temperature(m=100.0, T=550.0),
    )
    graph.add_edge(
        LiquidTurbine,
        node_source=node1,
        node_target=node2,
        name="TurbineEdge",
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

