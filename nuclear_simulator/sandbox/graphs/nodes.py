
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.edges import Edge

# Import libraries
from nuclear_simulator.sandbox.graphs.base import Component


# Make an abstract base class for graph nodes
class Node(Component):
    """
    Abstract base class for graph nodes.
    """

    # Set class level attributes
    BASE_FIELDS: tuple[str, ...] = tuple([
        *Component.BASE_FIELDS,
        "flows",
        "edges_incoming", 
        "edges_outgoing", 
    ])

    # Define instance attributes
    flows: dict[str, float]
    edges_incoming: list[Edge]
    edges_outgoing: list[Edge]

    def __init__(
            self,
            id: Optional[int] = None,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:

        # Initialize base Component attributes
        super().__init__(id=id, name=name, **kwargs)

        # Set attributes
        self.flows = {}
        self.edges_incoming: list[Edge] = []
        self.edges_outgoing: list[Edge] = []

        # Done
        return

    def update_from_graph(self, dt: float) -> None:
        """
        Update the node's state based on flows from incoming edges.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's state variables in place.
        """

        # Initialize flows
        flows = {key: 0.0 for key in self.get_fields()}

        # Validate flows are not None
        for edge in self.edges_incoming + self.edges_outgoing:
            if edge.flows is None:
                raise ValueError(f"{edge} flows have not been calculated for {self}")

        # Add incoming flows
        for edge in self.edges_incoming:
            for key, value in edge.flows.items():
                if not hasattr(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                flows[key] += value

        # Subtract outgoing flows
        for edge in self.edges_outgoing:
            for key, value in edge.flows.items():
                if not hasattr(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                flows[key] -= value
        
        # Update state variables
        for key, value in flows.items():
            current_value = getattr(self, key)
            setattr(self, key, current_value + value * dt)

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
