
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional
if TYPE_CHECKING:
    from nuclear_simulator.sandbox.graphs.controllers import Signal

# Import libraries
import time
from pydantic import BaseModel, Field
from nuclear_simulator.sandbox.utils.nestedattrs import getattr_nested, setattr_nested, hasattr_nested


# Make an abstract base class for graph components
class Component(BaseModel):
    """
    Abstract base class for graph components.
    """

    # Model configuration
    model_config = {
        "extra": "allow",                 # Allow extra fields (for private attributes)
        "arbitrary_types_allowed": True,  # Allow non-Pydantic values for fields
    }
    
    # Define base fields
    id: Optional[int] = None
    name: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        """
        Initialize component and set up signal lists.
        """
        # Call super init
        super().__init__(**data)
        # Initialize signal lists
        self.signals_incoming: list[Signal] = []
        self.signals_outgoing: list[Signal] = []
        # Done
        return

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name or self.id})"

    @property
    def state(self) -> dict[str, Any]:
        """Return current state as a dict of Pydantic model fields."""
        return {k: getattr(self, k) for k in self.get_state_fields()}
    
    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return [
            "id", 
            "name", 
            "signals_incoming", 
            "signals_outgoing"
        ]

    def get_state_fields(self) -> list[str]:
        """Return list of Pydantic model field names."""
        # Get all model fields
        fields = sorted(list(self.model_fields.keys()))
        # Remove non-state fields
        fields = [f for f in fields if f not in self.get_nonstate_fields()]
        # Return output
        return fields
    

    # --- Update methods ---

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
                if not hasattr_nested(self, key):
                    raise KeyError(f"Signal contains unknown state variable '{key}' for {self}")
                
                # Set state variable
                setattr_nested(self, key, value)

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
    comp = TestComponent(id=0, name="test", x=0.0, y=0.0)
    # Checks
    print(list(comp.model_fields.keys()))
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

    