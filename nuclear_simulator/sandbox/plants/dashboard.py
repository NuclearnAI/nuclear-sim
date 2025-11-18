
# Import libraries
import colorsys
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from nuclear_simulator.sandbox.graphs import Graph
from nuclear_simulator.sandbox.materials import Material, MaterialExchange


class Dashboard:
    """Simple live dashboard for monitoring data."""

    # Set material tags
    MATERIAL_TAGS = ('energy', 'gas', 'liquid', 'solid', 'fuel', 'material')

    def __init__(self, graph: Graph, plot_every: int = 100):
        """
        Initialize dashboard with monitor.
        Args:
            graph:      Graph that the dashboard will monitor.
            plot_every: Number of steps between plot updates.
        """

        # Set attributes
        self.graph = graph
        self.step_count = 0
        self.plot_every = plot_every

        # Initialize data storage
        self.data = {
            'T': {}, 
            'P': {}, 
            'm': {}, 
            'U': {}, 
            'V': {},
            'm_dot': {}, 
            'U_dot': {}, 
            'V_dot': {},
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
            'm':     self.ax[0, 0],
            'U':     self.ax[0, 1],
            'V':     self.ax[0, 2],
            'm_dot': self.ax[1, 0],
            'U_dot': self.ax[1, 1],
            'V_dot': self.ax[1, 2],
            'T':     self.ax[0, 3],
            'P':     self.ax[1, 3],
        }
        self.plot_colors: dict[str, tuple] = {}
        self._update_legend: bool = True

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
        for node in self.graph.get_nodes().values():

            # Get name
            name = node.name or node.id

            # Check for pressure
            P = node.state.get('P', None)

            # Loop over state
            for key, value in node.state.items():

                # Skip non-material states
                if not isinstance(value, Material):
                    continue

                # Log material properties
                self.data['T'].setdefault(f'{name}.{key}', []).append(value.T)

                # Ignore mass, energy, volume for environment components
                if not name.lower().startswith('env:'):
                    self.data['m'].setdefault(f'{name}.{key}', []).append(value.m)
                    self.data['U'].setdefault(f'{name}.{key}', []).append(value.U)
                    self.data['V'].setdefault(f'{name}.{key}', []).append(value.V)

                # Add pressure if available
                if P is not None:
                    self.data['P'].setdefault(f'{name}.{key}', []).append(P)

        # Loop over edges
        for edge in self.graph.get_edges().values():

            # Get name
            name = edge.name or edge.id

            # Loop over material flows and log
            for key, value in edge.flows.items():
                if isinstance(value, MaterialExchange):
                    # Only log energy flow for Energy types
                    self.data['U_dot'].setdefault(f'{name}.{key}', []).append(value.U)
                elif isinstance(value, Material):
                    self.data['m_dot'].setdefault(f'{name}.{key}', []).append(value.m)
                    self.data['U_dot'].setdefault(f'{name}.{key}', []).append(value.U)
                    self.data['V_dot'].setdefault(f'{name}.{key}', []).append(value.V)

        # Done
        return

    def update_figure(self):
        """Update the figure with current data."""

        # Plot each data dictionary
        for key in self.data.keys():
            if key in self.ax_dict:
                self.plot_dict(self.data[key], key, self.ax_dict[key])

        # Create global legend
        if self._update_legend:
            handles = [
                Line2D([0], [0], color=color, lw=1.5)
                for key, color in self.plot_colors.items()
            ]
            labels = list(self.plot_colors.keys())
            self.fig.subplots_adjust(right=0.8)
            self.fig.legend(
                handles, 
                labels, 
                loc='upper left', 
                bbox_to_anchor=(0.82, 1.0),
                fontsize='x-small', 
                frameon=False
            )
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
            ax.plot(values, label=key, color=color)
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

    
