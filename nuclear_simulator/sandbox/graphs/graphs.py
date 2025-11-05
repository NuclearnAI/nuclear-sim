
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Type
if TYPE_CHECKING:
    from nuclear_simulator.sandbox.graphs.base import Component
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.edges import Edge
    from nuclear_simulator.sandbox.graphs.controllers import Controller

# Import libraries
from itertools import count
from threading import Lock
from pydantic import BaseModel


# ID allocator class for thread-safe unique ID generation
class IdCounter:
    def __init__(self, start=1):
        self._ctr = count(start)
        self._lock = Lock()
    def next(self) -> int:
        with self._lock:
            return next(self._ctr)


# Define abstract base class for graphs
class Graph(BaseModel):
    """
    Abstract base class for graphs containing nodes, edges, controllers, and sub-graphs.
    """

    # Model configuration
    model_config = {
        "extra": "allow",                 # Allow extra fields (for private attributes)
        "arbitrary_types_allowed": True,  # Allow non-Pydantic values for fields
    }

    # Set class attributes
    id: Optional[int] = None
    name: Optional[str] = None

    def __init__(
            self, 
            id_counter: IdCounter | None = None, 
            name: Optional[str] = None,
            **data: Any
        ) -> None:
        """
        Initialize graph and set up component registries.
        """

        # Initialize ID counter
        if id_counter is None:
            id_counter = IdCounter()
        _id = id_counter.next()

        # Call super init
        super().__init__(id=_id, name=name, **data)

        # Set private attributes
        self.id_counter = id_counter
        self.graphs: dict[int, Graph] = {}
        self.nodes: dict[int, Node] = {}
        self.edges: dict[int, Edge] = {}
        self.controllers: dict[int, Controller] = {}
        
        # Done
        return
    
    def __repr__(self) -> str:
        return f"Graph[Nodes: {len(self.get_nodes())} | Edges: {len(self.get_edges())}]"
    
    def get_nodes(self) -> dict[int, Node]:
        """Return dict of nodes in the graph, recursively including sub-graphs."""
        nodes = self.nodes
        for g in self.graphs.values():
            g_nodes = g.get_nodes()
            if any(id in nodes for id in g_nodes):
                raise ValueError("Duplicate node IDs found in sub-graphs")
            nodes.update(g_nodes)
        return nodes
    
    def get_edges(self) -> dict[int, Edge]:
        """Return dict of edges in the graph, recursively including sub-graphs."""
        edges = self.edges
        for g in self.graphs.values():
            g_edges = g.get_edges()
            if any(id in edges for id in g_edges):
                raise ValueError("Duplicate edge IDs found in sub-graphs")
            edges.update(g_edges)
        return edges
    
    def get_controllers(self) -> dict[int, Controller]:
        """Return dict of controllers in the graph, recursively including sub-graphs."""
        controllers = self.controllers
        for g in self.graphs.values():
            g_controllers = g.get_controllers()
            if any(id in controllers for id in g_controllers):
                raise ValueError("Duplicate controller IDs found in sub-graphs")
            controllers.update(g_controllers)
        return controllers
    
    def get_all_components(self) -> dict[int, Component]:
        """Return dict of all components (nodes, edges, controllers) in the graph."""
        # Initialize component dictionary
        components: dict[int, Component] = {}
        # Add nodes
        nodes = self.get_nodes()
        if any(id in components for id in nodes):
            raise ValueError("Duplicate node IDs found in graph components")
        components.update(nodes)
        # Add edges
        edges = self.get_edges()
        if any(id in components for id in edges):
            raise ValueError("Duplicate edge IDs found in graph components")
        components.update(edges)
        # Add controllers
        controllers = self.get_controllers()
        if any(id in components for id in controllers):
            raise ValueError("Duplicate controller IDs found in graph components")
        components.update(controllers)
        # Return output
        return components
    
    def get_component(self, identifier: int | str) -> Component:
        """
        Get a component (node, edge, or controller) by its id or name.
        Args:
            identifier: The id (int) or name (str) of the component to retrieve.
        Returns:
            The component with the specified id or name.
        """
        if isinstance(identifier, int):
            return self.get_component_from_id(identifier)
        elif isinstance(identifier, str):
            return self.get_component_from_name(identifier)
        else:
            raise TypeError("Identifier must be an int (id) or str (name)")
    
    def get_component_from_id(self, id: int) -> Component:
        """
        Get a component (node, edge, or controller) by its id.
        Args:
            id: The id of the component to retrieve.
        Returns:
            The component with the specified id.
        """
        all_components: dict[int, Component] = self.get_all_components()
        if id in all_components:
            return all_components[id]
        else:
            raise KeyError(f"No component with id '{id}' found in graph")
        
    def get_component_from_name(self, name: str) -> Component:
        """
        Get a component (node, edge, or controller) by its name.
        Args:
            name: The name of the component to retrieve.
        Returns:
            The component with the specified name.
        """
        all_components: dict[int, Component] = self.get_all_components()
        for comp in all_components.values():
            if comp.name == name:
                return comp
        raise KeyError(f"No component with name '{name}' found in graph")
    
    def add_node(
            self, 
            node_type: Type[Node], 
            name: Optional[str] = None,
            **kwargs
        ) -> Node:
        """
        Add a node to the graph.
        Args:
            node_type: The node class instance to add.
            name:      Optional name for the node.
            **kwargs:  Additional keyword arguments for the node.
        Modifies:
            Updates self.nodes with the new node.
        """
        
        # Get node id
        id = self.id_counter.next()

        # Create node instance
        node = node_type(id=id, name=name, **kwargs)
        self.nodes[id] = node

        # Return node
        return node
    
    def add_edge(
            self,
            edge_type: Type[Edge],
            node_source: Node,
            node_target: Node,
            name: Optional[str] = None,
            **kwargs
        ) -> Edge:
        """
        Add an edge to the graph.
        Args:
            edge_type:      The edge class instance to add.
            node_source:    The source node for the edge.
            node_target:    The target node for the edge.
            name:           Optional name for the edge.
            **kwargs:       Additional keyword arguments for the edge.
        Modifies:
            Updates self.edges with the new edge.
        """

        # Check that nodes exist in graph
        if node_source not in self.get_nodes().values():
            raise ValueError("Source node not found in graph")
        if node_target not in self.get_nodes().values():
            raise ValueError("Target node not found in graph")

        # Get edge id
        id = self.id_counter.next()

        # Create edge instance
        edge = edge_type(
            node_source=node_source,
            node_target=node_target,
            id=id,
            name=name,
            **kwargs
        )
        self.edges[id] = edge

        # Return edge
        return edge

    def add_controller(
            self,
            controller_type: type[Controller],
            connections: dict[str, Node | Edge],
            name: Optional[str] = None,
            **kwargs
        ) -> Controller:
        """
        Add a controller to the graph.
        Args:
            controller_type: The controller class instance to add.
            connections:     Dict of connection names to Node/Edge instances.
            name:            Optional name for the controller.
            **kwargs:        Additional keyword arguments for the controller.
        Modifies:
            Updates self.controllers with the new controller.
        """

        # Get controller id
        id = self.id_counter.next()

        # Create controller instance
        controller = controller_type(id=id, name=name, **kwargs)
        controller.add_connections(**connections)
        self.controllers[id] = controller

        # Return controller
        return controller
    
    def add_graph(
            self,
            graph_type: type[Graph],
            name: Optional[str] = None,
            **kwargs
        ):
        """
        Add a sub-graph to the graph.
        Args:
            graph_type: The graph class instance to add.
            name:       Optional name for the sub-graph.
            **kwargs:   Additional keyword arguments for the sub-graph.
        Modifies:
            Updates self.graphs with the new sub-graph.
        """

        # Create graph instance
        graph = graph_type(
            id_counter=self.id_counter, 
            name=name, 
            **kwargs
        )
        self.graphs[graph.id] = graph

        # Return sub-graph
        return graph
    
    def update(self, dt: float) -> None:
        """
        Update the entire graph over a timestep dt.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates all nodes, edges, and controllers in the graph.
        """

        # Update edges
        for edge in self.get_edges().values():
            edge.update(dt)

        # Update nodes
        for node in self.get_nodes().values():
            node.update(dt)

        # Update controllers
        for controller in self.get_controllers().values():
            controller.update(dt)

        # Done
        return


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.edges import Edge
    from nuclear_simulator.sandbox.graphs.controllers import Controller
    # Create minimal graph components
    # - Node with one state variable 'a'
    class TestNode(Node):
        a: float  # generic state variable
    # - Edge that transfers 'a' between nodes, with conductance 'g'
    class PipeEdge(Edge):
        g: float  # conductance (dimensionless here)
        def update_from_signals(self, dt: float) -> None:
            # Controller can set g via signal payloads; latest wins
            for s in self.signals_incoming:
                if "g" in s.payload:
                    self.g = float(s.payload["g"])
        def calculate_flows(self, dt: float) -> dict[str, float]:
            # Flows are RATES by convention
            return {"a": self.g * (self.node_source.a - self.node_target.a)}
    # - Controller that reads 'a' from two nodes and sets edge 'g' accordingly
    class TestController(Controller):
        # Read two nodes; write to the edge
        REQUIRED_CONNECTIONS_READ = ("n1", "n2")
        REQUIRED_CONNECTIONS_WRITE = ("set_g",)
        def update(self, dt: float) -> None:
            a1 = self.connections_read["n1"].read()["a"]
            a2 = self.connections_read["n2"].read()["a"]
            # Simple control: open fully if gradient exists, else close
            new_g = 1.0 if abs(a1 - a2) > 0 else 0.0
            self.connections_write["set_g"].write({"g": new_g})
    # Build graph
    dt = 0.1
    g = Graph()
    n1 = g.add_node(TestNode, name="N1", a=10.0)
    n2 = g.add_node(TestNode, name="N2", a=0.0)
    e  = g.add_edge(PipeEdge, node_source=n1, node_target=n2, name="E", g=0.0)
    cntrl = g.add_controller(
        TestController,
        connections={"n1": n1, "n2": n2, "set_g": e},
        name="C"
    )
    # Test 1: controller latency means no flow yet (g set AFTER edges/nodes this tick)
    a1_0, a2_0 = n1.a, n2.a
    g.update(dt)
    assert n1.a == a1_0 and n2.a == a2_0, "State should not change on first tick due to control latency"
    assert e.flows is not None and abs(e.flows["a"]) < 1e-12, "Flow should be zero with g=0 on first tick"
    # Test 2: controller's command applied; flow moves 'a' from N1 -> N2
    g.update(dt)
    # Expected delta: rate = g*(10-0)=10; dt=0.1 => delta = 1.0
    assert abs(n1.a - (a1_0 - 1.0)) < 1e-9, f"n1.a expected {a1_0 - 1.0}, got {n1.a}"
    assert abs(n2.a - (a2_0 + 1.0)) < 1e-9, f"n2.a expected {a2_0 + 1.0}, got {n2.a}"
    # Test 3: continue stepping and verify flow continues
    a1_prev, a2_prev = n1.a, n2.a
    g.update(dt)
    # Flows should continue with the same rate
    rate = e.flows["a"]
    expected_delta = rate * dt
    assert abs(n1.a - (a1_prev - expected_delta)) < 1e-9, f"n1.a expected {a1_prev - expected_delta}, got {n1.a}"
    assert abs(n2.a - (a2_prev + expected_delta)) < 1e-9, f"n2.a expected {a2_prev + expected_delta}, got {n2.a}"
    # Test 4: verify component access by id and name
    assert g.get_component(n1.id) == n1, "Should retrieve node by id"
    assert g.get_component("N1") == n1, "Should retrieve node by name"
    assert g.get_component(e.id) == e, "Should retrieve edge by id"
    assert g.get_component(cntrl.id) == cntrl, "Should retrieve controller by id"
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")
