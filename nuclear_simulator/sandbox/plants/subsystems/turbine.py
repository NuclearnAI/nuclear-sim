
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.edges import LiquidPipe, LiquidPump
from nuclear_simulator.sandbox.plants.vessels import PressurizedGasVessel
from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater




# Define Turbine
class Turbine(Graph):
    """
    
    """

    # Set attributes
    m_dot: float = 100.0

    def __init__(self, **data) -> None:
        """Initialize primary loop graph."""

        # Call super init
        super().__init__(**data)


        
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
    Test subsystem.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard

    # Create graph
    turbine = Turbine()

    # Initialize dashboard
    dashboard = Dashboard(turbine)

    # Simulate for a while
    dt = 1
    n_steps = 1000
    for i in range(n_steps):
        turbine.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

