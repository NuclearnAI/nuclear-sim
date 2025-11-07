
# Define exports
__all__ = [
    "LiquidVessel"
]

# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.liquids import Liquid


# Define liquid vessel node
class LiquidVessel(Node):
    """
    A node representing a vessel containing a liquid.
    """

    # Instance attributes
    V0: float | None = None  # [m^3]    Baseline volume for pressure calculation
    P0: float                # [Pa]     Baseline pressure for pressure calculation
    dPdV: float              # [Pa/m^3] Stiffness-like coefficient (dP/dV of "tank" cushion)
    liquid: Liquid           # [-]      Liquid stored in the vessel

    def __init__(self, **data) -> None:
        """Initialize liquid vessel node."""
        # Call super init
        super().__init__(**data)
        # Set baseline volume if not provided
        if self.V0 is None:
            self.V0 = self.liquid.V
        # Validate
        self.liquid.validate()
        # Done
        return

    # Add validation to update
    def update(self, dt):
        """
        Update method with validation.
        Args:
            dt: Time step size (s).
        """
        super().update(dt)
        self.liquid.validate()
        return
    
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
    # Import libraries
    from nuclear_simulator.sandbox.materials.liquids import Liquid
    # Create liquid
    class DummyLiquid(Liquid):
        HEAT_CAPACITY = 500.0
        DENSITY = 8000.0
    liquid = DummyLiquid(m=1000.0, U=1e6)
    # Create vessel
    vessel = LiquidVessel(liquid=liquid, P0=2e7, dPdV=1e9)
    # Update
    vessel.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

