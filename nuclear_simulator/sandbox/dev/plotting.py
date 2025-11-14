
# Import libraries
import matplotlib.pyplot as plt


def plot_dict(
        data: dict[str, list[float]], 
        title: str | None = None,
        fig=None,
        ax=None,
    ):
    """
    Plots each key in the dictionary as a labeled line.

    Args:
        data:  Dictionary mapping str to list[float].
        title: Optional title for the plot.
        fig:   Optional matplotlib Figure. If None, creates a new one.
        ax:    Optional matplotlib Axes. If None, creates a new one.

    Returns:
        fig, ax: The matplotlib Figure and Axes.
    """

    # Create figure and axes if not provided
    if ax is None and fig is None:
        fig, ax = plt.subplots(1, 1)
    elif ax is None:
        fig.clf()
        ax = fig.add_subplot(1, 1, 1)
    elif fig is None:
        fig = ax.figure
        ax.clear()
    plt.ion()
    plt.show()

    # Plot each entry
    for key, values in data.items():
        ax.plot(values, label=key)

    # Finalize plot
    if title is not None:
        ax.set_title(title)
    ax.legend()
    ax.set_xlabel('Index')
    ax.set_ylabel('Value')
    fig.tight_layout()
    plt.pause(0.1)

    # Return figure and axes
    return fig, ax

