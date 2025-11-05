
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.containers import LiquidVessel
from nuclear_simulator.sandbox.plants.thermo import ThermalCoupling
from nuclear_simulator.sandbox.materials.nuclear import PWRPrimaryWater, UraniumDioxide



# Define Fuel node
class ReactorFuel(Node):
    """
    Simplified fuel node for reactor core.
    Attributes:
        boron_ppm:            [ppm]   Boron concentration
        boron_alpha:          [1/ppm] Boron reactivity effect per ppm
        fission_power_gain:   [W]     Gain at rho = 1
        control_rod_position: [0-1]   Inserted fraction
        fuel:                 [-]     Fuel material
    """

    # Set attributes
    boron_ppm: float            = 500.0
    boron_alpha: float          = 1e-4
    fission_power_gain: float   = 1e9
    control_rod_position: float = 0.10
    fuel: UraniumDioxide = Field(
        default_factory=lambda:(
            UraniumDioxide.from_temperature(
                m=80_000.0,
                T=600.0,
            )
        )
    )

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
    Attributes:
        P0:       [Pa]    Baseline pressure for pressure calculation
        dPdV:     [Pa/m^3] Stiffness-like coefficient (dP/dV of "tank" cushion)
        liquid:   [-]     Liquid stored in the vessel
    """
    P0: float = 15.5e6
    dPdV: float = 1.0e9
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda:(
            PWRPrimaryWater.from_temperature(
                m=10_000.0,
                T=550.0,    
            )
        )
    )


# Define Reactor Fuel-Coolant Thermal Coupling
class FuelCoolantThermalCoupling(ThermalCoupling):
    """
    Thermal coupling between reactor fuel and coolant.
    Attributes:
        tag:               [str] Tag of the material to exchange heat between
        conductance:       [W/K] Fuel-coolant conductance
    """
    tag: str = "material"
    conductance: float = 3e6


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
        fuel     = self.add_node(ReactorFuel, name="ReactorFuel")
        coolant  = self.add_node(ReactorCoolant, name="ReactorCoolant")
        coupling = self.add_edge(
            edge_type=FuelCoolantThermalCoupling,
            node_source=fuel, 
            node_target=coolant, 
            alias_source={"material": "fuel"},
            alias_target={"material": "liquid"},
            name="HeatExchange:Fuel-Coolant"
        )
        # Done
        return
    
    @property
    def fuel(self) -> ReactorFuel:
        """Get reactor fuel node."""
        return self.get_component_from_name("ReactorFuel")
    
    @property
    def coolant(self) -> ReactorCoolant:
        """Get reactor coolant node."""
        return self.get_component_from_name("ReactorCoolant")
    
    @property
    def coupling(self) -> FuelCoolantThermalCoupling:
        """Get reactor fuel-coolant coupling edge."""
        return self.get_component_from_name("HeatExchange:Fuel-Coolant")


# Test
def test_file():
    """
    Test reactor node functionality.
    """
    # Create reactor
    reactor = Reactor()
    # Update reactor
    dt = 1.0  # [s]
    reactor.update(dt)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

