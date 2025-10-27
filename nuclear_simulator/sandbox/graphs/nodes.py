
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.edges import Edge
    from nuclear_simulator.sandbox.graphs.controllers import Signal

# Import libraries
from abc import ABC


# Make an abstract base class for graph nodes
class Node(ABC):
    """
    Abstract base class for graph nodes.
    """

    # Define attributes
    id: int
    name: str
    edges_incoming: list[Edge]
    edges_outgoing: list[Edge]
    signals_incoming: list[Signal]
    signals_outgoing: list[Signal]

    # Set fields that are not part of state
    _BASE_FIELDS = [
        "id", 
        "name", 
        "edges_incoming", 
        "edges_outgoing", 
        "signals_incoming", 
        "signals_outgoing", 
    ]

    def __init__(
            self, 
            id: int,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:
        
        # Set attributes
        self.id = id
        self.name = name

        # Validate state variables match the state dictionary
        required_vars = self.get_fields()
        missing_keys = [key for key in required_vars if key not in kwargs]
        extra_keys   = [key for key in kwargs if key not in required_vars]
        if missing_keys:
            raise KeyError(f"State variable(s) {missing_keys} missing in state dictionary")
        if extra_keys:
            raise KeyError(f"State dictionary contains unknown variable(s) {extra_keys}")
        
        # Set state variables
        for k, v in kwargs.items():
            setattr(self, k, v)

        # Initialize edge and signal lists
        self.edges_incoming: list[Edge] = []
        self.edges_outgoing: list[Edge] = []
        self.signals_incoming: list[Signal] = []
        self.signals_outgoing: list[Signal] = []
        
        # Done
        return

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
    
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
        Update the node's state based on flows from incoming edges.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's state variables in place.
        """
        self.update_from_signals(dt)
        self.update_from_state(dt)
        self.update_from_edges(dt)
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
            for key, value in edge.flows.items():
                if not hasattr(self, key):
                    raise KeyError(f"{edge} contains unknown flow '{key}' for {self}")
                current_value = getattr(self, key)
                setattr(self, key, current_value + value * dt)
        # Subtract outgoing flows
        for edge in self.edges_outgoing:
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
    node = TestNode(id=1, name="Test Node", a=10.0, b=5)
    # Print the node
    print(node)
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")
