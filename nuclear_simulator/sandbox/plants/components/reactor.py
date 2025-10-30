
# Import libraries
from nuclear_simulator.sandbox.plants.thermograph import ThermoNode
from nuclear_simulator.sandbox.plants.physics import (
    calc_temperature_from_energy, calc_energy_from_temperature
)


# Define Reactor node
class Reactor(ThermoNode):
    """
    Simplified reactor core model with fuel and coolant thermal masses.
    """

    # Coolant parameters
    coolant_P     = 15.5e6        # [Pa]        Operating pressure
    coolant_T     = 550.0         # [K]         Coolant temperature
    coolant_m     = 10_000.0      # [kg]        Coolant mass in reactor
    coolant_U     = None          # [J]         Coolant internal energy (computed in __init__)
    coolant_cp    = 4_200.0       # [J/(kg*K)]  Effective solid cp (water-ish)
    coolant_K     = 2.2e9         # [Pa]        Bulk modulus of coolant
    coolant_alpha = 5e-4          # [1/K]       Thermal expansion coefficient
    # Fuel parameters
    fuel_T  = 600.0               # [K]         Fuel temperature
    fuel_m  = 80_000.0            # [kg]        Fuel mass in reactor
    fuel_U  = None                # [J]         Fuel internal energy (computed in __init__)
    fuel_cp = 300.0               # [J/(kg*K)]  Effective solid cp (fuel + structure)
    # Control parameters
    boron_ppm            = 500.0  # [ppm]       Boron concentration in ppm
    control_rod_position = 0.1    # [-]  Inserted fraction (0-1)
    # Constants
    alpha_boron        = 1e-4     # [1/ppm]     Damping effect of boron
    G_fuel_coolant     = 3e6      # [W/K]       Fuel–coolant heat transfer coefficient
    fission_power_gain = 1e9      # [W]         Power output at ρ = 1.0

    def update_from_state(self, dt: float) -> None:
        """
        Update reactor state based on internal parameters.
        Args:
            dt: [s] Time step for the update.
        Modifies:
            Updates the reactor's state variables in place.
        """
        
        # Extract parameters
        fuel_U = self.fuel_U
        fuel_m = self.fuel_m
        fuel_cp = self.fuel_cp
        coolant_U = self.coolant_U
        coolant_m = self.coolant_m
        coolant_cp = self.coolant_cp
        boron_ppm = self.boron_ppm
        alpha_boron = self.alpha_boron
        G_fuel_coolant = self.G_fuel_coolant
        fission_power_gain = self.fission_power_gain
        control_rod_position = self.control_rod_position

        # Update fuel energy based on controls
        reactivity    = (1.0 - control_rod_position) - (boron_ppm * alpha_boron)
        power_fission = max(0.0, reactivity * fission_power_gain)
        dU_fuel       = power_fission * dt
        fuel_U       += dU_fuel
        
        # Update coolant energy based on heat transfer from fuel
        fuel_T     = calc_temperature_from_energy(fuel_U, fuel_m, fuel_cp)
        coolant_T  = calc_temperature_from_energy(coolant_U, coolant_m, coolant_cp)
        dU         = G_fuel_coolant * (fuel_T - coolant_T) * dt
        fuel_U    -= dU
        coolant_U += dU
        fuel_T     = calc_temperature_from_energy(fuel_U, fuel_m, fuel_cp)
        coolant_T  = calc_temperature_from_energy(coolant_U, coolant_m, coolant_cp)

        # Update state variables
        self.fuel_U = fuel_U
        self.fuel_T = fuel_T
        self.coolant_U = coolant_U
        self.coolant_T = coolant_T

        # Done
        return
