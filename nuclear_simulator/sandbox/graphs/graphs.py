
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Type
if TYPE_CHECKING:
    from nuclear_simulator.sandbox.graphs.base import Component
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.graphs.edges import Edge
    from nuclear_simulator.sandbox.graphs.controllers import Controller, Signal

# Import libraries
from threading import Lock
from itertools import count
from nuclear_simulator.sandbox.graphs.base import Component


# ID allocator class for thread-safe unique ID generation
class IdCounter:
    def __init__(self, start=1):
        self._ctr = count(start)
        self._lock = Lock()
    def next(self) -> int:
        with self._lock:
            return next(self._ctr)


# Define abstract base class for graphs
class Graph(Component):
    """
    Abstract base class for graphs containing nodes, edges, controllers, and sub-graphs.
    """

    def __init__(
            self, 
            id_counter: IdCounter | None = None,
            **data: Any
        ) -> None:
        """
        Initialize graph and set up component registries.
        """

        # Initialize ID counter
        if id_counter is None:
            id_counter = IdCounter()
        id = id_counter.next()

        # Call super init
        super().__init__(id=id, **data)

        # Set private attributes
        self.id_counter = id_counter
        self.graphs: dict[int, Graph] = {}
        self.nodes: dict[int, Node] = {}
        self.edges: dict[int, Edge] = {}
        self.controllers: dict[int, Controller] = {}
        
        # Done
        return
    
    def __repr__(self) -> str:
        n_nodes = len(self.get_nodes())
        n_edges = len(self.get_edges())
        n_graphs = len(self.graphs)
        return f"{self.__class__.__name__}[Nodes: {n_nodes} | Edges: {n_edges} | Graphs: {n_graphs}]"
    
    def update(
            self, 
            dt: float, 
            steps: int = 1
        ) -> None:
        """
        Update the entire graph over a timestep dt.
        Args:
            dt:    Time step for the update.
            steps: Number of sub-steps to divide dt into.
        Modifies:
            Updates all nodes, edges, and controllers in the graph in that order.
        """

        # Loop over steps
        for i in range(steps):

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

    def get_nodes(self) -> dict[int, Node]:
        """Return dict of nodes in the graph, recursively including sub-graphs."""
        nodes = {i: n for i, n in self.nodes.items()}
        for g in self.graphs.values():
            g_nodes = g.get_nodes()
            if any(id in nodes for id in g_nodes):
                raise ValueError("Duplicate node IDs found in sub-graphs")
            nodes.update(g_nodes)
        return nodes
    
    def get_edges(self) -> dict[int, Edge]:
        """Return dict of edges in the graph, recursively including sub-graphs."""
        edges = {i: e for i, e in self.edges.items()}
        for g in self.graphs.values():
            g_edges = g.get_edges()
            if any(id in edges for id in g_edges):
                raise ValueError("Duplicate edge IDs found in sub-graphs")
            edges.update(g_edges)
        return edges
    
    def get_controllers(self) -> dict[int, Controller]:
        """Return dict of controllers in the graph, recursively including sub-graphs."""
        controllers = {i: c for i, c in self.controllers.items()}
        for g in self.graphs.values():
            g_controllers = g.get_controllers()
            if any(id in controllers for id in g_controllers):
                raise ValueError("Duplicate controller IDs found in sub-graphs")
            controllers.update(g_controllers)
        return controllers
    
    def get_graphs(self) -> dict[int, Graph]:
        """Return dict of sub-graphs in the graph, recursively including sub-graphs."""
        graphs = {i: g for i, g in self.graphs.items()}
        for g in self.graphs.values():
            g_graphs = g.get_graphs()
            if any(id in graphs for id in g_graphs):
                raise ValueError("Duplicate graph IDs found in sub-graphs")
            graphs.update(g_graphs)
        return graphs
    
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
        # Add graphs
        graphs = self.get_graphs()
        if any(id in components for id in graphs):
            raise ValueError("Duplicate graph IDs found in graph components")
        components.update(graphs)
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

        # If Node Type is a Graph, route to add_graph
        if issubclass(node_type, Graph):
            return self.add_graph(graph_type=node_type, name=name, **kwargs)
        
        # Get node id
        id = self.id_counter.next()

        # Add prefix to name
        if (name is not None) and (self.name is not None):
            name = f"{self.name}:{name}"

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

        # Add prefix to name
        if (name is not None) and (self.name is not None):
            name = f"{self.name}:{name}"

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
            connections: Optional[dict[str, Node | Edge]] = None,
            name: Optional[str] = None,
            **kwargs
        ) -> Controller:
        """
        Add a controller to the graph.
        Args:
            controller_type: The controller class instance to add.
            connections:     Optional dict of connection names to Node/Edge instances.
            name:            Optional name for the controller.
            **kwargs:        Additional keyword arguments for the controller.
        Modifies:
            Updates self.controllers with the new controller.
        """

        # Get controller id
        id = self.id_counter.next()

        # Add prefix to name
        if (name is not None) and (self.name is not None):
            name = f"{self.name}:{name}"

        # Create controller instance
        controller = controller_type(id=id, name=name, **kwargs)
        self.controllers[id] = controller

        # Add connections if provided
        if connections is not None:
            controller.add_connections(**connections)

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

        # Get id counter
        id_counter = self.id_counter

        # Add prefix to name
        if (name is not None) and (self.name is not None):
            name = f"{self.name}:{name}"

        # Create graph instance
        graph = graph_type(
            id_counter=id_counter, 
            name=name, 
            **kwargs
        )
        self.graphs[graph.id] = graph

        # Return sub-graph
        return graph
    
    def swap_node(
            self,
            node: Node,
            new_node_type: Type[Node],
            name: Optional[str] = None,
            **kwargs
        ):
        """
        Replace a node in the graph with a new node of a different type.
        Args:
            node:           The Node to replace.
            new_node_type:  The type (class) of the new node to create.
            name:           Optional name for the new node (default to old name).
            **kwargs:       Additional keyword args to pass to the new node constructor.
        Returns:
            The new Node instance that was created and added to the graph.
        """

        # Check if node is in this graph or a sub-graph
        if node not in self.nodes:
            for g in self.graphs.values():
                if node in g.get_nodes().values():
                    return g.swap_node(
                        node=node,
                        new_node_type=new_node_type,
                        name=name,
                        **kwargs
                    )
            raise ValueError("Node to swap not found in this graph or sub-graphs")

        # Get old node information
        old_id = node.id
        old_name = node.name
        old_flows = node.flows
        old_edges_incoming = list(node.edges_incoming)
        old_edges_outgoing = list(node.edges_outgoing)
        old_signals_incoming = list(node.signals_incoming)
        old_signals_outgoing = list(node.signals_outgoing)

        # Delete old node
        del self.nodes[old_id]

        # Get new name
        if name is None:
            name = old_name

        # Add new node
        new_node = new_node_type(id=old_id, name=name, **kwargs)
        self.nodes[old_id] = new_node

        # Restore attributes
        new_node.flows = old_flows
        new_node.edges_incoming = old_edges_incoming
        new_node.edges_outgoing = old_edges_outgoing
        new_node.signals_incoming = old_signals_incoming
        new_node.signals_outgoing = old_signals_outgoing

        # Reconnect graph references
        for edge in old_edges_incoming:
            edge.node_target = new_node
        for edge in old_edges_outgoing:
            edge.node_source = new_node
        for signal in old_signals_incoming:
            signal.target_component = new_node
        for signal in old_signals_outgoing:
            signal.source_component = new_node

        # Return new node
        return new_node
    
    def swap_edge(
            self,
            edge: Edge,
            new_edge_type: Type[Edge],
            name: Optional[str] = None,
            **kwargs
        ):
        """
        Replace an edge in the graph with a new edge of a different type.
        Args:
            edge:           The Edge to replace.
            new_edge_type:  The type (class) of the new edge to create.
            name:           Optional name for the new edge (default to old name).
            **kwargs:       Additional keyword args to pass to the new edge constructor.
        Returns:
            The new Edge instance that was created and added to the graph.
        """

        # Check if edge is in this graph or a sub-graph
        if edge not in self.edges:
            for g in self.graphs.values():
                if edge in g.get_edges().values():
                    return g.swap_edge(
                        edge=edge,
                        new_edge_type=new_edge_type,
                        name=name,
                        **kwargs
                    )
            raise ValueError("Edge to swap not found in this graph or sub-graphs")

        # Get old edge information
        old_id = edge.id
        old_name = edge.name
        old_flows = edge.flows
        old_node_source = edge.node_source
        old_node_target = edge.node_target
        old_alias_source = edge.alias_source
        old_alias_target = edge.alias_target
        old_signals_incoming = list(edge.signals_incoming)
        old_signals_outgoing = list(edge.signals_outgoing)

        # Delete old edge
        del self.edges[old_id]

        # Get new name
        if name is None:
            name = old_name

        # Add prefix to name
        if (name is not None) and (self.name is not None):
            name = f"{self.name}:{name}"

        # Add new edge
        new_edge = new_edge_type(
            node_source=old_node_source,
            node_target=old_node_target,
            id=old_id,
            name=name,
            **kwargs
        )
        self.edges[old_id] = new_edge

        # Restore attributes
        new_edge.flows = old_flows
        new_edge.alias_source = old_alias_source
        new_edge.alias_target = old_alias_target
        new_edge.signals_incoming = old_signals_incoming
        new_edge.signals_outgoing = old_signals_outgoing

        # Reconnect graph
        old_node_source.edges_outgoing.remove(edge)
        old_node_source.edges_outgoing.append(new_edge)
        old_node_target.edges_incoming.remove(edge)
        old_node_target.edges_incoming.append(new_edge)
        for signal in old_signals_incoming:
            signal.target_component = new_edge
        for signal in old_signals_outgoing:
            signal.source_component = new_edge

        # Return new edge
        return new_edge
    
    def swap_controller(
            self,
            controller: Controller,
            new_controller_type: Type[Controller],
            name: Optional[str] = None,
            **kwargs
        ):
        return NotImplementedError("Controller swapping not yet implemented")
    
    def swap_graph(
            self,
            graph: Graph,
            new_graph_type: Type[Graph],
            name: Optional[str] = None,
            **kwargs
        ):
        return NotImplementedError("Graph swapping not yet implemented")

    def swap_component(
            self,
            component: Component,
            new_component_type: Type[Component],
            name: Optional[str] = None,
            **kwargs
        ):
        """
        Replace a component in the graph with a new component of a different type.
        Args:
            component:          The Component to replace.
            new_component_type: The type (class) of the new component to create.
            name:               Optional name for the new component (default to old name).
            **kwargs:           Additional keyword args to pass to the new component constructor.
        Returns:
            The new Component instance that was created and added to the graph.
        """
        if isinstance(component, Node):
            return self.swap_node(
                node=component,
                new_node_type=new_component_type,
                name=name,
                **kwargs
            )
        elif isinstance(component, Edge):
            return self.swap_edge(
                edge=component,
                new_edge_type=new_component_type,
                name=name,
                **kwargs
            )
        elif isinstance(component, Controller):
            return self.swap_controller(
                controller=component,
                new_controller_type=new_component_type,
                name=name,
                **kwargs
            )
        elif isinstance(component, Graph):
            return self.swap_graph(
                graph=component,
                new_graph_type=new_component_type,
                name=name,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported component type: {type(component)}")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the graph to a dictionary.
        Handles all nodes, edges, controllers, and subgraphs.
        """
        # Import required modules for class lookup
        from nuclear_simulator.sandbox.graphs.nodes import Node
        from nuclear_simulator.sandbox.graphs.edges import Edge
        from nuclear_simulator.sandbox.graphs.controllers import Controller
        
        # Initialize the output dictionary
        graph_dict = {
            "class": self.__class__.__module__ + "." + self.__class__.__name__,
            "id": self.id,
            "name": self.name,
            "id_counter": self.id_counter.next() - 1,  # Get current counter state
            "data": {},  # Additional data passed to __init__
            "subgraphs": {},
            "nodes": {},
            "edges": {},
            "controllers": {}
        }
        
        # Store any additional state fields
        for field in self.get_state_fields():
            if field not in ["id", "name"]:
                graph_dict["data"][field] = getattr(self, field)
        
        # Serialize subgraphs recursively
        for graph_id, subgraph in self.graphs.items():
            graph_dict["subgraphs"][str(graph_id)] = subgraph.to_dict()
        
        # Serialize nodes
        for node_id, node in self.nodes.items():
            node_dict = {
                "class": node.__class__.__module__ + "." + node.__class__.__name__,
                "id": node.id,
                "name": node.name,
                "state": {}
            }
            # Store all state fields
            for field in node.get_state_fields():
                if field not in ["id", "name"]:
                    node_dict["state"][field] = getattr(node, field)
            graph_dict["nodes"][str(node_id)] = node_dict
        
        # Serialize edges
        for edge_id, edge in self.edges.items():
            edge_dict = {
                "class": edge.__class__.__module__ + "." + edge.__class__.__name__,
                "id": edge.id,
                "name": edge.name,
                "node_source_id": edge.node_source.id,
                "node_target_id": edge.node_target.id,
                "alias_source": edge.alias_source,
                "alias_target": edge.alias_target,
                "state": {}
            }
            # Store all state fields
            for field in edge.get_state_fields():
                if field not in ["id", "name"]:
                    edge_dict["state"][field] = getattr(edge, field)
            graph_dict["edges"][str(edge_id)] = edge_dict
        
        # Serialize controllers
        for controller_id, controller in self.controllers.items():
            controller_dict = {
                "class": controller.__class__.__module__ + "." + controller.__class__.__name__,
                "id": controller.id,
                "name": controller.name,
                "connections": {},
                "state": {}
            }
            
            # Store connections (signal targets)
            for conn_name, signal in controller.connections_read.items():
                # Signal source is the component being read
                source_component = signal.source_component
                controller_dict["connections"][conn_name] = {
                    "type": "read",
                    "component_id": source_component.id
                }
            
            for conn_name, signal in controller.connections_write.items():
                # Signal target is the component being written to
                target_component = signal.target_component
                controller_dict["connections"][conn_name] = {
                    "type": "write",
                    "component_id": target_component.id
                }
            
            # Store all state fields
            for field in controller.get_state_fields():
                if field not in ["id", "name"]:
                    controller_dict["state"][field] = getattr(controller, field)
            
            graph_dict["controllers"][str(controller_id)] = controller_dict
        
        return graph_dict
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Graph:
        """
        Reconstruct a graph from a dictionary.
        Rebuilds in order: subgraphs → nodes → edges → controllers
        """
        import importlib
        from nuclear_simulator.sandbox.graphs.controllers import Signal
        
        # Helper function to get class from string
        def get_class_from_string(class_string: str):
            module_name, class_name = class_string.rsplit(".", 1)
            if module_name == "__main__":
                # Handle test classes defined in __main__
                import __main__
                return getattr(__main__, class_name)
            else:
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
        
        # Create the graph instance with the saved ID counter state
        id_counter = IdCounter(start=data.get("id_counter", 0) + 1)
        graph_class = get_class_from_string(data["class"]) if "class" in data else cls
        
        # Prepare init data
        init_data = data.get("data", {}).copy()
        init_data["name"] = data.get("name")
        
        # Create graph with manual ID assignment
        graph = graph_class(id_counter=id_counter, **init_data)
        # Override the auto-assigned ID with the saved one
        graph.id = data["id"]
        
        # Keep track of all components by ID for connection rebuilding
        all_components = {graph.id: graph}
        
        # 1. Rebuild subgraphs recursively
        for graph_id_str, subgraph_data in data.get("subgraphs", {}).items():
            subgraph = Graph.from_dict(subgraph_data)
            subgraph.id_counter = graph.id_counter  # Share the ID counter
            graph.graphs[subgraph.id] = subgraph
            # Collect all components from subgraph
            all_components.update(subgraph.get_all_components())
            all_components[subgraph.id] = subgraph
        
        # 2. Rebuild nodes
        for node_id_str, node_data in data.get("nodes", {}).items():
            node_class = get_class_from_string(node_data["class"])
            node_state = node_data.get("state", {})
            node = node_class(
                id=node_data["id"],
                name=node_data.get("name"),
                **node_state
            )
            graph.nodes[node.id] = node
            all_components[node.id] = node
        
        # 3. Rebuild edges (with connections to nodes)
        for edge_id_str, edge_data in data.get("edges", {}).items():
            edge_class = get_class_from_string(edge_data["class"])
            
            # Find source and target nodes
            source_id = edge_data["node_source_id"]
            target_id = edge_data["node_target_id"]
            node_source = all_components[source_id]
            node_target = all_components[target_id]
            
            edge_state = edge_data.get("state", {})
            edge = edge_class(
                id=edge_data["id"],
                name=edge_data.get("name"),
                node_source=node_source,
                node_target=node_target,
                alias_source=edge_data.get("alias_source"),
                alias_target=edge_data.get("alias_target"),
                **edge_state
            )
            graph.edges[edge.id] = edge
            all_components[edge.id] = edge
        
        # 4. Rebuild controllers (with connections)
        for controller_id_str, controller_data in data.get("controllers", {}).items():
            controller_class = get_class_from_string(controller_data["class"])
            controller_state = controller_data.get("state", {})
            
            controller = controller_class(
                id=controller_data["id"],
                name=controller_data.get("name"),
                **controller_state
            )
            graph.controllers[controller.id] = controller
            all_components[controller.id] = controller
            
            # Rebuild connections
            connections = {}
            for conn_name, conn_data in controller_data.get("connections", {}).items():
                component_id = conn_data["component_id"]
                component = all_components[component_id]
                connections[conn_name] = component
            
            # Add all connections at once
            if connections:
                controller.add_connections(**connections)
        
        return graph



# Test
if __name__ == "__main__":
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
def test_file():
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
    # Run simulation
    dt = 1.0
    n_steps = 10
    for t in range(n_steps):
        g.update(dt)
    # Convert to dict and back
    g_dict = g.to_dict()
    g_restored = Graph.from_dict(g_dict)
    # Check that restored graph matches original
    print(f"Original graph: {g}")
    print(f"Restored graph: {g_restored}")
    # Verify structure is preserved
    assert len(g.nodes) == len(g_restored.nodes), "Node count mismatch"
    assert len(g.edges) == len(g_restored.edges), "Edge count mismatch"
    assert len(g.controllers) == len(g_restored.controllers), "Controller count mismatch"
    # Verify node states
    for node_id in g.nodes:
        orig_node = g.nodes[node_id]
        restored_node = g_restored.nodes.get(node_id)
        assert restored_node is not None, f"Node {node_id} not found in restored graph"
        assert orig_node.name == restored_node.name, f"Node {node_id} name mismatch"
        assert orig_node.a == restored_node.a, f"Node {node_id} state mismatch"
    print("Serialization test passed!")
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")
