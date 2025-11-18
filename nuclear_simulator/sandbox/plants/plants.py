
# Import libraries
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.reactors import Reactor
from nuclear_simulator.sandbox.plants.transfer.pipes import LiquidPipe, GasPipe
from nuclear_simulator.sandbox.plants.transfer.pumps import LiquidPump
from nuclear_simulator.sandbox.plants.steam_generators import SteamGenerator


# Define plant
class Plant(Graph):
    """
    Nuclear power plant graph.
    """

    def __init__(self, **data) -> None:
        super().__init__(**data)

        # --- Add nodes and subgraphs ---
        reactor: Reactor = self.add_graph(
            Reactor, 
            name="Reactor"
        )
        sg: SteamGenerator = self.add_graph(
            SteamGenerator, 
            name="SteamGenerator",
            use_water_source=True,
            use_steam_sink=True,
        )

        # --- Primary loop plumbing ---

        # SG:Primary:ColdLeg -> ReactorCoolant (with pump)
        self.add_edge(
            edge_type=LiquidPump,
            node_source=sg.primary_out,
            node_target=reactor.coolant,
            name="Primary:Pump:SG:ColdLeg->Reactor",
            m_dot=sg.primary_m_dot,
        )
        # ReactorCoolant -> SG:Primary:HotLeg
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=reactor.coolant,
            node_target=sg.primary_in,
            name="Primary:Pipe:Reactor->SG:HotLeg",
            m_dot=sg.primary_m_dot,
        )

        # Done
        return

    # ------------- Convenience accessors -------------

    @property
    def reactor(self) -> Reactor:
        return self.get_component_from_name("Reactor")

    @property
    def steam_generator(self) -> SteamGenerator:
        return self.get_component_from_name("SteamGenerator")


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.graphs.diagram import draw_graph
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard

    # Create plant
    plant = Plant()

    # Draw graph
    fig, ax = draw_graph(plant)

    # Initialize dashboard
    dashboard = Dashboard(plant.steam_generator)

    # Simulate for a while
    dt = .001
    n_steps = 100000
    dashboard.plot_every = n_steps // 1000
    for i in range(n_steps):
        plant.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

