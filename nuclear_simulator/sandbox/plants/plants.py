
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.subsystems.reactors import Reactor
from nuclear_simulator.sandbox.plants.subsystems.pressurizers import PressurizerSystem
from nuclear_simulator.sandbox.plants.subsystems.steam_generators import SteamGenerator
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

    def __init__(self, **data) -> None:
        super().__init__(**data)

        # --- Add nodes and subgraphs ---
        self.reactor: Reactor = self.add_graph(
            Reactor, 
            name="Reactor"
        )
        self.sg: SteamGenerator = self.add_graph(
            SteamGenerator, 
            name="SG",
            use_water_source=True,
            use_steam_sink=True,
        )
        self.pressurizer: PressurizerSystem = self.add_graph(
            PressurizerSystem,
            name="Pressurizer"
        )

        # --- Primary loop plumbing ---

        # SG:Primary:ColdLeg -> Pressurizer
        self.add_edge(
            edge_type=LiquidPump,
            node_source=self.sg.primary_out,
            node_target=self.pressurizer.primary_in,
            name="Pump:Primary:SG->Pressurizer",
            m_dot=self.sg.primary_m_dot,
        )
        # Pressurizer -> ReactorCoolant
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.pressurizer.primary_out,
            node_target=self.reactor.primary_in,
            name="Pipe:Primary:Pressurizer->Reactor",
            m_dot=self.sg.primary_m_dot,
        )
        # ReactorCoolant -> SG:Primary:HotLeg
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.reactor.coolant,
            node_target=self.sg.primary_in,
            name="Pipe:Primary:Reactor->SG",
            m_dot=self.sg.primary_m_dot,
        )

        # Done
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
    dashboard = Dashboard(plant)

    # Simulate for a while
    dt = .001
    n_steps = 100_000
    dashboard.plot_every = n_steps // 1000
    for i in range(n_steps):
        plant.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

