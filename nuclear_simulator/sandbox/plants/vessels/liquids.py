
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.liquids import Liquid


# Define liquid vessel node
class LiquidVessel(Node):
    """
    A node representing a vessel containing a liquid.
    Attributes:
        P:      [Pa]     Current pressure
        liquid: [-]      Liquid stored in the vessel
        V0:     [m^3]    Optional reference volume for pressure calculation
        P0:     [Pa]     Optional reference pressure for pressure calculation
        dP_dV:  [Pa/m^3] Optional reference stiffness for pressure calculation
    """
    P: float                    # [Pa]     Current pressure
    liquid: Liquid              # [-]      Liquid stored in the vessel
    V0: float | None = None     # [m^3]    Reference volume for pressure calculation
    P0: float | None = None     # [Pa]     Reference pressure for pressure calculation
    dP_dV: float | None = None  # [Pa/m^3] Reference stiffness for pressure calculation

    def __init__(self, **data) -> None:
        """Initialize liquid vessel node."""
        # Call super init
        super().__init__(**data)
        # Set derived attributes
        if self.V0 is None:
            self.V0 = self.liquid.V
        if self.P0 is None:
            self.P0 = self.P
        if self.dP_dV is None:
            # Default: 1% change in volume -> 10% change in pressure
            self.dP_dV = 10.0 * self.P0 / self.V0
        # Validate
        try:
            self.liquid.validate()
        except Exception as e:
            raise ValueError("Liquid validation failed during initialization.") from e
        # Done
        return

    def update_from_state(self, dt: float) -> None:
        """
        Advance the vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the vessel pressure `P`.
        """
        self.P = self.P0 + self.dP_dV * (self.liquid.V - self.V0)
        return
    
    @property
    def T(self) -> float:
        """[K] Current temperature of the liquid."""
        return self.liquid.T
    
    @property
    def m(self) -> float:
        """[kg] Current mass of the liquid."""
        return self.liquid.m
    
    @property
    def U(self) -> float:
        """[J] Current internal energy of the liquid."""
        return self.liquid.U
    
    @property
    def V(self) -> float:
        """[m^3] Current volume of the liquid."""
        return self.liquid.V
    



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
    vessel = LiquidVessel(liquid=liquid, P=2e7)
    # Update
    vessel.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

