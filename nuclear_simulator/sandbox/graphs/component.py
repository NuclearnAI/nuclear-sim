
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs.controllers import Signal

# Import libraries
from abc import ABC


# Define component base fields
COMPONENT_BASE_FIELDS = [
    "id", 
    "name", 
    "signals_incoming", 
    "signals_outgoing", 
]


# Make an abstract base class for graph components
class Component(ABC):
    """
    Abstract base class for graph components.
    """

    # Define class-level attributes
    _id_counter: int = 0
    _BASE_FIELDS: list[str] = COMPONENT_BASE_FIELDS

    # Define instance attributes
    id: int
    name: str
    signals_incoming: list[Signal]
    signals_outgoing: list[Signal]

    def __init__(
            self,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:

        # Add id
        self.id = Component._id_counter
        Component._id_counter += 1
        
        # Set attributes
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
        fields = [k for k in cls.__annotations__ if k not in cls._BASE_FIELDS and not k.startswith('_')]
        return sorted(fields)

    def update(self, dt: float) -> None:
        """Update component state over timestep dt."""
        raise NotImplementedError("Component update method not implemented")


