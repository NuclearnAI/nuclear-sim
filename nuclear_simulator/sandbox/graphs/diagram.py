
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Callable
    from nuclear_simulator.sandbox.graphs import Graph, Node, Edge, Controller, Signal

# Import libraries
import tempfile
import pygraphviz as pgv
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from io import BytesIO



def draw_graph(
        graph: Graph, 
        get_style: Callable[[Any], dict[str, Any]] | None = None,
        fig=None, 
        ax=None,
    ):
    """
    Render a Graph as a flow diagram using PyGraphviz.
    Args:
        graph:      Graph to visualize.
        get_style:  Optional function to get style dict for each component.
        fig:        Optional matplotlib Figure to plot into.
        ax:         Optional matplotlib Axes to plot into.
    Returns:
        fig, ax: Matplotlib Figure and Axes containing the diagram.
    """

    # Get default style function
    if get_style is None:
        def get_style(component: Any) -> dict[str, Any]:
            return {}

    # Create figure and axis if not provided
    if fig is None and ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    elif fig is None:
        fig = ax.get_figure()
    elif ax is None:
        fig.clf()
        ax = fig.add_subplot(1, 1, 1)
    plt.ion()
    plt.show()

    # Build a graph diagram
    diagram = pgv.AGraph(directed=True)

    # Recursive function to add nodes and subgraphs
    def _add_nodes(d: pgv.AGraph, g: Graph):
        """Recursively add nodes and subgraphs to the diagram."""
        # Add nodes
        for node in g.nodes.values():
            label = node.name or node.id
            style = get_style(node)
            d.add_node(node.id, label=label, **style)
        # Add controllers as nodes
        for controller in g.controllers.values():
            label = controller.name or controller.id
            style = {"shape": "diamond"}
            style.update(get_style(controller))
            d.add_node(controller.id, label=label, **style)
        # Recurse into subgraphs
        for sg in g.graphs.values():
            label = sg.name or sg.id
            style = get_style(sg)
            sd = d.add_subgraph(name=f'cluster_{sg.id}', label=label, **style)
            _add_nodes(sd, sg)
        # Done
        return
    
    # Add nodes to diagram
    _add_nodes(diagram, graph)

    # Add edges
    for edge in graph.get_edges().values():
        label = edge.__class__.__name__
        style = get_style(edge)
        diagram.add_edge(
            edge.node_source.id, 
            edge.node_target.id, 
            label=label,
            **style,
        )

    # Add signals from controllers to edges
    for controller in graph.get_controllers().values():
        all_signals = (
            list(controller.connections_read.values())
            + list(controller.connections_write.values())
        )
        for signal in all_signals:
            label = "read"
            style = {"style": "dashed", "color": "yellow"}
            style.update(get_style(signal))
            diagram.add_edge(
                signal.source_component.id,
                signal.target_component.id,
                label=label,
                **style,
            )

    # Choose a layout engine: 'dot' is best for flows
    diagram.layout("dot")

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(suffix=".png") as tmpfile:
        # Get output filename
        outfile = tmpfile.name
        # Output PNG
        diagram.draw(outfile)
        # Render to memory as PNG bytes
        png_bytes = diagram.draw(format="png", prog="dot")
        # Convert to an image array
        img = mpimg.imread(BytesIO(png_bytes))

    # Plot the image
    ax.imshow(img)
    ax.axis("off")
    plt.pause(0.1)
    
    # Done
    return fig, ax


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.plants import Plant
    # Create plant
    plant = Plant()
    # Draw graph
    fig, ax = draw_graph(plant)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests complete.")

