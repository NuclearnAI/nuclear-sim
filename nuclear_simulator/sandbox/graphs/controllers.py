
# Annotation imports
from __future__ import annotations
from typing import Any

# Import libraries
from abc import ABC, abstractmethod
from nuclear_simulator.sandbox.graphs.nodes import Node
from nuclear_simulator.sandbox.graphs.edges import Edge


# Signal class
class Signal(ABC):
    """
    Special connector that carries information (not mass/energy).
    """

    # Define attributes
    source_component: Node | Edge | Controller
    target_component: Node | Edge | Controller

    def __init__(
            self,
            source_component: Node | Edge | Controller,
            target_component: Node | Edge | Controller,
        ) -> None:

        # Set attributes
        self.source_component = source_component
        self.target_component = target_component

        # Ensure that source xor target is a Controller
        is_source_controller = isinstance(self.source_component, Controller)
        is_target_controller = isinstance(self.target_component, Controller)
        if is_source_controller == is_target_controller:
            raise ValueError("Signal must connect a Controller to a Node or Edge")

        # Link to endpoints
        self.source_component.signals_outgoing.append(self)
        self.target_component.signals_incoming.append(self)

    def __repr__(self) -> str:
        return f"Signal[{self.source_component} -> {self.target_component}]"

    def read(self) -> None:
        """
        Set self.payload to the source component's state.
        """
        if hasattr(self.source_component, "state"):
            self.payload = self.source_component.state
        else:
            raise NotImplementedError("Source component has no state to read")
        return self.payload
    
    def write(self, payload: dict[str, Any]) -> None:
        """
        Set payload to be sent to the target component.
        """
        self.payload = payload
        return
    

# Controller class
class Controller(ABC):
    """
    Special graph component that sends/receives control signals.
    """

    # Add read and write lists to be defined by subclasses
    READ_CONNECTIONS: list[str] = []
    WRITE_CONNECTIONS: list[str] = []

    # Define attributes
    id: int
    name: str | None
    connections: dict[str, Signal]
    signals_incoming: list[Signal]
    signals_outgoing: list[Signal]

    # Set fields that are not part of state
    _BASE_FIELDS = [
        "READ_CONNECTIONS",
        "WRITE_CONNECTIONS",
        "id", 
        "name", 
        "connections",
        "signals_incoming", 
        "signals_outgoing",
    ]

    def __init__(
            self,
            id: int,
            name: str | None = None,
            **kwargs: Any
        ) -> None:

        # Set attributes
        self.id = id
        self.name = name

        # Initialize signal lists
        self.connections: dict[str, Signal] = {k: None for k in self.READ_CONNECTIONS + self.WRITE_CONNECTIONS}
        self.signals_incoming: list[Signal] = []
        self.signals_outgoing: list[Signal] = []

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @classmethod
    def get_fields(cls) -> list[str]:
        """Return annotated state fields, excluding base attributes."""
        fields = [f for f in cls.__annotations__.keys() if f not in cls._BASE_FIELDS]
        return sorted(fields)
    
    def add_read_connection(self, name: str, component: Node | Edge) -> None:
        """
        Create an incoming signal from a component to this controller.
        Args:
            name:      Name of the signal.
            component: Node or Edge to read from.
        Modifies:
            Adds a Signal to self.signals_incoming.
        """
        # Validate name
        if name not in self.READ_CONNECTIONS:
            raise KeyError(f"Signal name '{name}' not in controller's READ_CONNECTIONS list")
        # Create signal between component and self
        signal = Signal(source_component=component, target_component=self)
        # Add signal to connections
        self.connections[name] = signal
        return
    
    def add_write_connection(self, name: str, component: Node | Edge) -> None:
        """
        Create an outgoing signal from this controller to a component.
        Args:
            name:      Name of the signal.
            component: Node or Edge to write to.
        Modifies:
            Adds a Signal to self.signals_outgoing.
        """
        # Validate name
        if name not in self.WRITE_CONNECTIONS:
            raise KeyError(f"Signal name '{name}' not in controller's WRITE_CONNECTIONS list")
        # Create signal between self and component
        signal = Signal(source_component=self, target_component=component)
        # Add signal to connections
        self.connections[name] = signal
        return
    
    def add_connections(self, **connections: Node | Edge) -> None:
        """
        Add multiple connections at once using keyword arguments.
        Args:
            connections: Keyword arguments where key is signal name and value is Node or Edge.
        Modifies:
            Adds Signals to self.signals_incoming and self.signals_outgoing.
        """
        # Loop over components
        for name, component in connections.items():
            # Check which type of connection to add
            if name in self.READ_CONNECTIONS:
                self.add_read_connection(name, component)
            elif name in self.WRITE_CONNECTIONS:
                self.add_write_connection(name, component)
            else:
                raise KeyError(f"Signal name '{name}' not in controller's connection lists")
        return

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        Update the controller's payload based on incoming signals.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Controller.update() must be implemented by subclasses")
    

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.graphs.nodes import Node
    # Define dummy node
    class TestNode(Node):
        a: float
        b: int
        def update_from_state(self, dt):
            self.b += 1 * dt
            return
        def update_from_signals(self, dt):
            increase_a_amount = sum([s.payload['a_increase'] for s in self.signals_incoming])
            self.a += increase_a_amount * dt
            return
    # Define dummy controller
    class TestController(Controller):
        READ_CONNECTIONS = ['read_node']
        WRITE_CONNECTIONS = ['write_node']
        def update(self, dt: float) -> None:
            # Read b from source node
            b_source = self.connections['read_node'].read()['b']
            # Write to target node
            self.connections['write_node'].write({'a_increase': (1 if b_source > 5 else 0)})
            return
    # Create nodes and controller
    node1 = TestNode(id=1, name="Node1", a=0.0, b=0)
    node2 = TestNode(id=2, name="Node2", a=0.0, b=10)
    controller = TestController(id=1, name="Controller1")
    controller.add_connections(
        read_node=node1,
        write_node=node2,
    )
    # Simulate one timestep
    print('Simulating')
    dt = 1.0
    num_steps = 10
    for t in range(num_steps):
        # Update nodes
        node1.update(dt)
        node2.update(dt)
        # Update controller after edges and nodes
        controller.update(dt)
        # Print status
        print(f'- {t}/{num_steps}: Node1 a={node1.a}, b={node1.b}; Node2 a={node2.a}, b={node2.b}')
    # Done
    print('Done')
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")
