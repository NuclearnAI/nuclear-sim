
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.plants.vessels import Vessel
from nuclear_simulator.sandbox.plants.materials import UraniumDioxide


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


