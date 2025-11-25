# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar, Any, Optional
if TYPE_CHECKING:
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.edges import Edge

# Import libraries
from abc import ABC, abstractmethod
from pydantic import PrivateAttr
from nuclear_simulator.sandbox.graphs.base import Component
from nuclear_simulator.sandbox.graphs.utils import getattr_nested, setattr_nested, hasattr_nested


# Signal class
class Signal:
    """
    Special connector that carries information (not mass/energy).
    """

    def __init__(
            self,
            source_component: Node | Edge | Controller,
            target_component: Node | Edge | Controller,
        ) -> None:

        # Ensure that source xor target is a Controller
        is_source_controller = isinstance(source_component, Controller)
        is_target_controller = isinstance(target_component, Controller)
        if is_source_controller == is_target_controller:
            raise ValueError("Signal must connect a Controller to a Node or Edge")

        # Set attributes
        self.payload = {}  # Initialize empty payload
        self.source_component = source_component
        self.target_component = target_component

        # Link to endpoints
        self.source_component.signals_outgoing.append(self)
        self.target_component.signals_incoming.append(self)

    def __repr__(self) -> str:
        tag_src = self.source_component.name or self.source_component.id
        tag_tgt = self.target_component.name or self.target_component.id
        return f"Signal[{tag_src} -> {tag_tgt}]"

    def read(self) -> dict[str, Any]:
        """
        Set self.payload to the source component's state.
        """
        if isinstance(self.source_component, Controller):
            # If reading a controller, assume controller already wrote payload
            return self.payload
        else:
            # If reading a node/edge, get its state
            self.payload = {k: v for (k, v) in self.source_component.state.items()}
            if hasattr_nested(self.source_component, 'flows'):
                self.payload['flows'] = {
                    k: v for (k, v) in self.source_component.flows.items()
                }
            return self.payload
    
    def write(self, payload: dict[str, Any]) -> None:
        """
        Set payload to be sent to the target component.
        """
        self.payload = payload
        return
    

# Controller class
class Controller(Component):
    """
    Special graph component that sends/receives control signals.
    """

    # Define class-level attributes
    REQUIRED_CONNECTIONS_READ: ClassVar[tuple[str, ...] | None] = None
    REQUIRED_CONNECTIONS_WRITE: ClassVar[tuple[str, ...] | None] = None

    def __init__(self, connections=None, **data: Any) -> None:
        """
        Initialize controller and set up connection dictionaries.
        """
        # Call super init
        super().__init__(**data)
        # Initialize monitor (read payload dictionary)
        self.monitor: dict[str, Any] = {}
        # Initialize connection dictionaries
        self.connections_read: dict[str, Signal] = {}
        self.connections_write: dict[str, Signal] = {}
        # Add connections if provided
        if connections is not None:
            self.add_connections(**connections)
        # Done
        return
    
    @property
    def connections_all(self) -> dict[str, Signal]:
        """Return all connections (read and write) as a single dictionary."""
        all_connections = {}
        all_connections.update(self.connections_read)
        all_connections.update(self.connections_write)
        return all_connections
    
    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "REQUIRED_CONNECTIONS_READ",
            "REQUIRED_CONNECTIONS_WRITE",
            "connections_read",
            "connections_write",
        ]
    
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
        if self.REQUIRED_CONNECTIONS_READ and name not in self.REQUIRED_CONNECTIONS_READ:
            raise KeyError(f"Signal name '{name}' not in controller's REQUIRED_CONNECTIONS_READ list")

        # Create signal between component and self
        signal = Signal(source_component=component, target_component=self)

        # Add signal to connections
        self.connections_read[name] = signal

        # Return self for chaining
        return self
    
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
        if self.REQUIRED_CONNECTIONS_WRITE and name not in self.REQUIRED_CONNECTIONS_WRITE:
            raise KeyError(f"Signal name '{name}' not in controller's REQUIRED_CONNECTIONS_WRITE list")
        
        # Create signal between self and component
        signal = Signal(source_component=self, target_component=component)

        # Add signal to connections
        self.connections_write[name] = signal

        # Return self for chaining
        return self
    
    def add_connections(self, **connections: dict[str, Node | Edge]) -> None:
        """
        Add multiple connections at once using keyword arguments.
        Args:
            connections: Keyword arguments where key is signal name and value is Node or Edge.
        Modifies:
            Adds Signals to self.signals_incoming and self.signals_outgoing.
        """

        # Ensure required connections are defined
        if self.REQUIRED_CONNECTIONS_READ is None:
            raise ValueError(
                f"Controller subclass {self.__class__.__name__} must define REQUIRED_CONNECTIONS_READ"
            )
        if self.REQUIRED_CONNECTIONS_WRITE is None:
            raise ValueError(
                f"Controller subclass {self.__class__.__name__} must define REQUIRED_CONNECTIONS_WRITE"
            )

        # Get required connections
        req_read = self.REQUIRED_CONNECTIONS_READ
        req_write = self.REQUIRED_CONNECTIONS_WRITE

        # Loop over components
        for name, component in connections.items():

            # Check which type of connection to add
            if (name in req_read) and (name in req_write):
                self.add_read_connection(name, component)
                self.add_write_connection(name, component)
            elif name in req_read:
                self.add_read_connection(name, component)
            elif name in req_write:
                self.add_write_connection(name, component)
            else:
                raise KeyError(f"Signal name '{name}' not in controller's connection lists")

        # Return self for chaining
        return self

    def update(self, dt: float = 0) -> None:
        """
        Update the controller logic. Default to just update monitor.
        Args:
            dt:     [s] Time step for update
        Modifies:
            self.monitor
        """
        # Clear monitor
        self.monitor = {}
        # Update monitor by reading all connected components
        for name, signal in self.connections_read.items():
            self.monitor[name] = signal.read()
        # Done
        return
    

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
            increase_a_amount = sum([s.payload.get('a_increase', 0) for s in self.signals_incoming])
            self.a += increase_a_amount * dt
            return
    # Define dummy controller
    class TestController(Controller):
        REQUIRED_CONNECTIONS_READ = ('read_node',)
        REQUIRED_CONNECTIONS_WRITE = ('write_node',)
        def update(self, dt: float) -> None:
            # Read b from source node
            b_source = self.connections_read['read_node'].read()['b']
            # Write to target node
            self.connections_write['write_node'].write({'a_increase': (1 if b_source > 5 else 0)})
            return
    # Create nodes and controller
    node1 = TestNode(name="Node1", a=0.0, b=0)
    node2 = TestNode(name="Node2", a=0.0, b=10)
    controller = TestController(name="Controller1")
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