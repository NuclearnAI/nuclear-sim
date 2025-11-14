
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.vessels import LiquidVessel
from nuclear_simulator.sandbox.plants.thermo.heat import HeatExchange
from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater, UraniumDioxide



# Define Fuel node
class ReactorFuel(Node):
    """
    Simplified fuel node for reactor core.
    Attributes:
        boron_ppm:            [ppm]   Boron concentration
        boron_alpha:          [1/ppm] Boron reactivity effect per ppm
        fission_power_gain:   [W]     Gain factor mapping reactivity to power
        control_rod_position: [0-1]   Inserted fraction
        fuel:                 [-]     Fuel material
    """

    # Set attributes
    boron_ppm: float            = 1000.0            # typical BOC-ish value
    boron_alpha: float          = -7e-5             # ~ -7 pcm/ppm
    fission_power_gain: float   = 3.0e9             # ~3 GWth at rho=0
    control_rod_position: float = 0.10
    fuel: UraniumDioxide = Field(
        default_factory=lambda: (
            UraniumDioxide.from_temperature(m=1000.0, T=600.0)
        )
    )

    # Add validation to update
    def update(self, dt):
        """
        Update method with validation.
        Args:
            dt: Time step size (s).
        """
        super().update(dt)
        try:
            self.fuel.validate()
        except Exception as e:
            raise ValueError("Fuel validation failed during update.") from e
        return

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
        self.fuel.U += power_fission * dt

        # Done
        return
    

# Define Coolant node
class ReactorCoolant(LiquidVessel):
    """
    Simplified coolant node for reactor core.
    """
    P: float = 15.5e6
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda: (
            PWRPrimaryWater.from_temperature(m=10_000.0, T=550.0)
        )
    )


# Define Reactor Fuel-Coolant Heat Exchange
class FuelCoolantHeatExchange(HeatExchange):
    """
    Heat exchange between reactor fuel and coolant.
    """
    conductance: float = 5.0e7  # typical order 1e7-1e8 W/K


# Define Reactor
class Reactor(Graph):
    """
    Simplified reactor core node with Fuel and Coolant vessel.

    """

    def __init__(self, **data) -> None:
        """Initialize reactor graph."""
        # Call super init
        super().__init__(**data)
        # Build graph
        fuel     = self.add_node(ReactorFuel, name="Reactor:Fuel")
        coolant  = self.add_node(ReactorCoolant, name="Reactor:Coolant")
        coupling = self.add_edge(
            edge_type=FuelCoolantHeatExchange,
            node_source=fuel, 
            node_target=coolant, 
            alias_source={"material": "fuel"},
            alias_target={"material": "liquid"},
            name="Reactor:HeatExchange:Fuel->Coolant"
        )
        # Done
        return
    
    @property
    def fuel(self) -> ReactorFuel:
        """Get reactor fuel node."""
        return self.get_component_from_name("Reactor:Fuel")
    
    @property
    def coolant(self) -> ReactorCoolant:
        """Get reactor coolant node."""
        return self.get_component_from_name("Reactor:Coolant")
    
    @property
    def coupling(self) -> FuelCoolantHeatExchange:
        """Get reactor fuel-coolant coupling edge."""
        return self.get_component_from_name("Reactor:HeatExchange:Fuel->Coolant")


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

