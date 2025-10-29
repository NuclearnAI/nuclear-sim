
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.plants.physics import (
    calc_temperature_from_energy, calc_energy_from_temperature
)


# Define Reactor node
class Reactor(Node):
    """
    Simplified reactor core model with fuel and coolant thermal masses.
    """

    # Fuel parameters
    fuel_T: float = 600.0              # [K]         Fuel temperature
    fuel_U: float = 0.0                # [J]         Fuel internal energy (computed in __init__)
    fuel_m: float = 80_000.0           # [kg]        Fuel mass in reactor
    fuel_cp: float = 300.0             # [J/(kg·K)]  Effective solid cp (fuel + structure)
    # Coolant parameters
    coolant_T: float = 550.0           # [K]         Coolant temperature
    coolant_U: float = 0.0             # [J]         Coolant internal energy (computed in __init__)
    coolant_m: float = 10_000.0        # [kg]        Coolant mass in reactor
    coolant_cp: float = 4_200.0        # [J/(kg·K)]  Effective solid cp (water-ish)
    # Control parameters
    boron_ppm: float = 500.0           # [ppm]       Boron concentration in ppm
    control_rod_position: float = 0.1  # [unitless]  Inserted fraction (0-1)
    # Constants
    alpha_boron: float = 1e-4          # [1/ppm]     Damping effect of boron
    G_fuel_coolant: float = 3e6        # [W/K]       Fuel–coolant heat transfer coefficient
    fission_power_gain: float = 1e9    # [W]         Power output at ρ = 1.0


    def __init__(self, **kwargs):
        """Initialize reactor state."""

        # Initialize parent
        super().__init__(**kwargs)

        # Initialize energy based on temperatures
        self.fuel_U = calc_energy_from_temperature(
            T=self.fuel_T, 
            m=self.fuel_m, 
            cp=self.fuel_cp
        )
        self.coolant_U = calc_energy_from_temperature(
            T=self.coolant_T, 
            m=self.coolant_m, 
            cp=self.coolant_cp
        )

        # Done
        return

    def update_from_signals(self, dt: float) -> None:
        """
        Update reactor parameters based on incoming control signals.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates control parameters in place.
        """
        
        # Process incoming signals
        for signal in self.signals_incoming:

            # Get payload
            payload = signal.payload

            # Check boron
            if "boron_ppm" in payload:
                self.boron_ppm = payload["boron_ppm"]
                if self.boron_ppm < 0.0:
                    raise ValueError("Boron ppm cannot be negative")
                
            # Check control rod position
            if "control_rod_position" in payload:
                self.control_rod_position = payload["control_rod_position"]
                if not (0.0 <= self.control_rod_position <= 1.0):
                    raise ValueError("Control rod position must be between 0 and 1")

        # Done
        return

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
        control_rod_position = self.control_rod_position
        alpha_boron = self.alpha_boron
        G_fuel_coolant = self.G_fuel_coolant
        fission_power_gain = self.fission_power_gain

        # Update fuel energy based on controls
        reactivity    = (1.0 - control_rod_position) - (boron_ppm * alpha_boron) # [unitless]
        power_fission = max(0.0, reactivity * fission_power_gain)  # [W]/[J/s]
        dU_fuel       = power_fission * dt  # [J]
        fuel_U       += dU_fuel  # [J]
        
        # Update coolant energy based on heat transfer from fuel
        fuel_T     = calc_temperature_from_energy(fuel_U, fuel_m, fuel_cp)  # [K]
        coolant_T  = calc_temperature_from_energy(coolant_U, coolant_m, coolant_cp)  # [K]
        dU         = G_fuel_coolant * (fuel_T - coolant_T) * dt  # [J]
        fuel_U    -= dU  # [J]
        coolant_U += dU  # [J]
        fuel_T     = calc_temperature_from_energy(fuel_U, fuel_m, fuel_cp)  # [K]
        coolant_T  = calc_temperature_from_energy(coolant_U, coolant_m, coolant_cp)  # [K]

        # Update state variables
        self.fuel_U = fuel_U
        self.fuel_T = fuel_T
        self.coolant_U = coolant_U
        self.coolant_T = coolant_T

        # Done
        return
