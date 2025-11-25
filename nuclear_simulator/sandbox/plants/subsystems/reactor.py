
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
        control_rod_position: [0-1]   Inserted fraction
        boron_ppm:            [ppm]   Boron concentration
        boron_alpha:          [1/ppm] Boron reactivity effect per ppm
        specific_power_gain:  [W/kg]  Gain factor mapping reactivity to power
    """
    contents: UraniumDioxide = Field(
        default_factory=lambda: (
            UraniumDioxide.from_temperature(m=30_000.0, T=UraniumDioxide.T0)
        )
    )
    control_rod_position: float = 0.1
    boron_ppm: float            = 1000.0
    boron_alpha: float          = 7e-5
    specific_power_gain: float  = 1000

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
        reactivity = max(0.0, reactivity)

        # Add fission heat to fuel based on reactivity
        power_fission = reactivity * self.specific_power_gain * self.contents.m

        # Update fuel internal energy
        self.contents.U += power_fission * dt

        # Done
        return
    
    @classmethod
    def calibrate_specific_power_gain(
            cls,
            target_power_output: float,
            contents: UraniumDioxide | None = None,
            control_rod_position: float | None = None,
            boron_ppm: float | None = None,
            boron_alpha: float | None = None,
        ) -> float:
        """
        Calibrate the specific power gain to achieve a target power density.
        Args:
            target_power_output:  [W]     Desired power output
            contents:             [-]      Fuel material
            control_rod_position: [0-1]   Inserted fraction
            boron_ppm:            [ppm]   Boron concentration
            boron_alpha:          [1/ppm] Boron reactivity effect per ppm
        Returns:
            specific_power_gain:  [W/kg] Calibrated specific power gain
        """

        # Get defaults
        if contents is None:
            contents = cls.model_fields["contents"].default_factory()
        if control_rod_position is None:
            control_rod_position = cls.model_fields["control_rod_position"].default
        if boron_ppm is None:
            boron_ppm = cls.model_fields["boron_ppm"].default
        if boron_alpha is None:
            boron_alpha = cls.model_fields["boron_alpha"].default

        # Compute reactivity
        reactivity = (1.0 - control_rod_position) - (boron_ppm * boron_alpha)

        # Avoid division by zero
        if reactivity <= 0.0:
            raise ValueError("Reactivity is zero or negative; cannot calibrate power gain.")

        # Calculate specific power gain
        specific_power_gain = target_power_output / (reactivity * contents.m)

        # Return result
        return specific_power_gain


# Define Reactor
class Reactor(Graph):
    """
    Simplified reactor core node with Fuel.
    Attributes:
        baseline_power_output:  [W] Target reactor thermal power
    Nodes:
        fuel: ReactorFuel node  [-] Reactor fuel
    Edges:
        None
    """
    baseline_power_output: float = 20e6


    def __init__(self, **data) -> None:
        """Initialize reactor graph."""

        # Call super init
        super().__init__(**data)

        # Get constants
        specific_power_gain = ReactorFuel.calibrate_specific_power_gain(
            target_power_output=self.baseline_power_output
        )

        # Build graph
        self.core = self.add_node(
            ReactorFuel,
            name="Fuel",
            specific_power_gain=specific_power_gain,
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

