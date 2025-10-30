
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.controllers import Signal

# Import libraries
import copy
from abc import ABC


# Make an abstract base class for graph components
class Component(ABC):
    """
    Abstract base class for graph components.
    """

    # Define instance attributes
    id: int
    name: Optional[str]
    signals_incoming: list[Signal]
    signals_outgoing: list[Signal]

    # Define class-level attributes
    _id_counter: int = 0
    BASE_FIELDS: tuple[str, ...] = (
        "id", 
        "name", 
        "signals_incoming", 
        "signals_outgoing", 
    )

    def __init__(
            self,
            id: Optional[int] = None,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:

        # Set id attribute for component and update class counter
        if id is None:
            id = Component._id_counter
            Component._id_counter += 1
        else:
            Component._id_counter = max(Component._id_counter, id + 1)
        
        # Set attributes
        self.id = id
        self.name = name

        # Fill in missing state variables with defaults
        default_vars = self.get_defaults()
        for k, v in default_vars.items():
            kwargs.setdefault(k, copy.deepcopy(v))

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
        # Initialize set for fields
        fields: set[str] = set()
        # Walk MRO (method resolution order) to gather annotations from all bases
        for base in cls.__mro__:
            # Loop over annotations
            anns = getattr(base, "__annotations__", {})
            for k in anns:
                # Check if field is not private and not in base fields
                if not k.startswith("_") and k not in getattr(base, "BASE_FIELDS", ()):
                    # Add field to set
                    fields.add(k)
        # Sort fields
        fields = sorted(fields)
        # Return output
        return fields
    
    @classmethod
    def get_defaults(cls) -> dict[str, Any]:
        """Return default values for annotated state fields."""
        # Initialize defaults dictionary
        defaults: dict[str, Any] = {}
        # Walk MRO (method resolution order) to gather defaults from all bases
        for base in reversed(cls.__mro__):
            # Loop over annotations
            anns = getattr(base, "__annotations__", {})
            for k in anns:
                # Check if field is not private and not in base fields
                if not k.startswith("_") and k not in getattr(base, "BASE_FIELDS", ()):
                    if hasattr(base, k):
                        # Set value in defaults if not already set
                        defaults.setdefault(k, getattr(base, k))
        # Return output
        return defaults

    def update(self, dt: float) -> None:
        """
        Update the edge's internal state based on the current graph state.
        Args:
            dt: Time step size (s).
        Modifies:
            Updates self.flows with calculated flow values.
        """
        self.update_from_signals(dt)
        self.update_from_graph(dt)
        self.update_from_state(dt)
        return

    def update_from_signals(self, dt: float) -> None:
        """
        Update reactor parameters based on incoming control signals.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates state based on incoming signals.
            Defaults to setting state variables to match incoming signal payloads.
        """
        
        # Loop over incoming signals
        for signal in self.signals_incoming:
            payload = signal.payload

            # Loop over payload items
            for key, value in payload.items():

                # Check if key is a valid state variable
                if not hasattr(self, key):
                    raise KeyError(f"Signal contains unknown state variable '{key}' for {self}")
                
                # Set state variable
                setattr(self, key, value)

        # Done
        return

    def update_from_state(self, dt: float) -> None:
        """
        Optional: override in subclasses if the edge has its own dynamics.
        Example: A pipe that decays over time might update its diameter here.
        Default: no-op.
        """
        return
    
    def update_from_graph(self, dt: float) -> None:
        """
        Optional: override in subclasses to update based on graph state.
        Example: An edge that calculates flows based on node states would do so here.
        Default: no-op.
        """
        pass


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
