
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.nodes import Node

# Import libraries
from abc import abstractmethod
from nuclear_simulator.sandbox.graphs.base import Component


# Make an abstract base class for graph edges
class Edge(Component):
    """
    Abstract base class for graph edges.
    """

    # Define instance attributes
    flows: dict[str, float] | None
    node_source: Node
    node_target: Node

    # Define class-level attributes
    BASE_FIELDS = (
        *Component.BASE_FIELDS,
        "flows", 
        "node_source", 
        "node_target", 
    )

    def __init__(
            self,
            node_source: Node,
            node_target: Node,
            id: Optional[int] = None,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:

        # Initialize base Component attributes
        super().__init__(id=id, name=name, **kwargs)

        # Set attributes
        self.flows = None  # Set to None until calculated
        self.node_source = node_source
        self.node_target = node_target

        # Link to nodes
        self.node_source.edges_outgoing.append(self)
        self.node_target.edges_incoming.append(self)

        # Done
        return

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}[{self.node_source.id} -> {self.node_target.id}]"
    
    def update_from_graph(self, dt: float) -> None:
        """
        Update edge flows based on current states of source and target nodes.
        Args:
            dt: Time step size (s).
        Modifies:
            Updates self.flows with calculated flow values.
        """
        self.flows = self.calculate_flows(dt, self.node_source, self.node_target)
        return

    @abstractmethod
    def calculate_flows(self, dt: float, node_source: Node, node_target: Node) -> dict[str, float]:
        """
        Compute instantaneous flows for this edge based on current node states.
        Must return a dict of flow quantities (e.g., {"m": ..., "H": ..., "Q": ...}).
        """
        raise NotImplementedError("calculate_flows must be implemented by Edge subclasses.")
    

# Test
def test_file():
    # Import node
    from nuclear_simulator.sandbox.graphs.nodes import Node
    # Define a test node class
    class TestNode(Node):
        a: float
        b: int
    # Define a test edge class
    class TestEdge(Edge):
        def calculate_flows(self, dt: float, node_source: Node, node_target: Node) -> dict[str, float]:
            return {"a": (node_source.a - node_target.a) / 2}
    # Create nodes and edge
    node1 = TestNode(name="Node1", a=10.0, b=5)
    node2 = TestNode(name="Node2", a=20.0, b=10)
    edge = TestEdge(node_source=node1, node_target=node2)
    # Print initial states
    print(f"Node1 state: {node1.state}")
    print(f"Node2 state: {node2.state}")
    print(f"Edge flows: {edge.flows}")
    # Update graph
    dt = .1
    edge.update(dt=dt)
    node1.update(dt=dt)
    node2.update(dt=dt)
    # Print updated states
    print(f"Node1 state: {node1.state}")
    print(f"Node2 state: {node2.state}")
    print(f"Edge flows: {edge.flows}")
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")
