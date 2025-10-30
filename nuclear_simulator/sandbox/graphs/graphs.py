
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional, Type
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.edges import Edge
    from nuclear_simulator.sandbox.graphs.controllers import Controller

# Import libraries
from abc import ABC
from nuclear_simulator.sandbox.graphs.base import Component


# Define abstract base class for graphs
class Graph(ABC):
    """
    Abstract base class for graphs containing nodes and edges.
    """

    # Define instance attributes
    id_counter: int
    nodes: dict[int, Node]
    edges: dict[int, Edge]
    controllers: dict[int, Controller]

    def __init__(self, id_counter=None) -> None:

        # Set attributes
        self.id_counter = id_counter or 0

        # Set components
        self.nodes: dict[int, Node] = {}
        self.edges: dict[int, Edge] = {}
        self.controllers: dict[int, Controller] = {}

        # Done
        return
    
    def __repr__(self) -> str:
        return f"Graph[Nodes: {len(self.nodes)}, Edges: {len(self.edges)}, Controllers: {len(self.controllers)}]"
    
    @classmethod
    def from_dict(
            cls, 
            data: dict[str, Any], 
            registry: dict[str, Type[Component]]
        ) -> Graph:
        """
        Deserialize the graph from a dictionary.
        Args:
            data:     The dictionary representation of the graph.
            registry: A mapping from component type names to their classes.
        Returns:
            The deserialized Graph instance.
        """

        # Create graph instance
        graph = cls(id_counter=data["id_counter"])

        # Deserialize nodes
        for node_id_str, node_data in data["nodes"].items():
            node_id = int(node_id_str)
            # Get parameters
            node_type = registry[node_data["type"]]
            node_name = node_data["name"]
            node_state = node_data["state"]
            # Initialize and add to graph
            graph.nodes[node_id] = node_type(id=node_id, name=node_name, **node_state)

        # Deserialize edges
        for edge_id_str, edge_data in data["edges"].items():
            edge_id = int(edge_id_str)
            # Get parameters
            edge_type = registry[edge_data["type"]]
            edge_name = edge_data["name"]
            edge_state = edge_data["state"]
            node_source = graph.nodes[edge_data["node_source_id"]]
            node_target = graph.nodes[edge_data["node_target_id"]]
            # Initialize and add to graph
            graph.edges[edge_id] = edge_type(
                node_source=node_source,
                node_target=node_target,
                id=edge_id,
                name=edge_name,
                **edge_state
            )

        # Deserialize controllers
        for controller_id_str, controller_data in data["controllers"].items():
            controller_id = int(controller_id_str)
            # Get parameters
            controller_type = registry[controller_data["type"]]
            controller_name = controller_data["name"]
            controller_state = controller_data["state"]
            controller_connection_ids = controller_data["connection_ids"]
            # Initialize controller
            controller = controller_type(id=controller_id, name=controller_name, **controller_state)
            # Add connections
            connections = {k: graph.get_component(v) for k, v in controller_connection_ids.items()}
            controller.add_connections(**connections)
            # Add to graph
            graph.controllers[controller_id] = controller

        # Done
        return graph
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the graph to a dictionary.
        Returns:
            A dictionary representation of the graph.
        """

        # Serialize nodes
        nodes_dict = {
            node_id: {
                "type": node.__class__.__name__,
                "name": node.name,
                "state": node.state,
            }
            for node_id, node in self.nodes.items()
        }

        # Serialize edges
        edges_dict = {
            edge_id: {
                "type": edge.__class__.__name__,
                "name": edge.name,
                "state": edge.state,
                "node_source_id": edge.node_source.id,
                "node_target_id": edge.node_target.id,
            }
            for edge_id, edge in self.edges.items()
        }

        # Serialize controllers
        controllers_dict = {}
        for controller_id, controller in self.controllers.items():
            connection_ids = {}
            for key, signal in controller.connections_read.items():
                connection_ids[key] = signal.source_component.id
            for name, signal in controller.connections_write.items():
                connection_ids[name] = signal.target_component.id
            controllers_dict[controller_id] = {
                "type": controller.__class__.__name__,
                "name": controller.name,
                "state": controller.state,
                "connection_ids": connection_ids,
            }

        # Combine into graph dict
        graph_dict = {
            "id_counter": self.id_counter,
            "nodes": nodes_dict,
            "edges": edges_dict,
            "controllers": controllers_dict, 
        }

        # Return output
        return graph_dict

    def get_component(self, id: int) -> Component:
        """
        Get a component (node, edge, or controller) by its id.
        Args:
            id: The id of the component to retrieve.
        Returns:
            The component with the specified id.
        """

        # Search in nodes
        if id in self.nodes:
            return self.nodes[id]
        
        # Search in edges
        if id in self.edges:
            return self.edges[id]
        
        # Search in controllers
        if id in self.controllers:
            return self.controllers[id]
        
        # If not found, raise error
        raise KeyError(f"No component with id {id} found in graph")
    
    def add_node(
            self, 
            node_type: Type[Node], 
            name: Optional[str] = None,
            **state
        ) -> Node:
        """
        Add a node to the graph.
        Args:
            node_cls: The node class instance to add.
        Modifies:
            Updates self.nodes with the new node.
        """
        
        # Get node id
        id = self.id_counter
        self.id_counter += 1

        # Create node instance
        node = node_type(id=id, name=name, **state)
        self.nodes[id] = node

        # Done
        return node
    
    def add_edge(
            self,
            edge_type: Type[Edge],
            node_source_id: int,
            node_target_id: int,
            name: Optional[str] = None,
            **state
        ) -> Edge:
        """
        Add an edge to the graph.
        Args:
            edge_cls:       The edge class instance to add.
            node_source_id: The source node id for the edge.
            node_target_id: The target node id for the edge.
        Modifies:
            Updates self.edges with the new edge.
        """

        # Get edge id
        id = self.id_counter
        self.id_counter += 1

        # Create edge instance
        edge = edge_type(
            node_source=self.nodes[node_source_id],
            node_target=self.nodes[node_target_id],
            id=id,
            name=name,
            **state
        )
        self.edges[id] = edge

        # Done
        return edge

    def add_controller(
            self,
            controller_type: type[Controller],
            connection_ids: dict[str, int],
            name: Optional[str] = None,
            **state
        ) -> Controller:
        """
        Add a controller to the graph.
        Args:
            controller_cls: The controller class instance to add.
            read_connection_ids: The read connection ids for the controller.
            write_connection_ids: The write connection ids for the controller.
        Modifies:
            Updates self.controllers with the new controller.
        """

        # Get controller id
        id = self.id_counter
        self.id_counter += 1

        # Get components by ids
        components = {k: self.get_component(v) for k, v in connection_ids.items()}

        # Create controller instance
        controller = controller_type(id=id, name=name, **state)
        controller.add_connections(**components)
        self.controllers[id] = controller

        # Done
        return controller
    
    def update(self, dt: float = None, steps=1) -> None:
        """
        Update the entire graph over a timestep dt.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates all nodes, edges, and controllers in the graph.
        """

        # Get dt
        dt = dt or self.dt

        # Loop over steps
        for _ in range(steps):

            # Update edges
            for edge in self.edges.values():
                edge.update(dt)

            # Update nodes
            for node in self.nodes.values():
                node.update(dt)

            # Update controllers
            for controller in self.controllers.values():
                controller.update(dt)

            # Update time
            self.time += dt

        # Done
        return


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.edges import Edge
    from nuclear_simulator.sandbox.graphs.controllers import Controller
    # Create minimial graph components
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
        def calculate_flows(self, dt: float, node_source: Node, node_target: Node) -> dict[str, float]:
            # Flows are RATES by convention
            return {"a": self.g * (node_source.a - node_target.a)}
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
    # - Registry for deserialization
    registry = {
        "TestNode": TestNode,
        "PipeEdge": PipeEdge,
        "TestController": TestController,
    }
    # Build graph
    g = Graph(dt=0.1)
    n1 = g.add_node(TestNode, name="N1", a=10.0)
    n2 = g.add_node(TestNode, name="N2", a=0.0)
    e  = g.add_edge(PipeEdge, node_source_id=n1.id, node_target_id=n2.id, name="E", g=0.0)
    cntrl = g.add_controller(
        TestController,
        connection_ids={"n1": n1.id, "n2": n2.id, "set_g": e.id},
        name="C"
    )
    # Test 1: controller latency means no flow yet (g set AFTER edges/nodes this tick)
    a1_0, a2_0 = n1.a, n2.a
    g.update(g.dt)
    assert n1.a == a1_0 and n2.a == a2_0, "State should not change on first tick due to control latency"
    assert e.flows is not None and abs(e.flows["a"]) < 1e-12, "Flow should be zero with g=0 on first tick"
    # Test 1: controller’s command applied; flow moves 'a' from N1 -> N2
    g.update(g.dt)
    # Expected delta: rate = g*(10-0)=10; dt=0.1 => delta = 1.0
    assert abs(n1.a - (a1_0 - 1.0)) < 1e-9, f"n1.a expected {a1_0 - 1.0}, got {n1.a}"
    assert abs(n2.a - (a2_0 + 1.0)) < 1e-9, f"n2.a expected {a2_0 + 1.0}, got {n2.a}"
    # Test 3: Round-trip serialize/deserialize and continue stepping
    blob = g.to_dict()
    g2 = Graph.from_dict(blob, registry=registry)
    # One more tick on deserialized graph should continue transferring 'a'
    a1_prev, a2_prev = g2.nodes[n1.id].a, g2.nodes[n2.id].a
    g2.update(g2.dt)
    assert g2.edges[e.id].flows is not None
    rate = g2.edges[e.id].flows["a"]
    expected_delta = rate * g2.dt  # flows are rates
    assert abs(g2.nodes[n1.id].a - (a1_prev - expected_delta)) < 1e-9
    assert abs(g2.nodes[n2.id].a - (a2_prev + expected_delta)) < 1e-9
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

