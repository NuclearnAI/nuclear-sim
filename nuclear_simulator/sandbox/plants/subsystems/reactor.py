
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph
from nuclear_simulator.sandbox.plants.materials import UraniumDioxide
from nuclear_simulator.sandbox.plants.vessels.reactor import ReactorFuel


# Define Reactor
class Reactor(Graph):
    """
    Simplified reactor core node with Fuel.
    Attributes:
        power_output_setpoint:  [W] Target reactor thermal power
    Nodes:
        fuel: ReactorFuel node  [-] Reactor fuel
    Edges:
        None
    """
    power_output_setpoint: float = 20e6


    def __init__(self, **data) -> None:
        """Initialize reactor graph."""

        # Call super init
        super().__init__(**data)

        # Build graph
        self.core: ReactorFuel = self.add_node(
            ReactorFuel,
            name="Fuel",
            specific_power_gain=ReactorFuel.calibrate_specific_power_gain(
                target_power_output=self.power_output_setpoint
            ),
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
    Test reactor node functionality.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard

    # Create reactor
    reactor = Reactor()

    # Initialize dashboard
    dashboard = Dashboard(reactor)

    # Simulate for a while
    dt = 1
    n_steps = 1000
    for i in range(n_steps):
        reactor.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

