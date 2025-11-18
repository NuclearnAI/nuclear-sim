
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
from nuclear_simulator.sandbox.materials.base import Energy
from nuclear_simulator.sandbox.plants.transfer.base import TransferEdge


# Heat exchange edge
class HeatExchange(TransferEdge):
    """
    Exchanges heat between two node materials.

    Attributes:
        conductance:   [W/K]  Heat transfer conductance between the two nodes
    """
    conductance: float

    def calculate_material_flow(self, dt: float) -> dict[str, Any]:
        """
        Calculates energy exchange between node_source.tag_a and node_target.tag_b.

        Args:
            dt:  [s]  Time step (used only by caller; we return per-second flows)

        Returns:
            flows: [J/s] Energy flow from source -> target
        """

        # Get materials
        mat_src: Material = self.get_contents_source()
        mat_tgt: Material = self.get_contents_target()
        T_src = mat_src.T
        T_tgt = mat_tgt.T

        # Heat rate
        dU = self.conductance * (T_src - T_tgt)

        # Package flow
        flow = Energy(U=dU)

        # Return flow
        return flow

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.vessels import Vessel
    from nuclear_simulator.sandbox.plants.materials import UraniumDioxide, PWRPrimaryWater
    # Dummy materials & node
    class ReactorVessel(Vessel):
        contents: UraniumDioxide = UraniumDioxide.from_temperature(m=1000.0, T=600.0)
    class CoolantVessel(Vessel):
        contents: PWRPrimaryWater = PWRPrimaryWater.from_temperature(m=10_000.0, T=550.0)
    # Create nodes
    node_a = ReactorVessel(name="A")
    node_b = CoolantVessel(name="B")
    edge = HeatExchange(
        node_a, 
        node_b,
        conductance=5.0e5
    )
    # Update graph
    dt = 0.1
    edge.update(dt)
    node_a.update(dt)
    node_b.update(dt)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
    