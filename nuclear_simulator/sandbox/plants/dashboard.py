
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.graphs import Graph, Component

# Import libraries
import colorsys
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from nuclear_simulator.sandbox.materials import Material, Energy, Mass, Volume
from nuclear_simulator.sandbox.graphs.diagrams import draw_graph
from nuclear_simulator.sandbox.plants.vessels import Vessel
from nuclear_simulator.sandbox.plants.edges import (
    TransferEdge,
    Pipe, LiquidPipe, GasPipe,
    Pump, LiquidPump, GasPump,
    HeatExchange,
    BoilingEdge, CondensingEdge,
    TurbineEdge,
)


class Dashboard:
    """Simple live dashboard for monitoring data."""

    def __init__(
            self, graph: Graph, 
            show_nodes: bool = True,
            show_edges: bool = True,
            plot_every: int = 100,
            plot_memory: int = 1000,
        ):
        """
        Initialize dashboard with monitor.
        Args:
            graph:      Graph that the dashboard will monitor.
            plot_every: Number of steps between plot updates.
        """

        # Set attributes
        self.graph = graph
        self.show_nodes = show_nodes
        self.show_edges = show_edges
        self.plot_every = plot_every
        self.plot_memory = plot_memory

        # Initialize data storage
        self.data = {
            'T': {}, 
            'P': {}, 
            'm': {}, 
            'U': {}, 
            'V': {},
            'dm/dt': {}, 
            'dU/dt': {}, 
            'dV/dt': {},
        }

        # Initialize plot
        with plt.rc_context({'font.size': 6}):
            fig, ax = plt.subplots(2, 5, layout='constrained')
            fig.set_size_inches(16, 9)
            fig.canvas.manager.full_screen_toggle()
            plt.ion()
            plt.show()
            plt.pause(0.1)
            self.fig = fig
            self.ax = ax

        # Set up ax dictionary
        self.ax_dict = {
            'm':       self.ax[0, 0],
            'U':       self.ax[0, 1],
            'V':       self.ax[0, 2],
            'T':       self.ax[0, 3],
            'legend':  self.ax[0, 4],
            'dm/dt':   self.ax[1, 0],
            'dU/dt':   self.ax[1, 1],
            'dV/dt':   self.ax[1, 2],
            'P':       self.ax[1, 3],
            'diagram': self.ax[1, 4],
        }
        self.plot_colors: dict[str, tuple] = {}

        # Set flags for updating dashboard elements
        self.step_count = 0
        self._update_diagram: bool = True
        self._update_legend: bool = True

        # Step once to initialize figures
        self.step()

        # Done
        return

    def step(self):
        """Run one update and plot cycle."""
        self.update_data()
        if self.step_count % self.plot_every == 0:
            self.update_figure()
        self.step_count += 1
        return

    def update_data(self):
        """Update data storage with current graph state."""

        # Loop over nodes
        if self.show_nodes:
            for node in self.graph.get_nodes().values():

                # Get name
                name = node.name or node.id

                # Check for pressure
                P = node.state.get('P', None)

                # Check for material contents
                if 'contents' in node.state:
                    mat: Material = node.state['contents']
                    # Log material properties
                    self.data['T'].setdefault(f'{name}.contents', []).append(mat.T)
                    # Add pressure if available
                    if P is not None:
                        self.data['P'].setdefault(f'{name}.contents', []).append(P)
                    # Ignore mass, energy, volume for environment components
                    if not name.lower().startswith('env:'):
                        self.data['m'].setdefault(f'{name}.contents', []).append(mat.m)
                        self.data['U'].setdefault(f'{name}.contents', []).append(mat.U)
                        self.data['V'].setdefault(f'{name}.contents', []).append(mat.V)

        # Loop over edges
        if self.show_edges:
            for edge in self.graph.get_edges().values():

                # Get name
                name = edge.name or edge.id

                # Check for energy output
                if isinstance(edge, TurbineEdge):
                    energy_out = edge.energy_output
                    self.data['dU/dt'].setdefault(f'{name}.energy_output', []).append(energy_out)

                # Loop over material flows and log
                for key, value in edge.flows.items():
                    if isinstance(value, Energy):
                        self.data['dU/dt'].setdefault(f'{name}.{key}', []).append(value.U)
                    elif isinstance(value, Mass):
                        self.data['dm/dt'].setdefault(f'{name}.{key}', []).append(value.m)
                    elif isinstance(value, Volume):
                        self.data['dV/dt'].setdefault(f'{name}.{key}', []).append(value.V)
                    elif isinstance(value, Material):
                        self.data['dm/dt'].setdefault(f'{name}.{key}', []).append(value.m)
                        self.data['dU/dt'].setdefault(f'{name}.{key}', []).append(value.U)
                        self.data['dV/dt'].setdefault(f'{name}.{key}', []).append(value.V)
        # Done
        return

    def update_figure(self):
        """Update the figure with current data."""

        # Plot each data dictionary
        for key in self.data.keys():
            if key in self.ax_dict:
                self.plot_dict(self.data[key], key, self.ax_dict[key])

        # Plot diagram
        if self._update_diagram:
            ax_diagram = self.ax_dict['diagram']
            self.plot_diagram(ax_diagram)
            self._update_diagram = False

        # Create global legend
        if self._update_legend:
            ax_legend = self.ax_dict['legend']
            handles = [
                Line2D([0], [0], color=color, lw=1.5)
                for key, color in self.plot_colors.items()
            ]
            labels = list(self.plot_colors.keys())
            ax_legend.clear()
            ax_legend.legend(handles, labels, fontsize='x-small', frameon=False)
            ax_legend.axis('off')
            self._update_legend = False

        # Finalize plot
        plt.pause(0.1)

        # Done
        return

    def plot_dict(self, data, title, ax):
        """Plot data dictionary on given axes."""
        ax.clear()
        for key, values in data.items():
            color = self.get_plot_color(key)
            ax.plot(values[-self.plot_memory:], label=key, color=color)
        ax.set_title(title)
        ax.set_xlabel('Index')
        ax.set_ylabel('Value')
        return

    def get_plot_color(self, key: str):
        """
        Return a color for the given legend key.

        If the key is new, add it to _legend_colors and recompute colors for
        all keys using equally spaced points on the HSV color wheel, with
        keys sorted alphabetically for deterministic ordering.

        Args:
            key: Legend key string.
        Returns:
            color: (r, g, b) tuple with values in [0, 1].
        """
        # If it's a new key, add and recompute the whole wheel
        if key not in self.plot_colors:
            # Add placeholder so it appears in the key set
            self.plot_colors[key] = (0.0, 0.0, 0.0)

            # Sort keys for deterministic assignment
            keys = sorted(self.plot_colors.keys())
            n = len(keys)
            if n > 0:
                for i, k in enumerate(keys):
                    # Equally spaced hues on [0, 1)
                    h = i / n
                    s = 0.7
                    v = 0.9
                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                    self.plot_colors[k] = (r, g, b)
            
            # Sort plot colors dictionary
            self.plot_colors = dict(sorted(self.plot_colors.items()))

            # Indicate that legend needs update
            self._update_legend = True

        # Get color
        color = self.plot_colors[key]

        # Return output
        return color
    
    def plot_diagram(self, ax):
        """Plot current graph diagram."""
        ax.clear()
        draw_graph(
            self.graph,
            get_style=self.get_diagram_style,
            ax=ax,
        )
        return
    
    def get_diagram_style(self, component: Component) -> dict[str, Any]:
        """Return style dict for given component."""
        if isinstance(component, Vessel):
            # Vessels return default node style
            return {}
        elif isinstance(component, Pipe):
            # Pipes return default edge style
            return {}
        elif isinstance(component, Pump):
            # Pumps are bold edges
            return {'style': 'tapered', 'penwidth': 7.0}
        elif isinstance(component, HeatExchange):
            # Heat exchangers are dotted red edges
            return {'style': 'dotted', 'color': 'red', 'penwidth': 2.0, 'xlabel': "🔥"}
        elif isinstance(component, CondensingEdge):
            # Condensing edges are dashed blue edges
            return {'style': 'dashed', 'color': 'blue', 'penwidth': 2.0, 'xlabel': "💧"}
        elif isinstance(component, BoilingEdge):
            # Boiling edges are dashed red edges
            return {'style': 'dashed', 'color': 'orange', 'penwidth': 2.0, 'xlabel': "♨️"}
        elif isinstance(component, TurbineEdge):
            # Turbine edges are bold dashed gray edges
            return {
                'style': 'tapered', 
                'color': 'gray', 
                'penwidth': 3, 
                'dir': 'both',
                'arrowhead': 'normal', 
                'arrowtail': 'none', 
                'xlabel': "⚙️",
            }
        else:
            # Other components use default style
            return {}

    
