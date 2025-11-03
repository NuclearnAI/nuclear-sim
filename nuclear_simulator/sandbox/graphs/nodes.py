# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional
if TYPE_CHECKING:
    from nuclear_simulator.sandbox.graphs.edges import Edge

# Import libraries
from nuclear_simulator.sandbox.graphs.base import Component
from nuclear_simulator.sandbox.utils.nestedattrs import getattr_nested, setattr_nested, hasattr_nested


# Make an abstract base class for graph nodes
class Node(Component):
    """
    Abstract base class for graph nodes.
    """

    def __init__(self, **data: Any) -> None:
        """
        Initialize Node and add private attributes.
        """
        # Initialize base Component attributes (Pydantic fields)
        super().__init__(**data)
        # Set private attributes
        self.flows: dict[str, Any] = {}
        # Initialize edge lists
        self.edges_incoming: list[Edge] = []
        self.edges_outgoing: list[Edge] = []
        # Done
        return

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "flows",
            "edges_incoming",
            "edges_outgoing",
        ]

    def update_from_graph(self, dt: float) -> None:
        """
        Update the node's state based on flows from incoming edges.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's state variables in place.
        """

        # Initialize flows
        flows = {key: 0.0 for key in self.get_state_fields()}

        # Validate flows are not None
        for edge in self.edges_incoming + self.edges_outgoing:
            if edge.flows is None:
                raise ValueError(f"{edge} flows have not been calculated for {self}")

        # Add incoming flows
        for edge in self.edges_incoming:
            for key, value in edge.get_flows_target().items():
                if not hasattr_nested(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                flows[key] += value

        # Subtract outgoing flows
        for edge in self.edges_outgoing:
            for key, value in edge.get_flows_source().items():
                if not hasattr_nested(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                flows[key] -= value
        
        # Update state variables
        for key, value in flows.items():
            current_value = getattr_nested(self, key)
            setattr_nested(self, key, current_value + value * dt)

        # Set flows
        self.flows = flows

        # Done
        return


# Test
def test_file():
    # Define a test node class
    class TestNode(Node):
        a: float
        b: int
    # Create a test node
    node = TestNode(name="Test Node", a=10.0, b=5)
    # Print the node
    print(node)
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")