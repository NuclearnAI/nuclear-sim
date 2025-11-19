
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
    boron_ppm: float            = 1000.0            # typical BOC-ish value
    boron_alpha: float          = -7e-5             # ~ -7 pcm/ppm
    fission_power_gain: float   = 3.0e9             # ~3 GWth at rho=0
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
    

# Define Coolant node
class ReactorCoolant(PressurizedLiquidVessel):
    """
    Simplified coolant node for reactor core.
    """
    P: float = PWRPrimaryWater.P0
    contents: PWRPrimaryWater = Field(
        default_factory=lambda: (
            PWRPrimaryWater.from_temperature(m=10_000.0, T=PWRPrimaryWater.T0)
        )
    )


# Define Reactor
class Reactor(Graph):
    """
    Simplified reactor core node with Fuel and Coolant vessel.
    """

    # Set attributes
    conductance_fuel_coolant: float = 5.0e7  # typical order 1e7-1e8 W/K

    def __init__(self, **data) -> None:
        """Initialize reactor graph."""

        # Call super init
        super().__init__(**data)

        # Build graph
        self.fuel     = self.add_node(ReactorFuel, name=f"{self.name}:Fuel")
        self.coolant  = self.add_node(ReactorCoolant, name=f"{self.name}:Coolant")
        self.coupling = self.add_edge(
            edge_type=HeatExchange,
            node_source=self.fuel, 
            node_target=self.coolant,
            name=f"HeatExchange:{self.name}:Fuel->Coolant",
            conductance=self.conductance_fuel_coolant,
        )
        
        # Done
        return
    
    @property
    def primary_in(self) -> ReactorCoolant:
        """Convenience accessor for primary inlet (coolant)."""
        return self.coolant
    
    @property
    def primary_out(self) -> ReactorCoolant:
        """Convenience accessor for primary outlet (coolant)."""
        return self.coolant


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

