
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any

# Import libraries
from pydantic import computed_field, ConfigDict
from nuclear_simulator.sandbox.materials import Material, Gas, Liquid
from nuclear_simulator.sandbox.physics.gases import calc_volume_ideal_gas
from nuclear_simulator.sandbox.plants.vessels.base import Vessel



# Define boiling vessel node
class BoilingVessel(Vessel):
    """
    A node representing a vessel containing both gas and liquid phases.
    """
    contents: None = None # Override contents to disable base class
    gas: Gas
    liquid: Liquid
    P: float | None = None
    V: float | None = None

    def __init__(self, **data) -> None:
        """Initialize vessel node."""

        # Call super init
        super().__init__(**data)

        # Set derived properties
        self.V = self.liquid.V + self.gas.V
        self.P = self.gas.P
        
        # Done
        return
    
    def get_contents(self):
        """Get contents as a list."""
        contents = []
        if self.gas is not None:
            contents.append(self.gas)
        if self.liquid is not None:
            contents.append(self.liquid)
        return contents
    
    def update_from_state(self, dt):
        """Update vessel from state."""
        
        # Get totals
        V_tot = self.V
        m_tot = self.gas.m + self.liquid.m
        U_tot = self.gas.U + self.liquid.U

        # Get liquid fraction
        liq_frac = self.liquid.boiling.calculate_liquid_fraction(
            m=m_tot,
            U=U_tot,
            V=V_tot,
        )

        # Update liquid contents
        m_liq = m_tot * liq_frac
        U_liq = U_tot * liq_frac
        liq_new = self.liquid.__class__(m=m_liq, U=U_liq)

        # Update gas contents
        m_gas = m_tot * (1 - liq_frac)
        U_gas = U_tot * (1 - liq_frac)
        V_gas = V_tot - liq_new.V
        gas_new = self.gas.__class__(m=m_gas, U=U_gas, V=V_gas)

        # Update pressure
        P_new = gas_new.P

        # Update attributes
        self.P = P_new
        self.gas = gas_new
        self.liquid = liq_new

        # Done
        return
    
class CondensingVessel(BoilingVessel):
    """
    A node representing a vessel containing both gas and liquid phases.
    Condensing vessel assumes heat loss to environment causes condensation.
    """
    pass


# Test
def test_file():
    # Import dummy materials
    from nuclear_simulator.sandbox.plants.materials import PWRSecondaryWater, PWRSecondarySteam
    # Create materials
    liquid = PWRSecondaryWater.from_temperature(m=1000, T=550.0)
    gas = PWRSecondarySteam.from_temperature_pressure(m=1000, T=600.0, P=2e7)
    # Create vessel
    vessel = BoilingVessel(
        gas=gas, 
        liquid=liquid, 
    )
    # Update
    vessel.update(.1)

    # Test contents
    print('contents' in vessel.state)
    print(vessel.contents)

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

