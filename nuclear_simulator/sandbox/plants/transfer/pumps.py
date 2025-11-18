
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional

# Import libraries
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.transfer.base import TransferEdge
from nuclear_simulator.sandbox.physics import calc_energy_from_temperature


# Create class for pumps
class Pump(TransferEdge):
    """
    Flows fluid between two nodes at a controllable mass flow rate.
    Attributes:
        m_dot:              [kg/s]  Mass flow rate
        m_dot_setpoint:     [kg/s]  Commanded mass flow rate
        tag_material:       [str]   Tag of the fluid on each node this pipe moves
        MAX_FLOW_FRACTION:  [-]     Maximum fraction of node mass that can flow per time step.
    """
    m_dot: float | None = None
    m_dot_setpoint: float | None = None
    max_flow_fraction: float = 0.1

    def __init__(self, **data) -> None:
        """Initialize pump edge."""
        # Call super init
        super().__init__(**data)

        # Initialize m_dot_setpoint
        if (self.m_dot_setpoint is None) and (self.m_dot is None):
            # Case: Neither set -> error
            raise ValueError("Pump requires m_dot_setpoint or initial m_dot.")
        elif self.m_dot_setpoint is None:
            # Case: m_dot set -> use m_dot as setpoint
            self.m_dot_setpoint = self.m_dot
        elif self.m_dot is None:
            # Case: m_dot_setpoint set -> use as initial m_dot
            self.m_dot = self.m_dot_setpoint

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

        # Get fluid properties
        if isinstance(fluid_src, Gas):
            fluid_type = Gas
        elif isinstance(fluid_src, Liquid):
            fluid_type = Liquid
        else:
            raise TypeError("Pipe material must be Gas or Liquid.")
        fluid_class = type(fluid_src)

        # Get flow rate from setpoint
        m_dot = self.m_dot_setpoint

        # Calculate energy flow rate based on mass flow and energy density
        if m_dot > 0:
            m_dot = min(m_dot, self.max_flow_fraction * fluid_src.m / dt)
            U_dot = m_dot * (fluid_src.U / fluid_src.m)
        else:
            m_dot = max(m_dot, -self.max_flow_fraction * fluid_tgt.m / dt)
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

# Class for gas pumps
class GasPump(Pump):
    """
    Pumps gas between two nodes at a controllable mass flow rate.
    """
    

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
        m_dot=100.0
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
