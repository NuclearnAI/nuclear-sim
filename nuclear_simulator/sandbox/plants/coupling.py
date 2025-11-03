
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
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.utils.nestedattrs import getattr_nested, setattr_nested, hasattr_nested


# Define thermal coupling edge
class ThermalCoupling(Edge):
    """
    Exchanges heat between two node materials.
    """

    # Heat transfer conductance
    G: float = 1.0e6  # [W/K] (J/s/K)
    tag_source: str
    tag_target: str

    def calculate_flows(
            self,
            dt: float,
            node_source: Node,
            node_target: Node,
        ) -> dict[str, Any]:
        """
        Calculates energy exchange between node_source.tag_a and node_target.tag_b.

        Args:
            dt:          [s]  Time step (used only by caller; we return per-second flows)
            node_source: Source node (side A)
            node_target: Target node (side B)

        Returns:
            flows: Dict with two entries (tag_a, tag_b), each a Material-like object
                   carrying U_dot (J/s) and zero mass.
        """

        # Get materials
        mat_src: Material = getattr_nested(node_source, self.tag_source)
        mat_tgt: Material = getattr_nested(node_target, self.tag_target)
        T_src = mat_src.T
        T_tgt = mat_tgt.T

        # Heat rate (positive means A -> B)
        dU = self.G * (T_src - T_tgt)

        # Package flows to be applied to their respective node attributes
        flows = {'_source': {}, '_target': {}}
        flows['_source'][self.tag_source] = Energy(U=dU)
        flows['_target'][self.tag_target] = Energy(U=dU)

        # Return flows
        return flows


# Test
def test_file():
    # Import libraries
    from pydantic import Field
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
    edge = ThermalCoupling(node_a, node_b, id=3, tag_source="fuel", tag_target="coolant", G=5.0e5)
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