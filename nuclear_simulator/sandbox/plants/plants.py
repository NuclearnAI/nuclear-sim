
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.edges.heat import HeatExchange
from nuclear_simulator.sandbox.plants.subsystems.reactor import Reactor
from nuclear_simulator.sandbox.plants.subsystems.primary_loop import PrimaryLoop
from nuclear_simulator.sandbox.plants.subsystems.secondary_loop import SecondaryLoop
from nuclear_simulator.sandbox.plants.edges import (
    GasPipe, 
    GasPump,
    LiquidPipe, 
    LiquidPump, 
)

# Define plant
class Plant(Graph):
    """
    Nuclear power plant graph.
    """
    conductance_reactor_primary: float = 1e5  # W/K
    conductance_primary_secondary: float = 1e5  # W/K

    def __init__(self, **data) -> None:

        # Call super init
        super().__init__(**data)

        # Get name prefix
        prefix = '' if (self.name is None) else f"{self.name}:"

        # Add nodes and subgraphs
        self.reactor: Reactor = self.add_graph(
            Reactor, 
            name=f"{prefix}Reactor"
        )
        self.primary_loop: PrimaryLoop = self.add_graph(
            PrimaryLoop, 
            name=f"{prefix}PrimaryLoop"
        )
        self.secondary_loop: SecondaryLoop = self.add_graph(
            SecondaryLoop, 
            name=f"{prefix}SecondaryLoop"
        )

        # Add edges
        self.add_edge(
            edge_type=HeatExchange,
            node_source=self.reactor.core,
            node_target=self.primary_loop.core,
            name=f"HeatExchange:{prefix}[ReactorCore->PrimaryLoop]",
            conductance=self.conductance_reactor_primary,
        )
        self.add_edge(
            edge_type=HeatExchange,
            node_source=self.primary_loop.sg,
            node_target=self.secondary_loop.sg_water,
            name=f"HeatExchange:{prefix}[PrimarySG->SecondarySG]",
            conductance=self.conductance_primary_secondary,
        )

        # Done
        return
    
    def update(self, dt: float) -> None:
        """Update the graph by one time step.
        Args:
            dt:  [s] Time step for the update.
        """
        try:
            super().update(dt)
        except Exception as e:
            raise RuntimeError(f"Error updating {self.__class__.__name__}: {e}") from e
        return


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard

    # Create plant
    plant = Plant()

    # Initialize dashboard
    dashboard = Dashboard(plant.secondary_loop)

    # Simulate for a while
    dt = 1
    n_steps = 100_000
    for i in range(n_steps):
        plant.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

