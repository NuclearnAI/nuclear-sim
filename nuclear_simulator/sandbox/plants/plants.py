
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
    power_output_setpoint: float = 20e6


    def __init__(self, **data) -> None:

        # Call super init
        super().__init__(**data)

        # Add subgraphs
        self.reactor: Reactor = self.add_graph(
            Reactor, 
            name="Reactor",
            power_output_setpoint=self.power_output_setpoint,
        )
        self.primary_loop: PrimaryLoop = self.add_graph(
            PrimaryLoop, 
            name="PrimaryLoop",
            power_output_setpoint=self.power_output_setpoint,
        )
        self.secondary_loop: SecondaryLoop = self.add_graph(
            SecondaryLoop, 
            name="SecondaryLoop",
            power_output_setpoint=self.power_output_setpoint,
        )

        # Calibrate conductance from power output
        dT_reactor_primary = (
            self.reactor.core.contents.T - self.primary_loop.core.contents.T
        )
        conductance_reactor_primary = (
            self.power_output_setpoint / dT_reactor_primary
        )
        dT_primary_secondary = (
            self.primary_loop.sg.contents.T - self.secondary_loop.sg.liquid.T
        )
        conductance_primary_secondary = (
            self.power_output_setpoint / dT_primary_secondary
        )

        # Add edges
        self.add_edge(
            edge_type=HeatExchange,
            node_source=self.reactor.core,
            node_target=self.primary_loop.core,
            name="HeatExchange:[Reactor->Primary]",
            conductance=conductance_reactor_primary,
        )
        self.add_edge(
            edge_type=HeatExchange,
            node_source=self.primary_loop.sg,
            node_target=self.secondary_loop.sg,
            name="HeatExchange:[Primary->Secondary]",
            alias_target={"contents": "liquid"},
            conductance=conductance_primary_secondary,
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
    dashboard = Dashboard(plant)

    # Simulate for a while
    dt = 1
    n_steps = 100_000
    for i in range(n_steps):
        plant.update(dt)
        dashboard.step()
        print(plant.secondary_loop.turbine.power_output)

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

