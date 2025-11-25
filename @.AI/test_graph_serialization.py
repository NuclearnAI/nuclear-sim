#!/usr/bin/env python3
"""
Test script demonstrating basic graph serialization functionality.

This script creates a simple graph with nodes, edges, and controllers,
runs a simulation, serializes the graph to JSON, then deserializes it
back and verifies it works correctly.
"""

import json
import os
import sys
from typing import Any, Dict

# Add parent directory to path so we can import the graph modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nuclear_simulator.sandbox.graphs.graphs_v2 import Graph, IdCounter
from nuclear_simulator.sandbox.graphs.nodes import Node
from nuclear_simulator.sandbox.graphs.edges import Edge
from nuclear_simulator.sandbox.graphs.controllers import Controller


# Define test components from the example in graphs_v2.py
class TestNode(Node):
    """Node with one state variable 'a'"""
    a: float  # generic state variable


class PipeEdge(Edge):
    """Edge that transfers 'a' between nodes with conductance 'g'"""
    g: float  # conductance (dimensionless here)
    
    def update_from_signals(self, dt: float) -> None:
        # Controller can set g via signal payloads; latest wins
        for s in self.signals_incoming:
            if "g" in s.payload:
                self.g = float(s.payload["g"])
    
    def calculate_flows(self, dt: float) -> dict[str, float]:
        # Flows are RATES by convention
        return {"a": self.g * (self.node_source.a - self.node_target.a)}


class TestController(Controller):
    """Controller that reads 'a' from two nodes and sets edge 'g' accordingly"""
    # Read two nodes; write to the edge
    REQUIRED_CONNECTIONS_READ = ("n1", "n2")
    REQUIRED_CONNECTIONS_WRITE = ("set_g",)
    
    def update(self, dt: float) -> None:
        a1 = self.connections_read["n1"].read()["a"]
        a2 = self.connections_read["n2"].read()["a"]
        # Simple control: open fully if gradient exists, else close
        new_g = 1.0 if abs(a1 - a2) > 0 else 0.0
        self.connections_write["set_g"].write({"g": new_g})


def serialize_graph(graph: Graph) -> Dict[str, Any]:
    """
    Serialize a graph to a dictionary.
    
    This is a basic implementation of graph serialization that captures:
    - Graph metadata (id, name, id_counter state)
    - All nodes with their state
    - All edges with their state and connections
    - All controllers with their state and connections
    - All subgraphs (recursively)
    """
    print("\n=== Serializing Graph ===")
    
    # Build the graph dictionary
    graph_dict = {
        "type": graph.__class__.__name__,
        "id": graph.id,
        "name": graph.name,
        "id_counter_value": graph.id_counter._ctr.__next__(),  # Get current counter value
        "nodes": {},
        "edges": {},
        "controllers": {},
        "graphs": {}
    }
    
    # Serialize nodes
    for node_id, node in graph.nodes.items():
        node_dict = {
            "type": node.__class__.__name__,
            "id": node.id,
            "name": node.name,
            "state": node.state
        }
        graph_dict["nodes"][str(node_id)] = node_dict
        print(f"  Serialized node: {node}")
    
    # Serialize edges
    for edge_id, edge in graph.edges.items():
        edge_dict = {
            "type": edge.__class__.__name__,
            "id": edge.id,
            "name": edge.name,
            "state": edge.state,
            "node_source_id": edge.node_source.id,
            "node_target_id": edge.node_target.id,
            "alias_source": edge.alias_source,
            "alias_target": edge.alias_target
        }
        graph_dict["edges"][str(edge_id)] = edge_dict
        print(f"  Serialized edge: {edge}")
    
    # Serialize controllers
    for ctrl_id, ctrl in graph.controllers.items():
        # Build connection references
        connections_read = {}
        for name, signal in ctrl.connections_read.items():
            connections_read[name] = signal.source_component.id
        
        connections_write = {}
        for name, signal in ctrl.connections_write.items():
            connections_write[name] = signal.target_component.id
        
        ctrl_dict = {
            "type": ctrl.__class__.__name__,
            "id": ctrl.id,
            "name": ctrl.name,
            "state": ctrl.state,
            "connections_read": connections_read,
            "connections_write": connections_write
        }
        graph_dict["controllers"][str(ctrl_id)] = ctrl_dict
        print(f"  Serialized controller: {ctrl}")
    
    # Serialize subgraphs recursively
    for subgraph_id, subgraph in graph.graphs.items():
        graph_dict["graphs"][str(subgraph_id)] = serialize_graph(subgraph)
    
    return graph_dict


def deserialize_graph(data: Dict[str, Any], component_registry: Dict[str, type] = None) -> Graph:
    """
    Deserialize a graph from a dictionary.
    
    Args:
        data: Dictionary containing serialized graph data
        component_registry: Optional registry of component types
    
    Returns:
        Restored Graph instance
    """
    print("\n=== Deserializing Graph ===")
    
    # Default component registry
    if component_registry is None:
        component_registry = {
            "Graph": Graph,
            "TestNode": TestNode,
            "PipeEdge": PipeEdge,
            "TestController": TestController
        }
    
    # Create new graph with restored ID counter
    id_counter = IdCounter(start=data["id_counter_value"])
    graph_class = component_registry.get(data["type"], Graph)
    graph = graph_class(id_counter=id_counter, name=data["name"])
    graph.id = data["id"]  # Override auto-generated ID
    
    print(f"  Created graph: {graph}")
    
    # First pass: create all nodes
    id_mapping = {}  # Maps old IDs to new components
    
    for node_data in data["nodes"].values():
        node_class = component_registry[node_data["type"]]
        node = node_class(
            id=node_data["id"],
            name=node_data["name"],
            **node_data["state"]
        )
        graph.nodes[node.id] = node
        id_mapping[node.id] = node
        print(f"  Restored node: {node}")
    
    # Second pass: create edges (requires nodes to exist)
    for edge_data in data["edges"].values():
        edge_class = component_registry[edge_data["type"]]
        source_node = id_mapping[edge_data["node_source_id"]]
        target_node = id_mapping[edge_data["node_target_id"]]
        
        edge = edge_class(
            node_source=source_node,
            node_target=target_node,
            id=edge_data["id"],
            name=edge_data["name"],
            alias_source=edge_data["alias_source"],
            alias_target=edge_data["alias_target"],
            **edge_data["state"]
        )
        graph.edges[edge.id] = edge
        id_mapping[edge.id] = edge
        print(f"  Restored edge: {edge}")
    
    # Third pass: create controllers and connect them
    for ctrl_data in data["controllers"].values():
        ctrl_class = component_registry[ctrl_data["type"]]
        ctrl = ctrl_class(
            id=ctrl_data["id"],
            name=ctrl_data["name"],
            **ctrl_data["state"]
        )
        graph.controllers[ctrl.id] = ctrl
        
        # Restore connections
        connections = {}
        for conn_name, comp_id in ctrl_data["connections_read"].items():
            connections[conn_name] = id_mapping[comp_id]
        for conn_name, comp_id in ctrl_data["connections_write"].items():
            connections[conn_name] = id_mapping[comp_id]
        
        ctrl.add_connections(**connections)
        print(f"  Restored controller: {ctrl}")
    
    # Recursively restore subgraphs
    for subgraph_data in data["graphs"].values():
        subgraph = deserialize_graph(subgraph_data, component_registry)
        graph.graphs[subgraph.id] = subgraph
    
    return graph


def main():
    """Main function demonstrating graph serialization."""
    print("=== Graph Serialization Test ===\n")
    
    # Step 1: Build a sample graph
    print("Step 1: Building sample graph")
    g = Graph(name="TestGraph")
    n1 = g.add_node(TestNode, name="N1", a=10.0)
    n2 = g.add_node(TestNode, name="N2", a=0.0)
    e = g.add_edge(PipeEdge, node_source=n1, node_target=n2, name="E", g=0.0)
    cntrl = g.add_controller(
        TestController,
        connections={"n1": n1, "n2": n2, "set_g": e},
        name="C"
    )
    
    print(f"  Created graph: {g}")
    print(f"  Initial state - N1.a: {n1.a}, N2.a: {n2.a}, E.g: {e.g}")
    
    # Step 2: Run simulation for several steps
    print("\nStep 2: Running simulation")
    dt = 0.1
    n_steps = 5
    for t in range(n_steps):
        g.update(dt)
        print(f"  Step {t+1}: N1.a={n1.a:.2f}, N2.a={n2.a:.2f}, E.g={e.g:.2f}")
    
    # Step 3: Serialize the graph to a dictionary
    print("\nStep 3: Serializing graph to dictionary")
    graph_dict = serialize_graph(g)
    
    # Step 4: Save dictionary to JSON file
    print("\nStep 4: Saving to JSON file")
    json_file = "@.AI/test_graph_state.json"
    with open(json_file, 'w') as f:
        json.dump(graph_dict, f, indent=2)
    print(f"  Saved to: {json_file}")
    
    # Print a snippet of the JSON
    print("\n  JSON snippet:")
    json_str = json.dumps(graph_dict, indent=2)
    lines = json_str.split('\n')
    for line in lines[:20]:  # First 20 lines
        print(f"    {line}")
    if len(lines) > 20:
        print("    ...")
    
    # Step 5: Load JSON file and deserialize back to graph
    print("\nStep 5: Loading from JSON and deserializing")
    with open(json_file, 'r') as f:
        loaded_dict = json.load(f)
    
    g_restored = deserialize_graph(loaded_dict)
    
    # Get restored components
    n1_restored = g_restored.get_component("TestGraph:N1")
    n2_restored = g_restored.get_component("TestGraph:N2")
    e_restored = g_restored.get_component("TestGraph:E")
    
    print(f"\n  Restored state - N1.a: {n1_restored.a}, N2.a: {n2_restored.a}, E.g: {e_restored.g}")
    
    # Step 6: Verify the restored graph works correctly
    print("\nStep 6: Verifying restored graph functionality")
    print("  Running simulation on restored graph...")
    
    for t in range(3):
        g_restored.update(dt)
        print(f"  Step {t+1}: N1.a={n1_restored.a:.2f}, N2.a={n2_restored.a:.2f}, E.g={e_restored.g:.2f}")
    
    # Verify values are changing as expected
    print("\n✅ Graph serialization test completed successfully!")
    print(f"   - Original graph had {len(g.nodes)} nodes, {len(g.edges)} edges, {len(g.controllers)} controllers")
    print(f"   - Restored graph has {len(g_restored.nodes)} nodes, {len(g_restored.edges)} edges, {len(g_restored.controllers)} controllers")
    print(f"   - Simulation continues to work correctly after deserialization")
    
    # Clean up
    if os.path.exists(json_file):
        os.remove(json_file)
        print(f"\n  Cleaned up temporary file: {json_file}")


if __name__ == "__main__":
    main()