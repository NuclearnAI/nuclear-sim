
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.graphs import Node
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
from nuclear_simulator.sandbox.graphs.edges import Edge
from nuclear_simulator.sandbox.materials.base import Energy


# Heat exchange edge
class HeatExchange(Edge):
    """
    Exchanges heat between two node materials.

    Attributes:
        conductance:   [W/K]  Heat transfer conductance between the two nodes
        tag:           str    Tag of the material on each node to exchange heat between
    """

    # Heat transfer conductance
    conductance: float
    tag: str = "material"

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "tag",
        ]

    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Calculates energy exchange between node_source.tag_a and node_target.tag_b.

        Args:
            dt:  [s]  Time step (used only by caller; we return per-second flows)

        Returns:
            flows: Dict with two entries (tag_a, tag_b), each a Material-like object
                   carrying U_dot (J/s) and zero mass.
        """

        # Get materials
        mat_src: Material = self.get_field_source(self.tag)
        mat_tgt: Material = self.get_field_target(self.tag)
        T_src = mat_src.T
        T_tgt = mat_tgt.T

        # Heat rate (positive means A -> B)
        dU = self.conductance * (T_src - T_tgt)

        # Package flows
        flows = {
            self.tag: Energy(U=dU)
        }

        # Return flows
        return flows


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.materials.liquids import Liquid
    # Dummy materials & node
    class DummyLiquid(Liquid):
        HEAT_CAPACITY = 4200.0
        DENSITY = 1000.0
    class TestNode(Node):
        fuel: DummyLiquid
        coolant: DummyLiquid
    # Create graph
    node_a = TestNode(
        name="A", 
        fuel=DummyLiquid(m=10.0, U=2.0e6), 
        coolant=DummyLiquid(m=0.0, U=0.0)
    )
    node_b = TestNode(
        name="B", 
        fuel=DummyLiquid(m=0.0, U=0.0), 
        coolant=DummyLiquid(m=10.0, U=1.0e6)
    )
    edge = HeatExchange(
        node_a, 
        node_b,
        alias_source={"material": "fuel"},
        alias_target={"material": "coolant"},
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