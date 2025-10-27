
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.controllers import Signal

# Import libraries
from abc import ABC


# Make an abstract base class for graph components
class Component(ABC):
    """
    Abstract base class for graph components.
    """

    # Define class-level attributes
    _id_counter: int = 0
    _BASE_FIELDS: tuple[str, ...] = tuple([
        "id", 
        "name", 
        "signals_incoming", 
        "signals_outgoing", 
    ])

    # Define instance attributes
    id: int
    name: str
    signals_incoming: list[Signal]
    signals_outgoing: list[Signal]

    def __init__(
            self,
            id: Optional[int] = None,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:

        # Get default id
        if id is None:
            id = Component._id_counter
            Component._id_counter += 1
        
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

        # Initialize signal lists
        self.signals_incoming: list[Signal] = []
        self.signals_outgoing: list[Signal] = []
        
        # Done
        return

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name or self.id})"
    
    @property
    def state(self) -> dict[str, Any]:
        """Return current state as a dict of annotated fields."""
        return {k: getattr(self, k) for k in self.get_fields()}
    
    @classmethod
    def get_fields(cls) -> list[str]:
        """Return annotated state fields, excluding base attributes."""
        fields: set[str] = set()
        for base in cls.__mro__:
            anns = getattr(base, "__annotations__", {})
            for k in anns:
                if not k.startswith("_") and k not in getattr(base, "_BASE_FIELDS", ()):
                    fields.add(k)
        return sorted(fields)

    def update(self, dt: float) -> None:
        """Update component state over timestep dt."""
        raise NotImplementedError("Component update method not implemented")


# Test
def test_file():
    # Create a child component class
    class TestComponent(Component):
        x: float
        y: float
        def update(self, dt: float) -> None:
            self.x += dt
            self.y += 2 * dt
            return
    # Instantiate
    comp = TestComponent(name="test", x=0.0, y=0.0)
    # Checks
    print(comp.get_fields())
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
