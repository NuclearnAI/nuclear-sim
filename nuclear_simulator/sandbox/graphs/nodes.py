
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.edges import Edge

# Import libraries
from nuclear_simulator.sandbox.graphs.components import Component


# Make an abstract base class for graph nodes
class Node(Component):
    """
    Abstract base class for graph nodes.
    """

    # Set class level attributes
    _BASE_FIELDS: tuple[str, ...] = tuple([
        *Component._BASE_FIELDS,
        "edges_incoming", 
        "edges_outgoing", 
    ])

    # Define instance attributes
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
        self.edges_incoming: list[Edge] = []
        self.edges_outgoing: list[Edge] = []

        # Done
        return

    def update(self, dt: float) -> None:
        """
        Update the node's state based on flows from incoming edges.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's state variables in place.
        """
        self.update_from_signals(dt)
        self.update_from_edges(dt)
        self.update_from_state(dt)
        return
    
    def update_from_signals(self, dt: float) -> None:
        """
        Optional: override in subclasses to modify edge state based on external signals.
        Example: A reactor node might adjust its reactivity based on a control signal.
        Default: no-op.
        """
        return
    
    def update_from_state(self, dt: float) -> None:
        """
        Optional: override in subclasses if the node has its own dynamics.
        Example: A tank that leaks over time might update its volume here.
        Default: no-op.
        """
        return

    def update_from_edges(self, dt: float) -> None:
        """
        Update the node's state based on flows from incoming edges.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's state variables in place.
        """

        # Add incoming flows
        for edge in self.edges_incoming:
            if edge.flows is None:
                raise ValueError(f"{edge} flows have not been calculated for {self}")
            for key, value in edge.flows.items():
                if not hasattr(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                current_value = getattr(self, key)
                setattr(self, key, current_value + value * dt)

        # Subtract outgoing flows
        for edge in self.edges_outgoing:
            if edge.flows is None:
                raise ValueError(f"{edge} flows have not been calculated for {self}")
            for key, value in edge.flows.items():
                if not hasattr(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                current_value = getattr(self, key)
                setattr(self, key, current_value - value * dt)

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
