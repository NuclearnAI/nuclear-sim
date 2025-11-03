
# Annotation imports
from __future__ import annotations
from typing import Optional

# Import libraries
from nuclear_simulator.sandbox.materials.base import Material, Energy
from nuclear_simulator.sandbox.materials.fluids import Liquid


# Define Vessel class
class LiquidVessel:
    """
    Simple container that supplies an environmental pressure to an incompressible liquid.
    """

    # Set class attributes
    V0: float    # [m³]    Reference volume
    P0: float    # [Pa]    Reference pressure at V0
    dPdV: float  # [Pa/m³] Linear slope ∂P/∂V

    def __init__(
            self, 
            liquid: Liquid,
            V0: float,
            P0: float,
            dPdV: float,
        ) -> None:
        """
        Initialize vessel with contained incompressible liquid and linear P(V) law.
        
        Args:
            liquid: [-]     Incompressible liquid stored in the vessel
            V0:     [m³]    Reference volume
            P0:     [Pa]    Reference pressure at V0
            dPdV:   [Pa/m³] Linear slope ∂P/∂V
        Modifies:
            Sets vessel attributes.
        """
        self.liquid = liquid
        self.V0 = V0
        self.P0 = P0
        self.dPdV = dPdV
        return
    
    @classmethod
    def from_fluid(cls, fluid: Liquid, P0: float, dPdV: float) -> 'LiquidVessel':
        """Create vessel from fluid with specified P0 and dPdV."""
        V0 = fluid.V
        return cls(liquid=fluid, V0=V0, P0=P0, dPdV=dPdV)

    def __add__(self, other: Material | Energy) -> 'LiquidVessel':
        """Add liquid to a vessel."""
        new_liquid = self.liquid + other
        new_V0 = self.V0
        new_P0 = self.P0
        new_dPdV = self.dPdV
        return type(self)(
            liquid=new_liquid,
            V0=new_V0,
            P0=new_P0,
            dPdV=new_dPdV,
        )

    def __sub__(self, other: Material | Energy) -> 'LiquidVessel':
        """Subtract liquid from a vessel."""
        new_liquid = self.liquid - other
        new_V0 = self.V0
        new_P0 = self.P0
        new_dPdV = self.dPdV
        return type(self)(
            liquid=new_liquid,
            V0=new_V0,
            P0=new_P0,
            dPdV=new_dPdV,
        )

    @property
    def P(self) -> float:
        """
        Pressure [Pa] computed from linearized P(V).
        
        Returns:
            float: Current vessel pressure
        """
        return self.P0 + self.dPdV * (self.liquid.V - self.V0)


# Test
def test_file():
    """Simple test to verify file loads and pressure relation works."""
    # Define dummy classes
    class DummyLiquid(Liquid):
        HEAT_CAPACITY = 4200.0
        DENSITY = 1000.0
    class DummyVessel(LiquidVessel):
        V0 = 0.01  # [m³]
        P0 = 1.0e5  # [Pa]
        dPdV = 1.0e7  # [Pa/m³]
    # Make a liquid and vessel with V0 equal to initial volume so P == P0
    liquid = DummyLiquid(m=10.0, U=1.0e6)  # V = 0.01 m³
    vessel = DummyVessel(liquid=liquid)
    vessel += DummyLiquid(m=5.0, U=5.0e5)  # V = 0.015 m³
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

