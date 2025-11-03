
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.materials.nuclear import Coolant, Fuel
from nuclear_simulator.sandbox.materials.vessels import LiquidVessel
from nuclear_simulator.sandbox.physics import (
    calc_temperature_from_energy, calc_energy_from_temperature
)


# Define Fuel node
class ReactorFuel(Node):
    """
    Simplified fuel node for reactor core.
    """

    # Material
    fuel: Fuel = Field(
        default_factory=lambda:(
            Fuel.from_temperature(
                m=80_000.0,
                T=600.0,
            )
        )
    )

    # Instance attributes
    boron_ppm: float            = 500.0   # [ppm]   Boron concentration
    boron_alpha: float          = 1e-4    # [1/ppm] Boron worth
    fission_power_gain: float   = 1e9     # [W]     Gain at ρ = 1
    control_rod_position: float = 0.10    # [0-1]   Inserted fraction

    def update_from_state(self, dt: float) -> None:
        """
        Advance the fuel node by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the fuel internal energy `fuel.U`.
        """

        # Add fission heat to fuel based on reactivity
        reactivity = (1.0 - self.control_rod_position) - (self.boron_ppm * self.boron_alpha)
        power_fission = max(0.0, reactivity * self.fission_power_gain)
        self.fuel.U += power_fission * dt

        # Done
        return
    

# Define Coolant node
class ReactorCoolant(Node):
    """
    Simplified coolant node for reactor core.
    """

    # Material
    coolant: LiquidVessel = Field(
        default_factory=lambda:(
            LiquidVessel.from_fluid(
                fluid=Coolant.from_temperature(
                    m=10_000.0,
                    T=550.0,
                ),
                P0=15.5e6,
                dPdV=1.0e9,
            )
        )
    )


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
            fuel, 
            coolant, 
            name="Fuel-Coolant Heat Exchange"
        )
        # Done
        return


# # Define Reactor node
# class Reactor(Node):
#     """
#     Simplified reactor core node with Fuel and Coolant vessel.
#     """

#     # Materials
#     coolant: Coolant = Field(
#         default_factory=lambda:(
#             Coolant.from_temperature(
#                 m=10_000.0,
#                 T=550.0,
#             )
#         )
#     )
#     fuel: Fuel = Field(
#         default_factory=lambda:(
#             Fuel.from_temperature(
#                 m=80_000.0,
#                 T=600.0,
#             )
#         )
#     )

#     # Coolant pressure parameters
#     coolant_P: float = 15.5e6        # [Pa]     Pressure of the coolant.
#     coolant_P0: float | None = None  # [Pa]     Reference pressure at V0
#     coolant_V0: float | None = None  # [m^3]    Volume at which dP/dV = 0; if None, set to initial V
#     coolant_dPdV: float = 1.0e9      # [Pa/m^3] Stiffness-like coefficient (dP/dV of "tank" cushion)

#     # Control parameters
#     boron_ppm: float            = 500.0   # [ppm]
#     control_rod_position: float = 0.10    # [0-1], inserted fraction

#     # Constants
#     alpha_boron: float          = 1e-4    # [1/ppm] boron worth
#     G_fuel_coolant: float       = 3e6     # [W/K]   fuel–coolant conductance
#     fission_power_gain: float   = 1e9     # [W] at ρ = 1


#     def __init__(self, **data) -> None:
#         super().__init__(**data)
#         if self.coolant_P0 is None:
#             self.coolant_P0 = self.coolant_P
#         if self.coolant_V0 is None:
#             self.coolant_V0 = self.coolant.V
#         return

#     # --- Core update ---
#     def update_from_state(self, dt: float) -> None:
#         """
#         Advance the reactor node by dt seconds:
#         1) Add fission heat to fuel (simple reactivity model).
#         2) Exchange heat between fuel and coolant by a lumped conductance.
#         3) Update node pressure from cushion model using coolant volume.

#         Side-effects: mutates `fuel.U`, `coolant.U`, and `coolant_P`.
#         """
        
#         # Add fission heat to fuel based on reactivity
#         reactivity = (1.0 - self.control_rod_position) - (self.boron_ppm * self.alpha_boron)
#         power_fission = max(0.0, reactivity * self.fission_power_gain)
#         self.fuel.U += power_fission * dt

#         # Exchange heat between fuel and coolant
#         Tf = self.fuel.T
#         Tc = self.coolant.T
#         dU = self.G_fuel_coolant * (Tf - Tc) * dt

#         # Heat flows from fuel to coolant (sign by (Tf - Tc))
#         self.fuel.U    -= dU
#         self.coolant.U += dU

#         # Increase pressure based on cushion model
#         V = self.coolant.V
#         V0 = self.coolant_V0
#         P0 = self.coolant_P0
#         dPdV = self.coolant_dPdV
#         self.coolant_P = P0 + dPdV * (V - V0)

#         # Done
#         return


# Test
def test_file():
    """
    Test reactor node functionality.
    """
    # Create reactor
    reactor = Reactor()
    # Initial state
    initial_fuel_U     = reactor.fuel.U
    # Update reactor
    dt = 1.0  # [s]
    reactor.update_from_state(dt)
    # Check that fuel and coolant energies have changed
    assert reactor.fuel.U != initial_fuel_U
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

