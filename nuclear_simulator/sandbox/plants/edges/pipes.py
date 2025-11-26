
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


# Class for pipes using flow conductance model
class Pipe(TransferEdge):
    """
    Flows fluid between two nodes based on pressure difference and inertia.
    
    Attributes:
        m_dot:              [kg/s]       Previous mass flow rate for first-order response
        K:                  [kg/(s·√Pa)] Flow conductance coefficient
        tau:                [s]          Response time constant
    """
    m_dot: float | None = None
    K: float
    tau: float

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
            U_dot = m_dot * (fluid_src.U / (fluid_src.m + 1e-6))
        else:
            U_dot = m_dot * (fluid_tgt.U / (fluid_tgt.m + 1e-6))

        # Create fluid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Store current flow rate for next timestep
        self.m_dot = m_dot

        # Return output
        return fluid_flow


# Class for leaky pipes
class LeakyPipe(Pipe):
    """
    A Pipe that leaks a fraction of its flow to the environment.
    Attributes:
        leak_rate:     [kg/s] Rate of flow lost to environment.
    """
    leak_rate: float = 1/86400  # 1 kg per day

    def update_from_state(self, dt):
        """
        Update the pipe state by leaking mass and energy.
        Args:
            dt:  [s] Time step size.
        Modifies:
            Reduces material in the pipe flows.
        """

        # Get current material flow
        material: Material = self.flows[self.tag_material]

        # Calculate leak amount
        m_flow = abs(material.m)
        m_leak = min(self.leak_rate * dt, m_flow)
        fraction_remaining = 1.0 - (m_leak / max(m_flow, 1e-6))

        # Update material in pipe (multipy instead of subtract to avoid issuses with Material)
        material = material * fraction_remaining

        # Store updated material
        self.flows[self.tag_material] = material

        # Done
        return


# Class for liquid pipes with typical conductance values
class LiquidPipe(Pipe):
    """A Pipe for liquids with typical conductance parameters."""
    K: float = 1.0
    tau: float = 10.0


# Class for gas pipes with typical conductance values
class GasPipe(Pipe):
    """A Pipe for gases with typical conductance parameters."""
    K: float = 1.0
    tau: float = 10.0


# Combined classes for leaky variants
class LeakyLiquidPipe(LiquidPipe, LeakyPipe):
    """A LeakyPipe for liquids."""
    pass


class LeakyGasPipe(GasPipe, LeakyPipe):
    """A LeakyPipe for gases."""
    pass



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
        LeakyLiquidPipe,
        node_source=node1,
        node_target=node2,
        name="LeakyPipe",
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

