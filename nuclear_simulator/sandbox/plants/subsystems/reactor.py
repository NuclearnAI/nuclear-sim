
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.vessels import Vessel, PressurizedLiquidVessel
from nuclear_simulator.sandbox.plants.edges.heat import HeatExchange
from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater, UraniumDioxide


# Define Fuel node
class ReactorFuel(Vessel):
    """
    Simplified fuel node for reactor core.
    Attributes:
        contents:             [-]     Fuel material
        boron_ppm:            [ppm]   Boron concentration
        boron_alpha:          [1/ppm] Boron reactivity effect per ppm
        fission_power_gain:   [W]     Gain factor mapping reactivity to power
        control_rod_position: [0-1]   Inserted fraction
    """
    contents: UraniumDioxide = Field(
        default_factory=lambda: (
            UraniumDioxide.from_temperature(m=100.0, T=UraniumDioxide.T0)
        )
    )
    boron_ppm: float            = 1000.0
    boron_alpha: float          = -7e-5
    fission_power_gain: float   = 3.0e5
    control_rod_position: float = 0.1

    # Update method
    def update_from_state(self, dt: float) -> None:
        """
        Advance the fuel node by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the fuel internal energy `fuel.U`.
        """

        # Compute reactivity based on control rods and boron concentration 
        reactivity = (1.0 - self.control_rod_position) - (self.boron_ppm * self.boron_alpha)

        # Add fission heat to fuel based on reactivity
        power_fission = max(0.0, reactivity * self.fission_power_gain)

        # Update fuel internal energy
        self.contents.U += power_fission * dt

        # Done
        return


# Define Reactor
class Reactor(Graph):
    """
    Simplified reactor core node with Fuel.
    Attributes:
        None
    Nodes:
        fuel: ReactorFuel node
    Edges:
        None
    """

    def __init__(self, **data) -> None:
        """Initialize reactor graph."""

        # Call super init
        super().__init__(**data)

        # Get name prefix
        prefix = '' if (self.name is None) else f"{self.name}:"

        # Build graph
        self.core = self.add_node(ReactorFuel, name=f"{prefix}Fuel")
        
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
    dt = .001
    n_steps = 10000
    for i in range(n_steps):
        reactor.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

