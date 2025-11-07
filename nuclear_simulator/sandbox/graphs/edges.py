
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional
if TYPE_CHECKING:
    from nuclear_simulator.sandbox.graphs.nodes import Node

# Import libraries
from abc import abstractmethod
from nuclear_simulator.sandbox.graphs.base import Component
from nuclear_simulator.sandbox.graphs.utils import getattr_nested, setattr_nested, hasattr_nested


# Make an abstract base class for graph edges
class Edge(Component):
    """
    Abstract base class for graph edges.
    """

    def __init__(self,
            node_source: Node,
            node_target: Node,
            alias_source: Optional[dict[str, str]] = None,
            alias_target: Optional[dict[str, str]] = None,
            **data: Any
        ) -> None:
        """Initialize Edge and add private attributes."""
        # Initialize base Component attributes (Pydantic fields)
        super().__init__(**data)
        # Set private attributes
        self.flows: dict[str, Any] = {}
        # Link to nodes
        self.node_source = node_source
        self.node_target = node_target
        self.node_source.edges_outgoing.append(self)
        self.node_target.edges_incoming.append(self)
        # Set up alias dictionaries
        self.alias_source = dict(alias_source or {})
        self.alias_target = dict(alias_target or {})
        # Done
        return

    def __repr__(self) -> str:
        tag_src = self.node_source.name or self.node_source.id
        tag_tgt = self.node_target.name or self.node_target.id
        return f"{self.__class__.__name__}[{tag_src} -> {tag_tgt}]"

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "flows",
            "node_source",
            "node_target",
        ]
    
    def get_flows_source(self) -> dict[str, Any]:
        """Return flows with tags for source node."""
        flows = {k: v for (k, v) in self.flows.items()}
        flows = {k: v for k, v in flows.items() if (k != "_target") and (k != "_source")}
        flows = {self.alias_source.get(k, k): v for k, v in flows.items()}
        flows.update(self.flows.get("_source", {}))
        return flows
    
    def get_flows_target(self) -> dict[str, Any]:
        """Return flows with tags for target node."""
        flows = {k: v for (k, v) in self.flows.items()}
        flows = {k: v for k, v in flows.items() if (k != "_target") and (k != "_source")}
        flows = {self.alias_target.get(k, k): v for k, v in flows.items()}
        flows.update(self.flows.get("_target", {}))
        return flows
    
    def get_field_source(self, key: Optional[str] = None) -> Any:
        """
        Get source node state field for a given state key.
        Args:
            key: State variable key.
        Returns:
            Field value for key on source node.
        """
        key = self.alias_source.get(key, key)
        return getattr_nested(self.node_source, key)

    def get_field_target(self, key: Optional[str] = None) -> Any:
        """
        Get target node state field for a given state key.
        Args:
            key: State variable key.
        Returns:
            Field value for key on target node.
        """
        key = self.alias_target.get(key, key)
        return getattr_nested(self.node_target, key)

    def update_from_graph(self, dt: float) -> None:
        """
        Update edge flows based on current states of source and target nodes.
        Args:
            dt: Time step size (s).
        Modifies:
            Updates self.flows with calculated flow values.
        """
        self.flows = self.calculate_flows(dt)
        return

    @abstractmethod
    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Compute instantaneous flows for this edge based on current node states.
        Must return a dict of flow quantities (e.g., {"m": ..., "U": ..., }).
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
        def calculate_flows(self, dt: float) -> dict[str, float]:
            return {"a": (self.node_source.a - self.node_target.a) / 2}
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
