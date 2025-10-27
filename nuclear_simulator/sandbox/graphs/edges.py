
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.controllers import Signal

# Import libraries
from abc import ABC, abstractmethod


# Make an abstract base class for graph edges
class Edge(ABC):
    """
    Abstract base class for graph edges.
                ...
    """

    # Define attributes
    id: int
    flows: dict[str, float] | None
    node_source: Node
    node_target: Node
    signals_incoming: list[Signal]
    signals_outgoing: list[Signal]

    # Set fields that are not part of state
    _BASE_FIELDS = [
        "id", 
        "flows",
        "node_source", 
        "node_target",
        "signals_incoming", 
        "signals_outgoing", 
    ]

    def __init__(
            self,
            id: int,
            node_source: Node,
            node_target: Node,
            **kwargs: Any
        ) -> None:

        # Set attributes
        self.id = id
        self.node_source = node_source
        self.node_target = node_target
        self.flows = None  # Set to None until calculated

        # Validate extra kwargs against annotated state fields
        required_vars = self.get_fields()
        missing_keys = [k for k in required_vars if k not in kwargs]
        extra_keys   = [k for k in kwargs if k not in required_vars]
        if missing_keys:
            raise KeyError(f"State variable(s) {missing_keys} missing in edge init kwargs")
        if extra_keys:
            raise KeyError(f"Edge init contains unknown variable(s) {extra_keys}")

        # Set state variables as attributes
        for k, v in kwargs.items():
            setattr(self, k, v)

        # Link to nodes
        self.node_source.edges_outgoing.append(self)
        self.node_target.edges_incoming.append(self)

        # Initialize signal lists
        self.signals_incoming: list[Signal] = []
        self.signals_outgoing: list[Signal] = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}[{self.node_source.id} -> {self.node_target.id}]"
    
    @property
    def state(self) -> dict[str, Any]:
        """Return current state as a dict of annotated fields."""
        return {k: getattr(self, k) for k in self.get_fields()}

    @classmethod
    def get_fields(cls) -> list[str]:
        """Return annotated state fields, excluding base attributes."""
        fields = [f for f in cls.__annotations__.keys() if f not in cls._BASE_FIELDS]
        return sorted(fields)
    

    # --- Step update methods ---

    def update(self, dt: float) -> None:
        """
        Update the edge's internal state (if any) and compute flows for this tick.
        Flows are stored in `self.flows` with a fixed vocabulary (e.g., m_dot, H_dot, Q_dot).
        Args:
            dt: Time step size (s).
        Modifies:
            Updates self.flows with calculated flow values.
        """
        self.update_from_signals(dt)
        self.update_from_state(dt)
        self.update_from_nodes(dt)
        return

    def update_from_signals(self, dt: float) -> None:
        """
        Optional: override in subclasses to modify edge state based on external signals.
        Example: A valve edge might adjust its openness based on a control signal.
        Default: no-op.
        """
        return

    def update_from_state(self, dt: float) -> None:
        """
        Optional: override in subclasses if the edge has its own dynamics.
        Example: A pipe that decays over time might update its diameter here.
        Default: no-op.
        """
        return
    
    def update_from_nodes(self, dt: float) -> None:
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
            return {"a": dt * (node_source.a - node_target.a) / 2}
    # Create nodes and edge
    node1 = TestNode(id=1, name="Node1", a=10.0, b=5)
    node2 = TestNode(id=2, name="Node2", a=20.0, b=10)
    edge = TestEdge(id=1, node_source=node1, node_target=node2)
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
